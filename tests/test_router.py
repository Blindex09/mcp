"""Roteador semantico: quem decide a camada e um modelo (nunca palavra-chave, regra ou limiar), com cascata por fatos.

O modelo do roteador, o gerador e o verificador sao simulados por HTTP falso; o que se prova aqui e o desenho:
economia (nada de chamada extra quando nao ha o que escolher), qualidade (sobe de camada por fato objetivo ou por um verificador
independente, nunca pela confianca declarada pelo proprio modelo), seguranca de falha e aprendizado em contexto.
"""
import json

import pytest

import llm
import router
from a11y import learn
from router import Hint

GEN_FAST, GEN_MAIN = "modelo-pequeno", "modelo-grande"


@pytest.fixture()
def world(monkeypatch, tmp_path):
    """Dois modelos configurados; devolve o log de chamadas e o roteiro de respostas de cada papel."""
    monkeypatch.setenv("A11Y_MCP_BACKEND", "openai-compatible")
    monkeypatch.setenv("A11Y_MCP_BASE_URL", "http://provedor.local/v1")
    monkeypatch.setenv("A11Y_MCP_MODEL", GEN_MAIN)
    monkeypatch.setenv("A11Y_MCP_MODEL_FAST", GEN_FAST)
    monkeypatch.setenv("A11Y_MCP_HOME", str(tmp_path))
    router.reset()
    log: list[dict] = []
    script = {"router": '{"tier": "fast", "verify": false, "reason": "pedido simples"}', "verifier": '{"adequate": true}',
              "fast": "resposta do pequeno", "main": "resposta do grande"}

    async def fake_post(url, headers, payload):
        prompt = payload["messages"][0]["content"]
        text = prompt if isinstance(prompt, str) else next(p["text"] for p in prompt if p["type"] == "text")
        role = "router" if "ROTEADOR" in text else "verifier" if "VERIFICADOR" in text else ("fast" if payload["model"] == GEN_FAST else "main")
        log.append({"role": role, "model": payload["model"], "prompt": text, "has_image": not isinstance(prompt, str)})
        reply = script[role]
        if isinstance(reply, BaseException):
            raise reply
        return {"choices": [{"message": {"content": reply}}]}

    monkeypatch.setattr(llm, "_http_post", fake_post)
    return log, script


HINT = Hint(purpose="decidir o proximo passo de um usuario de teclado numa pagina", brief="passo 3 de 20; pagina de checkout")


async def test_single_model_needs_no_router_call(monkeypatch, world):
    log, _ = world
    monkeypatch.delenv("A11Y_MCP_MODEL_FAST")
    assert await router.ask_routed(None, "pedido", hint=HINT) == "resposta do grande"
    assert [c["role"] for c in log] == ["main"]  # nada a escolher: zero custo de roteamento


async def test_same_model_in_both_tiers_needs_no_router_call(monkeypatch, world):
    log, _ = world
    monkeypatch.setenv("A11Y_MCP_MODEL_FAST", GEN_MAIN)
    await router.ask_routed(None, "pedido", hint=HINT)
    assert [c["role"] for c in log] == ["main"]


async def test_router_picks_cheap_tier_and_the_strong_model_is_never_called(world):
    log, _ = world
    assert await router.ask_routed(None, "pedido", hint=HINT) == "resposta do pequeno"
    assert [(c["role"], c["model"]) for c in log] == [("router", GEN_FAST), ("fast", GEN_FAST)]


async def test_router_picks_strong_tier(world):
    log, script = world
    script["router"] = '{"tier": "main", "verify": false, "reason": "raciocinio longo com evidencia visual"}'
    assert await router.ask_routed(None, "pedido", hint=HINT) == "resposta do grande"
    assert [c["role"] for c in log] == ["router", "main"]


async def test_the_decision_depends_only_on_the_model_never_on_the_words_of_the_request(world):
    """Sem palavra-chave: a mesma resposta do roteador produz a mesma rota, seja qual for o texto do pedido."""
    log, script = world
    script["router"] = '{"tier": "main", "verify": false, "reason": "x"}'
    for purpose in ("escrever o relatorio final", "arrumar um botao", "zzz qqq", "decidir o proximo passo"):
        log.clear()
        await router.ask_routed(None, "p", hint=Hint(purpose=purpose, brief=purpose))
        assert [c["role"] for c in log] == ["router", "main"], purpose
    script["router"] = '{"tier": "fast", "verify": false, "reason": "x"}'
    for purpose in ("escrever o relatorio final", "raciocinio complexo e critico"):
        log.clear()
        await router.ask_routed(None, "p", hint=Hint(purpose=purpose, brief=""))
        assert [c["role"] for c in log] == ["router", "fast"], purpose


async def test_objective_validation_failure_escalates_to_the_strong_model(world):
    log, script = world
    script["fast"] = "isto nao e json"

    def is_json(reply):
        return reply is not None and reply.startswith("{")

    script["main"] = '{"ok": true}'
    out = await router.ask_routed(None, "pedido", hint=Hint(purpose="p", brief="b", validate=is_json))
    assert out == '{"ok": true}'
    assert [c["role"] for c in log] == ["router", "fast", "main"]
    assert router.stats()["escalated_by_fact"] == 1


async def test_valid_cheap_answer_is_accepted_without_escalation(world):
    log, script = world
    script["fast"] = '{"ok": true}'
    out = await router.ask_routed(None, "p", hint=Hint(purpose="p", brief="b", validate=lambda r: bool(r) and r.startswith("{")))
    assert out == '{"ok": true}' and [c["role"] for c in log] == ["router", "fast"]


async def test_verify_uses_an_independent_stronger_text_only_check_and_escalates_on_inadequate(world):
    log, script = world
    script["router"] = '{"tier": "fast", "verify": true, "reason": "erro seria caro e nao ha como checar por fato"}'
    script["verifier"] = '{"adequate": false, "problem": "ignora a evidencia"}'
    out = await router.ask_routed(None, "pedido", images=[b"img"], hint=HINT)
    assert out == "resposta do grande"
    roles = [(c["role"], c["model"]) for c in log]
    assert roles == [("router", GEN_FAST), ("fast", GEN_FAST), ("verifier", GEN_MAIN), ("main", GEN_MAIN)]
    verifier = next(c for c in log if c["role"] == "verifier")
    assert not verifier["has_image"] and "resposta do pequeno" in verifier["prompt"]  # confere a resposta, sem pagar imagem
    assert router.stats()["escalated_by_verifier"] == 1


async def test_verify_accepts_when_the_checker_finds_it_adequate(world):
    log, script = world
    script["router"] = '{"tier": "fast", "verify": true, "reason": "x"}'
    assert await router.ask_routed(None, "p", hint=HINT) == "resposta do pequeno"
    assert [c["role"] for c in log] == ["router", "fast", "verifier"]


async def test_verifier_is_not_called_when_the_router_does_not_ask_for_it(world):
    log, _ = world
    await router.ask_routed(None, "p", hint=HINT)
    assert "verifier" not in [c["role"] for c in log]


async def test_verify_is_not_used_on_the_strong_tier(world):
    log, script = world
    script["router"] = '{"tier": "main", "verify": true, "reason": "x"}'
    await router.ask_routed(None, "p", hint=HINT)
    assert [c["role"] for c in log] == ["router", "main"]  # ja esta na camada mais forte: nao ha para onde subir


@pytest.mark.parametrize("bad", ["nao sei", "", "[]", '{"tier": "banana"}', '{"verify": true}', '{"tier": 3}'])
async def test_unreadable_or_invalid_router_answer_falls_back_to_the_strong_tier(world, bad):
    """Falha segura: sem decisao valida do roteador, prioriza qualidade. Nunca levanta excecao."""
    log, script = world
    script["router"] = bad
    assert await router.ask_routed(None, "p", hint=HINT) == "resposta do grande"
    assert [c["role"] for c in log] == ["router", "main"]
    assert router.stats()["router_fallbacks"] == 1


async def test_router_provider_error_falls_back_to_the_strong_tier(world):
    import httpx

    _, script = world
    script["router"] = httpx.ConnectError("caiu")
    assert await router.ask_routed(None, "p", hint=HINT) == "resposta do grande"


async def test_cheap_tier_giving_no_answer_escalates(world):
    import httpx

    log, script = world
    script["fast"] = httpx.ReadTimeout("t")
    assert await router.ask_routed(None, "p", hint=HINT) == "resposta do grande"
    assert [c["role"] for c in log] == ["router", "fast", "main"]


async def test_call_without_hint_goes_straight_to_the_strong_model(world):
    log, _ = world
    assert await router.ask_routed(None, "p") == "resposta do grande"
    assert [c["role"] for c in log] == ["main"]


async def test_router_prompt_carries_facts_and_never_a_fixed_rule(world):
    log, _ = world
    await router.ask_routed(None, "x" * 5000, images=[b"a", b"b"], max_tokens=900, hint=HINT)
    prompt = log[0]["prompt"]
    assert GEN_FAST in prompt and GEN_MAIN in prompt  # o roteador sabe quais modelos existem
    assert HINT.purpose in prompt and HINT.brief in prompt
    assert "5000" in prompt and "2" in prompt and "900" in prompt  # fatos: tamanho do pedido, imagens anexas, saida esperada
    assert log[0]["has_image"] is False  # a imagem nao vai ao roteador: so o fato de existir


async def test_lessons_and_recent_outcomes_come_back_into_the_router_prompt(world):
    log, _ = world
    learn._save([{"topic": "relatorios de sessao longa", "learning": "o modelo pequeno omitiu achados; a camada forte acertou",
                  "scope": router.ROUTING_SCOPE, "updated": "2026-09-26T00:00:00+00:00"},
                 {"topic": "outro escopo", "learning": "NAO DEVE APARECER NO ROTEADOR", "scope": "geral", "updated": "2026-09-26T00:00:00+00:00"}])
    await router.ask_routed(None, "p", hint=HINT)  # 1a chamada gera um resultado recente
    await router.ask_routed(None, "p", hint=HINT)
    second = [c for c in log if c["role"] == "router"][1]["prompt"]
    assert "omitiu achados" in second and "NAO DEVE APARECER" not in second
    assert "camada fast" in second or "fast" in second  # resultado recente da 1a chamada


async def test_learning_disabled_does_not_read_lessons(monkeypatch, world):
    log, _ = world
    learn._save([{"topic": "t", "learning": "LICAO SECRETA", "scope": router.ROUTING_SCOPE, "updated": "2026-09-26T00:00:00+00:00"}])
    monkeypatch.setenv("A11Y_MCP_LEARN", "0")
    await router.ask_routed(None, "p", hint=HINT)
    assert "LICAO SECRETA" not in log[0]["prompt"]


async def test_outcomes_feed_the_learning_digest_and_the_model_can_store_routing_lessons(world):
    _, script = world
    script["fast"] = "lixo"
    await router.ask_routed(None, "p", hint=Hint(purpose="escrever relatorio", brief="b", validate=lambda r: r == "ok"))
    digest = router.drain_outcomes()
    assert "escrever relatorio" in digest and "subiu" in digest.lower()
    assert router.drain_outcomes() == ""  # entregue uma vez so

    async def ask(prompt, images, max_tokens, hint=None):
        assert "ROTEAMENTO" in prompt and "escrever relatorio" in prompt
        return json.dumps([{"topic": "relatorio", "learning": "relatorio pede a camada forte", "scope": router.ROUTING_SCOPE}])

    await learn.learn_from_run(ask, "site.exemplo", "resumo da execucao", routing=digest)
    stored = [e for e in learn.load_all() if e["scope"] == router.ROUTING_SCOPE]
    assert stored and stored[0]["learning"] == "relatorio pede a camada forte"
    assert all(e["scope"] != router.ROUTING_SCOPE for e in learn.relevant("site.exemplo"))  # nao polui o prompt do agente


async def test_stats_show_the_economy(world):
    _, script = world
    await router.ask_routed(None, "p", hint=HINT)
    script["router"] = '{"tier": "main", "verify": false, "reason": "x"}'
    await router.ask_routed(None, "p", hint=HINT)
    s = router.stats()
    assert s["calls"] == 2 and s["router_calls"] == 2 and s["to_fast"] == 1 and s["to_main"] == 1 and s["active"] is True


async def test_sampling_only_client_without_backend_goes_straight_through(monkeypatch, fake_ctx):
    """Sem provedor configurado nao existem camadas: o modelo do cliente responde direto."""
    monkeypatch.delenv("A11Y_MCP_MODEL_FAST", raising=False)
    ctx, prompts = fake_ctx("resposta do cliente")
    assert await router.ask_routed(ctx, "p", hint=HINT) == "resposta do cliente"
    assert len(prompts) == 1


def test_no_keyword_or_rule_based_decision_in_the_router_source():
    """Guarda das regras mestras: a decisao vem do modelo. Nada de regex, listas de palavras ou limiares no roteador."""
    import ast
    import inspect

    src = inspect.getsource(router)
    tree = ast.parse(src)
    assert "import re" not in src and "re." not in [n.value.id + "." for n in ast.walk(tree) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "re"]
    for node in ast.walk(tree):  # nenhuma comparacao numerica de "dificuldade": so fatos objetivos e a resposta do modelo
        if isinstance(node, ast.Compare) and any(isinstance(c, ast.Constant) and isinstance(c.value, float) for c in node.comparators):
            pytest.fail("limiar numerico no roteador")


PAGE = '<!doctype html><html lang="pt"><title>t</title><body><main><h1>Loja</h1><a href="#a">Comprar</a><a href="#b">Trocar</a></main></body></html>'


async def test_find_tool_is_routed_and_a_made_up_name_makes_the_cheap_answer_climb(world):
    import mcp_server

    log, script = world
    script["fast"] = '["nome-inventado"]'  # fato objetivo: nao existe no catalogo -> sobe de camada
    script["main"] = '["component-identity-guide"]'
    tools = mcp_server.mcp._tool_manager
    out = json.loads(await tools.get_tool("a11y_find").fn(task="preciso julgar o que cada componente e", ctx=None))
    assert [i["name"] for i in out["items"]] == ["component-identity-guide"]
    assert [c["role"] for c in log] == ["router", "fast", "main"]
    status = json.loads(await tools.get_tool("a11y_status").fn())
    assert status["routing"]["escalated_by_fact"] == 1 and status["routing"]["active"] is True


async def test_pipeline_roles_bypass_the_router_only_memory_still_goes_through_it(monkeypatch, world):
    """Passo (papel main) e relatorio (papel write, com o proprio modelo da pessoa) nunca passam pelo classificador -
    sao papel fixo, fato tecnico ou preferencia configurada. So a atualizacao de memoria continua roteada."""
    from a11y import agent
    from a11y.session import SESSION

    log, script = world
    GEN_WRITE = "modelo-que-escreve-relatorio"
    monkeypatch.setenv("A11Y_MCP_MODEL_WRITE", GEN_WRITE)
    decision = json.dumps({"thought": "x", "friction": None, "action": {"type": "press", "value": "Tab"}})
    script["router"] = '{"tier": "fast", "verify": false, "reason": "atualizar memoria e barato"}'

    async def fake_post(url, headers, payload):
        prompt = payload["messages"][0]["content"]
        text = prompt if isinstance(prompt, str) else next(p["text"] for p in prompt if p["type"] == "text")
        if payload["model"] == GEN_WRITE:
            role, reply = "write", "RELATORIO ESCRITO PELO PAPEL WRITE"
        elif "ROTEADOR" in text:
            role, reply = "router", script["router"]
        elif "VERIFICADOR" in text:
            role, reply = "verifier", script["verifier"]
        elif "mantem a memoria" in text:  # so esta chamada passa pela escolha de camada
            role, reply = "memory", "[]"
        else:  # o proprio passo do agente: papel main forcado, nunca chega aqui vindo do roteador
            role, reply = "decision", decision
        log.append({"role": role, "model": payload["model"], "prompt": text})
        return {"choices": [{"message": {"content": reply}}]}

    monkeypatch.setattr(llm, "_http_post", fake_post)

    async def ask(prompt, images, max_tokens, hint=None, tier=None):
        return await router.ask_routed(None, prompt, images=images, max_tokens=max_tokens, hint=hint, tier=tier)

    async def noop(*a, **k):
        return None

    r = await agent.run_agent(session=SESSION, ask=ask, mode="task", goal="comprar", url=None, html=PAGE,
                              persona="keyboard", max_steps=2, vision=False, progress=noop)
    assert r["stopped_by"] == "step_limit" and len(r["steps"]) == 2
    assert r["report"] == "RELATORIO ESCRITO PELO PAPEL WRITE"
    assert [c["role"] for c in log if c["role"] in ("decision", "write")] == ["decision", "decision", "write"]
    assert all(c["model"] == GEN_MAIN for c in log if c["role"] == "decision")  # papel main: sempre o mesmo modelo
    assert all(c["model"] == GEN_WRITE for c in log if c["role"] == "write")  # papel write: o modelo que a pessoa escolheu
    memory_calls = [c for c in log if c["role"] in ("router", "memory")]
    assert any(c["role"] == "router" and "atualizar a memoria" in c["prompt"] for c in memory_calls)  # so ela e' roteada
    assert router.stats()["forced_calls"] == 3  # 2 decisoes + 1 relatorio, nenhuma passou pelo classificador
