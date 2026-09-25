"""Julgamento pelo modelo (sampling): nada de palavra-chave, regex ou ranking lexical."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from mcp.types import TextContent

import mcp_server
import sampling


def fake_ctx(*replies: str | None):
    """Ctx cujo modelo responde em sequencia; None = cliente sem sampling."""
    queue = list(replies)
    prompts: list[str] = []

    async def create_message(messages, max_tokens):
        prompts.append(messages[0].content.text)
        reply = queue.pop(0)
        if reply is None:
            raise RuntimeError("sampling nao suportado")
        return SimpleNamespace(content=TextContent(type="text", text=reply))

    return SimpleNamespace(session=SimpleNamespace(create_message=create_message)), prompts


@pytest.fixture()
def skills_dir(tmp_path, monkeypatch):
    for name, desc in [
        ("azure-deploy-agent", "Deploy agents to Azure"),
        ("chat-ui-a11y", "Accessible chat interfaces"),
        ("pastry-baking", "Bake croissants"),
    ]:
        d = tmp_path / name
        d.mkdir()
        (d / "SKILL.md").write_text(f"# {name}\n\n{desc}", encoding="utf-8")
    monkeypatch.setattr(mcp_server, "SKILLS_PATH", tmp_path)
    monkeypatch.setattr(mcp_server, "CLASSIFICATION_CACHE", tmp_path / "cls.json")
    return tmp_path


def test_extract_json_tolerates_surrounding_text():
    assert sampling.extract_json('Claro! ["a", "b"] pronto') == ["a", "b"]
    assert sampling.extract_json('x {"a": ["b"]} y', "object") == {"a": ["b"]}
    assert sampling.extract_json("sem json") is None
    assert sampling.extract_json("[quebrado") is None


async def test_ask_model_none_when_client_has_no_sampling():
    ctx, _ = fake_ctx(None)
    assert await sampling.ask_model(ctx, "oi") is None


async def test_find_skills_model_decides_and_invented_names_are_dropped(skills_dir):
    ctx, prompts = fake_ctx('["chat-ui-a11y", "nome-inventado"]')
    out = await mcp_server.find_skills("quero uma tela de conversa que leitor de tela consiga usar", ctx)
    assert "chat-ui-a11y" in out and "nome-inventado" not in out and "pastry" not in out
    assert "TAREFA" in prompts[0] and "pastry-baking" in prompts[0]  # o modelo viu o catalogo inteiro


async def test_find_skills_without_sampling_gives_no_keyword_fallback(skills_dir):
    ctx, _ = fake_ctx(None)
    out = await mcp_server.find_skills("azure", ctx)
    assert "sampling" in out and "azure-deploy-agent" not in out


async def test_find_skills_batches_and_model_breaks_ties(skills_dir, monkeypatch):
    monkeypatch.setattr(mcp_server, "_FIND_BATCH", 1)
    monkeypatch.setattr(mcp_server, "_FIND_MAX_RESULTS", 1)
    ctx, prompts = fake_ctx('["azure-deploy-agent"]', '["chat-ui-a11y"]', "[]", '["chat-ui-a11y"]')
    out = await mcp_server.find_skills("x", ctx)
    assert len(prompts) == 4 and "chat-ui-a11y" in out and "azure-deploy-agent" not in out


async def test_classify_skills_uses_model_validates_and_caches(skills_dir):
    reply = json.dumps({"azure-deploy-agent": ["devops", "ai", "inventada"], "chat-ui-a11y": ["accessibility"]})
    ctx, _ = fake_ctx(reply)
    out = await mcp_server.classify_skills(ctx)
    assert "Classificadas 2" in out
    cats = {s["name"]: s["categories"] for s in mcp_server.get_skills(force_reload=True)}
    assert cats["azure-deploy-agent"] == ["ai", "devops"] or set(cats["azure-deploy-agent"]) == {"devops", "ai"}
    assert cats["chat-ui-a11y"] == ["accessibility"]
    assert cats["pastry-baking"] == ["unclassified"]  # o modelo nao classificou: nada de chute por nome


async def test_classify_skills_is_incremental_via_cache(skills_dir):
    ctx, _ = fake_ctx('{"azure-deploy-agent": ["devops"], "chat-ui-a11y": [], "pastry-baking": []}')
    await mcp_server.classify_skills(ctx)
    ctx2, prompts2 = fake_ctx()
    assert "ja estao classificadas" in await mcp_server.classify_skills(ctx2)
    assert prompts2 == []


async def test_classify_without_sampling_leaves_everything_unclassified(skills_dir):
    ctx, _ = fake_ctx(None)
    assert "sampling" in await mcp_server.classify_skills(ctx)
    assert all(s["categories"] == ["unclassified"] for s in mcp_server.get_skills(force_reload=True))


def test_no_lexical_machinery_left_in_server():
    src = Path(mcp_server.__file__).read_text(encoding="utf-8")
    for banned in ("rank_bm25", "BM25", "CATEGORY_RULES", "categorize_skill_name", "substrings"):
        assert banned not in src
