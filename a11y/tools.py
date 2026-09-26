"""Ferramentas MCP de acessibilidade (conteudo embutido + auditoria automatizada)."""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import Context

from llm import NO_MODEL_HELP, ask_model, extract_json

from . import audit
from .compare import compare_browsers
from .content_index import ContentIndex
from .crawl import crawl
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

    @mcp.tool()
    async def a11y_list_content() -> str:
        """Catalog of the built-in accessibility knowledge base. Each item has a name, kind
        (reference guide, component example, template file or script), a plain-language "quando_usar" description and, for guides, its section headings.
        Read the catalog and CHOOSE what fits the task, then open it with a11y_get_reference
        a11y_get_example or a11y_get_template. Covers ARIA, WCAG audit checklists, NVDA/VoiceOver testing,
        AI-chat/agent UI accessibility, mobile, frameworks, and ready-made accessible
        components (modal, tabs, combobox, treegrid, ...)."""
        return _json(get_index().catalog())

    @mcp.tool()
    async def a11y_find(task: str, ctx: Context) -> str:  # type: ignore[type-arg]
        """Ask the model to pick which accessibility references/examples fit a task, described
        in plain language (any language, no keywords needed). Selection is done by the
        client's model via MCP sampling (or a configured fallback model) over the full
        catalog - not by keyword matching. If neither exists, the catalog is returned so
        the calling model can choose itself."""
        catalog = get_index().catalog()
        prompt = (
            "You route accessibility work. Given the task and the catalog, pick the items "
            "(at most 6, most useful first) a developer should read. Judge by meaning and "
            "intent, not by shared words. Answer ONLY with a JSON array of catalog names.\n\n"
            f"TASK:\n{task}\n\nCATALOG:\n{_json(catalog)}"
        )
        raw = await ask_model(ctx, prompt, max_tokens=400, tier="fast")  # escolher guias e' tarefa leve
        names = extract_json(raw, "array")
        if not isinstance(names, list):  # sem sampling ou resposta ilegivel: o modelo chamador escolhe
            return _json(
                {"selection": "unavailable", "note": f"{NO_MODEL_HELP} Escolha pelo catalogo abaixo.", "catalog": catalog}
            )
        valid = {(c["kind"], c["name"]) for c in catalog}
        picked = [c for c in catalog if c["name"] in names and (c["kind"], c["name"]) in valid]
        return _json({"selection": "model", "items": picked})

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
    async def a11y_audit(url: str = "", html: str = "", level: str = "AA", browser: str = "chromium") -> str:
        """Run an automated axe-core WCAG audit in headless Chromium. Provide EITHER url
        (http/https only) OR html (a full HTML string). level: A | AA | AAA. browser: chromium | firefox | webkit (installed automatically on first use).
        Returns violations sorted by impact, items needing manual review, and pass count.
        Automated checks catch only part of WCAG - always follow up with keyboard and
        screen-reader testing (see a11y_get_reference "audit-checklist")."""
        try:
            return _json(await audit.run_axe(url or None, html or None, level, browser))
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
    async def a11y_tab_order(url: str = "", html: str = "", max_steps: int = 60, browser: str = "chromium") -> str:
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
    async def a11y_crawl(url: str, max_pages: int = 10, level: str = "AA", browser: str = "chromium") -> str:
        """Scan SEVERAL pages of the same site and return consolidated FACTS (no judgment): axe violations per page and per
        rule, page-map summaries (lang, title, h1 count, heading jumps, images without alt, links without text, unnamed fields,
        landmarks, reading order), duplicate titles, pages missing lang/title/h1. Discovers URLs from sitemap.xml plus
        same-site links; respects robots.txt; GET only (anything that would change data is blocked); polite pause; max 30 pages.
        A sample, not a substitute for testing important flows like a user (a11y_open / a11y_walkthrough). url: http/https start page."""
        try:
            return _json(await crawl(url, max_pages, level, browser))
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
