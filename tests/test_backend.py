"""Modelo de apoio (clientes sem sampling): configuracao por ambiente, ordem e falhas."""
import httpx
import pytest

import mcp_server
import sampling
from tests.test_model_driven import (  # noqa: F401 - fixture reutilizada
    fake_ctx,
    skills_dir,
)


@pytest.fixture()
def calls(monkeypatch):
    """Intercepta o HTTP; devolve a lista de chamadas e um dict para escolher a resposta."""
    log: list[dict] = []
    reply: dict = {"data": {}, "error": None}

    async def fake_post(url, headers, payload):
        log.append({"url": url, "headers": headers, "payload": payload})
        if reply["error"]:
            raise reply["error"]
        return reply["data"]

    monkeypatch.setattr(sampling, "_http_post", fake_post)
    return log, reply


def test_no_backend_by_default():
    assert sampling.configured_backend() is None


def test_backend_detection(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    assert sampling.configured_backend() == "anthropic"
    monkeypatch.setenv("SKILLS_MCP_BACKEND", "ollama")
    assert sampling.configured_backend() == "ollama"
    monkeypatch.setenv("SKILLS_MCP_BACKEND", "banana")
    assert sampling.configured_backend() is None


async def test_client_sampling_has_priority_over_backend(monkeypatch, calls):
    log, _ = calls
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    ctx, _prompts = fake_ctx("resposta do cliente")
    assert await sampling.ask_model(ctx, "oi") == "resposta do cliente"
    assert log == []  # nao gastou o backend


async def test_falls_back_to_anthropic_when_client_has_no_sampling(monkeypatch, calls):
    log, reply = calls
    monkeypatch.setenv("ANTHROPIC_API_KEY", "segredo")
    monkeypatch.setenv("SKILLS_MCP_MODEL", "claude-x")
    reply["data"] = {"content": [{"type": "text", "text": '["a"]'}]}
    ctx, _ = fake_ctx(None)
    assert await sampling.ask_model(ctx, "pergunta", max_tokens=123) == '["a"]'
    call = log[0]
    assert call["url"] == sampling.ANTHROPIC_URL
    assert call["headers"]["x-api-key"] == "segredo"
    assert call["payload"] == {
        "model": "claude-x", "max_tokens": 123, "messages": [{"role": "user", "content": "pergunta"}],
    }


async def test_anthropic_default_model(monkeypatch, calls):
    log, reply = calls
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    reply["data"] = {"content": [{"type": "text", "text": "ok"}]}
    await sampling.ask_model(None, "x")
    assert log[0]["payload"]["model"] == sampling.ANTHROPIC_DEFAULT_MODEL


async def test_ollama_backend(monkeypatch, calls):
    log, reply = calls
    monkeypatch.setenv("SKILLS_MCP_BACKEND", "ollama")
    monkeypatch.setenv("SKILLS_MCP_MODEL", "llama3")
    monkeypatch.setenv("OLLAMA_HOST", "meu-host:11434")
    reply["data"] = {"message": {"content": "resposta"}}
    assert await sampling.ask_model(None, "x") == "resposta"
    assert log[0]["url"] == "http://meu-host:11434/api/chat"
    assert log[0]["payload"]["model"] == "llama3" and log[0]["payload"]["stream"] is False


async def test_ollama_without_model_returns_none(monkeypatch, calls):
    log, _ = calls
    monkeypatch.setenv("SKILLS_MCP_BACKEND", "ollama")
    assert await sampling.ask_model(None, "x") is None
    assert log == []


@pytest.mark.parametrize("error", [httpx.ConnectError("x"), httpx.ReadTimeout("t"), ValueError("json")])
async def test_backend_failure_returns_none_and_never_leaks_key(monkeypatch, calls, caplog, error):
    _, reply = calls
    monkeypatch.setenv("ANTHROPIC_API_KEY", "SEGREDO-123")
    reply["error"] = error
    assert await sampling.ask_model(None, "x") is None
    assert "SEGREDO-123" not in caplog.text


async def test_find_skills_works_via_backend_without_client_sampling(monkeypatch, calls, skills_dir):  # noqa: F811
    _, reply = calls
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    reply["data"] = {"content": [{"type": "text", "text": '["azure-deploy-agent", "inventado"]'}]}
    ctx, _ = fake_ctx(None)
    out = await mcp_server.find_skills("subir agente na nuvem", ctx)
    assert "azure-deploy-agent" in out and "inventado" not in out


async def test_no_model_anywhere_explains_how_to_configure(skills_dir):  # noqa: F811
    ctx, _ = fake_ctx(None)
    out = await mcp_server.find_skills("x", ctx)
    assert "ANTHROPIC_API_KEY" in out and "sampling" in out and "azure-deploy-agent" not in out
