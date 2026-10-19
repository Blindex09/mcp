"""Ferramentas MCP de acessibilidade (conteudo embutido + auditoria automatizada)."""

from __future__ import annotations

import json
from typing import Any

from . import audit
from .compare import compare_browsers
from .content_index import ContentIndex
from .crawl import crawl
from .prompts import FLUXOS, workflow_text
from .tools_files import register_files
from .tools_ux import register_ux

_MAX_CHARS = 40_000
_index: ContentIndex | None = None


def get_index() -> ContentIndex:
    global _index
    if _index is None:
        _index = ContentIndex()
    return _index


def _clip(text: str, max_chars: int = _MAX_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n\n[... truncado em {max_chars} caracteres de {len(text)}]"


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _error(e: Exception) -> str:
    return _json({"error": f"{type(e).__name__}: {e}"})


def register(mcp: Any) -> None:
    """Registra as ferramentas e recursos de acessibilidade no servidor FastMCP."""
    register_ux(mcp)
    register_files(mcp)

    @mcp.tool()
    async def a11y_list_content(kind: str = "") -> str:
        """Catalog of the built-in accessibility knowledge base. Each item has a name, kind
        (reference guide, component example, template file or script), a plain-language "quando_usar" description and, for guides, its section headings.
        Read the catalog and CHOOSE what fits the task, then open it with a11y_get_reference
        a11y_get_example or a11y_get_template. Covers ARIA, WCAG audit checklists, NVDA/VoiceOver testing,
        AI-chat/agent UI accessibility, mobile, frameworks, and ready-made accessible
        components (modal, tabs, combobox, treegrid, ...).
        kind: optional, reference | example | template | script. The full catalog is large (~25 KB); ask for one kind when you already
        know whether you need a guide or a ready-made component."""
        items = get_index().catalog()
        wanted = kind.strip().lower()
        if wanted:
            kinds = sorted({i["kind"] for i in items})
            if wanted not in kinds:
                return _json({"error": f"kind invalido: {kind}", "available": kinds})
            items = [i for i in items if i["kind"] == wanted]
        return _json(items)

    @mcp.tool()
    async def a11y_workflow(
        name: str, url: str = "", task: str = "", persona: str = "keyboard", focus: str = "", selector: str = "", stack: str = "html",
        max_pages: int = 10, base_run_id: str = "", head_run_id: str = "",
    ) -> str:
        """Ready-made workflow for YOU to follow with this server's tools (the same text as the MCP prompts, for clients that do not show prompts, such as some
        Codex versions). name: a11y_review (url, focus) | a11y_walkthrough (url, task, persona) | a11y_component (url, selector) | a11y_site_scan (url, max_pages) |
        a11y_compare_runs (base_run_id, head_run_id) | a11y_write_accessible_code (task, stack). Returns instructions: which guides to read, which tools and probes to use,
        what you may and may not claim, and how to report. The server does not run the workflow and calls no model: you do."""
        try:
            return workflow_text(name, url=url, task=task, persona=persona, focus=focus, selector=selector, stack=stack, max_pages=max_pages,
                                 base_run_id=base_run_id, head_run_id=head_run_id)
        except ValueError as e:
            return _json({"error": str(e), "available": list(FLUXOS)})

    @mcp.tool()
    async def a11y_get_reference(name: str, section: str = "") -> str:
        """Read a full accessibility reference guide by name (from a11y_list_content),
        e.g. "aria-rules-dos-and-donts", "audit-checklist", "nvda-testing-guide".
        section: optional heading substring to return only that part of the guide."""
        text = get_index().read("reference", name)
        if text is None:
            return _json({"error": f"referencia nao encontrada: {name}", "available": sorted(get_index().references)})
        if section:
            from .content_index import _split_markdown

            parts = [f"## {h}\n{b}" for h, b in _split_markdown(text) if section.lower() in h.lower()]
            if not parts:
                return _json({"error": f"secao nao encontrada: {section}"})
            text = "\n\n".join(parts)
        return _clip(text)

    @mcp.tool()
    async def a11y_get_example(name: str) -> str:
        """Get the source of an accessible component example by name (from
        a11y_list_content), e.g. "modal-native-dialog", "tabs-vanilla", "combobox-react-aria"."""
        text = get_index().read("example", name)
        if text is None:
            return _json({"error": f"exemplo nao encontrado: {name}", "available": sorted(get_index().examples)})
        return _clip(text)

    @mcp.tool()
    async def a11y_get_template(name: str) -> str:
        """Get a file of the accessible AI/agent React template (assets/accessible-ai-react/...) or
        an audit script (scripts/audit-axe.js, scripts/audit-contrast.js), by the exact path shown
        in a11y_list_content, e.g. "assets/accessible-ai-react/src/ai/turnReducer.js"."""
        text = get_index().read("template", name)
        if text is None:
            return _json({"error": f"arquivo nao encontrado: {name}", "available": sorted(get_index().templates)})
        return _clip(text)

    @mcp.tool()
    async def a11y_contrast(foreground: str, background: str, size_px: float = 16, bold: bool = False) -> str:
        """Check WCAG 2.2 color contrast between two hex colors (#rgb or #rrggbb).
        Returns the ratio and AA/AAA pass/fail for text (size-aware) and UI components."""
        try:
            return _json(audit.contrast_report(foreground, background, size_px, bold))
        except ValueError as e:
            return _error(e)

    @mcp.tool()
    async def a11y_audit(url: str = "", html: str = "", level: str = "AA", browser: str = "chromium", color_scheme: str = "") -> str:
        """Run an automated axe-core WCAG audit in headless Chromium. Provide EITHER url
        (http/https only) OR html (a full HTML string). level: A | AA | AAA. browser: chromium | firefox | webkit (installed automatically on first use).
        color_scheme: light | dark (optional; emulates prefers-color-scheme, so contrast in the dark theme is audited too).
        Returns violations sorted by impact, items needing manual review, and pass count.
        Automated checks catch only part of WCAG - always follow up with keyboard and
        screen-reader testing (see a11y_get_reference "audit-checklist")."""
        try:
            return _json(await audit.run_axe(url or None, html or None, level, browser, color_scheme or None))
        except Exception as e:  # noqa: BLE001 - fronteira da ferramenta: devolve erro ao cliente
            return _error(e)

    @mcp.tool()
    async def a11y_aria_snapshot(url: str = "", html: str = "", browser: str = "chromium") -> str:
        """Return the page's accessibility tree (roles, accessible names, states) as YAML,
        i.e. what a screen reader is given. Provide EITHER url (http/https) OR html.
        Use to compare visible content with computed names and spot duplicated or missing semantics."""
        try:
            return _clip(await audit.aria_snapshot(url or None, html or None, browser))
        except Exception as e:  # noqa: BLE001 - fronteira da ferramenta: devolve erro ao cliente
            return _error(e)

    @mcp.tool()
    async def a11y_tab_order(url: str = "", html: str = "", max_steps: int = 0, browser: str = "chromium") -> str:
        """Press Tab repeatedly and report the keyboard focus order: element, role, accessible
        name, visibility and whether a focus indicator is present. Provide EITHER url (http/https)
        OR html. Useful to detect keyboard traps, illogical order, and invisible focus."""
        try:
            return _json(await audit.tab_order(url or None, html or None, max_steps, browser))
        except Exception as e:  # noqa: BLE001 - fronteira da ferramenta: devolve erro ao cliente
            return _error(e)

    @mcp.tool()
    async def a11y_compare_browsers(url: str = "", html: str = "", browsers: str = "chromium,firefox", level: str = "AA") -> str:
        """Same page in several browsers, side by side, FACTS only: accessibility-tree differences, axe violations that
        appear in only one browser, and keyboard focus order per browser. browsers: comma list of chromium, firefox,
        webkit (at least 2; missing ones are installed automatically). Provide EITHER url (http/https) OR html.
        Whether a difference is a page bug or just how each browser exposes accessibility is your judgment
        (see the guide cross-browser-a11y). Not a real screen reader."""
        try:
            names = [b.strip() for b in browsers.split(",") if b.strip()]
            return _json(await compare_browsers(url or None, html or None, names, level))
        except Exception as e:  # noqa: BLE001 - fronteira da ferramenta: devolve erro ao cliente
            return _error(e)

    @mcp.tool()
    async def a11y_crawl(url: str, max_pages: int = 10, level: str = "AA", browser: str = "chromium", color_scheme: str = "") -> str:
        """Scan SEVERAL pages of the same site and return consolidated FACTS (no judgment): axe violations per page and per
        rule, page-map summaries (lang, title, h1 count, heading jumps, images without alt, links without text, unnamed fields,
        landmarks, reading order), duplicate titles, pages missing lang/title/h1. Discovers URLs from sitemap.xml plus
        same-site links; respects robots.txt; GET only (anything that would change data is blocked); polite pause; max 30 pages.
        A sample, not a substitute for testing important flows like a user (a11y_open and the probes). url: http/https start page.
        color_scheme: light | dark (optional; audits the dark theme too)."""
        try:
            return _json(await crawl(url, max_pages, level, browser, color_scheme or None))
        except Exception as e:  # noqa: BLE001 - fronteira da ferramenta: devolve erro ao cliente
            return _error(e)

    @mcp.resource("a11y://reference/{name}")
    def a11y_reference_resource(name: str) -> str:
        """Accessibility reference guide as an MCP resource."""
        return get_index().read("reference", name) or f"referencia nao encontrada: {name}"

    @mcp.resource("a11y://example/{name}")
    def a11y_example_resource(name: str) -> str:
        """Accessible component example as an MCP resource."""
        return get_index().read("example", name) or f"exemplo nao encontrado: {name}"
