"""Regra: nenhum relogio fixo mata trabalho em andamento; o que demora e' tentado de novo com mais tempo."""
import asyncio

import httpx
import pytest

import llm
from a11y import audit
from a11y.patience import patient, with_patience
from a11y.session import SESSION


async def test_patient_retries_with_growing_timeout_and_only_the_last_failure_surfaces():
    seen: list[float] = []

    async def factory(t):
        seen.append(t)
        if t < 5:
            raise TimeoutError("lento")
        return "ok"

    assert await patient(factory, 1.0) == "ok"
    assert seen == [1.0, 3.0, 9.0]  # 1s, depois 3x, depois 9x: nunca desiste na primeira

    async def never(t):
        raise TimeoutError("sempre lento")

    with pytest.raises(TimeoutError):
        await patient(never, 1.0, attempts=2)


async def test_non_timeout_errors_are_not_retried():
    calls = []

    async def boom(t):
        calls.append(t)
        raise ValueError("erro de verdade")

    with pytest.raises(ValueError):
        await patient(boom, 1.0)
    assert calls == [1.0]  # so timeout ganha mais tempo; erro real sobe na hora


async def test_with_patience_wraps_work_that_takes_no_timeout_argument():
    state = {"n": 0}

    async def work():
        state["n"] += 1
        await asyncio.sleep(0.25)
        return "pronto"

    assert await with_patience(work, 0.1) == "pronto"  # 0.1s estoura, 0.3s basta
    assert state["n"] == 2


async def test_model_call_repeats_the_same_request_with_more_time(monkeypatch):
    timeouts: list[float] = []

    class FakeClient:
        def __init__(self, timeout):
            timeouts.append(timeout)
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers=None, json=None):
            if self.timeout < 300:
                raise httpx.ReadTimeout("modelo lento")
            return httpx.Response(200, json={"ok": True}, request=httpx.Request("POST", url))

    monkeypatch.setattr(llm.httpx, "AsyncClient", FakeClient)
    assert await llm._http_post("http://x/y", {}, {"a": 1}) == {"ok": True}
    assert timeouts == [120.0, 360.0]  # o pedido nao foi abandonado: recebeu mais tempo


async def test_audit_uses_patience_instead_of_a_hard_deadline(monkeypatch):
    calls = []

    async def spy(factory, first, attempts=3):
        calls.append(first)
        return await factory()

    monkeypatch.setattr(audit, "with_patience", spy)

    async def fn(page):
        return "ok"

    html = "<html lang=pt><title>t</title><body><p>oi</p></body></html>"
    assert await audit._with_page(None, html, fn) == "ok"
    assert calls == [audit.TOTAL_TIMEOUT_S]  # a 1a espera e' so o comeco: a paciencia cuida do resto


async def test_slow_action_is_retried_with_more_time_not_failed(monkeypatch):
    from a11y import session as sm

    monkeypatch.setattr(sm, "ACTION_TIMEOUT_MS", 60)
    page = """<!doctype html><html lang="pt"><title>l</title><body><div id="host"></div>
    <script>setTimeout(() => { document.getElementById('host').innerHTML = '<button id="b">Tardio</button>'; }, 250);</script></body></html>"""
    await SESSION.open(None, page)
    try:
        r = await SESSION.act("click", "css:#b")  # o botao so existe daqui a 250ms
        assert r["action"] == "click"
    finally:
        await SESSION.close()


async def test_an_action_with_effect_runs_exactly_once_even_when_the_wait_is_slow(monkeypatch):
    """Regressao: a paciencia repetia o CLIQUE a cada estouro de tempo; repetir uma acao com efeito (comprar, enviar) e' perigoso."""
    from a11y import session as sm

    monkeypatch.setattr(sm, "ACTION_TIMEOUT_MS", 60)
    page = """<!doctype html><html lang="pt"><title>u</title><body><div id="host"></div><div id="n">0</div>
    <script>setTimeout(() => { const b = document.createElement('button'); b.id = 'b'; b.textContent = 'Comprar';
      b.addEventListener('click', () => { const n = document.getElementById('n'); n.textContent = String(+n.textContent + 1); });
      document.getElementById('host').append(b); }, 300);</script></body></html>"""
    await SESSION.open(None, page)
    try:
        await SESSION.act("click", "css:#b")  # o botao so existe daqui a 300ms; a espera paciente cresce ate ele aparecer
        assert await SESSION.page.locator("#n").inner_text() == "1"  # clicou UMA vez
    finally:
        await SESSION.close()


async def test_clicking_a_form_submit_does_not_hang_waiting_for_a_held_navigation():
    """Regressao: click esperava a navegacao terminar; com a requisicao retida esperando aprovacao, travava minutos."""
    import time

    page = """<!doctype html><html lang="pt"><title>f</title><body><form method="post" action="http://api.example.invalid/x"><button>Enviar</button></form></body></html>"""
    await SESSION.open(None, page, allow_mutations="ask")
    try:
        t = time.monotonic()
        r = await SESSION.act("click", "css:button")
        assert time.monotonic() - t < 8  # voltou logo, com o pedido retido
        assert len(r["approvals_pending"]) == 1 and r["approvals_pending"][0]["kind"] == "envio de formulario"
    finally:
        await SESSION.close()
