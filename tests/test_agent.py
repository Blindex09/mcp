"""Usuario autonomo: o MODELO decide (aqui roteirizado); o HARNESS impoe limites, persona e fechamento."""
import json

import pytest

from a11y import agent
from a11y.session import SESSION, SessionError
from tests.test_session import SITE


def decision(action, thought="penso", friction=None):
    return json.dumps({"thought": thought, "friction": friction, "action": action})


class Script:
    """ask() roteirizado: cada resposta e' str ou callable(prompt)->str; None = modelo indisponivel."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.prompts: list[str] = []
        self.images: list[list[bytes] | None] = []

    async def __call__(self, prompt, images, max_tokens):
        self.prompts.append(prompt)
        self.images.append(images)
        if not self.replies:
            return "RELATORIO FINAL"
        r = self.replies.pop(0)
        return r(prompt) if callable(r) else r


async def run(script, **kw):
    kw.setdefault("mode", "task")
    kw.setdefault("goal", "abrir os detalhes")
    kw.setdefault("url", None)
    kw.setdefault("html", SITE)
    return await agent.run_agent(session=SESSION, ask=script, **kw)


FINISH = decision({"type": "finish", "outcome": "completed", "summary": "x"})


async def test_full_run_model_decides_harness_records_and_closes():
    s = Script(
        decision({"type": "press", "value": "Tab"}, "vou ao primeiro controle", "nao sei onde estou"),
        decision({"type": "press", "value": "Tab"}),
        decision({"type": "finish", "outcome": "completed_with_friction", "summary": "deu, com esforco"}),
        "Relatorio escrito pelo modelo",
    )
    r = await run(s, persona="keyboard")
    assert r["outcome"] == "completed_with_friction" and r["stopped_by"] == "finished"
    assert r["report"] == "Relatorio escrito pelo modelo"
    assert [x["action"] for x in r["steps"]] == ["press", "press", "finish"]
    assert r["frictions"] == ["Passo 1: nao sei onde estou"]
    assert r["narration"][0] == "Passo 1: vou ao primeiro controle"
    assert r["steps"][0]["effect"] and r["facts"]["model_calls"] == 4
    assert r["not_verified"] == agent.NOT_VERIFIED
    assert any("Leitor de tela real" in x for x in r["not_verified"])
    assert SESSION.page is None  # sessao fechada


async def test_prompt_carries_persona_goal_allowed_actions_and_facts_not_a_verdict():
    s = Script(FINISH, "R")
    await run(s, persona="keyboard", goal="abrir os detalhes")
    p = s.prompts[0]
    assert "keyboard" in p and "abrir os detalhes" in p and "Acoes permitidas AGORA" in p
    allowed = p.split("Acoes permitidas AGORA:")[1].split("finish")[0]
    assert "click" not in allowed and "press" in allowed  # teclado sem mouse
    assert "Detalhes" in p and "editavel" in p and "datalist_options=3" in p
    assert "CONHECIMENTO DE APOIO" in p


async def test_persona_is_enforced_even_if_the_model_asks_for_a_click():
    s = Script(
        decision({"type": "click", "target": "e1"}),
        decision({"type": "finish", "outcome": "not_completed", "summary": "nao consegui"}),
        "R",
    )
    r = await run(s, persona="keyboard")
    assert "nao permitida" in r["steps"][0]["refused"]
    assert "RECUSADA pelo servidor" in s.prompts[1]  # o modelo ve a recusa e decide de novo
    assert r["outcome"] == "not_completed"


async def test_action_errors_become_observations_not_crashes():
    s = Script(decision({"type": "click", "target": "e999"}), FINISH, "R")
    r = await run(s, persona="default")
    assert "error" in r["steps"][0] and "ERRO" in s.prompts[1]


async def test_invalid_json_is_retried_once_then_gives_up():
    r = await run(Script("nao e json", FINISH, "R"))
    assert r["stopped_by"] == "finished"
    r2 = await run(Script("lixo", "mais lixo", "R"))
    assert r2["stopped_by"] == "model_invalid_output"


async def test_model_unavailable_stops_cleanly():
    r = await run(Script(None, None))
    assert r["stopped_by"] == "model_unavailable" and r["facts"]["steps_used"] == 0
    assert SESSION.page is None


async def test_repeated_identical_action_in_same_state_is_stopped_by_the_harness():
    same = decision({"type": "press", "value": "Escape"})
    r = await run(Script(same, same, same, same, "R"), persona="keyboard")
    assert r["stopped_by"] == "repeated_action"


async def test_step_and_time_limits():
    def press(v):
        return decision({"type": "press", "value": v})

    r = await run(Script(press("Tab"), press("Tab"), press("Tab"), "R"), persona="keyboard", max_steps=2)
    assert r["stopped_by"] == "step_limit" and r["facts"]["steps_used"] == 2
    r = await run(Script("R"), max_steps=9999)
    assert r["facts"]["max_steps"] == agent.MAX_STEPS_CEILING
    saved, agent.TIME_BUDGET_S = agent.TIME_BUDGET_S, 0
    try:
        r = await run(Script("R"))
        assert r["stopped_by"] == "time_budget"
    finally:
        agent.TIME_BUDGET_S = saved


async def test_vision_only_for_personas_that_can_see():
    seeing = Script(FINISH, "R")
    await run(seeing, persona="default")
    assert seeing.images[0] and seeing.images[0][0][:2] == b"\xff\xd8"
    assert seeing.images[1] is None  # o relatorio nao leva imagem
    blind = Script(FINISH, "R")
    await run(blind, persona="screen_reader")
    assert blind.images[0] is None and "NAO ve a tela" in blind.prompts[0]
    off = Script(FINISH, "R")
    await run(off, persona="default", vision=False)
    assert off.images[0] is None


async def test_review_mode_brings_the_identity_and_design_guides():
    s = Script(FINISH, "R")
    await run(s, mode="review", goal="componentes e design")
    p = s.prompts[0]
    assert "revisor de UX" in p and "Component Identity Guide" in p and "Design Language Review" in p


async def test_reach_and_announce_are_available_and_summarized():
    s = Script(
        decision({"type": "reach", "target": "e5"}),
        decision({"type": "announce", "target": "e5"}),
        FINISH,
        "R",
    )
    r = await run(s, persona="screen_reader")
    assert "Tab ate o alvo" in r["steps"][0]["effect"]
    assert "leitor de tela recebe" in r["steps"][1]["effect"]


async def test_validation_and_cleanup():
    with pytest.raises(SessionError):
        await run(Script(), mode="outro")
    with pytest.raises(SessionError):
        await run(Script(), goal="  ")

    async def boom(prompt, images, max_tokens):
        raise RuntimeError("falha do modelo")

    with pytest.raises(RuntimeError):
        await agent.run_agent(session=SESSION, ask=boom, mode="task", goal="x", url=None, html=SITE)
    assert SESSION.page is None  # fechou mesmo com excecao


async def test_compact_element_and_effect_summary_are_facts_only():
    await SESSION.open(None, SITE)
    try:
        d = await SESSION.dossier()
        lines = [agent.compact_element(e) for e in d["elements"]]
        assert any("editavel" in ln and "datalist_options=3" in ln for ln in lines)
        assert any("role-attr=button" in ln and "papel-calculado=button" in ln and "haspopup=true" in ln and "popup_links=2" in ln for ln in lines)
        assert all("focavel=" in ln and "clicavel=" in ln for ln in lines)  # fatos crus, sem veredito
        assert any("em=nav" in ln for ln in lines)
    finally:
        await SESSION.close()
    summary = agent.effect_summary({"focus_after": None, "tree_added": ["  - x"], "announcements": [{"text": "oi"}]})
    assert summary == "foco em nenhum elemento; apareceu: - x; anunciado: oi"


async def test_tools_fail_clearly_without_any_model_and_work_with_a_provider(monkeypatch, fake_ctx):
    import llm
    import mcp_server

    tools = mcp_server.mcp._tool_manager
    ctx, _ = fake_ctx(None, None)
    out = json.loads(await tools.get_tool("a11y_walkthrough").fn(ctx, task="x", html=SITE))
    assert "A11Y_MCP_MODEL" in out["error"]
    status = json.loads(await tools.get_tool("a11y_status").fn())
    assert status["model"]["ready"] is False
    assert status["browser"]["state"] in {"unknown", "ready", "installing", "failed"}

    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setenv("A11Y_MCP_MODEL", "m")
    finish = {"type": "finish", "outcome": "completed", "summary": "ok"}
    replies = [json.dumps({"thought": "fim", "friction": None, "action": finish}), "Relatorio do provedor"]

    async def fake_post(url, headers, payload):
        return {"content": [{"type": "text", "text": replies.pop(0)}]}

    monkeypatch.setattr(llm, "_http_post", fake_post)
    ctx2, _ = fake_ctx(None)
    out = json.loads(await tools.get_tool("a11y_walkthrough").fn(ctx2, task="abrir detalhes", html=SITE))
    assert out["outcome"] == "completed" and out["report"] == "Relatorio do provedor"
