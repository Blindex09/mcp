"""Modelo de relatório: uma aba por tela, passos com visão e sem visão em colunas separadas, código problemático e corrigido em colunas
separadas. O mesmo modelo vale para Word e PDF (seções por tela, passos e código)."""
from openpyxl import load_workbook

from accessibility_mcp.a11y import documents, report_artifacts
from accessibility_mcp.a11y.report_artifacts import (
    _XLSX_HEADERS,
    FIXED_CODE_HEADER,
    OBSERVED_CODE_HEADER,
    SCREEN_READER_STEPS_HEADER,
    VISUAL_STEPS_HEADER,
    screen_of,
    sheet_title,
    workbook_report,
)


def _record():
    return {
        "url": "https://example.test/",
        "report_context": {
            "screens": [
                {"name": "Home", "description": "Página inicial."},
                {"name": "Cotação 3 - Datas e cidadania", "description": "Etapa 3 de 5."},
                {"name": "Cotação 4 - Preferências", "description": "Etapa opcional.",
                 "items": [{"item": "Testado", "detail": "Teclado e navegador."},
                           {"item": "Ponto positivo", "detail": "Caixas de seleção dentro de um grupo com nome."}]},
            ],
        },
        "findings": [
            {"id": "f1", "criterion": "2.4.3", "claim": "O calendário abre sem receber o foco", "outcome": "failed",
             "severity": "serious", "priority": "P0", "page_url": "https://example.test/seguro", "recommendation": "Levar o foco ao diálogo.",
             "report_details": {
                 "screen": "Cotação 3 - Datas e cidadania",
                 "reproduction_steps_visual": ["Abrir a página e clicar em Selecionar."],
                 "reproduction_steps_keyboard": ["Apertar Tab até Selecionar e Enter."],
                 "reproduction_steps_screen_reader": ["Apertar Tab: o NVDA fala \"Selecionar, botão\"."],
                 "code_snippet": "<button type=\"button\">Selecionar</button>\ncreatePortal(dialogo, document.body)",
                 "fixed_code": "<button type=\"button\" aria-label=\"Selecionar datas da viagem\">Selecionar</button>",
             }},
            {"id": "f2", "criterion": "1.4.3", "claim": "Texto com contraste baixo", "outcome": "failed",
             "severity": "serious", "priority": "P1", "page_url": "https://example.test/",
             "report_details": {"screen": "Todas as telas", "reproduction_steps_visual": ["Medir o contraste."]}},
            {"id": "f3", "criterion": "4.1.3", "claim": "Troca de tela sem aviso", "outcome": "failed",
             "severity": "serious", "priority": "P1", "page_url": "https://example.test/",
             "report_details": {"reproduction_steps_screen_reader_proposed": ["Apertar Enter em Começar."]}},
        ],
    }


def test_workbook_has_one_sheet_per_screen_and_the_template_columns(tmp_path):
    path = tmp_path / "modelo.xlsx"
    assert not workbook_report(_record(), "QA", path)["issues"]
    wb = load_workbook(path)
    try:
        assert wb.sheetnames == ["Home", "Cotação 3 - Datas e cidadania", "Cotação 4 - Preferências",
                                 "Todas as telas"]
        assert "Achados" not in wb.sheetnames
        date_sheet = wb["Cotação 3 - Datas e cidadania"]
        headers = [cell.value for cell in date_sheet[1]]
        assert headers == _XLSX_HEADERS
        assert headers.index(OBSERVED_CODE_HEADER) + 1 == headers.index(FIXED_CODE_HEADER)
        row = dict(zip(headers, [cell.value for cell in date_sheet[2]]))
        assert "Abrir a página" in row[VISUAL_STEPS_HEADER] and "Por teclado (com visão)" in row[VISUAL_STEPS_HEADER]
        assert "Apertar Tab: o NVDA fala" in row[SCREEN_READER_STEPS_HEADER]
        assert "Executado com leitor de tela real" in row[SCREEN_READER_STEPS_HEADER]
        assert "createPortal(dialogo, document.body)" in row[OBSERVED_CODE_HEADER]
        assert "aria-label" in row[FIXED_CODE_HEADER] and "createPortal" not in row[FIXED_CODE_HEADER]
        # tela sem achado declarada: ficha de itens
        notes = wb["Cotação 4 - Preferências"]
        assert [cell.value for cell in notes[1]] == ["Item", "Detalhe"]
        assert [cell.value for cell in notes["A"]][1:3] == ["Testado", "Ponto positivo"]
        # achado sem passos com leitor: não se inventa fala
        home = wb["Home"]
        home_headers = [cell.value for cell in home[1]]
        proposed = dict(zip(home_headers, [cell.value for cell in home[2]]))
        assert "NÃO foi executado com leitor de tela" in proposed[SCREEN_READER_STEPS_HEADER]
        every = wb["Todas as telas"]
        every_row = dict(zip(home_headers, [cell.value for cell in every[2]]))
        assert every_row[SCREEN_READER_STEPS_HEADER] == "Não executado com leitor de tela nesta ocorrência."
        names = [name for sheet in wb.worksheets for name in sheet.tables]
        assert len(names) == len(set(names)) and all("-" not in name and " " not in name for name in names)
        for sheet in wb.worksheets:
            assert len(sheet.title) <= 31
    finally:
        wb.close()


def test_screen_name_falls_back_to_the_url_path():
    assert screen_of({"page_urls": ["https://example.test/"]}) == "Home"
    assert screen_of({"page_urls": ["https://example.test/salas-vip"]}) == "Salas vip"
    assert screen_of({"report_details": {"screen": "Compra - Dados"}, "page_urls": ["https://example.test/x"]}) == "Compra - Dados"


def test_sheet_titles_are_valid_and_unique():
    used: set[str] = set()
    first = sheet_title("Cotação: etapa [3]/5 com um nome muito comprido demais", used)
    second = sheet_title("Cotação: etapa [3]/5 com um nome muito comprido demais", used)
    assert len(first) <= 31 and len(second) <= 31 and first != second
    assert not set("[]:*?/\\") & set(first + second)


def test_word_and_pdf_follow_the_same_template():
    spec = documents.report_spec(_record(), "QA")
    headings = [block.text for block in spec.blocks if block.kind == "heading" and block.level == 3]
    wanted = ["Home", "Cotação 3 - Datas e cidadania", "Cotação 4 - Preferências", "Todas as telas"]
    assert [heading for heading in headings if heading in wanted] == wanted
    text = " ".join(block.text for block in spec.blocks if block.kind in ("paragraph", "heading"))
    assert report_artifacts.VISUAL_STEPS_LABEL in text and report_artifacts.SCREEN_READER_STEPS_LABEL in text
    code_tables = [block for block in spec.blocks if block.kind == "table" and block.text in report_artifacts.CODE_LABELS]
    assert {block.text for block in code_tables} == set(report_artifacts.CODE_LABELS)
    observed = next(block for block in code_tables if block.text == report_artifacts.OBSERVED_CODE_LABEL)
    assert ["createPortal(dialogo, document.body)"] in observed.rows
    notes = next(block for block in spec.blocks if block.kind == "table" and block.text == "Tela testada: Cotação 4 - Preferências")
    assert ["Testado", "Teclado e navegador."] in notes.rows


def test_design_impact_column_and_edit_tools_are_off_by_default(monkeypatch, tmp_path):
    record = _record()
    record["findings"][0]["report_details"]["design_impact"] = "Nenhum: só muda o nome acessível, nada visível."
    path = tmp_path / "impacto.xlsx"
    assert not workbook_report(record, "QA", path)["issues"]
    wb = load_workbook(path)
    try:
        sheet = wb["Cotação 3 - Datas e cidadania"]
        headers = [cell.value for cell in sheet[1]]
        assert headers.index(FIXED_CODE_HEADER) + 1 == headers.index("Impacto no design")
        row = dict(zip(headers, [cell.value for cell in sheet[2]]))
        assert row["Impacto no design"].startswith("Nenhum")
        other = dict(zip(headers, [cell.value for cell in wb["Todas as telas"][2]]))
        assert other["Impacto no design"] == "Não registrado"
    finally:
        wb.close()
    spec = documents.report_spec(record, "QA")
    text = " ".join(block.text for block in spec.blocks if block.kind in ("paragraph", "heading"))
    assert report_artifacts.DESIGN_IMPACT_LABEL in text and "Nenhum: só muda o nome acessível" in str(spec.model_dump())

    import asyncio

    from mcp.server.fastmcp import FastMCP

    from accessibility_mcp.a11y import tools_files

    async def names() -> set[str]:
        server = FastMCP("t")
        tools_files.register_files(server)
        return {tool.name for tool in await server.list_tools()}

    monkeypatch.delenv("A11Y_MCP_ALLOW_EDITS", raising=False)
    off = asyncio.run(names())
    assert {"a11y_set_workspace", "a11y_read_file"} <= off
    assert not {"a11y_edit_file", "a11y_approve_edit", "a11y_undo_edit"} & off
    monkeypatch.setenv("A11Y_MCP_ALLOW_EDITS", "1")
    assert {"a11y_edit_file", "a11y_approve_edit", "a11y_undo_edit"} <= asyncio.run(names())
