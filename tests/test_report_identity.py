"""Relatorio com nome estavel (o mais recente prevalece) e achado sempre com o elemento identificado."""
import json

import pytest

from accessibility_mcp.a11y import documents, report_lint, runs
from accessibility_mcp.a11y.session import SESSION

PAGE = ('<!doctype html><html lang="pt"><title>t</title><body><main><h1>Titulo</h1><p id="aviso">Texto legal do rodape</p>'
        '<h3 id="salto">Produtos</h3></main></body></html>')


def _record(claim: str) -> dict:
    return {"url": "https://exemplo.test/contato", "findings": [{
        "criterion": "2.1.1", "severity": "serious", "priority": "P1", "claim": claim, "outcome": "failed",
        "element": {"tag": "button", "role": "button", "name": "Abrir"}, "location": {"css": "button#abrir", "attrs": {"id": "abrir"}},
    }]}


async def test_the_same_report_name_always_lands_on_the_same_file_and_the_newest_replaces_it(tmp_path, monkeypatch):
    from accessibility_mcp.server import mcp

    monkeypatch.setattr(documents, "folder", lambda: tmp_path)
    monkeypatch.setattr(runs, "load", lambda run_id: _record("Primeira versao do achado"))
    tool = mcp._tool_manager.get_tool("a11y_create_report")
    first = json.loads(await tool.fn(formats="xlsx", run_id="r1", title="Relatorio da pagina de contato", allow_incomplete=True))
    monkeypatch.setattr(runs, "load", lambda run_id: _record("Segunda versao do achado"))
    second = json.loads(await tool.fn(formats="xlsx", run_id="r1", title="  relatorio da PAGINA de contato ", allow_incomplete=True))
    assert first["document_id"] == second["document_id"] and first["files"][0]["path"] == second["files"][0]["path"]
    assert [p.name for p in tmp_path.iterdir() if p.is_dir()] == [first["document_id"]]  # nunca duas pastas para o mesmo relatorio
    from openpyxl import load_workbook

    workbook = load_workbook(second["files"][0]["path"])
    try:
        text = " ".join(str(c) for ws in workbook.worksheets for row in ws.iter_rows(values_only=True) for c in row if c)
    finally:
        workbook.close()
    assert "Segunda versao do achado" in text and "Primeira versao do achado" not in text
    index = json.loads((tmp_path / "relatorios-gerados.json").read_text(encoding="utf-8"))
    assert len(index) == 1  # a impressao digital antiga nao fica apontando para a pasta substituida


async def test_different_names_or_format_groups_never_overwrite_each_other(tmp_path, monkeypatch):
    monkeypatch.setattr(documents, "folder", lambda: tmp_path)
    ids = {documents.report_id("artifact:xlsx", "Relatorio A", "pt-BR"), documents.report_id("artifact:xlsx", "Relatorio B", "pt-BR"),
           documents.report_id("artifact:pptx", "Relatorio A", "pt-BR"), documents.report_id("artifact:xlsx", "Relatorio A", "pt")}
    assert len(ids) == 4
    first = documents.fresh_folder(documents.report_id("artifact:xlsx", "Relatorio A", "pt-BR"))
    (first / "report.xlsx").write_bytes(b"velho")
    again = documents.fresh_folder(documents.report_id("artifact:xlsx", "Relatorio A", "pt-BR"))
    assert again == first and list(again.iterdir()) == []
    with pytest.raises(ValueError, match="invalido"):
        documents.fresh_folder("../fora")


@pytest.fixture
async def page():
    await SESSION.open(None, PAGE, persona="default")
    try:
        yield
    finally:
        await SESSION.close()


async def test_a_finding_on_any_element_gets_its_tag_role_and_name_from_the_browser(page):
    from accessibility_mcp.server import mcp

    tool = mcp._tool_manager.get_tool("a11y_finding")
    texto = json.loads(await tool.fn(claim="Texto legal pequeno", criterion="1.4.3", target="css:#aviso"))["recorded"]
    assert texto["element"] == {"tag": "p", "role": "paragraph", "name": "Texto legal do rodape"} and texto["location"]["css"] == "#aviso"
    titulo = json.loads(await tool.fn(claim="Salto de nivel", criterion="1.3.1", target="css:#salto"))["recorded"]
    assert titulo["element"]["tag"] == "h3" and titulo["element"]["role"] == "heading" and titulo["element"]["name"] == "Produtos"


async def test_a_finding_whose_target_matches_nothing_is_refused_instead_of_saved_without_element(page):
    from accessibility_mcp.server import mcp

    tool = mcp._tool_manager.get_tool("a11y_finding")
    refused = json.loads(await tool.fn(claim="Nada aqui", criterion="1.3.1", target="css:#nao-existe"))
    assert "nao existe na pagina" in refused["error"] and SESSION.findings == []


def test_the_report_lint_blocks_a_finding_with_no_identified_element():
    record = {"url": "https://exemplo.test", "findings": [{
        "id": "f1", "criterion": "1.4.3", "severity": "moderate", "priority": "P2", "claim": "Contraste baixo", "outcome": "failed", "target": "css:p",
        "report_details": {"screen": "Home", "code_snippet": "x", "fixed_code": "y", "code_verified": True, "fix_tested": True, "design_impact": "Nenhum",
                           "reproduction_steps_visual": ["abrir"]}}]}
    issues = report_lint.lint(record, ("xlsx",))["issues"]
    gap = [i for i in issues if i["rule"] == "campo_vazio" and "Elemento não identificado" in i["message"]]
    assert gap and "target css" in gap[0]["message"]
