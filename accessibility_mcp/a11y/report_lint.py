"""Conferencia do relatorio ANTES de entrega: acha o que um revisor apontaria depois. REGRA DA CASA: nada vai sem confirmacao e nada vai faltando.

Cada regra verifica um fato do proprio registro (nao julga o mérito do achado): codigo ausente ou resumido, codigo nao encontrado no arquivo real,
correcao sem teste, impacto no design nao dito, tela sem nome, passos de leitor de tela sem execucao registrada. Devolve uma lista para quem
gerou o relatorio corrigir. O a11y_create_report NAO gera o arquivo enquanto houver erros (a regra da casa: nada sem confirmacao, nada faltando).
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from . import code_evidence, report_artifacts, report_context

_FAILED = ("failed", "cantTell")
# Marcas de lacuna que o gerador escreve quando falta uma informacao: no Word e no PDF tambem nao podem sobrar.
_GAP = re.compile(r"(Não registrad[oa]s?|Não informad[oa]s?|A definir|Não identificad[oa]|Não avaliad[oa] por falta|sem registro|não foi registrad[oa])", re.IGNORECASE)


def _details(finding: dict[str, Any]) -> dict[str, Any]:
    return finding.get("report_details") or {}


def lint(record: dict[str, Any], formats: tuple[str, ...] = ("xlsx",), title: str = "Relatório", language: str = "pt-BR") -> dict[str, Any]:
    issues: list[dict[str, str]] = []

    def add(finding: dict[str, Any], rule: str, severity: str, message: str) -> None:
        issues.append({"finding": str(finding.get("id") or "?").upper(), "rule": rule, "severity": severity, "message": message})

    findings = [f for f in record.get("findings", []) if isinstance(f, dict) and f.get("outcome", "failed") in _FAILED]
    for finding in findings:
        if finding.get("outcome") == "cantTell":
            add(finding, "achado_nao_confirmado", "erro", "achado ainda 'a confirmar' (sem evidencia valida): confirme com a11y_trace ou tire do relatorio")
        d = _details(finding)
        observed, fixed = str(d.get("code_snippet") or ""), str(d.get("fixed_code") or "")
        if not observed.strip():
            add(finding, "codigo_ausente", "erro", "sem trecho de codigo observado: o desenvolvedor nao sabe onde mexer")
        else:
            if code_evidence.has_placeholder(observed):
                add(finding, "codigo_resumido", "erro", "o codigo observado tem \"…\" ou \"[...]\": nao e' copia literal do arquivo")
            if d.get("code_verified") is False:
                add(finding, "codigo_nao_achado", "erro", "o codigo observado nao existe exatamente no arquivo servido (a11y_verify_code)")
            elif d.get("code_verified") is None:
                add(finding, "codigo_nao_conferido", "erro", "o codigo observado nao foi conferido com a11y_verify_code")
        if not fixed.strip():
            add(finding, "correcao_ausente", "erro", "sem codigo corrigido sugerido")
        else:
            if code_evidence.has_placeholder(fixed):
                add(finding, "correcao_resumida", "erro", "o codigo corrigido tem \"…\" ou \"[...]\": nao da para copiar")
            if not d.get("fix_tested"):
                add(finding, "correcao_nao_testada", "erro", "a correcao nao foi aplicada e medida no navegador (a11y_try_patch) antes de ser sugerida")
        if not str(d.get("design_impact") or "").strip():
            add(finding, "impacto_no_design_ausente", "erro", "nao diz se a correcao muda algo que a pessoa ve (Nenhum ou Visual minimo: ...)")
        if not str(d.get("screen") or "").strip():
            add(finding, "tela_sem_nome", "erro", "sem tela declarada: a aba sai com o nome derivado da URL")
        has_visual = bool(d.get("reproduction_steps_visual") or d.get("reproduction_steps_keyboard") or d.get("reproduction_steps"))
        if not has_visual:
            add(finding, "sem_passos_com_visao", "erro", "sem passos para reproduzir com visao")
        sr_steps = d.get("reproduction_steps_screen_reader") or []
        not_applicable = bool(sr_steps) and str(sr_steps[0]).strip().lower().startswith("não se aplica")
        if sr_steps and not not_applicable and not finding.get("evidence_steps"):
            add(finding, "leitor_sem_evidencia", "erro", "passos com leitor de tela sem passo de evidencia (NVDA executado) citado")
    for occurrence in report_artifacts.occurrence_records(report_artifacts.normalize_findings({**record, "findings": findings})):
        row = dict(zip(report_artifacts._XLSX_HEADERS, report_artifacts._xlsx_row(occurrence), strict=False))
        for header, value in row.items():
            text = str(value or "").strip()
            gap = next((line.strip() for line in text.splitlines() if line.strip() in report_artifacts.GAP_CELLS), None)
            if not text or gap:
                hint = " (dê ao achado um target css:<seletor> que exista na página: o elemento é lido do navegador)" if gap == "Elemento não identificado" else ""
                add(occurrence, "campo_vazio", "erro", f"a coluna \"{header}\" ficaria sem informacao ({gap or 'Não registrado'}){hint}")
        screen_reader = row.get(report_artifacts.SCREEN_READER_STEPS_HEADER, "")
        if (report_context.SCREEN_READER_NOT_RUN in screen_reader or report_context.SCREEN_READER_PROPOSED_NOTE in screen_reader):
            add(occurrence, "leitor_nao_executado", "erro", "os passos sem visao nao foram executados com leitor de tela real (execute com a11y_nvda_do ou declare Não se aplica com o motivo)")
    for screen in (record.get("report_context") or {}).get("screens", []):
        name = str(screen.get("name") or "").strip()
        has_findings = any(str((f.get("report_details") or {}).get("screen") or "").strip() == name for f in findings)
        if name and not has_findings and not screen.get("items"):
            issues.append({"finding": name.upper(), "rule": "tela_sem_conteudo", "severity": "erro", "message": "a tela foi declarada mas nao tem achados nem itens (o que foi testado, nao testado e observado)"})
    if any(kind in ("docx", "pdf") for kind in formats):
        issues.extend(_document_gaps(record, title, language))
    counts = Counter(i["severity"] for i in issues)
    return {
        "issues": issues,
        "counts": dict(counts),
        "ok": not any(i["severity"] == "erro" for i in issues),
        "summary": (f"{counts.get('erro', 0)} erros que impedem a entrega, {counts.get('aviso', 0)} avisos, {counts.get('info', 0)} informacoes" if issues
                    else "nenhum problema encontrado na conferencia automatica (ela nao julga o merito dos achados)"),
    }


def _document_gaps(record: dict[str, Any], title: str, language: str) -> list[dict[str, str]]:
    """Word e PDF: cada frase, item de lista ou celula com marca de lacuna ("Não registrado", "Não informado"...) e' um erro, como na planilha."""
    from . import documents

    spec = documents.report_spec(record, title, language)
    seen: list[str] = []
    for block in spec.blocks:
        texts = [block.text, *block.items, *[cell for row in block.rows for cell in row]]
        for text in texts:
            if text and _GAP.search(text):
                excerpt = re.sub(r"\s+", " ", text).strip()[:90]
                if excerpt not in seen:
                    seen.append(excerpt)
    return [{"finding": "DOCUMENTO", "rule": "documento_com_lacuna", "severity": "erro",
             "message": f"o Word/PDF ficaria com informacao faltando: \"{text}\" (preencha em report_context ou no achado)"} for text in seen[:40]]
