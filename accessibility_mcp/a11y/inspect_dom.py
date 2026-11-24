"""Inspecao de um elemento pelo CDP do Chromium: o que o DevTools mostra (Elements, Styles, Computed, Event Listeners, Accessibility) como FATOS.

Nada aqui julga: o modelo do cliente decide o que e defeito. O modulo so le o navegador e devolve o que ele mede, com a origem de cada dado
(arquivo, linha e coluna da regra de CSS; posicao do trecho no arquivo).
"""

from __future__ import annotations

import re
from typing import Any

from . import code_evidence
from .session import SessionError

ESTADOS = ("hover", "focus", "focus-visible", "active")
MAX_REGRAS = 40
MAX_PROPRIEDADES = 40
MAX_MUDANCAS = 25
MAX_CODIGO_OUVINTE = 300
MARCA_DA_FERRAMENTA = re.compile(r'\sdata-a11y-[a-z-]+="[^"]*"')

# propriedades devolvidas do estilo calculado quando a pessoa nao pede outras: as que decidem leitura, foco, alvo de toque e visibilidade
PROPRIEDADES_PADRAO = (
    "color", "background-color", "font-family", "font-size", "font-weight", "line-height", "letter-spacing", "text-decoration-line",
    "display", "position", "visibility", "opacity", "width", "height", "overflow", "z-index", "pointer-events", "cursor", "transform",
    "outline-style", "outline-width", "outline-color", "outline-offset", "box-shadow",
    "border-top-width", "border-top-style", "border-top-color", "border-radius", "padding-top", "padding-right", "padding-bottom", "padding-left",
)

# marcas objetivas que cada biblioteca deixa na pagina; achar a marca e um fato, nao um julgamento de intencao
MARCAS_JS = r"""() => {
    const found = {};
    const probe = [...document.querySelectorAll('body *')].slice(0, 400);
    const keyed = (prefix) => probe.some(e => Object.keys(e).some(k => k.startsWith(prefix)));
    if (keyed('__reactFiber$') || keyed('__reactProps$') || document.querySelector('[data-reactroot]')) found.react = true;
    if (probe.some(e => e.__vue_app__ || e.__vue__) || window.__VUE__) found.vue = true;
    const ng = document.querySelector('[ng-version]');
    if (ng) found.angular = ng.getAttribute('ng-version');
    if ([...document.querySelectorAll('[class*="svelte-"]')].length) found.svelte = true;
    if (window.__NEXT_DATA__) found.next = true;
    if (window.__NUXT__) found.nuxt = true;
    if (window.jQuery) found.jquery = window.jQuery.fn && window.jQuery.fn.jquery || true;
    const custom = [...new Set(probe.map(e => e.tagName.toLowerCase()).filter(t => t.includes('-')))];
    if (custom.length) found.web_components = custom.slice(0, 20);
    return found;
}"""


def _offset(texto: str, linha: int, coluna: int) -> int:
    """Posicao no texto de uma linha/coluna (base 0), como o CDP informa."""
    linhas = texto.split("\n")
    return sum(len(ln) + 1 for ln in linhas[:linha]) + coluna


def _trecho(texto: str, faixa: dict[str, int] | None) -> str | None:
    if not texto or not faixa:
        return None
    ini = _offset(texto, faixa["startLine"], faixa["startColumn"])
    fim = _offset(texto, faixa["endLine"], faixa["endColumn"])
    return texto[ini:fim]


def _declaracoes(estilo: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for p in estilo.get("cssProperties", []):
        if p.get("parsedOk", True) and not p.get("disabled"):
            item = {"name": p["name"], "value": p.get("value", "")}
            if p.get("important"):
                item["important"] = True
            out.append(item)
    return out[:MAX_PROPRIEDADES]


async def _regra(cdp: Any, sheets: dict[str, dict[str, Any]], textos: dict[str, str], regra: dict[str, Any]) -> dict[str, Any]:
    estilo = regra["style"]
    sheet_id = estilo.get("styleSheetId")
    cabecalho = sheets.get(sheet_id or "", {})
    if sheet_id and sheet_id not in textos:
        try:
            textos[sheet_id] = (await cdp.send("CSS.getStyleSheetText", {"styleSheetId": sheet_id}))["text"]
        except Exception:  # noqa: BLE001 - folha que o navegador nao devolve: a regra segue sem o trecho original
            textos[sheet_id] = ""
    faixa = estilo.get("range")
    seletor = regra["selectorList"]["text"]
    corpo = _trecho(textos.get(sheet_id or "", ""), faixa)
    item: dict[str, Any] = {
        "selector": seletor, "origin": regra.get("origin"),
        "sheet": cabecalho.get("sourceURL") or None, "embedded_in_html": bool(cabecalho.get("isInline")),
        "properties": _declaracoes(estilo),
    }
    if faixa:  # a linha da regra e' relativa a folha; folha embutida no HTML comeca na linha do documento em que o <style> abre
        item["line"], item["column"] = faixa["startLine"] + cabecalho.get("startLine", 0) + 1, faixa["startColumn"] + 1
    if corpo is not None:
        item["code"] = f"{seletor}{{{corpo}}}"
    return item


def _mudancas(base: dict[str, str], depois: dict[str, str]) -> dict[str, list[str | None]]:
    mudou = {k: [base.get(k), v] for k, v in depois.items() if base.get(k) != v}
    return dict(list(mudou.items())[:MAX_MUDANCAS])


def _caixa(modelo: dict[str, Any]) -> dict[str, Any]:
    def rect(q: list[float]) -> dict[str, float]:
        return {"x": q[0], "y": q[1], "w": round(q[2] - q[0], 2), "h": round(q[5] - q[1], 2)}

    return {nome: rect(modelo[nome]) for nome in ("content", "padding", "border", "margin") if modelo.get(nome)}


async def _ouvintes(cdp: Any, node: int) -> list[dict[str, Any]]:
    """Ouvintes do elemento, com o arquivo e o inicio do codigo de cada um (o CDP so informa o script, a linha e a coluna)."""
    scripts: dict[str, dict[str, Any]] = {}

    def guarda(evento: dict[str, Any]) -> None:
        scripts[evento["scriptId"]] = evento

    cdp.on("Debugger.scriptParsed", guarda)
    objeto = (await cdp.send("DOM.resolveNode", {"nodeId": node}))["object"]["objectId"]
    try:
        await cdp.send("Debugger.disable")  # recomeca para o navegador reenviar todos os scripts ja carregados
        await cdp.send("Debugger.enable")
        got = await cdp.send("DOMDebugger.getEventListeners", {"objectId": objeto})
        out = []
        for ln in got.get("listeners", []):
            linha, coluna = ln.get("lineNumber", 0), ln.get("columnNumber", 0)
            try:
                fonte = (await cdp.send("Debugger.getScriptSource", {"scriptId": ln["scriptId"]}))["scriptSource"]
            except Exception:  # noqa: BLE001 - script que o navegador nao devolve: o ouvinte segue sem o trecho
                fonte = ""
            script = scripts.get(ln["scriptId"], {})
            # script embutido: o CDP da a posicao no documento; o texto do script comeca em startLine/startColumn
            rel_linha = linha - script.get("startLine", 0)
            rel_coluna = coluna - script.get("startColumn", 0) if rel_linha == 0 else coluna
            inicio = _offset(fonte, rel_linha, rel_coluna)
            out.append({
                "type": ln["type"], "capture": ln.get("useCapture", False), "passive": ln.get("passive", False), "once": ln.get("once", False),
                "script": script.get("url") or "script embutido no HTML", "line": linha + 1, "column": coluna + 1,
                "code": fonte[inicio:inicio + MAX_CODIGO_OUVINTE] if fonte else None,
            })
        return out
    finally:
        await cdp.send("Debugger.disable")
        cdp.remove_listener("Debugger.scriptParsed", guarda)
        await cdp.send("Runtime.releaseObject", {"objectId": objeto})


async def _arvore_de_acessibilidade(cdp: Any, node: int) -> dict[str, Any]:
    got = await cdp.send("Accessibility.getPartialAXTree", {"nodeId": node, "fetchRelatives": False})
    no = got["nodes"][0] if got.get("nodes") else {}
    nome = no.get("name", {})
    return {
        "role": no.get("role", {}).get("value"), "name": nome.get("value"), "ignored": no.get("ignored", False),
        "name_sources": [{k: v for k, v in s.items() if k in ("type", "attribute", "value", "invalid")} for s in nome.get("sources", []) if s.get("value")],
        "properties": [{"name": p["name"], "value": p.get("value", {}).get("value")} for p in no.get("properties", [])],
    }


async def _tecnologias(session: Any) -> dict[str, Any]:
    """Marcas das bibliotecas na pagina e quais arquivos servidos declaram mapa de codigo-fonte (source map)."""
    page = session._need()
    marcas = await page.evaluate(MARCAS_JS)
    assets = await code_evidence.collect_assets(session)
    com_mapa = [nome for nome, texto in assets.items() if nome.startswith("http") and "sourceMappingURL=" in texto[-400:]]
    return {
        "markers": marcas,
        "served_files": {"total": sum(1 for n in assets if n.startswith("http")), "with_source_map": com_mapa},
        "note": ("marca = vestigio que a biblioteca deixa no DOM ou na janela; ausencia de marca nao prova que a biblioteca nao e usada. "
                 "Arquivo com source map permite voltar do codigo minificado ao fonte original"),
    }


async def inspect_element(session: Any, target: str, properties: list[str] | None = None, states: bool = True) -> dict[str, Any]:
    """HTML completo, estilos aplicados com origem, estilo calculado, estados, ouvintes, caixa, acessibilidade e tecnologias do elemento."""
    page = session._need()
    loc = session._locator(target)
    if await loc.count() == 0:
        raise SessionError("elemento nao encontrado (rode a11y_dossier de novo depois de navegar)")
    cdp = session.cdp
    if cdp is None:
        raise SessionError("a inspecao completa usa o CDP do Chromium: abra a sessao com browser=chromium")
    node = await session.cdp_node(loc)
    if not node:
        raise SessionError("elemento dentro de Shadow DOM sem id: rode a11y_dossier antes e use o id dele")

    sheets: dict[str, dict[str, Any]] = {}

    def guarda(evento: dict[str, Any]) -> None:
        sheets[evento["header"]["styleSheetId"]] = evento["header"]

    cdp.on("CSS.styleSheetAdded", guarda)
    try:
        await cdp.send("CSS.disable")  # recomeca para o navegador reenviar o cabecalho de todas as folhas
        await cdp.send("CSS.enable")
        html = (await cdp.send("DOM.getOuterHTML", {"nodeId": node}))["outerHTML"]
        atributos = (await cdp.send("DOM.getAttributes", {"nodeId": node}))["attributes"]
        casadas = await cdp.send("CSS.getMatchedStylesForNode", {"nodeId": node})
        textos: dict[str, str] = {}
        regras = [await _regra(cdp, sheets, textos, m["rule"]) for m in casadas.get("matchedCSSRules", [])[:MAX_REGRAS]]
        herdadas = []
        for nivel in casadas.get("inherited", []):
            for m in nivel.get("matchedCSSRules", []):
                herdadas.append(await _regra(cdp, sheets, textos, m["rule"]))
        calculado_bruto = await cdp.send("CSS.getComputedStyleForNode", {"nodeId": node})
        calculado = {p["name"]: p["value"] for p in calculado_bruto["computedStyle"]}
        pedidas = tuple(properties) if properties else PROPRIEDADES_PADRAO
        por_estado: dict[str, Any] = {}
        if states:
            for estado in ESTADOS:
                forcados = [estado, "focus"] if estado == "focus-visible" else [estado]
                try:
                    await cdp.send("CSS.forcePseudoState", {"nodeId": node, "forcedPseudoClasses": forcados})
                    depois = {p["name"]: p["value"] for p in (await cdp.send("CSS.getComputedStyleForNode", {"nodeId": node}))["computedStyle"]}
                finally:
                    await cdp.send("CSS.forcePseudoState", {"nodeId": node, "forcedPseudoClasses": []})
                por_estado[estado] = _mudancas(calculado, depois)
        ouvintes = await _ouvintes(cdp, node)
        try:
            caixa = _caixa((await cdp.send("DOM.getBoxModel", {"nodeId": node}))["model"])
        except Exception:  # noqa: BLE001 - elemento sem caixa (display:none): o fato e' a ausencia
            caixa = {}
        acessibilidade = await _arvore_de_acessibilidade(cdp, node)
    finally:
        cdp.remove_listener("CSS.styleSheetAdded", guarda)

    inline = casadas.get("inlineStyle")
    return {
        "target": target, "url": page.url,
        "html": {"code": MARCA_DA_FERRAMENTA.sub("", html)[:6000], "truncated": len(html) > 6000,
                 "note": "outerHTML do navegador, completo: atributos style e svg inteiros. So as marcas data-a11y-*, postas pelas ferramentas deste servidor, foram retiradas"},
        "attributes": {atributos[i]: atributos[i + 1] for i in range(0, len(atributos), 2) if not atributos[i].startswith("data-a11y-")},
        "inline_style": _declaracoes(inline) if inline else [],
        "matched_rules": regras,
        "inherited_rules": herdadas[:MAX_REGRAS],
        "computed_style": {k: calculado.get(k) for k in pedidas},
        "state_changes": por_estado,
        "event_listeners": ouvintes,
        "box": caixa,
        "accessibility": acessibilidade,
        "technologies": await _tecnologias(session),
        "limits": [
            "ouvintes de bibliotecas que delegam (React) ficam no elemento raiz ou no document, nao no elemento: veja a11y_page_map.delegated_listeners",
            "estado calculado por estado (hover, focus, focus-visible, active) e forcado no navegador, sem disparar eventos da pagina: estilo aplicado por onFocus/onMouseEnter em JavaScript nao aparece aqui; confirme com Tab real e a11y_screenshot",
        ],
    }
