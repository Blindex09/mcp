from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar

import httpx
import pytest
import uvicorn
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.server.fastmcp import FastMCP

from accessibility_mcp.a11y.interop import (
    InteropError,
    InteropManager,
    _remote_httpx_client,
)

ROOT = Path(__file__).resolve().parent.parent


class A2AHandler(BaseHTTPRequestHandler):
    messages: ClassVar[list[dict[str, Any]]] = []

    def do_GET(self) -> None:
        if self.path != "/.well-known/agent-card.json":
            self.send_error(404)
            return
        self._send_json({"name": "agent-test", "description": "Dado remoto não confiável"})

    def do_POST(self) -> None:
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        A2AHandler.messages.append(payload)
        self._send_json({
            "jsonrpc": "2.0",
            "id": payload["id"],
            "result": {"taskId": payload.get("params", {}).get("id", "created")},
        })

    def _send_json(self, value: dict[str, Any]) -> None:
        body = json.dumps(value).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *args: object) -> None:
        return


def _start_http_server() -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", 0), A2AHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


@pytest.mark.asyncio
async def test_remote_http_clients_have_idle_timeouts_and_allow_overrides() -> None:
    client = _remote_httpx_client()
    try:
        assert client.timeout.connect == 10
        assert client.timeout.read == 30
        assert client.timeout.write == 30
        assert client.timeout.pool == 30
    finally:
        await client.aclose()

    override = httpx.Timeout(8, connect=2)
    client = _remote_httpx_client(timeout=override)
    try:
        assert client.timeout == override
    finally:
        await client.aclose()


async def _start_remote_mcp_server() -> tuple[uvicorn.Server, threading.Thread, str, list[str]]:
    remote = FastMCP("remote-test")
    calls: list[str] = []

    @remote.tool()
    async def echo_accessibility_fact(value: str) -> str:
        calls.append(value)
        return f"Recebido: {value}"

    config = uvicorn.Config(remote.streamable_http_app(), host="127.0.0.1", port=0, log_level="critical")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        await asyncio.sleep(0)
    port = server.servers[0].sockets[0].getsockname()[1]
    return server, thread, f"http://127.0.0.1:{port}/mcp", calls


@pytest.mark.asyncio
async def test_remote_mcp_uses_streamable_http_and_requires_exact_approval() -> None:
    remote_server, thread, endpoint, calls = await _start_remote_mcp_server()
    manager = InteropManager(allow_private_network=True)
    try:
        connected = await manager.connect_mcp("remote", endpoint)
        server_id = connected["server_id"]
        tools = await manager.list_mcp_tools(server_id)
        assert tools["untrusted_remote_content"] is True
        assert tools["tools"][0]["name"] == "echo_accessibility_fact"

        with pytest.raises(InteropError, match="não correspondem"):
            await manager.prepare_mcp_call(server_id, "echo_accessibility_fact", {})
        assert manager.pending == {}

        held = await manager.prepare_mcp_call(server_id, "echo_accessibility_fact", {"value": "fato"})
        assert held["approval_required"] is True
        assert held["exact_request_to_send"]["arguments_to_send"] == {"value": "fato"}
        assert calls == []

        denied = await manager.decide(held["approval_id"], "deny")
        assert denied["sent"] is False
        assert calls == []

        approved = await manager.prepare_mcp_call(server_id, "echo_accessibility_fact", {"value": "confirmado"})
        result = await manager.decide(approved["approval_id"], "allow")
        assert result["sent"] is True
        assert calls == ["confirmado"]
        assert result["result"]["result"]["content"][0]["text"] == "Recebido: confirmado"

        pending = await manager.prepare_mcp_call(server_id, "echo_accessibility_fact", {"value": "cancelar"})
        manager.disconnect_mcp(server_id)
        with pytest.raises(InteropError, match="não encontrado"):
            await manager.decide(pending["approval_id"], "allow")
    finally:
        remote_server.should_exit = True
        await asyncio.to_thread(thread.join)


@pytest.mark.asyncio
async def test_a2a_agent_card_and_json_rpc_messages_use_http_approval() -> None:
    A2AHandler.messages = []
    server = _start_http_server()
    endpoint = f"http://127.0.0.1:{server.server_address[1]}"
    manager = InteropManager(allow_private_network=True)
    try:
        card = await manager.get_a2a_agent_card(endpoint)
        assert card["agent_card"]["name"] == "agent-test"
        assert card["untrusted_remote_content"] is True

        held_message = await manager.prepare_a2a_send(endpoint, "Solicito avaliação")
        assert held_message["approval_required"] is True
        assert A2AHandler.messages == []
        sent = await manager.decide(held_message["approval_id"], "allow")
        assert sent["result"]["result"]["taskId"] == "created"
        assert A2AHandler.messages[0]["method"] == "SendMessage"
        assert A2AHandler.messages[0]["params"]["message"]["parts"] == [{"text": "Solicito avaliação"}]

        held_task = await manager.prepare_a2a_get_task(endpoint, "task-1", history_length=2)
        assert held_task["exact_request_to_send"]["jsonrpc_request_to_send"]["params"] == {
            "id": "task-1",
            "historyLength": 2,
        }
        denied = await manager.decide(held_task["approval_id"], "deny")
        assert denied["sent"] is False
        assert len(A2AHandler.messages) == 1
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.asyncio
async def test_mcp_call_fails_closed_if_remote_tool_definition_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    remote_server, thread, endpoint, calls = await _start_remote_mcp_server()
    manager = InteropManager(allow_private_network=True)
    try:
        connected = await manager.connect_mcp("remote", endpoint)
        held = await manager.prepare_mcp_call(
            connected["server_id"],
            "echo_accessibility_fact",
            {"value": "must-not-send"},
        )

        async def changed_tools(_server_id: str) -> dict[str, Any]:
            return {"tools": [{
                "name": "echo_accessibility_fact",
                "title": None,
                "description": "Changed after approval",
                "input_schema": {},
                "annotations": None,
            }]}

        monkeypatch.setattr(manager, "list_mcp_tools", changed_tools)
        with pytest.raises(InteropError, match="mudou"):
            await manager.decide(held["approval_id"], "allow")
        assert calls == []
    finally:
        remote_server.should_exit = True
        await asyncio.to_thread(thread.join)


@pytest.mark.asyncio
async def test_remote_endpoint_security_and_disconnect_cancel_pending_actions(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = InteropManager()
    with pytest.raises(InteropError, match="rede local"):
        await manager._validate_endpoint("http://127.0.0.1:8080/mcp")

    monkeypatch.setenv("A11Y_TEST_REMOTE_TOKEN", "sensitive-value")
    with pytest.raises(InteropError, match="HTTPS"):
        manager._token("A11Y_TEST_REMOTE_TOKEN", "http")
    assert manager._headers("sensitive-value")["Authorization"].endswith("sensitive-value")

    private_manager = InteropManager(allow_private_network=True)
    assert await private_manager._validate_endpoint("http://127.0.0.1:8080/mcp") == "http://127.0.0.1:8080/mcp"


@pytest.mark.asyncio
async def test_interop_tools_are_registered_and_callable_over_the_mcp_protocol(tmp_path: Path) -> None:
    env = {
        **os.environ,
        "A11Y_MCP_HOME": str(tmp_path / "home"),
        "A11Y_MCP_AUTO_INSTALL": "0",
        "A11Y_MCP_REMOTE_ALLOW_PRIVATE": "0",
        "PYTHONIOENCODING": "utf-8",
    }
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "mcp_server.py")], env=env)
    expected = {
        "a11y_remote_mcp_connect",
        "a11y_remote_mcp_connections",
        "a11y_remote_mcp_list_tools",
        "a11y_remote_mcp_call",
        "a11y_remote_approve",
        "a11y_remote_mcp_disconnect",
        "a11y_a2a_agent_card",
        "a11y_a2a_send_message",
        "a11y_a2a_get_task",
    }
    async with stdio_client(params) as (reader, writer), ClientSession(reader, writer) as session:
        await session.initialize()
        assert expected <= {tool.name for tool in (await session.list_tools()).tools}

        async def call(name: str, arguments: dict[str, str] | None = None) -> dict[str, Any]:
            result = await session.call_tool(name, arguments or {})
            return json.loads(result.content[0].text)

        assert (await call("a11y_remote_mcp_connections"))["connections"] == []
        assert "error" in await call("a11y_remote_mcp_connect", {"name": "nome inválido", "endpoint": ""})
        assert "error" in await call("a11y_remote_mcp_list_tools", {"server_id": "missing"})
        assert "error" in await call("a11y_remote_mcp_call", {"server_id": "missing", "tool_name": "echo"})
        assert "error" in await call("a11y_remote_approve", {"approval_id": "missing", "decision": "allow"})
        assert "error" in await call("a11y_remote_mcp_disconnect", {"server_id": "missing"})
        assert "error" in await call("a11y_a2a_agent_card", {"agent_url": "http://127.0.0.1:1"})
        assert "error" in await call("a11y_a2a_send_message", {
            "endpoint": "http://127.0.0.1:1",
            "message": "mensagem",
        })
        assert "error" in await call("a11y_a2a_get_task", {
            "endpoint": "http://127.0.0.1:1",
            "task_id": "task",
        })
