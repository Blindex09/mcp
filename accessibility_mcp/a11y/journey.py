"""Percurso: uma sequencia de acoes feita como a pessoa faria, com os fatos de CADA passo medidos automaticamente.

Em vez de repetir uma sonda por tela, o percurso passa por todas as trocas de etapa de um assistente (ou de uma compra) e diz, passo a passo:
onde ficou o foco, se o conteudo mudou, se alguem que nao ve a tela foi avisado e se digitar mudou o foco sozinho. Nao interpreta: devolve
fatos e as verificacoes do contrato (WCAG 2.4.3, 3.2.2, 4.1.3). Quem opera decide o que e' defeito.
"""

from __future__ import annotations

import json
from typing import Any

ACTIONS = ("click", "press", "type", "focus", "select", "wait", "hover")


def _same(a: Any, b: Any) -> bool:
    return json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)


def judge(step: dict[str, Any], effect: dict[str, Any]) -> list[dict[str, Any]]:
    """Verificacoes do contrato para UM passo, a partir do relatorio de efeito de `Session.act`."""
    issues: list[dict[str, Any]] = []
    before, after = effect.get("focus_before"), effect.get("focus_after")
    added, removed = effect.get("tree_added") or [], effect.get("tree_removed") or []
    announced = bool(effect.get("announcements"))
    changed = bool(added or removed or effect.get("url_changed"))
    action = step.get("action")
    label = step.get("label") or f"{action} {step.get('target') or ''}".strip()
    if action in ("click", "press") and changed:
        if after is None:
            issues.append({"step": label, "criterion": "2.4.3", "check": "foco_cai_no_corpo",
                           "fact": f"depois de {label} o conteudo mudou e o foco ficou no corpo da pagina (focus_before={before and before.get('name')!r})"})
        elif _same(before, after) and removed:
            issues.append({"step": label, "criterion": "2.4.3", "check": "foco_fica_para_tras",
                           "fact": f"o foco continua em {after.get('name')!r} e o conteudo novo fica fora do caminho do Tab (removido={removed[:2]})"})
        if not announced and (after is None or _same(before, after)):
            issues.append({"step": label, "criterion": "4.1.3", "check": "mudanca_nao_anunciada",
                           "fact": f"o conteudo mudou ({len(added)} linhas novas) sem regiao viva e sem mover o foco para ele"})
    if action == "type" and before is not None and after is not None and not _same(before, after):
        issues.append({"step": label, "criterion": "3.2.2", "check": "foco_pula_ao_digitar",
                       "fact": f"digitar mudou o foco de {before.get('name')!r} para {after.get('name')!r} sem a pessoa pedir"})
    return issues


async def run(session: Any, steps: list[dict[str, Any]], stop_on_error: bool = True) -> dict[str, Any]:
    """Executa os passos em ordem com `session.act` (as regras da persona e a aprovacao de envios continuam valendo)."""
    report: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    for index, step in enumerate(steps, 1):
        action = str(step.get("action") or "").lower()
        if action not in ACTIONS:
            report.append({"n": index, "error": f"acao invalida: {action!r}. Use uma de {', '.join(ACTIONS)}"})
            if stop_on_error:
                break
            continue
        try:
            effect = await session.act(action, str(step.get("target") or ""), str(step.get("value") or ""))
        except Exception as e:  # noqa: BLE001 - o passo falhou: o relatorio diz qual e por que
            report.append({"n": index, "label": step.get("label") or action, "error": str(e)[:300]})
            if stop_on_error:
                break
            continue
        found = judge({**step, "action": action}, effect)
        issues.extend(found)
        report.append({
            "n": index, "label": step.get("label") or f"{action} {step.get('target') or ''}".strip(),
            "focus_before": effect.get("focus_before") and effect["focus_before"].get("name"),
            "focus_after": effect.get("focus_after") and effect["focus_after"].get("name"),
            "tree_added": (effect.get("tree_added") or [])[:4], "tree_removed": (effect.get("tree_removed") or [])[:3],
            "announced": [a.get("text", "")[:80] for a in (effect.get("announcements") or [])][:3],
            "url_changed": effect.get("url_changed"), "issues": [i["check"] for i in found],
        })
    return {
        "journey": report, "issues": issues,
        "summary": (f"{len(issues)} verificacoes do contrato nao foram atendidas em {len(report)} passos" if issues
                    else f"nenhuma verificacao automatica falhou em {len(report)} passos (isso nao prova acessibilidade)"),
        "note": "fatos medidos em cada passo; o julgamento (e se o desvio e' defeito) e' de quem opera. Cite o numero do passo no a11y_finding.",
    }
