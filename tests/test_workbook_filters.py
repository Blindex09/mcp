"""Regressao do reparo real do Excel quando dois autofiltros ocupam a tabela."""
from openpyxl import load_workbook

from accessibility_mcp.a11y.report_artifacts import (
    _XLSX_HEADERS,
    validate_xlsx,
    workbook_report,
)


def finding_sheet(workbook):
    """Primeira aba de tela com achados (a planilha tem uma aba por tela; a de achados é a que começa em 'Site')."""
    return next(sheet for sheet in workbook.worksheets if sheet["A1"].value == "Site")


def test_report_uses_only_the_table_filter_and_detects_a_duplicate(tmp_path):
    path = tmp_path / "report.xlsx"
    record = {"findings": [{"claim": "Exemplo didatico", "outcome": "failed"}]}
    workbook_report(record, "Teste", path)
    workbook = load_workbook(path)
    sheet = finding_sheet(workbook)
    table = next(iter(sheet.tables.values()))
    assert table.autoFilter.ref == table.ref
    # Medium2 foi sinalizado pelo verificador nativo do Excel; Light1 passou.
    assert table.tableStyleInfo.name == "TableStyleLight1"
    assert sheet.auto_filter.ref is None
    assert validate_xlsx(path)["issues"] == []
    sheet.auto_filter.ref = table.ref
    workbook.save(path)
    workbook.close()
    assert "overlapping_table_filter" in {
        issue["code"] for issue in validate_xlsx(path)["issues"]
    }


def test_empty_report_keeps_a_worksheet_filter_without_a_table(tmp_path):
    path = tmp_path / "empty.xlsx"
    workbook_report({"findings": []}, "Sem achados", path)
    workbook = load_workbook(path)
    sheet = finding_sheet(workbook)
    assert not sheet.tables
    assert sheet.auto_filter.ref is None
    assert sheet["A1"].value == "Site"
    assert sheet.max_row == 1 and sheet.max_column == len(_XLSX_HEADERS)
    assert sheet.freeze_panes == "D2"
    workbook.close()
