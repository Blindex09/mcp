"""Sessao de teste como usuario: dossie, acoes com efeito, personas impostas, design e estresse.

Roda Chromium de verdade contra paginas locais (html=), sem rede.
"""
import json

import pytest

from a11y import audit
from a11y.session import SESSION, SessionError, tree_diff

SITE = """<!doctype html><html lang="pt"><head><title>Loja</title>
<style>
 :root { --brand: #0a5; }
 body { font: 16px/1.5 Georgia, serif; }
 .card { width: 800px; }
 .clip { width: 60px; height: 20px; overflow: hidden; font-size: 14px; }
</style></head><body>
<header><nav aria-label="Principal"><a href="/a">Inicio</a> <a href="/b">Produtos</a></nav></header>
<main>
 <h1>Loja</h1>
 <label for="q">Buscar</label><input id="q" type="text" list="cats">
 <datalist id="cats"><option value="Camisas"><option value="Calcas"><option value="Sapatos"></datalist>
 <button id="tog" aria-expanded="false" aria-controls="panel">Detalhes</button>
 <div id="panel" hidden><p>Conteudo</p></div>
 <button id="say">Avisar</button><div id="live" role="status"></div>
 <div id="menu-trigger" role="button" tabindex="0" aria-haspopup="true" aria-expanded="false" aria-controls="m">Categorias</div>
 <ul id="m" hidden><li><a href="/c1">Camisas</a></li><li><a href="/c2">Calcas</a></li></ul>
 <button tabindex="-1" id="hidden-from-tab">Fora do Tab</button>
 <div class="card">largo demais para 320px</div>
 <div class="clip">texto que vai ser cortado quando o espacamento crescer</div>
 <button id="alert">Alerta</button><button id="pop">Popup</button>
</main>
<script>
 const tog = document.getElementById('tog');
 tog.addEventListener('click', () => { const o = tog.getAttribute('aria-expanded') === 'true';
   tog.setAttribute('aria-expanded', String(!o)); document.getElementById('panel').hidden = o; });
 document.getElementById('say').addEventListener('click', () => { document.getElementById('live').textContent = 'Item adicionado'; });
 document.getElementById('alert').addEventListener('click', () => alert('cuidado'));
 document.getElementById('pop').addEventListener('click', () => window.open('about:blank'));
</script></body></html>"""


@pytest.fixture()
async def site():
    await SESSION.open(None, SITE)
    yield SESSION
    await SESSION.close()


async def _by(session, **match):
    d = await session.dossier()
    for e in d["elements"]:
        if all(str(e.get(k) or e["name_sources"].get(k) or e["text"]) == v or e.get(k) == v for k, v in match.items()):
            return e
    raise AssertionError(f"elemento nao achado: {match}")


async def test_dossier_gives_facts_not_classification(site):
    d = await site.dossier()
    assert d["title"] == "Loja" and d["count"] >= 8
    kinds = {e["id"]: e for e in d["elements"]}
    field = next(e for e in kinds.values() if e["tag"] == "input")
    assert field["editable"] and field["relations"]["datalist_options"] == 3
    assert field["name_sources"]["label"] == "Buscar"
    trigger = next(e for e in kinds.values() if e["role_attr"] == "button" and e["text"] == "Categorias")
    assert trigger["states"]["haspopup"] == "true" and trigger["relations"]["controls"] == "m"
    assert trigger["relations"]["popup_links"] == 2 and trigger["focusable"]
    assert trigger["context"]["landmark"] == "main" and trigger["context"]["heading"] == "Loja"
    assert trigger["style"]["font"] == "Georgia"  # div herda a fonte do site (campos nativos usam a do navegador)
    assert not any("class" in k or "kind" in k and k == "category" for k in field)  # nada classifica


async def test_dossier_scope_and_limits(site):
    d = await site.dossier("nav", 10)
    assert {e["tag"] for e in d["elements"]} == {"a"}
    assert (await site.dossier("#nao-existe"))["error"]
    assert (await site.dossier("", 2))["not_listed_over_limit"] > 0


async def test_act_click_shows_state_change_in_tree(site):
    e = await _by(site, text="Detalhes")
    r = await site.act("click", e["id"])
    added = " ".join(r["tree_added"])
    assert "expanded" in added and "Conteudo" in " ".join(r["tree_added"])
    assert r["focus_after"]["name"] == "Detalhes"


async def test_act_captures_live_announcement(site):
    e = await _by(site, text="Avisar")
    r = await site.act("click", e["id"])
    assert r["announcements"] and r["announcements"][0]["text"] == "Item adicionado"


async def test_act_records_dialogs_and_blocks_popups(site):
    a = await _by(site, text="Alerta")
    b = await _by(site, text="Popup")
    assert (await site.act("click", a["id"]))["js_dialogs"] == ["alert: cuidado"]
    assert (await site.act("click", b["id"]))["popups_blocked"] == ["about:blank"]


async def test_act_rejects_bad_targets_and_actions(site):
    with pytest.raises(SessionError):
        await site.act("click", "javascript:alert(1)")
    with pytest.raises(SessionError):
        await site.act("explodir", "e1")
    with pytest.raises(SessionError):
        await site.act("click", "css:" + "a" * 400)


async def test_keyboard_persona_has_no_mouse_and_screen_reader_cannot_see():
    await SESSION.open(None, SITE, persona="keyboard")
    try:
        e = await _by(SESSION, text="Detalhes")
        for action in ("click", "hover", "focus"):
            with pytest.raises(SessionError, match="nao tem mouse"):
                await SESSION.act(action, e["id"])
        await SESSION.act("press", "", "Tab")  # teclado esta liberado
        assert await SESSION.screenshot()  # teclado ve a tela
    finally:
        await SESSION.close()
    await SESSION.open(None, SITE, persona="screen_reader")
    try:
        with pytest.raises(SessionError, match="nao ve a tela"):
            await SESSION.screenshot()
        assert (await SESSION.observe())["accessibility_tree"]
    finally:
        await SESSION.close()


async def test_keyboard_flow_opens_disclosure_with_enter():
    await SESSION.open(None, SITE, persona="keyboard")
    try:
        target = await _by(SESSION, text="Detalhes")
        r = await SESSION.reach(target["id"])
        assert r["reached"] and r["tab_presses"] >= 3  # 2 links + campo antes
        out = await SESSION.act("press", "", "Enter")
        assert "expanded" in " ".join(out["tree_added"])
    finally:
        await SESSION.close()


async def test_reach_reports_unreachable_element(site):
    e = await _by(site, text="Fora do Tab")
    r = await site.reach(e["id"], max_tabs=40)
    assert r["reached"] is False and r["reason"]


async def test_announce_returns_accessibility_entry(site):
    e = await _by(site, text="Detalhes")
    out = await site.announce(e["id"])
    assert "button" in out["accessibility_tree"] and "Detalhes" in out["accessibility_tree"]


async def test_personas_emulate_the_browser():
    await SESSION.open(None, SITE, persona="low_vision")
    try:
        assert SESSION.page.viewport_size["width"] == 320
    finally:
        await SESSION.close()
    await SESSION.open(None, SITE, persona="mobile_touch")
    try:
        assert await SESSION.page.evaluate("() => navigator.maxTouchPoints > 0") is True
    finally:
        await SESSION.close()
    await SESSION.open(None, SITE, persona="reduced_motion")
    try:
        assert await SESSION.page.evaluate("() => matchMedia('(prefers-reduced-motion: reduce)').matches")
    finally:
        await SESSION.close()


async def test_design_tokens_measure_what_the_site_uses(site):
    t = await site.design_tokens()
    assert t["css_variables"].get("--brand") == "#0a5"
    assert t["font_families"][0]["value"] == "Georgia"
    assert t["base"]["body_size"] == "16px" and t["type_styles"]


async def test_preview_css_is_temporary_and_safe(site):
    e = await _by(site, text="Detalhes")
    r = await site.preview_css(e["id"], "font-size: 22px; letter-spacing: 0.05em")
    assert r["after"]["font-size"] == "22px" and r["before"]["font-size"] != "22px"
    assert (await site.preview_css(e["id"], "", revert=True))["reverted"]
    assert await site.page.evaluate("id => getComputedStyle(document.querySelector(`[data-a11y-id=${id}]`)).fontSize", e["id"]) != "22px"
    for bad in ("background: url(http://x/y.png)", "x: y; @import 'a'", "color: red<script>", "font size: 1px"):
        with pytest.raises(SessionError):
            await site.preview_css(e["id"], bad)


async def test_stress_reflow_and_text_spacing(site):
    r = await site.stress("reflow_320")
    assert r["horizontal_scroll"] and any("largo demais" in o["text"] for o in r["overflowing_elements"])
    assert site.page.viewport_size["width"] != 320  # restaurou
    s = await site.stress("text_spacing")
    assert s["newly_clipped_with_user_spacing"] or s["clipped_before"] >= 1
    with pytest.raises(SessionError):
        await site.stress("outro")


async def test_screenshot_is_a_jpeg(site):
    data = await site.screenshot()
    assert data[:2] == b"\xff\xd8"
    e = await _by(site, text="Detalhes")
    assert (await site.screenshot(e["id"]))[:2] == b"\xff\xd8"


async def test_open_validates_and_replaces_previous_session():
    with pytest.raises(audit.ValueError if hasattr(audit, "ValueError") else ValueError):
        await SESSION.open("file:///c:/windows/win.ini", None)
    with pytest.raises(SessionError):
        await SESSION.open(None, None)
    with pytest.raises(SessionError, match="persona invalida"):
        await SESSION.open(None, SITE, persona="ninja")
    await SESSION.open(None, SITE)
    first = SESSION.page
    await SESSION.open(None, SITE)
    assert SESSION.page is not first
    assert await SESSION.close() is True and await SESSION.close() is False
    with pytest.raises(SessionError, match="nenhuma sessao"):
        await SESSION.observe()


def test_tree_diff_is_exact_about_what_changed():
    d = tree_diff(['- button "A"', '- text "x"'], ['- button "A" [expanded]', '- text "x"'])
    assert d == {"removed": ['- button "A"'], "added": ['- button "A" [expanded]']}


async def test_mcp_tools_registered_and_return_json():
    import mcp_server

    names = {t.name for t in await mcp_server.mcp.list_tools()}
    assert {"a11y_open", "a11y_close", "a11y_dossier", "a11y_observe", "a11y_act", "a11y_reach",
            "a11y_announce", "a11y_screenshot", "a11y_design_tokens", "a11y_preview_css", "a11y_stress"} <= names
    tool = mcp_server.mcp._tool_manager.get_tool
    out = json.loads(await tool("a11y_dossier").fn())
    assert "nenhuma sessao" in out["error"]
    opened = json.loads(await tool("a11y_open").fn(html=SITE, persona="keyboard"))
    try:
        assert opened["persona"] == "keyboard"
        refused = json.loads(await tool("a11y_act").fn(action="click", target="e1"))
        assert "nao tem mouse" in refused["error"]
    finally:
        await tool("a11y_close").fn()
