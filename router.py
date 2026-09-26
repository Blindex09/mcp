"""Roteador semantico: escolhe qual modelo atende cada pedido, gastando o minimo que ainda entregue um resultado correto.

Regras mestras: quem decide e um MODELO, lendo o sentido do pedido; nada de palavra-chave, regex, tabela de dificuldade ou
limiar. O codigo so entrega os fatos ao modelo, valida fatos objetivos e impoe o que e configuracao.

Desenho (o que a pesquisa recomenda, sem depender de rotulos nem de probabilidades internas, que a API nao da):

1. Pre-roteador semantico. Um modelo barato le a FINALIDADE do pedido (texto livre de quem chama), um resumo do contexto, fatos
   objetivos (tamanho, imagens anexas, saida esperada), os resultados recentes e as licoes aprendidas, e escolhe a camada e se a
   resposta precisa de conferencia. As licoes entram no proprio prompt (aprendizado em contexto): o roteador se adapta sem retreino.
2. Cascata por fatos. A resposta barata so sobe de camada quando (a) nao veio, (b) a validacao objetiva de quem chamou falhou ou
   (c) um verificador INDEPENDENTE e mais forte, so quando o roteador pediu, a julgou inadequada. Nunca pela confianca que o proprio
   modelo declara: essa confianca quase nao depende da resposta.
3. Aprendizado. Cada rota e cada subida viram linhas de resultado; ao fim da execucao o modelo de memoria (a11y/learn.py) decide
   que licoes guardar no escopo de roteamento, e elas voltam ao prompt do roteador.

Economia: com um so modelo configurado (ou o mesmo nas duas camadas) nao ha o que escolher, entao nao ha chamada de roteamento.
Falha segura: sem decisao valida do roteador, vale a camada forte (qualidade primeiro).
"""

from __future__ import annotations

from collections import Counter, deque
from typing import Any

import llm
from a11y import learn
from llm import Hint

__all__ = ["ROUTING_SCOPE", "Hint", "ask_routed", "drain_outcomes", "reset", "stats"]

ROUTING_SCOPE = "roteamento"
ROUTER_TOKENS = 200  # orcamento de saida do roteador e do verificador: so um JSON curto
VERIFIER_TOKENS = 200
LESSON_CHARS = 2000
CLIP_CHARS = 3500  # quanto do pedido e da resposta o verificador le

_STATS: Counter[str] = Counter()
_OUTCOMES: deque[str] = deque(maxlen=40)  # o que vira digest de aprendizado (entregue uma vez)
_RECENT: deque[str] = deque(maxlen=8)  # o que o roteador ve como experiencia recente desta execucao


def reset() -> None:
    _STATS.clear()
    _OUTCOMES.clear()
    _RECENT.clear()


def stats() -> dict[str, Any]:
    """Contadores para provar a economia (nao ha estado escondido): quantas rotas, para onde, quantas subidas e por que."""
    keys = ("calls", "router_calls", "to_fast", "to_main", "router_fallbacks", "escalated_by_fact",
            "escalated_by_verifier", "verifier_calls")
    return {**{k: _STATS[k] for k in keys}, "active": _tiers() is not None}


def drain_outcomes() -> str:
    """Resultados de roteamento ainda nao aprendidos, para o digest de aprendizado. Entregues uma unica vez."""
    text = "\n".join(_OUTCOMES)
    _OUTCOMES.clear()
    return text


def _tiers() -> tuple[str, str] | None:
    """(modelo barato, modelo forte), ou None quando nao ha escolha: sem provedor, sem modelo, ou o mesmo modelo nas duas camadas."""
    if llm.configured_backend() is None:
        return None
    main, fast = llm._model_for("main"), llm._model_for("fast")
    if not main or not fast or fast == main:
        return None
    return fast, main


def _lessons() -> str:
    if not learn.enabled():
        return ""
    entries = [e for e in learn.load_all() if e.get("scope") == ROUTING_SCOPE]
    return "\n".join(f"- {e['topic']}: {e['learning']}" for e in entries)[:LESSON_CHARS]


def _note(hint: Hint, line: str) -> None:
    entry = f"{hint.purpose[:100]} | {line}"
    _OUTCOMES.append(entry)
    _RECENT.append(entry)


def _router_prompt(prompt: str, images: list[bytes] | None, max_tokens: int, hint: Hint, fast: str, main: str) -> str:
    recent = "\n".join(f"- {r}" for r in _RECENT)
    lessons = _lessons()
    return (
        "Voce e o ROTEADOR de um servidor de testes de acessibilidade. Decida qual modelo deve atender o pedido abaixo, gastando o "
        "minimo que ainda entregue um resultado correto.\n"
        f"Modelos: fast = {fast} (mais barato e rapido); main = {main} (mais capaz e mais caro). Use o que voce sabe sobre eles.\n"
        "Julgue pelo SENTIDO deste pedido: quao dificil ele e, quanto depende de raciocinio ou de evidencia visual, e o que custa uma "
        "resposta errada (um passo desperdicado se corrige no seguinte; um relatorio final errado engana quem le). Nao ha regra fixa "
        "nem tabela: cada pedido e decidido por si.\n"
        "Se escolher fast, diga tambem se a resposta deve ser CONFERIDA por um verificador independente e mais forte (verify true): "
        "so quando um erro seria caro e nao puder ser checado por fato objetivo.\n\n"
        f"FINALIDADE: {hint.purpose}\nCONTEXTO: {hint.brief or '(sem contexto adicional)'}\n"
        f"FATOS: o pedido tem {len(prompt)} caracteres; {len(images or [])} imagem(ns) anexa(s), que voce nao ve; "
        f"a saida esperada e de ate {max_tokens} tokens.\n"
        + (f"\nRESULTADOS RECENTES DESTA EXECUCAO (camada usada e se precisou subir):\n{recent}\n" if recent else "")
        + (f"\nLICOES APRENDIDAS SOBRE ROTEAMENTO:\n{lessons}\n" if lessons else "")
        + '\nResponda SOMENTE com JSON: {"tier": "fast" ou "main", "verify": true ou false, "reason": "uma frase"}'
    )


async def _choose(
    ctx: Any, prompt: str, images: list[bytes] | None, max_tokens: int, hint: Hint, fast: str, main: str
) -> tuple[str, bool]:
    _STATS["router_calls"] += 1
    raw = await llm.ask_model(ctx, _router_prompt(prompt, images, max_tokens, hint, fast, main), ROUTER_TOKENS, None, "fast")
    data = llm.extract_json(raw, "object")
    tier = data.get("tier") if isinstance(data, dict) else None
    if not isinstance(data, dict) or tier not in ("fast", "main"):  # fato objetivo: a camada devolvida existe? Senao, qualidade primeiro
        _STATS["router_fallbacks"] += 1
        return "main", False
    return str(tier), bool(data.get("verify") is True and tier == "fast")


async def _verify(ctx: Any, prompt: str, reply: str, hint: Hint) -> tuple[bool, str]:
    """Conferencia independente (camada forte, so texto): a resposta cumpre o pedido? Devolve (adequada, problema).
    Sem resposta legivel do verificador, aceita: a chamada barata ja foi paga e nao ha fato contra ela."""
    _STATS["verifier_calls"] += 1
    vprompt = (
        "Voce e o VERIFICADOR de um servidor de testes de acessibilidade. Um modelo menor respondeu ao pedido abaixo. Confira, pelo "
        "SENTIDO, se a resposta cumpre o pedido: completa, coerente com o que foi pedido e sem afirmar o que o pedido nao sustenta. "
        "Nao estime confianca nem adivinhe: julgue o que da para julgar so pelo texto (voce nao ve imagens). Se nao da para julgar, "
        "diga adequate true e explique em problem.\n\n"
        f"FINALIDADE: {hint.purpose}\n\nPEDIDO:\n{prompt[:CLIP_CHARS]}\n\nRESPOSTA A CONFERIR:\n{reply[:CLIP_CHARS]}\n\n"
        'Responda SOMENTE com JSON: {"adequate": true ou false, "problem": "o que esta errado, em uma frase"}'
    )
    data = llm.extract_json(await llm.ask_model(ctx, vprompt, VERIFIER_TOKENS, None, "main"), "object")
    if not isinstance(data, dict) or not isinstance(data.get("adequate"), bool):
        return True, ""
    return data["adequate"], str(data.get("problem") or "")[:200]


async def ask_routed(
    ctx: Any, prompt: str, *, images: list[bytes] | None = None, max_tokens: int = 800, hint: Hint | None = None
) -> str | None:
    """Pergunta ao modelo certo. None = nenhum respondeu. Sem dica ou sem escolha possivel, vai direto a camada forte."""
    _STATS["calls"] += 1
    tiers = _tiers()
    if tiers is None or hint is None:
        return await llm.ask_model(ctx, prompt, max_tokens, images, "main")
    fast, main = tiers
    tier, verify = await _choose(ctx, prompt, images, max_tokens, hint, fast, main)
    if tier == "main":
        _STATS["to_main"] += 1
        _note(hint, "camada main (escolha do roteador ou falha segura)")
        return await llm.ask_model(ctx, prompt, max_tokens, images, "main")
    _STATS["to_fast"] += 1
    reply = await llm.ask_model(ctx, prompt, max_tokens, images, "fast")
    why = ""
    if reply is None:
        why = "a camada barata nao respondeu"
        _STATS["escalated_by_fact"] += 1
    elif hint.validate is not None and not hint.validate(reply):
        why = "a validacao objetiva da resposta falhou"
        _STATS["escalated_by_fact"] += 1
    elif verify:
        adequate, problem = await _verify(ctx, prompt, reply, hint)
        if not adequate:
            why = f"o verificador julgou inadequada ({problem or 'sem detalhe'})"
            _STATS["escalated_by_verifier"] += 1
    if not why:
        _note(hint, "camada fast, atendida sem subir" + (" (conferida)" if verify else ""))
        return reply
    _note(hint, f"camada fast, subiu para main: {why}")
    better = await llm.ask_model(ctx, prompt, max_tokens, images, "main")
    return better if better is not None else reply  # se a forte tambem falhar, uma resposta ainda vale mais que nenhuma
