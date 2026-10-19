"""Regra 8: nenhum prazo ou teto fixo do codigo corta trabalho em andamento (instalacao, sessao, passos, paradas, paginas).

O que encerra e convergir, parar de avancar, repetir a mesma coisa, o cancelamento ou um orcamento que a PESSOA escolheu.
"""

import ast
import inspect
from pathlib import Path

from accessibility_mcp.a11y import (
    audit,
    crawl,
    probes,
    provisioning,
    session,
    tools_ux,
)

ROOT = Path(__file__).resolve().parent.parent / "accessibility_mcp"

# arquivo -> motivo. wait_for so aparece onde ele NAO decide o fim do trabalho.
ALLOWED_WAIT_FOR = {
    "a11y/patience.py": "repete com espera maior, nao desiste",
    "a11y/provisioning.py": "so quanto o cliente espera por uma resposta; a instalacao segue (shield)",
    "a11y/session.py": "sonda de 2 s que mede se a pagina responde enquanto assenta (agitacao), nao a duracao de uma tarefa",
}


def _wait_for_calls() -> list[str]:
    found = []
    for path in sorted(ROOT.rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        if rel in ALLOWED_WAIT_FOR:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and ast.unparse(node.func).endswith("wait_for"):
                found.append(f"{rel}:{node.lineno}")
    return found


def test_no_wait_for_with_a_deadline_outside_the_allowed_places():
    assert _wait_for_calls() == []


def test_installs_wait_for_the_command_instead_of_killing_it_on_a_clock():
    assert "timeout" not in inspect.signature(provisioning._run).parameters
    assert not hasattr(provisioning, "PIP_TIMEOUT_S") and not hasattr(provisioning, "BROWSER_TIMEOUT_S")


def test_steps_stops_pages_and_tabs_have_no_ceiling_in_the_code():
    assert not hasattr(probes, "MAX_STOPS") and not hasattr(crawl, "MAX_PAGES_CEILING")
    assert inspect.signature(audit.tab_order).parameters["max_steps"].default == 0
    assert inspect.signature(session.Session.reach).parameters["max_tabs"].default == 0
    assert inspect.signature(probes.tab_walk).parameters["max_stops"].default == 0
    assert inspect.getsource(tools_ux).count("max_steps: int = 25") == 0
