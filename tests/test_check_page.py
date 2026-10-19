"""a11y_check_page: a verificacao de comportamento em UMA chamada (para clientes que sobem o servidor de novo a cada chamada)."""
import json

import pytest

from accessibility_mcp import server as mcp_server
from accessibility_mcp.a11y import check_page as cp
from accessibility_mcp.a11y.session import SESSION, SessionError

HEAD = '<!doctype html><html lang="pt"><head><title>Teste</title></head><body><main>'
PAGINA = HEAD + """
<h1>Loja</h1>
<button id="abrir">Abrir</button>
<dialog id="d" aria-labelledby="t"><h2 id="t">Confirmar</h2><button id="x">Fechar</button></dialog>
<div class="fake">Comprar</div>
<ul><li><button>Um</button></li><li><button>Dois</button></li></ul>
<form novalidate><label for="email">E-mail</label><input id="email" type="email" required><button type="submit" id="enviar">Enviar</button></form>
<script>
 document.getElementById('abrir').addEventListener('click', () => document.getElementById('d').showModal());
 document.getElementById('x').addEventListener('click', () => document.getElementById('d').close());
 document.querySelector('form').addEventListener('submit', (e) => e.preventDefault());
 document.querySelector('.fake').addEventListener('click', () => {});
</script></main></body></html>"""


async def _call(**kw):
    return json.loads(await mcp_server.mcp._tool_manager.get_tool("a11y_check_page").fn(**kw))


def test_parse_probes_accepts_a_json_list_and_rejects_the_rest():
    assert cp.parse_probes("") == [] and cp.parse_probes("   ") == []
    assert cp.parse_probes('[{"kind": "dialog", "target": "css:#a"}]') == [{"kind": "dialog", "target": "css:#a", "container": ""}]
    for ruim in ("nao e json", '{"kind": "dialog"}', '[1, 2]', '[{"target": "x"}]'):
        with pytest.raises(SessionError):
            cp.parse_probes(ruim)


async def test_first_call_gives_facts_and_selectors_that_point_back_to_the_same_elements():
    r = await _call(html=PAGINA)
    assert r["opened"]["persona"] == "keyboard" and r["tab_walk"]["stops"] and r["target_size"]["kind"] == "target_size"
    assert r["page_facts"]["h1_count"] == 1 and "not_verified" in r and "leitor de tela real" in r["not_verified"]
    por_texto = {e["text"]: e for e in r["elements"] if e["text"]}
    assert por_texto["Abrir"]["css"] == "#abrir" and por_texto["Abrir"]["role"] == "button" and por_texto["Abrir"]["name"] == "Abrir"
    assert por_texto["Comprar"]["clickable"] is True and por_texto["Comprar"]["focusable"] is False  # o div que so o mouse alcanca
    # seletores sem id: voltam a UM so elemento da pagina
    await SESSION.open(None, PAGINA)
    try:
        for e in r["elements"]:
            assert await SESSION.page.locator(e["css"]).count() == 1, e
    finally:
        await SESSION.close()
    assert SESSION.page is None  # a ferramenta nao deixa sessao aberta


async def test_second_call_runs_the_requested_probes_with_the_selectors_of_the_first():
    r = await _call(html=PAGINA, probes=json.dumps([{"kind": "dialog", "target": "css:#abrir"}, {"kind": "form_errors", "target": "css:#enviar"}]))
    dialogo, erros = r["probes"]
    assert dialogo["kind"] == "dialog" and dialogo["unmet"] == [] and len(dialogo["checks"]) == 8
    assert erros["kind"] == "form_errors" and "campo_invalido_marcado" in erros["unmet"]  # o formulario nao marca o campo nem avisa


async def test_a_failing_probe_is_reported_and_the_session_is_still_closed():
    r = await _call(html=PAGINA, probes=json.dumps([{"kind": "dialog", "target": "css:#nao-existe"}, {"kind": "zzz", "target": "css:#abrir"}, {"kind": "tabs", "target": "css:#abrir"}]))
    assert "nao encontrado" in r["probes"][0]["error"] and "invalida" in r["probes"][1]["error"] and r["probes"][2]["kind"] == "tabs"
    assert SESSION.page is None


async def test_it_refuses_to_take_over_an_open_session_and_does_not_close_it():
    await SESSION.open(None, PAGINA)
    try:
        r = await _call(html=PAGINA)
        assert "ja ha uma sessao aberta" in r["error"]
        assert SESSION.page is not None  # o trabalho de quem abriu a sessao continua la
    finally:
        await SESSION.close()


async def test_bad_input_is_an_error_message_not_a_crash():
    assert "informe exatamente um" in (await _call())["error"]
    assert "probes deve ser" in (await _call(html=PAGINA, probes="lixo"))["error"]
    assert SESSION.page is None


async def test_mutations_are_held_not_sent_on_a_non_local_page(monkeypatch):
    """Pagina que nao e' local: o POST e' retido e a chamada unica o descarta (nada e' enviado); o resultado diz o que foi retido."""
    r = await _call(html=HEAD + '<form method="post" action="https://exemplo.test/enviar"><input name="a" aria-label="a"><button id="b" type="submit">Enviar</button></form></main></body></html>',
                    probes=json.dumps([{"kind": "form_errors", "target": "css:#b"}]))
    assert "approvals_pending_dropped" in r and isinstance(r["approvals_pending_dropped"], list)
    assert SESSION.page is None
