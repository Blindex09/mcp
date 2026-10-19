"""Gera o site estatico "Leitor de tela: o que a pessoa ouve" a partir das 6 pesquisas do MCP.

As pesquisas sao texto puro (titulos, paragrafos e listas simples). O HTML segue o que o proprio MCP recomenda
(a11y_get_example html-semantic-foundation e css-accessibility): link de pular, landmarks nomeados, um so h1,
foco visivel, tema claro e escuro, movimento reduzido e reflow. Os cartoes da pagina inicial sao uma lista de links com
descricao, sem titulo dentro do item: titulo de cartao visual nao e titulo de documento (aria-rules-dos-and-donts do MCP).
Secao sem nome nao vira landmark: os titulos
dao a estrutura, e landmarks demais atrapalham quem navega por eles (page-structure-review do MCP).

Uso:  python demo/leitor-de-tela/construir.py     (escreve os .html e o estilo.css nesta pasta)
"""

from __future__ import annotations

import html
import re
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
REFS = HERE.parent.parent / "accessibility_mcp" / "a11y" / "content" / "references"

# (arquivo da pesquisa, nome curto no menu, o que a pessoa encontra nela)
PESQUISAS = [
    ("screen-reader-html-elements", "Elementos HTML",
     "O que o leitor de tela fala para cada elemento HTML (títulos, listas, links, botões, campos, tabelas, imagens, áreas da página e diálogos), acessível e não acessível."),
    ("screen-reader-structure-focus-navigation", "Estrutura, foco e navegação",
     "Ordem de foco, hierarquia de títulos, listas, tabelas e grades, e as teclas de navegação por tipo e por tabela no NVDA, no JAWS e no VoiceOver."),
    ("screen-reader-aria-patterns", "ARIA e padrões",
     "Como NVDA, JAWS, VoiceOver e TalkBack tratam ARIA e os padrões de componentes (diálogo, abas, acordeão, menu, combobox, tabela e grade), e os mitos comuns."),
    ("screen-reader-css-and-modes", "CSS e modos de leitura",
     "O que o CSS esconde ou muda na árvore de acessibilidade, e os modos de leitura e de foco de cada leitor de tela, com as teclas."),
    ("screen-reader-actions-keys-events", "Ações, teclas e eventos",
     "O que o leitor de tela faz e fala em cada ação, tecla e evento: clique, teclado, foco, estados que mudam, atributos HTML e conteúdo carregado depois."),
    ("screen-reader-dynamic-js-react", "JavaScript dinâmico e React",
     "Conteúdo que muda sem recarregar a página: regiões vivas, foco depois da mudança, rotas, formulários e validação, React e portais."),
]
NOME_DO_SITE = "Leitor de tela: o que a pessoa ouve"

ESTILO = """\
/* Segue o css-accessibility do MCP: foco visivel, movimento reduzido, tema claro/escuro, contraste, reflow e alvos de toque. */
:root {
  color-scheme: light dark;
  --texto: light-dark(#1a1a1a, #f2f2f2);
  --fundo: light-dark(#ffffff, #121212);
  --suave: light-dark(#4a4a4a, #c4c4c4);
  --link: light-dark(#0a4aad, #8ab4f8);
  --borda: light-dark(#8a8a8a, #8a8a8a);
  --destaque: light-dark(#eef3fb, #1c2230);
}
* { box-sizing: border-box; }
html { font-size: 100%; }
body {
  margin: 0;
  color: var(--texto);
  background: var(--fundo);
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
  font-size: 1.125rem;
  line-height: 1.6;
  overflow-wrap: anywhere;
}
a { color: var(--link); text-underline-offset: 0.15em; }
:focus-visible { outline: 3px solid var(--link); outline-offset: 2px; border-radius: 3px; }
:focus:not(:focus-visible) { outline: none; }
main:focus { outline: none; }

.pular {
  position: absolute; left: -9999px; top: 0.5rem; z-index: 10;
  padding: 0.75rem 1rem; background: var(--link); color: var(--fundo); border-radius: 4px;
}
.pular:focus { left: 0.5rem; }

.coluna { max-width: 46rem; margin-inline: auto; padding-inline: 1rem; }
header { border-bottom: 1px solid var(--borda); padding-block: 0.75rem; }
.marca { font-weight: 700; margin: 0 0 0.25rem; }
nav ul { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 0.25rem 0.5rem; }
nav a { display: inline-block; min-height: 44px; min-width: 44px; padding: 0.55rem 0.5rem; }
nav a[aria-current="page"] { font-weight: 700; text-decoration: none; border-bottom: 3px solid currentColor; }
main { padding-block: 1.5rem 3rem; }
h1 { font-size: 1.9rem; line-height: 1.25; margin: 0 0 1rem; }
h2 { font-size: 1.4rem; line-height: 1.3; margin: 2.25rem 0 0.75rem; }
p, li { max-width: 70ch; }
li { margin-block: 0.4rem; }
.origem { color: var(--suave); border-left: 4px solid var(--borda); padding-left: 1rem; }
.neste-texto { background: var(--destaque); border: 1px solid var(--borda); border-radius: 6px; padding: 0.5rem 1rem 0.75rem; margin-block: 1.5rem; }
.neste-texto h2 { font-size: 1.1rem; margin: 0.5rem 0 0.25rem; }
.neste-texto ol { margin: 0; padding-left: 1.4rem; }
.neste-texto a { min-height: 24px; display: inline-block; padding-block: 0.15rem; }
.cartoes { list-style: none; padding: 0; margin: 1.5rem 0; display: grid; gap: 1rem; }
.cartoes li { max-width: none; margin: 0; border: 1px solid var(--borda); border-radius: 8px; padding: 0.25rem 1rem 1rem; }
.cartoes a { display: inline-block; min-height: 44px; margin: 0.35rem 0 0; padding-block: 0.4rem; font-size: 1.2rem; font-weight: 700; }
.cartoes p { margin: 0; }
.entre { display: flex; flex-wrap: wrap; gap: 1rem; justify-content: space-between; margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--borda); }
.entre a { display: inline-block; min-height: 44px; padding: 0.55rem 0; }
footer { border-top: 1px solid var(--borda); padding-block: 1rem 2rem; color: var(--suave); font-size: 1rem; }

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; scroll-behavior: auto !important; }
}
@media (prefers-contrast: more) {
  :root { --texto: light-dark(#000000, #ffffff); --suave: light-dark(#222222, #eeeeee); }
  a { text-decoration-thickness: 2px; }
}
@media (forced-colors: active) {
  nav a[aria-current="page"] { border-bottom-color: Highlight; }
  .neste-texto, .cartoes li { border-color: CanvasText; }
}
"""


def slug(texto: str) -> str:
    base = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", base).strip("-") or "secao"


def ler_pesquisa(arquivo: str) -> list[tuple[str, object]]:
    """Titulos (#, ##), paragrafos e listas simples (- ou 1.) viram blocos; o resto nao existe nessas pesquisas."""
    texto = (REFS / f"{arquivo}.md").read_text(encoding="utf-8")
    blocos: list[tuple[str, object]] = []
    paragrafo: list[str] = []
    lista: list[str] = []
    tipo_lista = ""

    def fechar_paragrafo() -> None:
        if paragrafo:
            blocos.append(("p", " ".join(paragrafo)))
            paragrafo.clear()

    def fechar_lista() -> None:
        nonlocal tipo_lista
        if lista:
            blocos.append((tipo_lista, list(lista)))
            lista.clear()
            tipo_lista = ""

    for linha in texto.splitlines():
        s = linha.strip()
        titulo = re.match(r"^(#{1,6})\s+(.*)$", s)
        item = re.match(r"^(?:[-*]|(\d+)[.)])\s+(.*)$", s)
        if not s:
            fechar_paragrafo()
            fechar_lista()
        elif titulo:
            fechar_paragrafo()
            fechar_lista()
            blocos.append((f"h{len(titulo.group(1))}", titulo.group(2)))
        elif item:
            fechar_paragrafo()
            novo = "ol" if item.group(1) else "ul"
            if tipo_lista and tipo_lista != novo:
                fechar_lista()
            tipo_lista = novo
            lista.append(item.group(2))
        else:
            fechar_lista()
            paragrafo.append(s)
    fechar_paragrafo()
    fechar_lista()
    return blocos


def esc(texto: str) -> str:
    return html.escape(texto, quote=True)


def cabecalho(titulo_pagina: str, atual: str | None) -> str:
    itens = ['<li><a href="index.html"' + (' aria-current="page"' if atual is None else "") + ">Início</a></li>"]
    for arquivo, curto, _ in PESQUISAS:
        corrente = ' aria-current="page"' if arquivo == atual else ""
        itens.append(f'<li><a href="{arquivo}.html"{corrente}>{esc(curto)}</a></li>')
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(titulo_pagina)}</title>
<link rel="stylesheet" href="estilo.css">
</head>
<body>
<a class="pular" href="#conteudo">Pular para o conteúdo</a>
<header>
<div class="coluna">
<p class="marca">{esc(NOME_DO_SITE)}</p>
<nav aria-label="Pesquisas">
<ul>
{chr(10).join(itens)}
</ul>
</nav>
</div>
</header>
<main id="conteudo" tabindex="-1">
<div class="coluna">
"""


RODAPE = """</div>
</main>
<footer>
<div class="coluna">
<p>Pesquisas do projeto MCP de acessibilidade (origem: Qaaccessibility, em fontes oficiais, consultadas em 17 e 18 de outubro de 2026). A fala exata varia por leitor de tela, versão, navegador e configuração; nada aqui dispensa o teste manual com o leitor de tela real.</p>
</div>
</footer>
</body>
</html>
"""


def pagina_pesquisa(indice: int) -> str:
    arquivo, curto, _ = PESQUISAS[indice]
    blocos = ler_pesquisa(arquivo)
    titulo = next(str(t) for tipo, t in blocos if tipo == "h1")
    usados: set[str] = set()
    secoes: list[tuple[str, str]] = []
    # o leitor de tela le o titulo da aba a cada pagina aberta: o titulo da pesquisa (ate 25 palavras) vai no h1, a aba leva o nome curto
    saida: list[str] = [cabecalho(f"{curto} | {NOME_DO_SITE}", arquivo), f"<h1>{esc(titulo)}</h1>\n"]

    # a introducao (antes do primeiro ##) e o indice da pagina
    intro = []
    for tipo, valor in blocos:
        if tipo == "h2":
            break
        if tipo != "h1":
            intro.append((tipo, valor))
    for tipo, valor in intro:
        classe = ' class="origem"' if tipo == "p" and str(valor).startswith("Origem:") else ""
        saida.append(f"<p{classe}>{esc(str(valor))}</p>\n" if tipo == "p" else bloco_lista(tipo, valor))
    h2s = [str(v) for t, v in blocos if t == "h2"]
    for texto in h2s:
        base, n = slug(texto), 2
        ident = base
        while ident in usados:
            ident, n = f"{base}-{n}", n + 1
        usados.add(ident)
        secoes.append((ident, texto))
    if len(secoes) >= 3:
        itens = "\n".join(f'<li><a href="#{i}">{esc(t)}</a></li>' for i, t in secoes)
        saida.append(f'<nav class="neste-texto" aria-labelledby="neste-texto"><h2 id="neste-texto">Nesta página</h2>\n<ol>\n{itens}\n</ol>\n</nav>\n')

    aberta = False
    k = 0
    depois_do_h2 = False
    for tipo, valor in blocos:
        if tipo == "h2":
            if aberta:
                saida.append("</section>\n")
            ident, texto = secoes[k]
            k += 1
            saida.append(f'<section>\n<h2 id="{ident}">{esc(texto)}</h2>\n')
            aberta, depois_do_h2 = True, True
        elif depois_do_h2:
            saida.append(f"<p>{esc(str(valor))}</p>\n" if tipo == "p" else bloco_lista(tipo, valor))
    if aberta:
        saida.append("</section>\n")

    anterior = PESQUISAS[indice - 1] if indice > 0 else None
    seguinte = PESQUISAS[indice + 1] if indice < len(PESQUISAS) - 1 else None
    links = []
    links.append(f'<a href="{anterior[0]}.html">Anterior: {esc(anterior[1])}</a>' if anterior else '<a href="index.html">Início</a>')
    if seguinte:
        links.append(f'<a href="{seguinte[0]}.html">Próxima: {esc(seguinte[1])}</a>')
    saida.append(f'<nav class="entre" aria-label="Entre as pesquisas">\n{chr(10).join(links)}\n</nav>\n')
    saida.append(RODAPE)
    return "".join(saida)


def bloco_lista(tipo: str, itens: object) -> str:
    marcas = "".join(f"<li>{esc(i)}</li>\n" for i in itens)  # type: ignore[attr-defined]
    return f"<{tipo}>\n{marcas}</{tipo}>\n"


def pagina_inicial() -> str:
    cartoes = []
    for arquivo, curto, descricao in PESQUISAS:
        cartoes.append(f'<li>\n<a href="{arquivo}.html">{esc(curto)}</a>\n<p>{esc(descricao)}</p>\n</li>')
    return (
        cabecalho(NOME_DO_SITE, None)
        + f"""<h1>{esc(NOME_DO_SITE)}</h1>
<p>Seis pesquisas sobre o comportamento do leitor de tela em cenários diferentes: elementos HTML, estrutura e navegação, ARIA, CSS, ações do teclado e conteúdo dinâmico. Para cada um, o que a pessoa ouve quando o recurso é acessível e quando não é.</p>
<p class="origem">As falas variam por leitor de tela (NVDA, JAWS, VoiceOver, TalkBack), versão, navegador e verbosidade. Cada pesquisa diz o que foi confirmado em fonte oficial, o que veio de terceiros e o que não pôde ser lido.</p>
<ul class="cartoes">
{chr(10).join(cartoes)}
</ul>
"""
        + RODAPE
    )


def main() -> int:
    (HERE / "estilo.css").write_text(ESTILO, encoding="utf-8")
    (HERE / "index.html").write_text(pagina_inicial(), encoding="utf-8")
    for i, (arquivo, _, _) in enumerate(PESQUISAS):
        (HERE / f"{arquivo}.html").write_text(pagina_pesquisa(i), encoding="utf-8")
    print(f"site gerado em {HERE}: index.html + {len(PESQUISAS)} pesquisas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
