"""Trava o caso central: 'axe verde' NAO significa acessivel (site de demonstracao demo/loja)."""
import sys
from pathlib import Path

import pytest

DEMO = Path(__file__).resolve().parent.parent / "demo" / "loja"
sys.path.insert(0, str(DEMO))

import verificar as v

from a11y import audit
from a11y.session import SESSION


@pytest.fixture(scope="module")
def base_url():
    srv, port = v.serve()
    yield f"http://127.0.0.1:{port}"
    srv.shutdown()


async def test_axe_finds_the_generic_problems_only_in_v1(base_url):
    v1 = await audit.run_axe(url=f"{base_url}/v1-original/index.html")
    assert {x["id"] for x in v1["violations"]} == {"button-name", "image-alt", "color-contrast", "html-has-lang"}
    for ver in ("v2-axe-verde", "v3-corrigido"):
        assert (await audit.run_axe(url=f"{base_url}/{ver}/index.html"))["violations"] == []


async def test_green_axe_but_a_keyboard_user_cannot_buy_in_v2_and_can_in_v3(base_url):
    results = {}
    for ver in ("v2-axe-verde", "v3-corrigido"):
        await SESSION.open(f"{base_url}/{ver}/index.html", None, "keyboard")  # persona sem mouse, imposta pelo servidor
        try:
            ok, _ = await v.tab_until(lambda f: f["text"].startswith("Comprar"))
            if ok:
                await SESSION.act("press", "", "Enter")
            results[ver] = (ok, await SESSION.page.evaluate("() => document.getElementById('toast').textContent"))
        finally:
            await SESSION.close()
    assert results["v2-axe-verde"] == (False, "")  # botao e' um <div>: nao recebe foco
    assert results["v3-corrigido"][0] is True and "Adicionado ao carrinho" in results["v3-corrigido"][1]


async def test_dossier_reports_mouse_only_controls_and_the_computed_role(base_url):
    async def facts(ver):
        await SESSION.open(f"{base_url}/{ver}/index.html", None, "default")
        try:
            els = (await SESSION.dossier("", 100))["elements"]
            mouse_only = [e for e in els if e["clickable"] and not e["focusable"] and (e["computed"] or {}).get("role") in ("generic", None)]
            cat = next(e for e in els if e["tag"] == "input" and (e["computed"] or {}).get("name") == "Categoria")
            return len(mouse_only), cat["computed"]["role"]
        finally:
            await SESSION.close()

    assert await facts("v2-axe-verde") == (5, "textbox")
    assert await facts("v3-corrigido") == (0, "combobox")


async def test_purchase_notice_is_silent_in_v2_and_announced_in_v3(base_url):
    async def announced(ver):
        await SESSION.open(f"{base_url}/{ver}/index.html", None, "default")
        try:
            els = (await SESSION.dossier("", 100))["elements"]
            buy = next(e for e in els if (e["text"] or "").startswith("Comprar"))
            return [a["text"] for a in (await SESSION.act("click", buy["id"]))["announcements"]]
        finally:
            await SESSION.close()

    assert await announced("v2-axe-verde") == []
    assert await announced("v3-corrigido") == ["Adicionado ao carrinho: Sencha Premium"]
