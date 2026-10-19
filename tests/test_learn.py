"""Aprendizado sempre: o modelo do cliente decide o que lembrar (a11y_learn); o codigo guarda, valida, marca a origem e nao duplica."""
import json

from accessibility_mcp.a11y import learn


def test_learning_is_stored_outside_the_project_and_is_immediately_relevant(tmp_path):
    assert learn.store_path() == tmp_path / "a11y-home"  # isolado pelo conftest; em uso real: ~/.a11y-mcp
    learn.remember("loja.com", "menu so por hover", "no site loja.com o menu Produtos so abre com o mouse; sondar com hover")
    learn.remember(learn.GENERAL, "sondagem", "clicar e ler a diferenca na arvore mostra o que cada componente e")
    assert (tmp_path / "a11y-home" / "learnings.json").exists()
    assert {e["topic"] for e in learn.relevant("loja.com")} == {"menu so por hover", "sondagem"}
    assert {e["topic"] for e in learn.relevant("outro.com")} == {"sondagem"}  # o especifico do site nao vaza para outros


def test_every_entry_says_it_was_written_by_the_client_model():
    entry = learn.remember(learn.GENERAL, "origem", "texto")
    assert entry is not None and entry["origin"] == learn.ORIGIN == "cliente"
    assert json.loads((learn.store_path() / "learnings.json").read_text(encoding="utf-8"))["entries"][0]["origin"] == "cliente"


def test_same_topic_updates_the_existing_entry_never_duplicates():
    learn.remember("loja.com", "Menu so por hover", "versao 1")
    learn.remember("loja.com", "menu  SO por hover", "versao 2 com mais detalhe")
    learn.remember("loja.com", "menu so por hover", "versao 3")
    mine = [e for e in learn.load_all() if e["scope"] == "loja.com"]
    assert len(mine) == 1 and mine[0]["learning"] == "versao 3"  # mesmo assunto (texto normalizado): atualiza, nao duplica


def test_omission_never_deletes_and_removal_must_be_explicit():
    learn.remember("loja.com", "a", "errado")
    learn.remember(learn.GENERAL, "b", "geral")
    learn.remember("outro.com", "c", "de outro site")  # nao menciona a nem b
    assert {e["topic"] for e in learn.load_all()} == {"a", "b", "c"}  # esquecer de citar nao apaga nada
    merged = learn.merge_changes(learn.load_all(), [{"topic": "A", "scope": "loja.com", "remove": True}], {"loja.com"})
    assert {e["topic"] for e in merged} == {"b", "c"}
    merged = learn.merge_changes(merged, [{"topic": "b", "scope": "estranho.com", "remove": True}], {"loja.com"})
    assert {e["topic"] for e in merged} == {"b", "c"}  # escopo alheio ao permitido: ignorado


def test_empty_or_invalid_input_never_corrupts_the_store():
    learn.remember(learn.GENERAL, "ok", "valido")
    for topic, text, scope in (("", "sem topico", "geral"), ("t", "", "geral"), ("t", "sem escopo", ""), ("  ", "  ", "geral")):
        assert learn.remember(scope, topic, text) is None
    assert learn.merge_changes(learn.load_all(), ["lixo", 3, None, {"topic": "x"}], {"geral"}) == learn.load_all()
    assert [e["topic"] for e in learn.load_all()] == ["ok"]


def test_size_limits_and_opt_out(monkeypatch):
    for i in range(50):
        learn.remember(learn.GENERAL, f"t{i}", "x" * 900)
    stored = learn.load_all()
    assert len(stored) == learn.MAX_PER_SCOPE and all(len(e["learning"]) <= learn.MAX_LEARNING_CHARS for e in stored)  # teto por escopo
    monkeypatch.setenv("A11Y_MCP_LEARN", "0")
    assert learn.remember(learn.GENERAL, "novo", "n") is None
    assert learn.enabled() is False and not any(e["topic"] == "novo" for e in learn.load_all())


def test_forget_is_the_persons_control_and_host_extraction():
    learn._save([{"topic": "a", "learning": "1", "scope": "g"}, {"topic": "a", "learning": "2", "scope": "x.com"}])
    assert learn.forget("A", "x.com") == 1 and [e["scope"] for e in learn.load_all()] == ["g"]
    assert learn.forget("nao existe") == 0
    assert learn.host_of("https://Loja.com.br:8443/a?b=1") == "loja.com.br" and learn.host_of(None) == "html-local"


async def test_the_learn_tool_saves_lists_and_forgets_through_the_server():
    from accessibility_mcp import server as mcp_server

    call = lambda name, **kw: mcp_server.mcp._tool_manager.get_tool(name).fn(**kw)
    saved = json.loads(await call("a11y_learn", topic="foco", learning="o foco some depois do dialogo fechar", scope="loja.com"))
    assert saved["saved"]["scope"] == "loja.com" and saved["saved"]["origin"] == "cliente"
    assert [e["topic"] for e in json.loads(await call("a11y_learnings", host="loja.com"))["entries"]] == ["foco"]
    assert "nada gravado" in json.loads(await call("a11y_learn", topic="", learning="x"))["error"]
    assert json.loads(await call("a11y_forget", topic="foco"))["removed"] == 1
    assert json.loads(await call("a11y_learnings"))["entries"] == []
