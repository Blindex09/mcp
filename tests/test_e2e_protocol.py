"""Ponta a ponta PELO PROTOCOLO MCP: o servidor roda como processo separado (como no Claude) e TODAS as ferramentas sao chamadas.

- um mini-site de varias paginas (tests/fixtures/mini_site) com defeitos de todo tipo, servido localmente;
- o servidor NAO chama modelo: nenhum modelo e' configurado aqui, e o fluxo de achados, execucoes salvas e aprendizado e' conduzido pelo cliente;
- no fim, a matriz: toda ferramenta registrada precisa ter sido exercitada.
"""
import http.server
import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import ClassVar

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "tests" / "fixtures" / "mini_site"


# ------------------------------------------------------------------ site
class SiteHandler(http.server.SimpleHTTPRequestHandler):
    posts: ClassVar[list[str]] = []

    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(SITE), **k)

    def do_GET(self):
        if self.path == "/robots.txt":
            self._text("User-agent: *\nDisallow: /privado/\n", "text/plain")
        elif self.path == "/sitemap.xml":
            self._text(f"<urlset><url><loc>http://{self.headers['Host']}/sobre.html</loc></url></urlset>", "application/xml")
        else:
            super().do_GET()

    def do_POST(self):
        SiteHandler.posts.append(self.path)
        self._text("<html><body>recebido</body></html>", "text/html")

    def _text(self, body, ctype):
        data = body.encode()
        self.send_response(200)
        self.send_header("content-type", ctype)
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args, **kwargs):
        return


def start_vm_agent(token: str):
    """Sobe o agente da VM (nvda/vm) com um NVDA simulado: prova o contrato Python x Node pelo protocolo. Sem Node, segue sem VM."""
    node = shutil.which("node")
    if not node:
        return None, None, {}
    proc = subprocess.Popen(
        [node, str(ROOT / "nvda" / "vm" / "simulado.mjs")], stdout=subprocess.PIPE, text=True,
        env={**os.environ, "NVDA_AGENT_TOKEN": token},
    )
    assert proc.stdout is not None
    line = proc.stdout.readline()
    assert line.startswith("PORTA "), line
    return node, proc, {"A11Y_MCP_NVDA_VM": f"http://127.0.0.1:{line.split()[1]}", "A11Y_MCP_NVDA_TOKEN": token}


def serve(handler):
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def js(result):
    return json.loads(result.content[0].text)


@pytest.mark.slow
async def test_every_tool_over_the_real_protocol(tmp_path):
    site = serve(SiteHandler)
    base = f"http://127.0.0.1:{site.server_address[1]}"
    SiteHandler.posts = []
    env = {
        **os.environ, "PYTHONIOENCODING": "utf-8", "A11Y_MCP_HOME": str(tmp_path / "home"),
    }
    for chave in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_API_KEY"):
        env.pop(chave, None)  # prova: nada de provedor de modelo no ambiente, e o servidor funciona do mesmo jeito
    ws_dir = tmp_path / "projeto"
    ws_dir.mkdir()
    (ws_dir / "pagina.html").write_text("<img src=a.png>\n", encoding="utf-8")
    env.update({"A11Y_MCP_EDIT_APPROVAL": "1"})  # nenhuma pasta configurada: a pessoa a escolhe na conversa
    vm_token = "token-de-teste-com-mais-de-16"
    node, vm, vm_env = start_vm_agent(vm_token)  # agente da VM de verdade (Node), com NVDA SIMULADO por tras
    env.update(vm_env)
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "mcp_server.py")], env=env)
    called: set[str] = set()

    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        registered = {t.name for t in (await s.list_tools()).tools}

        async def call(tool, /, **args):
            called.add(tool)
            return await s.call_tool(tool, args)

        # ---------- conhecimento e escolha
        cat = js(await call("a11y_list_content"))
        assert any(c["name"] == "page-structure-review" for c in cat) and all(c["quando_usar"] for c in cat)
        assert "a11y_find" not in registered and "a11y_walkthrough" not in registered and "a11y_review" not in registered  # nada depende de modelo
        prompts = {p.name for p in (await s.list_prompts()).prompts}
        assert prompts == {"a11y_review", "a11y_walkthrough", "a11y_component", "a11y_site_scan", "a11y_compare_runs", "a11y_write_accessible_code", "a11y_accessible_document"}
        guided = (await s.get_prompt("a11y_review", {"url": f"{base}/index.html"})).messages[0].content.text
        assert "testing-playbook-for-ai" in guided and "NOT verified" in guided and "a11y_probe" in guided
        assert (await call("a11y_workflow", name="a11y_review", url=f"{base}/index.html")).content[0].text == guided  # a mesma coisa por ferramenta (clientes sem prompts)
        assert "Component Identity Guide" in (await call("a11y_get_reference", name="component-identity-guide")).content[0].text
        assert "modal" in (await call("a11y_get_example", name="modal-native-dialog")).content[0].text.lower()
        assert "conversationReducer" in (await call("a11y_get_template", name="assets/accessible-ai-react/src/ai/turnReducer.js")).content[0].text
        assert js(await call("a11y_contrast", foreground="#767676", background="#ffffff"))["AA_text"] is True

        # ---------- medicao rapida (sem sessao)
        index = f"{base}/index.html"
        axe = js(await call("a11y_audit", url=index))
        assert {"image-alt", "color-contrast"} <= {v["id"] for v in axe["violations"]} or "image-alt" in {v["id"] for v in axe["violations"]}
        assert "navigation" in (await call("a11y_aria_snapshot", url=index)).content[0].text
        assert js(await call("a11y_tab_order", url=index))[0]["element"]["name"] == "Início"
        cmp = js(await call("a11y_compare_browsers", url=index, browsers="chromium,firefox"))
        assert cmp["browsers"] == ["chromium", "firefox"]
        # Diferenca real entre navegadores (antes escondida: a varredura parava no 1o passo e tudo parecia "identica"):
        # o Firefox faz o proprio iframe ser uma parada de Tab antes do conteudo dele; o Chromium vai direto ao conteudo.
        tabs = cmp["differences"]["firefox"]["tab_order"]
        assert tabs != "identica" and len(tabs["chromium"]) >= 8
        assert [t for t in tabs["firefox"] if not t.startswith("iframe:")] == tabs["chromium"]
        assert any(t.startswith("iframe:") for t in tabs["firefox"]) and not any(t.startswith("iframe:") for t in tabs["chromium"])

        # ---------- varias paginas
        crawl = js(await call("a11y_crawl", url=index, max_pages=8))
        visited = {p["url"].replace(base, "") for p in crawl["pages"]}
        assert {"/index.html", "/produtos.html", "/contato.html", "/sobre.html"} <= visited  # sobre so pelo sitemap e pelo menu
        assert [u.replace(base, "") for u in crawl["skipped"]["robots_disallowed"]] == ["/privado/x.html"]
        assert crawl["site_facts"]["duplicate_titles"][0]["title"] == "Página" and any("sobre" in u for u in crawl["site_facts"]["pages_without_lang"])

        # ---------- verificacao de comportamento em UMA chamada (cliente que nao mantem sessao)
        one = js(await call("a11y_check_page", url=index, probes=json.dumps([{"kind": "disclosure", "target": "css:button"}])))
        assert one["tab_walk"]["stops"] and one["elements"] and all(e["css"] for e in one["elements"]) and one["probes"][0]["kind"] == "disclosure"
        assert "leitor de tela real" in one["not_verified"]

        # ---------- sessao: olhos, maos e cobertura
        opened = js(await call("a11y_open", url=index, persona="default"))
        assert opened["mutations"] == "permitidas" and opened["browser"] == "chromium"
        pm = js(await call("a11y_page_map"))
        m = pm["main"]
        assert {"from": 1, "to": 3, "text": "Destaques (pulou o h2)"} in m["headings"]["level_jumps"]
        assert any(i["alt"] is None for i in m["images"]["items"]) and m["links"]["same_text_different_destination"]
        assert m["tables"]["items"][0]["header_cells"] == 0 and m["media"][0]["tracks"] == [] and m["iframes"][0]["title"] == "Mapa da loja"
        assert any(h["rule"] == ".dd:hover .menu" for h in m["hover_reveals"]["items"]) and pm["frames"][0]["map"]["headings"]["outline"][0]["text"] == "Mapa"
        dossier = js(await call("a11y_dossier", max_elements=100))
        by_text = {e["text"]: e for e in dossier["elements"] if e["text"]}
        assert by_text["Comprar"]["clickable"] and not by_text["Comprar"]["focusable"] and by_text["Comprar"]["computed"]["role"] == "generic"
        assert by_text["Ver detalhes"]["where"]["in_shadow"] and by_text["Abrir mapa"]["where"]["frame_url"].startswith("about:srcdoc")
        assert js(await call("a11y_observe"))["title"] == "Mini Loja"
        clicked = js(await call("a11y_act", action="click", target=by_text["Comprar"]["id"]))
        assert clicked["announcements"] == []  # o aviso aparece na arvore mas NAO e anunciado
        assert any("Adicionado ao carrinho" in x for x in clicked["tree_added"])
        fav = js(await call("a11y_act", action="click", target=by_text["Favoritar"]["id"]))
        assert fav["focus_after"] is None or fav["action"] == "click"
        reach = js(await call("a11y_reach", target=by_text["Ver detalhes"]["id"]))
        assert reach["reached"] is True
        assert "button" in js(await call("a11y_announce", target=by_text["Ver detalhes"]["id"]))["accessibility_tree"]
        assert js(await call("a11y_focus_style", target=by_text["Abrir mapa"]["id"]))["properties_changed"] >= 0
        assert js(await call("a11y_design_tokens"))["base"]["body_size"] == "13px"
        prev = js(await call("a11y_preview_css", target=by_text["Comprar"]["id"], css="font-size: 18px"))
        assert prev["after"]["font-size"] == "18px"
        assert js(await call("a11y_preview_css", target=by_text["Comprar"]["id"], revert=True))["reverted"] is True
        shot = await call("a11y_screenshot")
        assert shot.content[0].type == "image" and shot.content[0].mimeType == "image/jpeg"
        assert "horizontal_scroll" in js(await call("a11y_stress", kind="reflow_320"))
        assert "clipped_before" in js(await call("a11y_stress", kind="text_spacing"))
        cov = js(await call("a11y_coverage"))
        assert cov["page_map"] is True and cov["design_measured"] and cov["stress_run"] == ["reflow_320", "text_spacing"]
        assert any("nunca foram sondados" in g for g in cov["gaps"])
        # ---------- sondas de comportamento, achados com evidencia e exportacao
        walk = js(await call("a11y_probe", kind="tab_walk"))
        assert walk["stops_total"] >= 3 and "ended_because" in walk
        assert "tab_walk" in js(await call("a11y_coverage"))["probes_run"]
        trace = js(await call("a11y_trace"))
        n_probe = trace["steps"][-1]["n"]
        assert trace["steps"][-1]["kind"] == "probe:tab_walk"
        rec = js(await call("a11y_finding", claim="o botao Comprar so funciona com mouse", criterion="2.1.1", severity="blocker", target=by_text["Comprar"]["id"], evidence_steps=str(n_probe)))
        assert rec["recorded"]["outcome"] == "failed" and rec["recorded"]["element"]["name"] == "Comprar"
        earl = js(await call("a11y_report", format="earl", save=False))
        assert earl["@graph"][0]["earl:result"]["earl:outcome"] == {"@id": "earl:failed"} and "run_id" not in earl
        assert js(await call("a11y_report", format="sarif", save=False))["runs"][0]["results"][0]["ruleId"] == "WCAG-2.1.1"
        first_run = js(await call("a11y_report", format="json", goal="comprar um item"))["run_id"]  # guarda a execucao para exportar e comparar
        assert js(await call("a11y_close"))["closed"] is True

        # ---------- documentos reais e relatorio dos achados medidos, pelo mesmo protocolo
        generated = js(await call("a11y_create_document", document={"title": "Guia de teclado", "blocks": [{"kind": "paragraph", "text": "Percorra os controles e registre o foco."}]}, formats="docx"))
        assert "error" not in generated
        output = generated["files"][0]
        assert js(await call("a11y_validate_document", path=output["path"], external=False))["status"] == "automated_checks_passed"
        resource = await s.read_resource(output["uri"])
        assert resource.contents[0].mimeType == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        report_file = js(await call("a11y_create_report", formats="docx", run_id=first_run))
        assert report_file["files"][0]["validation"]["status"] == "automated_checks_passed"

        # ---------- persona imposta pelo servidor (sem mouse)
        js(await call("a11y_open", url=index, persona="keyboard"))
        refused = js(await call("a11y_act", action="click", target="e1"))
        assert "nao tem mouse" in refused["error"]
        await call("a11y_close")

        # ---------- aprovacao: retido ate a pessoa decidir
        contato = f"{base}/contato.html"
        opened = js(await call("a11y_open", url=contato, allow_mutations="ask"))
        assert opened["mutations"].startswith("COM APROVACAO")
        els = {e["text"]: e for e in js(await call("a11y_dossier"))["elements"] if e["text"]}
        pend = js(await call("a11y_act", action="click", target=els["Enviar"]["id"]))["approvals_pending"]
        assert len(pend) == 1 and pend[0]["kind"] == "envio de formulario" and SiteHandler.posts == []  # retido: o servidor nao recebeu
        assert not any(ch in json.dumps(pend) for ch in ("@",))  # so nomes de campos, nunca valores
        denied = js(await call("a11y_approve", decision="deny"))
        assert denied["decided"][0]["decision"] == "deny" and SiteHandler.posts == []
        pend2 = js(await call("a11y_act", action="click", target=els["Enviar"]["id"]))["approvals_pending"]
        approved = js(await call("a11y_approve", decision="allow", ids=pend2[0]["id"]))
        assert approved["decided"][0]["decision"] == "allow" and SiteHandler.posts == ["/enviar"]  # so depois da aprovacao
        await call("a11y_close")

        # ---------- segunda execucao conduzida pelo cliente, execucoes salvas e aprendizado (sem modelo no servidor)
        js(await call("a11y_open", url=index, persona="keyboard"))
        js(await call("a11y_probe", kind="tab_walk"))
        weak = js(await call("a11y_finding", claim="a ordem de Tab parece estranha"))
        assert weak["recorded"]["outcome"] == "cantTell"  # sem evidencia valida nunca vira failed
        second_run = js(await call("a11y_report", format="json"))["run_id"]
        await call("a11y_close")
        assert first_run and second_run and first_run != second_run
        listing = js(await call("a11y_runs"))
        assert {r["run_id"] for r in listing["runs"]} >= {first_run, second_run} and listing["enabled"] is True
        assert js(await call("a11y_export", run_id=first_run, format="sarif"))["version"] == "2.1.0"
        assert js(await call("a11y_diff", base_run_id=first_run, head_run_id=second_run))["counts"]["fixed"] >= 1  # o achado do 1o nao esta no 2o
        saved = js(await call("a11y_learn", topic="botao so de mouse", learning="div clicavel sem foco e sem papel indica controle so de mouse; sondar com teclado"))
        assert saved["saved"]["origin"] == "cliente" and saved["saved"]["scope"] == "geral"
        again = js(await call("a11y_learn", topic="Botao  SO de mouse", learning="versao 2"))  # mesmo assunto: atualiza, nunca duplica
        assert again["saved"]["learning"] == "versao 2"
        learned = js(await call("a11y_learnings"))
        assert [e["topic"] for e in learned["entries"]] == ["Botao  SO de mouse"] and str(tmp_path / "home") in learned["folder"]
        assert js(await call("a11y_forget", topic="botao so de mouse"))["removed"] == 1

        # ---------- fala real do NVDA (VM): so fatos, com a origem declarada
        spoken = js(await call("a11y_nvda_speech", url=base + "/index.html", tabs=2, reads=1))
        if node:
            assert [x["fala"] for x in spoken["tab_walk"]] == ["Tab 1 em 127.0.0.1", "Tab 2 em 127.0.0.1"]
            assert spoken["reading_mode"][0]["fala"] == "item 1" and "VM" in spoken["source"]
            assert vm_token not in json.dumps(spoken)
        else:
            assert "A11Y_MCP_NVDA_VM" in spoken["error"]

        # ---------- editor de arquivos: ler, editar (retido ate a resposta), aprovar, desfazer
        assert "a11y_set_workspace" in js(await call("a11y_read_file", path="pagina.html"))["error"]
        assert js(await call("a11y_set_workspace", path=str(ws_dir)))["workspace"]
        lido = js(await call("a11y_read_file", path="pagina.html"))
        assert lido["total_lines"] == 1 and "<img src=a.png>" in lido["content"]
        retido = js(await call("a11y_edit_file", path="pagina.html", old_string="<img src=a.png>", new_string='<img src=a.png alt="logo">'))
        assert retido["held"] and (ws_dir / "pagina.html").read_text(encoding="utf-8") == "<img src=a.png>\n"
        decidido = js(await call("a11y_approve_edit", decision="allow", approval_id=retido["approval_id"]))
        assert decidido["results"][0]["applied"] and 'alt="logo"' in (ws_dir / "pagina.html").read_text(encoding="utf-8")
        assert js(await call("a11y_undo_edit"))["restored_from_backup"] is True
        assert (ws_dir / "pagina.html").read_text(encoding="utf-8") == "<img src=a.png>\n"
        assert "fora da pasta" in js(await call("a11y_read_file", path="../fora.txt"))["error"]

        # ---------- diagnostico
        st = js(await call("a11y_status"))
        assert st["browsers"]["chromium"]["state"] == "ready" and "nao chama modelo" in st["model"]

    site.shutdown()
    if vm:
        vm.kill()
        vm.wait()
    missing = registered - called
    assert not missing, f"ferramentas nao exercitadas pelo protocolo: {sorted(missing)}"
    assert registered == called  # a matriz fecha: nada registrado ficou sem prova pelo protocolo
