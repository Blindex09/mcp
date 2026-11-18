"""Regressões de resultados inconclusivos, rastreabilidade e contexto QA."""

from pathlib import Path

import pytest
from openpyxl import load_workbook
from pypdf import PdfReader

from accessibility_mcp.a11y import documents, report_artifacts, wcag
from accessibility_mcp.a11y.report_context import (
    CriterionResult,
    FindingDetails,
    ReportContext,
    ScopeSample,
    apply_context,
    criterion_result,
    missing_report_data,
    report_pages,
)


def finding_sheet(workbook):
    """Primeira aba de tela com achados (a planilha tem uma aba por tela; a de achados é a que começa em 'Site')."""
    return next(sheet for sheet in workbook.worksheets if sheet["A1"].value == "Site")


def test_official_context_is_placed_and_missing_data_is_visible(tmp_path):
    record = apply_context({"url": "https://example.test", "findings": []}, ReportContext(
        conformance_target="WCAG 2.2 AAA", accessibility_support_baseline="Firefox e NVDA",
        technologies_relied_upon="HTML e JavaScript", evaluation_tools="axe-core versão de teste",
        product_exploration="Busca e compra", random_sample="Sorteio de páginas complementares",
        evaluator_languages="Português", monitoring_plan="Reavaliar a cada publicação",
    ))
    spec = documents.report_spec(record, "QA")
    sections = {}
    current = "Identificação"
    for block in spec.blocks:
        if block.kind == "heading" and block.level == 2:
            current = block.text
        sections[current] = sections.get(current, "") + str(block.model_dump())
    assert "Dados não registrados para revisão" in sections["Resumo"]
    assert "axe-core versão de teste" in sections["Como a avaliação foi feita"]
    assert "Português" in sections["Ficha técnica"]
    assert "Reavaliar a cada publicação" in sections["Acompanhamento e novas avaliações"]
    assert ["Avaliação", "Avaliador"] in missing_report_data(record)
    assert ["Avaliação", "Norma e nível pretendidos"] not in missing_report_data(record)
    path = tmp_path / "context.xlsx"
    report_artifacts.workbook_report(record, "QA", path)
    wb = load_workbook(path)
    try:
        assert "Resumo" not in wb.sheetnames
    finally:
        wb.close()


def test_absent_reproduction_is_reported_without_inventing_steps():
    record = {"findings": [{"id": "f1", "criterion": "2.1.1", "outcome": "failed"}]}
    assert ["Achados: f1", "Passos para reproduzir"] in missing_report_data(record)
    assert "Passos para reproduzir" in str(documents.report_spec(record, "QA").model_dump())


def test_report_preserves_reproduction_per_occurrence_and_unknown_criteria(tmp_path):
    record = {"url": "https://example.test", "findings": [
        {"id": "f1", "criterion": "2.1.1", "claim": "Controle inoperável", "outcome": "cantTell", "priority": "P1", "evidence_steps": [3]},
        {"id": "f2", "criterion": "2.1.1", "claim": "Controle inoperável", "outcome": "cantTell", "priority": "P1", "evidence_steps": [7]},
    ]}
    context = ReportContext(evaluator="Equipe QA", sampling="Jornada de compra", evaluator_contact="qa@example.test", samples=[
        ScopeSample(url="https://example.test", title="Carrinho", journey="Pagamento", selection_reason="Processo essencial", testing_method="Teclado", environment="Windows / navegador de teste"),
    ], findings=[
        FindingDetails(finding_id="f1", reproduction_steps=["Abrir carrinho", "Pressionar Enter"], expected_result="Abrir pagamento", actual_result="Sem mudança", evidence="Captura local 01", due_date="2026-11-10", retest_date="2026-11-11", retest_version="build-2", retest_evaluator="QA 2", retest_result="Persiste", retest_evidence="Captura 02"),
        FindingDetails(finding_id="f2", reproduction_steps=["Abrir menu", "Pressionar Espaço"], actual_result="Requer confirmação"),
    ])
    enriched = apply_context(record, context)
    assert "report_details" not in record["findings"][0]
    path = tmp_path / "qa.xlsx"
    assert not report_artifacts.workbook_report(enriched, "QA", path)["issues"]
    wb = load_workbook(path)
    try:
        rows = [dict(zip(report_artifacts._XLSX_HEADERS, row)) for row in finding_sheet(wb).iter_rows(min_row=2, values_only=True)]
        assert len(rows) == 2
        assert rows[0]["ID"] == "F1" and rows[1]["ID"] == "F2"
        assert "Abrir carrinho" in rows[0][report_artifacts.VISUAL_STEPS_HEADER] and "Abrir menu" in rows[1][report_artifacts.VISUAL_STEPS_HEADER]
        assert "Evidência (passos do trace)" not in rows[0]
        assert "Evidência" not in rows[1]
        assert wb.sheetnames[0] != "Resumo"
        assert not {"Matriz WCAG", "Correções e retestes", "Referências", "Resumo", "Escopo e ambiente"} & set(wb.sheetnames)
        assert len(wb.sheetnames) >= 1
        headers = [cell.value for cell in finding_sheet(wb)[1]]
        assert headers[:8] == ["Site", "Sistema operacional", "Navegadores", "Princípio", "Diretriz",
                               "Criticidade", "Prioridade", "Roteiro"]
        for name in ("Princípio", "Diretriz", "Criticidade", "Prioridade", "Sistema operacional",
                     "Navegadores", "Site", "Problema", "Correção recomendada"):
            assert name in headers, name
        assert finding_sheet(wb).row_dimensions[2].height >= 30
    finally:
        wb.close()
    spec = documents.report_spec(enriched, "QA")
    text = str(spec.model_dump())
    assert "Parcialmente suportado" not in text
    assert "Inconclusivo" in text
    assert "Equipe QA" in text and "Abrir carrinho" in text and "Abrir menu" in text
    assert "Processo essencial" not in text  # amostra faz parte do escopo, removido do documento
    assert [block.text for block in spec.blocks if block.kind == "heading" and block.level == 2] == [
        "Resumo", "O que já está certo",
        "Como a avaliação foi feita", "Problemas encontrados", "Tabela de conformidade com a WCAG 2.2",
        "O que corrigir primeiro", "Como confirmar que foi corrigido", "Limites desta avaliação",
        "Ficha técnica", "Referências",
    ]
    paragraphs = [block.text for block in spec.blocks if block.kind == "paragraph"]
    for label in ("Onde está", "O que foi medido", "Por que reprova", report_artifacts.VISUAL_STEPS_LABEL, report_artifacts.SCREEN_READER_STEPS_LABEL, "Como corrigir"):
        assert any(text.startswith(label + ".") for text in paragraphs), label
    assert not any(text.startswith("Quem sente") for text in paragraphs)


def test_legacy_findings_get_identification_and_wcag_metadata_in_word():
    spec = documents.report_spec({"findings": [{"criterion": "2.1.1", "claim": "Controle sem teclado", "outcome": "failed"}]}, "QA")
    content = str(spec.model_dump())
    assert "Sem tela" in content
    assert "2.1.1 — Teclado" in content
    assert "F1" in content
    assert spec.toc is True
    matrices = [block for block in spec.blocks if block.kind == "table" and block.text.startswith("Tabela de conformidade com a WCAG 2.2")]
    assert all(len(block.rows) <= 12 for block in matrices)
    assert sum(len(block.rows) for block in matrices) == sum(wcag.level_of(n) in ("A", "AA") for n in wcag.CRITERIA)


def test_report_speaks_plain_language_and_keeps_the_qa_facts():
    record = {"url": "https://example.test/", "findings": [{
        "id": "f1", "criterion": "2.5.8", "claim": "Alvos pequenos demais para o dedo", "outcome": "failed",
        "severity": "serious", "priority": "P1", "impact": "Quem tem tremor erra o alvo e acerta o link vizinho.",
        "recommendation": "Aumentar a área clicável para 24 pixels.",
        "report_details": {
            "page_area": "os links do rodapé", "actual_result": "36 dos 51 alvos medem menos de 24x24 pixels",
            "expected_result": "24x24 pixels", "criterion_rationale": "A área clicável fica abaixo do mínimo",
        },
    }]}
    spec = documents.report_spec(record, "QA")
    paragraphs = [block.text for block in spec.blocks if block.kind == "paragraph"]
    onde = next(text for text in paragraphs if text.startswith("Onde está."))
    assert "links do rodapé" in onde and "https://example.test/" in onde
    assert any(text.startswith("O que foi medido. 36 dos 51 alvos") for text in paragraphs)
    assert any(text.startswith("Por que reprova. A área clicável") for text in paragraphs)
    assert not any(text.startswith("Quem sente") for text in paragraphs)
    assert any(text.startswith("Como corrigir. Aumentar a área clicável") for text in paragraphs)
    dump = str(spec.model_dump())
    assert "2.5.8 — Tamanho do alvo (mínimo)" in dump
    assert "P1 — prioridade alta" in dump


def test_positive_result_requires_scope_evidence_and_complete_coverage():
    fields = {"criterion": "1.1.1", "outcome": "passed", "scope": "Página inicial", "remarks": "Imagens avaliadas"}
    with pytest.raises(ValueError, match="evidência"):
        CriterionResult(**fields)
    with pytest.raises(ValueError, match="cobertura completa"):
        CriterionResult(**fields, evidence=["Avaliação manual das alternativas"])
    assessment = CriterionResult(**fields, evidence=["Avaliação manual das alternativas"], complete=True)
    context = ReportContext(criteria=[assessment])
    record = apply_context({"findings": []}, context)
    assert criterion_result(record, "1.1.1", [])[0] == "Atende no escopo avaliado"
    with pytest.raises(ValueError, match="contradiz"):
        apply_context({"findings": [{"criterion": "1.1.1", "outcome": "cantTell"}]}, context)
    untested = ReportContext(criteria=[CriterionResult(criterion="1.1.1", outcome="untested", scope="Página inicial", remarks="Sem teste")])
    with pytest.raises(ValueError, match="contradiz"):
        apply_context({"findings": [{"criterion": "1.1.1", "outcome": "failed"}]}, untested)


@pytest.mark.parametrize("findings,details", [
    ([], [FindingDetails(finding_id="missing")]),
    ([{"id": "f1"}, {"id": "f1"}], [FindingDetails(finding_id="f1")]),
    ([{"id": "f1"}], [FindingDetails(finding_id="f1"), FindingDetails(finding_id="f1")]),
])
def test_context_rejects_unknown_or_ambiguous_ids(findings, details):
    with pytest.raises(ValueError, match="ambíguo"):
        apply_context({"findings": findings}, ReportContext(findings=details))


async def test_pdf_report_keeps_reproduction_and_criterion_results(monkeypatch):
    monkeypatch.setenv("A11Y_MCP_AUTO_INSTALL", "0")
    record = apply_context({"url": "https://example.test", "findings": [{
        "id": "f1", "criterion": "2.1.1", "claim": "Botão sem ativação", "outcome": "failed",
    }]}, ReportContext(evaluator="Equipe de QA", findings=[FindingDetails(
        finding_id="f1", reproduction_steps=["Pressionar Enter no botão"],
        expected_result="Abrir painel", actual_result="Painel permanece fechado",
        problem_location="Página inicial > cabeçalho > botão Abrir painel",
        retest="Ainda não executado",
    )]))
    result = await documents.create(documents.report_spec(record, "Relatório QA"), "pdf")
    entry = result["files"][0]
    reader = PdfReader(entry["path"])
    text = " ".join(page.extract_text() for page in reader.pages)
    assert "Pressionar Enter no botão" in text
    assert "Painel permanece fechado" in text
    assert "Página inicial > cabeçalho > botão Abrir painel" in text
    assert "Ainda não executado" in text
    assert "4.1.3" in text
    assert reader.trailer["/Root"]["/StructTreeRoot"]
    assert not entry["validation"]["issues"]


def test_repeated_issues_keep_each_pages_impact_recommendation_and_identification(tmp_path):
    findings = report_artifacts.normalize_findings({"findings": [
        {"criterion": "2.1.1", "claim": "Controle inoperável", "outcome": "failed", "page_url": "https://example.test/a",
         "impact": "Não abre o carrinho", "recommendation": "Corrigir botão do carrinho"},
        {"criterion": "2.1.1", "claim": "Controle inoperável", "outcome": "failed", "page_url": "https://example.test/b",
         "impact": "Não abre o menu", "recommendation": "Corrigir botão do menu", "report_details": {"fix_applied": "Alteração em desenvolvimento"}},
    ]})
    rows = [dict(zip(report_artifacts._FINDING_HEADERS, report_artifacts._row(item))) for item in report_artifacts.occurrence_records(findings)]
    assert rows[0]["ID"] != rows[1]["ID"]
    assert [item["impact"] for item in report_artifacts.occurrence_records(findings)] == [
        "Não abre o carrinho", "Não abre o menu",
    ]
    assert "Impacto para as pessoas" not in report_artifacts._FINDING_HEADERS
    assert rows[1]["Correção recomendada"] == "Corrigir botão do menu"


def test_scope_includes_finding_pages_and_does_not_turn_save_time_into_test_date():
    record = {"url": "https://example.test/", "created": "2026-10-27T00:00:00Z", "findings": [
        {"id": "f1", "criterion": "2.1.1", "claim": "Barreira", "outcome": "failed", "page_url": "https://example.test/contato"},
    ]}
    assert report_pages(record) == ["https://example.test/", "https://example.test/contato"]
    spec = documents.report_spec(record, "QA")
    assert not any(block.kind == "table" and block.text == "Dados do escopo" for block in spec.blocks)


def test_document_cards_preserve_environment_for_each_occurrence():
    record = {"findings": [
        {"id": "f1", "criterion": "2.1.1", "claim": "Controle inoperável", "outcome": "failed",
         "page_url": "https://example.test/a", "report_details": {
             "operating_system": "Windows", "browsers": "Firefox", "journey": "Abrir menu",
             "problem_location": "Página A > cabeçalho > botão Menu"}},
        {"id": "f2", "criterion": "2.1.1", "claim": "Controle inoperável", "outcome": "failed",
         "page_url": "https://example.test/b", "report_details": {
             "operating_system": "Linux", "browsers": "Chromium", "journey": "Abrir carrinho",
             "problem_location": "Página B > cabeçalho > botão Carrinho"}},
    ]}
    cards = [block for block in documents.report_spec(record, "QA").blocks
             if block.kind == "table" and block.text.startswith("Ficha do achado")]
    assert len(cards) == 2
    assert [row[0] for row in cards[0].rows[:8]] == [
        "Site", "Sistema operacional", "Navegadores", "Princípio", "Diretriz",
        "Criticidade", "Prioridade", "Roteiro",
    ]
    assert dict(cards[0].rows)["Sistema operacional"] == "Windows"
    assert dict(cards[1].rows)["Sistema operacional"] == "Linux"
    assert dict(cards[1].rows)["Navegadores"] == "Chromium"
    assert dict(cards[1].rows)["Página (URL)"] == "https://example.test/b"
    assert dict(cards[1].rows)["Roteiro"] == "Página B > cabeçalho > botão Carrinho"


def test_multiple_occurrences_on_one_page_are_not_counted_as_pages():
    spec = documents.report_spec({"url": "https://example.test/", "findings": [
        {"id": "f1", "criterion": "2.1.1", "claim": "Controle inoperável", "outcome": "failed"},
        {"id": "f2", "criterion": "2.1.1", "claim": "Controle inoperável", "outcome": "failed"},
    ]}, "QA")
    text = " ".join(block.text for block in spec.blocks)
    assert "F1 · " in text and "F2 · " in text
    assert "aparece em 2 páginas" not in text


def test_executed_probes_are_not_reported_as_positive_results():
    spec = documents.report_spec({"coverage": {"probes_run": ["tab_walk", "target_size"]},
                                  "findings": [{"id": "f1", "criterion": "2.5.8", "outcome": "failed"}]}, "QA")
    text = str(spec.model_dump())
    assert "Nenhuma aprovação com cobertura completa e evidência foi registrada" in text
    assert "sem achado registrado" not in text
    assert "do começo ao fim" not in text
    assert "foi sempre conferido à mão" not in text
    record = apply_context({"findings": []}, ReportContext(criteria=[CriterionResult(
        criterion="3.1.1", outcome="passed", complete=True, scope="Página inicial",
        evidence=["Idioma en medido no HTML"], remarks="Idioma identificado",
    )]))
    approved = str(documents.report_spec(record, "QA").model_dump())
    assert "3.1.1 — Idioma identificado. Escopo: Página inicial" in approved
    assert "Idioma en medido no HTML" not in approved


def test_workbook_places_headers_in_row_one_and_occurrences_below(tmp_path):
    path = tmp_path / "vertical.xlsx"
    record = {"url": "https://example.test/", "findings": [
        {"id": "f1", "criterion": "2.1.1", "claim": "Menu", "priority": "P1",
         "report_details": {"journey": "Abrir menu", "operating_system": "Windows",
                            "problem_location": "Cabeçalho > botão Menu"}},
        {"id": "f2", "criterion": "3.1.1", "claim": "Idioma", "priority": "P2",
         "report_details": {"journey": "Ler conteúdo", "operating_system": "Linux",
                            "problem_location": "Documento HTML > atributo lang"}},
    ]}
    assert not report_artifacts.workbook_report(record, "QA", path)["issues"]
    wb = load_workbook(path)
    try:
        sheet = finding_sheet(wb)
        assert wb.active.title == finding_sheet(wb).title
        assert [sheet.cell(1, column).value for column in range(1, 9)] == [
            "Site", "Sistema operacional", "Navegadores", "Princípio", "Diretriz",
            "Criticidade", "Prioridade", "Roteiro",
        ]
        assert sheet["A2"].value == sheet["A3"].value == "example.test"
        assert sheet["B2"].value == "Windows"
        assert sheet["B3"].value == "Linux"
        assert sheet["G2"].value == "P1 — prioridade alta"
        assert sheet["G3"].value == "P2 — prioridade média"
        assert sheet["G2"].fill.fgColor.rgb.endswith("FF6B35")
        assert sheet["G3"].fill.fgColor.rgb.endswith("FFD966")
        assert sheet.column_dimensions["G"].width >= 30
        assert sheet["H2"].value == "Cabeçalho > botão Menu"
        assert sheet["H3"].value == "Documento HTML > atributo lang"
        assert not sheet.merged_cells.ranges
        assert sheet.freeze_panes == "D2"
    finally:
        wb.close()


@pytest.mark.parametrize("location", [
    "Página inicial > rodapé > seção Empresa > link Contato",
    "Página inicial > conteúdo principal > título Novidades",
    "Página de contato > formulário Fale conosco > campo E-mail",
    "Página inicial > cabeçalho > link Contato (há outro no rodapé)",
])
def test_roteiro_uses_exact_location_instead_of_journey(tmp_path, location):
    record = apply_context({"url": "https://example.test/", "findings": [
        {"id": "f1", "criterion": "2.1.1", "claim": "Problema de exemplo", "outcome": "failed"},
    ]}, ReportContext(findings=[FindingDetails(
        finding_id="f1", problem_location=location, journey="Navegar pelo site",
        reproduction_steps=["Abrir a página", "Pressionar Tab"],
    )]))
    path = tmp_path / "location.xlsx"
    report_artifacts.workbook_report(record, "QA", path)
    wb = load_workbook(path)
    try:
        assert finding_sheet(wb)["H2"].value == location
    finally:
        wb.close()
    spec = documents.report_spec(record, "QA")
    card = next(block for block in spec.blocks if block.kind == "table" and block.text == "Ficha do achado F1")
    assert dict(card.rows)["Roteiro"] == location
    assert any(block.text.startswith("Onde está. " + location) for block in spec.blocks)
    assert any(block.kind == "list" and block.ordered and block.items == ["Abrir a página", "Pressionar Tab"] for block in spec.blocks)


def test_legacy_journey_is_not_misrepresented_as_exact_location():
    record = {"findings": [{"id": "f1", "criterion": "2.1.1", "claim": "Barreira",
                            "report_details": {"journey": "Abrir menu"}}]}
    occurrence = report_artifacts.occurrence_records(report_artifacts.normalize_findings(record))[0]
    row = dict(zip(report_artifacts._FINDING_HEADERS, report_artifacts._row(occurrence)))
    assert row["Roteiro"] == "Local exato do problema não registrado"
    assert ["Achados: f1", "Roteiro: localização exata do problema"] in missing_report_data(record)


def test_report_context_keeps_recorded_location_when_adding_other_details():
    source = {"findings": [{"id": "f1", "report_details": {
        "problem_location": "Rodapé > seção Empresa > link Contato", "page_area": "Rodapé",
    }}]}
    enriched = apply_context(source, ReportContext(findings=[FindingDetails(
        finding_id="f1", reproduction_steps=["Pressionar Tab até Contato"],
    )]))
    assert enriched["findings"][0]["report_details"]["problem_location"] == source["findings"][0]["report_details"]["problem_location"]
    assert "reproduction_steps" not in source["findings"][0]["report_details"]
    updated = apply_context(source, ReportContext(findings=[FindingDetails(
        finding_id="f1", problem_location="Cabeçalho > link Contato",
    )]))
    assert updated["findings"][0]["report_details"]["problem_location"] == "Cabeçalho > link Contato"


async def test_reproduction_routes_keep_numbered_actions_and_exact_location_in_all_cards(tmp_path, monkeypatch):
    from docx import Document

    monkeypatch.setenv('A11Y_MCP_HOME', str(tmp_path / 'routes-home'))
    location = 'Página de contato > formulário Fale conosco > campo E-mail (não o campo da newsletter no rodapé)'
    record = apply_context({'url': 'https://example.test/contato', 'findings': [
        {'id': 'f1', 'criterion': '3.3.1', 'claim': 'Erro sem descrição', 'outcome': 'failed'},
    ]}, ReportContext(findings=[FindingDetails(
        finding_id='f1', problem_location=location,
        reproduction_steps_visual=['Abra https://example.test/contato.', 'No formulário Fale conosco, digite abc em E-mail.', 'Acione Enviar e observe a borda vermelha sem mensagem textual.'],
        reproduction_steps_keyboard=['Abra https://example.test/contato e inicie no começo da página.', 'Use Tab até o campo E-mail do formulário Fale conosco, antes da newsletter.', 'Digite abc; use Tab até Enviar e pressione Enter.'],
        reproduction_steps_screen_reader=['No ambiente NVDA e Firefox registrado, abra https://example.test/contato.', 'Navegue por campos até E-mail, no formulário Fale conosco.', 'Digite abc e ative Enviar; confira a identificação do campo com erro.'],
    )]))
    finding = report_artifacts.occurrence_records(report_artifacts.normalize_findings(record))[0]
    row = dict(zip(report_artifacts._FINDING_HEADERS, report_artifacts._row(finding)))
    steps = row['Passos para reproduzir']
    assert row['Roteiro'] == location
    assert 'Com visão\n1. Abra https://example.test/contato.' in steps
    assert 'Por teclado\n1. Abra https://example.test/contato' in steps
    assert 'Sem visão\n1. No ambiente NVDA e Firefox registrado' in steps
    assert ['Achados: f1', 'Passos para reproduzir'] not in missing_report_data(record)
    path = tmp_path / 'routes.xlsx'
    report_artifacts.workbook_report(record, 'QA', path)
    wb = load_workbook(path)
    try:
        fields = {cell.value: cell.column for cell in finding_sheet(wb)[1]}
        visual_cell = finding_sheet(wb).cell(2, fields[report_artifacts.VISUAL_STEPS_HEADER]).value
        reader_cell = finding_sheet(wb).cell(2, fields[report_artifacts.SCREEN_READER_STEPS_HEADER]).value
        assert '1. Abra https://example.test/contato' in visual_cell and 'Por teclado (com visão)' in visual_cell
        assert 'No ambiente NVDA e Firefox registrado' in reader_cell
        assert finding_sheet(wb)['H2'].value == location
    finally:
        wb.close()
    spec = documents.report_spec(record, 'QA')
    card = next(block for block in spec.blocks if block.kind == 'table' and block.text == 'Ficha do achado F1')
    assert dict(card.rows)['Roteiro'] == location
    route_lists = [block for block in spec.blocks if block.kind == 'list' and block.ordered]
    for field in ('reproduction_steps_visual', 'reproduction_steps_keyboard', 'reproduction_steps_screen_reader'):
        assert any(block.items == record['findings'][0]['report_details'][field] for block in route_lists)
    generated = await documents.create(spec, 'both')
    docx_path = next(f['path'] for f in generated['files'] if f['path'].endswith('.docx'))
    pdf_path = next(f['path'] for f in generated['files'] if f['path'].endswith('.pdf'))
    doc = Document(docx_path)
    for step in record['findings'][0]['report_details']['reproduction_steps_keyboard']:
        paragraph = next(p for p in doc.paragraphs if p.text == step)
        assert paragraph._p.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pPr/{http://schemas.openxmlformats.org/wordprocessingml/2006/main}numPr') is not None
    from accessibility_mcp.a11y.document_validation import validate_pdf
    pdf_check = validate_pdf(Path(pdf_path))
    assert pdf_check['facts']['tags'].get('/L', 0) >= 3
    docx_text = '\n'.join(p.text for p in doc.paragraphs)
    pdf_text = '\n'.join(p.extract_text() for p in PdfReader(pdf_path).pages)
    for text in (docx_text, pdf_text):
        assert 'com visão (baixa visão ou QA de acessibilidade)' in text and 'Por teclado' in text and 'sem visão (quem usa leitor de tela)' in text
        assert 'newsletter' in text and 'NVDA e Firefox registrado' in text


def test_visual_route_does_not_invent_keyboard_or_screen_reader_actions():
    from accessibility_mcp.a11y.report_context import reproduction_text

    result = reproduction_text({'reproduction_steps_visual': ['Abra a página e localize o título Contato.']})
    assert result == 'Com visão\n1. Abra a página e localize o título Contato.'


def test_reports_omit_page_title_field_and_preserve_url_and_exact_location(tmp_path):
    record = {'url': 'https://example.test/', 'findings': [
        {'id': 'f1', 'claim': 'Exemplo', 'criterion': '2.4.2', 'outcome': 'failed',
         'report_details': {'page_title': 'TITULO_INTERNO_OMITIDO_123',
                            'problem_location': 'Página inicial > documento HTML > título ausente'}},
    ]}
    path = tmp_path / 'without-page-title.xlsx'
    report_artifacts.workbook_report(record, 'QA', path)
    wb = load_workbook(path)
    try:
        headers = [cell.value for cell in finding_sheet(wb)[1]]
        assert len(headers) == len(report_artifacts._XLSX_HEADERS) and 'Título da página' not in headers
        assert finding_sheet(wb)['H2'].value == record['findings'][0]['report_details']['problem_location']
        assert finding_sheet(wb).cell(2, headers.index('Página (URL)') + 1).value == 'https://example.test/'
        assert 'TITULO_INTERNO_OMITIDO_123' not in str([[c.value for c in row] for sheet in wb for row in sheet])
    finally:
        wb.close()
    spec = documents.report_spec(record, 'QA')
    assert 'TITULO_INTERNO_OMITIDO_123' not in str(spec.model_dump())
    assert record['findings'][0]['report_details']['page_title'] == 'TITULO_INTERNO_OMITIDO_123'


async def test_reports_omit_preconditions_evidence_and_trace_without_removing_reproduction(tmp_path, monkeypatch):
    import copy

    from docx import Document

    monkeypatch.setenv("A11Y_MCP_AUTO_INSTALL", "0")
    record = apply_context({"url": "https://example.test/", "findings": [{
        "id": "f1", "criterion": "2.1.1", "outcome": "failed", "claim": "Controle sem teclado",
        "evidence_steps": [987654321],
    }]}, ReportContext(findings=[FindingDetails(
        finding_id="f1", problem_location="Cabeçalho > botão Menu",
        preconditions="PRECONDICAO_OMITIDA_ABC", evidence="EVIDENCIA_OMITIDA_DEF",
        retest_evidence="RETESTE_OMITIDO_GHI", reproduction_steps=["Pressionar Enter no Menu"],
    )]))
    original = copy.deepcopy(record)
    path = tmp_path / "clean.xlsx"
    report_artifacts.workbook_report(record, "QA", path)
    wb = load_workbook(path)
    try:
        xlsx_text = " ".join(str(c.value) for s in wb for row in s for c in row)
        assert "Referências" not in wb.sheetnames
        assert "Pressionar Enter no Menu" in xlsx_text
        assert not {"Pré-condições", "Evidência", "Evidência (passos do trace)"} & {c.value for c in finding_sheet(wb)[1]}
    finally:
        wb.close()
    spec = documents.report_spec(record, "QA")
    generated = await documents.create(spec, "both")
    docx_path = next(f["path"] for f in generated["files"] if f["path"].endswith(".docx"))
    pdf_path = next(f["path"] for f in generated["files"] if f["path"].endswith(".pdf"))
    doc = Document(docx_path)
    docx_text = " ".join([p.text for p in doc.paragraphs] + [c.text for t in doc.tables for row in t.rows for c in row.cells])
    pdf_text = " ".join(p.extract_text() for p in PdfReader(pdf_path).pages)
    for text in (xlsx_text, docx_text, pdf_text):
        for marker in ("PRECONDICAO_OMITIDA_ABC", "EVIDENCIA_OMITIDA_DEF", "RETESTE_OMITIDO_GHI", "987654321"):
            assert marker not in text
        assert "Pressionar Enter no Menu" in text
        assert "Índice de evidências por ocorrência" not in text
    assert record == original


@pytest.mark.parametrize(("code", "label"), [
    ("P0", "P0 — corrigir imediatamente"), ("P1", "P1 — prioridade alta"),
    ("P2", "P2 — prioridade média"), ("P3", "P3 — prioridade baixa"),
    ("unrated", "A definir"),
])
def test_priority_display_is_explained_in_finding_rows_and_document_facts(code, label):
    finding = {"priority": code, "criterion": "2.1.1"}
    row = dict(zip(report_artifacts._FINDING_HEADERS, report_artifacts._row(finding)))
    assert row["Prioridade"] == label
    assert dict(report_artifacts.finding_facts(finding))["Prioridade"] == label
    assert finding["priority"] == code


def test_reports_use_only_roteiro_for_page_area_and_preserve_distinct_results(tmp_path):
    finding = {"id": "f1", "criterion": "2.4.7", "outcome": "failed", "page_url": "https://example.test/",
               "report_details": {"page_area": "AREA_LEGADA_NAO_EXIBIR_ABC",
                   "problem_location": "Página inicial > formulário Contato > botão Enviar",
                   "expected_result": "Ao receber foco, o botão apresenta um indicador visual.",
                   "actual_result": "O botão recebeu foco por Tab sem indicador visual.",
                   "criterion_rationale": "A ausência do indicador no botão focado contraria o requisito de foco visível de 2.4.7."}}
    record = {"url": "https://example.test/", "findings": [finding]}
    path = tmp_path / "roteiro.xlsx"
    report_artifacts.workbook_report(record, "QA", path)
    wb = load_workbook(path)
    try:
        headers = [c.value for c in finding_sheet(wb)[1]]
        assert len(headers) == len(report_artifacts._XLSX_HEADERS) and "Área da página" not in headers
        row = dict(zip(headers, next(finding_sheet(wb).iter_rows(min_row=2, values_only=True))))
        assert row["Roteiro"] == finding["report_details"]["problem_location"]
        assert row["Justificativa da falha"] == finding["report_details"]["criterion_rationale"]
        assert row["Resultado esperado"] == finding["report_details"]["expected_result"]
    finally:
        wb.close()
    content = str(documents.report_spec(record, "QA").model_dump())
    assert "AREA_LEGADA_NAO_EXIBIR_ABC" not in content
    assert finding["report_details"]["criterion_rationale"] in content
    assert finding["report_details"]["expected_result"] in content
    assert finding["report_details"]["page_area"] == "AREA_LEGADA_NAO_EXIBIR_ABC"


async def test_unexecuted_reader_guidance_is_labeled_in_all_formats_and_does_not_become_evidence(tmp_path, monkeypatch):
    from docx import Document

    from accessibility_mcp.a11y.report_context import reproduction_groups

    monkeypatch.setenv("A11Y_MCP_HOME", str(tmp_path / "reader-guidance"))
    visual = ["Abra https://example.test/contato.", "Localize o botão Enviar no formulário Contato."]
    proposed = ["Com NVDA e Chromium, abra https://example.test/contato; orientação não executada.",
                "No modo de navegação, use H até Contato e B até Enviar."]
    original = {"url": "https://example.test/contato", "coverage": {"gaps": ["Leitor não executado"]},
                "findings": [{"id": "f1", "criterion": "2.1.1", "outcome": "cantTell", "claim": "Exemplo"}]}
    record = apply_context(original, ReportContext(findings=[FindingDetails(finding_id="f1",
        reproduction_steps_visual=visual, reproduction_steps_screen_reader_proposed=proposed)]))
    finding = record["findings"][0]
    assert finding["outcome"] == "cantTell" and record["coverage"] == original["coverage"]
    assert not finding["report_details"].get("reproduction_steps_screen_reader")
    groups = reproduction_groups(finding["report_details"])
    label = "Sem visão — orientação de navegação não executada"
    assert groups == [("Com visão", visual), (label, proposed)]
    workbook = tmp_path / "reader.xlsx"
    report_artifacts.workbook_report(record, "QA", workbook)
    wb = load_workbook(workbook)
    try:
        sheet = finding_sheet(wb);headers = [c.value for c in sheet[1]]
        steps_cell = sheet.cell(2, headers.index(report_artifacts.SCREEN_READER_STEPS_HEADER) + 1)
        visual_cell = sheet.cell(2, headers.index(report_artifacts.VISUAL_STEPS_HEADER) + 1)
        assert sheet.column_dimensions[steps_cell.column_letter].width >= 70
        assert "Roteiro sugerido: NÃO foi executado com leitor de tela" in steps_cell.value and proposed[1] in steps_cell.value
        assert visual[1] in visual_cell.value
    finally:
        wb.close()
    output = await documents.create(documents.report_spec(record, "QA"), "both")
    for item in output["files"]:
        path = Path(item["path"])
        if path.suffix == ".docx":
            doc = Document(path);text = "\n".join(p.text for p in doc.paragraphs)
            paragraph = next(p for p in doc.paragraphs if p.text == proposed[1])
            assert paragraph._p.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pPr/{http://schemas.openxmlformats.org/wordprocessingml/2006/main}numPr") is not None
        else:
            text = "\n".join(p.extract_text() for p in PdfReader(path).pages)
        assert "Roteiro sugerido: NÃO foi executado com leitor de tela" in text and proposed[1] in text and visual[1] in text
