"""Scripts que rodam DENTRO da pagina para coletar FATOS (nunca classificam).

Ficam em arquivos .js reais (a11y/js/) para poderem ser lidos, testados e revisados como JavaScript.
Quem decide "isso e uma combobox / um menu / um acordeao" e o modelo, lendo estes fatos junto com o comportamento
observado. Nada aqui usa palavra-chave para adivinhar categoria; a descoberta do que e interativo vem do proprio
navegador (arvore de acessibilidade e DOMSnapshot), ver session.py.
"""

from pathlib import Path

_JS = Path(__file__).parent / "js"


def _load(name: str) -> str:
    return (_JS / f"{name}.js").read_text(encoding="utf-8").strip()


# Instalado a cada documento novo: registra o texto que entra em regioes vivas (o que um leitor de tela anunciaria).
LIVE_OBSERVER_JS = _load("live_observer")
# Descritor curto do elemento em foco (usado nos relatorios de efeito).
FOCUS_JS = _load("focus")
# Dossie de UM elemento: FATOS (Shadow DOM aberto/fechado e iframes, porque a raiz e o proprio documento do elemento).
DOSSIER_ITEM_JS = _load("dossier")  # function(scope){...} com this = o elemento (via CDP callFunctionOn ou Playwright)
# Linguagem de design real do site (contagens do que ele usa).
DESIGN_JS = _load("design")
# Estresse: reflow em 320 px (WCAG 1.4.10) e texto cortado com espacamento do usuario (WCAG 1.4.12).
REFLOW_JS = _load("reflow")
CLIPPED_JS = _load("clipped")

# Espera adaptativa: a pagina "assentou" quando o DOM fica quieto (sem tempo fixo; so ha um teto).
SETTLE_JS = _load("settle")

# Descoberta sem CDP (Firefox/WebKit): focavel pelo tabIndex do navegador ou cursor:pointer (sinal mais fraco).
DISCOVER_JS = _load("discover")

# Mapa da pagina: fatos de TODO o conteudo (titulos, landmarks, imagens, links, formularios, tabelas, midia, iframes,
# regioes vivas, ordem de leitura, regras :hover), atravessando Shadow DOM aberto.
PAGE_MAP_JS = _load("page_map")

# Gancho instalado antes dos scripts da pagina: quem tem listener de acao (Firefox/WebKit) e acoes delegadas a ancestrais.
LISTENER_HOOK_JS = _load("listener_hook")

# Contador de mutacoes do DOM: sinal de progresso para as esperas adaptativas (a pagina ainda esta trabalhando?).
ACTIVITY_JS = _load("activity")
