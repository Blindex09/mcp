"""a11y_inspect mede o elemento como o DevTools: HTML completo, estilos com origem, estados forcados, ouvintes, caixa e acessibilidade."""
import http.server
import json
import threading

import pytest

from accessibility_mcp.a11y import inspect_dom
from accessibility_mcp.a11y.session import SESSION, SessionError

PAGE = b"""<!doctype html><html lang="pt"><head><title>t</title>
<style>
.cta { color: #333; background: #fff; }
.cta:hover { color: #c00; }
.cta:focus-visible { outline: 3px solid #00f; }
</style></head><body>
<button class="cta" id="go" style="margin: 7px" data-testid="go-btn" aria-label="Escolher destino">Escolher</button>
<my-card id="card">cartao</my-card>
<script>
  document.getElementById('go').addEventListener('click', function abrirPainel() { window.aberto = true; });
  document.getElementById('go').__reactFiber$abc = {};
</script>
<script src="/app.js"></script>
</body></html>"""
JS = b"console.log('app');\n//# sourceMappingURL=app.js.map\n"


class Site(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body, kind = (JS, "application/javascript") if self.path == "/app.js" else (PAGE, "text/html; charset=utf-8")
        self.send_response(200)
        self.send_header("content-type", kind)
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args, **kwargs):
        return


@pytest.fixture
async def page():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Site)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    await SESSION.open(f"http://127.0.0.1:{srv.server_address[1]}", None, persona="default")
    try:
        yield
    finally:
        await SESSION.close()
        srv.shutdown()


async def test_inspect_returns_what_devtools_shows_for_an_element(page):
    async with SESSION.lock:
        got = await inspect_dom.inspect_element(SESSION, "css:#go")
    assert got["html"]["code"] == '<button class="cta" id="go" style="margin: 7px" data-testid="go-btn" aria-label="Escolher destino">Escolher</button>'
    assert got["attributes"]["data-testid"] == "go-btn" and "data-a11y-id" not in got["attributes"]
    assert {"name": "margin", "value": "7px"} in got["inline_style"] or any(p["name"].startswith("margin") for p in got["inline_style"])
    cta = next(r for r in got["matched_rules"] if r["selector"] == ".cta")
    assert cta["origin"] == "regular" and cta["embedded_in_html"] is True and cta["sheet"].startswith("http://127.0.0.1:") and cta["line"] == 3
    assert cta["code"].replace(" ", "").startswith(".cta{color:#333;background:#fff;}".replace(" ", ""))
    assert got["computed_style"]["color"] == "rgb(51, 51, 51)"
    assert got["box"]["content"]["w"] > 0
    assert got["accessibility"]["role"] == "button" and got["accessibility"]["name"] == "Escolher destino"
    assert any(src.get("attribute") == "aria-label" for src in got["accessibility"]["name_sources"])


async def test_forced_states_show_what_changes_on_hover_and_focus_visible(page):
    async with SESSION.lock:
        got = await inspect_dom.inspect_element(SESSION, "css:#go")
    assert got["state_changes"]["hover"]["color"] == ["rgb(51, 51, 51)", "rgb(204, 0, 0)"]
    assert got["state_changes"]["focus-visible"]["outline-style"][1] == "solid"
    assert got["state_changes"]["hover"].get("outline-style") is None


async def test_listeners_and_technology_markers_are_reported_as_facts(page):
    async with SESSION.lock:
        got = await inspect_dom.inspect_element(SESSION, "css:#go", properties=["display"], states=False)
        card = await inspect_dom.inspect_element(SESSION, "css:#card")
    clicks = [ln for ln in got["event_listeners"] if ln["type"] == "click"]
    # o navegador situa a funcao na lista de parametros: o trecho comeca ali e segue com o corpo real do ouvinte
    assert clicks and clicks[0]["code"].startswith("() { window.aberto = true; })") and clicks[0]["line"] == 10
    assert got["computed_style"] == {"display": "inline-block"} and got["state_changes"] == {}
    assert got["technologies"]["markers"]["react"] is True and got["technologies"]["markers"]["web_components"] == ["my-card"]
    assert any(url.endswith("/app.js") for url in got["technologies"]["served_files"]["with_source_map"])
    assert card["event_listeners"] == []


async def test_inspect_refuses_a_missing_element(page):
    async with SESSION.lock:
        with pytest.raises(SessionError, match="nao encontrado"):
            await inspect_dom.inspect_element(SESSION, "css:#nao-existe")


async def test_the_tool_is_registered_and_leaves_a_trace_step(page):
    from accessibility_mcp.server import mcp

    out = json.loads(await mcp._tool_manager.get_tool("a11y_inspect").fn(target="css:#go", states=False))
    assert out["trace_step"] and out["accessibility"]["name"] == "Escolher destino"
