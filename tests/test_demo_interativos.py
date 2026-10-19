"""Cenarios interativos do site de exemplos: as sondas do MCP precisam separar o exemplo bom do ruim, no Chromium de verdade."""
import asyncio
import importlib.util
import sys
from pathlib import Path

import pytest

DEMO = Path(__file__).resolve().parent.parent / "demo" / "exemplos-leitor-de-tela"
INTERATIVOS = ["dialogo", "acordeao", "abas", "menu", "combobox", "erros-de-formulario", "mudanca-de-tela"]


@pytest.fixture(scope="module")
def site():
    sys.path.insert(0, str(DEMO))
    spec = importlib.util.spec_from_file_location("construir_interativos", DEMO / "construir.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    medidas = asyncio.run(mod.medir_todos())
    return mod, medidas


def _cumpridos(medida):
    return {c["check"]: c["met"] for c in medida["sonda"]}


def _exemplos(mod, medidas, slug):
    cenario = next(c for c in mod.CENARIOS if c["slug"] == slug)
    return [(ex["tipo"], medidas[(slug, i)]) for i, ex in enumerate(cenario["exemplos"])]


@pytest.mark.slow
def test_good_and_ok_interactive_examples_meet_every_check_and_bad_ones_fail_some(site):
    mod, medidas = site
    for slug in INTERATIVOS:
        for tipo, medida in _exemplos(mod, medidas, slug):
            falhas = [k for k, v in _cumpridos(medida).items() if v is False]
            if tipo == "ruim":
                assert falhas, (slug, "o exemplo ruim precisa reprovar alguma verificacao da sonda")
            else:
                assert not falhas, (slug, tipo, falhas)
                assert medida["violacoes"] == [], (slug, medida["violacoes"])


@pytest.mark.slow
def test_native_details_is_not_a_false_negative_and_the_div_trigger_is_caught(site):
    mod, medidas = site
    exemplos = _exemplos(mod, medidas, "acordeao")
    ok = next(m for t, m in exemplos if t == "ok")
    ruim = next(m for t, m in exemplos if t == "ruim")
    assert _cumpridos(ok)["expoe_estado"] is True and _cumpridos(ok)["enter_alterna"] is True
    assert _cumpridos(ruim)["gatilho_recebe_foco"] is False
    assert _cumpridos(ruim)["foco_fica_no_botao_apos_enter"] is False


@pytest.mark.slow
def test_the_bad_form_marks_nothing_but_the_good_one_marks_describes_and_focuses(site):
    mod, medidas = site
    exemplos = _exemplos(mod, medidas, "erros-de-formulario")
    ruim = next(m for t, m in exemplos if t == "ruim")
    bom = next(m for t, m in exemplos if t == "bom")
    assert _cumpridos(ruim)["campo_invalido_marcado"] is False and _cumpridos(ruim)["erro_descrito_no_campo"] is False
    assert all(v is True for v in _cumpridos(bom).values())


def test_interactive_example_ids_are_unique_inside_each_page(site):
    mod, _ = site
    import re

    for slug in INTERATIVOS:
        cenario = next(c for c in mod.CENARIOS if c["slug"] == slug)
        ids = re.findall(r'\bid="([^"]+)"', "".join(ex["html"] for ex in cenario["exemplos"]))
        assert len(ids) == len(set(ids)), (slug, [i for i in ids if ids.count(i) > 1])


@pytest.mark.slow
@pytest.mark.parametrize("pagina", ["menu", "dialogo", "acordeao", "abas", "combobox", "erros-de-formulario"])
async def test_every_live_control_in_the_interactive_pages_meets_the_24px_minimum(pagina):
    from accessibility_mcp.a11y.probes import run_probe
    from accessibility_mcp.a11y.session import SESSION

    html = (DEMO / f"{pagina}.html").read_text(encoding="utf-8")
    css = (DEMO / "estilo.css").read_text(encoding="utf-8")
    html = html.replace('<link rel="stylesheet" href="estilo.css">', f"<style>{css}</style>")
    assert "<style>" in html, "a folha de estilo precisa entrar na pagina medida"
    await SESSION.open(None, html, "mobile_touch")
    try:
        r = await run_probe(SESSION, "target_size")
    finally:
        await SESSION.close()
    assert r["smaller_than_24px"] == 0, r["fail_spacing_exception"]
