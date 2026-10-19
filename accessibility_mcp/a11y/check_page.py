"""Verificacao de comportamento em UMA chamada: abre a pagina, mede, roda as sondas pedidas e fecha.

Para quem nao consegue manter uma sessao aberta entre chamadas (um cliente MCP que sobe o servidor de novo a cada chamada, como o do Qaaccessibility).
O servidor continua sem julgar nada: devolve fatos do teclado e das sondas e uma lista de elementos com um seletor `css` que pode ser usado numa
SEGUNDA chamada como alvo das sondas de contrato. Quem decide o que e' cada elemento, quais sondas rodar e se um desvio e' defeito e' o modelo de quem chama.
"""

from __future__ import annotations

import json
from typing import Any

from .probes import run_probe
from .session import Session, SessionError

PROBE_KINDS_WITHOUT_TARGET = ("tab_walk", "focus_obscured", "target_size")


def parse_probes(raw: str) -> list[dict[str, str]]:
    """Le a lista de sondas pedida: JSON `[{"kind": "dialog", "target": "css:#abrir"}, ...]`. Texto vazio = nenhuma."""
    if not raw or not raw.strip():
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise SessionError(f"probes deve ser um JSON no formato [{{\"kind\": \"dialog\", \"target\": \"css:#abrir\"}}]: {e.msg}") from e
    if not isinstance(data, list) or not all(isinstance(x, dict) and isinstance(x.get("kind"), str) for x in data):
        raise SessionError("probes deve ser uma lista de objetos com \"kind\" (e \"target\" para as sondas que pedem alvo)")
    return [{"kind": x["kind"], "target": str(x.get("target") or ""), "container": str(x.get("container") or "")} for x in data]


def _brief(element: dict[str, Any]) -> dict[str, Any]:
    computed = element.get("computed") or {}
    states = element.get("states") or {}
    return {
        "css": element.get("css"), "tag": element.get("tag"), "role": computed.get("role") or element.get("role_attr"), "name": computed.get("name"),
        "text": element.get("text"), "clickable": element.get("clickable"), "focusable": element.get("focusable"), "actionable": element.get("actionable"),
        "expanded": states.get("expanded"), "haspopup": states.get("haspopup"), "in_shadow": (element.get("where") or {}).get("in_shadow"),
    }


def _page_facts(page_map: dict[str, Any]) -> dict[str, Any]:
    main = page_map.get("main", {})
    headings, links, forms, order = main.get("headings", {}), main.get("links", {}), main.get("forms", {}), main.get("reading_order", {})
    return {
        "h1_count": headings.get("h1_count"), "heading_level_jumps": headings.get("level_jumps"), "landmarks": [x.get("role") for x in main.get("landmarks", {}).get("items", [])],
        "links_same_text_different_destination": len(links.get("same_text_different_destination", [])), "fields_without_any_name": forms.get("fields_without_any_name"),
        "live_regions": len(main.get("live_regions", [])), "reading_order_inverted_pairs": order.get("inverted_pairs"), "hover_reveals": (main.get("hover_reveals") or {}).get("total"),
    }


def _compact_probe(kind: str, target: str, result: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"kind": kind, "target": target or None, "summary": result.get("summary")}
    for key in ("unmet", "checks", "stuck_at", "obscured_stops", "ended_because", "links_sem_parada", "links_sem_parada_nota", "fail_spacing_exception", "smaller_than_24px"):
        if key in result:
            out[key] = result[key]
    return out


async def check_page(
    session: Session, url: str = "", html: str = "", probes: str = "", persona: str = "keyboard", browser: str = "chromium", color_scheme: str = "",
) -> dict[str, Any]:
    """Abre uma sessao descartavel, mede e fecha SEMPRE, mesmo se uma sondagem falhar. Recusa se ja ha uma sessao aberta (nao fecha o trabalho de ninguem)."""
    requested = parse_probes(probes)
    if session.page is not None:
        raise SessionError("ja ha uma sessao aberta: feche com a11y_close ou use as ferramentas de sessao (a11y_probe). Esta ferramenta e' para quem nao mantem sessao entre chamadas")
    opened = await session.open(url or None, html or None, persona, color_scheme or None, browser, "auto")
    try:
        walk = await run_probe(session, "tab_walk")
        sizes = await run_probe(session, "target_size")
        dossier = await session.dossier(max_elements=200)
        page_map = await session.page_map()
        results: list[dict[str, Any]] = []
        for spec in requested:
            try:
                got = await run_probe(session, spec["kind"], spec["target"] or None, spec["container"] or None)
                results.append(_compact_probe(spec["kind"], spec["target"], got))
            except SessionError as e:
                results.append({"kind": spec["kind"], "target": spec["target"] or None, "error": str(e)})
        coverage = session.coverage_report()
        return {
            "opened": {k: opened.get(k) for k in ("opened", "persona", "browser", "title", "limits", "mutations")},
            "tab_walk": {
                "summary": walk["summary"], "stops": [{"tag": s.get("tag"), "name": s.get("name")} for s in walk["stops"] if isinstance(s.get("n"), int)],
                **{k: walk[k] for k in ("ended_because", "stuck_at", "obscured_stops", "offscreen_stops", "links_sem_parada", "links_sem_parada_nota") if k in walk},
            },
            "target_size": _compact_probe("target_size", "", sizes),
            "page_facts": _page_facts(page_map),
            "elements": [_brief(e) for e in dossier["elements"]],
            "elements_not_listed": dossier.get("not_listed_over_limit", 0),
            "probes": results,
            "approvals_pending_dropped": session.pending_approvals(),
            "not_verified": coverage.get("gaps", []) + ["leitor de tela real", "dispositivo real", "fluxos que mudam dados (retidos, nada foi enviado)"],
            "next_step": "para provar um componente use probes=[{\"kind\": \"dialog\"|\"disclosure\"|\"menu\"|\"tabs\"|\"combobox\"|\"listbox\"|\"tree\"|\"tooltip\"|\"form_errors\"|\"status_update\"|\"route_change\", \"target\": \"css:<seletor de elements>\"}] numa nova chamada",
            "note": "fatos medidos; o que cada elemento e' e se um desvio e' defeito e' julgamento de quem chama",
        }
    finally:
        await session.close()
