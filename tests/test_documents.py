"""Arquivos reais, defeitos plantados e fronteiras de seguranca dos documentos."""

import json
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest
from docx import Document
from openpyxl import load_workbook
from PIL import Image
from pptx import Presentation
from pydantic import ValidationError
from pypdf import PdfReader, PdfWriter

from accessibility_mcp.a11y import documents, files, report_artifacts
from accessibility_mcp.a11y.document_schema import Assessment, Block, DocumentSpec
from accessibility_mcp.a11y.document_validation import (
    validate,
    validate_docx,
    validate_pdf,
)


def finding_sheet(workbook):
    """Primeira aba de tela com achados (a planilha tem uma aba por tela; a de achados é a que começa em 'Site')."""
    return next(sheet for sheet in workbook.worksheets if sheet["A1"].value == "Site")


def test_pdf_html_keeps_numbered_step_line_breaks_and_escapes_text():
    spec = DocumentSpec(title='Passos', blocks=[Block(kind='paragraph', text='Por teclado\n1. Abra a página.\n2. Localize <Enviar>.')])
    html = documents.build_html(spec, {})
    assert '<p>Por teclado<br>1. Abra a página.<br>2. Localize &lt;Enviar&gt;.</p>' in html


@pytest.fixture(autouse=True)
def no_validator_download_in_unit_tests(monkeypatch):
    monkeypatch.setenv("A11Y_MCP_AUTO_INSTALL", "0")


@pytest.fixture
def spec():
    return DocumentSpec(title="Relatório de acessibilidade", author="Equipe de QA", blocks=[
        Block(kind="paragraph", text="Avaliação de teclado e formulários com evidências."),
        Block(kind="heading", text="Resultados"),
        Block(kind="table", text="Critérios avaliados", headers=["Critério", "Resultado"], rows=[["2.1.1", "Não avaliado"]]),
        Block(kind="list", items=["Conferir o foco", "Verificar os anúncios"]),
        Block(kind="link", text="Diretrizes do W3C", url="https://www.w3.org/WAI/"),
    ])


@pytest.mark.parametrize("status", ["Supports", "Not Applicable", "Partially Supports", "Does Not Support"])
def test_conformance_needs_evidence_not_just_a_status(status):
    with pytest.raises(ValidationError, match="evidencia"):
        Assessment(criterion="2.1.1", status=status, coverage="complete", remarks="Sem achados")


def test_positive_claim_needs_complete_evaluation_and_valid_criterion():
    with pytest.raises(ValidationError, match="cobertura"):
        Assessment(criterion="2.1.1", status="Supports", evidence=["Scanner verde"], remarks="Teste parcial")
    with pytest.raises(ValidationError, match="inexistente"):
        Assessment(criterion="9.9.9", status="Not Evaluated", remarks="Sem teste")
    assert Assessment(criterion="2.1.1", status="Not Evaluated", remarks="Falta teclado").coverage == "not_evaluated"


@pytest.mark.parametrize("block", [
    {"kind": "heading", "level": 3, "text": "Pulo"},
    {"kind": "table", "headers": ["Nome"], "rows": [["A", "B"]]},
    {"kind": "image", "source": "foto.png"},
    {"kind": "link", "text": "Executar", "url": "javascript:alert(1)"},
    {"kind": "link", "text": "Site", "url": "http:sem-servidor"},
    {"kind": "paragraph", "text": " "},
])
def test_incomplete_or_unsafe_document_is_rejected_before_writing(block):
    with pytest.raises(ValidationError):
        DocumentSpec.model_validate({"title": "Teste", "blocks": [block]})


async def test_docx_is_an_actual_semantic_document_and_mutations_are_caught(spec):
    generated = await documents.create(spec, "docx")
    path = Path(generated["files"][0]["path"])
    result = validate_docx(path)
    assert result["issues"] == []
    assert result["facts"]["heading_levels"] == [1, 2]
    assert result["facts"]["language"] == "pt-BR"
    assert result["conformance"] == "not_determined" and not result["complete_validation"]
    doc = Document(str(path))
    assert doc.core_properties.title == spec.title
    assert not doc.styles["Title"].element.xpath("./w:pPr/w:pBdr")
    assert doc.tables[0].cell(1, 1).text == "Não avaliado"
    assert all(row._tr.xpath("./w:trPr/w:cantSplit") for row in doc.tables[0].rows)
    assert all(p.paragraph_format.keep_with_next for cell in doc.tables[0].rows[0].cells for p in cell.paragraphs)
    doc.core_properties.title = ""
    row_properties = doc.tables[0].rows[0]._tr.trPr
    row_properties.remove(row_properties[0])
    doc.save(str(path))
    assert {i["code"] for i in validate_docx(path)["issues"]} >= {"missing_title", "table_missing_header"}


async def test_pdf_has_tags_unicode_fonts_headings_tables_lists_and_links(spec):
    generated = await documents.create(spec, "pdf")
    result = generated["files"][0]["validation"]
    assert result["issues"] == []
    assert result["facts"]["tags"]["/TH"] == 2
    assert result["facts"]["tags"]["/L"] == 1 and result["facts"]["tags"]["/Link"] == 1
    path = Path(generated["files"][0]["path"])
    reader = PdfReader(path)
    assert "Não avaliado" in reader.pages[0].extract_text()
    assert b"<pdfuaid:part>1</pdfuaid:part>" in reader.root_object["/Metadata"].get_data()
    assert reader.pages[0]["/Tabs"] == "/S"
    assert reader.pages[0]["/Annots"][0].get_object()["/Contents"] == "Diretrizes do W3C"
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    del writer.root_object["/StructTreeRoot"]
    writer.write(path)
    assert "missing_tags" in {i["code"] for i in validate_pdf(path)["issues"]}


async def test_pdf_link_description_uses_the_url_actually_normalized_by_the_browser(spec):
    spec.blocks = [Block(kind="link", text="Referência do W3C", url="https://WWW.W3.ORG")]
    result = await documents.create(spec, "pdf")
    reader = PdfReader(result["files"][0]["path"])
    annotation = reader.pages[0]["/Annots"][0].get_object()
    assert annotation["/A"]["/URI"] == "https://www.w3.org/"
    assert annotation["/Contents"] == "Referência do W3C"


async def test_local_image_alt_survives_both_formats_and_missing_alt_is_detected(spec, tmp_path, monkeypatch):
    monkeypatch.setattr(files, "_CHOSEN", tmp_path)
    Image.new("RGB", (300, 100), "white").save(tmp_path / "imagem.png")
    spec.blocks.append(Block(kind="image", source="imagem.png", alt="Fluxo de avaliação do formulário"))
    result = await documents.create(spec)
    for entry in result["files"]:
        assert not entry["validation"]["issues"]
    docx_path = Path(result["files"][0]["path"])
    doc = Document(str(docx_path))
    assert doc.inline_shapes[0]._inline.docPr.get("descr") == "Fluxo de avaliação do formulário"
    del doc.inline_shapes[0]._inline.docPr.attrib["descr"]
    doc.save(str(docx_path))
    assert "image_missing_alt" in {i["code"] for i in validate_docx(docx_path)["issues"]}


async def test_tall_image_fits_the_docx_page(spec, tmp_path, monkeypatch):
    from docx.shared import Cm

    monkeypatch.setattr(files, "_CHOSEN", tmp_path)
    Image.new("RGB", (50, 1000), "white").save(tmp_path / "alta.png")
    spec.blocks.append(Block(kind="image", source="alta.png", alt="Figura vertical"))
    result = await documents.create(spec, "docx")
    doc = Document(result["files"][0]["path"])
    shape = doc.inline_shapes[0]
    assert shape.width <= Cm(12) and shape.height <= Cm(20)
    from docx.shared import Pt
    assert doc.paragraphs[-1].paragraph_format.space_before == Pt(12)


def test_text_is_escaped_and_no_untrusted_html_can_run(spec):
    spec.blocks = [Block(kind="paragraph", text='<script src="http://localhost/segredo"></script>')]
    html = documents.build_html(spec, {})
    assert "<script" not in html and "&lt;script" in html
    assert '<html lang="pt-BR">' in html


def test_document_paths_cannot_escape_or_read_secret_files(tmp_path, monkeypatch):
    monkeypatch.setattr(files, "_CHOSEN", tmp_path)
    for document_id, filename in [("../fora", "document.pdf"), ("a" * 32, "../../.env"), ("a" * 32, "validation.json")]:
        with pytest.raises(ValueError):
            documents.artifact_path(document_id, filename)
    with pytest.raises(files.FileError):
        documents.resolve_input(str(tmp_path / ".env"))
    with pytest.raises(files.FileError):
        documents.resolve_input(str(tmp_path.parent / "fora.pdf"))


async def test_outputs_do_not_overwrite_and_can_be_read_as_resources(spec):
    from accessibility_mcp.server import mcp

    first = await documents.create(spec, "docx")
    second = await documents.create(spec, "docx")
    assert first["document_id"] != second["document_id"]
    contents = await mcp.read_resource(first["files"][0]["uri"])
    assert next(iter(contents)).content[:2] == b"PK"


def test_empty_report_never_invents_conformance_or_passes():
    result = documents.report_spec({"url": "https://exemplo.test", "findings": []}, "Avaliação")
    assert result.assessments == []
    text = " ".join(b.text for b in result.blocks)
    assert "não comprova conformidade" in text and "não avaliados" in text
    with pytest.raises(ValueError, match="portugues"):
        documents.report_spec({}, "Report", "en")


def test_spreadsheet_and_presentation_group_pages_and_keep_exact_locations(tmp_path):
    finding = {
        "criterion": "1.1.1",
        "severity": "moderate",
        "priority": "P2",
        "claim": "=HYPERLINK(\"https://example.invalid\", \"Imagem sem texto alternativo\")",
        "impact": "A pessoa que usa leitor de tela não recebe a informação da imagem.",
        "recommendation": "Adicione um texto alternativo que descreva a imagem.",
        "outcome": "failed",
        "element": {"tag": "img", "role": "img", "name": "Marca"},
        "target": "css:img.logo",
        "location": {"css": "img.logo", "attrs": {"src": "/logo.svg"}},
        "evidence_steps": [2],
    }
    second = {
        **finding,
        "severity": "serious",
        "priority": "P1",
        "element": {"tag": "img", "role": "img", "name": "Marca alternativa"},
        "target": "css:header img.logo",
        "location": {"css": "header img.logo", "attrs": {"src": "/logo.svg"}},
        "page_url": "https://example.test/sobre",
        "evidence_steps": [4],
    }
    record = {
        "url": "https://example.test/",
        "findings": [{**finding, "page_url": "https://example.test/"}, second],
    }
    findings = report_artifacts.normalize_findings(record)
    assert len(findings) == 1
    assert findings[0]["page_urls"] == ["https://example.test/", "https://example.test/sobre"]
    assert findings[0]["severity"] == "serious" and findings[0]["priority"] == "P1"
    assert findings[0]["evidence_steps"] == [2, 4]
    assert {location["selector"] for location in findings[0]["locations"]} == {
        "CSS: img.logo; arquivo: /logo.svg",
        "CSS: header img.logo; arquivo: /logo.svg",
    }
    uncertain = report_artifacts.normalize_findings({
        "findings": [{**finding, "outcome": "cantTell", "page_url": "https://example.test/confirmar"}],
    })
    assert len(uncertain) == 1 and uncertain[0]["outcome"] == "cantTell"
    assert len(report_artifacts.normalize_findings({**record, "findings": [*record["findings"], uncertain[0]]})) == 2

    files = report_artifacts.create(record, "=HYPERLINK(\"https://example.invalid\", \"Resumo\")", ("xlsx", "pptx"), tmp_path)
    assert all(not entry["validation"]["issues"] for entry in files)
    assert all(entry["validation"]["conformance"] == "not_determined" for entry in files)

    workbook = load_workbook(tmp_path / "report.xlsx", data_only=False)
    try:
        sheet = finding_sheet(workbook)
        assert "Resumo" not in workbook.sheetnames
        assert all(cell.data_type != "f" for row in workbook.worksheets[0].iter_rows() for cell in row)
        assert sheet["A1"].value == "Site"
        assert sheet["A2"].value == "example.test"
        rows = [dict(zip(report_artifacts._XLSX_HEADERS, row)) for ws in workbook.worksheets if ws["A1"].value == "Site"
                for row in ws.iter_rows(min_row=2, values_only=True)]
        assert len(rows) == 2
        assert rows[0]["ID"] == "F1"
        assert rows[0]["Prioridade"] == "P2 — prioridade média" and rows[1]["Prioridade"] == "P1 — prioridade alta"
        assert rows[0]["Página (URL)"] == "https://example.test/"
        assert rows[1]["Página (URL)"] == "https://example.test/sobre"
        assert "header img.logo" in rows[1]["Localização (seletor)"]
        assert rows[0]["Problema"].startswith("'=")
        assert all(cell.data_type != "f" for row in sheet.iter_rows() for cell in row)
        assert rows[0]["Critério WCAG"].startswith("1.1.1")
        assert list(report_artifacts.FIRST_SHEETS) == []
        assert list(report_artifacts.LAST_SHEETS) == []
        assert workbook.sheetnames == ["Home", "Sobre"]
    finally:
        workbook.close()

    presentation = Presentation(tmp_path / "report.pptx")
    text = "\n".join(shape.text for slide in presentation.slides for shape in slide.shapes if shape.has_text_frame)
    assert "Problemas confirmados: 1" in text
    assert "Mesmo problema em 2 páginas" in text
    assert "header img.logo" in text


async def test_report_run_ids_generate_xlsx_and_resource_download(tmp_path, monkeypatch):
    from accessibility_mcp.a11y import runs
    from accessibility_mcp.server import mcp

    records = {
        "first": {
            "url": "https://example.test/",
            "findings": [{
                "criterion": "2.1.1", "severity": "serious", "priority": "P1",
                "claim": "O botão não funciona pelo teclado", "outcome": "failed",
                "element": {"tag": "button", "role": "button", "name": "Abrir"},
                "location": {"css": "button#abrir", "attrs": {"id": "abrir"}},
            }],
        },
        "second": {
            "url": "https://example.test/contato",
            "findings": [{
                "criterion": "2.1.1", "severity": "serious", "priority": "P1",
                "claim": "O botão não funciona pelo teclado", "outcome": "failed",
                "element": {"tag": "button", "role": "button", "name": "Abrir"},
                "location": {"css": "button#abrir", "attrs": {"id": "abrir"}},
            }],
        },
    }
    monkeypatch.setattr(documents, "folder", lambda: tmp_path)
    monkeypatch.setattr(runs, "load", records.get)
    tool = mcp._tool_manager.get_tool("a11y_create_report")
    result = json.loads(await tool.fn(formats="xlsx", run_ids=["first", "second"], allow_incomplete=True))
    assert "error" not in result
    downloaded = await mcp.read_resource(f"a11y://document/{result['document_id']}/report.xlsx")
    assert next(iter(downloaded)).content[:2] == b"PK"
    workbook = load_workbook(tmp_path / result["document_id"] / "report.xlsx")
    try:
        rows = [dict(zip(report_artifacts._XLSX_HEADERS, row)) for ws in workbook.worksheets if ws["A1"].value == "Site"
                for row in ws.iter_rows(min_row=2, values_only=True)]
        assert len(rows) == 2
        assert rows[1]["Página (URL)"] == "https://example.test/contato"
    finally:
        workbook.close()


async def test_report_from_saved_run_keeps_evidence_and_coverage():
    from accessibility_mcp.a11y import runs
    from accessibility_mcp.server import mcp

    run_id = runs.save("exemplo.test", {"url": "https://exemplo.test", "findings": [{"criterion": "2.1.1", "claim": "Controle sem teclado", "outcome": "failed", "evidence_steps": [3]}], "coverage": {"gaps": ["NVDA não executado"], "probes_run": ["keyboard_contract"], "actions_taken": 9}})
    tool = mcp._tool_manager.get_tool("a11y_create_report")
    result = json.loads(await tool.fn(formats="docx", run_id=run_id, allow_incomplete=True))
    assert "error" not in result
    path = Path(result["files"][0]["path"])
    document = Document(str(path))
    paragraphs = " ".join(p.text for p in document.paragraphs)
    cells = " ".join(cell.text for table in document.tables for row in table.rows for cell in row.cells)
    text = paragraphs + " " + cells
    assert "Controle sem teclado" in text and "[3]" not in text and "NVDA não executado" in text
    assert "9 ações" in text


async def test_external_validator_missing_is_not_a_pass(spec, monkeypatch):
    from accessibility_mcp.a11y import document_validation

    monkeypatch.delenv("A11Y_MCP_VERAPDF", raising=False)
    monkeypatch.setattr(document_validation.shutil, "which", lambda _: None)
    result = await documents.create(spec, "pdf")
    check = await validate(Path(result["files"][0]["path"]))
    assert check["pdf_ua"]["status"] == "not_run"
    assert check["status"] == "partial"
    assert check["conformance"] == "not_determined"


async def test_pdf_empty_title_is_missing_instead_of_the_string_none(spec, tmp_path):
    from pypdf import PdfWriter

    result = await documents.create(spec, "pdf")
    writer = PdfWriter(clone_from=result["files"][0]["path"])
    writer.add_metadata({"/Title": ""})
    path = tmp_path / "sem-titulo.pdf"
    writer.write(path)
    check = validate_pdf(path)
    assert check["facts"]["title"] == ""
    assert "missing_title" in {issue["code"] for issue in check["issues"]}


def test_docx_with_external_entities_is_rejected(spec, tmp_path):
    from defusedxml.common import DefusedXmlException

    path = tmp_path / "hostil.docx"
    documents.build_docx(spec, {}, path)
    with ZipFile(path) as source:
        members = {name: source.read(name) for name in source.namelist()}
    members["word/document.xml"] = b'<!DOCTYPE x [<!ENTITY xxe SYSTEM "file:///segredo">]><x>&xxe;</x>'
    with ZipFile(path, "w") as target:
        for name, data in members.items():
            target.writestr(name, data)
    with pytest.raises(DefusedXmlException):
        validate_docx(path)


async def test_verapdf_installer_hash_mismatch_never_executes_code(monkeypatch):
    import httpx

    from accessibility_mcp.a11y import verapdf_runtime

    monkeypatch.setenv("A11Y_MCP_AUTO_INSTALL", "1")
    monkeypatch.setattr(verapdf_runtime.shutil, "which", lambda _: sys.executable)
    original_client = httpx.AsyncClient
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=b"instalador adulterado"))
    monkeypatch.setattr(verapdf_runtime.httpx, "AsyncClient", lambda **kwargs: original_client(transport=transport, **kwargs))
    with pytest.raises(ValueError, match="hash"):
        await verapdf_runtime.ensure()
    assert not verapdf_runtime.cached_jar().exists()


@pytest.mark.parametrize(("xml", "returncode", "expected"), [
    (b'<report><validationReport isCompliant="true"/></report>', 0, "passed"),
    (b'<report><validationReport isCompliant="true"/></report>', 2, "error"),
    (b'<report><validationReport isCompliant="false"/></report>', 1, "failed"),
    (b'<report><batchSummary/></report>', 0, "error"),
    (b'nao e XML', 0, "error"),
])
async def test_verapdf_exit_and_report_are_both_checked(monkeypatch, tmp_path, xml, returncode, expected):
    from accessibility_mcp.a11y import document_validation

    class Process:
        def __init__(self):
            self.returncode = returncode

        async def communicate(self):
            return xml, b""

    async def launch(*args, **kwargs):
        assert "--flavour" in args and "ua1" in args
        return Process()

    monkeypatch.setenv("A11Y_MCP_VERAPDF", sys.executable)
    monkeypatch.setattr(document_validation.asyncio, "create_subprocess_exec", launch)
    assert (await document_validation.verapdf(tmp_path / "arquivo.pdf"))["status"] == expected


async def test_same_report_is_never_generated_twice(tmp_path, monkeypatch):
    from accessibility_mcp.a11y import runs
    from accessibility_mcp.server import mcp

    record = {"url": "https://exemplo.test", "findings": [{"criterion": "2.1.1", "claim": "Controle sem teclado", "outcome": "failed"}]}
    monkeypatch.setattr(documents, "folder", lambda: tmp_path)
    monkeypatch.setattr(runs, "load", {"a": record}.get)
    tool = mcp._tool_manager.get_tool("a11y_create_report")
    first = json.loads(await tool.fn(formats="xlsx", run_id="a", allow_incomplete=True))
    second = json.loads(await tool.fn(formats="xlsx", run_id="a", allow_incomplete=True))
    assert "error" not in first and second.get("reused") is True
    assert second["files"][0]["path"] == first["files"][0]["path"]
    assert len([p for p in tmp_path.iterdir() if p.is_dir()]) == 1
    record["findings"][0]["claim"] = "Controle sem teclado e sem foco"
    third = json.loads(await tool.fn(formats="xlsx", run_id="a", allow_incomplete=True))
    # conteudo novo, mesmo relatorio: o mais recente SUBSTITUI o anterior no mesmo caminho, e continua so uma pasta
    assert not third.get("reused") and third["files"][0]["path"] == first["files"][0]["path"]
    assert len([p for p in tmp_path.iterdir() if p.is_dir()]) == 1


def _build_synthetic_tagged_pdf(
    path: Path,
    *,
    display_doc_title: bool = True,
    suspects: bool = False,
    role_map: dict[str, str] | None = None,
    custom_role: str | None = None,
    shared_mcid: bool = False,
    tabs_s: bool = True,
    link_contents: str = "Ir",
    untagged_text: bool = False,
    nested_artifact: bool = False,
    irregular_table: bool = False,
    cid_missing_gidmap: bool = False,
    tounicode_bad: bool = False,
    reverse_order: bool = False,
) -> Path:
    """Constroi um PDF sintetico estruturado minimo para testar cada regra isolada de validate_pdf."""
    from pypdf.generic import (
        ArrayObject,
        BooleanObject,
        DecodedStreamObject,
        DictionaryObject,
        NameObject,
        NumberObject,
        TextStringObject,
    )

    writer = PdfWriter()
    page = writer.add_blank_page(width=400, height=400)
    page_ref = page.indirect_reference
    assert page_ref is not None

    font_desc = writer._add_object(
        DictionaryObject({
            NameObject("/Type"): NameObject("/FontDescriptor"),
            NameObject("/FontName"): NameObject("/TestFont"),
            NameObject("/FontFile2"): writer._add_object(DecodedStreamObject()),
        })
    )
    cid_font_dict = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/CIDFontType2"),
        NameObject("/BaseFont"): NameObject("/TestFont"),
        NameObject("/FontDescriptor"): font_desc,
    })
    if not cid_missing_gidmap:
        cid_font_dict[NameObject("/CIDToGIDMap")] = NameObject("/Identity")
    cid_ref = writer._add_object(cid_font_dict)

    tu_data = (
        "/CIDInit /ProcSet findresource begin 12 dict begin begincmap\n"
        "1 beginbfchar\n<0001> <0000>\nendbfchar\nendcmap\n"
        if tounicode_bad
        else "/CIDInit /ProcSet findresource begin 12 dict begin begincmap\n1 beginbfchar\n<0041> <0041>\nendbfchar\nendcmap\n"
    )
    tu_stream = DecodedStreamObject()
    tu_stream.set_data(tu_data.encode("latin-1"))
    type0 = writer._add_object(
        DictionaryObject({
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type0"),
            NameObject("/BaseFont"): NameObject("/TestFont"),
            NameObject("/Encoding"): NameObject("/Identity-H"),
            NameObject("/DescendantFonts"): ArrayObject([cid_ref]),
            NameObject("/ToUnicode"): writer._add_object(tu_stream),
        })
    )
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): type0})})

    parts: list[str] = []
    for idx in range(5):
        if idx == 1 and nested_artifact:
            parts.append(f"/P <</MCID {idx}>> BDC /Artifact BMC BT /F1 12 Tf 20 300 Td <0041> Tj ET EMC EMC")
        else:
            tag = "/H1" if idx == 0 else "/P"
            parts.append(f"{tag} <</MCID {idx}>> BDC BT /F1 12 Tf 20 {350 - idx * 20} Td <0041> Tj ET EMC")
    if untagged_text:
        parts.append("BT /F1 12 Tf 20 380 Td <0041> Tj ET")
    cs = DecodedStreamObject()
    cs.set_data("\n".join(parts).encode("latin-1"))
    page[NameObject("/Contents")] = writer._add_object(cs)

    mcid_seq = [0, 4, 3, 2, 1] if reverse_order else [0, 1, 2, 3, 4]
    elems = []
    for i, m in enumerate(mcid_seq):
        role = NameObject(f"/{custom_role}") if (custom_role and i == 1) else (NameObject("/H1") if i == 0 else NameObject("/P"))
        elems.append(writer._add_object(DictionaryObject({NameObject("/S"): role, NameObject("/Pg"): page_ref, NameObject("/K"): NumberObject(m)})))
    if shared_mcid:
        elems.append(writer._add_object(DictionaryObject({NameObject("/S"): NameObject("/P"), NameObject("/Pg"): page_ref, NameObject("/K"): NumberObject(1)})))

    if irregular_table:
        c1 = writer._add_object(DictionaryObject({NameObject("/S"): NameObject("/TH"), NameObject("/Pg"): page_ref, NameObject("/K"): NumberObject(1)}))
        c2 = writer._add_object(DictionaryObject({NameObject("/S"): NameObject("/TH"), NameObject("/Pg"): page_ref, NameObject("/K"): NumberObject(2)}))
        r1 = writer._add_object(DictionaryObject({NameObject("/S"): NameObject("/TR"), NameObject("/K"): ArrayObject([c1, c2])}))
        d1 = writer._add_object(DictionaryObject({NameObject("/S"): NameObject("/TD"), NameObject("/Pg"): page_ref, NameObject("/K"): NumberObject(3)}))
        r2 = writer._add_object(DictionaryObject({NameObject("/S"): NameObject("/TR"), NameObject("/K"): ArrayObject([d1])}))
        elems.append(writer._add_object(DictionaryObject({NameObject("/S"): NameObject("/Table"), NameObject("/K"): ArrayObject([r1, r2])})))

    link_struct = writer._add_object(DictionaryObject({NameObject("/S"): NameObject("/Link"), NameObject("/Pg"): page_ref}))
    elems.append(link_struct)
    doc_elem = writer._add_object(DictionaryObject({NameObject("/S"): NameObject("/Document"), NameObject("/K"): ArrayObject(elems)}))
    st_dict = DictionaryObject({NameObject("/Type"): NameObject("/StructTreeRoot"), NameObject("/K"): ArrayObject([doc_elem])})
    if role_map:
        st_dict[NameObject("/RoleMap")] = DictionaryObject({NameObject(f"/{k}"): NameObject(f"/{v}") for k, v in role_map.items()})
    writer.root_object[NameObject("/StructTreeRoot")] = writer._add_object(st_dict)

    annot = DictionaryObject({
        NameObject("/Type"): NameObject("/Annot"),
        NameObject("/Subtype"): NameObject("/Link"),
        NameObject("/Rect"): ArrayObject([NumberObject(10), NumberObject(10), NumberObject(80), NumberObject(30)]),
        NameObject("/StructParent"): NumberObject(0),
        NameObject("/A"): DictionaryObject({NameObject("/S"): NameObject("/URI"), NameObject("/URI"): TextStringObject("https://example.test")}),
    })
    if link_contents:
        annot[NameObject("/Contents")] = TextStringObject(link_contents)
    page[NameObject("/Annots")] = ArrayObject([writer._add_object(annot)])
    if tabs_s:
        page[NameObject("/Tabs")] = NameObject("/S")

    mi = DictionaryObject({NameObject("/Marked"): BooleanObject(True)})
    if suspects:
        mi[NameObject("/Suspects")] = BooleanObject(True)
    writer.root_object[NameObject("/MarkInfo")] = mi
    writer.root_object[NameObject("/Lang")] = TextStringObject("pt-BR")
    writer.root_object[NameObject("/ViewerPreferences")] = DictionaryObject({NameObject("/DisplayDocTitle"): BooleanObject(display_doc_title)})
    writer.add_metadata({"/Title": "Documento Sintetico"})
    writer.write(path)
    return path


@pytest.mark.parametrize(
    ("kwargs", "expected_code"),
    [
        ({}, None),
        ({"suspects": True}, "structure_marked_suspect"),
        ({"display_doc_title": False}, "display_doc_title_missing"),
        ({"role_map": {"A": "B", "B": "A"}}, "role_map_circular"),
        ({"role_map": {"P": "Div"}}, "role_map_remaps_standard"),
        ({"custom_role": "CustomWidget"}, "role_map_unmapped_custom"),
        ({"shared_mcid": True}, "duplicate_mcid_reference"),
        ({"reverse_order": True}, "reading_order_mismatch"),
        ({"nested_artifact": True}, "nested_artifact_tagged"),
        ({"untagged_text": True}, "untagged_page_content"),
        ({"tabs_s": False}, "page_tabs_not_structure"),
        ({"link_contents": ""}, "link_missing_contents"),
        ({"cid_missing_gidmap": True}, "font_missing_cid_to_gid_map"),
        ({"tounicode_bad": True}, "font_tounicode_noncharacter"),
        ({"irregular_table": True}, "table_irregular_grid"),
    ],
)
def test_validate_pdf_deep_structural_checks(tmp_path, kwargs, expected_code):
    pdf_path = _build_synthetic_tagged_pdf(tmp_path / "case.pdf", **kwargs)
    res = validate_pdf(pdf_path)
    codes = {i["code"] for i in res["issues"]}
    if expected_code is None:
        assert codes == set()
    else:
        assert expected_code in codes, (expected_code, res["issues"])

