"""Planilhas e apresentacoes estruturadas para relatorios de acessibilidade."""

from __future__ import annotations

from pathlib import Path
from textwrap import wrap
from typing import Any
from urllib.parse import urlparse
from zipfile import ZipFile

from openpyxl import Workbook, load_workbook
from openpyxl.cell.cell import MergedCell
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.cell_range import CellRange
from openpyxl.worksheet.properties import PageSetupProperties
from openpyxl.worksheet.table import Table, TableStyleInfo
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR
from pptx.util import Inches, Pt

from . import wcag
from .report_context import (
    reproduction_screen_reader_text,
    reproduction_text,
    reproduction_visual_text,
)

_SEVERITY_LABELS = {
    "blocker": "Bloqueadora",
    "serious": "Séria",
    "moderate": "Moderada",
    "minor": "Leve",
    "unrated": "Não definida",
}
_PRIORITY_LABELS = {
    "P0": "P0 — corrigir imediatamente",
    "P1": "P1 — prioridade alta",
    "P2": "P2 — prioridade média",
    "P3": "P3 — prioridade baixa",
    "unrated": "A definir",
}
_SEVERITY_RANK = {"blocker": 0, "serious": 1, "moderate": 2, "minor": 3, "unrated": 4}
_PRIORITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "unrated": 4}
_PRAZO = {
    "P0": "A acordar na triagem",
    "P1": "A acordar na triagem",
    "P2": "A acordar na triagem",
    "P3": "A acordar na triagem",
    "unrated": "Definir depois da triagem",
}

# Campos do registro de achados: um dado por célula, na ordem em que a pessoa
# lê a planilha. Identificação, ambiente e triagem precedem os textos longos.
_FINDING_HEADERS = [
    "Site", "Sistema operacional", "Navegadores", "Princípio", "Diretriz",
    "Criticidade", "Prioridade", "Roteiro",
    "ID", "Página (URL)", "Critério WCAG", "Nível",
    "Problema", "Correção recomendada", "Justificativa da falha",
    "Ambiente do teste", "Método de teste",
    "Elemento", "Localização (seletor)",
    "Resultado observado", "Resultado esperado", "Passos para reproduzir",
    "Trecho de código observado", "Código corrigido sugerido", "Impacto no design",
]

# Modelo da planilha: no lugar de uma aba única de achados, UMA ABA POR TELA testada. Os passos de reprodução ficam em duas colunas
# (quem enxerga: baixa visão ou QA de acessibilidade; quem usa leitor de tela e não enxerga) e o código problemático e o corrigido
# ficam em colunas separadas.
VISUAL_STEPS_HEADER = "Passos para reproduzir — com visão (baixa visão ou QA de acessibilidade)"
SCREEN_READER_STEPS_HEADER = "Passos para reproduzir — sem visão (quem usa leitor de tela)"
OBSERVED_CODE_HEADER = "Trecho de código observado (HTML, JS ou CSS)"
FIXED_CODE_HEADER = "Código corrigido sugerido (HTML, JS ou CSS)"
_XLSX_HEADERS: list[str] = []
for _header in _FINDING_HEADERS:
    if _header == "Passos para reproduzir":
        _XLSX_HEADERS += [VISUAL_STEPS_HEADER, SCREEN_READER_STEPS_HEADER]
    elif _header == "Trecho de código observado":
        _XLSX_HEADERS.append(OBSERVED_CODE_HEADER)
    elif _header == "Código corrigido sugerido":
        _XLSX_HEADERS.append(FIXED_CODE_HEADER)
    else:
        _XLSX_HEADERS.append(_header)

VISUAL_STEPS_LABEL = "Como reproduzir — com visão (baixa visão ou QA de acessibilidade)"
SCREEN_READER_STEPS_LABEL = "Como reproduzir — sem visão (quem usa leitor de tela)"
OBSERVED_CODE_LABEL = "Código problemático (HTML, JS ou CSS)"
FIXED_CODE_LABEL = "Código corrigido sugerido (HTML, JS ou CSS)"
CODE_LABELS = (OBSERVED_CODE_LABEL, FIXED_CODE_LABEL)
DESIGN_IMPACT_LABEL = "Impacto no design"
FIRST_SHEETS: tuple[str, ...] = ()  # o relatório não tem aba de resumo: começa direto pelas telas
LAST_SHEETS: tuple[str, ...] = ()  # a planilha só tem as abas das telas testadas
REPORT_SHEETS = (*FIRST_SHEETS, *LAST_SHEETS)  # as abas por tela ficam entre as duas listas

_TEXT_FONT = Font(bold=True, size=11, color="17365D")
_HEAD_FILL = PatternFill("solid", fgColor="17365D")
_HEAD_FONT = Font(bold=True, color="FFFFFF")
_BORDER = Border(
    left=Side(style="thin", color="BFBFBF"), right=Side(style="thin", color="BFBFBF"),
    top=Side(style="thin", color="BFBFBF"), bottom=Side(style="thin", color="BFBFBF"),
)
_WRAP = Alignment(wrap_text=True, vertical="top")
_WRAP_HEAD = Alignment(wrap_text=True, vertical="center")
_PRIORITY_FILL = {
    "P0": PatternFill("solid", fgColor="C00000"),
    "P1": PatternFill("solid", fgColor="FF6B35"),
    "P2": PatternFill("solid", fgColor="FFD966"),
    "P3": PatternFill("solid", fgColor="A9D08E"),
}

REFERENCIAS = [
    ("WCAG 2.2 (norma)", "https://www.w3.org/TR/WCAG22/"),
    ("Understanding WCAG 2.2", "https://www.w3.org/WAI/WCAG22/Understanding/"),
    ("Template de relatório de avaliação (W3C WAI)", "https://www.w3.org/WAI/test-evaluate/report-template/"),
    ("WCAG-EM (metodologia de avaliação)", "https://www.w3.org/TR/WCAG-EM/"),
    ("Recursos de avaliação (W3C WAI)", "https://www.w3.org/WAI/test-evaluate/"),
    ("ACT Rules (regras de teste)", "https://www.w3.org/WAI/standards-guidelines/act/rules/"),
    ("VPAT / Accessibility Conformance Report (ITI)", "https://www.itic.org/policy/accessibility/vpat"),
    ("EARL (relatório legível por máquina)", "https://www.w3.org/WAI/standards-guidelines/earl/"),
    ("Elementos de um relatório de teste (Section508.gov)", "https://www.section508.gov/test/elements-of-an-accessibility-test-report/"),
    ("Registro de problemas de acessibilidade (Harvard DAS)", "https://accessibility.huit.harvard.edu/template-reporting-accessibility-issues"),
    ("Planejamento de auditoria (GOV.UK)", "https://www.gov.uk/service-manual/helping-people-to-use-your-service/getting-an-accessibility-audit"),
    ("Planilhas acessíveis (Section508.gov)", "https://www.section508.gov/blog/accessibility-bytes/accessible-spreadsheets/"),
    ("Exemplo de relatório Excel (Accessible.org)", "https://accessible.org/sample-accessibility-audit-report/"),
    ("Gestão de achados e retestes (DfE)", "https://accessibility.education.gov.uk/audits-issues-statements/issues/manage-and-prioritise-issues"),
]


def _safe_cell_value(value: Any) -> Any:
    if isinstance(value, str) and value.lstrip(" \t\r\n")[:1] in ("=", "+", "-", "@"):
        return "'" + value
    return value


def _locations(finding: dict[str, Any], fallback_url: str) -> list[dict[str, Any]]:
    page_url = str(finding.get("page_url") or fallback_url or "")
    location = finding.get("location") or {}
    attrs = location.get("attrs") or {}
    element = finding.get("element") or {}
    target = str(finding.get("target") or "")
    selector = str(location.get("css") or (target[4:] if target.startswith("css:") else ""))
    details = []
    if selector:
        details.append(f"CSS: {selector}")
    if attrs.get("id"):
        details.append(f"id: {attrs['id']}")
    if attrs.get("href"):
        details.append(f"link: {attrs['href']}")
    if attrs.get("src"):
        details.append(f"arquivo: {attrs['src']}")
    if target.startswith("e"):
        details.append(f"referência na sessão: {target}")
    where = location.get("where") or {}
    frame_url = where.get("frame_url")
    if frame_url and frame_url != page_url:
        details.append(f"quadro incorporado: {frame_url}")
    name = str(element.get("name") or "")
    tag = str(element.get("tag") or "")
    role = str(element.get("role") or "")
    element_label = " — ".join(item for item in (name, role, tag) if item) or "Elemento não identificado"
    return [{
        "page_url": page_url,
        "element": element_label,
        "selector": "; ".join(details) or "Seletor não registrado",
        "evidence_steps": finding.get("evidence_steps", []),
        "finding_id": str(finding.get("id") or "Não registrado"),
        "original_id": str(finding.get("original_id") or finding.get("id") or "Não registrado"),
        "run_id": str(finding.get("run_id") or "Sessão atual"),
        "report_details": dict(finding.get("report_details") or {}),
        "finding_data": {key: finding.get(key) for key in (
            "id", "criterion", "severity", "priority", "claim", "impact", "recommendation", "outcome",
        )},
    }]


def normalize_findings(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Agrupa o mesmo achado por páginas sem ocultar os elementos e seletores observados."""
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in record.get("findings", []):
        if not isinstance(item, dict) or item.get("outcome", "failed") not in ("failed", "cantTell"):
            continue
        criterion = str(item.get("criterion") or "")
        identity = (
            criterion,
            str(item.get("claim") or "Problema sem descrição"),
            str(item.get("outcome") or "failed"),
        )
        group = grouped.setdefault(identity, {**item, "pages": [], "locations": []})
        group["pages"].extend(_locations(item, str(record.get("url") or "")))
        severity = str(item.get("severity") or "unrated").lower()
        current_severity = str(group.get("severity") or "unrated").lower()
        if _SEVERITY_RANK.get(severity, 4) < _SEVERITY_RANK.get(current_severity, 4):
            group["severity"] = severity
        priorities = [str(value) for value in (group.get("priority"), item.get("priority")) if str(value or "").startswith("P")]
        if priorities:
            group["priority"] = min(priorities)
        if item.get("outcome") == "failed":
            group["outcome"] = "failed"
    result = []
    for group in grouped.values():
        unique_pages: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
        for location in group["pages"]:
            unique_pages[(location["run_id"], location["finding_id"], location["page_url"], location["element"], location["selector"])] = location
        group["locations"] = list(unique_pages.values())
        group["page_urls"] = list(dict.fromkeys(location["page_url"] for location in group["locations"] if location["page_url"]))
        group["evidence_steps"] = sorted({
            step for location in group["locations"] for step in location["evidence_steps"]
        })
        group.pop("pages", None)
        result.append(group)
    result.sort(key=lambda item: (str(item.get("priority") or "P9"), str(item.get("criterion") or ""), str(item.get("claim") or "")))
    for index, finding in enumerate(result, 1):
        if not finding.get("id"):
            finding["id"] = f"f{index}"
    context = record.get("report_context") or {}
    coverage = record.get("coverage") or {}
    for finding in result:
        pages = [str(url) for url in finding.get("page_urls") or [] if url]
        if not finding.get("site"):
            finding["site"] = _site_of(pages[0]) if pages else ""
        details = finding.get("report_details") or {}
        if not (details.get("operating_system") or finding.get("operating_system")):
            finding["operating_system"] = str(context.get("operating_system") or "")
        if not (details.get("browsers") or finding.get("browsers")):
            finding["browsers"] = str(context.get("browsers") or coverage.get("browser") or "")
    return result


def _criterion_text(finding: dict[str, Any]) -> tuple[str, str, str]:
    criterion = str(finding.get("criterion") or "")
    principle = str(finding.get("principle") or wcag.principle_of(criterion) or "Não informado")
    guideline, guideline_name = wcag.guideline_of(criterion)
    guideline_label = f"{guideline} — {guideline_name}" if guideline else "Não informada"
    criterion_name = str(wcag.name_pt_of(criterion) or finding.get("criterion_name") or "Critério não identificado")
    level = str(finding.get("level") or wcag.level_of(criterion))
    criterion_label = f"{criterion} — {criterion_name}" if criterion else criterion_name
    if level:
        criterion_label += f" (nível {level})"
    return principle, guideline_label, criterion_label


def _short_title(claim: str, limit: int = 90) -> str:
    """Primeira frase da reivindicacao, para o titulo curto do registro de achados."""
    text = " ".join(str(claim or "").split())
    for mark in (". ", "; "):
        if mark in text[: limit + 20]:
            text = text.split(mark)[0] + "."
            break
    return text[:limit].rstrip() if len(text) > limit else text


def _site_of(url: str) -> str:
    """Endereco do site sem caminho: o que identifica o produto, nao a pagina."""
    host = urlparse(str(url or "")).netloc
    return host.removeprefix("www.")


def finding_location(finding: dict[str, Any]) -> str:
    """Texto do avaliador; em registros antigos, só reúne fatos de localização."""
    details = finding.get("report_details") or {}
    if str(details.get("problem_location") or "").strip():
        return str(details["problem_location"])
    parts = []
    if details.get("page_area"):
        parts.append(f"Região registrada: {details['page_area']}")
    for location in finding.get("locations") or []:
        if location.get("element") and location["element"] != "Elemento não identificado":
            parts.append(f"Elemento observado: {location['element']}")
        if location.get("selector") and location["selector"] != "Seletor não registrado":
            parts.append(f"Localização técnica: {location['selector']}")
    if not parts:
        return "Local exato do problema não registrado"
    return "Descrição detalhada do local não registrada pelo avaliador. Fatos disponíveis: " + "; ".join(dict.fromkeys(parts))


def _row(finding: dict[str, Any]) -> list[str]:
    """Uma linha do registro de achados: um dado por coluna, sem texto agregado."""
    locations = finding.get("locations") or []
    pages = [str(url) for url in finding.get("page_urls", []) if url]
    if len(pages) > 1:
        page_text = f"Mesmo problema em {len(pages)} páginas:\n" + "\n".join(pages)
    else:
        page_text = pages[0] if pages else "Página não registrada"
    element_text = "\n".join(dict.fromkeys(location["element"] for location in locations)) or "Elemento não identificado"
    if len(pages) > 1:
        selectors = "\n".join(
            f"{location['page_url']}\n{location['selector']}"
            for location in locations
        ) or "Seletor não registrado"
    else:
        selectors = "\n".join(dict.fromkeys(location["selector"] for location in locations)) or "Seletor não registrado"
    severity = str(finding.get("severity") or "unrated").lower()
    priority = str(finding.get("priority") or "unrated")
    criterion_number = str(finding.get("criterion") or "")
    principle, guideline_label, _ = _criterion_text(finding)
    claim = str(finding.get("claim") or "Problema sem descrição")
    details = finding.get("report_details") or {}
    reproduction = reproduction_text(details)
    site = str(finding.get("site") or _site_of(pages[0] if pages else ""))
    values = {
        "ID": str(finding.get("id") or "Não registrado").upper(),
        "Problema": claim,
        "Site": site, "Página (URL)": page_text,
        "Roteiro": finding_location(finding),
        "Elemento": element_text, "Localização (seletor)": selectors,
        "Princípio": principle, "Diretriz": guideline_label,
        "Critério WCAG": (f"{criterion_number} — {wcag.name_pt_of(criterion_number)}".strip(" —")
                          if criterion_number else "Não identificado"),
        "Nível": wcag.level_of(criterion_number),
        "Criticidade": _SEVERITY_LABELS.get(severity, "Não definida"),
        "Prioridade": _PRIORITY_LABELS.get(priority, "A definir"),
        "Sistema operacional": details.get("operating_system") or finding.get("operating_system"),
        "Navegadores": details.get("browsers") or finding.get("browsers"),
        "Ambiente do teste": details.get("environment"),
        "Método de teste": details.get("testing_method"),
        "Passos para reproduzir": reproduction,
        "Resultado esperado": details.get("expected_result"), "Resultado observado": details.get("actual_result"),
        "Justificativa da falha": details.get("criterion_rationale"),
        "Trecho de código observado": details.get("code_snippet"), "Código corrigido sugerido": details.get("fixed_code"),
        "Impacto no design": details.get("design_impact"),
        "Correção recomendada": finding.get("recommendation"),
    }
    return [str(values.get(header) or "Não registrado") for header in _FINDING_HEADERS]


def _xlsx_row(finding: dict[str, Any]) -> list[str]:
    """Linha do modelo da planilha: passos com visão e sem visão em colunas separadas, código observado e corrigido também."""
    base = dict(zip(_FINDING_HEADERS, _row(finding)))
    details = finding.get("report_details") or {}
    out: list[str] = []
    for header in _FINDING_HEADERS:
        if header == "Passos para reproduzir":
            out.append(reproduction_visual_text(details) or "Não registrado")
            out.append(reproduction_screen_reader_text(details))
        else:
            out.append(base[header])
    return out


def screen_of(finding: dict[str, Any]) -> str:
    """Nome da tela do achado: o declarado pelo avaliador ou, sem declaração, derivado do caminho da URL (/ = Home)."""
    declared = str((finding.get("report_details") or {}).get("screen") or "").strip()
    if declared:
        return declared
    pages = [str(url) for url in (finding.get("page_urls") or []) if url] or [str(finding.get("page_url") or "")]
    path = urlparse(pages[0]).path.strip("/") if pages and pages[0] else ""
    if not path:
        return "Home" if pages and pages[0] else "Sem tela"
    return path.split("/")[-1].replace("-", " ").replace("_", " ").capitalize()


def sheet_title(name: str, used: set[str]) -> str:
    """Nome de aba válido no Excel (até 31 caracteres, sem []:*?/\\) e único."""
    clean = "".join(" " if ch in '[]:*?/\\' else ch for ch in name).strip().strip("'") or "Tela"
    clean = clean[:31].rstrip()
    candidate, number = clean, 2
    while candidate.lower() in {u.lower() for u in used}:
        suffix = f" ({number})"
        candidate = clean[: 31 - len(suffix)].rstrip() + suffix
        number += 1
    used.add(candidate)
    return candidate


def screen_groups(record: dict[str, Any], occurrences: list[dict[str, Any]]) -> list[tuple[str, str, list[dict[str, Any]], list[dict[str, str]]]]:
    """Telas na ordem do modelo: as declaradas em report_context.screens, depois as demais por ordem de aparição.

    Devolve (nome, descrição, ocorrências, itens da ficha). Tela declarada sem achado vira ficha de Item/Detalhe.
    """
    context = record.get("report_context") or {}
    order: list[str] = []
    notes: dict[str, dict[str, Any]] = {}
    for note in context.get("screens") or []:
        name = str(note.get("name") or "").strip()
        if name and name not in notes:
            notes[name] = note
            order.append(name)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for occurrence in occurrences:
        name = screen_of(occurrence)
        grouped.setdefault(name, []).append(occurrence)
        if name not in notes and name not in order:
            order.append(name)
    return [(name, str((notes.get(name) or {}).get("description") or ""), grouped.get(name, []),
             [{"item": str(item.get("item") or ""), "detail": str(item.get("detail") or "")} for item in (notes.get(name) or {}).get("items") or []])
            for name in order]


def occurrence_records(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Projeção por ocorrência: não reutiliza reprodução ou impacto de outra página do grupo."""
    records: list[dict[str, Any]] = []
    used: set[str] = set()
    for group in findings:
        for location in group["locations"]:
            identifier = location["finding_id"] if location["finding_id"] != "Não registrado" else group["id"]
            if identifier in used:
                identifier = f"{identifier}-o{len(records) + 1}"
            used.add(identifier)
            records.append({**group, **location["finding_data"], **location,
                            "id": identifier,
                            "group_id": group["id"], "locations": [location],
                            "page_urls": [location["page_url"]] if location["page_url"] else []})
    return records


def finding_facts(finding: dict[str, Any]) -> list[list[str]]:
    """Identificação do achado em pares campo/valor: um dado por célula, sem frase corrida."""
    values = dict(zip(_FINDING_HEADERS, _row(finding)))
    number = str(finding.get("criterion") or "")
    rows: list[list[str]] = []
    for header, label in (
        ("Site", "Site"),
        ("Sistema operacional", "Sistema operacional"),
        ("Navegadores", "Navegadores"),
        ("Princípio", "Princípio"),
        ("Diretriz", "Diretriz"),
        ("Criticidade", "Criticidade"),
        ("Prioridade", "Prioridade"),
        ("Roteiro", "Roteiro"),
        ("Página (URL)", "Página (URL)"),
        ("Critério WCAG", "Critério"),
        ("Nível", "Nível"),
    ):
        value = values[header]
        if header == "Critério WCAG" and number:
            value = f"{number} — {wcag.name_pt_of(number)}"
        rows.append([label, value])
    return rows


_NARRATIVE_SENTINELS = {
    "", "Não registrado", "Não registrada", "Não informado", "Não informada", "A definir",
    "Não definida", "Elemento não identificado", "Seletor não registrado", "Página não registrada",
    "Sem passo de evidência", "Não registrado pelo avaliador",
}


def _narrative_text(value: object) -> str:
    """Texto de uma linha, sem rotulo vazio nem frase ja terminada em ponto."""
    text = " ".join(str(value or "").split()).rstrip(".")
    return "" if text in _NARRATIVE_SENTINELS else text


def issue_narrative(finding: dict[str, Any]) -> list[tuple[str, str]]:
    """Ficha em linguagem natural, na ordem em que a pessoa precisa entender o problema.

    Devolve pares (rotulo, texto): Onde esta, O que foi medido, Por que reprova,
    Como reproduzir (so quando registrado) e Como corrigir. Campo sem registro diz que nao foi
    registrado, em vez de inventar texto.
    """
    values = dict(zip(_FINDING_HEADERS, _row(finding)))
    details = finding.get("report_details") or {}
    number = str(finding.get("criterion") or "")
    criterion_name = wcag.name_pt_of(number) or "critério não identificado"

    area = _narrative_text(details.get("page_area"))
    element = _narrative_text(values.get("Elemento"))
    locations = finding.get("locations") or []
    selector = "; ".join(dict.fromkeys(
        str(location.get("selector") or "") for location in locations if location.get("selector")
    ))
    if not selector:
        selector = str(finding.get("selector") or "")
    if not selector:
        raw_selector = " ".join(str(values.get("Localização (seletor)") or "").split())
        selector = raw_selector.split("CSS:", 1)[1].strip() if "CSS:" in raw_selector else raw_selector
    selector = "; ".join(part.strip().removeprefix("CSS: ") for part in selector.split(";")) if selector else ""
    selector = "" if selector in _NARRATIVE_SENTINELS else selector
    page = _narrative_text(finding.get("page_url")) or _narrative_text(values.get("Página (URL)"))
    where_parts = [part for part in (area, f"o elemento {element}" if element else "") if part]
    page_urls = [str(url) for url in (finding.get("page_urls") or []) if url]
    if len(page_urls) > 1:
        where = f"Mesmo problema em {len(page_urls)} páginas: " + ", ".join(page_urls)
        if where_parts:
            where = ", ".join(where_parts) + ". " + where
    elif where_parts:
        where = ", ".join(where_parts)
        if page:
            where += f" — página {page}"
    else:
        where = f"a página {page}" if page else "local não registrado"
        where += "; a região da tela não foi registrada pelo avaliador"
    if selector:
        where += f". No código: {selector.removeprefix('CSS: ')}"
    if str(details.get("problem_location") or "").strip():
        where = str(details["problem_location"])
        if page:
            where += f" — página {page}"
        if selector:
            where += f". No código: {selector.removeprefix('CSS: ')}"

    claim = _narrative_text(finding.get("claim"))
    actual = _narrative_text(details.get("actual_result"))
    measured = [
        part for part in (
            actual or (f"não houve medição registrada à parte; o avaliador registrou: {claim}" if claim else ""),
            f"Esperado: {_narrative_text(details.get('expected_result'))}" if _narrative_text(details.get("expected_result")) else "",
        ) if part
    ]
    measured_text = ". ".join(measured) if measured else "A medição não foi registrada pelo avaliador"

    rationale = _narrative_text(details.get("criterion_rationale"))
    if rationale:
        why = rationale
    elif number:
        why = (f"O achado não atende ao critério {number} — {criterion_name}. "
               "O avaliador não registrou a justificativa detalhada")
    else:
        why = "O avaliador não registrou o critério nem a justificativa da falha"

    recommendation = _narrative_text(finding.get("recommendation"))
    sections = [
        ("Onde está", where),
        ("O que foi medido", measured_text),
        ("Por que reprova", why),
    ]
    sections.append((VISUAL_STEPS_LABEL, reproduction_visual_text(details) or "Passos não registrados pelo avaliador"))
    sections.append((SCREEN_READER_STEPS_LABEL, reproduction_screen_reader_text(details)))
    sections.append(("Como corrigir", recommendation or "Correção não registrada pelo avaliador"))
    sections.append((DESIGN_IMPACT_LABEL, _narrative_text(details.get("design_impact")) or "Impacto no design não registrado pelo avaliador"))
    for label, key in ((OBSERVED_CODE_LABEL, "code_snippet"), (FIXED_CODE_LABEL, "fixed_code")):
        code = str(details.get(key) or "").strip("\n")
        if code.strip():
            sections.append((label, code))
    retest = [
        part for part in (
            f"correção aplicada: {_narrative_text(details.get('fix_applied'))} (versão {_narrative_text(details.get('retest_version'))})"
            if _narrative_text(details.get("fix_applied")) else "",
            f"versão testada: {_narrative_text(details.get('retest_version'))}" if _narrative_text(details.get("retest_version")) and not _narrative_text(details.get("fix_applied")) else "",
            f"data: {_narrative_text(details.get('retest_date'))}" if _narrative_text(details.get("retest_date")) else "",
            f"avaliador: {_narrative_text(details.get('retest_evaluator'))}" if _narrative_text(details.get("retest_evaluator")) else "",
            f"resultado: {_narrative_text(details.get('retest_result'))}" if _narrative_text(details.get("retest_result")) else "",
            _narrative_text(details.get("retest")),
        ) if part
    ]
    if retest:
        sections.append(("Reteste", "; ".join(retest)))
    return [(label, text[:1].upper() + text[1:] if text[:1].islower() else text) for label, text in sections]


def workbook_report(record: dict[str, Any], title: str, path: Path, language: str = "pt-BR") -> dict[str, Any]:
    findings = normalize_findings(record)
    occurrences = occurrence_records(findings)

    wb = Workbook()
    placeholder = wb.active  # folha em branco do openpyxl: sai no fim, sem aba de resumo
    wb.properties.language = language

    used_titles = set(FIRST_SHEETS) | set(LAST_SHEETS)
    screen_titles: list[str] = []
    finding_titles: list[str] = []
    groups = screen_groups(record, occurrences)
    if not groups:
        groups = [("Achados", "", [], [])]
    for index, (name, description, screen_findings, items) in enumerate(groups, 1):
        sheet = wb.create_sheet(sheet_title(name, used_titles))
        screen_titles.append(sheet.title)
        if screen_findings or not items:
            sheet.sheet_properties.tabColor = "C00000"
            sheet.append(_XLSX_HEADERS)
            for finding in screen_findings:
                sheet.append(_xlsx_row(finding))
            _style_finding_sheet(sheet, screen_findings, table_name=f"Tela{index}")
            finding_titles.append(sheet.title)
        else:
            sheet.sheet_properties.tabColor = "70AD47"
            sheet.append(["Item", "Detalhe"])
            for entry in items:
                sheet.append([entry["item"], entry["detail"]])
            if description:
                sheet.append(["Tela", description])
            sheet.column_dimensions["A"].width = 26
            sheet.column_dimensions["B"].width = 110
            _style_plain_sheet(sheet, 2, table_name=f"Tela{index}")
    wb.properties.title = title
    wb.properties.subject = "Relatório de acessibilidade com registro de achados, matriz WCAG e cobertura"

    for worksheet in wb.worksheets:
        for line in worksheet.iter_rows():
            for cell in line:
                if isinstance(cell, MergedCell):
                    continue
                cell.value = _safe_cell_value(cell.value)
    if placeholder is not None:
        wb.remove(placeholder)
    for position, name in enumerate([*FIRST_SHEETS, *screen_titles, *LAST_SHEETS]):
        wb.move_sheet(name, offset=position - wb.sheetnames.index(name))
    for worksheet in wb.worksheets:
        _setup_print(worksheet, wide=worksheet.title in finding_titles)
    wb.active = wb.sheetnames.index(finding_titles[0] if finding_titles else screen_titles[0])
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return validate_xlsx(path)


def _style_plain_sheet(sheet: Any, columns: int, table_name: str | None = None) -> None:
    for cell in sheet[1]:
        cell.font = _HEAD_FONT
        cell.fill = _HEAD_FILL
        cell.alignment = _WRAP_HEAD
    for line in sheet.iter_rows(min_row=2):
        for cell in line:
            cell.alignment = _WRAP
    sheet.freeze_panes = "A2"
    if sheet.max_row > 1:
        table = Table(displayName=table_name or f"{sheet.title.replace(' ', '')}Table", ref=f"A1:{get_column_letter(columns)}{sheet.max_row}")
        table.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=True, showColumnStripes=False)
        sheet.add_table(table)
    sheet.row_dimensions[1].height = 30


def _style_finding_sheet(sheet: Any, findings: list[dict[str, Any]], table_name: str | None = None) -> None:
    """Cabeçalhos na primeira linha; uma ocorrência completa por linha."""
    widths = {"Site": 26, "Sistema operacional": 26, "Navegadores": 42,
              "Princípio": 20, "Diretriz": 32, "Criticidade": 17, "Prioridade": 30,
              "Roteiro": 62, VISUAL_STEPS_HEADER: 70, SCREEN_READER_STEPS_HEADER: 70,
              OBSERVED_CODE_HEADER: 90, FIXED_CODE_HEADER: 90, "Impacto no design": 45}
    _style_plain_sheet(sheet, len(_XLSX_HEADERS), table_name=table_name)
    for column, header in enumerate(_XLSX_HEADERS, 1):
        sheet.column_dimensions[get_column_letter(column)].width = widths.get(header, 55)
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = _WRAP
            cell.border = _BORDER
        lines = max(sum(max(1, len(wrap(line, width=max(10, int(sheet.column_dimensions[cell.column_letter].width) - 5))))
                        for line in str(cell.value or "").split("\n")) for cell in row)
        sheet.row_dimensions[row[0].row].height = min(409, max(30, lines * 16 + 8))
    priority_column = _XLSX_HEADERS.index("Prioridade") + 1
    criterion_column = _XLSX_HEADERS.index("Critério WCAG") + 1
    for row_number in range(2, sheet.max_row + 1):
        priority_cell = sheet.cell(row_number, priority_column)
        priority = str(findings[row_number - 2].get("priority") or "unrated")
        priority_cell.fill = _PRIORITY_FILL.get(priority, PatternFill())
        priority_cell.font = Font(bold=True, color="FFFFFF" if priority == "P0" else "000000")
        requirement = sheet.cell(row_number, criterion_column)
        number = str(requirement.value or "").split(" — ")[0].strip()
        if wcag.url_of(number):
            requirement.hyperlink = wcag.url_of(number)
            requirement.font = Font(color="0563C1", underline="single")
    sheet.freeze_panes = "D2"


def _setup_print(sheet: Any, wide: bool = False) -> None:
    """Prepara a impressao: paisagem, A4, ajuste a largura e cabecalho repetido.

    Sem isso, uma planilha larga imprime os rotulos numa folha e os valores na
    seguinte; a planilha de achados repete site, ambiente e classificação em cada folha.
    """
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.paperSize = sheet.PAPERSIZE_A4
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    sheet.page_margins.left = 0.4
    sheet.page_margins.right = 0.4
    sheet.page_margins.top = 0.5
    sheet.page_margins.bottom = 0.5
    if wide:
        sheet.page_setup.fitToWidth = 0
        sheet.page_setup.scale = 100
        sheet.print_title_rows = "1:1"
        sheet.print_title_cols = "A:A"


def validate_xlsx(path: Path, report_schema: bool = True) -> dict[str, Any]:
    with ZipFile(path) as package:
        if sum(item.file_size for item in package.infolist()) > 100 * 1024 * 1024:
            raise ValueError("Pacote XLSX excede o limite de seguranca de descompressao de 100 MiB.")
    wb = load_workbook(path, read_only=False, data_only=False, keep_links=False)
    try:
        issues = []
        required = REPORT_SHEETS
        missing = [name for name in required if name not in wb.sheetnames]
        screens = [name for name in wb.sheetnames if name not in required]
        if report_schema and missing:
            issues.append({"code": "missing_report_sheets", "location": f"faltam: {', '.join(missing)}"})
        elif report_schema and not screens:
            issues.append({"code": "missing_screen_sheets", "location": "falta pelo menos uma aba de tela"})
        elif report_schema and wb.sheetnames != [*FIRST_SHEETS, *screens, *LAST_SHEETS]:
            issues.append({"code": "report_sheet_order", "location": "ordem das abas do relatório"})
        finding_sheets = [wb[name] for name in screens if wb[name]["A1"].value == "Site"]
        sheet = finding_sheets[0] if finding_sheets else None
        headers = [cell.value for cell in sheet[1]] if sheet is not None else []
        for finding_sheet in finding_sheets:
            if report_schema and [cell.value for cell in finding_sheet[1]] != _XLSX_HEADERS:
                issues.append({"code": "missing_finding_headers", "location": f"aba {finding_sheet.title}, linha 1"})
        findings = sum(max(0, finding_sheet.max_row - 1) for finding_sheet in finding_sheets)
        for worksheet in wb.worksheets:
            if worksheet.auto_filter.ref:
                filter_range = CellRange(worksheet.auto_filter.ref)
                for table in worksheet.tables.values():
                    if not filter_range.isdisjoint(CellRange(table.ref)):
                        issues.append({"code": "overlapping_table_filter", "location": f"{worksheet.title}: {table.ref}"})
        facts = {
            "title": wb.properties.title,
            "language": wb.properties.language,
            "sheets": wb.sheetnames,
            "findings": findings if report_schema else None,
            "headers": headers,
            "table_names": [name for finding_sheet in finding_sheets for name in finding_sheet.tables],
            "screen_sheets": screens,
            "freeze_panes": {name: wb[name].freeze_panes for name in wb.sheetnames},
            "report_schema_checked": report_schema,
            "worksheets": [{"name": ws.title, "rows": ws.max_row, "columns": ws.max_column,
                            "merged_ranges": [str(area) for area in ws.merged_cells.ranges],
                            "tables": [{"name": table.displayName, "ref": table.ref,
                                        "header_row_count": table.headerRowCount,
                                        "headers": [column.name for column in table.tableColumns]}
                                       for table in ws.tables.values()],
                            "defined_names": list(ws.defined_names)} for ws in wb],
            "defined_names": list(wb.defined_names),
        }
        return {"format": "xlsx", "status": "issues_found" if issues else "automated_checks_passed", "issues": issues,
                "facts": facts, "human_review_required": ["Confira nomes de colunas, filtros, ordem e leitura da planilha com o aplicativo de destino."],
                "conformance": "not_determined", "complete_validation": False}
    finally:
        wb.close()


def _set_language(shape: Any, language: str) -> None:
    for paragraph in shape.text_frame.paragraphs:
        for run in paragraph.runs:
            run._r.get_or_add_rPr().set("lang", language)


def validate_pptx(path: Path) -> dict[str, Any]:
    with ZipFile(path) as package:
        if sum(item.file_size for item in package.infolist()) > 100 * 1024 * 1024:
            raise ValueError("Pacote PPTX excede o limite de seguranca de descompressao de 100 MiB.")
    prs = Presentation(str(path))
    issues: list[dict[str, str]] = []
    titles = []
    language_count = 0
    for index, slide in enumerate(prs.slides, 1):
        title_shape = slide.shapes.title
        title = title_shape.text.strip() if title_shape is not None else ""
        titles.append(title)
        if not title:
            issues.append({"code": "slide_missing_title", "location": f"slide {index}"})
        if not any(shape.has_text_frame and shape.text.strip() for shape in slide.shapes):
            issues.append({"code": "slide_missing_text", "location": f"slide {index}"})
        for shape in slide.shapes:
            if shape.has_text_frame:
                language_count += sum(
                    1 for paragraph in shape.text_frame.paragraphs for run in paragraph.runs
                    if run._r.rPr is not None and run._r.rPr.get("lang")
                )
    if not prs.slides:
        issues.append({"code": "presentation_without_slides", "location": "apresentação"})
    facts = {"title": prs.core_properties.title, "slides": len(prs.slides), "slide_titles": titles, "runs_with_language": language_count}
    return {"format": "pptx", "status": "issues_found" if issues else "automated_checks_passed", "issues": issues,
            "facts": facts, "human_review_required": ["Confira a ordem de leitura, os títulos, o texto e o ajuste visual de cada slide no aplicativo de apresentação."],
            "conformance": "not_determined", "complete_validation": False}


def presentation_report(record: dict[str, Any], title: str, path: Path, language: str = "pt-BR") -> dict[str, Any]:
    findings = normalize_findings(record)
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    layout = prs.slide_layouts[0]
    intro = prs.slides.add_slide(layout)
    intro.shapes.title.text = title
    confirmed = sum(finding.get("outcome") == "failed" for finding in findings)
    uncertain = sum(finding.get("outcome") == "cantTell" for finding in findings)
    coverage = record.get("coverage") or {}
    report_context = record.get("report_context") or {}
    gaps = coverage.get("gaps")
    persona = str(record.get("persona") or "")
    intro.placeholders[1].text = (
        f"Site: {record.get('url') or 'Não informado'}\n"
        f"Sistema operacional: {report_context.get('operating_system') or 'Não registrado'}\n"
        f"Navegadores: {report_context.get('browsers') or coverage.get('browser') or 'Não informado'}\n"
        f"Navegação testada: {persona if persona and persona != 'default' else 'padrão, sem simulação específica'}\n"
        f"Problemas confirmados: {confirmed}\n"
        f"Problemas que precisam de confirmação: {uncertain}\n"
        f"Lacunas de cobertura: {'; '.join(str(gap) for gap in gaps) if gaps else ('Nenhuma registrada.' if coverage else 'Cobertura não registrada.')}\n"
        "Este documento não é uma declaração de conformidade."
    )
    _set_language(intro.shapes.title, language)
    _set_language(intro.placeholders[1], language)
    for index, finding in enumerate(findings, 1):
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        identifier = str(finding.get("id") or index).upper()
        slide.shapes.title.text = f"{identifier} · {_short_title(str(finding.get('claim') or 'Descrição não informada'), 100)}"
        row = dict(zip(_FINDING_HEADERS, _row(finding)))
        fields = [
            f"Site: {row['Site']}  |  Roteiro: {row['Roteiro']}",
            f"Princípio: {row['Princípio']}  |  Diretriz: {row['Diretriz']}  |  Critério WCAG {row['Critério WCAG']} ({row['Nível']})",
            f"Criticidade: {row['Criticidade']}  |  Prioridade: {row['Prioridade']}",
            f"Sistema operacional: {row['Sistema operacional']}  |  Navegadores: {row['Navegadores']}",
            *[f"{label}: {text}." for label, text in issue_narrative(finding)],
        ]
        body = slide.placeholders[1]
        frame = body.text_frame
        frame.clear()
        frame.word_wrap = True
        frame.vertical_anchor = MSO_ANCHOR.TOP
        frame.margin_left = Inches(0.25)
        frame.margin_right = Inches(0.25)
        for field_index, text in enumerate(fields):
            paragraph = frame.paragraphs[0] if field_index == 0 else frame.add_paragraph()
            paragraph.text = text
            paragraph.space_after = Pt(8)
            for run in paragraph.runs:
                run.font.size = Pt(14)
                run.font.color.rgb = RGBColor(35, 35, 35)
                run._r.get_or_add_rPr().set("lang", language)
        _set_language(slide.shapes.title, language)
    if not findings:
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = "Nenhum problema foi registrado"
        body = slide.placeholders[1]
        body.text = "Isso não significa que o site esteja acessível; pode não ter havido avaliação suficiente."
        _set_language(slide.shapes.title, language)
        _set_language(body, language)
    path.parent.mkdir(parents=True, exist_ok=True)
    prs.core_properties.title = title
    prs.core_properties.subject = "Relatório de acessibilidade com localização dos problemas"
    prs.core_properties.language = language
    prs.save(str(path))
    return validate_pptx(path)


def create(record: dict[str, Any], title: str, formats: tuple[str, ...], folder: Path, language: str = "pt-BR") -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    generators = {"xlsx": workbook_report, "pptx": presentation_report}
    filenames = {"xlsx": "report.xlsx", "pptx": "report.pptx"}
    mime_types = {
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }
    for kind in formats:
        path = folder / filenames[kind]
        validation = generators[kind](record, title, path, language)
        outputs.append({"path": str(path), "filename": filenames[kind], "mime_type": mime_types[kind], "bytes": path.stat().st_size, "validation": validation})
    return outputs

