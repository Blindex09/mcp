"""Integration and startup smoke-tests for mcp_server."""
import importlib.util
import subprocess
import sys
import time
from pathlib import Path
from types import ModuleType
from typing import Any

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


def test_required_callables_exist() -> None:
    """Core public functions must be present after import."""
    mod = _load_module()
    expected = [
        "find_skills",
        "classify_skills",
        "get_skills",
        "discover_skills",
        "build_category_response",
        "main",
    ]
    for name in expected:
        assert hasattr(mod, name), f"Missing callable: {name}"
        assert callable(getattr(mod, name)), f"Not callable: {name}"


def test_required_constants_exist() -> None:
    """Infrastructure constants must be defined."""
    mod = _load_module()
    assert hasattr(mod, "SKILLS_PATH"), "Missing SKILLS_PATH"
    assert hasattr(mod, "_CACHE_TTL_SECONDS"), "Missing _CACHE_TTL_SECONDS"


def test_mcp_instance_exists() -> None:
    """FastMCP instance must be exposed as `mcp`."""
    mod = _load_module()
    assert hasattr(mod, "mcp"), "Missing FastMCP instance `mcp`"


def test_mcp_instance_has_instructions() -> None:
    """FastMCP instance must be configured with instructions."""
    mod = _load_module()
    mcp_instance: Any = mod.mcp  # type: ignore[attr-defined]
    # FastMCP exposes _instructions or stores it on the underlying server
    # Check any attribute that confirms instructions were passed
    attrs = dir(mcp_instance)
    has_instructions = (
        "instructions" in attrs
        or "_instructions" in attrs
        or hasattr(getattr(mcp_instance, "_settings", None), "instructions")
        or hasattr(getattr(mcp_instance, "settings", None), "instructions")
    )
    assert has_instructions, "FastMCP instance is missing `instructions` configuration"


def test_category_rules_and_icons_aligned() -> None:
    """Every taxonomy category offered to the classifier must have an icon."""
    mod = _load_module()
    rules: dict[str, Any] = dict.fromkeys(mod.CATEGORIES)  # type: ignore[attr-defined]
    icons: dict[str, str] = mod.CATEGORY_ICONS  # type: ignore[attr-defined]
    missing = set(rules.keys()) - set(icons.keys())
    assert not missing, f"CATEGORIES missing from CATEGORY_ICONS: {missing}"


def test_skills_path_is_path_object() -> None:
    """SKILLS_PATH must be a pathlib.Path instance."""
    mod = _load_module()
    assert isinstance(mod.SKILLS_PATH, Path)


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
