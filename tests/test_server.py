"""Integration and startup smoke-tests for mcp_server."""
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path
from types import ModuleType

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

LAUNCHER_PATH = Path(__file__).resolve().parent.parent / "mcp_server.py"  # ponto de entrada do cliente
SERVER_PATH = Path(__file__).resolve().parent.parent / "accessibility_mcp" / "server.py"


def _load_module() -> ModuleType:
    """Import mcp_server without running main()."""
    spec = importlib.util.spec_from_file_location("mcp_server_fresh", SERVER_PATH)
    assert spec is not None
    assert spec.loader is not None
    mod: ModuleType = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ---------------------------------------------------------------------------
# Module-level import tests
# ---------------------------------------------------------------------------


def test_module_imports_cleanly() -> None:
    """mcp_server.py must import without exceptions."""
    mod = _load_module()
    assert mod is not None


def test_server_identity_and_instructions() -> None:
    mod = _load_module()
    assert mod.mcp.name == "accessibility"
    assert callable(mod.main)
    assert "never calls a model" in mod.mcp.instructions and "a11y_list_content" in mod.mcp.instructions


async def test_server_exposes_only_accessibility_tools() -> None:
    mod = _load_module()
    names = {t.name for t in await mod.mcp.list_tools()}
    assert names == {
        # conhecimento e escolha
        "a11y_list_content", "a11y_workflow", "a11y_get_reference", "a11y_get_example", "a11y_get_template",
        # medicao de fatos (sem sessao)
        "a11y_contrast", "a11y_audit", "a11y_aria_snapshot", "a11y_tab_order",
        # teste como usuario (sessao persistente)
        "a11y_open", "a11y_close", "a11y_dossier", "a11y_observe", "a11y_act", "a11y_reach",
        "a11y_announce", "a11y_screenshot", "a11y_design_tokens", "a11y_preview_css", "a11y_stress", "a11y_focus_style",
        # diagnostico, cobertura, aprovacao e aprendizado (o modelo e o do cliente; o servidor nao chama modelo)
        "a11y_nvda_speech", "a11y_status", "a11y_compare_browsers", "a11y_page_map", "a11y_coverage", "a11y_crawl", "a11y_approve", "a11y_learnings", "a11y_learn", "a11y_forget",
        # editor de arquivos do projeto da pessoa
        "a11y_set_workspace", "a11y_read_file", "a11y_edit_file", "a11y_approve_edit", "a11y_undo_edit",
        # sondas de comportamento, achados com evidencia, execucoes salvas
        "a11y_probe", "a11y_check_page", "a11y_finding", "a11y_trace", "a11y_report", "a11y_runs", "a11y_export", "a11y_diff",
    }
    assert not any("skill" in n for n in names)
    # nenhuma ferramenta depende de modelo: as de antes (busca por modelo, usuario autonomo, revisao autonoma) nao existem mais
    assert not names & {"a11y_find", "a11y_walkthrough", "a11y_review"}


async def test_the_workflows_are_mcp_prompts_for_the_clients_own_model() -> None:
    mod = _load_module()
    nomes = {p.name for p in await mod.mcp.list_prompts()}
    assert nomes == {"a11y_review", "a11y_walkthrough", "a11y_component", "a11y_site_scan", "a11y_compare_runs", "a11y_write_accessible_code"}
    texto = (await mod.mcp.get_prompt("a11y_walkthrough", {"url": "http://exemplo.test", "task": "comprar um item", "persona": "screen_reader"})).messages[0].content.text
    assert "comprar um item" in texto and "screen_reader" in texto and "testing-playbook-for-ai" in texto
    assert "NOT verified" in texto and "Never answer a11y_approve" in texto  # as regras do que pode e nao pode acompanham todo fluxo


# ---------------------------------------------------------------------------
# Process / startup smoke-test
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_server_starts_and_does_not_crash() -> None:
    """Spawn the MCP server process and verify it stays alive for 2 seconds.

    The server listens on stdin/stdout (MCP stdio transport), so it idles
    waiting for input and must NOT exit immediately.
    """
    proc = subprocess.Popen(
        [sys.executable, str(LAUNCHER_PATH)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        time.sleep(2.0)
        exit_code = proc.poll()
        assert exit_code is None, (
            f"Server process exited prematurely with code {exit_code}.\n"
            f"Stderr: {proc.stderr.read().decode(errors='replace') if proc.stderr else ''}"
        )
    finally:
        proc.kill()
        proc.wait()


async def test_the_same_workflows_are_also_a_tool_for_clients_without_mcp_prompts() -> None:
    """Paridade entre clientes: o que o prompt do MCP entrega tambem sai por uma ferramenta (alguns clientes nao mostram prompts)."""
    mod = _load_module()
    call = mod.mcp._tool_manager.get_tool("a11y_workflow").fn
    argumentos = {
        "a11y_review": {"url": "http://x.test"}, "a11y_walkthrough": {"url": "http://x.test", "task": "t"}, "a11y_component": {"url": "http://x.test", "selector": "#a"},
        "a11y_site_scan": {"url": "http://x.test"}, "a11y_compare_runs": {"base_run_id": "b", "head_run_id": "h"}, "a11y_write_accessible_code": {"task": "t"},
    }
    for nome, args in argumentos.items():
        pronto = (await mod.mcp.get_prompt(nome, args)).messages[0].content.text
        assert await call(name=nome, **args) == pronto, nome
    erro = json.loads(await call(name="nao-existe"))
    assert "fluxo invalido" in erro["error"] and "a11y_review" in erro["available"]
    assert "precisa de: url, task" in json.loads(await call(name="a11y_walkthrough"))["error"]
