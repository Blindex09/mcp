"""Ferramentas MCP de acessibilidade (conteudo embutido + auditoria automatizada)."""

from __future__ import annotations

import json
from typing import Any

from . import audit
from .content_index import ContentIndex

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

    @mcp.tool()
    async def a11y_list_content() -> str:
        """List the built-in accessibility knowledge base: reference guides (ARIA, WCAG
        audit checklist, NVDA testing, AI-chat a11y, mobile, frameworks) and ready-made
        accessible component examples (modal, tabs, combobox, treegrid, ...).
        Start here, then use a11y_search or a11y_get_reference / a11y_get_example."""
        idx = get_index()
        return _json({"references": sorted(idx.references), "examples": sorted(idx.examples)})

    @mcp.tool()
    async def a11y_search(query: str, kind: str = "all", top_k: int = 8) -> str:
        """Semantic (BM25) search over the accessibility references and examples.
        query: what you need, e.g. "modal focus trap", "live region announcements", "NVDA table".
        kind: "all" | "reference" | "example" | "skill". Returns ranked snippets with the
        file name to open via a11y_get_reference / a11y_get_example."""
        if kind not in ("all", "reference", "example", "skill"):
            return _json({"error": "kind deve ser all, reference, example ou skill"})
        hits = get_index().search(query, kind=kind, top_k=top_k)
        return _json(
            [
                {
                    "score": round(s, 2),
                    "kind": c.kind,
                    "name": c.name,
                    "section": c.heading,
                    "snippet": c.text.strip()[:300],
                }
                for s, c in hits
            ]
        )

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
    async def a11y_contrast(foreground: str, background: str, size_px: float = 16, bold: bool = False) -> str:
        """Check WCAG 2.2 color contrast between two hex colors (#rgb or #rrggbb).
        Returns the ratio and AA/AAA pass/fail for text (size-aware) and UI components."""
        try:
            return _json(audit.contrast_report(foreground, background, size_px, bold))
        except ValueError as e:
            return _error(e)

    @mcp.tool()
    async def a11y_audit(url: str = "", html: str = "", level: str = "AA") -> str:
        """Run an automated axe-core WCAG audit in headless Chromium. Provide EITHER url
        (http/https only) OR html (a full HTML string). level: A | AA | AAA.
        Returns violations sorted by impact, items needing manual review, and pass count.
        Automated checks catch only part of WCAG - always follow up with keyboard and
        screen-reader testing (see a11y_get_reference "audit-checklist")."""
        try:
            return _json(await audit.run_axe(url or None, html or None, level))
        except Exception as e:  # noqa: BLE001 - fronteira da ferramenta: devolve erro ao cliente
            return _error(e)

    @mcp.tool()
    async def a11y_aria_snapshot(url: str = "", html: str = "") -> str:
        """Return the page's accessibility tree (roles, accessible names, states) as YAML,
        i.e. what a screen reader is given. Provide EITHER url (http/https) OR html.
        Use to compare visible content with computed names and spot duplicated or missing semantics."""
        try:
            return _clip(await audit.aria_snapshot(url or None, html or None))
        except Exception as e:  # noqa: BLE001 - fronteira da ferramenta: devolve erro ao cliente
            return _error(e)

    @mcp.tool()
    async def a11y_tab_order(url: str = "", html: str = "", max_steps: int = 60) -> str:
        """Press Tab repeatedly and report the keyboard focus order: element, role, accessible
        name, visibility and whether a focus indicator is present. Provide EITHER url (http/https)
        OR html. Useful to detect keyboard traps, illogical order, and invisible focus."""
        try:
            return _json(await audit.tab_order(url or None, html or None, max_steps))
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
