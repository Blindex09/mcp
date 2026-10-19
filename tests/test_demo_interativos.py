"""Cenarios interativos do site de exemplos: as sondas do MCP precisam separar o exemplo bom do ruim, no Chromium de verdade."""
import asyncio
import importlib.util
import re
import sys
from pathlib import Path

import pytest

DEMO = Path(__file__).resolve().parent.parent / "demo" / "exemplos-leitor-de-tela"
INTERATIVOS = ["dialogo", "acordeao", "abas", "menu", "combobox", "erros-de-formulario", "mudanca-de-tela"]
PILHAS = ["pilha-react", "pilha-vue", "pilha-svelte", "pilha-angular"]
COMPONENTES = ["ajax", "carrossel", "dica", "lista-de-opcoes", "arvore", "tabela-ordenavel", "web-components"]
PAGINAS_VIVAS = ["css", "chat-ia", *COMPONENTES]


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
    return {c["check"]: c["met"] for c in medida.get("sonda", [])}


def _exemplos(mod, medidas, slug):
    cenario = next(c for c in mod.CENARIOS if c["slug"] == slug)
    return [(ex["tipo"], medidas[(slug, i)]) for i, ex in enumerate(cenario["exemplos"])]


@pytest.mark.slow
def test_good_and_ok_interactive_examples_meet_every_check_and_bad_ones_fail_some(site):
    mod, medidas = site
    for slug in INTERATIVOS + PILHAS + COMPONENTES:
        for tipo, medida in _exemplos(mod, medidas, slug):
            if "sonda" not in medida:
                continue  # sem sonda de contrato (caixa de selecao personalizada): medida pela arvore, em outro teste
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


@pytest.mark.slow
@pytest.mark.parametrize("pilha", ["react", "vue", "svelte", "angular"])
def test_each_framework_keeps_the_same_contract_for_the_same_five_components(site, pilha):
    """O mesmo defeito nas quatro pilhas, medido no navegador: regiao viva nascida com o texto, erro sem campo marcado, tela que muda calada."""
    mod, medidas = site
    por_tema = {}
    cenario = next(c for c in mod.CENARIOS if c["slug"] == f"pilha-{pilha}")
    for i, ex in enumerate(cenario["exemplos"]):
        por_tema[ex["chave"]] = _cumpridos(medidas[("pilha-" + pilha, i)])
    assert por_tema["status-ruim"]["regiao_existia_antes"] is False and por_tema["status-bom"]["regiao_existia_antes"] is True
    assert por_tema["erro-ruim"]["campo_invalido_marcado"] is False and por_tema["erro-bom"]["foco_vai_ao_erro"] is True
    assert por_tema["rota-ruim"]["titulo_muda"] is False and por_tema["rota-bom"]["titulo_muda"] is True
    assert por_tema["dialogo-ruim"]["abre_com_teclado"] is False and por_tema["dialogo-bom"]["foco_volta_ao_gatilho"] is True
    assert por_tema["acordeao-ruim"]["gatilho_recebe_foco"] is False and por_tema["acordeao-bom"]["enter_alterna"] is True


@pytest.mark.slow
def test_the_svelte_compiler_itself_warns_about_the_click_only_div_and_not_about_the_button(site):
    mod, medidas = site
    cenario = next(c for c in mod.CENARIOS if c["slug"] == "pilha-svelte")
    avisos = {ex["chave"]: medidas[("pilha-svelte", i)]["avisos_compilador"] for i, ex in enumerate(cenario["exemplos"])}
    assert any(a.startswith("a11y_click_events_have_key_events") for a in avisos["acordeao-ruim"])
    assert avisos["acordeao-bom"] == []


def test_interactive_example_ids_are_unique_inside_each_page(site):
    mod, _ = site
    import re

    for slug in INTERATIVOS + COMPONENTES:
        cenario = next(c for c in mod.CENARIOS if c["slug"] == slug)
        ids = re.findall(r'\bid="([^"]+)"', "".join(ex["html"] for ex in cenario["exemplos"]))
        assert len(ids) == len(set(ids)), (slug, [i for i in ids if ids.count(i) > 1])


@pytest.mark.slow
@pytest.mark.parametrize("pagina", ["menu", "dialogo", "acordeao", "abas", "combobox", "erros-de-formulario", *PILHAS, *PAGINAS_VIVAS])
async def test_every_live_control_in_the_interactive_pages_meets_the_24px_minimum(pagina):
    from accessibility_mcp.a11y.probes import run_probe
    from accessibility_mcp.a11y.session import SESSION

    html = (DEMO / f"{pagina}.html").read_text(encoding="utf-8")
    css = (DEMO / "estilo.css").read_text(encoding="utf-8")
    html = html.replace('<link rel="stylesheet" href="estilo.css">', f"<style>{css}</style>")
    for script in re.findall(r'<script src="(app-[a-z]+\.js)"></script>', html):
        html = html.replace(f'<script src="{script}"></script>', "<script>" + (DEMO / script).read_text(encoding="utf-8").replace(r"<\/script", r"<\/script") + "</script>")
    assert "<style>" in html, "a folha de estilo precisa entrar na pagina medida"
    await SESSION.open(None, html, "mobile_touch")
    try:
        r = await run_probe(SESSION, "target_size")
    finally:
        await SESSION.close()
    assert r["smaller_than_24px"] == 0, r["fail_spacing_exception"]


@pytest.mark.slow
def test_css_pairs_are_separated_by_what_the_mcp_measured(site):
    mod, medidas = site
    cenario = next(c for c in mod.CENARIOS if c["slug"] == "css")
    por_titulo = {ex["titulo"]: (ex, medidas[("css", i)]) for i, ex in enumerate(cenario["exemplos"])}
    assert "Contorno quando focado: none" in por_titulo["Foco do teclado removido"][1]["extra"]
    assert "Contorno quando focado: none" not in por_titulo["Foco visível"][1]["extra"] and "outline-style" in por_titulo["Foco visível"][1]["extra"]
    assert "alcança: 1 " in por_titulo["Submenu que só abre com o mouse (:hover)"][1]["extra"]
    assert "alcança: 3 " in por_titulo["Submenu que abre também com o foco"][1]["extra"]
    assert "ficar cortados" in por_titulo["Altura fixa que corta o texto com o espaçamento do usuário"][1]["extra"]
    assert "nada passou a ficar cortado" in por_titulo["Altura que cresce com o texto"][1]["extra"]
    assert "gira-ruim" in por_titulo["Animação que ignora a preferência por menos movimento"][1]["extra"]
    assert "é: none" in por_titulo["Animação que respeita a preferência"][1]["extra"]
    assert any(regra == "color-contrast" for regra, _ in por_titulo["Texto cinza claro sobre branco"][1]["violacoes"])
    assert por_titulo["Texto com contraste suficiente"][1]["violacoes"] == []
    assert "(abre em nova janela)" not in por_titulo["Texto para leitor de tela escondido com display:none"][1]["arvore"]
    assert "(abre em nova janela)" in por_titulo["Texto só para leitor de tela"][1]["arvore"]


@pytest.mark.slow
def test_the_list_without_marker_is_declared_uncertain_because_webkit_here_still_says_list(site):
    """Achado honesto: o Safari com VoiceOver ja perdeu a lista com list-style:none, mas o WebKit do Playwright nao reproduz. O site nao chama de ruim o que nao mediu."""
    mod, medidas = site
    cenario = next(c for c in mod.CENARIOS if c["slug"] == "css")
    i = next(n for n, ex in enumerate(cenario["exemplos"]) if ex["tipo"] == "incerto")
    assert "são iguais" in medidas[("css", i)]["extra"] and "list:" in medidas[("css", i)]["extra"]


@pytest.mark.slow
def test_the_custom_checkbox_gets_its_role_only_with_element_internals(site):
    mod, medidas = site
    cenario = next(c for c in mod.CENARIOS if c["slug"] == "web-components")
    arvores = {ex["titulo"]: medidas[("web-components", i)]["arvore"] for i, ex in enumerate(cenario["exemplos"])}
    assert "checkbox" not in arvores["Caixa de seleção personalizada sem papel nem teclado"]
    assert "checkbox" in arvores["Caixa de seleção personalizada com ElementInternals"]


@pytest.mark.slow
def test_streaming_answer_in_an_assertive_region_floods_announcements_and_the_good_one_says_once(site):
    _, medidas = site
    ruim, bom = (medidas[("chat-ia", i)]["extra"] for i in (0, 1))
    assert int(ruim.split("depois de apertar Enter no botão: ")[1].split(" ")[0]) >= 5
    assert "botão: 1 " in bom and "Resposta pronta" in bom


def test_mobile_examples_say_they_were_not_run_and_carry_code(site):
    mod, _ = site
    for slug in ("android", "ios"):
        cenario = next(c for c in mod.CENARIOS if c["slug"] == slug)
        assert {ex["tipo"] for ex in cenario["exemplos"]} == {"ruim", "bom"}
        for ex in cenario["exemplos"]:
            assert ex["nao_executado"].startswith("Não executado aqui") and ex["codigo"].strip()
            assert "Não executado aqui" in mod.bloco_nao_executado(ex, 0)
