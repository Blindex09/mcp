"""Integration and startup smoke-tests for mcp_server."""
import importlib.util
import subprocess
import sys
import time
from pathlib import Path
from types import ModuleType

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SERVER_PATH = Path(__file__).resolve().parent.parent / "mcp_server.py"


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
    assert "a11y_find" in mod.mcp.instructions


async def test_server_exposes_only_accessibility_tools() -> None:
    mod = _load_module()
    names = {t.name for t in await mod.mcp.list_tools()}
    assert names == {
        # conhecimento e escolha
        "a11y_list_content", "a11y_find", "a11y_get_reference", "a11y_get_example", "a11y_get_template",
        # medicao de fatos (sem sessao)
        "a11y_contrast", "a11y_audit", "a11y_aria_snapshot", "a11y_tab_order",
        # teste como usuario (sessao persistente)
        "a11y_open", "a11y_close", "a11y_dossier", "a11y_observe", "a11y_act", "a11y_reach",
        "a11y_announce", "a11y_screenshot", "a11y_design_tokens", "a11y_preview_css", "a11y_stress",
    }
    assert not any("skill" in n for n in names)


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
        [sys.executable, str(SERVER_PATH)],
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
