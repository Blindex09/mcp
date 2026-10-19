#!/usr/bin/env python3
"""
Accessibility MCP Server.

Servidor MCP somente de acessibilidade web e mobile: guias (WCAG 2.2, ARIA, NVDA, IA
conversacional acessivel, mobile, frameworks), exemplos de componentes acessiveis e
ferramentas de medicao (contraste, axe-core, arvore de acessibilidade, ordem de foco).

Este servidor NAO chama modelo e nao precisa de chave: o modelo e' o do cliente que o usa
(Claude Code, Codex, VS Code, Cursor...). Todo julgamento (qual guia serve, o que um elemento e,
o que corrigir) e' do modelo do cliente, nunca de palavra-chave, regex ou ranking lexical.
As ferramentas so medem fatos; os prompts do MCP (prompts.py) trazem fluxos prontos de trabalho.
"""

import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from mcp.server.fastmcp import FastMCP

from accessibility_mcp.a11y.prompts import register_prompts
from accessibility_mcp.a11y.provisioning import PROVISIONER
from accessibility_mcp.a11y.session import SESSION
from accessibility_mcp.a11y.tools import register as register_a11y
from accessibility_mcp.telemetry import instrument

# Logging so em stderr (stdout e' o canal do protocolo MCP)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_server: Any) -> AsyncIterator[dict[str, Any]]:
    """Ao iniciar, deixa o navegador pronto em segundo plano; ao encerrar, fecha a sessao aberta."""
    PROVISIONER.start_background()
    try:
        yield {}
    finally:
        await SESSION.close()


mcp = FastMCP(
    "accessibility",
    lifespan=lifespan,
    instructions=(
        "Accessibility server (WCAG 2.2, ARIA, screen readers, mobile, accessible AI/agent UIs). "
        "A green automated audit does NOT mean accessible: test like a user. "
        "This server never calls a model: YOU (the client model) judge; the tools measure facts. "
        "1) KNOWLEDGE: a11y_list_content gives the catalog (read the descriptions and choose by meaning); a11y_get_reference / a11y_get_example / "
        "a11y_get_template read the items. Start with the guides testing-playbook-for-ai, component-behavior-matrix, component-identity-guide, "
        "ux-persona-testing and design-language-review. Ready-made workflows are available as MCP prompts (a11y_review, a11y_walkthrough, a11y_component, "
        "a11y_site_scan, a11y_compare_runs, a11y_write_accessible_code). "
        "2) TEST LIKE A USER: a11y_open(url|html, persona) starts a persistent session (personas are enforced: "
        "keyboard and screen_reader have no mouse); a11y_dossier gives FACTS about every interactive element so YOU "
        "decide what each really is in that site's context; a11y_act / a11y_reach / a11y_announce probe behavior and "
        "report the effect; a11y_stress checks reflow and text spacing; a11y_close ends it. "
        "3) DESIGN: a11y_design_tokens measures the site's own design language; a11y_screenshot and a11y_preview_css "
        "let you try a change temporarily before recommending it, inside the site's scale. "
        "COVERAGE: a11y_page_map gives FACTS about ALL content (headings, images, links, forms, tables, media, iframes, reading order, hover rules), and the dossier crosses Shadow DOM and iframes; a11y_coverage lists what was and was NOT covered (always include it in reports); a11y_crawl scans several pages of a site (facts only, robots.txt respected, GET only). APPROVAL (never a flat refusal): on non-local sites, requests that change data (POST/PUT/PATCH/DELETE, form submits) are HELD and shown (method, URL, field names, never values) until the person answers via a11y_approve; local dev sites run with approval off; allow_mutations=auto|ask|allow|block. FINDINGS: a11y_finding records a problem with WCAG criterion and evidence (trace steps); a11y_report exports JSON, EARL or SARIF and keeps the run; a11y_runs / a11y_export / a11y_diff list, export and compare saved runs. LEARNING: a11y_learn saves a lesson for future sessions (a11y_learnings / a11y_forget list and remove). a11y_close also interrupts a long operation; a11y_status shows browser readiness. "
        "BROWSERS: pass browser=chromium|firefox|webkit (chromium is the most precise; the others list their limits); a11y_compare_browsers shows the same page side by side. "
        "4) ONE CALL (clients that cannot keep a session between calls): a11y_check_page(url, probes) opens a throwaway session, measures the keyboard behavior, runs the probes and closes. 5) QUICK CHECKS without a session: a11y_audit (axe-core), a11y_aria_snapshot, a11y_tab_order, a11y_contrast. "
        "The tools report facts and never classify; judging and reporting is yours. Always state what was NOT verified "
        "(real screen readers, real devices, untested flows)."
    ),
)

instrument(mcp)  # cada ferramenta registrada daqui em diante vira um span (sem args nem resultados)
register_a11y(mcp)
register_prompts(mcp)


def main() -> None:
    """Inicia o servidor MCP via stdio."""
    try:
        logger.info("Iniciando Accessibility MCP Server...")
        mcp.run(transport="stdio")
    except Exception:
        logger.exception("Erro fatal no servidor")
        sys.exit(1)


if __name__ == "__main__":
    main()
