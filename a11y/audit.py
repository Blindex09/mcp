"""Auditoria automatizada: contraste WCAG (puro) e axe-core via Playwright.

Seguranca: so navega em http/https (nunca file:, chrome:, javascript:), tem
timeout agregado e roda um navegador headless descartavel por chamada.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .provisioning import PROVISIONER

AXE_PATH = Path(__file__).parent / "vendor" / "axe.min.js"
NAV_TIMEOUT_MS = 30_000
TOTAL_TIMEOUT_S = 90
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


async def _launch(pw: Any) -> Any:
    try:
        return await pw.chromium.launch(headless=True)
    except Exception as first:  # binario da versao exata ausente: tenta outro instalado
        root = Path.home() / "AppData" / "Local" / "ms-playwright"
        for exe in sorted(root.glob("chromium-*/chrome-win*/chrome.exe"), reverse=True):
            try:
                return await pw.chromium.launch(headless=True, executable_path=str(exe))
            except Exception:  # noqa: BLE001, S112 - tenta o proximo binario
                continue
        raise RuntimeError(
            "Chromium do Playwright indisponivel. Rode: python -m playwright install chromium"
        ) from first


async def _with_page(
    url: str | None, html: str | None, fn: Callable[[Any], Awaitable[Any]]
) -> Any:
    if bool(url) == bool(html):
        raise ValueError("informe exatamente um entre url e html")
    if url:
        validate_url(url)  # antes de subir o navegador
    await PROVISIONER.ensure()  # instala Playwright/Chromium sozinho se faltar
    from playwright.async_api import async_playwright

    async def run() -> Any:
        async with async_playwright() as pw:
            browser = await _launch(pw)
            try:
                page = await browser.new_page()
                page.set_default_timeout(NAV_TIMEOUT_MS)
                if url:
                    await page.goto(url.strip(), wait_until="load")
                else:
                    await page.set_content(html or "", wait_until="load")
                return await fn(page)
            finally:
                await browser.close()

    return await asyncio.wait_for(run(), timeout=TOTAL_TIMEOUT_S)


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


async def run_axe(url: str | None = None, html: str | None = None, level: str = "AA") -> dict[str, Any]:
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

    result: dict[str, Any] = await _with_page(url, html, fn)
    return result


async def aria_snapshot(url: str | None = None, html: str | None = None) -> str:
    async def fn(page: Any) -> str:
        return str(await page.locator("body").aria_snapshot())

    result: str = await _with_page(url, html, fn)
    return result


_TAB_PROBE = """() => {
  const e = document.activeElement;
  if (!e || e === document.body) return null;
  const r = e.getBoundingClientRect();
  const cs = getComputedStyle(e);
  return {
    tag: e.tagName.toLowerCase(),
    role: e.getAttribute('role'),
    name: (e.getAttribute('aria-label') || e.innerText || e.getAttribute('title')
           || e.getAttribute('alt') || '').trim().slice(0, 80),
    id: e.id || null,
    visible: r.width > 0 && r.height > 0,
    focus_style: {outline: cs.outlineStyle + ' ' + cs.outlineWidth + ' ' + cs.outlineColor + ' offset ' + cs.outlineOffset, box_shadow: cs.boxShadow}
  };
}"""


async def tab_order(
    url: str | None = None, html: str | None = None, max_steps: int = 60
) -> list[dict[str, Any]]:
    steps = max(1, min(max_steps, 200))

    async def fn(page: Any) -> list[dict[str, Any]]:
        seen: list[dict[str, Any]] = []
        first_key = ""
        for i in range(steps):
            await page.keyboard.press("Tab")
            info = await page.evaluate(_TAB_PROBE)
            if info is None:
                break
            key = json.dumps(info, sort_keys=True)
            if i == 0:
                first_key = key
            elif key == first_key:
                break  # deu a volta no ciclo
            seen.append({"step": i + 1, "element": info})
        return seen

    result: list[dict[str, Any]] = await _with_page(url, html, fn)
    return result
