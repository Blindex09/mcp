"""Auditoria automatizada: contraste WCAG (puro) e axe-core via Playwright.

Seguranca: so navega em http/https (nunca file:, chrome:, javascript:), tem
timeout agregado e roda um navegador headless descartavel por chamada.
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .patience import patient
from .provisioning import provisioner_for

AXE_PATH = Path(__file__).parent / "vendor" / "axe.min.js"
NAV_TIMEOUT_MS = 30_000  # so a 1a espera; a MESMA navegacao e' tentada de novo com mais tempo (3x, 9x...), nao so o pedido inteiro
_LEVEL_TAGS = {
    "A": ["wcag2a", "wcag21a"],
    "AA": ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"],
    "AAA": ["wcag2a", "wcag2aa", "wcag2aaa", "wcag21a", "wcag21aa", "wcag22aa"],
}


# ---------------------------------------------------------------- contraste

def _parse_hex(value: str) -> tuple[int, int, int]:
    v = value.strip().lstrip("#")
    if re.fullmatch(r"[0-9a-fA-F]{3}", v):
        v = "".join(c * 2 for c in v)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", v):
        raise ValueError(f"cor invalida: {value!r} (use #rgb ou #rrggbb)")
    return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)


def _luminance(rgb: tuple[int, int, int]) -> float:
    def ch(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = (ch(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_report(fg: str, bg: str, size_px: float = 16, bold: bool = False) -> dict[str, Any]:
    l1, l2 = _luminance(_parse_hex(fg)), _luminance(_parse_hex(bg))
    ratio = (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)
    large = size_px >= 24 or (bold and size_px >= 18.66)
    return {
        "foreground": fg,
        "background": bg,
        "ratio": round(ratio, 2),
        "large_text": large,
        "AA_text": ratio >= (3.0 if large else 4.5),
        "AAA_text": ratio >= (4.5 if large else 7.0),
        "AA_ui_components": ratio >= 3.0,
    }


# --------------------------------------------------------------- navegador

def validate_url(url: str) -> str:
    p = urlparse(url.strip())
    if p.scheme not in ("http", "https") or not p.netloc:
        raise ValueError("so URLs http:// ou https:// sao permitidas")
    return url.strip()


async def _launch(pw: Any, browser: str = "chromium") -> Any:
    kind = getattr(pw, browser)
    try:
        return await kind.launch(headless=True)
    except Exception as first:  # binario da versao exata ausente: no Chromium, tenta outro instalado
        if browser == "chromium":
            root = Path.home() / "AppData" / "Local" / "ms-playwright"
            for exe in sorted(root.glob("chromium-*/chrome-win*/chrome.exe"), reverse=True):
                try:
                    return await kind.launch(headless=True, executable_path=str(exe))
                except Exception:  # noqa: BLE001, S112 - tenta o proximo binario
                    continue
        raise RuntimeError(
            f"{browser} do Playwright indisponivel. Rode: python -m playwright install {browser}"
        ) from first


COLOR_SCHEMES = ("light", "dark")


def check_color_scheme(value: str | None) -> str | None:
    """'' ou None = o padrao do navegador; so 'light' e 'dark' existem como emulacao (prefers-color-scheme)."""
    scheme = (value or "").strip().lower()
    if not scheme:
        return None
    if scheme not in COLOR_SCHEMES:
        raise ValueError("color_scheme deve ser light ou dark")
    return scheme


async def _with_page(
    url: str | None, html: str | None, fn: Callable[[Any], Awaitable[Any]], browser: str = "chromium", color_scheme: str | None = None
) -> Any:
    """Abre a pagina e roda fn(page). A navegacao (e a verificacao em si) usa tempo ADAPTATIVO: se a pagina/o site
    demorar mais que a 1a espera, a MESMA tentativa de navegar e' refeita com mais tempo (3x, 9x, 27x...), num
    navegador novo - nunca so um relogio unico que desiste e deixa de verificar um site so porque ele e' lento."""
    if bool(url) == bool(html):
        raise ValueError("informe exatamente um entre url e html")
    if url:
        validate_url(url)  # antes de subir o navegador
    scheme = check_color_scheme(color_scheme)
    await provisioner_for(browser).ensure()  # instala Playwright/navegador sozinho se faltar
    from playwright.async_api import async_playwright

    async def attempt(timeout_s: float) -> Any:
        nav_ms = int(timeout_s * 1000)
        async with async_playwright() as pw:
            instance = await _launch(pw, browser)
            try:
                page = await instance.new_page(color_scheme=scheme) if scheme else await instance.new_page()  # type: ignore[arg-type]
                page.set_default_timeout(nav_ms)  # piso para qualquer espera dentro de fn() sem timeout proprio
                if url:
                    await page.goto(url.strip(), wait_until="load", timeout=nav_ms)
                else:
                    await page.set_content(html or "", wait_until="load", timeout=nav_ms)
                return await fn(page)
            finally:
                await instance.close()

    return await patient(attempt, NAV_TIMEOUT_MS / 1000)


def summarize_axe(raw: dict[str, Any], max_nodes: int = 5) -> dict[str, Any]:
    def shape(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = []
        for v in items:
            out.append(
                {
                    "id": v.get("id"),
                    "impact": v.get("impact"),
                    "help": v.get("help"),
                    "wcag_tags": [t for t in v.get("tags", []) if t.startswith("wcag") or t == "best-practice"],
                    "help_url": v.get("helpUrl"),
                    "occurrences": len(v.get("nodes", [])),
                    "examples": [
                        {
                            "target": n.get("target"),
                            "html": (n.get("html") or "")[:200],
                            "fix": n.get("failureSummary"),
                        }
                        for n in v.get("nodes", [])[:max_nodes]
                    ],
                }
            )
        return out

    violations = shape(raw.get("violations", []))
    order = {"critical": 0, "serious": 1, "moderate": 2, "minor": 3}
    violations.sort(key=lambda v: order.get(v["impact"] or "minor", 4))
    return {
        "violations": violations,
        "needs_manual_review": shape(raw.get("incomplete", [])),
        "passes": len(raw.get("passes", [])),
        "note": (
            "Automatizado cobre so parte do WCAG; confirme com leitor de tela e teclado "
            "(ver referencia nvda-testing-guide)."
        ),
    }


async def run_axe(
    url: str | None = None, html: str | None = None, level: str = "AA", browser: str = "chromium", color_scheme: str | None = None
) -> dict[str, Any]:
    tags = _LEVEL_TAGS.get(level.upper())
    if tags is None:
        raise ValueError("level deve ser A, AA ou AAA")
    script = AXE_PATH.read_text(encoding="utf-8")

    async def fn(page: Any) -> dict[str, Any]:
        await page.add_script_tag(content=script)
        raw = await page.evaluate(
            "tags => axe.run(document, {runOnly: {type: 'tag', values: tags}})", tags
        )
        return summarize_axe(raw)

    result: dict[str, Any] = await _with_page(url, html, fn, browser, color_scheme)
    return result


async def aria_snapshot(url: str | None = None, html: str | None = None, browser: str = "chromium") -> str:
    async def fn(page: Any) -> str:
        return str(await page.locator("body").aria_snapshot())

    result: str = await _with_page(url, html, fn, browser)
    return result


_TAB_PROBE = """() => {
  let e = document.activeElement;
  while (e && e.shadowRoot && e.shadowRoot.activeElement) e = e.shadowRoot.activeElement;  // atravessa Shadow DOM aberto
  if (!e || e === document.body) return null;
  const r = e.getBoundingClientRect();
  const cs = getComputedStyle(e);
  // Identidade do no (nao da descricao): dois links com o mesmo texto e sem id continuam sendo dois elementos.
  const ids = (window.__a11yNodeIds = window.__a11yNodeIds || new WeakMap());
  if (!ids.has(e)) ids.set(e, (window.__a11yNodeSeq = (window.__a11yNodeSeq || 0) + 1));
  return {
    node: ids.get(e),
    tag: e.tagName.toLowerCase(),
    role: e.getAttribute('role'),
    name: (e.getAttribute('aria-label') || e.innerText || e.getAttribute('title')
           || e.getAttribute('alt') || '').trim().slice(0, 80),
    id: e.id || null,
    visible: r.width > 0 && r.height > 0,
    focus_style: {outline: cs.outlineStyle + ' ' + cs.outlineWidth + ' ' + cs.outlineColor + ' offset ' + cs.outlineOffset, box_shadow: cs.boxShadow}
  };
}"""


async def _focused_stop(page: Any) -> tuple[tuple[int, int], dict[str, Any]] | None:
    """Quem tem o foco AGORA e a IDENTIDADE do no (indice do frame, numero do no), atravessando iframes.

    A identidade vem do proprio no da pagina, nunca da descricao: dois links com o mesmo texto e o mesmo estilo
    sao dois elementos. None: o foco saiu da pagina."""
    info = await page.evaluate(_TAB_PROBE)
    if info is None:
        return None
    frame_index = 0
    if info["tag"] in ("iframe", "frame"):  # o foco esta dentro de um frame: pergunta a cada um quem o tem
        inner_found: tuple[int, dict[str, Any]] | None = None
        for i, fr in enumerate(page.frames):
            if i == 0:
                continue
            try:
                inner = await fr.evaluate(_TAB_PROBE)
            except Exception:  # noqa: BLE001, S112 - frame fechado ou em transicao
                continue
            if inner is None:
                continue
            if inner_found is None:
                inner_found = (i, inner)
            if inner["tag"] not in ("iframe", "frame"):  # frame aninhado: o foco real esta no mais fundo
                inner_found = (i, inner)
                break
        if inner_found is not None:
            frame_index, info = inner_found
    node = info.pop("node")
    return (frame_index, node), info


async def tab_stops(page: Any, steps: int) -> list[dict[str, Any]]:
    """Aperta Tab ate o foco sair da pagina, dar a volta ou parar de mover; cada parada e um NO, nao uma descricao."""
    seen: list[dict[str, Any]] = []
    first: tuple[int, int] | None = None
    previous: tuple[int, int] | None = None
    for i in range(steps) if steps else itertools.count():
        await page.keyboard.press("Tab")
        got = await _focused_stop(page)
        if got is None:
            break  # o foco saiu da pagina (Chromium/WebKit no ultimo elemento)
        ident, info = got
        if first is None:
            first = ident
        elif ident in (first, previous):
            break  # deu a volta no ciclo, ou o foco parou de mover (Firefox no ultimo elemento)
        previous = ident
        seen.append({"step": i + 1, "element": info})
    return seen


async def tab_order(
    url: str | None = None, html: str | None = None, max_steps: int = 0, browser: str = "chromium"
) -> list[dict[str, Any]]:
    steps = max(0, int(max_steps))  # 0 = ate o foco sair, dar a volta ou parar de mover

    async def fn(page: Any) -> list[dict[str, Any]]:
        return await tab_stops(page, steps)

    result: list[dict[str, Any]] = await _with_page(url, html, fn, browser)
    return result
