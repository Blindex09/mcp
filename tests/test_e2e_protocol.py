"""Ponta a ponta PELO PROTOCOLO MCP: o servidor roda como processo separado (como no Claude) e TODAS as ferramentas sao chamadas.

- um mini-site de varias paginas (tests/fixtures/mini_site) com defeitos de todo tipo, servido localmente;
- um servidor de modelo FALSO compativel com OpenAI, para o usuario autonomo, a escolha de guias e o aprendizado passarem por HTTP de verdade;
- no fim, a matriz: toda ferramenta registrada precisa ter sido exercitada.
"""
import http.server
import json
import os
import re
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


# ------------------------------------------------------------------ modelo falso (OpenAI-compativel)
class FakeModel(http.server.BaseHTTPRequestHandler):
    requests: ClassVar[list[dict]] = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        content = body["messages"][0]["content"]
        text = content if isinstance(content, str) else " ".join(p.get("text", "") for p in content if p.get("type") == "text")
        has_image = isinstance(content, list) and any(p.get("type") == "image_url" for p in content)
        kind = "learn" if "Voce mantem a memoria" in text else "report" if "RELATORIO desta sessao" in text else "find" if "You route accessibility work" in text else "step"
        FakeModel.requests.append({"model": body["model"], "kind": kind, "image": has_image, "auth": self.headers.get("authorization")})
        reply = self._reply(kind, text)
        data = json.dumps({"choices": [{"message": {"content": reply}}]}).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _reply(self, kind: str, text: str) -> str:
        if kind == "learn":
            return json.dumps([{"topic": "botao so de mouse", "learning": "div clicavel sem foco e sem papel indica controle so de mouse; sondar com teclado", "scope": "geral"}])
        if kind == "report":
            return "Relatorio: o usuario conseguiu ler a pagina, mas o botao Comprar nao recebe foco e o aviso de compra nao e anunciado. Nao foi verificado com leitor de tela real."
        if kind == "find":
            return json.dumps(["component-identity-guide", "nome-que-nao-existe"])
        step = int(re.search(r"PASSO (\d+)/", text).group(1))
        buy = re.search(r"^(e\d+) <div> .*nome='Comprar'.*$", text, re.MULTILINE)
        if step == 1:
            action = {"type": "page_map"}
        elif step == 2 and buy and "Acoes permitidas AGORA: announce, click" in text.replace("\n", " "):
            action = {"type": "click", "target": buy.group(1)}
        elif step == 2:
            action = {"type": "press", "value": "Tab"}
        else:
            action = {"type": "finish", "outcome": "completed_with_friction", "summary": "vi os problemas"}
        return json.dumps({"thought": f"passo {step}: olho a pagina", "friction": "controle so de mouse" if step == 2 else None, "look_next": False, "action": action})

    def log_message(self, *args, **kwargs):
        return


def serve(handler):
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def js(result):
    return json.loads(result.content[0].text)


@pytest.mark.slow
async def test_every_tool_over_the_real_protocol(tmp_path):
    site, model = serve(SiteHandler), serve(FakeModel)
    base = f"http://127.0.0.1:{site.server_address[1]}"
    SiteHandler.posts, FakeModel.requests = [], []
    env = {
        **os.environ, "PYTHONIOENCODING": "utf-8", "A11Y_MCP_HOME": str(tmp_path / "home"),
        "A11Y_MCP_BACKEND": "openai-compatible", "A11Y_MCP_BASE_URL": f"http://127.0.0.1:{model.server_address[1]}/v1",
        "A11Y_MCP_API_KEY": "chave-de-teste", "A11Y_MCP_MODEL": "fake-principal", "A11Y_MCP_MODEL_FAST": "fake-leve",
    }
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
        found = js(await call("a11y_find", task="preciso julgar o que cada componente e"))
        assert found["selection"] == "model" and [i["name"] for i in found["items"]] == ["component-identity-guide"]  # nome inventado descartado
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
        assert cmp["browsers"] == ["chromium", "firefox"] and cmp["differences"]["firefox"]["tab_order"] == "identica"

        # ---------- varias paginas
        crawl = js(await call("a11y_crawl", url=index, max_pages=8))
        visited = {p["url"].replace(base, "") for p in crawl["pages"]}
        assert {"/index.html", "/produtos.html", "/contato.html", "/sobre.html"} <= visited  # sobre so pelo sitemap e pelo menu
        assert [u.replace(base, "") for u in crawl["skipped"]["robots_disallowed"]] == ["/privado/x.html"]
        assert crawl["site_facts"]["duplicate_titles"][0]["title"] == "Página" and any("sobre" in u for u in crawl["site_facts"]["pages_without_lang"])

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
        assert js(await call("a11y_close"))["closed"] is True

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

        # ---------- usuario autonomo (modelo falso por HTTP) + aprendizado
        FakeModel.requests.clear()
        wt = js(await call("a11y_walkthrough", task="comprar um item", url=index, persona="default", max_steps=6))
        assert wt["outcome"] == "completed_with_friction" and wt["report"].startswith("Relatorio:") and wt["stopped_by"] == "finished"
        assert wt["coverage"]["page_map"] is True and wt["learned_topics"] == ["botao so de mouse"]
        assert "*" not in wt["report"]
        kinds = [(q["kind"], q["model"], q["image"]) for q in FakeModel.requests]
        assert kinds[0] == ("step", "fake-principal", True)  # 1o passo: com captura de tela
        assert all(model == "fake-principal" for kind, model, _ in kinds if kind in ("step", "report"))  # julgamento pesado: modelo principal
        assert ("learn", "fake-leve", False) in kinds  # lembrar e' leve: modelo barato
        assert not any(image for kind, _, image in kinds[1:] if kind == "step")  # captura so quando precisa
        rv = js(await call("a11y_review", focus="componentes e estrutura", url=index, max_steps=4))
        assert rv["report"].startswith("Relatorio:") and rv["facts"]["mode"] == "review"
        learned = js(await call("a11y_learnings"))
        assert [e["topic"] for e in learned["entries"]] == ["botao so de mouse"] and str(tmp_path / "home") in learned["folder"]
        assert js(await call("a11y_forget", topic="botao so de mouse"))["removed"] == 1

        # ---------- diagnostico
        st = js(await call("a11y_status"))
        assert st["model"]["ready"] is True and st["model"]["model_fast"] == "fake-leve" and st["browsers"]["chromium"]["state"] == "ready"
        assert "A11Y_MCP_API_KEY" not in json.dumps(st) and "chave-de-teste" not in json.dumps(st)  # nunca mostra segredos

    site.shutdown()
    model.shutdown()
    missing = registered - called
    assert not missing, f"ferramentas nao exercitadas pelo protocolo: {sorted(missing)}"
    assert registered == called  # a matriz fecha: nada registrado ficou sem prova pelo protocolo
