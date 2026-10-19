"""Site de pesquisas do leitor de tela: a pagina inicial segue o que o proprio MCP ensina (e mede)."""
import importlib.util
from pathlib import Path

from accessibility_mcp.a11y.session import SESSION

DEMO = Path(__file__).resolve().parent.parent / "demo" / "leitor-de-tela"


def _gerador():
    spec = importlib.util.spec_from_file_location("construir_leitor", DEMO / "construir.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


async def test_home_cards_are_a_list_of_links_not_a_list_of_headings():
    """Regressao real (dono ouvindo o site no NVDA): os cartoes eram li com h2 dentro, e o leitor falava 'lista com 6 itens' e depois um
    titulo por cartao: a mesma informacao duas vezes, e a lista de titulos da pagina cheia de rotulos de cartao. O guia aria-rules-dos-and-donts
    do MCP manda usar titulo na estrutura do documento e nao em titulo visual de cartao. Medido com o proprio mapa da pagina do MCP."""
    await SESSION.open(None, _gerador().pagina_inicial())
    try:
        mapa = (await SESSION.page_map())["main"]
        cartoes = next(d for d in mapa["lists"]["details"] if d["items"] == 6)
        assert cartoes["items_with_heading"] == 0 and mapa["lists"]["lists_with_headings_in_items"] == 0
        assert [h["level"] for h in mapa["headings"]["outline"]] == [1]  # so o h1: nenhum titulo de cartao no mapa da pagina
    finally:
        await SESSION.close()
