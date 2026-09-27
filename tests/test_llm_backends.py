"""Modelo do servidor: provedores diretos, visao, sem modelo padrao, ordem e falhas."""
import json

import httpx
import pytest

import llm
import mcp_server


async def _no_catalog(*_a, **_k):
    return None


@pytest.fixture()
def calls(monkeypatch):
    """Intercepta o HTTP; devolve o log de chamadas e o dict que define a resposta."""
    log: list[dict] = []
    reply: dict = {"data": {}, "error": None}

    async def fake_post(url, headers, payload):
        log.append({"url": url, "headers": headers, "payload": payload})
        if reply["error"]:
            raise reply["error"]
        return reply["data"]

    monkeypatch.setattr(llm, "_http_post", fake_post)
    return log, reply


def test_no_backend_by_default():
    assert llm.configured_backend() is None
    assert llm.backend_status()["ready"] is False


def test_backend_detection_is_configuration(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    assert llm.configured_backend() == "openai"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    assert llm.configured_backend() == "anthropic"
    monkeypatch.setenv("A11Y_MCP_BACKEND", "ollama")
    assert llm.configured_backend() == "ollama"
    monkeypatch.setenv("A11Y_MCP_BACKEND", "banana")
    assert llm.configured_backend() is None


def test_status_never_leaks_the_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "SEGREDO-123")
    monkeypatch.setenv("A11Y_MCP_MODEL", "m1")
    st = llm.backend_status()
    assert st == {
        "backend": "anthropic", "model": "m1", "model_source": "pessoa", "auto": False,
        "model_fast": None, "ready": True, "problem": None,
    }
    assert "SEGREDO-123" not in json.dumps(st)


async def test_no_hardcoded_default_falls_back_to_auto_resolution_and_gives_up_without_a_catalog(monkeypatch, calls):
    """Sem A11Y_MCP_MODEL o codigo nao tem opiniao propria sobre qual modelo usar: tenta resolver sozinho
    (models.resolve), e sem catalogo nem cliente que julgue, desiste sem chamar o provedor de chat."""
    import models

    log, _ = calls
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")  # chave sem modelo escolhido
    monkeypatch.setattr(models, "fetch_catalog", _no_catalog)
    assert await llm.ask_model(None, "x") is None
    assert log == []
    st = llm.backend_status()
    assert st["auto"] is True and st["model"] is None and st["ready"] is False  # sem modelo fixo AINDA
    assert st["problem"] is None  # nao e um erro: a proxima chamada de verdade pode resolver sozinha


async def test_direct_provider_has_priority_over_client_sampling(monkeypatch, calls, fake_ctx):
    log, reply = calls
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setenv("A11Y_MCP_MODEL", "m1")
    reply["data"] = {"content": [{"type": "text", "text": "do provedor"}]}
    ctx, prompts = fake_ctx("do cliente")
    assert await llm.ask_model(ctx, "oi") == "do provedor"
    assert prompts == [] and len(log) == 1


async def test_client_sampling_is_the_bonus_when_no_backend(fake_ctx):
    ctx, _ = fake_ctx("do cliente")
    assert await llm.ask_model(ctx, "oi") == "do cliente"


async def test_falls_back_to_client_when_provider_fails(monkeypatch, calls, fake_ctx):
    _, reply = calls
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setenv("A11Y_MCP_MODEL", "m1")
    reply["error"] = httpx.ConnectError("x")
    ctx, _ = fake_ctx("do cliente")
    assert await llm.ask_model(ctx, "oi") == "do cliente"


async def test_anthropic_request_shape_with_image(monkeypatch, calls):
    log, reply = calls
    monkeypatch.setenv("ANTHROPIC_API_KEY", "segredo")
    monkeypatch.setenv("A11Y_MCP_MODEL", "claude-x")
    reply["data"] = {"content": [{"type": "text", "text": '["a"]'}]}
    assert await llm.ask_model(None, "pergunta", max_tokens=123, images=[b"\xff\xd8img"]) == '["a"]'
    call = log[0]
    assert call["url"] == llm.ANTHROPIC_URL and call["headers"]["x-api-key"] == "segredo"
    body = call["payload"]
    assert body["model"] == "claude-x" and body["max_tokens"] == 123
    blocks = body["messages"][0]["content"]
    assert blocks[0]["type"] == "image" and blocks[0]["source"]["media_type"] == "image/jpeg"
    assert blocks[-1] == {"type": "text", "text": "pergunta"}


async def test_openai_request_shape_text_and_image(monkeypatch, calls):
    log, reply = calls
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setenv("A11Y_MCP_MODEL", "gpt-x")
    reply["data"] = {"choices": [{"message": {"content": "ok"}}]}
    assert await llm.ask_model(None, "texto") == "ok"
    assert log[0]["url"] == "https://api.openai.com/v1/chat/completions"
    assert log[0]["headers"]["authorization"] == "Bearer k"
    assert log[0]["payload"]["messages"][0]["content"] == "texto"
    await llm.ask_model(None, "texto", images=[b"img"])
    parts = log[1]["payload"]["messages"][0]["content"]
    assert parts[0]["type"] == "text" and parts[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


async def test_openai_compatible_needs_valid_base_url(monkeypatch, calls):
    log, reply = calls
    monkeypatch.setenv("A11Y_MCP_BACKEND", "openai-compatible")
    monkeypatch.setenv("A11Y_MCP_MODEL", "m")
    assert await llm.ask_model(None, "x") is None  # sem base url
    monkeypatch.setenv("A11Y_MCP_BASE_URL", "file:///etc/passwd")
    assert await llm.ask_model(None, "x") is None  # esquema invalido
    assert log == []
    monkeypatch.setenv("A11Y_MCP_BASE_URL", "http://localhost:1234/v1/")
    reply["data"] = {"choices": [{"message": {"content": "local"}}]}
    assert await llm.ask_model(None, "x") == "local"
    assert log[0]["url"] == "http://localhost:1234/v1/chat/completions"
    assert "authorization" not in log[0]["headers"]  # servidor local sem chave


async def test_ollama_backend_with_image(monkeypatch, calls):
    log, reply = calls
    monkeypatch.setenv("A11Y_MCP_BACKEND", "ollama")
    monkeypatch.setenv("A11Y_MCP_MODEL", "llava")
    monkeypatch.setenv("OLLAMA_HOST", "meu-host:11434")
    reply["data"] = {"message": {"content": "resposta"}}
    assert await llm.ask_model(None, "x", images=[b"i"]) == "resposta"
    assert log[0]["url"] == "http://meu-host:11434/api/chat"
    assert log[0]["payload"]["model"] == "llava" and log[0]["payload"]["messages"][0]["images"]


@pytest.mark.parametrize("error", [httpx.ConnectError("x"), httpx.ReadTimeout("t"), ValueError("json")])
async def test_failure_returns_none_and_never_leaks_key(monkeypatch, calls, caplog, error):
    _, reply = calls
    monkeypatch.setenv("ANTHROPIC_API_KEY", "SEGREDO-123")
    monkeypatch.setenv("A11Y_MCP_MODEL", "m")
    reply["error"] = error
    assert await llm.ask_model(None, "x") is None
    assert "SEGREDO-123" not in caplog.text


async def test_a11y_find_works_via_provider_without_client_sampling(monkeypatch, calls, fake_ctx):
    _, reply = calls
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setenv("A11Y_MCP_MODEL", "m")
    reply["data"] = {"content": [{"type": "text", "text": '["modal-native-dialog", "inventado"]'}]}
    ctx, _ = fake_ctx(None)
    tool = mcp_server.mcp._tool_manager.get_tool("a11y_find")
    data = json.loads(await tool.fn(task="dialogo modal", ctx=ctx))
    assert data["selection"] == "model"
    assert [i["name"] for i in data["items"]] == ["modal-native-dialog"]


async def test_no_model_anywhere_explains_how_to_configure(fake_ctx):
    ctx, _ = fake_ctx(None)
    tool = mcp_server.mcp._tool_manager.get_tool("a11y_find")
    data = json.loads(await tool.fn(task="x", ctx=ctx))
    assert data["selection"] == "unavailable"
    assert "A11Y_MCP_MODEL" in data["note"] and data["catalog"]


async def test_ollama_cloud_sends_the_key_as_bearer_and_defaults_to_the_cloud_host(monkeypatch, calls):
    """Ollama Cloud: https://ollama.com/api com Authorization Bearer (OLLAMA_API_KEY); so a chave basta para escolher o backend."""
    log, reply = calls
    monkeypatch.setenv("OLLAMA_API_KEY", "SEGREDO-NUVEM")
    monkeypatch.setenv("A11Y_MCP_MODEL", "gemma4:31b")
    assert llm.configured_backend() == "ollama"
    assert llm.backend_status()["ready"] is True
    reply["data"] = {"message": {"content": "resposta"}}
    assert await llm.ask_model(None, "x") == "resposta"
    assert log[0]["url"] == "https://ollama.com/api/chat"
    assert log[0]["headers"]["authorization"] == "Bearer SEGREDO-NUVEM"
    assert log[0]["payload"]["model"] == "gemma4:31b"


async def test_ollama_local_host_never_gets_an_authorization_header(monkeypatch, calls):
    log, reply = calls
    monkeypatch.setenv("A11Y_MCP_BACKEND", "ollama")
    monkeypatch.setenv("A11Y_MCP_MODEL", "llava")
    reply["data"] = {"message": {"content": "ok"}}
    assert await llm.ask_model(None, "x") == "ok"
    assert log[0]["url"] == "http://localhost:11434/api/chat"
    assert "authorization" not in log[0]["headers"]


async def test_ollama_explicit_host_with_key_uses_that_host(monkeypatch, calls):
    log, reply = calls
    monkeypatch.setenv("OLLAMA_API_KEY", "k")
    monkeypatch.setenv("OLLAMA_HOST", "https://ollama.exemplo.com")
    monkeypatch.setenv("A11Y_MCP_MODEL", "m")
    reply["data"] = {"message": {"content": "ok"}}
    assert await llm.ask_model(None, "x") == "ok"
    assert log[0]["url"] == "https://ollama.exemplo.com/api/chat"
    assert log[0]["headers"]["authorization"] == "Bearer k"


async def test_ollama_cloud_key_is_never_logged_on_failure(monkeypatch, calls, caplog):
    _, reply = calls
    monkeypatch.setenv("OLLAMA_API_KEY", "SEGREDO-NUVEM")
    monkeypatch.setenv("A11Y_MCP_MODEL", "m")
    reply["error"] = httpx.HTTPStatusError("401", request=httpx.Request("POST", "https://ollama.com/api/chat"),
                                           response=httpx.Response(401))
    assert await llm.ask_model(None, "x") is None
    assert "SEGREDO-NUVEM" not in caplog.text
