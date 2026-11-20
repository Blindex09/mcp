"""Prova de que o codigo citado num achado e' o codigo REAL do site.

Um relatorio so serve ao desenvolvedor se o trecho "observado" existe de verdade no arquivo servido. Este modulo junta o que a pagina
serve (HTML renderizado, scripts e CSS) e procura cada trecho EXATAMENTE como foi escrito. Nao interpreta nem corrige: devolve onde achou,
em que arquivo, em que posicao e com que impressao digital do arquivo (para detectar que o site foi recompilado depois do teste).
"""

from __future__ import annotations

import hashlib
import re
from typing import Any
from urllib.parse import urljoin, urlsplit

MAX_ASSET_BYTES = 40 * 1024 * 1024
MAX_ASSETS = 40
_PLACEHOLDER = re.compile(r"(\.\.\.|…)")
_SVG_SUMMARY = "<svg>…</svg>"  # convencao aceita: o miolo de um icone nao muda o problema e o HTML copiado do navegador o resume assim
_SVG = re.compile(r"<svg\b[^>]*>.*?</svg>", re.DOTALL)
_STYLE_ATTR = re.compile(r'\sstyle="[^"]*"')
_WS = re.compile(r"\s+")


def fingerprint(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", "replace")).hexdigest()[:10]


def has_placeholder(snippet: str) -> bool:
    """Trecho resumido (\"…\", \"[...]\"): nao e' copia literal. So `<svg>…</svg>` e' aceito (o HTML do navegador resume o miolo dos icones assim)."""
    return bool(_PLACEHOLDER.search(snippet.replace(_SVG_SUMMARY, "")))


def normalized_dom(html: str) -> str:
    """O mesmo DOM sem os atributos style e com o miolo dos <svg> resumido: e' o formato do HTML que o relatorio mostra."""
    return _SVG.sub(_SVG_SUMMARY, _STYLE_ATTR.sub("", html))


def _squash(text: str) -> str:
    return _WS.sub("", text)


def locate(snippet: str, assets: dict[str, str]) -> dict[str, Any]:
    """Procura o trecho, sem alterar nada, em cada arquivo. `assets` mapeia nome/endereco -> texto."""
    wanted = snippet.strip("\n")
    result: dict[str, Any] = {"chars": len(wanted), "placeholder": has_placeholder(wanted), "found": False, "matches": []}
    if not wanted.strip():
        result["problem"] = "trecho vazio"
        return result
    for name, text in assets.items():
        start, count = text.find(wanted), text.count(wanted)
        if start >= 0:
            result["matches"].append({"asset": name, "position": start, "count": count, "fingerprint": fingerprint(text)})
    result["found"] = bool(result["matches"])
    if not result["found"]:
        squashed = _squash(wanted)
        for name, text in assets.items():
            if squashed and squashed in _squash(text):
                result["found_ignoring_whitespace"] = name
                break
        if result["placeholder"]:
            result["problem"] = "o trecho tem \"…\" ou \"[...]\": nao e' copia literal. Copie o texto exato ou separe em trechos menores"
        elif "found_ignoring_whitespace" in result:
            result["problem"] = "o trecho existe, mas com espacos ou quebras de linha diferentes: copie exatamente como esta no arquivo"
        else:
            result["problem"] = "o trecho nao existe em nenhum arquivo servido pela pagina (parafraseado, de outra versao ou de outra tela)"
    return result


def verify(snippets: list[str], assets: dict[str, str]) -> dict[str, Any]:
    checked = [{"index": i + 1, **locate(snippet, assets)} for i, snippet in enumerate(snippets)]
    failed = [c for c in checked if not c["found"]]
    return {
        "all_found": not failed, "snippets": checked,
        "assets": {name: {"chars": len(text), "fingerprint": fingerprint(text)} for name, text in assets.items()},
        "summary": ("todos os trechos existem exatamente como escritos" if not failed else
                    f"{len(failed)} de {len(checked)} trechos nao foram achados exatamente: " + "; ".join(f"#{c['index']}: {c['problem']}" for c in failed)),
    }


def snippet_blocks(text: str) -> list[str]:
    """Separa o campo de codigo de um achado em trechos verificaveis: ignora linhas de cabecalho (\"JS, ...:\", \"HTML, ...:\", \"CSS, ...:\")
    e linhas de nota; blocos separados por linha em branco."""
    blocks: list[str] = []
    for raw in re.split(r"\n\s*\n", text or ""):
        lines = [ln for ln in raw.split("\n")]
        if lines and re.match(r"^(JS|CSS|HTML)\b[^\n]*:\s*$", lines[0]):
            lines = lines[1:]
        body = "\n".join(lines).strip("\n")
        if body.strip():
            blocks.append(body)
    return blocks


async def collect_assets(session: Any) -> dict[str, str]:
    """HTML renderizado + scripts e estilos que a pagina carregou (somente GET, mesmo contexto do navegador de teste)."""
    page = session._need()
    info = await page.evaluate(
        """() => ({
            html: document.documentElement.outerHTML,
            scripts: [...document.scripts].map(s => s.src).filter(Boolean),
            styles: [...document.querySelectorAll('link[rel~=stylesheet]')].map(l => l.href).filter(Boolean),
            inlineScripts: [...document.scripts].filter(s => !s.src).map(s => s.textContent),
            inlineStyles: [...document.querySelectorAll('style')].map(s => s.textContent),
        })"""
    )
    assets: dict[str, str] = {"DOM renderizado": info["html"], "DOM renderizado (sem style, svg resumido)": normalized_dom(info["html"])}
    for i, text in enumerate(info["inlineScripts"], 1):
        if text and text.strip():
            assets[f"script embutido #{i}"] = text
    for i, text in enumerate(info["inlineStyles"], 1):
        if text and text.strip():
            assets[f"estilo embutido #{i}"] = text
    base = page.url
    # arquivos que o webpack carrega sob demanda (code splitting) removem a propria tag <script> depois de carregar: o historico de recursos do navegador os guarda
    loaded = await page.evaluate(
        r"""() => performance.getEntriesByType('resource').map(r => ({url: r.name, kind: r.initiatorType}))
                 .filter(r => /\.(js|css)(\?|$)/i.test(r.url) || r.kind === 'script' || r.kind === 'css').map(r => r.url)"""
    )
    urls = list(dict.fromkeys([*info["scripts"], *info["styles"], *loaded]))[:MAX_ASSETS]
    for url in urls:
        absolute = urljoin(base, url)
        if urlsplit(absolute).scheme not in ("http", "https"):
            continue
        try:
            response = await session.context.request.get(absolute, timeout=60000)
            body = await response.body()
        except Exception:  # noqa: BLE001, S112 - arquivo indisponivel: so nao entra na busca
            continue
        if len(body) <= MAX_ASSET_BYTES and response.ok:
            assets[absolute] = body.decode("utf-8", "replace")
    return assets


# ---------------------------------------------------------------------------------------------------------------- de onde veio o elemento
_JSX_CALL = re.compile(r"\(0,[A-Za-z_$][\w$]*\.jsxs?\)\(|\b[A-Za-z_$][\w$]*\.createElement\(|\bjsxs?\(")
MAX_EXCERPT = 3000


def balanced_end(text: str, start: int) -> int | None:
    """Indice logo depois do ')' que fecha o '(' que abre em `start` - 1... ou None. Entende aspas e crases; nao tenta entender regex literal."""
    depth, i, quote = 0, start, ""
    while i < len(text):
        ch = text[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = ""
        elif ch in "\"'`":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            if depth == 0:
                return i + 1
            depth -= 1
        i += 1
    return None


def enclosing_call(text: str, position: int) -> dict[str, Any]:
    """O trecho EXATO do arquivo (sem alteracao) da chamada JSX/createElement que contem `position`: o elemento como o codigo o cria."""
    best = None
    for m in _JSX_CALL.finditer(text, max(0, position - 6000), position):
        end = balanced_end(text, m.end())
        if end and end > position:
            best = (m.start(), end)  # a ultima chamada que abre antes e ainda contem a posicao: a mais interna
    if best is None:
        lo, hi = max(0, position - 300), min(len(text), position + 300)
        return {"start": lo, "end": hi, "excerpt": text[lo:hi], "note": "nao achei a chamada que cria o elemento; recorte de 300 caracteres de cada lado"}
    start, end = best
    cut = end - start > MAX_EXCERPT
    return {"start": start, "end": end, "excerpt": text[start:start + MAX_EXCERPT] if cut else text[start:end], "truncated": cut,
            "note": "a chamada continua alem do recorte (copia exata do inicio)" if cut else "chamada completa, copia exata"}


def component_of(text: str, position: int) -> dict[str, Any] | None:
    m = None
    for m in re.finditer(r"function\s+([A-Za-z_$][\w$]*)\s*\(", text[max(0, position - 40000):position]):
        pass
    return {"name": m.group(1), "start": max(0, position - 40000) + m.start()} if m else None


def element_tokens(info: dict[str, Any]) -> list[str]:
    """Textos do elemento que identificam o codigo que o cria, do mais especifico ao mais geral: a classe INTEIRA, data-testid e a parte final dele
    (ids montados em tempo de execucao: prefixo + "seguro-viagem"), aria-label, id, nome, texto visivel, papel e cada classe."""
    attrs = info.get("attrs", {})
    out: list[str] = []
    cls = str(attrs.get("class") or "").strip()
    if " " in cls:
        out.append(cls)
    for key in ("data-testid", "id", "aria-label", "name"):
        value = str(attrs.get(key) or "").strip()
        if not value:
            continue
        out.append(value)
        stem = re.sub(r"\d+$", "", value)
        if stem and stem != value:
            out.append(stem)  # "wizard-age-0" -> "wizard-age-" (montado com o indice)
        head = value[: value.rfind("-") + 1]
        if len(head) >= 6 and head != value:
            out.append(head)  # "awz-esim-country-PT" -> "awz-esim-country-" (prefixo + codigo do pais, tabela de constantes)
        parts = value.split("-")
        for i in range(1, len(parts) - 1):
            tail = "-".join(parts[i:])
            if len(tail) >= 8:
                out.append(tail)  # "lv2-product-seguro-viagem" -> "seguro-viagem"
    text = str(info.get("text") or "").strip()
    if 2 <= len(text) <= 60:
        out.append(text)
    if attrs.get("role"):
        out.append(str(attrs["role"]))
    out.extend(cls.split()[:3])
    return list(dict.fromkeys(t for t in out if len(t) >= 3))


def _table_name(text: str, position: int) -> str | None:
    """Nome da tabela de constantes (objeto) que contem `position`: o ultimo `NOME:{` aberto antes dele."""
    depth = 0
    for i in range(position - 1, max(0, position - 20000), -1):
        ch = text[i]
        if ch == "}":
            depth += 1
        elif ch == "{":
            if depth == 0:
                m = re.search(r"([A-Za-z_$][\w$]*):$", text[max(0, i - 60):i])
                return m.group(1) if m else None
            depth -= 1
    return None


def _constant_needles(text: str, position: int, constant: str) -> list[str]:
    """Como a constante e' usada no codigo minificado: `V.Y9.TABELA.CONST` ou `alias.CONST`, onde `alias=X.Y9.TABELA` (so a MESMA tabela)."""
    table = _table_name(text, position)
    if not table:
        return ["." + constant]
    needles = [f".Y9.{table}.{constant}"]
    for alias in re.findall(r"([A-Za-z_$][\w$]*)=[A-Za-z_$][\w$]*\.Y9\." + re.escape(table) + r"\b", text):
        needles.append(f"{alias}.{constant}")
    return needles


def find_sources(info: dict[str, Any], assets: dict[str, str]) -> list[dict[str, Any]]:
    """Onde esta o codigo (JS) que cria o elemento: a chamada JSX que contem os textos do elemento. Ordena pela quantidade de textos distintos que a
    chamada contem (a que tem classe inteira, testid, papel e texto vence a que so tem uma classe comum). Copia exata, com posicao e arquivo."""
    tokens = element_tokens(info)
    candidates: dict[tuple[str, int], dict[str, Any]] = {}
    for token in tokens:
        for name, text in assets.items():
            if name.startswith(("DOM", "estilo")) or name.endswith(".css") or "gtag" in name or "facebook" in name or "gtm" in name or "fonts.googleapis" in name:
                continue
            needles = [f"{q}{token}{q}" for q in ('"', "'")]
            # o valor tambem pode vir de uma tabela de constantes (ESIM_DESTINATION:"awz-esim-destination"): procura onde a CONSTANTE e' usada,
            # na MESMA tabela (duas tabelas podem ter o mesmo nome de constante com valores diferentes)
            for const in re.finditer(r"\b([A-Z][A-Z0-9_]{2,}):[\"']" + re.escape(token) + r"[\"']", text):
                needles.extend(_constant_needles(text, const.start(), const.group(1)))
            for needle in needles:
                start = 0
                for _ in range(4):
                    p = text.find(needle, start)
                    if p < 0:
                        break
                    start = p + 1
                    if needle[-1].isalnum() or needle[-1] == "_":
                        if text[p + len(needle):p + len(needle) + 1].isalnum() or text[p + len(needle):p + len(needle) + 1] == "_":
                            continue  # ".ESIM_DESTINATION_X" nao e' ".ESIM_DESTINATION"
                        if needle[0].isalpha() and p > 0 and (text[p - 1].isalnum() or text[p - 1] in "_$"):
                            continue  # "xup.CONST" nao e' "up.CONST"
                    call = enclosing_call(text, p)
                    key = (name, call["start"])
                    if key not in candidates:
                        window = text[call["start"]:call["end"]]
                        candidates[key] = {"asset": name, "position": call["start"], "end": call["end"], "fingerprint": fingerprint(text), "component": component_of(text, p),
                                           "code": call["excerpt"], "note": call["note"], "matched_tokens": [t for t in tokens if f'"{t}"' in window or f"'{t}'" in window]}
    found = list(candidates.values())
    if any(not c["note"].startswith("nao achei") for c in found):
        found = [c for c in found if not c["note"].startswith("nao achei")]  # tabela de constantes e textos soltos nao sao o elemento
    ranked = sorted(found, key=lambda c: (-len(c["matched_tokens"]), c["end"] - c["position"]))
    for c in ranked:
        c["score"] = len(c["matched_tokens"])
    return ranked[:6]


def css_rules_js() -> str:
    return """(el) => {
        const out = [];
        for (const sheet of document.styleSheets) {
            let rules; try { rules = sheet.cssRules; } catch (e) { continue; }
            const walk = (list) => { for (const rule of list) {
                if (rule.cssRules && !rule.selectorText) { walk(rule.cssRules); continue; }
                if (!rule.selectorText) continue;
                let hit = false; try { hit = el.matches(rule.selectorText); } catch (e) {}
                if (hit) out.push({sheet: sheet.href || 'estilo embutido', selector: rule.selectorText, css: rule.cssText});
            } };
            walk(rules);
        }
        return out.slice(0, 40);
    }"""


def css_source(selector: str, assets: dict[str, str]) -> dict[str, Any] | None:
    """O texto ORIGINAL da regra (como esta no arquivo de estilo), porque o cssText do navegador reescreve cores e espacos. Lista de seletores
    ("a, b") casa com ou sem espaco depois da virgula."""
    parts = [re.escape(x.strip()) for x in selector.split(",") if x.strip()]
    if not parts:
        return None
    pattern = re.compile(r"\s*,\s*".join(parts) + r"\s*\{")
    for name, text in assets.items():
        if not (name.endswith(".css") or ".css?" in name or name.startswith("estilo embutido")):
            continue
        for m in pattern.finditer(text):
            before = text[:m.start()]
            comment_end = before.rfind("*/")
            cut = max(before.rfind("}") + 1, before.rfind("{") + 1, before.rfind(";") + 1, comment_end + 2 if comment_end >= 0 else 0)
            if before[cut:].strip():
                continue  # o seletor faz parte de uma lista maior ou de um seletor composto: nao e' esta regra
            end = text.find("}", m.end())
            if end > 0:
                return {"asset": name, "position": m.start(), "code": text[m.start():end + 1], "fingerprint": fingerprint(text)}
    return None


def rank_css_rules(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Regras genericas (*, ::before, html, body) vao para o fim: o que importa e' a regra mais especifica do elemento."""
    generic = {"*", "::after", "::before", "html", "body", "*, ::after, ::before", "*, ::before, ::after"}
    return sorted(rules, key=lambda r: (str(r.get("selector", "")).strip() in generic, -len(str(r.get("selector", "")))))
