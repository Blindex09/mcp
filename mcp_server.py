#!/usr/bin/env python3
"""
Accessibility MCP Server.

Servidor MCP somente de acessibilidade web e mobile: guias (WCAG 2.2, ARIA, NVDA, IA
conversacional acessivel, mobile, frameworks), exemplos de componentes acessiveis e
ferramentas de medicao (contraste, axe-core, arvore de acessibilidade, ordem de foco).

Todo julgamento (qual guia serve a uma tarefa) e feito por modelo - o do cliente via MCP
sampling ou um modelo de apoio configurado por ambiente (ver sampling.py) - nunca por
palavra-chave, regex ou ranking lexical. As ferramentas de medicao so reportam fatos.
"""

import logging
import sys

from mcp.server.fastmcp import FastMCP

from a11y.tools import register as register_a11y

# Logging so em stderr (stdout e' o canal do protocolo MCP)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

mcp = FastMCP(
    "accessibility",
    instructions=(
        "Accessibility server (WCAG 2.2, ARIA, screen readers, mobile, accessible AI/agent UIs). "
        "Workflow: 1) a11y_find(task) lets the model pick the right guides/examples for a task, "
        "or a11y_list_content() shows the whole catalog; "
        "2) a11y_get_reference(name) / a11y_get_example(name) to read them; "
        "3) measure with a11y_audit (axe-core), a11y_aria_snapshot (accessibility tree), "
        "a11y_tab_order (keyboard focus) and a11y_contrast. "
        "Automated checks cover only part of WCAG: keyboard, screen-reader and touch testing stay manual."
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
