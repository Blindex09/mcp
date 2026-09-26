"""Tempo adaptativo: leva o tempo que for enquanto ha progresso; nada de prazo fixo que interrompa trabalho em andamento."""
import http.server
import threading
import time
from typing import ClassVar

import pytest
from playwright.async_api import TimeoutError as PlaywrightTimeout

from a11y import session as sm
from a11y.session import SESSION


class Slow(http.server.BaseHTTPRequestHandler):
    hung: ClassVar[list[threading.Event]] = []

    def do_GET(self):
        if self.path == "/lento":
            time.sleep(4)  # servidor lento de verdade: mais que os 3 s que antes cortavam a espera
            self._send(b"resposta tardia")
        elif self.path == "/pendurado":
            ev = threading.Event()
            Slow.hung.append(ev)
            ev.wait(30)  # nunca responde durante o teste (long-poll / travado)
        elif self.path == "/sse":
            self.send_response(200)
            self.send_header("content-type", "text/event-stream")
            self.end_headers()
            for _ in range(200):
                try:
                    self.wfile.write(b"data: ping\n\n")
                    self.wfile.flush()
                except OSError:
                    return
                time.sleep(0.1)
        else:
            self._send(b"ok")

    def _send(self, body):
        self.send_response(200)
        self.send_header("content-type", "text/plain")
        self.send_header("access-control-allow-origin", "*")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args, **kwargs):
        return


@pytest.fixture()
def slow():
    Slow.hung = []
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Slow)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    for ev in Slow.hung:
        ev.set()
    srv.shutdown()


def page(url: str, path: str) -> str:
    return f"""<!doctype html><html lang="pt"><title>t</title><body><button id="go">Ir</button><div id="out"></div>
    <script>document.getElementById('go').addEventListener('click', () => {{
      fetch('{url}{path}').then(r => r.text()).then(t => {{ document.getElementById('out').textContent = t; }}); }});</script></body></html>"""


async def test_a_slow_server_response_is_waited_for_beyond_the_old_fixed_cap(slow):
    await SESSION.open(None, page(slow, "/lento"))
    try:
        t = time.monotonic()
        r = await SESSION.act("click", "css:#go")
        took = time.monotonic() - t
        assert took >= 3.9  # esperou a resposta do servidor lento (antes desistia aos 3 s)
        assert any("resposta tardia" in x for x in r["tree_added"])
        assert SESSION._req_durations and max(SESSION._req_durations) >= 3.9  # e aprendeu o ritmo do site
    finally:
        await SESSION.close()


async def test_requests_that_never_end_by_nature_do_not_hold_the_page_forever(slow, monkeypatch):
    monkeypatch.setattr(sm, "LONG_POLL_FLOOR_S", 0.4)
    await SESSION.open(None, page(slow, "/pendurado"))
    try:
        t = time.monotonic()
        await SESSION.act("click", "css:#go")  # a requisicao nunca responde: tratada como long-poll depois de um tempo, sem travar
        assert time.monotonic() - t < 8
    finally:
        await SESSION.close()


async def test_event_streams_are_not_counted_as_work_in_progress(slow):
    sse = f"""<!doctype html><html lang="pt"><title>s</title><body><button id="go">Ir</button>
    <script>document.getElementById('go').addEventListener('click', () => new EventSource('{slow}/sse'));</script></body></html>"""
    await SESSION.open(None, sse)
    try:
        t = time.monotonic()
        await SESSION.act("click", "css:#go")
        assert time.monotonic() - t < 6  # SSE nunca termina: nao conta como 'a pagina ainda esta trabalhando'
    finally:
        await SESSION.close()


async def test_waiting_for_an_element_continues_while_the_page_keeps_progressing():
    """O elemento so aparece depois de 4,5 s; a pagina muda o DOM o tempo todo: espera o tempo que for (nada de prazo fixo)."""
    html = """<!doctype html><html lang="pt"><title>p</title><body><div id="ticker"></div>
    <script>let n = 0; const iv = setInterval(() => { document.getElementById('ticker').textContent = String(++n); }, 250);
    setTimeout(() => { clearInterval(iv); const b = document.createElement('button'); b.id = 'tardio'; b.textContent = 'Pronto';
      b.addEventListener('click', () => { document.title = 'clicado'; }); document.body.append(b); }, 4500);</script></body></html>"""
    await SESSION.open(None, html)
    try:
        t = time.monotonic()
        await SESSION.act("click", "css:#tardio")
        assert time.monotonic() - t >= 4.4 and await SESSION.page.title() == "clicado"
    finally:
        await SESSION.close()


async def test_waiting_gives_up_quickly_when_the_page_is_quiet_and_the_element_never_comes():
    await SESSION.open(None, "<html lang=pt><title>q</title><body><p>parada</p></body></html>")
    try:
        t = time.monotonic()
        with pytest.raises(PlaywrightTimeout):
            await SESSION.act("click", "css:#nao-existe")
        assert time.monotonic() - t < 9  # pagina parada: nao ha o que esperar (parada por falta de progresso, nao por relogio)
    finally:
        await SESSION.close()


def test_idle_limit_grows_with_the_pace_of_the_conversation():
    fresh = sm.Session()
    assert fresh.idle_limit_s() == sm.IDLE_MIN_S
    fresh._max_gap = 3600  # a pessoa demora uma hora entre chamadas
    assert fresh.idle_limit_s() == 36000  # 10x o maior intervalo: nunca fecha no meio de uma conversa lenta


async def test_the_conversation_pace_is_learned_from_the_gaps_between_calls():
    await SESSION.open(None, "<html lang=pt><title>r</title><body>x</body></html>")
    try:
        SESSION.last_used -= 120  # a pessoa ficou 2 minutos sem chamar
        await SESSION.observe()
        assert SESSION._max_gap >= 120 and SESSION.idle_limit_s() == max(sm.IDLE_MIN_S, 10 * SESSION._max_gap)
    finally:
        await SESSION.close()


async def test_the_site_pace_learned_in_one_session_does_not_leak_into_the_next(slow):
    """Regressao: as duracoes de um site (4 s) esticavam o limite de long-poll do site seguinte."""
    await SESSION.open(None, page(slow, "/lento"))
    try:
        await SESSION.act("click", "css:#go")
        assert max(SESSION._req_durations) >= 3.9
    finally:
        await SESSION.close()
    await SESSION.open(None, "<html lang=pt><title>novo</title><body>x</body></html>")
    try:
        assert SESSION._req_durations == [] and SESSION._req_count == 0
    finally:
        await SESSION.close()
