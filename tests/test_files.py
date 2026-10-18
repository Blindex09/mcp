"""Editor de arquivos: pasta de trabalho, troca exata, integridade, aprovacao, copia de seguranca e desfazer."""

import json

import pytest

from accessibility_mcp.a11y import files


@pytest.fixture(autouse=True)
def ambiente(tmp_path, monkeypatch):
    work = tmp_path / "projeto"
    work.mkdir()
    monkeypatch.setenv("A11Y_MCP_WORKSPACE", str(work))
    monkeypatch.setenv("A11Y_MCP_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("A11Y_MCP_EDIT_APPROVAL", "0")
    files.PENDING.clear()
    files.HISTORY.clear()
    return work


def _write(work, name, text, newline=""):
    path = work / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline=newline) as handle:
        handle.write(text)
    return path


class TestPastaDeTrabalho:
    def test_sem_pasta_definida_diz_o_que_fazer(self, monkeypatch):
        monkeypatch.delenv("A11Y_MCP_WORKSPACE")
        with pytest.raises(files.FileError, match="A11Y_MCP_WORKSPACE"):
            files.read_file("a.html")

    def test_fora_da_pasta_e_recusado(self, ambiente, tmp_path):
        outro = tmp_path / "fora.txt"
        outro.write_text("x", encoding="utf-8")
        with pytest.raises(files.FileError, match="fora da pasta"):
            files.read_file(str(outro))
        with pytest.raises(files.FileError, match="fora da pasta"):
            files.read_file("../fora.txt")

    def test_link_simbolico_para_fora_nao_escapa(self, ambiente, tmp_path):
        alvo = tmp_path / "segredo.txt"
        alvo.write_text("x", encoding="utf-8")
        try:
            (ambiente / "atalho.txt").symlink_to(alvo)
        except OSError:
            pytest.skip("sem permissao para criar link simbolico")
        with pytest.raises(files.FileError, match="fora da pasta"):
            files.read_file("atalho.txt")

    @pytest.mark.parametrize("nome", [".env", ".env.local", "chave.pem", "credentials.json", ".git/config"])
    def test_segredos_e_git_nao_sao_lidos_nem_escritos(self, ambiente, nome):
        _write(ambiente, nome, "SEGREDO=1")
        with pytest.raises(files.FileError):
            files.read_file(nome)
        with pytest.raises(files.FileError):
            files.edit_file(nome, "SEGREDO=1", "SEGREDO=2")


class TestLeitura:
    def test_numera_as_linhas_e_aceita_recorte(self, ambiente):
        _write(ambiente, "a.html", "um\ndois\ntres\n")
        r = files.read_file("a.html", offset=1, limit=1)
        assert r["total_lines"] == 3 and r["from_line"] == 2 and r["content"].endswith("dois")

    def test_arquivo_binario_e_recusado(self, ambiente):
        (ambiente / "b.bin").write_bytes(b"\x00\x01\x02")
        with pytest.raises(files.FileError, match="binario"):
            files.read_file("b.bin")


class TestEdicaoExata:
    def test_troca_um_trecho_unico_e_preserva_o_fim_de_linha(self, ambiente):
        caminho = _write(ambiente, "p.html", "<img src=a>\r\n<p>x</p>\r\n")
        r = files.edit_file("p.html", "<img src=a>", '<img src=a alt="logo">')
        assert r["applied"] and "alt" in r["diff"]
        assert caminho.read_bytes() == b'<img src=a alt="logo">\r\n<p>x</p>\r\n'

    def test_trecho_ausente_e_trecho_repetido_dizem_o_que_fazer(self, ambiente):
        _write(ambiente, "p.html", "<b>a</b><b>a</b>")
        with pytest.raises(files.FileError, match="nao existe"):
            files.edit_file("p.html", "<i>", "<em>")
        with pytest.raises(files.FileError, match="2 vezes"):
            files.edit_file("p.html", "<b>", "<strong>")
        assert files.edit_file("p.html", "<b>", "<strong>", replace_all=True)["applied"]
        assert (ambiente / "p.html").read_text(encoding="utf-8") == "<strong>a</b><strong>a</b>"

    def test_igual_e_vazio_sao_recusados(self, ambiente):
        _write(ambiente, "p.html", "x")
        with pytest.raises(files.FileError, match="iguais"):
            files.edit_file("p.html", "x", "x")
        with pytest.raises(files.FileError, match="so serve para criar"):
            files.edit_file("p.html", "", "y")

    def test_cria_arquivo_novo_com_old_vazio(self, ambiente):
        r = files.edit_file("novo/pagina.html", "", "<h1>oi</h1>")
        assert r["created"] and (ambiente / "novo" / "pagina.html").read_text(encoding="utf-8") == "<h1>oi</h1>"


class TestIntegridade:
    def test_json_valido_nao_pode_virar_invalido(self, ambiente):
        caminho = _write(ambiente, "c.json", '{"a": 1}')
        with pytest.raises(files.FileError, match="invalido"):
            files.edit_file("c.json", '"a": 1', '"a": ')
        assert json.loads(caminho.read_text(encoding="utf-8")) == {"a": 1}

    def test_python_valido_nao_pode_virar_invalido(self, ambiente):
        _write(ambiente, "m.py", "x = 1\n")
        with pytest.raises(files.FileError, match="invalido"):
            files.edit_file("m.py", "x = 1", "x = ")

    def test_arquivo_que_ja_estava_quebrado_pode_ser_consertado(self, ambiente):
        _write(ambiente, "c.json", '{"a": ')
        assert files.edit_file("c.json", '{"a": ', '{"a": 1}')["applied"]


class TestAprovacao:
    def test_ligada_a_edicao_fica_retida_e_nada_muda_ate_a_resposta(self, ambiente, monkeypatch):
        monkeypatch.setenv("A11Y_MCP_EDIT_APPROVAL", "1")
        caminho = _write(ambiente, "p.html", "<img src=a>")
        r = files.edit_file("p.html", "<img src=a>", '<img src=a alt="x">')
        assert r["held"] and "alt" in r["diff"] and caminho.read_text(encoding="utf-8") == "<img src=a>"
        decidido = files.decide("allow", r["approval_id"])
        assert decidido["results"][0]["applied"]
        assert 'alt="x"' in caminho.read_text(encoding="utf-8")

    def test_negar_nao_escreve(self, ambiente, monkeypatch):
        monkeypatch.setenv("A11Y_MCP_EDIT_APPROVAL", "1")
        caminho = _write(ambiente, "p.html", "a")
        r = files.edit_file("p.html", "a", "b")
        assert files.decide("deny", r["approval_id"])["results"][0]["denied"]
        assert caminho.read_text(encoding="utf-8") == "a" and not files.PENDING

    def test_arquivo_que_mudou_durante_a_espera_nao_e_sobrescrito(self, ambiente, monkeypatch):
        monkeypatch.setenv("A11Y_MCP_EDIT_APPROVAL", "1")
        caminho = _write(ambiente, "p.html", "a")
        r = files.edit_file("p.html", "a", "b")
        caminho.write_text("a editado por outra pessoa", encoding="utf-8")
        resultado = files.decide("allow", r["approval_id"])["results"][0]
        assert "mudou" in resultado["error"]
        assert caminho.read_text(encoding="utf-8") == "a editado por outra pessoa"

    def test_desligada_edita_sem_perguntar(self, ambiente):
        _write(ambiente, "p.html", "a")
        assert files.edit_file("p.html", "a", "b")["applied"] is True

    def test_decisao_invalida_e_sem_retidas(self):
        with pytest.raises(files.FileError):
            files.decide("talvez")
        with pytest.raises(files.FileError, match="Nao ha edicao retida"):
            files.decide("allow")


class TestDesfazer:
    def test_restaura_o_conteudo_original_pelo_backup(self, ambiente):
        caminho = _write(ambiente, "p.html", "original")
        r = files.edit_file("p.html", "original", "mudou")
        assert caminho.read_text(encoding="utf-8") == "mudou"
        assert files.undo_edit(r["edit_id"])["restored_from_backup"]
        assert caminho.read_text(encoding="utf-8") == "original"

    def test_desfazer_um_arquivo_criado_remove_o_arquivo(self, ambiente):
        files.edit_file("novo.html", "", "x")
        files.undo_edit()
        assert not (ambiente / "novo.html").exists()

    def test_sem_edicoes_diz_que_nao_ha_o_que_desfazer(self):
        with pytest.raises(files.FileError, match="Nao ha edicao"):
            files.undo_edit()

    def test_o_backup_fica_fora_do_projeto(self, ambiente, tmp_path):
        _write(ambiente, "p.html", "a")
        files.edit_file("p.html", "a", "b")
        assert not list(ambiente.glob("**/*.a11y-tmp"))
        assert list((tmp_path / "home" / "edit-backups").rglob("p.html"))


class TestFerramentasMcp:
    async def test_as_quatro_ferramentas_estao_registradas(self):
        from accessibility_mcp.server import mcp

        nomes = {t.name for t in await mcp.list_tools()}
        assert {"a11y_read_file", "a11y_edit_file", "a11y_approve_edit", "a11y_undo_edit"} <= nomes

    async def test_erro_volta_como_texto_com_a_razao_nunca_excecao(self, ambiente):
        from accessibility_mcp.server import mcp

        resposta = await mcp.call_tool("a11y_read_file", {"path": "../fora.txt"})
        texto = str(resposta)
        assert "fora da pasta" in texto
