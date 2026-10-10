"""Varredura de varias paginas do MESMO site: fatos consolidados (axe + mapa da pagina) sem julgamento.

Regras do harness (protecao, nao opiniao): mesmo dominio, so http/https, respeita robots.txt, so navega (GET; qualquer
requisicao que altere dados e' bloqueada), ritmo com pausa entre paginas, teto de paginas e de tempo. Quem interpreta
os fatos (o que significa um titulo repetido, se uma pagina merece atencao) e o modelo.
"""

from __future__ import annotations

import asyncio
import functools
import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import Any
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

from . import audit
from . import page_scripts as js
from .patience import patient
from .provisioning import provisioner_for

MAX_PAGES_CEILING = 30
POLITE_PAUSE_S = 0.3
PAGE_TIMEOUT_MS = 20_000  # so a 1a espera por pagina; se estourar, repete com mais tempo
USER_AGENT = "accessibility-mcp-crawler"


def _same_site(url: str, origin: str) -> bool:
    p, o = urlparse(url), urlparse(origin)
    return p.scheme in ("http", "https") and p.netloc == o.netloc


def _clean(url: str) -> str:
    return urldefrag(url.strip())[0]


async def _robots(origin: str) -> RobotFileParser:
    rp = RobotFileParser()
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as c:
            r = await c.get(urljoin(origin, "/robots.txt"), headers={"user-agent": USER_AGENT})
        rp.parse(r.text.splitlines() if r.status_code == 200 else [])
    except (httpx.HTTPError, ValueError):
        rp.parse([])  # sem robots acessivel: nada e' proibido
    return rp


async def _sitemap_urls(origin: str, limit: int) -> list[str]:
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as c:
            r = await c.get(urljoin(origin, "/sitemap.xml"), headers={"user-agent": USER_AGENT})
        if r.status_code != 200:
            return []
        root = ET.fromstring(r.text)
        return [(e.text or "").strip() for e in root.iter() if e.tag.endswith("loc") and e.text][:limit]
    except (httpx.HTTPError, ET.ParseError, ValueError):
        return []


async def _goto(page: Any, target: str, timeout: float) -> Any:
    return await page.goto(target, wait_until="load", timeout=timeout)


async def _looks_html(url: str) -> bool:
    """Tipo de conteudo declarado pelo servidor (HEAD). Sem resposta clara, assume que e' pagina e deixa o navegador decidir."""
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as c:
            r = await c.head(url, headers={"user-agent": USER_AGENT})
        ctype = r.headers.get("content-type", "").lower()
        return not ctype or "html" in ctype
    except httpx.HTTPError:
        return True


def _summarize_map(m: dict[str, Any]) -> dict[str, Any]:
    h, im, lk, fm = m["headings"], m["images"], m["links"], m["forms"]
    return {
        "lang": m["document"]["lang"], "title": m["document"]["title"], "h1_count": h["h1_count"], "heading_level_jumps": len(h["level_jumps"]),
        "images_without_alt_attr": sum(1 for i in im["items"] if i["alt"] is None and not i["aria_label"] and i["aria_hidden"] != "true"),
        "links_without_text": lk["empty_text"], "links_same_text_other_destination": len(lk["same_text_different_destination"]),
        "fields_without_name": fm["fields_without_any_name"], "landmarks": m["landmarks"]["total"], "iframes": len(m["iframes"]),
        "reading_order_inverted_pairs": m["reading_order"]["inverted_pairs"], "hover_reveal_rules": m["hover_reveals"]["total"],
    }


async def crawl(url: str, max_pages: int = 10, level: str = "AA", browser: str = "chromium") -> dict[str, Any]:
    start = audit.validate_url(url)
    tags = audit._LEVEL_TAGS.get(level.upper())
    if tags is None:
        raise ValueError("level deve ser A, AA ou AAA")
    max_pages = max(1, min(int(max_pages), MAX_PAGES_CEILING))
    origin = f"{urlparse(start).scheme}://{urlparse(start).netloc}"
    await provisioner_for(browser).ensure()
    from playwright.async_api import async_playwright

    robots = await _robots(origin)
    queue: list[str] = [_clean(start)]
    for u in await _sitemap_urls(origin, max_pages * 3):
        if _same_site(u, origin) and _clean(u) not in queue:
            queue.append(_clean(u))
    seen: set[str] = set(queue)
    pages: list[dict[str, Any]] = []
    skipped: dict[str, list[str]] = {"robots_disallowed": [], "not_html": [], "error": []}
    script = audit.AXE_PATH.read_text(encoding="utf-8")

    async with async_playwright() as pw:
        inst = await audit._launch(pw, browser)
        try:
            ctx = await inst.new_context(accept_downloads=False)

            async def route(r: Any) -> None:  # so leitura: nada que altere dados
                await (r.continue_() if r.request.method.upper() in ("GET", "HEAD", "OPTIONS") else r.abort())

            await ctx.route("**/*", route)
            i = 0
            while i < len(queue) and len(pages) < max_pages:  # o orcamento e' o max_pages que a pessoa pediu, nao um relogio
                target = queue[i]
                i += 1
                if not robots.can_fetch(USER_AGENT, target):
                    skipped["robots_disallowed"].append(target)
                    continue
                if not await _looks_html(target):
                    skipped["not_html"].append(target)  # ex.: PDF, imagem, zip: nao e' pagina
                    continue
                page = await ctx.new_page()
                page.set_default_timeout(PAGE_TIMEOUT_MS)
                try:
                    resp = await patient(functools.partial(_goto, page, target), PAGE_TIMEOUT_MS)
                    ctype = (resp.headers.get("content-type", "") if resp else "").lower()
                    if resp and "html" not in ctype:
                        skipped["not_html"].append(target)
                        continue
                    await page.add_script_tag(content=script)
                    raw = await page.evaluate("tags => axe.run(document, {runOnly: {type: 'tag', values: tags}})", tags)
                    m = dict(await page.evaluate(js.PAGE_MAP_JS, None))
                    hrefs = await page.evaluate("() => Array.from(document.querySelectorAll('a[href]')).map(a => a.href)")
                    axe = audit.summarize_axe(raw, max_nodes=1)
                    pages.append({
                        "url": page.url, "status": resp.status if resp else None,
                        "axe_violations": [{"id": v["id"], "impact": v["impact"], "occurrences": v["occurrences"]} for v in axe["violations"]],
                        **_summarize_map(m),
                    })
                    for h in hrefs:
                        u = _clean(h)
                        if u and _same_site(u, origin) and u not in seen:
                            seen.add(u)
                            queue.append(u)
                except Exception as e:  # noqa: BLE001 - pagina que falha vira fato, nao derruba a varredura
                    skipped["error"].append(f"{target}: {type(e).__name__}: {str(e)[:60]}")
                finally:
                    await page.close()
                await asyncio.sleep(POLITE_PAUSE_S)
        finally:
            await inst.close()

    by_rule: dict[str, list[str]] = defaultdict(list)
    titles: dict[str, list[str]] = defaultdict(list)
    for p in pages:
        for v in p["axe_violations"]:
            by_rule[v["id"]].append(p["url"])
        titles[p["title"] or ""].append(p["url"])
    return {
        "start": start, "browser": browser, "level": level.upper(),
        "pages_visited": len(pages), "urls_discovered": len(seen), "not_visited": max(0, len(queue) - i),
        "pages": pages,
        "site_facts": {
            "axe_rules_by_pages": {k: {"pages": len(v), "urls": v[:8]} for k, v in sorted(by_rule.items(), key=lambda kv: -len(kv[1]))},
            "duplicate_titles": [{"title": t, "pages": len(u), "urls": u[:5]} for t, u in titles.items() if len(u) > 1],
            "pages_without_lang": [p["url"] for p in pages if not p["lang"]],
            "pages_without_title": [p["url"] for p in pages if not p["title"]],
            "pages_without_h1": [p["url"] for p in pages if p["h1_count"] == 0],
            "pages_with_several_h1": [p["url"] for p in pages if p["h1_count"] > 1],
            "pages_with_heading_jumps": [p["url"] for p in pages if p["heading_level_jumps"]],
            "images_without_alt_attr_total": sum(p["images_without_alt_attr"] for p in pages),
            "fields_without_name_total": sum(p["fields_without_name"] for p in pages),
        },
        "skipped": skipped,
        "note": "So fatos consolidados de amostra (ate max_pages), sem julgamento. Nao substitui teste como usuario nas paginas importantes.",
    }
