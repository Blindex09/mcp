"""Controles preenchiveis, sumario e destinos reais nos dois formatos."""
import pytest
from docx import Document
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, NameObject, TextStringObject

from accessibility_mcp.a11y import documents
from accessibility_mcp.a11y.document_schema import Block, DocumentSpec
from accessibility_mcp.a11y.document_validation import validate_docx, validate_pdf


@pytest.fixture
def spec():
    return DocumentSpec(title="Formulário com navegação", toc=True, blocks=[
        Block(kind="heading", text="Participação", id="participacao"),
        Block(kind="field", field_name="nome", text="Nome completo", help_text="Informe seu nome.", required=True, value="Ana"),
        Block(kind="field", field_name="area", text="Área de interesse", field_type="choice", help_text="Escolha uma opção.", options=["Web", "Documentos"], value="Documentos"),
        Block(kind="field", field_name="confirmacao", text="Confirmo minha participação", help_text="Marque para confirmar.", field_type="checkbox", checked=True),
        Block(kind="heading", text="Orientações", id="orientacoes"),
        Block(kind="link", text="Voltar à participação", url="#participacao"),
    ])


@pytest.mark.parametrize("change", [
    {"kind":"field", "text":"Nome", "help_text":"Preencha"},
    {"kind":"field", "field_name":"nome", "text":"Nome"},
    {"kind":"field", "field_name":"area", "text":"Área", "help_text":"Escolha", "field_type":"choice", "options":["Web","Web"]},
    {"kind":"field", "field_name":"area", "text":"Área", "help_text":"Escolha", "field_type":"choice", "options":["Web"], "value":"Outra"},
])
def test_invalid_controls_are_rejected(change):
    with pytest.raises(ValueError):
        Block(**change)


def test_destinations_and_field_names_are_checked_before_creating_files(spec):
    for blocks in [spec.blocks+[spec.blocks[1]],
                   [Block(kind="link",text="Destino ausente",url="#ausente")],
                   [Block(kind="heading",text="Um",id="duplicado"),Block(kind="heading",text="Dois",id="duplicado")]]:
        with pytest.raises(ValueError):
            DocumentSpec(title="Teste",blocks=blocks)


def test_word_contains_native_controls_toc_and_bookmark_links(spec, tmp_path):
    path = tmp_path / "controles.docx"
    documents.build_docx(spec, {}, path)
    result = validate_docx(path)
    assert result["issues"] == []
    assert result["facts"]["toc_field"] is True
    assert result["facts"]["heading_levels"][:2] == [1,2]
    assert [field["type"] for field in result["facts"]["fields"]] == ["text","dropDownList","checkbox"]
    doc = Document(path)
    contents_heading = next(p for p in doc.paragraphs if p.style.name == 'MCP Contents Heading')
    assert contents_heading._p.xpath('./w:pPr/w:outlineLvl')[0].get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val') == '1'
    assert contents_heading.style.element.xpath('./w:pPr/w:outlineLvl')[0].get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val') == '9'
    assert len(doc.element.xpath(".//w:sdt")) == 3
    assert len(doc.element.xpath(".//w:hyperlink[@w:anchor]")) == 3
    alias = doc.element.xpath(".//w:sdtPr/w:alias")[0]
    alias.set("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val", "")
    doc.element.xpath(".//w:hyperlink[@w:anchor]")[0].set("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}anchor", "ausente")
    doc.save(path)
    assert {issue["code"] for issue in validate_docx(path)["issues"]} >= {"form_missing_label","broken_internal_link"}


async def test_pdf_fields_are_canonical_tagged_fillable_and_have_appearances(spec, tmp_path):
    path = tmp_path / "controles.pdf"
    await documents.build_pdf(spec, {}, path)
    result = validate_pdf(path)
    assert result["issues"] == []
    reader = PdfReader(path)
    assert set(reader.get_fields()) == {"nome","area","confirmacao"}
    assert reader.get_fields()["nome"]["/V"] == "Ana"
    assert result["facts"]["fields"][0]["required"] is True
    assert result["facts"]["named_destinations"] >= 2
    writer = PdfWriter(clone_from=path)
    writer.update_page_form_field_values(None, {"nome":"João", "area":"Web", "confirmacao":"/Off"}, auto_regenerate=False)
    filled = tmp_path / "preenchido.pdf"
    writer.write(filled)
    assert PdfReader(filled).get_fields()["nome"]["/V"] == "João"
    assert PdfReader(filled).get_fields()["area"]["/V"] == "Web"
    assert validate_pdf(filled)["issues"] == []


async def test_pdf_detects_orphan_label_missing_tag_and_broken_destination(spec, tmp_path):
    path = tmp_path / "controles.pdf"
    await documents.build_pdf(spec, {}, path)
    writer = PdfWriter(clone_from=path)
    for page in writer.pages:
        for ref in page.get('/Annots',[]):
            annot = ref.get_object()
            if annot.get('/Subtype') == '/Widget':
                annot.pop(NameObject('/TU'),None)
                annot.pop(NameObject('/StructParent'),None)
            elif annot.get('/Subtype') == '/Link':
                annot[NameObject('/Dest')] = TextStringObject('ausente')
    writer.root_object['/AcroForm'][NameObject('/Fields')] = ArrayObject()
    writer.write(path)
    assert {issue['code'] for issue in validate_pdf(path)['issues']} >= {'orphan_form_widget','form_missing_label','form_not_tagged','broken_internal_link'}


async def test_multiple_pages_keep_widget_positions_inside_the_page(spec, tmp_path):
    spec.blocks[1:1] = [Block(kind='paragraph',text='Conteúdo de teste para percorrer as páginas. '*12) for _ in range(20)]
    path = tmp_path/'varias-paginas.pdf'
    await documents.build_pdf(spec, {}, path)
    reader = PdfReader(path)
    assert len(reader.pages) > 1
    for page in reader.pages:
        for ref in page.get('/Annots',[]):
            widget = ref.get_object()
            if widget.get('/Subtype') != '/Widget':
                continue
            left,bottom,right,top = widget['/Rect']
            assert 0 <= left < right <= float(page.mediabox.width)
            assert 0 <= bottom < top <= float(page.mediabox.height)
            expected_height = 20 if widget.get('/FT') == '/Btn' else 30
            assert abs(float(top-bottom) - expected_height) < 1
    assert validate_pdf(path)['issues'] == []


async def test_clipping_after_an_image_never_becomes_a_giant_widget(spec, tmp_path):
    import io

    from PIL import Image

    stream = io.BytesIO()
    Image.new('RGB',(700,220),'white').save(stream,format='PNG')
    spec.blocks[1:1] = [Block(kind='image',source='figura.png',alt='Figura de teste.')]
    spec.blocks.insert(-1,Block(kind='field',field_name='notas',text='Notas',help_text='Escreva uma observação.',multiline=True))
    path = tmp_path/'com-imagem.pdf'
    await documents.build_pdf(spec, {'figura.png':stream.getvalue()}, path)
    for page in PdfReader(path).pages:
        for ref in page.get('/Annots',[]):
            field = ref.get_object()
            if field.get('/Subtype') == '/Widget':
                height = float(field['/Rect'][3]-field['/Rect'][1])
                expected = 76 if field.get('/T') == 'notas' else 20 if field.get('/FT') == '/Btn' else 30
                assert abs(height-expected) < 1
