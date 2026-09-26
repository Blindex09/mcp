"""Firefox de verdade: mesma sessao, medicoes e comparacao entre navegadores, com os limites declarados."""
import json

import pytest

from a11y import audit
from a11y.compare import compare_browsers
from a11y.session import SESSION, SessionError
from tests.test_session import MIXED, SITE


@pytest.fixture()
async def firefox():
    r = await SESSION.open(None, SITE, browser="firefox")
    yield r
    await SESSION.close()


async def test_open_reports_browser_and_its_limits(firefox):
    assert firefox["browser"] == "firefox"
    assert any("sem CDP" in x for x in firefox["limits"])
    assert SESSION.cdp is None and SESSION.browser_name == "firefox"


async def test_chromium_stays_the_precise_default():
    r = await SESSION.open(None, SITE)
    try:
        assert r["browser"] == "chromium" and r["limits"] == [] and SESSION.cdp is not None
    finally:
        await SESSION.close()


async def test_invalid_browser_is_a_usage_error():
    with pytest.raises(SessionError, match="navegador invalido"):
        await SESSION.open(None, SITE, browser="edge")


async def test_firefox_dossier_gives_facts_with_honest_limits(firefox):
    d = await SESSION.dossier()
    assert d["browser"] == "firefox" and any("sem CDP" in x for x in d["limits"])
    field = next(e for e in d["elements"] if e["tag"] == "input")
    assert field["computed"]["role"] == "combobox" and field["computed"]["name"] == "Buscar"
    assert field["computed"]["source"] == "playwright-aria-snapshot"
    assert field["focusable"] is True and field["clickable"] is None  # desconhecido: nao finge saber
    assert field["relations"]["datalist_options"] == 3
    link = next(e for e in d["elements"] if e["tag"] == "a")
    assert link["computed"]["role"] == "link" and link["computed"]["name"] == "Inicio"


async def test_firefox_sees_listener_only_controls_through_the_listener_hook():
    """Firefox nao tem isClickable, mas o gancho em addEventListener registra quem tem listener de acao."""
    await SESSION.open(None, MIXED, browser="firefox")
    try:
        d = await SESSION.dossier()
        by_tag = {e["tag"]: e for e in d["elements"]}
        assert {"button", "x-chip", "div"} <= set(by_tag)
        assert by_tag["div"]["clickable"] is True and by_tag["div"]["focusable"] is False
        assert "click" in by_tag["div"]["behavior_hints"]["click_listeners"]
        assert by_tag["x-chip"]["clickable"] is None  # so focavel: clicavel desconhecido, nao finge saber
    finally:
        await SESSION.close()


async def test_firefox_actions_reach_persona_and_screenshot(firefox):
    d = await SESSION.dossier()
    tog = next(e for e in d["elements"] if e["computed"]["name"] == "Detalhes")
    r = await SESSION.act("click", tog["id"])
    assert "expanded" in " ".join(r["tree_added"])
    assert (await SESSION.screenshot())[:2] == b"\xff\xd8"
    assert (await SESSION.reach(tog["id"]))["reached"] is True


async def test_firefox_focus_style_falls_back_to_real_focus_and_says_so():
    page = """<!doctype html><html lang="pt"><title>f</title><style>#a:focus{outline:3px solid rgb(255,0,0)}</style>
    <body><button id="a">A</button></body></html>"""
    await SESSION.open(None, page, browser="firefox")
    try:
        e = (await SESSION.dossier())["elements"][0]
        fs = await SESSION.focus_style(e["id"])
        assert "foco real" in fs["method"] and "3px" in fs["outline_when_focused"]
        assert fs["changed_on_focus"]["outline-color"][1] == "rgb(255, 0, 0)"
    finally:
        await SESSION.close()


async def test_firefox_mobile_persona_does_not_crash_and_notes_the_gap():
    r = await SESSION.open(None, SITE, persona="mobile_touch", browser="firefox")
    try:
        assert any("is_mobile" in x for x in r["limits"])
        assert SESSION.page.viewport_size["width"] == 390
    finally:
        await SESSION.close()


async def test_audit_tools_take_a_browser():
    html = "<html lang=pt><title>t</title><body><main><img src=x><button>Ok</button></main></body></html>"
    for b in ("chromium", "firefox"):
        assert "image-alt" in {v["id"] for v in (await audit.run_axe(html=html, browser=b))["violations"]}
        assert "button" in await audit.aria_snapshot(html=html, browser=b)
        assert [s["element"]["tag"] for s in await audit.tab_order(html=html, browser=b)] == ["button"]


async def test_compare_browsers_reports_facts_and_what_differs():
    same = "<html lang=pt><title>t</title><body><main><h1>Oi</h1><button>Ok</button></main></body></html>"
    r = await compare_browsers(html=same, browsers=["chromium", "firefox"])
    assert r["browsers"] == ["chromium", "firefox"] and r["reference"] == "chromium"
    diff = r["differences"]["firefox"]
    assert diff["aria_tree"] == "identica" and diff["tab_order"] == "identica"
    assert diff["axe_only_in_reference"] == [] and diff["axe_only_here"] == []
    assert r["per_browser"]["firefox"]["tab_stops"] == ["button:Ok"]
    with pytest.raises(ValueError):
        await compare_browsers(html=same, browsers=["chromium"])
    with pytest.raises(Exception, match="navegador invalido"):
        await compare_browsers(html=same, browsers=["chromium", "edge"])


async def test_tools_expose_browser_and_comparison():
    import mcp_server

    tools = mcp_server.mcp._tool_manager
    out = json.loads(await tools.get_tool("a11y_compare_browsers").fn(
        html="<html lang=pt><title>t</title><body><main><button>Ok</button></main></body></html>"
    ))
    assert out["browsers"] == ["chromium", "firefox"] and "differences" in out
    bad = json.loads(await tools.get_tool("a11y_open").fn(html=SITE, browser="edge"))
    assert "navegador invalido" in bad["error"]
    opened = json.loads(await tools.get_tool("a11y_open").fn(html=SITE, browser="firefox"))
    try:
        assert opened["browser"] == "firefox"
    finally:
        await tools.get_tool("a11y_close").fn()
    status = json.loads(await tools.get_tool("a11y_status").fn())
    assert set(status["browsers"]) == {"chromium", "firefox", "webkit"}


THREE = "<html lang=pt><title>t</title><body><main><button>A</button><button>B</button><button>C</button></main></body></html>"


async def test_tab_order_stops_at_the_end_in_every_browser_even_when_focus_stays_on_the_last_element():
    """Regressao: no Firefox o Tab no ultimo elemento nao sai da pagina; o laco repetia o ultimo 47 vezes."""
    for b in ("chromium", "firefox"):
        stops = await audit.tab_order(html=THREE, browser=b)
        assert [s["element"]["name"] for s in stops] == ["A", "B", "C"], b
    r = await compare_browsers(html=THREE, browsers=["chromium", "firefox"])
    assert r["per_browser"]["chromium"]["tab_stops"] == r["per_browser"]["firefox"]["tab_stops"] == ["button:A", "button:B", "button:C"]
    assert r["differences"]["firefox"]["tab_order"] == "identica"


async def test_reach_reports_end_of_page_when_focus_stops_moving_in_firefox():
    await SESSION.open(None, THREE + "<!-- x -->", browser="firefox")
    try:
        await SESSION.page.evaluate("() => { const d = document.createElement('div'); d.id = 'x'; d.textContent = 'nao focavel'; document.body.append(d); }")
        r = await SESSION.reach("css:#x", max_tabs=30)
        assert r["reached"] is False and r["tab_presses"] < 30
        assert "fim da pagina" in r["reason"] or "saiu" in r["reason"]
    finally:
        await SESSION.close()
