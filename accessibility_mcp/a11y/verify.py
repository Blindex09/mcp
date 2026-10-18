"""Verificador: confere cada achado contra a EVIDENCIA medida antes de ele chegar ao relatorio.

A pesquisa (Flow-A11y, 2026) mostrou que agentes acham muito mas afirmam coisa que a evidencia nao sustenta (precisao baixa);
o remedio e' calibrar: so vale o que o rastro prova, e o que nao da para afirmar vira `cantTell`.

Divisao de papeis:
- O CODIGO monta o pacote de evidencia (passos citados, fatos do elemento) e valida o formato da resposta;
- um MODELO diz, para cada achado, se a evidencia o sustenta (supported), o refuta (unsupported) ou nao permite dizer (cantTell).
Sem pacote de evidencia nem chamada ao modelo: o achado vira cantTell na hora. Sem resposta valida do modelo: cantTell, nunca failed.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

from accessibility_mcp.llm import extract_json

AskFn = Callable[..., Awaitable[str | None]]
VERDICTS = ("supported", "unsupported", "cantTell")
PACKET_CHARS = 1400

_PROMPT = (
    "Voce e um revisor cetico de achados de acessibilidade. Para CADA achado abaixo, decida SOMENTE pelas evidencias medidas "
    "que acompanham o achado (passos executados e fatos do elemento), nunca pelo que voce acha provavel.\n"
    "- supported: as evidencias MOSTRAM o que o achado afirma.\n"
    "- unsupported: as evidencias CONTRADIZEM o achado (ex.: o achado diz que falta um atributo e o fato do elemento mostra que ele existe, "
    "ou diz que o foco se perdeu e o passo mostra o foco no lugar certo).\n"
    "- cantTell: as evidencias nao mostram nem contradizem (falta o fato para confirmar). Na duvida, use cantTell.\n"
    "Uma afirmacao especifica (um atributo ARIA, um estado, um comportamento de teclado) so e supported se aparece nas evidencias.\n"
    "Responda SOMENTE com JSON: "
    '{"verdicts": [{"id": "f1", "verdict": "supported|unsupported|cantTell", "reason": "uma frase simples e direta"}]}\n\n'
)


def packet_of(finding: dict[str, Any], trace: dict[int, dict[str, Any]], elements: dict[str, dict[str, Any]]) -> str:
    """O que a evidencia mostra: os passos citados e os fatos do elemento. Vazio = nada para conferir."""
    parts: list[str] = []
    for n in finding.get("evidence_steps", []):
        t = trace.get(n)
        if t:
            parts.append(f"passo {n}: {t.get('action')} {t.get('target') or ''} {t.get('value') or ''} -> {t.get('effect') or t.get('error') or t.get('refused') or ''}".strip())
            if t.get("facts"):
                parts.append("fatos do passo " + str(n) + ": " + json.dumps(t["facts"], ensure_ascii=False, default=str)[:600])
    el = elements.get(finding.get("target") or "")
    if el:
        parts.append("fatos do elemento " + str(finding["target"]) + ": " + json.dumps(el.get("brief"), ensure_ascii=False, default=str)[:700])
    return "\n".join(parts)[:PACKET_CHARS]


async def verify(ask: AskFn, findings: list[dict[str, Any]], trace: dict[int, dict[str, Any]], elements: dict[str, dict[str, Any]], page_facts: str = "") -> int:
    """Atualiza `outcome` e `verification` de cada achado. Devolve quantas chamadas ao modelo foram feitas (0 ou 1-2)."""
    packets: dict[str, str] = {}
    for f in findings:
        packet = packet_of(f, trace, elements)
        if packet:
            packets[f["id"]] = packet
        else:
            f["outcome"], f["verification"] = "cantTell", {"verdict": "cantTell", "reason": "nenhuma evidencia valida acompanha o achado: nao da para confirmar"}
    if not packets:
        return 0
    body = "".join(
        f"ACHADO {f['id']} (criterio {f.get('criterion') or 'nenhum'}, gravidade {f['severity']}): {f['claim']}\nEVIDENCIAS:\n{packets[f['id']]}\n\n"
        for f in findings if f["id"] in packets
    )
    prompt = _PROMPT + (f"FATOS GERAIS DA PAGINA:\n{page_facts[:1800]}\n\n" if page_facts else "") + body
    calls = 0
    verdicts: dict[str, dict[str, str]] = {}
    for attempt in (1, 2):
        calls += 1
        raw = await ask(prompt if attempt == 1 else prompt + "\nSua resposta anterior nao era o JSON pedido. Responda SOMENTE com o JSON.", None, 1200, tier="main")
        if raw is None:
            break
        parsed = extract_json(raw, "object")
        items = parsed.get("verdicts") if isinstance(parsed, dict) else None
        if isinstance(items, list):
            for it in items:
                if isinstance(it, dict) and it.get("id") in packets and it.get("verdict") in VERDICTS:
                    verdicts[str(it["id"])] = {"verdict": str(it["verdict"]), "reason": " ".join(str(it.get("reason") or "").split())[:240]}
            break
    for f in findings:
        if f["id"] not in packets:
            continue
        v = verdicts.get(f["id"]) or {"verdict": "cantTell", "reason": "o verificador nao respondeu sobre este achado: nao confirmado"}
        f["verification"] = v
        f["outcome"] = {"supported": "failed", "unsupported": "unsupported", "cantTell": "cantTell"}[v["verdict"]]
    return calls
