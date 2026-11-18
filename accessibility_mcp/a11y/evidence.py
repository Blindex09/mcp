"""Evidencia de fontes que nao sao a sessao de teclado: NVDA real, axe, contraste, mapa da pagina e dossie.

Por que existe: `a11y_finding` so confirma uma falha (`failed`) quando cita passos do rastro (`a11y_trace`) da sessao. Antes, so as acoes e
as sondagens do teclado escreviam nesse rastro; o que o NVDA real falou na VM, a medicao do axe, a do contraste, o mapa da pagina e o dossie
nao tinham passo para citar e o achado ficava `cantTell` mesmo com a observacao boa.

Aqui cada uma dessas fontes grava UM passo com FATOS compactos (o que o NVDA falou, o que o axe mediu, as cores e a razao, as regioes, os
nomes dos controles), sem veredito, e a ferramenta devolve `trace_step` na resposta para o modelo citar em `evidence_steps`.
O servidor so registra o que a fonte devolveu; quem julga continua sendo o modelo do cliente.
"""

from __future__ import annotations

from typing import Any

from .session import SESSION

MAX_LINES = 40  # falas guardadas por passo (o resto continua na resposta da ferramenta)
LINE_CHARS = 200
MAX_ITEMS = 60  # controles do dossie guardados por passo


def _clip(value: Any, n: int = LINE_CHARS) -> str:
    text = " ".join(str(value if value is not None else "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


def record(kind: str, facts: dict[str, Any], target: str | None = None, value: str | None = None) -> int | None:
    """Grava um passo no rastro da sessao e devolve o numero dele. Nunca derruba a ferramenta: sem rastro, devolve None."""
    try:
        return int(SESSION.log_trace(kind, target, value, facts))
    except Exception:  # noqa: BLE001 - evidencia e' bonus: a ferramenta de origem segue funcionando
        return None


def with_step(data: Any, step: int | None) -> Any:
    """Acrescenta `trace_step` a resposta (dict) para o modelo citar o passo em a11y_finding."""
    if step and isinstance(data, dict):
        return {**data, "trace_step": step}
    return data


def _lines(passos: Any) -> list[str]:
    out: list[str] = []
    for p in passos or []:
        fala = p.get("fala") if isinstance(p, dict) else p
        out.append(_clip(fala))
        if len(out) >= MAX_LINES:
            break
    return out


# ---------------------------------------------------------------- NVDA real

def nvda_session(action: str, command: dict[str, Any], result: dict[str, Any]) -> int | None:
    """Um comando da sessao aberta do NVDA (a11y_nvda_open/do/close): o que o NVDA falou, tal como veio da VM."""
    falas = _lines(result.get("passos"))
    if not falas and result.get("fala"):
        falas = [_clip(result["fala"])]
    facts: dict[str, Any] = {
        "fonte": "NVDA real (Guidepup) numa VM Windows", "acao": action, "tecla": command.get("tecla"),
        "repetir": command.get("repetir"), "reverso": bool(command.get("reverso")) or None,
        "url": result.get("url") or command.get("url"), "titulo_original": result.get("titulo_original") or result.get("titulo"),
        "falas": falas, "parou_por": result.get("parou_por"), "continua": result.get("continua"),
    }
    return record("nvda:" + action, {k: v for k, v in facts.items() if v not in (None, [], "")}, command.get("tecla"), str(command.get("repetir") or "") or None)


def nvda_speech(facts_in: dict[str, Any]) -> int | None:
    """O percurso fixo de a11y_nvda_speech (Tab, leitura, atalhos de letra, teclas pedidas)."""
    shortcuts = {cat: _lines(items) for cat, items in (facts_in.get("shortcuts") or {}).items()}
    facts: dict[str, Any] = {
        "fonte": facts_in.get("source"), "url": facts_in.get("url"), "tab": _lines(facts_in.get("tab_walk")),
        "leitura": _lines(facts_in.get("reading_mode")), "atalhos": {k: v for k, v in shortcuts.items() if v},
        "teclas": _lines(facts_in.get("key_sequence")), "erro": facts_in.get("error"),
    }
    return record("nvda:speech", {k: v for k, v in facts.items() if v not in (None, [], {}, "")})


# ---------------------------------------------------------------- axe e contraste

def axe(result: dict[str, Any], url: str, level: str) -> int | None:
    """Resultado do axe-core: regras, impacto, ocorrencias e o primeiro elemento de cada violacao (com a medida, ex.: razao de contraste)."""
    violations = []
    for v in (result.get("violations") or [])[:12]:
        examples = [{"alvo": _clip((e.get("target") or [""])[0], 120), "medida": _clip(e.get("fix"), 260)} for e in (v.get("examples") or [])[:3]]
        violations.append({"regra": v.get("id"), "impacto": v.get("impact"), "ocorrencias": v.get("occurrences"), "exemplos": examples})
    review = [{"regra": r.get("id"), "ocorrencias": r.get("occurrences")} for r in (result.get("needs_manual_review") or [])[:12]]
    facts = {"fonte": "axe-core", "url": url, "nivel": level, "violacoes": violations, "a_revisar": review, "passaram": result.get("passes")}
    return record("axe", facts, None, url)


def contrast(result: dict[str, Any]) -> int | None:
    """Razao de contraste calculada entre duas cores (a11y_contrast)."""
    return record("measure:contrast", {"fonte": "a11y_contrast", **{k: v for k, v in result.items() if isinstance(v, (str, int, float, bool))}})


# ---------------------------------------------------------------- mapa da pagina e dossie

def page_map(data: dict[str, Any]) -> int | None:
    """Resumo do mapa da pagina: documento, titulos, regioes, imagens, links, campos e regioes vivas."""
    main = data.get("main") or {}
    headings = main.get("headings") or {}
    landmarks = main.get("landmarks") or {}
    images = main.get("images") or {}
    forms = main.get("forms") or {}
    links = main.get("links") or {}
    facts = {
        "fonte": "a11y_page_map", "url": main.get("url"), "documento": {k: (main.get("document") or {}).get(k) for k in ("lang", "title")},
        "titulos": {"total": headings.get("total"), "h1": headings.get("h1_count"), "saltos": headings.get("level_jumps"),
                    "sumario": [{"nivel": h.get("level"), "texto": _clip(h.get("text"), 80)} for h in (headings.get("outline") or [])[:15]]},
        "regioes": {"total": landmarks.get("total"), "itens": [{"papel": i.get("role"), "nome": i.get("name")} for i in (landmarks.get("items") or [])[:20]],
                    "repetidas_sem_nome_distinto": landmarks.get("repeated_without_distinct_name"),
                    "tem_main": any(i.get("role") == "main" or i.get("tag") == "main" for i in (landmarks.get("items") or []))},
        "imagens": {"total": images.get("total"), "img_sem_atributo_alt": sum(1 for i in (images.get("items") or []) if i.get("tag") == "img" and i.get("alt") is None)},
        "links": {"total": links.get("total"), "sem_texto": links.get("empty_text"), "mesmo_texto_destino_diferente": len(links.get("same_text_different_destination") or [])},
        "campos": {"total": forms.get("fields_total"), "sem_nome": forms.get("fields_without_any_name")},
        "regioes_vivas": len(main.get("live_regions") or []), "iframes": len(main.get("iframes") or []),
    }
    return record("page_map", facts)


def dossier(data: dict[str, Any]) -> int | None:
    """Resumo do dossie: para cada controle, id, tag, papel, nome acessivel e estados principais."""
    items = []
    for e in (data.get("elements") or [])[:MAX_ITEMS]:
        computed = e.get("computed") or {}
        states = e.get("states") or {}
        items.append({
            "id": e.get("id"), "tag": e.get("tag"), "papel": computed.get("role") or e.get("role_attr"),
            "nome": _clip(computed.get("name") or (e.get("attrs") or {}).get("aria_label") or e.get("text"), 80),
            "pressionado": states.get("pressed"), "expandido": states.get("expanded"), "focavel": e.get("focusable"),
        })
    facts = {"fonte": "a11y_dossier", "url": data.get("url"), "total_descobertos": data.get("discovered_total"), "controles": items}
    return record("dossier", facts)
