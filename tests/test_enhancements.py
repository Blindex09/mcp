"""Testes reais em navegador das melhorias: anotacao de screenshot, diff por pixel no foco, accname_trace, aria-hidden, overlap, ariaNotify e midia."""

import pytest

from accessibility_mcp.a11y.session import SESSION, SessionError

HTML_PAGE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Enhancements Test</title>
<style>
  body { font: 16px/1.4 Arial, sans-serif; color: #111; background: #fff; margin: 20px; }
  button { margin: 12px; }
  #vis:focus-visible { outline: 3px solid #0b57d0; outline-offset: 2px; }
  #invis:focus-visible { outline: 3px solid #ffffff; outline-offset: 2px; }
  .fixed-wrap { height: 22px; width: 220px; margin-top: 12px; }
  .fixed-wrap p { margin: 0; line-height: 1.2; }
  .after-wrap { margin: 0; }
</style>
</head>
<body>
  <button id="vis" type="button">Foco visivel</button>
  <button id="invis" type="button">Foco branco</button>
  <button id="broken" type="button" aria-labelledby="missing-id vis">Com broken id</button>
  <span aria-hidden="true"><a id="hid" href="#oculto">Escondido</a></span>
  <button id="notify-btn" type="button">Notificar</button>
  <img src="x.png">
  <div class="fixed-wrap"><p>Escolha um cha verde hoje</p></div>
  <p class="after-wrap">Linha logo abaixo</p>
  <script>
    if (window.AudioContext) { window.__ctx = new AudioContext(); }
    document.getElementById('notify-btn').addEventListener('click', () => {
      if (typeof Element.prototype.ariaNotify === 'function') {
        document.getElementById('notify-btn').ariaNotify('Salvo via ariaNotify', {priority: 'high'});
      }
    });
  </script>
</body>
</html>"""


async def test_annotated_screenshot_draws_and_cleans_overlay():
    await SESSION.open(None, HTML_PAGE)
    try:
        jpeg = await SESSION.screenshot(annotate=True)
        assert jpeg[:2] == b"\xff\xd8"
        assert SESSION.last_annotation is not None
        assert SESSION.last_annotation["marked"]
        assert await SESSION.page.evaluate("() => document.getElementById('__a11y_annotate_overlay__')") is None
    finally:
        await SESSION.close()

    await SESSION.open(None, HTML_PAGE, persona="screen_reader")
    try:
        with pytest.raises(SessionError, match="nao ve a tela"):
            await SESSION.screenshot(annotate=True)
    finally:
        await SESSION.close()


async def test_focus_style_pixel_diff_distinguishes_visible_from_invisible_outline():
    await SESSION.open(None, HTML_PAGE)
    try:
        vis = await SESSION.focus_style("css:#vis", check_pixels=True)
        invis = await SESSION.focus_style("css:#invis", check_pixels=True)
        assert vis["properties_changed"] > 0 and invis["properties_changed"] > 0
        assert vis["pixel_diff"]["measured"] is True
        assert vis["pixel_diff"]["changed_pixels"] > 0
        assert vis["pixel_diff"]["max_pixel_contrast_ratio"] >= 3.0
        assert invis["pixel_diff"]["measured"] is True
        assert invis["pixel_diff"]["changed_pixels"] == 0
    finally:
        await SESSION.close()


async def test_dossier_accname_trace_and_aria_hidden_focusable():
    await SESSION.open(None, HTML_PAGE)
    try:
        els = {e.get("text"): e for e in (await SESSION.dossier())["elements"]}
        broken = els["Com broken id"]
        assert broken["aria_hidden_focusable"] is False
        lb = next(x for x in broken["accname_trace"] if x["source"] == "aria-labelledby")
        assert lb["missing_ids"] == ["missing-id"]
        assert els["Escondido"]["aria_hidden_focusable"] is True
    finally:
        await SESSION.close()


async def test_text_spacing_overlap_aria_notify_and_media_activity():
    await SESSION.open(None, HTML_PAGE)
    try:
        stress = await SESSION.stress("text_spacing")
        assert stress["overlaps_before"] == 0
        assert stress["newly_overlapping_with_user_spacing"]

        res = await SESSION.act("click", "css:#notify-btn")
        assert any(a.get("role") == "ariaNotify" and a.get("text") == "Salvo via ariaNotify" for a in res["announcements"])

        pmap = await SESSION.page_map()
        assert pmap["main"]["media_activity"]["audio_contexts"] >= 1
    finally:
        await SESSION.close()
