"""Regressao: a ordem de Tab identifica o elemento pelo no real, nao pela descricao (tag, nome, estilo).

Antes, dois links diferentes com o mesmo texto e sem id pareciam "o mesmo elemento": a_tab_order parava no primeiro,
como se o foco tivesse deixado de mover. Achado numa loja de teste com quatro "clique aqui".
"""
import http.server
import threading

import pytest

from accessibility_mcp.a11y import audit
from accessibility_mcp.a11y.compare import compare_browsers
from accessibility_mcp.a11y.session import SESSION

SAME_NAMES = (
    "<html lang=pt><title>t</title><body><main>"
    "<a href='#1'>clique aqui</a> <a href='#2'>clique aqui</a> <a href='#3'>clique aqui</a> <a href='#4'>clique aqui</a>"
    "</main></body></html>"
)
# Dois links iguais DENTRO de um iframe do mesmo site, entre dois botoes.
IFRAME_SAME_NAMES = (
    "<html lang=pt><title>t</title><body><main><button>Antes</button>"
    "<iframe title='Quadro' srcdoc=\"<a href='#a'>Ler mais</a> <a href='#b'>Ler mais</a>\"></iframe>"
    "<button>Depois</button></main></body></html>"
)
# Um Shadow DOM aberto com dois botoes iguais.
SHADOW_SAME_NAMES = (
    "<html lang=pt><title>t</title><body><main><x-c></x-c></main><script>"
    "const r = document.querySelector('x-c').attachShadow({mode: 'open'});"
    "r.innerHTML = '<button>Comprar</button><button>Comprar</button>';"
    "</script></body></html>"
)


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
async def test_tab_order_lists_every_link_even_when_their_text_is_identical(browser):
    stops = await audit.tab_order(html=SAME_NAMES, browser=browser)
    assert [s["element"]["name"] for s in stops] == ["clique aqui"] * 4, browser


async def test_tab_order_walks_through_same_named_links_inside_an_iframe():
    stops = await audit.tab_order(html=IFRAME_SAME_NAMES)
    assert [s["element"]["name"] for s in stops] == ["Antes", "Ler mais", "Ler mais", "Depois"]


async def test_tab_order_walks_through_same_named_buttons_in_open_shadow_dom():
    stops = await audit.tab_order(html=SHADOW_SAME_NAMES)
    assert [s["element"]["name"] for s in stops] == ["Comprar", "Comprar"]


async def test_tab_order_output_shape_is_unchanged():
    stops = await audit.tab_order(html=SAME_NAMES)
    assert set(stops[0]) == {"step", "element"}
    assert set(stops[0]["element"]) == {"tag", "role", "name", "id", "visible", "focus_style"}
    assert [s["step"] for s in stops] == [1, 2, 3, 4]


async def test_compare_browsers_sees_every_tab_stop_when_names_repeat():
    r = await compare_browsers(html=SAME_NAMES, browsers=["chromium", "firefox"])
    assert r["per_browser"]["chromium"]["tab_stops"] == ["a:clique aqui"] * 4
    assert r["per_browser"]["firefox"]["tab_stops"] == ["a:clique aqui"] * 4
    assert r["differences"]["firefox"]["tab_order"] == "identica"


async def test_reach_finds_the_fourth_of_four_identical_links_without_relying_on_ids():
    await SESSION.open(None, SAME_NAMES)
    try:
        d = await SESSION.dossier()
        ids = [e["id"] for e in d["elements"]]
        assert len(ids) == 4
        r = await SESSION.reach(ids[3])
        assert r["reached"] is True and r["tab_presses"] == 4
    finally:
        await SESSION.close()


async def test_reach_wraps_around_only_when_it_is_really_the_same_element():
    """Ainda detecta a volta ao inicio: com um alvo inexistente na ordem de foco, a lista percorre os 4 e para."""
    await SESSION.open(None, SAME_NAMES + "<div id='x' onclick='1'>so mouse</div>")
    try:
        d = await SESSION.dossier()
        mouse_only = [e for e in d["elements"] if not e["focusable"]]
        assert mouse_only, "o navegador deveria listar o div clicavel que nao entra na ordem de Tab"
        r = await SESSION.reach(mouse_only[0]["id"])
        assert r["reached"] is False and len(r["path"]) == 4
    finally:
        await SESSION.close()




# ----------------------------------------------------------------- acoes delegadas: proveniencia como fato
APP_JS = "document.addEventListener('click', function (e) { if (e.target.closest('.aba')) document.title = 'x'; });"
DELEGATING_PAGE = (
    "<html lang=pt><title>t</title><body><main><h1>Abas</h1>"
    "<div class='aba' style='cursor:pointer'>Camisetas</div><div class='aba' style='cursor:pointer'>Tenis</div></main>"
    "<script src='/app.js'></script></body></html>"
)
PLAIN_PAGE = "<html lang=pt><title>t</title><body><main><button>Ok</button></main></body></html>"


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        routes = {
            "/delegando.html": ("text/html", DELEGATING_PAGE), "/app.js": ("application/javascript", APP_JS),
            "/simples.html": ("text/html", PLAIN_PAGE),
        }
        ctype, body = routes.get(self.path, ("text/plain", "nao existe"))
        self.send_response(200 if self.path in routes else 404)
        self.send_header("content-type", ctype)
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *args, **kwargs):
        return


@pytest.fixture()
def served():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


async def test_dossier_and_coverage_say_when_a_page_script_delegates_actions_to_ancestors(served):
    """Fato, nao adivinhacao: o dossie nao inventa quais elementos sao clicaveis por delegacao, mas avisa que podem faltar."""
    await SESSION.open(f"{served}/delegando.html", None)
    try:
        d = await SESSION.dossier()
        page_owned = [x for x in d["delegated_listeners"] if x["source"]]
        assert any(x["on"] == "document" and x["type"] == "click" and x["source"].endswith("/app.js:1:10") for x in page_owned)
        assert any("delegacao" in limit for limit in d["limits"])
        assert any("ancestrais" in g for g in SESSION.coverage_report()["gaps"])
    finally:
        await SESSION.close()


async def test_playwrights_own_window_listeners_are_never_reported_as_the_page_s(served):
    """Regressao: apos agir na pagina, o Playwright registra 8 listeners em window; eles apareciam como delegacao da pagina."""
    await SESSION.open(f"{served}/simples.html", None)
    try:
        await SESSION.dossier()
        await SESSION.act("hover", "css:button")
        m = await SESSION.page_map()
        assert not any(d["source"] for d in m["delegated_listeners"]), m["delegated_listeners"]
        d = await SESSION.dossier()
        assert "delegated_listeners" not in d
        assert not any("delegacao" in limit for limit in d.get("limits", []))
        assert not any("ancestrais" in g for g in SESSION.coverage_report()["gaps"])
    finally:
        await SESSION.close()
