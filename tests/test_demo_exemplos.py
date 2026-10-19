"""Site de exemplos bons e ruins do leitor de tela: o que o MCP mede em cada exemplo tem que bater com o que o site promete."""
import asyncio
import importlib.util
import sys
from pathlib import Path

import pytest

DEMO = Path(__file__).resolve().parent.parent / "demo" / "exemplos-leitor-de-tela"


@pytest.fixture(scope="module")
def site():
    sys.path.insert(0, str(DEMO))
    spec = importlib.util.spec_from_file_location("construir_exemplos", DEMO / "construir.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    medidas = asyncio.run(mod.medir_todos())
    return mod, medidas


def _por_tipo(mod, medidas, slug, tipo):
    cenario = next(c for c in mod.CENARIOS if c["slug"] == slug)
    return [medidas[(slug, i)] for i, ex in enumerate(cenario["exemplos"]) if ex["tipo"] == tipo]


@pytest.mark.slow
def test_every_scenario_has_a_bad_and_a_good_example_and_the_good_ones_pass_axe(site):
    mod, medidas = site
    for c in mod.CENARIOS:
        tipos = {ex["tipo"] for ex in c["exemplos"]}
        assert {"ruim", "bom"} <= tipos, c["slug"]
        for i, ex in enumerate(c["exemplos"]):
            if ex["tipo"] in ("bom", "ok"):
                assert medidas[(c["slug"], i)]["violacoes"] == [], (c["slug"], ex["titulo"])


@pytest.mark.slow
def test_the_bad_example_changes_what_the_browser_hands_to_the_screen_reader(site):
    """O ruim parece igual ao bom, mas a arvore de acessibilidade tem que ser diferente: e' essa a diferenca que o leitor de tela ouve."""
    mod, medidas = site
    for c in mod.CENARIOS:
        if any(ex.get("sonda") for ex in c["exemplos"]):
            continue  # componente interativo: a diferenca e' de comportamento (teclado), medida pelas sondas em test_demo_interativos.py
        bons = {m["arvore"] for m in _por_tipo(mod, medidas, c["slug"], "bom")}
        for ruim in _por_tipo(mod, medidas, c["slug"], "ruim"):
            assert ruim["arvore"] not in bons, c["slug"]


@pytest.mark.slow
def test_a_heading_inside_a_list_item_keeps_the_level_of_its_own_tag(site):
    """Visto ouvindo o site: o leitor diz 'lista com N itens' e depois o titulo do item. Medido: o navegador entrega o nivel do proprio h3
    (aqui 3), e o titulo mora dentro do item da lista. Nunca o nivel 1."""
    mod, medidas = site
    arvore = next(m for m in _por_tipo(mod, medidas, "listas", "ruim") if "[level=3]" in m["arvore"])["arvore"]
    assert arvore.startswith("- list:") and arvore.count("- listitem:") == 2
    assert arvore.count("[level=3]") == 2 and "[level=1]" not in arvore


@pytest.mark.slow
def test_problems_that_axe_cannot_see_say_so_in_the_page(site):
    mod, medidas = site
    texto = mod.texto_do_axe("ruim", [])
    assert "não achou nada" in texto and "árvore de acessibilidade" in texto
    assert mod.texto_do_axe("bom", []).startswith("O axe não achou nenhuma violação")
    imagens_ruim = _por_tipo(mod, medidas, "imagens", "ruim")[0]
    assert any(regra == "image-alt" for regra, _ in imagens_ruim["violacoes"])  # este o axe acha
