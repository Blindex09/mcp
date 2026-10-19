"""Achados estruturados: cada achado diz QUAL criterio WCAG, QUAO grave, EM QUAL elemento e COM QUE EVIDENCIA.

Quem decide que algo e' um achado, o criterio e a gravidade e' o MODELO. O codigo so valida fatos objetivos (o criterio existe no
WCAG 2.2? o elemento citado foi visto? os passos citados aconteceram?), guarda, exporta (EARL do W3C e SARIF) e compara execucoes.
Sem evidencia valida o achado nao desaparece: vira `cantTell` (nao consigo afirmar), nunca `failed`.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from . import wcag

SEVERITIES = ("blocker", "serious", "moderate", "minor")
OUTCOMES = ("failed", "cantTell", "passed", "unsupported")  # unsupported: o verificador refutou; sai do relatorio, fica registrado
_TARGET = re.compile(r"e\d+|css:.{1,300}")
ASSERTOR = {"name": "a11y-mcp", "about": "servidor MCP de teste de acessibilidade como usuario (fatos medidos; quem julga e o modelo do cliente)"}


def _clean(text: object, limit: int) -> str:
    return " ".join(str(text or "").split())[:limit]


def build(raw: Any, *, step: int, steps_seen: set[int], elements_seen: dict[str, dict[str, Any]], persona: str, source: str = "model", default_evidence: bool = True) -> tuple[dict[str, Any] | None, list[str]]:
    """Transforma o que o modelo escreveu em um achado, validando so FATOS: devolve (achado | None, problemas notados).

    - criterio: tem que existir no WCAG 2.2, senao fica vazio (e o problema e' anotado);
    - elemento: tem que ser um id visto no dossie (ou css:), senao o alvo e' descartado (referencia invalida);
    - evidencia: so passos que de fato aconteceram, ate o passo atual.
    """
    problems: list[str] = []
    if not isinstance(raw, dict):
        return None, ["achado ignorado: nao e um objeto"]
    claim = _clean(raw.get("claim") or raw.get("description"), 500)
    if not claim:
        return None, ["achado ignorado: sem afirmacao (claim)"]
    criterion = wcag.normalize(raw.get("criterion"))
    if raw.get("criterion") and criterion is None:
        problems.append(f"criterio '{_clean(raw.get('criterion'), 30)}' nao existe no WCAG 2.2: sem criterio")
    severity = _clean(raw.get("severity"), 20).lower()
    if severity not in SEVERITIES:
        severity = "unrated"
    target = _clean(raw.get("target"), 300) or None
    element = None
    if target:
        if not _TARGET.fullmatch(target):
            problems.append(f"alvo '{target[:40]}' invalido: descartado")
            target = None
        elif target.startswith("e") and target not in elements_seen:
            problems.append(f"alvo '{target}' nunca apareceu no dossie: descartado")
            target = None
        elif target in elements_seen:
            element = elements_seen[target].get("descriptor")
    cited = raw.get("evidence_steps")
    cited = cited if isinstance(cited, list) else []
    evidence = sorted({int(s) for s in cited if isinstance(s, (int, float, str)) and str(s).isdigit() and int(s) in steps_seen and int(s) <= step})
    if cited and len(evidence) < len(cited):
        problems.append("parte da evidencia citada nao existe (passo inexistente ou futuro): descartada")
    if not evidence and default_evidence and step - 1 in steps_seen:
        evidence = [step - 1]  # o que o modelo acabou de ver
    finding = {
        "criterion": criterion, "criterion_name": wcag.name_of(criterion) if criterion else None,
        "level": wcag.level_of(criterion) if criterion else None,
        "severity": severity, "claim": claim, "target": target, "element": element, "persona": persona,
        "step": step, "evidence_steps": evidence, "source": source, "outcome": "failed", "notes": problems,
        "verification": None,
    }
    return finding, problems


def element_brief(e: dict[str, Any]) -> dict[str, Any]:
    """Fatos de um elemento do dossie para a evidencia dos achados (so o que existe: nulos e falsos saem)."""
    comp = e.get("computed") or {}

    def present(d: dict[str, Any] | None) -> dict[str, Any]:
        return {k: v for k, v in (d or {}).items() if v not in (None, False, "")}

    return {
        "tag": e["tag"], "type": e.get("type"), "role_attr": e.get("role_attr"), "role": comp.get("role"), "name": comp.get("name") or e.get("text"),
        "focusable": e.get("focusable"), "clickable": e.get("clickable"), "states": present(e.get("states")), "relations": present(e.get("relations")),
        "attrs": present(e.get("attrs")), "tabindex": e.get("tabindex"), "rect": e.get("rect"),
    }


def seen_entry(e: dict[str, Any]) -> dict[str, Any]:
    """O que se guarda de cada elemento visto no dossie: quem ele e (para identificar o achado entre execucoes) e os fatos (para a evidencia)."""
    brief = element_brief(e)
    return {"descriptor": {"tag": brief["tag"], "role": brief["role"] or brief["role_attr"], "name": brief["name"]}, "brief": brief}


def number(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ids estaveis dentro da execucao (f1, f2...)."""
    for i, f in enumerate(findings, 1):
        f["id"] = f"f{i}"
    return findings


def fingerprint(f: dict[str, Any]) -> str:
    """Identidade do achado ENTRE execucoes: criterio + persona + papel/nome do elemento (nao o id eN, que muda). Sem elemento, a afirmacao."""
    el = f.get("element") or {}
    who = f"{el.get('role') or el.get('tag') or ''}|{(el.get('name') or '').lower()}" if el else _clean(f.get("claim"), 80).lower()
    return hashlib.sha1(f"{f.get('criterion')}|{f.get('persona')}|{who}".encode()).hexdigest()[:16]


def diff(base: list[dict[str, Any]], head: list[dict[str, Any]]) -> dict[str, Any]:
    """Compara duas execucoes: o que e' novo, o que foi corrigido e o que continua. So considera achados que falharam ou nao foram confirmados."""
    live = ("failed", "cantTell")
    b = {fingerprint(f): f for f in base if f.get("outcome") in live}
    h = {fingerprint(f): f for f in head if f.get("outcome") in live}
    brief = lambda f: {k: f.get(k) for k in ("id", "criterion", "severity", "claim", "element", "outcome")}
    return {
        "new": [brief(h[k]) for k in h if k not in b],
        "fixed": [brief(b[k]) for k in b if k not in h],
        "persisting": [brief(h[k]) for k in h if k in b],
        "counts": {"new": len(set(h) - set(b)), "fixed": len(set(b) - set(h)), "persisting": len(set(h) & set(b))},
    }


# ---------------------------------------------------------------------------- exportacoes
_EARL_OUTCOME = {"failed": "earl:failed", "cantTell": "earl:cantTell", "passed": "earl:passed"}


def to_earl(findings: list[dict[str, Any]], url: str, *, created: str = "") -> dict[str, Any]:
    """EARL 1.0 em JSON-LD (W3C): quem testou, o que foi testado, qual criterio e o resultado (failed / cantTell / passed)."""
    graph: list[dict[str, Any]] = []
    for f in findings:
        if f.get("outcome") not in _EARL_OUTCOME:
            continue  # refutados nao entram: o verificador mostrou que a evidencia nao sustenta
        crit = f.get("criterion")
        result: dict[str, Any] = {
            "@type": "earl:TestResult", "earl:outcome": {"@id": _EARL_OUTCOME[f["outcome"]]},
            "dct:description": f["claim"], "a11y:severity": f.get("severity"), "a11y:evidenceSteps": f.get("evidence_steps", []),
        }
        if f.get("verification"):
            result["a11y:verification"] = f["verification"]
        if f.get("target") or f.get("element"):
            result["earl:pointer"] = {"@type": "ptr:CSSSelectorPointer" if str(f.get("target", "")).startswith("css:") else "ptr:LocationPointer",
                                       "a11y:target": f.get("target"), "a11y:element": f.get("element")}
        graph.append({
            "@type": "earl:Assertion", "@id": f"_:{f.get('id', 'f')}", "earl:assertedBy": {"@type": "earl:Assertor", "dct:title": ASSERTOR["name"], "dct:description": ASSERTOR["about"]},
            "earl:subject": {"@type": "earl:TestSubject", "dct:source": url, "a11y:persona": f.get("persona")},
            "earl:test": {"@type": "earl:TestCase", "@id": wcag.url_of(crit) if crit else "a11y:unmapped", "dct:title": f"WCAG 2.2 {crit} {wcag.name_of(crit)}" if crit else "sem criterio WCAG"},
            "earl:mode": {"@id": "earl:semiAuto"}, "earl:result": result,
        })
    report: dict[str, Any] = {
        "@context": {
            "earl": "http://www.w3.org/ns/earl#", "dct": "http://purl.org/dc/terms/", "ptr": "http://www.w3.org/2009/pointers#",
            "a11y": "https://github.com/Blindex09/mcp#",
        },
        "@id": "_:report", "@graph": graph,
    }
    if created:
        report["dct:created"] = created
    return report


def to_sarif(findings: list[dict[str, Any]], url: str) -> dict[str, Any]:
    """SARIF 2.1.0 para CI e para o painel de seguranca/qualidade do GitHub. `cantTell` vira kind=review (nao quebra o build)."""
    rules: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []
    for f in findings:
        if f.get("outcome") not in ("failed", "cantTell"):
            continue
        crit = f.get("criterion")
        rule_id = f"WCAG-{crit}" if crit else "A11Y-unmapped"
        rules.setdefault(rule_id, {
            "id": rule_id, "name": wcag.name_of(crit).replace(" ", "") if crit else "Unmapped",
            "shortDescription": {"text": f"WCAG 2.2 {crit} {wcag.name_of(crit)} (level {wcag.level_of(crit)})" if crit else "achado sem criterio WCAG"},
            "helpUri": wcag.url_of(crit) if crit else "https://www.w3.org/TR/WCAG22/",
        })
        failed = f["outcome"] == "failed"
        level = ("error" if f.get("severity") in ("blocker", "serious") else "warning") if failed else "note"
        el = f.get("element") or {}
        results.append({
            "ruleId": rule_id, "kind": "fail" if failed else "review", "level": level, "message": {"text": f["claim"]},
            "locations": [{
                "physicalLocation": {"artifactLocation": {"uri": url}},
                "logicalLocations": [{"name": f"{el.get('role') or el.get('tag') or 'pagina'} {el.get('name') or ''}".strip(), "kind": "element"}],
            }],
            "partialFingerprints": {"a11yFingerprint/v1": fingerprint(f)},
            "properties": {"severity": f.get("severity"), "persona": f.get("persona"), "evidenceSteps": f.get("evidence_steps", []), "verification": f.get("verification")},
        })
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json", "version": "2.1.0",
        "runs": [{"tool": {"driver": {"name": ASSERTOR["name"], "informationUri": "https://github.com/Blindex09/mcp", "rules": list(rules.values())}}, "results": results}],
    }


def digest(findings: list[dict[str, Any]], limit: int = 12) -> str:
    """Uma linha por achado (criterio, gravidade, desfecho, afirmacao) para o relatorio, o aprendizado e o resumo."""
    lines = []
    for f in findings[:limit]:
        crit = f"WCAG {f['criterion']} " if f.get("criterion") else ""
        why = f" [{f['verification']['reason']}]" if f.get("verification") and f["verification"].get("reason") else ""
        lines.append(f"{f['id']} {crit}{f['severity']} {f['outcome']}: {f['claim']}{why}")
    return "\n".join(lines)
