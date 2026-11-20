"""Ferramentas sob demanda: o inicio lista so o nucleo; o resto aparece quando a conversa pede, e nada deixa de existir."""

import json
import os
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent.parent


async def test_start_lists_only_the_core_and_find_tools_activates_the_rest(tmp_path):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "A11Y_MCP_HOME": str(tmp_path / "home"), "A11Y_MCP_DOCUMENTS_DIR": str(tmp_path / "docs")}
    env.pop("A11Y_MCP_LAZY_TOOLS", None)
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "mcp_server.py")], env=env)
    async with stdio_client(params) as (reader, writer), ClientSession(reader, writer) as session:
        await session.initialize()
        start = await session.list_tools()
        names = {t.name for t in start.tools}
        assert names == {"a11y_find_tools", "a11y_call", "a11y_open", "a11y_close", "a11y_status"}
        assert len(json.dumps([t.model_dump() for t in start.tools])) < 15_000  # antes: ~94 KB
        found = json.loads((await session.call_tool("a11y_find_tools", {"query": "create report xlsx"})).content[0].text)
        assert "a11y_create_report" in found["ativadas"] and found["ferramentas"][0]["input_schema"]
        assert "a11y_create_report" in {t.name for t in (await session.list_tools()).tools}
        # clientes que nao atualizam a lista chamam pelo nome
        called = json.loads((await session.call_tool("a11y_call", {"name": "a11y_list_content", "arguments": {"kind": "template"}})).content[0].text)
        assert called
        bad = json.loads((await session.call_tool("a11y_call", {"name": "nao_existe"})).content[0].text)
        assert "error" in bad


async def test_every_tool_is_still_registered_and_reachable_by_search():
    from accessibility_mcp.a11y import lazy_tools
    from accessibility_mcp.server import mcp

    everything = [t for t in await mcp.list_tools() if t.name not in lazy_tools.CORE]
    assert len(everything) > 50
    for query, expected in (("nvda speech", "a11y_nvda_speech"), ("contrast ratio", "a11y_contrast"), ("verify code", "a11y_verify_code"), ("tab order", "a11y_tab_order"), ("crawl site pages", "a11y_crawl")):
        assert expected in [t.name for t in lazy_tools.rank(query, everything)], query
    assert [t.name for t in lazy_tools.rank("a11y_dossier,a11y_act", everything)] == ["a11y_dossier", "a11y_act"]


@pytest.mark.parametrize("value", ["0", "false", "off"])
def test_lazy_mode_can_be_turned_off(monkeypatch, value):
    from accessibility_mcp.a11y import lazy_tools

    monkeypatch.setenv("A11Y_MCP_LAZY_TOOLS", value)
    assert lazy_tools.enabled() is False
