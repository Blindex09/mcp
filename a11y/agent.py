"""Usuario autonomo: um agente (modelo + harness) que opera a sessao como uma pessoa faria.

Papeis que nunca se invertem (regra do projeto):
- O MODELO decide tudo que e julgamento: o que tentar a seguir, se entendeu a tela, onde travou, o que e cada
  elemento naquele site, o que melhorar, quando terminou e como explicar. Ele ve a tela (screenshot) e a arvore
  de acessibilidade, e escreve em texto corrido.
- O HARNESS (este codigo) so impoe o que e permitido: persona (sem mouse para teclado/leitor de tela), formato
  da acao, teto de passos/chamadas/tempo, parada em laco de acoes identicas, fechamento da sessao e registro.
Nenhuma palavra-chave, regex ou regra decide o que o usuario "deveria" fazer.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections.abc import Awaitable, Callable
from typing import Any

from llm import extract_json

from .content_index import CONTENT_DIR
from .session import PERSONAS, Session, SessionError

MAX_STEPS_CEILING = 60
TIME_BUDGET_S = 420
REPEAT_LIMIT = 3
HISTORY_LINES = 10
TREE_LINES_IN_PROMPT = 120
DOSSIER_LINES_IN_PROMPT = 40
GUIDE_CHARS = 5000

AskFn = Callable[[str, list[bytes] | None, int], Awaitable[str | None]]
ProgressFn = Callable[[int, int, str], Awaitable[None]]

_POINTER_ACTIONS = {"click", "hover", "focus", "select"}
_TARGET_ACTIONS = _POINTER_ACTIONS | {"reach", "announce"}
_ALL_ACTIONS = _POINTER_ACTIONS | {"press", "type", "wait", "reach", "announce"}

# Fatos sobre o que este harness NAO consegue verificar (nao e julgamento: e o alcance das ferramentas).
NOT_VERIFIED = [
    "Leitor de tela real (NVDA/JAWS/VoiceOver/TalkBack): a arvore de acessibilidade e um substituto, nao a fala real.",
    "Dispositivos e tecnologias assistivas reais (celular fisico, comando de voz, switch, lupa).",
    "Fluxos que exigem login, dados reais ou etapas nao percorridas nesta execucao.",
    "Conteudo que muda com dados, horario ou usuario; outras paginas e breakpoints nao visitados.",
]


def _guide(name: str) -> str:
    path = CONTENT_DIR / "references" / f"{name}.md"
    try:
        return path.read_text(encoding="utf-8")[:GUIDE_CHARS]
    except OSError:
        return ""


def compact_element(e: dict[str, Any]) -> str:
    """Uma linha por elemento do dossie, so com fatos (para caber no prompt)."""
    st = e["states"]
    bits = [f"{e['id']} <{e['tag']}{'[' + e['type'] + ']' if e.get('type') else ''}>"]
    if e.get("role_attr"):
        bits.append(f"role={e['role_attr']}")
    ns = e["name_sources"]
    name = ns.get("aria_label") or ns.get("labelledby") or ns.get("label") or e.get("text") or ns.get("placeholder") or ns.get("title")
    bits.append(f"nome={str(name)[:50]!r}" if name else "SEM NOME")
    for key in ("expanded", "haspopup", "checked", "selected", "pressed", "invalid"):
        if st.get(key) not in (None, False, "false"):
            bits.append(f"{key}={st[key]}")
    if e.get("editable"):
        bits.append("editavel")
    rel = e["relations"]
    for key in ("datalist_options", "native_options", "popup_items", "popup_links"):
        if rel.get(key):
            bits.append(f"{key}={rel[key]}")
    if not e.get("focusable"):
        bits.append("nao-focavel")
    if e.get("context", {}).get("landmark"):
        bits.append(f"em={e['context']['landmark']}")
    return " ".join(bits)


def effect_summary(r: dict[str, Any]) -> str:
    parts: list[str] = []
    f = r.get("focus_after")
    parts.append(f"foco -> {f['tag']} {f['name']!r}" if f else "foco em nenhum elemento")
    if r.get("url_changed"):
        parts.append(f"URL -> {r['url_changed']['to']}")
    if r.get("tree_added"):
        parts.append("apareceu: " + " | ".join(x.strip()[:50] for x in r["tree_added"][:3]))
    if r.get("tree_removed"):
        parts.append("sumiu: " + " | ".join(x.strip()[:50] for x in r["tree_removed"][:2]))
    if r.get("announcements"):
        parts.append("anunciado: " + " | ".join(a["text"][:60] for a in r["announcements"][:2]))
    if r.get("js_dialogs"):
        parts.append(f"dialogo JS: {r['js_dialogs'][0][:50]}")
    if r.get("popups_blocked"):
        parts.append("popup bloqueado")
    if r.get("console_errors"):
        parts.append(f"erro de console: {r['console_errors'][0][:50]}")
    return "; ".join(parts)


def _allowed_actions(persona: str) -> list[str]:
    no_pointer = PERSONAS[persona].get("no_pointer")
    return sorted(a for a in _ALL_ACTIONS if not (no_pointer and a in _POINTER_ACTIONS))


def _system_prompt(mode: str, persona: str, goal: str, allowed: list[str], vision: bool) -> str:
    about = PERSONAS[persona]["about"]
    seeing = (
        "Voce ve a tela (imagem anexa) e recebe a arvore de acessibilidade." if vision
        else "Voce NAO ve a tela: so recebe a arvore de acessibilidade e os anuncios (como um leitor de tela)."
    )
    if mode == "task":
        role = (
            f"Voce e uma pessoa real usando este site. Persona: {persona} ({about}). {seeing} "
            f"Objetivo dela: {goal}\n"
            "Aja como essa pessoa agiria, um passo por vez, sem conhecer o codigo. Registre em 'friction' qualquer "
            "atrito ou duvida (nome confuso, mudanca silenciosa, foco perdido, caminho longo), mesmo sem falha tecnica. "
            "Se nao conseguir cumprir o objetivo, isso e o achado principal: encerre com outcome=not_completed."
        )
        guide = _guide("ux-persona-testing")
    else:
        role = (
            f"Voce e um revisor de UX e acessibilidade. Persona de teste: {persona} ({about}). {seeing} "
            f"Foco da revisao: {goal}\n"
            "Para cada componente interativo relevante, descubra o que ele REALMENTE e para as pessoas naquele site "
            "(campo de texto, combobox, lista de selecao, menu de acoes, navegacao, acordeao, abas, dialogo...), "
            "PROVANDO o comportamento (aja e observe o efeito), e compare com o que ele expoe hoje. Para design, use a "
            "linguagem do proprio site. Registre cada achado em 'friction' com a evidencia. Encerre quando tiver coberto "
            "os componentes mais importantes (nao precisa de todos)."
        )
        guide = _guide("component-identity-guide") + "\n\n" + _guide("design-language-review")[:2500]
    return (
        f"{role}\n\nAcoes permitidas AGORA: {', '.join(allowed)}, finish. "
        "Responda SOMENTE com um objeto JSON: "
        '{"thought": "o que voce percebe e por que age assim, em portugues corrido e natural", '
        '"friction": "atrito ou achado deste passo, ou null", '
        '"action": {"type": "<acao>", "target": "<id do dossie, ex.: e12, ou css:seletor>", "value": "<tecla/texto/opcao>"} '
        'OU {"type": "finish", "outcome": "completed|completed_with_friction|not_completed", "summary": "..."}}. '
        "target so nas acoes que precisam de alvo. Para press use nomes de tecla (Tab, Shift+Tab, Enter, Space, Escape, "
        "ArrowDown...). Nao invente ids: use os da lista de elementos.\n\n"
        f"CONHECIMENTO DE APOIO (guias do servidor):\n{guide}"
    )


def _observation_text(obs: dict[str, Any], elements: list[str], history: list[str], step: int, max_steps: int) -> str:
    tree = "\n".join(obs["accessibility_tree"][:TREE_LINES_IN_PROMPT])
    hist = "\n".join(history[-HISTORY_LINES:]) or "(primeiro passo)"
    ann = "; ".join(a["text"] for a in obs.get("recent_announcements", [])) or "(nada)"
    focus = obs.get("focus")
    return (
        f"PASSO {step}/{max_steps}\nURL: {obs['url']}\nTitulo: {obs['title']}\n"
        f"Foco: {focus['tag'] + ' ' + repr(focus['name']) if focus else 'nenhum'}\n"
        f"Anuncios recentes: {ann}\n\nHISTORICO:\n{hist}\n\n"
        f"ELEMENTOS INTERATIVOS (fatos):\n" + "\n".join(elements) + f"\n\nARVORE DE ACESSIBILIDADE:\n{tree}"
    )


async def run_agent(
    *,
    session: Session,
    ask: AskFn,
    mode: str,
    goal: str,
    url: str | None,
    html: str | None,
    persona: str = "default",
    max_steps: int = 25,
    vision: bool = True,
    progress: ProgressFn | None = None,
) -> dict[str, Any]:
    if mode not in ("task", "review"):
        raise SessionError("mode deve ser task ou review")
    if not goal.strip():
        raise SessionError("informe o objetivo (task) ou o foco da revisao")
    max_steps = max(1, min(int(max_steps), MAX_STEPS_CEILING))
    started = time.monotonic()
    opened = await session.open(url, html, persona)
    see = vision and not PERSONAS[persona].get("no_visual")
    allowed = _allowed_actions(persona)
    system = _system_prompt(mode, persona, goal, allowed, see)
    narration: list[str] = []
    frictions: list[str] = []
    steps: list[dict[str, Any]] = []
    history: list[str] = []
    model_calls = 0
    stopped_by = "step_limit"
    outcome = "not_completed"
    summary = ""
    repeats: dict[str, int] = {}
    try:
        for step in range(1, max_steps + 1):
            if time.monotonic() - started > TIME_BUDGET_S:
                stopped_by = "time_budget"
                break
            obs = await session.observe()
            dossier = await session.dossier("", DOSSIER_LINES_IN_PROMPT)
            elements = [compact_element(e) for e in dossier.get("elements", [])]
            shot = [await session.screenshot()] if see else None
            prompt = f"{system}\n\n{_observation_text(obs, elements, history, step, max_steps)}"
            decision: dict[str, Any] | None = None
            for attempt in (1, 2):
                model_calls += 1
                raw = await ask(prompt if attempt == 1 else prompt + "\n\nSua resposta anterior nao era um JSON valido. Responda SOMENTE com o JSON pedido.", shot, 900)
                if raw is None:
                    stopped_by = "model_unavailable"
                    break
                parsed = extract_json(raw, "object")
                if isinstance(parsed, dict) and isinstance(parsed.get("action"), dict) and parsed["action"].get("type"):
                    decision = parsed
                    break
            if decision is None:
                stopped_by = stopped_by if stopped_by == "model_unavailable" else "model_invalid_output"
                break
            thought = str(decision.get("thought") or "").strip()
            if decision.get("friction"):
                frictions.append(f"Passo {step}: {str(decision['friction']).strip()}")
            action = decision["action"]
            kind = str(action.get("type"))
            narration.append(f"Passo {step}: {thought or '(sem comentario)'}")
            if progress:
                await progress(step, max_steps, thought[:120] or kind)
            if kind == "finish":
                outcome = str(action.get("outcome") or "completed_with_friction")
                summary = str(action.get("summary") or "")
                stopped_by = "finished"
                steps.append({"step": step, "action": "finish", "outcome": outcome})
                break
            record = {"step": step, "action": kind, "target": action.get("target"), "value": action.get("value")}
            problem = None
            if kind not in allowed:
                problem = f"acao '{kind}' nao permitida para a persona {persona}. Permitidas: {', '.join(allowed)}"
            elif kind in _TARGET_ACTIONS and not action.get("target"):
                problem = f"a acao '{kind}' precisa de target"
            if problem:
                record["refused"] = problem
                history.append(f"{step}. {kind} -> RECUSADA pelo servidor: {problem}")
            else:
                sig = hashlib.sha1(json.dumps([kind, action.get("target"), action.get("value"), obs["url"], obs["focus"]], sort_keys=True, default=str).encode()).hexdigest()
                repeats[sig] = repeats.get(sig, 0) + 1
                if repeats[sig] >= REPEAT_LIMIT:
                    stopped_by = "repeated_action"
                    record["refused"] = f"mesma acao no mesmo estado {REPEAT_LIMIT} vezes"
                    steps.append(record)
                    break
                try:
                    if kind == "reach":
                        result = await session.reach(str(action["target"]))
                        eff = f"Tab ate o alvo: alcancado={result['reached']} apos {result['tab_presses']} Tab" + (f" ({result.get('reason')})" if result.get("reason") else "")
                    elif kind == "announce":
                        result = await session.announce(str(action["target"]))
                        eff = "leitor de tela recebe: " + " ".join(result["accessibility_tree"].split())[:160]
                    else:
                        result = await session.act(kind, str(action.get("target") or ""), str(action.get("value") or ""))
                        eff = effect_summary(result)
                    record["effect"] = eff
                    history.append(f"{step}. {kind} {action.get('target') or ''} {action.get('value') or ''} -> {eff}".replace("  ", " "))
                except Exception as e:  # noqa: BLE001 - erro da acao vira observacao para o modelo decidir
                    record["error"] = f"{type(e).__name__}: {str(e)[:160]}"
                    history.append(f"{step}. {kind} {action.get('target') or ''} -> ERRO: {record['error']}")
            steps.append(record)
            await asyncio.sleep(0)  # ponto de cancelamento cooperativo
        report = await _write_report(ask, mode, goal, persona, narration, frictions, steps, outcome, summary, stopped_by)
        model_calls += 1
    finally:
        await session.close()
    return {
        "outcome": outcome, "stopped_by": stopped_by, "report": report, "narration": narration,
        "frictions": frictions, "steps": steps,
        "facts": {"mode": mode, "persona": persona, "opened": opened["opened"], "steps_used": len(steps),
                  "max_steps": max_steps, "model_calls": model_calls, "vision": bool(see),
                  "elapsed_s": round(time.monotonic() - started, 1)},
        "not_verified": NOT_VERIFIED,
    }


async def _write_report(
    ask: AskFn, mode: str, goal: str, persona: str, narration: list[str], frictions: list[str],
    steps: list[dict[str, Any]], outcome: str, summary: str, stopped_by: str,
) -> str:
    log = "\n".join(
        f"{s['step']}. {s['action']} {s.get('target') or ''} {s.get('value') or ''} -> "
        f"{s.get('effect') or s.get('error') or s.get('refused') or s.get('outcome') or ''}" for s in steps
    )
    limits = {
        "step_limit": "a execucao atingiu o limite de passos antes de terminar",
        "time_budget": "a execucao atingiu o limite de tempo",
        "repeated_action": "a execucao parou por repetir a mesma acao no mesmo estado (possivel laco)",
        "model_unavailable": "o modelo deixou de responder",
        "model_invalid_output": "o modelo nao devolveu um formato valido",
        "finished": "o proprio usuario simulado encerrou",
    }.get(stopped_by, stopped_by)
    prompt = (
        "Escreva o RELATORIO desta sessao em portugues, em texto corrido e humano, para quem constroi o site. "
        + ("Modo: tarefa de usuario." if mode == "task" else "Modo: revisao de componentes e design.")
        + f"\nPersona: {persona}\nObjetivo/foco: {goal}\nDesfecho: {outcome}. Como terminou: {limits}.\n"
        f"Resumo do proprio agente: {summary or '(nenhum)'}\n\nO QUE VOCE PERCEBEU PASSO A PASSO:\n" + "\n".join(narration)
        + "\n\nATRITOS E ACHADOS REGISTRADOS:\n" + ("\n".join(frictions) or "(nenhum)") + f"\n\nLOG DE ACOES:\n{log}\n\n"
        "Estruture: 1) o que aconteceu e se deu para cumprir o objetivo; 2) achados ordenados por gravidade "
        "(bloqueio, serio, moderado, leve), cada um com a evidencia observada, por que importa para a pessoa e a "
        "correcao que mantem o design do site; 3) o que voce NAO conseguiu verificar. Nao chame de acessivel algo so "
        "porque nada falhou; diga o que foi de fato provado."
    )
    raw = await ask(prompt, None, 1800)
    return raw or "(o modelo nao respondeu ao pedido de relatorio; use a narracao e os atritos abaixo)"


__all__ = ["NOT_VERIFIED", "compact_element", "effect_summary", "run_agent"]
