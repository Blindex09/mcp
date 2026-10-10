"""Resolucao automatica de modelo: so a chave basta, quando o provedor tem roteador nativo ou quando um modelo
(o do cliente, ou uma escolha ja guardada) decide pelo catalogo real. Nunca uma tabela de "qual e bom" no codigo."""
import httpx
import pytest

import llm
import models
from a11y import learn


def test_native_auto_is_a_fact_about_the_provider_not_our_opinion():
    assert models.native_auto("openai", None) == models.OPENAI_NATIVE_AUTO
    assert models.native_auto("openai-compatible", "https://openrouter.ai/api/v1") == models.OPENROUTER_NATIVE_AUTO
    assert models.native_auto("openai-compatible", "http://localhost:1234/v1") is None  # outro compativel: sem nativo
    assert models.native_auto("anthropic", None) is None  # a Anthropic nao publica um roteador nativo
    assert models.native_auto("ollama", None) is None


def test_remember_and_persisted_roundtrip_reuses_learn_infrastructure(tmp_path, monkeypatch):
    monkeypatch.setenv("A11Y_MCP_HOME", str(tmp_path))
    assert models.persisted("anthropic") is None
    models.remember("anthropic", "claude-x")
    assert models.persisted("anthropic") == "claude-x"
    entries = [e for e in learn.load_all() if e["scope"] == models.MODEL_SCOPE]
    assert entries == [{"topic": "anthropic", "learning": "claude-x", "scope": models.MODEL_SCOPE, "updated": entries[0]["updated"]}]
    models.remember("anthropic", "claude-y")  # o mesmo provedor: atualiza, nunca duplica
    assert models.persisted("anthropic") == "claude-y"
    assert len([e for e in learn.load_all() if e["scope"] == models.MODEL_SCOPE]) == 1


async def test_native_auto_wins_over_catalog_and_is_remembered(tmp_path, monkeypatch):
    monkeypatch.setenv("A11Y_MCP_HOME", str(tmp_path))
    called = False

    async def boom(*_a, **_k):
        nonlocal called
        called = True
        return ["nao devia ser buscado"]

    monkeypatch.setattr(models, "fetch_catalog", boom)
    r = await models.resolve(None, "openai", None, {})
    assert r == models.Resolution(models.OPENAI_NATIVE_AUTO, "nativo")
    assert called is False  # o nativo resolve antes de qualquer busca de catalogo
    assert models.persisted("openai") == models.OPENAI_NATIVE_AUTO  # guardado: a proxima nem passa por aqui


async def test_persisted_choice_wins_over_native_and_over_a_new_catalog_search(tmp_path, monkeypatch):
    monkeypatch.setenv("A11Y_MCP_HOME", str(tmp_path))
    models.remember("openai", "gpt-escolhido-antes")
    r = await models.resolve(None, "openai", None, {})
    assert r == models.Resolution("gpt-escolhido-antes", "aprendido")


async def test_no_catalog_available_returns_no_choice_without_guessing(tmp_path, monkeypatch):
    monkeypatch.setenv("A11Y_MCP_HOME", str(tmp_path))

    async def none(*_a, **_k):
        return None

    monkeypatch.setattr(models, "fetch_catalog", none)
    r = await models.resolve(None, "anthropic", None, {"ANTHROPIC_API_KEY": "k"})
    assert r == models.Resolution(None, "sem-escolha")


async def test_client_model_picks_from_the_real_catalog_by_meaning_and_the_choice_is_remembered(tmp_path, monkeypatch, fake_ctx):
    monkeypatch.setenv("A11Y_MCP_HOME", str(tmp_path))

    async def catalog(*_a, **_k):
        return ["claude-mini-2026", "claude-grande-2026"]

    monkeypatch.setattr(models, "fetch_catalog", catalog)
    ctx, prompts = fake_ctx('{"model": "claude-grande-2026"}')
    r = await models.resolve(ctx, "anthropic", None, {"ANTHROPIC_API_KEY": "k"})
    assert r.model == "claude-grande-2026" and r.source == "escolhido-pelo-modelo"
    assert "claude-mini-2026" in prompts[0] and "claude-grande-2026" in prompts[0]  # o catalogo real foi mostrado
    assert models.persisted("anthropic") == "claude-grande-2026"  # nao pergunta de novo da proxima vez


async def test_a_name_invented_outside_the_real_catalog_is_rejected(tmp_path, monkeypatch, fake_ctx):
    """Unica validacao: o nome devolvido existe DE FATO no catalogo (checagem de fato, nao julgamento)."""
    monkeypatch.setenv("A11Y_MCP_HOME", str(tmp_path))

    async def catalog(*_a, **_k):
        return ["modelo-real"]

    monkeypatch.setattr(models, "fetch_catalog", catalog)
    ctx, _ = fake_ctx('{"model": "modelo-que-nao-existe"}')
    r = await models.resolve(ctx, "anthropic", None, {"ANTHROPIC_API_KEY": "k"})
    assert r == models.Resolution(None, "sem-escolha", ["modelo-real"])
    assert models.persisted("anthropic") is None


async def test_without_a_client_that_offers_sampling_the_catalog_comes_back_for_the_person_to_decide(tmp_path, monkeypatch):
    monkeypatch.setenv("A11Y_MCP_HOME", str(tmp_path))

    async def catalog(*_a, **_k):
        return ["modelo-a", "modelo-b"]

    monkeypatch.setattr(models, "fetch_catalog", catalog)
    r = await models.resolve(None, "anthropic", None, {"ANTHROPIC_API_KEY": "k"})  # ctx=None: sem sampling
    assert r == models.Resolution(None, "sem-escolha", ["modelo-a", "modelo-b"])


# ---------------------------------------------------------------- catalogo real (formato de cada provedor)

@pytest.fixture()
def http_get(monkeypatch):
    calls: list[dict] = []
    reply: dict = {"data": {}, "error": None}

    async def fake_get(url, headers):
        calls.append({"url": url, "headers": headers})
        if reply["error"]:  # o _get real nunca deixa a excecao escapar (mesma garantia de _http_post)
            return None
        return reply["data"]

    monkeypatch.setattr(models, "_get", fake_get)
    return calls, reply


async def test_anthropic_catalog_shape(http_get):
    calls, reply = http_get
    reply["data"] = {"data": [{"id": "claude-a"}, {"id": "claude-b"}]}
    out = await models.fetch_catalog("anthropic", None, {"ANTHROPIC_API_KEY": "segredo"})
    assert out == ["claude-a", "claude-b"]
    assert calls[0]["url"] == "https://api.anthropic.com/v1/models?limit=1000"
    assert calls[0]["headers"]["x-api-key"] == "segredo"


async def test_anthropic_catalog_without_key_never_calls_out(http_get):
    calls, _ = http_get
    assert await models.fetch_catalog("anthropic", None, {}) is None
    assert calls == []


async def test_openai_catalog_shape(http_get):
    calls, reply = http_get
    reply["data"] = {"data": [{"id": "gpt-a"}]}
    out = await models.fetch_catalog("openai", None, {"OPENAI_API_KEY": "k"})
    assert out == ["gpt-a"] and calls[0]["url"] == "https://api.openai.com/v1/models"
    assert calls[0]["headers"]["authorization"] == "Bearer k"


async def test_openai_compatible_catalog_uses_the_configured_base_and_no_base_means_no_call(http_get):
    calls, reply = http_get
    assert await models.fetch_catalog("openai-compatible", None, {}) is None
    assert calls == []
    reply["data"] = {"data": [{"id": "local-a"}]}
    out = await models.fetch_catalog("openai-compatible", "http://localhost:1234/v1", {})
    assert out == ["local-a"] and calls[0]["url"] == "http://localhost:1234/v1/models"
    assert "authorization" not in calls[0]["headers"]


async def test_ollama_catalog_shape_and_cloud_key(http_get):
    calls, reply = http_get
    reply["data"] = {"models": [{"model": "gemma4:31b"}, {"name": "so-tem-name"}]}
    out = await models.fetch_catalog("ollama", None, {"_ollama_host": "https://ollama.com", "OLLAMA_API_KEY": "chave"})
    assert out == ["gemma4:31b", "so-tem-name"]
    assert calls[0]["url"] == "https://ollama.com/api/tags" and calls[0]["headers"]["authorization"] == "Bearer chave"


async def test_catalog_fetch_failure_never_raises(http_get):
    _, reply = http_get
    reply["error"] = httpx.ConnectError("sem rede")
    assert await models.fetch_catalog("anthropic", None, {"ANTHROPIC_API_KEY": "k"}) is None


# --------------------------------------------------------- fio inteiro por llm.ask_model


async def test_openai_key_alone_is_enough_end_to_end(monkeypatch, tmp_path):
    """So a chave: sem A11Y_MCP_MODEL, a OpenAI tem roteador nativo proprio, entao nem precisa de catalogo/cliente."""
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setenv("A11Y_MCP_HOME", str(tmp_path))
    posted = {}

    async def fake_post(url, headers, payload):
        posted.update(payload)
        return {"choices": [{"message": {"content": "ok"}}]}

    monkeypatch.setattr(llm, "_http_post", fake_post)
    assert await llm.ask_model(None, "oi") == "ok"
    assert posted["model"] == models.OPENAI_NATIVE_AUTO


async def test_anthropic_key_alone_resolves_via_the_calling_clients_model(monkeypatch, tmp_path, fake_ctx):
    """So a chave, sem roteador nativo: o modelo do CLIENTE le o catalogo real e escolhe, uma vez."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setenv("A11Y_MCP_HOME", str(tmp_path))

    async def catalog(*_a, **_k):
        return ["claude-boa-2026"]

    monkeypatch.setattr(models, "fetch_catalog", catalog)
    posted = {}

    async def fake_post(url, headers, payload):
        posted.update(payload)
        return {"content": [{"type": "text", "text": "ok"}]}

    monkeypatch.setattr(llm, "_http_post", fake_post)
    ctx, _ = fake_ctx('{"model": "claude-boa-2026"}')
    assert await llm.ask_model(ctx, "oi") == "ok"
    assert posted["model"] == "claude-boa-2026"
    assert models.persisted("anthropic") == "claude-boa-2026"


async def test_fast_tier_without_its_own_choice_reuses_whatever_main_resolves_to(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setenv("A11Y_MCP_HOME", str(tmp_path))
    posted = {}

    async def fake_post(url, headers, payload):
        posted.update(payload)
        return {"choices": [{"message": {"content": "ok"}}]}

    monkeypatch.setattr(llm, "_http_post", fake_post)
    await llm.ask_model(None, "oi", tier="fast")
    assert posted["model"] == models.OPENAI_NATIVE_AUTO


# --------------------------------------------------------------- papeis (vision/write/...)

def test_persisted_and_remember_are_per_role_main_keeps_the_old_bare_topic(tmp_path, monkeypatch):
    monkeypatch.setenv("A11Y_MCP_HOME", str(tmp_path))
    models.remember("ollama", "modelo-principal")  # role="main" (padrao): topico continua so o backend
    models.remember("ollama", "modelo-visao", role="vision")
    models.remember("ollama", "modelo-escritor", role="write")
    assert models.persisted("ollama") == "modelo-principal"
    assert models.persisted("ollama", "main") == "modelo-principal"
    assert models.persisted("ollama", "vision") == "modelo-visao"
    assert models.persisted("ollama", "write") == "modelo-escritor"
    topics = {(e["topic"]) for e in learn.load_all() if e["scope"] == models.MODEL_SCOPE}
    assert topics == {"ollama", "ollama:vision", "ollama:write"}  # main sem sufixo: compativel com o que ja existia


async def test_role_without_its_own_choice_falls_back_to_main_never_invents_one(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setenv("A11Y_MCP_HOME", str(tmp_path))
    monkeypatch.setenv("A11Y_MCP_MODEL", "modelo-principal")
    posted = []

    async def fake_post(url, headers, payload):
        posted.append(payload["model"])
        return {"choices": [{"message": {"content": "ok"}}]}

    monkeypatch.setattr(llm, "_http_post", fake_post)
    await llm.ask_model(None, "x", tier="vision")  # ninguem escolheu um modelo de visao ainda
    assert posted == ["modelo-principal"]


async def test_explicit_env_for_a_role_wins_over_a_persisted_choice(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setenv("A11Y_MCP_HOME", str(tmp_path))
    monkeypatch.setenv("A11Y_MCP_MODEL", "modelo-principal")
    monkeypatch.setenv("A11Y_MCP_MODEL_WRITE", "modelo-da-variavel")
    models.remember("openai", "modelo-guardado", role="write")
    posted = []

    async def fake_post(url, headers, payload):
        posted.append(payload["model"])
        return {"choices": [{"message": {"content": "ok"}}]}

    monkeypatch.setattr(llm, "_http_post", fake_post)
    await llm.ask_model(None, "x", tier="write")
    assert posted == ["modelo-da-variavel"]  # a variavel de ambiente sempre vence


async def test_a_role_with_a_remembered_choice_uses_it_without_asking_again(tmp_path, monkeypatch, fake_ctx):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setenv("A11Y_MCP_HOME", str(tmp_path))
    monkeypatch.setenv("A11Y_MCP_MODEL", "modelo-principal")
    models.remember("openai", "modelo-de-visao-escolhido", role="vision")
    posted = []

    async def fake_post(url, headers, payload):
        posted.append(payload["model"])
        return {"choices": [{"message": {"content": "ok"}}]}

    monkeypatch.setattr(llm, "_http_post", fake_post)
    ctx, prompts = fake_ctx("nao deveria ser chamado")  # o cliente nem precisa ser perguntado
    await llm.ask_model(ctx, "x", tier="vision")
    assert posted == ["modelo-de-visao-escolhido"] and prompts == []


async def test_role_resolution_never_triggers_the_catalog_bootstrap_by_itself(tmp_path, monkeypatch):
    """So o papel main tenta descobrir sozinho por catalogo; um papel especializado sem escolha nunca dispara isso -
    so herda o que main ja resolveu (evita 3 buscas de catalogo/3 perguntas ao cliente por sessao)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setenv("A11Y_MCP_HOME", str(tmp_path))
    called = False

    async def boom(*_a, **_k):
        nonlocal called
        called = True

    monkeypatch.setattr(models, "fetch_catalog", boom)
    assert await llm._resolve_model(None, "vision", "anthropic") is None
    assert called is True  # tentou UMA vez, herdando a resolucao do papel "main" - nao existe busca propria do "vision"
