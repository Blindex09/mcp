"""Comparacao entre navegadores: a mesma pagina vista em Chromium, Firefox e/ou WebKit.

So FATOS lado a lado (arvore de acessibilidade, violacoes do axe, ordem de foco) e o que difere. Se uma diferenca
importa, e por que o navegador expoe diferente, e julgamento do modelo (guia: cross-browser-a11y).
"""

from __future__ import annotations

import difflib
from typing import Any

from . import audit
from .provisioning import BROWSERS, check_browser_name

MAX_DIFF_LINES = 60


async def _one(url: str | None, html: str | None, level: str, browser: str) -> dict[str, Any]:
    tags = audit._LEVEL_TAGS.get(level.upper())
    if tags is None:
        raise ValueError("level deve ser A, AA ou AAA")
    script = audit.AXE_PATH.read_text(encoding="utf-8")

    async def fn(page: Any) -> dict[str, Any]:
        aria = str(await page.locator("body").aria_snapshot())
        await page.add_script_tag(content=script)
        raw = await page.evaluate("tags => axe.run(document, {runOnly: {type: 'tag', values: tags}})", tags)
        stops: list[dict[str, Any]] = []
        first = previous = ""
        for i in range(60):
            await page.keyboard.press("Tab")
            info = await page.evaluate(audit._TAB_PROBE)
            if info is None:
                break  # o foco saiu da pagina
            sig = f"{info['tag']}|{info['name']}|{info['id']}"
            if i == 0:
                first = sig
            elif sig == first or sig == previous:
                break  # deu a volta, ou o foco parou de mover (fim da pagina no Firefox)
            previous = sig
            stops.append({"step": i + 1, **info})
        return {"aria": aria, "axe": audit.summarize_axe(raw), "tab_stops": stops}

    result: dict[str, Any] = await audit._with_page(url, html, fn, browser)
    return result


async def compare_browsers(
    url: str | None = None, html: str | None = None, browsers: list[str] | None = None, level: str = "AA"
) -> dict[str, Any]:
    names = list(dict.fromkeys(browsers or ["chromium", "firefox"]))
    if len(names) < 2:
        raise ValueError(f"informe pelo menos 2 navegadores entre: {', '.join(BROWSERS)}")
    for b in names:
        check_browser_name(b)
    per: dict[str, dict[str, Any]] = {}
    for b in names:
        per[b] = await _one(url, html, level, b)
    base = names[0]
    out: dict[str, Any] = {"browsers": names, "reference": base, "differences": {}, "per_browser": {}}
    for b in names:
        d = per[b]
        out["per_browser"][b] = {
            "aria_lines": len(d["aria"].splitlines()),
            "axe_violation_ids": sorted(v["id"] for v in d["axe"]["violations"]),
            "tab_stops": [f"{s['tag']}:{s['name']}" for s in d["tab_stops"]],
        }
    for b in names[1:]:
        a, c = per[base], per[b]
        aria_diff = list(difflib.unified_diff(
            a["aria"].splitlines(), c["aria"].splitlines(), fromfile=base, tofile=b, lineterm="", n=0
        ))
        ids_a = set(out["per_browser"][base]["axe_violation_ids"])
        ids_b = set(out["per_browser"][b]["axe_violation_ids"])
        tabs_a, tabs_b = out["per_browser"][base]["tab_stops"], out["per_browser"][b]["tab_stops"]
        out["differences"][b] = {
            "aria_tree": aria_diff[:MAX_DIFF_LINES] or "identica",
            "axe_only_in_reference": sorted(ids_a - ids_b),
            "axe_only_here": sorted(ids_b - ids_a),
            "tab_order": "identica" if tabs_a == tabs_b else {base: tabs_a, b: tabs_b},
        }
    out["note"] = (
        "So fatos. Diferencas podem ser bug da pagina ou modo diferente de cada navegador expor a acessibilidade; "
        "decida com o guia cross-browser-a11y. Nao e leitor de tela real."
    )
    return out
