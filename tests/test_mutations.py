"""Exploracao segura: em sites nao-locais o teste nao pode alterar dados (POST/PUT/PATCH/DELETE/envio de formulario)."""
import http.server
import threading
from typing import ClassVar

import pytest

from a11y.session import SESSION, SessionError, is_local_dev


class Recorder(http.server.BaseHTTPRequestHandler):
    seen: ClassVar[list[str]] = []

    def _do(self):
        Recorder.seen.append(self.command)
        body = b"<html><body>ok</body></html>" if self.command == "GET" and self.path == "/page" else b"ok"
        self.send_response(200)
        self.send_header("content-type", "text/html" if self.path == "/page" else "text/plain")
        self.send_header("access-control-allow-origin", "*")
        self.end_headers()
        self.wfile.write(body)

    do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = _do

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("access-control-allow-origin", "*")
        self.send_header("access-control-allow-methods", "GET, POST, PUT, PATCH, DELETE")
        self.send_header("access-control-allow-headers", "*")
        self.end_headers()

    def log_message(self, *args, **kwargs):
        return


@pytest.fixture()
def api():
    Recorder.seen = []
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Recorder)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def page(api_url: str) -> str:
    return f"""<!doctype html><html lang="pt"><title>m</title><body>
    <form id="f" method="post" action="{api_url}/form"><button id="enviar">Enviar formulario</button></form>
    <button id="post">Comprar (POST)</button><button id="get">Ler (GET)</button><div id="out"></div>
    <script>
     document.getElementById('post').addEventListener('click', () => fetch('{api_url}/order', {{method: 'POST', body: 'x'}}).then(() => {{ out.textContent = 'POST ok'; }}).catch(() => {{ out.textContent = 'POST falhou'; }}));
     document.getElementById('get').addEventListener('click', () => fetch('{api_url}/data').then(() => {{ out.textContent = 'GET ok'; }}));
    </script></body></html>"""


def test_which_hosts_count_as_local_development():
    for url in (None, "", "http://localhost:3000/x", "http://127.0.0.1:8000", "http://[::1]:8080/", "https://app.localhost/", "http://loja.test/"):
        assert is_local_dev(url), url
    for url in ("https://example.com/", "http://192.168.0.10/", "https://staging.empresa.com.br/", "http://localhost.evil.com/"):
        assert not is_local_dev(url), url


async def test_block_mode_stops_post_fetch_and_form_submission_from_reaching_the_server(api):
    await SESSION.open(None, page(api), allow_mutations="block")
    try:
        els = {e["text"]: e["id"] for e in (await SESSION.dossier())["elements"]}
        r = await SESSION.act("click", els["Comprar (POST)"])
        assert r["mutations_blocked"] and r["mutations_blocked"][0].startswith("POST ")
        r2 = await SESSION.act("click", els["Enviar formulario"])
        assert any(m.startswith("POST ") and m.endswith("/form") for m in SESSION.blocked)
        assert "POST" not in Recorder.seen  # o servidor NUNCA recebeu o POST
        assert await SESSION.page.locator("#enviar").count() == 1  # a pagina continua onde estava (nao virou pagina de erro)
        await SESSION.act("click", els["Ler (GET)"])
        assert "GET" in Recorder.seen  # leitura continua livre
        assert any("requisicao(oes) que alterariam dados" in g for g in SESSION.coverage_report()["gaps"])
        assert r2["mutations_blocked"] is not None
    finally:
        await SESSION.close()


async def test_allow_mode_lets_the_request_through(api):
    opened = await SESSION.open(None, page(api), allow_mutations="allow")
    try:
        assert opened["mutations"] == "permitidas"
        els = {e["text"]: e["id"] for e in (await SESSION.dossier())["elements"]}
        r = await SESSION.act("click", els["Comprar (POST)"])
        assert r["mutations_blocked"] == [] and "POST" in Recorder.seen
    finally:
        await SESSION.close()


async def test_auto_mode_allows_local_dev_and_open_reports_the_policy(api):
    opened = await SESSION.open(f"{api}/page", None)  # 127.0.0.1: desenvolvimento local
    try:
        assert opened["mutations"] == "permitidas" and SESSION.allow_mutations is True
    finally:
        await SESSION.close()
    blocked = await SESSION.open(None, page(api), allow_mutations="block")
    try:
        assert blocked["mutations"].startswith("BLOQUEADAS")
    finally:
        await SESSION.close()


async def test_invalid_mode_is_a_usage_error():
    with pytest.raises(SessionError, match="allow_mutations"):
        await SESSION.open(None, "<html></html>", allow_mutations="talvez")


async def test_agent_and_tools_carry_the_policy(api):
    import json

    import mcp_server

    tools = mcp_server.mcp._tool_manager
    out = json.loads(await tools.get_tool("a11y_open").fn(html=page(api), allow_mutations="block"))
    try:
        assert out["mutations"].startswith("BLOQUEADAS")
    finally:
        await tools.get_tool("a11y_close").fn()


# ---------------- aprovacao ligada/desligada (regra: nunca recusa seca) ----------------

def form_page(api_url: str) -> str:
    return f"""<!doctype html><html lang="pt"><title>a</title><body>
    <button id="post">Comprar</button><div id="out"></div>
    <script>document.getElementById('post').addEventListener('click', () =>
      fetch('{api_url}/order', {{method: 'POST', headers: {{'content-type': 'application/json'}}, body: JSON.stringify({{item: 'cha', senha: 'segredo123'}})}})
        .then(r => r.text()).then(t => {{ document.getElementById('out').textContent = 'Pedido criado'; }}));
    </script></body></html>"""


def test_policy_resolution_and_payload_summary_never_leaks_values():
    from a11y.session import effective_policy, payload_summary

    assert effective_policy("auto", "http://localhost:3000") == "allow"
    assert effective_policy("auto", "https://loja-real.com.br/") == "ask"  # aprovacao ligada onde ha risco real
    assert effective_policy("allow", "https://loja-real.com.br/") == "allow"
    assert effective_policy("block", "http://localhost/") == "block"
    s = payload_summary("post", "https://x.com/pay?token=abc", '{"cartao": "4111111111111111", "nome": "Ana"}', "application/json", False)
    assert s["method"] == "POST" and s["fields"] == ["cartao (16 caracteres)", "nome (3 caracteres)"]
    assert "4111" not in str(s) and "Ana" not in str(s)  # nomes e tamanhos, nunca o conteudo
    f = payload_summary("POST", "https://x.com/f", "email=a%40b.com&senha=zzz", "application/x-www-form-urlencoded", True)
    assert f["kind"] == "envio de formulario" and f["fields"] == ["email (7 caracteres)", "senha (3 caracteres)"]


async def test_ask_mode_holds_the_request_shows_what_it_would_change_and_sends_only_after_approval(api):
    opened = await SESSION.open(None, form_page(api), allow_mutations="ask")
    try:
        assert opened["mutations"].startswith("COM APROVACAO")
        buy = (await SESSION.dossier())["elements"][0]["id"]
        r = await SESSION.act("click", buy)
        assert len(r["approvals_pending"]) == 1
        item = r["approvals_pending"][0]
        assert item["method"] == "POST" and item["kind"] == "chamada da pagina"
        assert item["fields"] == ["item (3 caracteres)", "senha (10 caracteres)"]  # mostra o que mudaria, sem os valores
        assert "segredo123" not in str(item)
        assert "POST" not in Recorder.seen  # RETIDA: o servidor ainda nao recebeu nada
        assert await SESSION.page.locator("#out").inner_text() == ""
        out = await SESSION.decide("allow", [item["id"]])
        assert out["decided"][0]["decision"] == "allow" and out["still_pending"] == []
        assert "POST" in Recorder.seen  # depois da aprovacao, segue
        assert any("Pedido criado" in x for x in out["tree_added"])  # e a pessoa ve o efeito
    finally:
        await SESSION.close()


async def test_denial_is_recorded_and_the_page_keeps_working(api):
    await SESSION.open(None, form_page(api), allow_mutations="ask")
    try:
        buy = (await SESSION.dossier())["elements"][0]["id"]
        r = await SESSION.act("click", buy)
        out = await SESSION.decide("deny", [r["approvals_pending"][0]["id"]])
        assert out["decided"][0]["decision"] == "deny" and "POST" not in Recorder.seen
        assert any("nao aprovada" in b for b in SESSION.blocked)
        assert any("requisicao(oes) que alterariam dados nao foram enviadas" in g for g in SESSION.coverage_report()["gaps"])
        again = await SESSION.act("hover", buy)  # a pagina segue utilizavel
        assert again["approvals_pending"] == []
    finally:
        await SESSION.close()


async def test_allow_all_turns_approval_off_for_the_rest_of_the_session(api):
    await SESSION.open(None, form_page(api), allow_mutations="ask")
    try:
        buy = (await SESSION.dossier())["elements"][0]["id"]
        await SESSION.act("click", buy)
        out = await SESSION.decide("allow_all")
        assert out["policy_now"] == "allow" and "POST" in Recorder.seen
        Recorder.seen.clear()
        again = await SESSION.act("click", buy)  # agora faz sem perguntar
        assert again["approvals_pending"] == [] and "POST" in Recorder.seen
    finally:
        await SESSION.close()


async def test_closing_with_pending_requests_never_leaves_anything_stuck_or_sent(api):
    await SESSION.open(None, form_page(api), allow_mutations="ask")
    buy = (await SESSION.dossier())["elements"][0]["id"]
    await SESSION.act("click", buy)
    assert len(SESSION.pending) == 1
    await SESSION.close()
    assert SESSION.pending == {} or all(p["future"].done() for p in SESSION.pending.values())
    assert "POST" not in Recorder.seen


async def test_decide_validates_and_the_tool_reports_errors(api):
    import json

    import mcp_server

    with pytest.raises(SessionError):
        await SESSION.decide("allow")  # sem sessao
    await SESSION.open(None, form_page(api), allow_mutations="ask")
    try:
        with pytest.raises(SessionError, match="decision deve ser"):
            await SESSION.decide("talvez")
        with pytest.raises(SessionError, match="nenhum pedido pendente"):
            await SESSION.decide("allow", ["a99"])
        tool = mcp_server.mcp._tool_manager.get_tool("a11y_approve")
        assert "nenhum pedido pendente" in json.loads(await tool.fn(decision="allow", ids="a42"))["error"]
    finally:
        await SESSION.close()
