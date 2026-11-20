"""O MCP entrega sozinho o que antes se conferia a mao: codigo real, percurso medido, correcao testada, relatorio conferido."""
import http.server
import threading
from typing import ClassVar

import httpx
import pytest

from accessibility_mcp.a11y import code_evidence, journey, nvda_vm, report_lint
from accessibility_mcp.a11y.session import SESSION

# ----------------------------------------------------------------------------------------------- codigo real
ASSETS = {
    "DOM renderizado": '<button type="button" data-testid="go" aria-pressed="false">Ir</button>',
    "https://site.test/app.js": 'const a=1;function f(){setTimeout(()=>{x.focus()},0)}const b=2;',
}


def test_exact_snippet_is_found_with_asset_position_and_fingerprint():
    found = code_evidence.locate("setTimeout(()=>{x.focus()},0)", ASSETS)
    assert found["found"] and found["matches"][0]["asset"] == "https://site.test/app.js"
    assert found["matches"][0]["position"] == ASSETS["https://site.test/app.js"].find("setTimeout")
    assert len(found["matches"][0]["fingerprint"]) == 10


def test_paraphrased_shortened_or_whitespace_changed_snippets_are_reported_with_the_reason():
    assert "nao existe" in code_evidence.locate("setTimeout(()=>{x?.focus()},0)", ASSETS)["problem"]
    shortened = code_evidence.locate('<button type="button" … aria-pressed="false">', ASSETS)
    assert not shortened["found"] and shortened["placeholder"] and "nao e' copia literal" in shortened["problem"]
    spaced = code_evidence.locate("setTimeout(() => { x.focus() }, 0)", ASSETS)
    assert not spaced["found"] and spaced["found_ignoring_whitespace"] == "https://site.test/app.js" and "espacos" in spaced["problem"]


def test_snippet_blocks_skip_the_header_lines_of_the_report_cell():
    cell = ('Copiado de https://site.test.\n\nHTML, etapa 1:\n<button>Ir</button>\n\nJS, posicao 10:\nconst a=1;')
    assert code_evidence.snippet_blocks(cell) == ["Copiado de https://site.test.", "<button>Ir</button>", "const a=1;"]
    verdict = code_evidence.verify(["const a=1;", "nada disso"], ASSETS)
    assert not verdict["all_found"] and "#2" in verdict["summary"]


# ----------------------------------------------------------------------------------------------- percurso
def _effect(**kw):
    base = {"focus_before": {"tag": "button", "name": "Escolher"}, "focus_after": {"tag": "button", "name": "Escolher"},
            "tree_added": [], "tree_removed": [], "announcements": [], "url_changed": None}
    return {**base, **kw}


def test_journey_flags_focus_on_body_unannounced_change_and_focus_jump_while_typing():
    drop = journey.judge({"action": "click", "label": "Escolher destino"},
                         _effect(focus_after=None, tree_added=['- button "Canadá"'], tree_removed=['- button "Escolher"']))
    assert {i["check"] for i in drop} == {"foco_cai_no_corpo", "mudanca_nao_anunciada"}
    behind = journey.judge({"action": "press", "label": "Avançar"}, _effect(tree_removed=['- textbox "Idade"'], tree_added=['- textbox "Data"']))
    assert "foco_fica_para_tras" in {i["check"] for i in behind}
    announced = journey.judge({"action": "click", "label": "ok"}, _effect(focus_after=None, tree_added=["- p: oi"], announcements=[{"text": "Etapa 2"}]))
    assert {i["check"] for i in announced} == {"foco_cai_no_corpo"}
    jump = journey.judge({"action": "type", "label": "idade"}, _effect(focus_after={"tag": "input", "name": "Idade 2"}, focus_before={"tag": "input", "name": "Idade 1"}))
    assert [i["check"] for i in jump] == ["foco_pula_ao_digitar"] and jump[0]["criterion"] == "3.2.2"
    assert journey.judge({"action": "click"}, _effect()) == []


# ----------------------------------------------------------------------------------------------- conferencia do relatorio
def test_report_lint_lists_what_a_reviewer_would_point_out():
    findings = [
        {"id": "f1", "outcome": "failed", "evidence_steps": [], "report_details": {
            "screen": "Home", "reproduction_steps_visual": ["a"], "reproduction_steps_screen_reader": ["Tab: fala"],
            "code_snippet": '<svg…/>', "fixed_code": "<b>x</b>", "code_verified": False}},
        {"id": "f2", "outcome": "failed", "evidence_steps": [3], "report_details": {
            "screen": "Home", "reproduction_steps_visual": ["a"], "code_snippet": "<a>", "code_verified": True,
            "fixed_code": "<a href>", "fix_tested": True, "design_impact": "Nenhum"}},
        {"id": "f3", "outcome": "passed"},
    ]
    result = report_lint.lint({"findings": findings})
    rules = {(i["finding"], i["rule"]) for i in result["issues"]}
    assert {("F1", "codigo_resumido"), ("F1", "codigo_nao_achado"), ("F1", "correcao_nao_testada"), ("F1", "impacto_no_design_ausente"),
            ("F1", "leitor_sem_evidencia")} <= rules
    code_rules = {"codigo_ausente", "codigo_resumido", "codigo_nao_achado", "codigo_nao_conferido", "correcao_ausente", "correcao_nao_testada", "impacto_no_design_ausente"}
    assert not any(i["finding"] == "F2" and i["rule"] in code_rules for i in result["issues"]) and not any(i["finding"] == "F3" for i in result["issues"])
    assert result["ok"] is False and result["counts"]["erro"] >= 6
    assert report_lint.lint({"findings": []})["ok"] is True


# ----------------------------------------------------------------------------------------------- VM do NVDA mudou de endereco
async def test_nvda_vm_is_found_again_when_its_address_changed(monkeypatch):
    monkeypatch.setattr(nvda_vm, "_neighbors", lambda: ["192.168.80.1", "192.168.80.131", "192.168.80.254", "10.0.0.5"])
    assert nvda_vm.candidate_bases("http://192.168.80.128:8765") == ["http://192.168.80.131:8765"]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "192.168.80.128":
            raise httpx.ConnectError("sem rota", request=request)
        return httpx.Response(202, json={"id": "j1"})

    monkeypatch.setattr(nvda_vm, "_found_base", None)
    monkeypatch.setattr(nvda_vm, "_neighbors", lambda: ["192.168.80.131"])
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        resp, base = await nvda_vm._post_found(client, "http://192.168.80.128:8765", "/sessao/comando", {})
    assert resp.status_code == 202 and base == "http://192.168.80.131:8765" and nvda_vm._found_base == base
    monkeypatch.setenv("A11Y_MCP_NVDA_VM", "http://192.168.80.128:8765")
    monkeypatch.setenv("A11Y_MCP_NVDA_TOKEN", "t")
    assert nvda_vm.configured() == ("http://192.168.80.131:8765", "t")


async def test_nvda_vm_gives_an_actionable_error_when_nothing_answers(monkeypatch):
    monkeypatch.setattr(nvda_vm, "_found_base", None)
    monkeypatch.setattr(nvda_vm, "_neighbors", list)

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sem rota", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(nvda_vm.NvdaVmError, match="DHCP"):
            await nvda_vm._post_found(client, "http://192.168.80.128:8765", "/x", {})


# ----------------------------------------------------------------------------------------------- correcao testada de verdade
class Site(http.server.BaseHTTPRequestHandler):
    PAGE: ClassVar[bytes] = (b'<!doctype html><html lang="pt"><title>t</title><body><h1 id="t" tabindex="-1">Titulo</h1>'
                             b'<div id="step1"><button id="go" type="button">Escolher</button></div><div id="step2" hidden><p>Nova etapa</p></div>'
                             b'<script src="/app.js"></script></body></html>')
    JS: ClassVar[bytes] = (b'const FOCO_NA_ETAPA=false;\n'
                           b'document.getElementById("go").addEventListener("click",()=>{document.getElementById("step1").remove();'
                           b'const s=document.getElementById("step2");s.hidden=false;if(FOCO_NA_ETAPA){s.setAttribute("tabindex","-1");s.focus()}});')

    def do_GET(self):
        body, kind = (self.JS, "application/javascript") if self.path == "/app.js" else (self.PAGE, "text/html; charset=utf-8")
        self.send_response(200)
        self.send_header("content-type", kind)
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args, **kwargs):
        return


@pytest.fixture()
def site():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Site)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


async def test_a_fix_is_tested_in_the_session_without_touching_the_site(site):
    await SESSION.open(site, None, persona="default")
    try:
        async with SESSION.lock:
            assets = await code_evidence.collect_assets(SESSION)
        real = "const FOCO_NA_ETAPA=false;"
        assert code_evidence.verify([real], assets)["all_found"]
        assert not code_evidence.verify(["const FOCO_NA_ETAPA = false;"], assets)["all_found"]

        steps = [{"action": "click", "target": "css:#go", "label": "Escolher"}]
        async with SESSION.lock:
            before = await journey.run(SESSION, steps)
        assert {i["check"] for i in before["issues"]} >= {"foco_cai_no_corpo", "mudanca_nao_anunciada"}

        async with SESSION.lock:
            patched = await SESSION.try_patch("/app.js", real, "const FOCO_NA_ETAPA=true;")
            assert patched["hits"] == 1 and patched["active_patches"] == 1
            after = await journey.run(SESSION, steps)
        assert after["issues"] == [], after
        missing = await SESSION.try_patch("/app.js", "texto que nao existe", "x")
        assert missing["hits"] == 0 and "problem" in missing and len(SESSION.patches) == 1
        assert SESSION.clear_patches() == 1
        assert Site.JS.count(b"FOCO_NA_ETAPA=false") == 1  # o arquivo do site nao foi alterado
    finally:
        await SESSION.close()


def _complete_finding():
    return {"id": "f9", "criterion": "4.1.2", "claim": "Botão sem nome", "outcome": "failed", "severity": "serious", "priority": "P1", "evidence_steps": [4],
            "page_url": "https://x.test/", "recommendation": "Dar nome ao botão.",
            "report_details": {
                "screen": "Home", "problem_location": "Home > botão Ir", "actual_result": "sem nome", "expected_result": "com nome", "criterion_rationale": "sem nome acessivel",
                "environment": "Windows, Edge", "operating_system": "Windows 11", "browsers": "Edge", "testing_method": "NVDA e teclado", "page_area": "topo",
                "reproduction_steps_visual": ["Abrir a página e olhar o botão."], "reproduction_steps_screen_reader": ["Tab: o NVDA fala \"botão\"."],
                "code_snippet": "<button>Ir</button>", "fixed_code": '<button aria-label="Ir">Ir</button>', "design_impact": "Nenhum",
                "code_verified": True, "fix_tested": True}}


def test_house_rule_nothing_unconfirmed_and_nothing_missing_blocks_the_report():
    pending = {**_complete_finding(), "outcome": "cantTell"}
    assert "achado_nao_confirmado" in {i["rule"] for i in report_lint.lint({"findings": [pending]})["issues"]}
    proposed = _complete_finding()
    proposed["report_details"] = {**proposed["report_details"], "reproduction_steps_screen_reader": [], "reproduction_steps_screen_reader_proposed": ["Apertar Tab."]}
    assert "leitor_nao_executado" in {i["rule"] for i in report_lint.lint({"findings": [proposed]})["issues"]}
    declared = _complete_finding()
    declared["report_details"] = {**declared["report_details"], "reproduction_steps_screen_reader": ["Não se aplica: contraste não é falado pelo leitor de tela."]}
    declared["evidence_steps"] = []
    assert not {"leitor_sem_evidencia", "leitor_nao_executado"} & {i["rule"] for i in report_lint.lint({"findings": [declared]})["issues"]}
    empty_screen = report_lint.lint({"findings": [], "report_context": {"screens": [{"name": "Compra", "items": []}]}})
    assert [i["rule"] for i in empty_screen["issues"]] == ["tela_sem_conteudo"]


async def test_create_report_refuses_to_generate_an_incomplete_report(tmp_path, monkeypatch):
    import json

    from accessibility_mcp.server import mcp

    monkeypatch.setenv("A11Y_MCP_DOCUMENTS_DIR", str(tmp_path / "docs"))
    await SESSION.open(None, "<html lang=pt><title>t</title><body><button>Ir</button></body></html>")
    try:
        SESSION.findings.append({"id": "f1", "criterion": "4.1.2", "claim": "Botão sem nome", "outcome": "failed", "severity": "serious"})
        tool = mcp._tool_manager.get_tool("a11y_create_report")
        blocked = json.loads(await tool.fn(formats="xlsx"))
        assert "relatorio NAO gerado" in blocked["error"] and blocked["lint"]["ok"] is False
        assert not (tmp_path / "docs").exists()
        draft = json.loads(await tool.fn(formats="xlsx", allow_incomplete=True))
        assert "error" not in draft and draft["lint"]["ok"] is False
    finally:
        await SESSION.close()


# ----------------------------------------------------------------------------------------------- de onde veio o elemento
def test_enclosing_call_returns_the_exact_jsx_call_even_with_parentheses_inside_strings():
    js = 'var a=1;const el=(0,G.jsxs)("div",{className:"x",children:[(0,G.jsx)("button",{"data-testid":"go-btn",title:"a)b(",children:f(1,2)})]});var z=2;'
    pos = js.find('"go-btn"')
    inner = code_evidence.enclosing_call(js, pos)
    assert inner["excerpt"] == '(0,G.jsx)("button",{"data-testid":"go-btn",title:"a)b(",children:f(1,2)})'
    assert js[inner["start"]:inner["end"]] == inner["excerpt"] and not inner.get("truncated")
    nothing = code_evidence.enclosing_call("abc def", 3)
    assert "nao achei" in nothing["note"]


def test_element_tokens_and_sources_use_testid_stem_text_and_classes():
    info = {"attrs": {"data-testid": "wizard-age-0", "class": "a b c"}, "text": "Idade"}
    tokens = code_evidence.element_tokens(info)
    assert tokens[:4] == ["a b c", "wizard-age-0", "wizard-age-", "Idade"] or tokens[:3] == ["wizard-age-0", "wizard-age-", "Idade"] or "wizard-age-" in tokens
    bundle = 'x=(0,G.jsx)("input",{name:"traveler-age-".concat(a),"data-testid":"wizard-age-".concat(a),placeholder:"Idade"})'
    sources = code_evidence.find_sources(info, {"https://s.test/main.js": bundle, "DOM renderizado": '"wizard-age-"'})
    assert sources and sources[0]["code"].startswith('(0,G.jsx)("input"') and sources[0]["asset"] == "https://s.test/main.js"
    assert sources[0]["position"] == bundle.find("(0,G.jsx)")


class JsxSite(http.server.BaseHTTPRequestHandler):
    JS: ClassVar[bytes] = (b'const G={jsx:(t,p)=>{const e=document.createElement(t);for(const k in p){if(k==="children")e.textContent=p[k];else e.setAttribute(k,p[k])}return e}};\n'
                           b'document.body.append((0,G.jsx)("button",{"data-testid":"go-btn",type:"button",children:"Escolher"}));')

    def do_GET(self):
        page = (b'<!doctype html><html lang="pt"><title>t</title><style>button{color:#8a8a8a}</style><body><script src="/app.js"></script></body></html>')
        body, kind = (self.JS, "application/javascript") if self.path == "/app.js" else (page, "text/html; charset=utf-8")
        self.send_response(200)
        self.send_header("content-type", kind)
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args, **kwargs):
        return


async def test_source_of_returns_the_defective_code_from_the_site_and_findings_can_be_filled_from_tested_patches():
    import json

    from accessibility_mcp.server import mcp

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), JsxSite)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        await SESSION.open(f"http://127.0.0.1:{srv.server_address[1]}", None, persona="default")
        source = json.loads(await mcp._tool_manager.get_tool("a11y_source_of").fn(target="css:[data-testid=go-btn]"))
        real = '(0,G.jsx)("button",{"data-testid":"go-btn",type:"button",children:"Escolher"})'
        assert source["js_sources"][0]["code"] == real and source["js_sources"][0]["asset"].endswith("/app.js")
        assert source["html"]["code"] == '<button data-testid="go-btn" type="button">Escolher</button>'
        assert source["trace_step"] and any(rule["source"] and rule["source"]["code"] == "button{color:#8a8a8a}" for rule in source["css_rules"])
        async with SESSION.lock:
            patched = await SESSION.try_patch("/app.js", real, real.replace('type:"button"', 'type:"button","aria-label":"Escolher destino"'))
        assert patched["hits"] == 1
        finding = json.loads(await mcp._tool_manager.get_tool("a11y_finding").fn(
            claim="Botão sem nome completo", criterion="2.4.6", severity="moderate", from_patches=True, evidence_steps=str(source["trace_step"]), screen="Home"))
        details = finding["recorded"]["report_details"]
        assert real in details["code_snippet"] and '"aria-label":"Escolher destino"' in details["fixed_code"]
        assert details["code_verified"] is True and details["fix_tested"] is True
        SESSION.clear_patches()
        refused = json.loads(await mcp._tool_manager.get_tool("a11y_finding").fn(claim="x", from_patches=True))
        assert "from_patches=true precisa" in refused["error"]
    finally:
        await SESSION.close()
        srv.shutdown()


def test_css_source_returns_the_original_rule_text_and_skips_selector_lists_that_only_end_in_it():
    sheet = ".a,.b{color:red}.b{color:blue}@media (min-width:1px){.b{font-size:9px}}"
    assert code_evidence.css_source(".b", {"main.css": sheet})["code"] == ".b{color:blue}"
    assert code_evidence.css_source(".a, .b", {"main.css": sheet})["code"] == ".a,.b{color:red}"
    assert code_evidence.css_source(".nao", {"main.css": sheet}) is None
    ranked = code_evidence.rank_css_rules([{"selector": "*, ::after, ::before"}, {"selector": ".wc-cami-lockup-role"}])
    assert ranked[0]["selector"] == ".wc-cami-lockup-role"


def test_css_source_ignores_a_comment_before_the_rule():
    sheet = "/* ── Seguro hero row ── */\n        .lv2-hero-row { gap: 10px; }"
    assert code_evidence.css_source(".lv2-hero-row", {"estilo embutido #1": sheet})["code"] == ".lv2-hero-row { gap: 10px; }"


def test_sources_follow_a_testid_that_comes_from_a_constants_table():
    bundle = ('K={ESIM_DESTINATION:"awz-esim-destination",OTHER:"x"};'
              'a=(0,G.jsx)("input",{"data-testid":V.Y9.ADDON_WIZARD.ESIM_DESTINATION,type:"search",placeholder:"Busque"});b=1;')
    sources = code_evidence.find_sources({"attrs": {"data-testid": "awz-esim-destination"}, "text": ""}, {"https://s.test/main.js": bundle})
    assert sources and sources[0]["code"] == '(0,G.jsx)("input",{"data-testid":V.Y9.ADDON_WIZARD.ESIM_DESTINATION,type:"search",placeholder:"Busque"})'


class LazySite(http.server.BaseHTTPRequestHandler):
    PAGE: ClassVar[bytes] = (b'<!doctype html><html lang="pt"><title>t</title><body><script>'
                             b'const s=document.createElement("script");s.src="/chunk.7f3a.js";s.onload=()=>s.remove();document.head.appendChild(s);</script></body></html>')
    CHUNK: ClassVar[bytes] = b'const G={jsx:(t,p)=>{const e=document.createElement(t);for(const k in p){k==="children"?e.textContent=p[k]:e.setAttribute(k,p[k])}return e}};document.body.append((0,G.jsx)("button",{"data-testid":"lazy-btn",children:"Carregado depois"}));'

    def do_GET(self):
        body, kind = (self.CHUNK, "application/javascript") if self.path.startswith("/chunk.7f3a.js") else (self.PAGE, "text/html; charset=utf-8")
        self.send_response(200)
        self.send_header("content-type", kind)
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args, **kwargs):
        return


async def test_code_from_a_lazy_chunk_that_removed_its_own_script_tag_is_still_found():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), LazySite)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        await SESSION.open(f"http://127.0.0.1:{srv.server_address[1]}", None, persona="default")
        await SESSION.page.wait_for_selector("[data-testid=lazy-btn]")
        assert await SESSION.page.evaluate("document.scripts.length") == 1  # a tag do chunk ja saiu do documento
        async with SESSION.lock:
            assets = await code_evidence.collect_assets(SESSION)
        assert any(name.endswith("/chunk.7f3a.js") for name in assets)
        found = code_evidence.find_sources({"attrs": {"data-testid": "lazy-btn"}, "text": ""}, assets)
        assert found and found[0]["code"] == '(0,G.jsx)("button",{"data-testid":"lazy-btn",children:"Carregado depois"})'
    finally:
        await SESSION.close()
        srv.shutdown()
