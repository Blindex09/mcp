"""O cadastro nos clientes: os comandos e formatos seguem o que as paginas oficiais de cada cliente documentam (conferidas em 2026-10-19)."""
import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("a11y_setup", Path(__file__).resolve().parent.parent / "scripts" / "setup.py")
setup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup)


def test_cli_commands_for_claude_code_and_codex():
    claude = setup.cli_add_command("claude")
    assert claude[:8] == ["claude", "mcp", "add", "--transport", "stdio", "--scope", "user", "accessibility"] and claude[8] == "--"
    codex = setup.cli_add_command("codex")
    assert codex[:4] == ["codex", "mcp", "add", "accessibility"] and codex[4] == "--"
    assert claude[9:] == codex[5:] == setup.LAUNCH and "mcp_server.py" in setup.LAUNCH
    with pytest.raises(ValueError):
        setup.cli_add_command("outro")


def test_vscode_snippet_uses_the_servers_key_not_the_old_settings_key():
    dado = json.loads(setup.vscode_json())
    assert list(dado) == ["servers"] and dado["servers"]["accessibility"]["type"] == "stdio" and dado["servers"]["accessibility"]["args"][0] == "--directory"
    assert "mcp.servers" not in setup.vscode_json()


def test_json_clients_merge_without_erasing_other_servers(tmp_path):
    arquivo = tmp_path / "mcp.json"
    arquivo.write_text(json.dumps({"mcpServers": {"outro": {"command": "x"}}, "extra": 1}), encoding="utf-8")
    setup._merge_mcp_servers(arquivo, "teste")
    dado = json.loads(arquivo.read_text(encoding="utf-8"))
    assert dado["extra"] == 1 and dado["mcpServers"]["outro"] == {"command": "x"} and dado["mcpServers"]["accessibility"]["command"] == "uv"
    setup._merge_mcp_servers(arquivo, "teste")  # rodar de novo nao duplica nem quebra
    assert list(json.loads(arquivo.read_text(encoding="utf-8"))["mcpServers"]) == ["outro", "accessibility"]
