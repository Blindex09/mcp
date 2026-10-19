"""Conferencia objetiva da evidencia de um achado, sem modelo.

Quem julga e' o modelo do cliente (Claude Code, Codex, VS Code...): ele registra o achado com `a11y_finding`, citando os passos do rastro que o provam.
O servidor so confere FATOS: os passos citados existem no rastro, o elemento foi visto na sessao e o criterio WCAG e' um numero real.
Sem evidencia valida o achado fica `cantTell` (nao confirmado), nunca `failed`.
"""

from __future__ import annotations

import json
from typing import Any

PACKET_CHARS = 1400


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
    return chr(10).join(parts)[:PACKET_CHARS]
