"""Aprendizado sempre: o modelo decide o que lembrar e como fundir; o codigo guarda, valida e nao duplica."""
import json

import pytest

from a11y import learn
from tests.test_agent import FINISH, Script, run


def entries_json(*items):
    return json.dumps([{"topic": t, "learning": ln, "scope": sc} for t, ln, sc in items], ensure_ascii=False)


async def test_learning_is_stored_outside_the_project_and_is_immediately_relevant(tmp_path):
    assert learn.store_path() == tmp_path / "a11y-home"  # isolado pelo conftest; em uso real: ~/.a11y-mcp
    ask = Script(entries_json(("menu so por hover", "no site loja.com o menu Produtos so abre com o mouse; sondar com hover", "loja.com"),
                              ("sondagem", "clicar e ler a diferenca na arvore mostra o que cada componente e", learn.GENERAL)))
    topics = await learn.learn_from_run(ask, "loja.com", "resumo")
    assert topics == ["menu so por hover", "sondagem"]
    assert (tmp_path / "a11y-home" / "learnings.json").exists()
    assert {e["topic"] for e in learn.relevant("loja.com")} == {"menu so por hover", "sondagem"}
    assert {e["topic"] for e in learn.relevant("outro.com")} == {"sondagem"}  # o especifico do site nao vaza para outros


async def test_same_topic_updates_the_existing_entry_never_duplicates():
    await learn.learn_from_run(Script(entries_json(("Menu so por hover", "versao 1", "loja.com"))), "loja.com", "r1")
    await learn.learn_from_run(
        Script(entries_json(("menu  SO por hover", "versao 2 com mais detalhe", "loja.com"), ("menu so por hover", "versao 3", "loja.com"))),
        "loja.com", "r2",
    )  # o modelo tratou do mesmo assunto duas vezes na mesma resposta
    mine = [e for e in learn.load_all() if e["scope"] == "loja.com"]
    assert len(mine) == 1 and mine[0]["learning"] == "versao 3"  # mesmo assunto (texto normalizado): atualiza, nao duplica


async def test_omission_never_deletes_and_removal_must_be_explicit():
    await learn.learn_from_run(Script(entries_json(("a", "errado", "loja.com"), ("b", "geral", learn.GENERAL))), "loja.com", "r1")
    await learn.learn_from_run(Script(entries_json(("c", "de outro site", "outro.com"))), "outro.com", "r2")  # nao menciona a nem b
    assert {e["topic"] for e in learn.load_all()} == {"a", "b", "c"}  # esquecer de citar nao apaga nada
    remove = json.dumps([{"topic": "A", "scope": "loja.com", "remove": True}])  # o modelo provou que "a" estava errado
    await learn.learn_from_run(Script(remove), "loja.com", "r3")
    assert {e["topic"] for e in learn.load_all()} == {"b", "c"}
    await learn.learn_from_run(Script(json.dumps([{"topic": "b", "scope": "estranho.com", "remove": True}])), "loja.com", "r4")
    assert {e["topic"] for e in learn.load_all()} == {"b", "c"}  # escopo alheio ao da execucao: ignorado


async def test_invalid_output_never_corrupts_the_store_or_breaks_the_run():
    await learn.learn_from_run(Script(entries_json(("ok", "valido", learn.GENERAL))), "x.com", "r")
    for bad in ("nao e json", "{}", "[1, 2]", None, entries_json(("", "sem topico", learn.GENERAL)), entries_json(("t", "escopo alheio", "estranho.com"))):
        await learn.learn_from_run(Script(bad), "x.com", "r")
    assert [e["topic"] for e in learn.load_all()] == ["ok"]  # nenhuma resposta ruim alterou o que ja estava guardado

    async def boom(*a, **k):
        raise RuntimeError("modelo caiu")

    assert await learn.learn_from_run(boom, "x.com", "r") == []  # aprender e' bonus: nunca derruba


async def test_size_limits_and_opt_out(monkeypatch):
    many = entries_json(*[(f"t{i}", "x" * 900, learn.GENERAL) for i in range(50)])
    await learn.learn_from_run(Script(many), "x.com", "r")
    stored = learn.load_all()
    assert len(stored) == learn.MAX_PER_SCOPE and all(len(e["learning"]) <= learn.MAX_LEARNING_CHARS for e in stored)  # teto por escopo
    monkeypatch.setenv("A11Y_MCP_LEARN", "0")
    assert await learn.learn_from_run(Script(entries_json(("novo", "n", learn.GENERAL))), "x.com", "r") == []
    assert learn.enabled() is False and not any(e["topic"] == "novo" for e in learn.load_all())


def test_forget_is_the_persons_control_and_host_extraction():
    learn._save([{"topic": "a", "learning": "1", "scope": "g"}, {"topic": "a", "learning": "2", "scope": "x.com"}])
    assert learn.forget("A", "x.com") == 1 and [e["scope"] for e in learn.load_all()] == ["g"]
    assert learn.forget("nao existe") == 0
    assert learn.host_of("https://Loja.com.br:8443/a?b=1") == "loja.com.br" and learn.host_of(None) == "html-local"


async def test_agent_learns_after_a_run_and_the_next_run_starts_knowing_it():
    first = Script(FINISH, "RELATORIO", entries_json(("hover", "o menu so abre com o mouse", learn.GENERAL)))
    r1 = await run(first)
    assert r1["learned_topics"] == ["hover"]
    assert "o menu so abre com o mouse" not in first.prompts[0]  # a 1a execucao ainda nao sabia
    learn_prompt = first.prompts[-1]
    assert "APRENDIZADOS ATUAIS" in learn_prompt and "RESUMO DA EXECUCAO" in learn_prompt and "nunca crie duplicata" in learn_prompt
    assert "SOMENTE AS MUDANCAS" in learn_prompt
    second = Script(FINISH, "R2", entries_json(("hover", "o menu so abre com o mouse; sondar com hover", learn.GENERAL)))
    await run(second)
    assert "APRENDIZADOS DE EXECUCOES ANTERIORES" in second.prompts[0] and "o menu so abre com o mouse" in second.prompts[0]
    assert len(learn.load_all()) == 1  # o segundo aprendizado atualizou o mesmo assunto


async def test_learn_call_uses_the_light_tier(monkeypatch):
    tiers = []

    class Spy(Script):
        async def __call__(self, prompt, images, max_tokens, tier="main"):
            tiers.append(tier)
            return await super().__call__(prompt, images, max_tokens, tier)

    await run(Spy(FINISH, "R", entries_json(("t", "l", learn.GENERAL))))
    assert tiers[-1] == "fast" and set(tiers[:-1]) == {"main"}  # decidir/relatar = pesado; lembrar = leve


async def test_tools_list_and_forget():
    import mcp_server

    tools = mcp_server.mcp._tool_manager
    await learn.learn_from_run(Script(entries_json(("x", "y", learn.GENERAL))), "s.com", "r")
    out = json.loads(await tools.get_tool("a11y_learnings").fn())
    assert out["enabled"] is True and [e["topic"] for e in out["entries"]] == ["x"]
    assert json.loads(await tools.get_tool("a11y_forget").fn(topic="x"))["removed"] == 1
    assert json.loads(await tools.get_tool("a11y_learnings").fn())["entries"] == []


@pytest.mark.parametrize("name", ["a11y_learnings", "a11y_forget"])
async def test_learning_tools_registered(name):
    import mcp_server

    assert name in {t.name for t in await mcp_server.mcp.list_tools()}
