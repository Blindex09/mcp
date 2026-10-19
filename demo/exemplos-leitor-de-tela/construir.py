"""Gera o site "Leitor de tela: exemplos bons e ruins", medindo cada exemplo com o proprio MCP.

Para cada exemplo, o gerador abre o HTML num navegador e guarda (1) a arvore de acessibilidade que o navegador entrega ao leitor de
tela e (2) as violacoes que o axe acha. Nada disso e escrito a mao. O texto do porque e do que corrigir esta em exemplos.py.

Uso:  python demo/exemplos-leitor-de-tela/construir.py     (escreve os .html e o estilo.css nesta pasta)
"""

from __future__ import annotations

import asyncio
import html
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent))

from exemplos import CENARIOS, ROTULO
from interativos import ROTAS

from accessibility_mcp.a11y import audit

NOME_DO_SITE = "Leitor de tela: exemplos bons e ruins"

ESTILO = """\
:root {
  color-scheme: light dark;
  --texto: light-dark(#1a1a1a, #f2f2f2);
  --fundo: light-dark(#ffffff, #121212);
  --suave: light-dark(#4a4a4a, #c4c4c4);
  --link: light-dark(#0a4aad, #8ab4f8);
  --borda: light-dark(#8a8a8a, #8a8a8a);
  --destaque: light-dark(#eef3fb, #1c2230);
  --ruim: light-dark(#a3231b, #ff9d94);
  --bom: light-dark(#17642b, #8fe3a0);
  --ok: light-dark(#7a4a00, #ffd27a);
}
* { box-sizing: border-box; }
html { font-size: 100%; }
body {
  margin: 0; color: var(--texto); background: var(--fundo);
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
  font-size: 1.125rem; line-height: 1.6; overflow-wrap: anywhere;
}
a { color: var(--link); text-underline-offset: 0.15em; }
:focus-visible { outline: 3px solid var(--link); outline-offset: 2px; border-radius: 3px; }
:focus:not(:focus-visible) { outline: none; }
main:focus { outline: none; }
.pular { position: absolute; left: -9999px; top: 0.5rem; z-index: 10; padding: 0.75rem 1rem; background: var(--link); color: var(--fundo); border-radius: 4px; }
.pular:focus { left: 0.5rem; }
.coluna { max-width: 46rem; margin-inline: auto; padding-inline: 1rem; }
header { border-bottom: 1px solid var(--borda); padding-block: 0.75rem; }
.marca { font-weight: 700; margin: 0 0 0.25rem; }
nav ul { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 0.25rem 0.5rem; }
nav a { display: inline-block; min-height: 44px; min-width: 44px; padding: 0.55rem 0.5rem; }
nav a[aria-current="page"] { font-weight: 700; text-decoration: none; border-bottom: 3px solid currentColor; }
main { padding-block: 1.5rem 3rem; }
h1 { font-size: 1.9rem; line-height: 1.25; margin: 0 0 1rem; }
h2 { font-size: 1.4rem; line-height: 1.3; margin: 2.5rem 0 0.75rem; }
h3 { font-size: 1.1rem; line-height: 1.3; margin: 1.5rem 0 0.4rem; }
p, li { max-width: 70ch; }
.neste-texto { background: var(--destaque); border: 1px solid var(--borda); border-radius: 6px; padding: 0.5rem 1rem 0.75rem; margin-block: 1.5rem; }
.neste-texto h2 { font-size: 1.1rem; margin: 0.5rem 0 0.25rem; }
.neste-texto ol { margin: 0; padding-left: 1.4rem; }
.neste-texto a { min-height: 24px; display: inline-block; padding-block: 0.15rem; }
.etiqueta { font-weight: 700; }
.t-ruim { color: var(--ruim); }
.t-bom { color: var(--bom); }
.t-ok { color: var(--ok); }
.exemplo { border: 2px dashed var(--borda); border-radius: 8px; padding: 1rem; margin-block: 0.75rem; }
.exemplo-ruim { border-left: 8px solid var(--ruim); }
.exemplo-bom { border-left: 8px solid var(--bom); }
.exemplo-ok { border-left: 8px solid var(--ok); }
pre { white-space: pre-wrap; overflow-wrap: anywhere; background: var(--destaque); border: 1px solid var(--borda); border-radius: 6px; padding: 0.75rem 1rem; font-size: 0.95rem; line-height: 1.45; margin: 0.4rem 0; }
.entre { display: flex; flex-wrap: wrap; gap: 1rem; justify-content: space-between; margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--borda); }
.entre a { display: inline-block; min-height: 44px; padding: 0.55rem 0; }
footer { border-top: 1px solid var(--borda); padding-block: 1rem 2rem; color: var(--suave); font-size: 1rem; }

/* aparencia dos exemplos: ruim e bom parecem iguais de proposito; a diferenca esta na estrutura, nao no visual */
.exemplo .vt1 { font-size: 1.6rem; font-weight: 700; line-height: 1.25; }
.exemplo .vt2 { font-size: 1.25rem; font-weight: 700; margin-top: 0.75rem; }
.exemplo h3, .exemplo h4, .exemplo h5 { font-size: 1.25rem; margin: 0.75rem 0 0; }
.exemplo .botao, .exemplo .fake-botao { display: inline-block; min-height: 44px; padding: 0.55rem 1rem; border: 2px solid var(--link); border-radius: 6px; background: var(--fundo); color: var(--link); font: inherit; cursor: pointer; }
.exemplo ul.cartoes { list-style: none; padding: 0; }
.exemplo ul.cartoes li { border: 1px solid var(--borda); border-radius: 6px; padding: 0.25rem 0.75rem; margin-block: 0.5rem; max-width: none; }
.exemplo table { border-collapse: collapse; }
.exemplo td, .exemplo th { border: 1px solid var(--borda); padding: 0.35rem 0.75rem; text-align: left; }
.exemplo input { font: inherit; min-height: 44px; padding: 0.25rem 0.5rem; }
.exemplo .caixa-falsa { margin-top: 0.75rem; padding: 0.75rem 1rem; border: 2px solid var(--borda); border-radius: 6px; background: var(--destaque); }
.exemplo .abas-falsas { display: flex; gap: 0.5rem; margin-bottom: 0.5rem; }
.exemplo .opcao-falsa { padding: 0.35rem 0.5rem; border: 1px solid var(--borda); }
.exemplo [role="tablist"] { display: flex; gap: 0.5rem; margin-bottom: 0.5rem; }
.exemplo [role="tab"] { min-height: 44px; padding: 0.55rem 1rem; border: 2px solid var(--link); border-radius: 6px; background: var(--fundo); color: var(--link); font: inherit; cursor: pointer; }
.exemplo [role="tab"][aria-selected="true"] { background: var(--link); color: var(--fundo); }
.exemplo [role="menu"], .exemplo [role="listbox"] { list-style: none; margin: 0.25rem 0; padding: 0.25rem; border: 2px solid var(--borda); border-radius: 6px; max-width: 16rem; }
.exemplo [role="menuitem"], .exemplo [role="option"] { display: block; width: 100%; min-height: 44px; padding: 0.5rem 0.75rem; text-align: left; border: 0; background: transparent; color: var(--texto); font: inherit; cursor: pointer; }
.exemplo [role="option"][aria-selected="true"] { background: var(--link); color: var(--fundo); }
.exemplo dialog { max-width: 28rem; border: 2px solid var(--borda); border-radius: 8px; background: var(--fundo); color: var(--texto); }
.exemplo .erro-visual { color: var(--ruim); font-weight: 700; }
.exemplo summary { cursor: pointer; min-height: 44px; padding-block: 0.5rem; }
.exemplo button { min-height: 44px; min-width: 44px; padding: 0.5rem 1rem; font: inherit; }

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; scroll-behavior: auto !important; }
}
@media (prefers-contrast: more) {
  :root { --texto: light-dark(#000000, #ffffff); --suave: light-dark(#222222, #eeeeee); }
}
@media (forced-colors: active) {
  nav a[aria-current="page"] { border-bottom-color: Highlight; }
  .exemplo, .neste-texto, pre { border-color: CanvasText; }
}
"""


def esc(texto: str) -> str:
    return html.escape(texto, quote=True)


async def medir(fragmento: str) -> dict[str, Any]:
    """A arvore de acessibilidade do fragmento e as violacoes do axe (nivel AA), medidas pelo codigo do proprio MCP."""
    documento = (
        '<!doctype html><html lang="pt-BR"><head><title>exemplo</title></head><body><main><div id="medida">'
        + fragmento + "</div></main></body></html>"
    )
    axe_js = audit.AXE_PATH.read_text(encoding="utf-8")

    async def fn(page: Any) -> dict[str, Any]:
        arvore = str(await page.locator("#medida").aria_snapshot())
        await page.add_script_tag(content=axe_js)
        bruto = await page.evaluate("tags => axe.run(document, {runOnly: {type: 'tag', values: tags}})", audit._LEVEL_TAGS["AA"])
        violacoes = [(v["id"], v["help"]) for v in audit.summarize_axe(bruto)["violations"]]
        return {"arvore": arvore.strip(), "violacoes": violacoes}

    resultado: dict[str, Any] = await audit._with_page(None, documento, fn)
    return resultado


async def medir_sonda(fragmento: str, tipo: str, alvo: str, documento: str | None = None) -> list[dict[str, Any]]:
    """Roda a sonda do MCP (teclado de verdade, no Chromium) contra o exemplo sozinho e devolve os checks esperado x observado."""
    from accessibility_mcp.a11y.probes import run_probe
    from accessibility_mcp.a11y.session import SESSION

    if documento is None:
        documento = '<!doctype html><html lang="pt-BR"><head><title>exemplo</title></head><body><main>' + fragmento + "</main></body></html>"
    await SESSION.open(None, documento)
    try:
        resultado = await run_probe(SESSION, tipo, alvo)
    finally:
        await SESSION.close()
    return list(resultado["checks"])


async def medir_todos() -> dict[tuple[str, int], dict[str, Any]]:
    medidas: dict[tuple[str, int], dict[str, Any]] = {}
    for cenario in CENARIOS:
        for i, ex in enumerate(cenario["exemplos"]):
            medida = await medir(ex["html"])
            if ex.get("sonda"):
                medida["sonda"] = await medir_sonda(ex["html"], *ex["sonda"], documento=ROTAS[ex["documento"]] if ex.get("documento") else None)
            medidas[(cenario["slug"], i)] = medida
    return medidas


def cabecalho(titulo: str, atual: str | None) -> str:
    itens = ['<li><a href="index.html"' + (' aria-current="page"' if atual is None else "") + ">Início</a></li>"]
    for c in CENARIOS:
        corrente = ' aria-current="page"' if c["slug"] == atual else ""
        itens.append(f'<li><a href="{c["slug"]}.html"{corrente}>{esc(c["nome"])}</a></li>')
    lista = "\n".join(itens)
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(titulo)}</title>
<link rel="stylesheet" href="estilo.css">
</head>
<body>
<a class="pular" href="#conteudo">Pular para o conteúdo</a>
<header>
<div class="coluna">
<p class="marca">{esc(NOME_DO_SITE)}</p>
<nav aria-label="Cenários">
<ul>
{lista}
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
<p>Exemplos do projeto MCP de acessibilidade. A árvore de acessibilidade e o resultado do axe foram medidos pelo próprio MCP, no Chromium, quando o site foi gerado. O que cada leitor de tela fala varia com o leitor, a versão, o navegador e a configuração: ouça os exemplos vivos no seu leitor e compare.</p>
</div>
</footer>
</body>
</html>
"""


def texto_do_axe(tipo: str, violacoes: list[tuple[str, str]]) -> str:
    if violacoes:
        achados = "; ".join(f"{regra} ({ajuda})" for regra, ajuda in violacoes)
        return f"O axe achou: {achados}."
    if tipo == "ruim":
        return "O axe não achou nada neste exemplo. É um problema que só aparece olhando a árvore de acessibilidade ou ouvindo com o leitor de tela."
    return "O axe não achou nenhuma violação (nível AA)."


NL = chr(10)


def texto_da_sonda(checks: list[dict[str, Any]]) -> str:
    linhas = []
    for c in checks:
        estado = "não deu para medir" if c["met"] is None else ("cumpriu" if c["met"] else "NÃO cumpriu")
        linhas.append(f"{estado}: {c['expected']}. Observado: {c['observed']}.")
    return NL.join(linhas)


def bloco_exemplo(cenario: dict[str, Any], i: int, medida: dict[str, Any]) -> str:
    ex = cenario["exemplos"][i]
    tipo = ex["tipo"]
    ident = f"ex-{i + 1}"
    return (
        f'<h2 id="{ident}"><span class="etiqueta t-{tipo}">{esc(ROTULO[tipo])}:</span> {esc(ex["titulo"])}</h2>\n'
        f'<div class="exemplo exemplo-{tipo}" role="group" aria-label="Exemplo ao vivo, {esc(ROTULO[tipo].lower())}: {esc(ex["titulo"])}">{ex["html"]}</div>\n'
        f'<h3>Por quê</h3>\n<p>{esc(ex["porque"])}</p>\n'
        f'<h3>O que corrigir</h3>\n<p>{esc(ex["corrigir"])}</p>\n'
        f'<h3>O que o navegador entrega ao leitor de tela (medido)</h3>\n<pre>{esc(medida["arvore"])}</pre>\n'
        f'<h3>O que o axe acha (medido)</h3>\n<p>{esc(texto_do_axe(tipo, medida["violacoes"]))}</p>\n'
        + (f'<h3>Comportamento com o teclado (sonda {esc(ex["sonda"][0])}, medido)</h3>\n<pre>{esc(texto_da_sonda(medida["sonda"]))}</pre>\n' if medida.get("sonda") else "")
        +
        f'<h3>Código</h3>\n<pre>{esc(ex["html"])}</pre>\n'
    )


def pagina_cenario(indice: int, medidas: dict[tuple[str, int], dict[str, Any]]) -> str:
    c = CENARIOS[indice]
    saida = [cabecalho(f"{c['nome']} | {NOME_DO_SITE}", c["slug"]), f"<h1>{esc(c['nome'])}</h1>\n", f"<p>{esc(c['resumo'])}</p>\n"]
    itens = "\n".join(
        f'<li><a href="#ex-{i + 1}">{esc(ROTULO[ex["tipo"]])}: {esc(ex["titulo"])}</a></li>' for i, ex in enumerate(c["exemplos"])
    )
    saida.append(f'<nav class="neste-texto" aria-labelledby="neste-texto"><h2 id="neste-texto">Nesta página</h2>\n<ol>\n{itens}\n</ol>\n</nav>\n')
    for i in range(len(c["exemplos"])):
        saida.append(bloco_exemplo(c, i, medidas[(c["slug"], i)]))
    anterior = CENARIOS[indice - 1] if indice > 0 else None
    seguinte = CENARIOS[indice + 1] if indice < len(CENARIOS) - 1 else None
    links = [f'<a href="{anterior["slug"]}.html">Anterior: {esc(anterior["nome"])}</a>' if anterior else '<a href="index.html">Início</a>']
    if seguinte:
        links.append(f'<a href="{seguinte["slug"]}.html">Próximo: {esc(seguinte["nome"])}</a>')
    saida.append('<nav class="entre" aria-label="Entre os cenários">\n' + "\n".join(links) + "\n</nav>\n")
    saida.append(RODAPE)
    return "".join(saida)


def pagina_inicial() -> str:
    secoes = []
    for c in CENARIOS:
        tipos = ", ".join(sorted({ROTULO[ex["tipo"]].lower() for ex in c["exemplos"]}))
        secoes.append(f'<h2><a href="{c["slug"]}.html">{esc(c["nome"])}</a></h2>\n<p>{esc(c["resumo"])} ({esc(tipos)}.)</p>')
    return (
        cabecalho(NOME_DO_SITE, None)
        + f"""<h1>{esc(NOME_DO_SITE)}</h1>
<p>Para cada assunto há um exemplo ruim, um bom e, quando existe, um que parece estranho mas não precisa de correção. Os exemplos estão vivos na página: ouça com o seu leitor de tela e compare. Embaixo de cada um estão o porquê, o que corrigir, o que o navegador entrega ao leitor de tela e o que o axe acha, medidos pelo próprio MCP.</p>
<p>Ruim e bom parecem iguais de propósito. A diferença está na estrutura, não no visual.</p>
{chr(10).join(secoes)}
"""
        + RODAPE
    )


def main() -> int:
    medidas = asyncio.run(medir_todos())
    (HERE / "estilo.css").write_text(ESTILO, encoding="utf-8")
    (HERE / "index.html").write_text(pagina_inicial(), encoding="utf-8")
    for nome, pagina in ROTAS.items():
        (HERE / f"{nome}.html").write_text(pagina, encoding="utf-8")
    for i, c in enumerate(CENARIOS):
        (HERE / f"{c['slug']}.html").write_text(pagina_cenario(i, medidas), encoding="utf-8")
    total = sum(len(c["exemplos"]) for c in CENARIOS)
    print(f"site gerado em {HERE}: index.html + {len(CENARIOS)} cenarios, {total} exemplos medidos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
