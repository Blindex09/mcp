"""Julgamento pelo modelo: leitura da resposta e escolha via a11y_find (sem palavra-chave)."""
import json

import llm
import mcp_server


def test_extract_json_tolerates_surrounding_text():
    assert llm.extract_json('Claro! ["a", "b"] pronto') == ["a", "b"]
    assert llm.extract_json('x {"a": ["b"]} y', "object") == {"a": ["b"]}
    assert llm.extract_json("sem json") is None
    assert llm.extract_json("[quebrado") is None


async def test_ask_model_none_when_no_sampling_and_no_backend(fake_ctx):
    ctx, _ = fake_ctx(None)
    assert await llm.ask_model(ctx, "oi") is None


async def test_a11y_find_model_sees_whole_catalog_and_invented_names_are_dropped(fake_ctx):
    ctx, prompts = fake_ctx('["modal-native-dialog", "nome-inventado"]')
    tool = mcp_server.mcp._tool_manager.get_tool("a11y_find")
    data = json.loads(await tool.fn(task="janela que bloqueia o fundo e devolve o foco", ctx=ctx))
    assert [i["name"] for i in data["items"]] == ["modal-native-dialog"]
    assert "audit-checklist" in prompts[0] and "modal-native-dialog" in prompts[0]


def test_no_lexical_machinery_anywhere():
    from pathlib import Path

    root = Path(mcp_server.__file__).parent
    for f in [root / "mcp_server.py", root / "llm.py", *(root / "a11y").glob("*.py")]:
        src = f.read_text(encoding="utf-8")
        for banned in ("rank_bm25", "BM25", "CATEGORY_RULES", "categorize_skill_name"):
            assert banned not in src, f"{banned} em {f.name}"
