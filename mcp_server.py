#!/usr/bin/env python3
"""
Accessibility MCP Server.

Servidor MCP somente de acessibilidade web e mobile: guias (WCAG 2.2, ARIA, NVDA, IA
conversacional acessivel, mobile, frameworks), exemplos de componentes acessiveis e
ferramentas de medicao (contraste, axe-core, arvore de acessibilidade, ordem de foco).

Todo julgamento (qual guia serve a uma tarefa) e feito por modelo - o do cliente via MCP
sampling ou um modelo de apoio configurado por ambiente (ver llm.py) - nunca por
palavra-chave, regex ou ranking lexical. As ferramentas de medicao so reportam fatos.
"""

import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from mcp.server.fastmcp import FastMCP

from a11y.provisioning import PROVISIONER
from a11y.session import SESSION
from a11y.tools import register as register_a11y

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
        "1) KNOWLEDGE: a11y_find(task) picks guides/examples by meaning; a11y_get_reference / a11y_get_example / "
        "a11y_get_template read them. Start with the guides component-identity-guide, ux-persona-testing and "
        "design-language-review. "
        "2) TEST LIKE A USER: a11y_open(url|html, persona) starts a persistent session (personas are enforced: "
        "keyboard and screen_reader have no mouse); a11y_dossier gives FACTS about every interactive element so YOU "
        "decide what each really is in that site's context; a11y_act / a11y_reach / a11y_announce probe behavior and "
        "report the effect; a11y_stress checks reflow and text spacing; a11y_close ends it. "
        "3) DESIGN: a11y_design_tokens measures the site's own design language; a11y_screenshot and a11y_preview_css "
        "let you try a change temporarily before recommending it, inside the site's scale. "
        "COVERAGE: a11y_page_map gives FACTS about ALL content (headings, images, links, forms, tables, media, iframes, reading order, hover rules), and the dossier crosses Shadow DOM and iframes; a11y_coverage lists what was and was NOT covered (always include it in reports); a11y_crawl scans several pages of a site (facts only, robots.txt respected, GET only). SAFETY: on non-local sites, requests that change data (POST/PUT/PATCH/DELETE, form submits) are blocked and reported unless allow_mutations=allow. "
        "AUTONOMOUS: a11y_walkthrough(task, persona) and a11y_review(focus) run a model as the user (with screenshots) and return a report; a11y_close interrupts; a11y_status shows browser/model readiness. "
        "BROWSERS: pass browser=chromium|firefox|webkit (chromium is the most precise; the others list their limits); a11y_compare_browsers shows the same page side by side. "
        "4) QUICK CHECKS without a session: a11y_audit (axe-core), a11y_aria_snapshot, a11y_tab_order, a11y_contrast. "
        "The tools report facts and never classify; judging and reporting is yours. Always state what was NOT verified "
        "(real screen readers, real devices, untested flows)."
    ),
)

register_a11y(mcp)


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
