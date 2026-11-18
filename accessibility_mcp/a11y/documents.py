"""Geracao de DOCX semantico e PDF marcado, sem chamar modelo nem executar HTML do cliente."""

from __future__ import annotations

import asyncio
import base64
import io
import json
import os
import re
import uuid
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any, Literal

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from PIL import Image
from playwright.async_api import async_playwright
from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    BooleanObject,
    ContentStream,
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
    TextStringObject,
)

from . import document_controls as controls
from . import files, learn, pdf_forms, wcag
from .document_schema import Block, DocumentSpec
from .document_validation import validate
from .provisioning import provisioner_for

Formats = Literal["docx", "pdf", "both"]
MIMES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
    "report.xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "report.pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


def folder() -> Path:
    """Pasta dos documentos gerados. A11Y_MCP_DOCUMENTS_DIR a substitui; por padrao fica dentro da pasta de dados."""
    override = os.environ.get("A11Y_MCP_DOCUMENTS_DIR", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return learn.store_path().resolve() / "documents"


def artifact_path(document_id: str, filename: str) -> Path:
    if not re.fullmatch(r"[a-f0-9]{32}", document_id) or filename not in ("document.docx", "document.pdf", "report.xlsx", "report.pptx"):
        raise ValueError("Identificador ou nome de documento invalido.")
    root = folder()
    path = (root / document_id / filename).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Caminho fora da pasta de documentos.")
    return path


def resolve_input(path: str) -> Path:
    candidate = Path(path).expanduser().resolve()
    if candidate.is_relative_to(folder()):
        relative = candidate.relative_to(folder())
        if len(relative.parts) != 2:
            raise ValueError("Caminho de documento invalido.")
        return artifact_path(*relative.parts)
    return files.resolve(path)


def _images(spec: DocumentSpec) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    for block in spec.blocks:
        if block.kind == "image":
            path = files.resolve(block.source)
            if path.suffix.lower() not in (".png", ".jpg", ".jpeg"):
                raise ValueError("Imagem deve ser PNG ou JPEG local, dentro da pasta escolhida.")
            with Image.open(path) as image:
                image.load()
                stream = io.BytesIO()
                image.convert("RGB").save(stream, format="PNG")
                result[block.source] = stream.getvalue()
    return result


def _all_blocks(spec: DocumentSpec) -> list[Block]:
    blocks = list(spec.blocks)
    if spec.assessments:
        blocks.append(Block(kind="heading", text="Avaliação por critério", level=2))
        for assessment in spec.assessments:
            blocks.append(Block(kind="heading", text=f"WCAG {assessment.criterion}", level=3))
            blocks.append(Block(kind="paragraph", text=f"Resultado: {assessment.status}. Cobertura declarada: {assessment.coverage}. {assessment.remarks}"))
            if assessment.evidence:
                blocks.append(Block(kind="list", items=assessment.evidence))
        blocks.append(Block(kind="paragraph", text="Critérios não listados não foram avaliados neste documento. A avaliação se limita ao escopo e às evidências declarados."))
    return blocks


def _property(parent: Any, tag: str, **attrs: str) -> Any:
    element = OxmlElement(tag)
    for name, value in attrs.items():
        element.set(qn(name), value)
    parent.append(element)
    return element


def build_docx(spec: DocumentSpec, images: dict[str, bytes], path: Path) -> None:
    doc = Document()
    props = doc.core_properties
    props.title, props.subject, props.author = spec.title, spec.subject, spec.author
    props.language = spec.language
    props.comments = ""
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.top_margin = section.bottom_margin = section.left_margin = section.right_margin = Cm(2)
    normal = doc.styles["Normal"]
    normal.font.name, normal.font.size = "Arial", Pt(11)
    normal.font.color.rgb = RGBColor(0, 0, 0)
    normal.paragraph_format.line_spacing = 1.3
    normal.paragraph_format.space_after = Pt(8)
    defaults = doc.styles.element.find(qn("w:docDefaults"))
    rpr_default = defaults.find(qn("w:rPrDefault"))
    rpr = rpr_default.find(qn("w:rPr"))
    lang = rpr.find(qn("w:lang"))
    if lang is None:
        lang = _property(rpr, "w:lang")
    lang.set(qn("w:val"), spec.language)
    for name in ("Title", "Heading 1", "Heading 2", "Heading 3", "Heading 4", "Heading 5", "Heading 6"):
        doc.styles[name].font.color.rgb = RGBColor(0, 0, 0)
        paragraph_properties = doc.styles[name].element.find(qn("w:pPr"))
        if paragraph_properties is not None:
            for border in list(paragraph_properties.findall(qn("w:pBdr"))):
                paragraph_properties.remove(border)
    doc.styles["Caption"].font.color.rgb = RGBColor(0, 0, 0)
    doc.styles["Caption"].font.size = Pt(11)
    title = doc.add_paragraph(spec.title, "Title")
    _property(title._p.get_or_add_pPr(), "w:outlineLvl", **{"w:val": "0"})
    controls.bookmark(title, "document_title", 0)
    blocks = _all_blocks(spec)
    entries = controls.destinations(blocks)
    if spec.toc:
        controls.table_of_contents(doc, entries, spec.language.startswith("pt"))
    heading_number = 0
    for index, block in enumerate(blocks, 1):
        if block.kind == "heading":
            paragraph = doc.add_heading(block.text, level=block.level)
            controls.bookmark(paragraph, entries[heading_number][1], heading_number+1)
            heading_number += 1
        elif block.kind == "paragraph":
            doc.add_paragraph(block.text)
        elif block.kind == "list":
            # Cada lista numerada tem sua propria instancia para recomecar em 1.
            style = "List Number" if block.ordered else "List Bullet"
            numbering = doc.part.numbering_part.element
            style_id = doc.styles[style].style_id
            abstract = numbering.xpath(f'./w:abstractNum[w:lvl/w:pStyle[@w:val="{style_id}"]]')
            num_id = None
            if abstract:
                num = numbering.add_num(int(abstract[0].get(qn("w:abstractNumId"))))
                num.add_lvlOverride(ilvl=0).add_startOverride(1)
                num_id = num.numId
            for item in block.items:
                paragraph = doc.add_paragraph(item, style)
                if num_id is not None:
                    numbering_properties = paragraph._p.get_or_add_pPr().get_or_add_numPr()
                    numbering_properties.get_or_add_ilvl().val = 0
                    numbering_properties.get_or_add_numId().val = num_id
        elif block.kind == "table":
            caption = doc.add_paragraph(block.text, "Caption")
            caption.paragraph_format.keep_with_next = True
            table = doc.add_table(rows=1, cols=len(block.headers))
            table.style = "Table Grid"
            table.autofit = False
            _property(table.rows[0]._tr.get_or_add_trPr(), "w:tblHeader", **{"w:val": "true"})
            _property(table._tbl.tblPr, "w:tblCaption", **{"w:val": block.text})
            for cell, text in zip(table.rows[0].cells, block.headers):
                cell.text = text
                for run in cell.paragraphs[0].runs:
                    run.bold = True
            for row in block.rows:
                cells = table.add_row().cells
                for cell, text in zip(cells, row):
                    cell.text = text
            keep_table = block.text.startswith("Ficha do achado") or len(block.rows) <= 3
            for row_index, table_row in enumerate(table.rows):
                _property(table_row._tr.get_or_add_trPr(), "w:cantSplit")
                if row_index == 0 or (keep_table and row_index < len(table.rows) - 1):
                    for cell in table_row.cells:
                        for paragraph in cell.paragraphs:
                            paragraph.paragraph_format.keep_with_next = True
        elif block.kind == "image":
            with Image.open(io.BytesIO(images[block.source])) as image:
                width, height = image.size
            scale = min(12 / width, 20 / height)
            shape = doc.add_picture(io.BytesIO(images[block.source]), width=Cm(width * scale))
            shape._inline.docPr.set("descr", block.alt)
            picture_paragraph = doc.paragraphs[-1]
            picture_paragraph.paragraph_format.space_before = Pt(12)
            picture_paragraph.paragraph_format.space_after = Pt(12)
            picture_paragraph.paragraph_format.line_spacing = 1.0
        elif block.kind == "link":
            paragraph = doc.add_paragraph()
            if block.url.startswith("#"):
                controls.internal_link(paragraph, block.url[1:], block.text)
                continue
            link = OxmlElement("w:hyperlink")
            rel = doc.part.relate_to(block.url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
            link.set(qn("r:id"), rel)
            run = _property(link, "w:r")
            properties = _property(run, "w:rPr")
            _property(properties, "w:color", **{"w:val": "000080"})
            _property(properties, "w:u", **{"w:val": "single"})
            _property(run, "w:t").text = block.text
            paragraph._p.append(link)
        elif block.kind == "field":
            controls.word_field(doc, block, index, spec.language.startswith("pt"))
    doc.save(str(path))


def build_html(spec: DocumentSpec, images: dict[str, bytes]) -> str:
    blocks = _all_blocks(spec)
    entries = controls.destinations(blocks)
    body = [f'<h1 id="document_title">{escape(spec.title)}</h1>']
    if spec.toc:
        links = ''.join(f'<li><a href="#{ident}">{escape(block.text)}</a></li>' for block, ident in entries)
        caption = "Sumário" if spec.language.startswith("pt") else "Contents"
        body.append(f'<nav aria-label="{caption}"><h2>{caption}</h2><ul>{links}</ul></nav>')
    heading_number = 0
    for block in blocks:
        text = escape(block.text)
        if block.kind == "heading":
            ident = entries[heading_number][1]
            heading_number += 1
            body.append(f'<h{block.level} id="{ident}">{text}</h{block.level}>')
        elif block.kind == "paragraph":
            body.append("<p>" + text.replace("\n", "<br>") + "</p>")
        elif block.kind == "list":
            tag = "ol" if block.ordered else "ul"
            body.append(f"<{tag}>" + "".join(f"<li>{escape(s)}</li>" for s in block.items) + f"</{tag}>")
        elif block.kind == "table":
            head = "".join(f'<th scope="col">{escape(h)}</th>' for h in block.headers)
            rows = "".join("<tr>" + "".join(f"<td>{escape(c)}</td>" for c in row) + "</tr>" for row in block.rows)
            keep = ' class="keep"' if text.startswith("Ficha do achado") or len(block.rows) <= 3 else ""
            body.append(f"<table{keep}><caption>{text}</caption><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>")
        elif block.kind == "image":
            encoded = base64.b64encode(images[block.source]).decode("ascii")
            body.append(f'<img src="data:image/png;base64,{encoded}" alt="{escape(block.alt, quote=True)}">')
        elif block.kind == "link":
            body.append(f'<p><a href="{escape(block.url, quote=True)}">{text}</a></p>')
        elif block.kind == "field":
            label = controls.field_label(block, spec.language.startswith("pt"))
            name = escape(block.field_name, quote=True)
            accessible = escape(label + '. ' + block.help_text, quote=True)
            if block.field_type == "choice":
                # Chromium imprime select sem tag Form; o controle AcroForm /Ch
                # real e ligado a esta caixa marcada depois da impressao.
                control = f'<input type="text" id="{name}" aria-label="{accessible}">'
            elif block.multiline:
                control = f'<textarea id="{name}" aria-label="{accessible}"></textarea>'
            else:
                kind = 'checkbox' if block.field_type == 'checkbox' else 'text'
                control = f'<input type="{kind}" id="{name}" aria-label="{accessible}">'
            body.append(f'<div class="document-field"><p><label for="{name}">{escape(label)}</label></p><p>{escape(block.help_text)}</p>{control}</div>')
    return f'''<!doctype html><html lang="{escape(spec.language, quote=True)}"><head><meta charset="utf-8">
<title>{escape(spec.title)}</title><meta name="author" content="{escape(spec.author, quote=True)}">
<style>@page {{size:A4;margin:20mm}} body {{font:11pt Arial,sans-serif;line-height:1.4;color:#000;background:#fff}}
h1 {{font-size:24pt}} h2 {{font-size:18pt}} h3 {{font-size:14pt}} h1,h2,h3,h4,h5,h6 {{break-after:avoid}}
p,li,td,th {{overflow-wrap:anywhere}} p {{orphans:3;widows:3}} table {{width:100%;border-collapse:collapse;table-layout:fixed}}
caption {{text-align:left;font-weight:bold;margin:8pt 0;break-after:avoid}} th,td {{border:1px solid #555;padding:6pt;text-align:left;vertical-align:top}}
thead {{display:table-header-group}} tr {{break-inside:avoid}} table.keep {{break-inside:avoid}} img {{max-width:100%;max-height:220mm;object-fit:contain}}
a {{color:#000080;text-decoration:underline}} .document-field {{break-inside:avoid;margin:14pt 0}}
input,select,textarea {{font:11pt Arial;border:1pt solid #000;border-radius:0;width:100%;height:30pt;box-sizing:border-box;background:#fff;color:#000}}
textarea {{height:76pt}} input[type=checkbox] {{width:20pt;height:20pt}}</style></head><body>{''.join(body)}</body></html>'''


async def build_pdf(spec: DocumentSpec, images: dict[str, bytes], path: Path) -> None:
    await provisioner_for("chromium").ensure()
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            page = await browser.new_page(java_script_enabled=False)
            await page.route("**/*", lambda route: route.abort())
            await page.set_content(build_html(spec, images))
            links = await page.locator("a").evaluate_all("anchors => Object.fromEntries(anchors.map(a => [a.href, a.textContent]))")
            await page.pdf(path=str(path), tagged=True, outline=True, prefer_css_page_size=True, print_background=True)
        finally:
            await browser.close()
    await asyncio.to_thread(_finish_pdf, spec, path, links)


def _finish_pdf(spec: DocumentSpec, path: Path, links: dict[str, str]) -> None:
    """Completa lacunas objetivas do exportador Chromium, preservando a arvore de tags.

    O Chromium deixa o fundo da pagina sem Artifact, links sem Contents e nao escreve XMP.
    So marcamos pintura grafica sem MCID como decoracao; texto nunca e descartado como artefato.
    """
    writer = PdfWriter()
    writer.clone_document_from_reader(PdfReader(path))
    painting = {b"f", b"F", b"f*", b"S", b"s", b"B", b"B*", b"b", b"b*", b"sh"}
    for page in writer.pages:
        page[NameObject("/Tabs")] = NameObject("/S")
        stream = ContentStream(page["/Contents"], writer)
        operations, depth = [], 0
        for operands, operator in stream.operations:
            if operator in (b"BDC", b"BMC"):
                depth += 1
            if depth == 0 and operator in painting:
                operations.extend([([NameObject("/Artifact")], b"BMC"), (operands, operator), ([], b"EMC")])
            else:
                operations.append((operands, operator))
            if operator == b"EMC":
                depth -= 1
        stream.operations = operations
        page[NameObject("/Contents")] = writer._add_object(stream)
        for ref in page.get("/Annots", []):
            annot = ref.get_object()
            action = annot.get("/A")
            action = action.get_object() if action is not None else {}
            uri = str(action.get("/URI", ""))
            if annot.get("/Subtype") == "/Link" and uri in links:
                annot[NameObject("/Contents")] = TextStringObject(links[uri])
            elif annot.get("/Subtype") == "/Link" and "/Dest" in annot:
                destination = str(annot["/Dest"]).lstrip("/")
                labels = [text for href, text in links.items() if href.endswith("#" + destination)]
                if labels:
                    annot[NameObject("/Contents")] = TextStringObject(labels[0])
    pdf_forms.prepare_lists(writer)
    pdf_forms.add_forms(writer, [block for block in _all_blocks(spec) if block.kind == "field"], spec.language.startswith("pt"))
    writer.root_object[NameObject("/ViewerPreferences")] = DictionaryObject({NameObject("/DisplayDocTitle"): BooleanObject(True)})
    metadata = DecodedStreamObject()
    metadata.set_data(f'''<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
<rdf:Description rdf:about="" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:pdfuaid="http://www.aiim.org/pdfua/ns/id/">
<pdfuaid:part>1</pdfuaid:part><dc:title><rdf:Alt><rdf:li xml:lang="x-default">{escape(spec.title)}</rdf:li></rdf:Alt></dc:title>
<dc:language><rdf:Bag><rdf:li>{escape(spec.language)}</rdf:li></rdf:Bag></dc:language>
<dc:creator><rdf:Seq><rdf:li>{escape(spec.author)}</rdf:li></rdf:Seq></dc:creator>
</rdf:Description></rdf:RDF></x:xmpmeta><?xpacket end="w"?>'''.encode())
    metadata[NameObject("/Type")] = NameObject("/Metadata")
    metadata[NameObject("/Subtype")] = NameObject("/XML")
    writer.root_object[NameObject("/Metadata")] = writer._add_object(metadata)
    writer.generate_file_identifiers()
    buffer = io.BytesIO()
    writer.write(buffer)
    path.write_bytes(buffer.getvalue())


async def create(spec: DocumentSpec, formats: Formats = "both") -> dict[str, Any]:
    if formats not in ("docx", "pdf", "both"):
        raise ValueError("Formato deve ser docx, pdf ou both.")
    images = _images(spec)
    document_id = uuid.uuid4().hex
    target = folder() / document_id
    target.mkdir(parents=True, exist_ok=False)
    outputs: list[dict[str, Any]] = []
    for kind in ("docx", "pdf") if formats == "both" else (formats,):
        path = artifact_path(document_id, f"document.{kind}")
        if kind == "docx":
            await asyncio.to_thread(build_docx, spec, images, path)
        else:
            await build_pdf(spec, images, path)
        validation = await validate(path)
        outputs.append({"path": str(path), "uri": f"a11y://document/{document_id}/document.{kind}",
                        "mime_type": MIMES[kind], "bytes": path.stat().st_size, "validation": validation})
    (target / "validation.json").write_text(json.dumps(outputs, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"document_id": document_id, "files": outputs, "created": datetime.now(timezone.utc).isoformat(),
            "note": "Arquivos gerados. A validacao automatica nao substitui revisao visual, semantica e com leitor de tela."}


def report_spec(record: dict[str, Any], title: str, language: str = "pt-BR") -> DocumentSpec:
    """Relatorio em linguagem natural, na ordem do W3C WAI e do WCAG-EM.

    O servidor nao escreve o texto: ele organiza, em frases simples, o que o avaliador
    registrou (claim, medicao, correcao, evidencias) e o que as ferramentas mediram.
    Campo sem registro aparece como "Nao registrado", nunca inventado.
    """
    if language not in ("pt", "pt-BR", "pt-PT"):
        raise ValueError(
            "O relatorio automatico e redigido em portugues. Para outro idioma, escreva o conteudo e use "
            "a11y_create_document com o idioma correspondente."
        )
    from .report_artifacts import (
        _PRAZO,
        _PRIORITY_LABELS,
        CODE_LABELS,
        REFERENCIAS,
        SCREEN_READER_STEPS_LABEL,
        VISUAL_STEPS_LABEL,
        _short_title,
        finding_facts,
        issue_narrative,
        normalize_findings,
        occurrence_records,
        screen_groups,
    )
    from .report_context import (
        context_rows,
        criterion_result,
        missing_report_data,
        reproduction_screen_reader_sections,
        reproduction_visual_sections,
    )

    url = str(record.get("url") or "Não informado")
    findings = normalize_findings(record)
    confirmed = [f for f in findings if f.get("outcome") == "failed"]
    uncertain = [f for f in findings if f.get("outcome") == "cantTell"]
    coverage = record.get("coverage") or {}
    report_context = record.get("report_context") or {}
    product = str(report_context.get("product_name") or record.get("host") or url)
    period = str(report_context.get("evaluation_period") or record.get("evaluation_date") or "")
    if not period:
        created = str(record.get("created") or "")[:10]
        period = "/".join(reversed(created.split("-"))) if created.count("-") == 2 else "data não registrada"
    by_priority: dict[str, int] = {}
    for finding in findings:
        key = str(finding.get("priority") or "unrated")
        by_priority[key] = by_priority.get(key, 0) + 1
    by_criterion = sorted({str(f.get("criterion")) for f in findings if f.get("criterion")})
    by_principle: dict[str, list[dict[str, Any]]] = {}
    for finding in findings:
        principle = str(finding.get("principle") or wcag.principle_of(str(finding.get("criterion") or "")) or "Não identificado")
        by_principle.setdefault(principle, []).append(finding)
    worst = min((str(f.get("priority") or "unrated") for f in findings), key=lambda p: {"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(p, 4), default="unrated")
    worst_finding = next((f for f in findings if str(f.get("priority") or "unrated") == worst), None)

    blocks: list[Block] = []

    # 1. Resumo: o veredito, o tamanho do problema e a prioridade.
    blocks.append(Block(kind="heading", text="Resumo"))
    if findings:
        count = len(findings)
        severity_counts: dict[str, int] = {}
        for finding in findings:
            key = str(finding.get("severity") or "unrated").lower()
            severity_counts[key] = severity_counts.get(key, 0) + 1
        severity_bits = []
        for key, label in (("blocker", "bloqueante"), ("serious", "sério"), ("moderate", "moderado"), ("minor", "leve")):
            total = severity_counts.get(key, 0)
            if total:
                severity_bits.append(f"{total} {'é' if total == 1 else 'são'} {label}{'' if total == 1 else 's'}")
        verdict = ""
        if confirmed and uncertain:
            verdict = (
                f"A avaliação de {url}, feita em {period}, encontrou {count} problemas de acessibilidade: "
                f"{len(confirmed)} confirmados e {len(uncertain)} que ainda precisam de confirmação antes de "
                "serem tratados como falha."
            )
        elif confirmed:
            verdict = (
                f"A avaliação de {url}, feita em {period}, encontrou {count} "
                f"{'problema confirmado' if count == 1 else 'problemas confirmados'} de acessibilidade."
            )
        else:
            verdict = (
                f"A avaliação de {url}, feita em {period}, registrou {count} "
                f"{'problema' if count == 1 else 'problemas'} de acessibilidade que ainda "
                f"{'precisa' if count == 1 else 'precisam'} de confirmação antes de "
                f"{'ser tratado' if count == 1 else 'serem tratados'} como falha. "
                f"{'Nenhum foi confirmado' if count == 1 else 'Nenhum deles foi confirmado'} nesta execução."
            )
        if severity_bits:
            verdict += " " + ", ".join(severity_bits[:-1]) + (" e " if len(severity_bits) > 1 else "") + severity_bits[-1] + "."
        blocks.append(Block(kind="paragraph", text=verdict))
        if worst_finding:
            number = str(worst_finding.get("criterion") or "")
            criterion = f" (critério {number}, {wcag.name_pt_of(number)})" if number else ""
            claim = _short_title(str(worst_finding.get("claim") or "Descrição não informada"), 140)
            if len(claim) > 1 and claim[1].islower():
                claim = claim[0].lower() + claim[1:]
            blocks.append(Block(kind="paragraph", text=(
                f"O de prioridade mais alta é o achado {str(worst_finding.get('id') or '').upper()}{criterion}: {claim}.")))
        priority_rows = [
            [_PRIORITY_LABELS.get(p, p), str(by_priority[p]), _PRAZO.get(p, "")]
            for p in ("P0", "P1", "P2", "P3") if by_priority.get(p)
        ]
        if by_priority.get("unrated"):
            priority_rows.append([_PRIORITY_LABELS["unrated"], str(by_priority["unrated"]), _PRAZO["unrated"]])
        if priority_rows:
            blocks.append(Block(kind="table", text="Problemas por prioridade", headers=["Prioridade", "Quantidade", "Prazo"], rows=priority_rows))
    else:
        blocks.append(Block(kind="paragraph", text=(
            f"As verificações feitas em {period} não registraram barreiras em {product}. Isso não comprova conformidade: "
            "os critérios que não foram testados continuam não avaliados, e a ausência de achado não aprova nenhum deles.")))

    missing = missing_report_data(record)
    if missing:
        blocks.append(Block(kind="paragraph", text=(
            "Há dados que o avaliador não registrou, listados abaixo. A lista verifica a presença dos campos; "
            "não julga a qualidade das evidências nem a conclusão da auditoria.")))
        blocks.append(Block(kind="table", text="Dados não registrados para revisão", headers=["Onde", "Informação ausente"], rows=missing))
    else:
        blocks.append(Block(kind="paragraph", text=(
            "Os campos documentais estão preenchidos. A suficiência das evidências e as conclusões continuam "
            "dependendo de revisão de quem avaliou.")))

    # 2. O que ja esta certo: so o que a execucao prova.
    probes = [str(item) for item in (coverage.get("probes_run") or [])]
    stresses = [str(item) for item in (coverage.get("stress_run") or [])]
    positive_results = [item for item in report_context.get("criteria", [])
                        if item.get("outcome") == "passed" and item.get("complete") and item.get("evidence")
                        and not any(str(f.get("criterion")) == item.get("criterion") for f in findings)]
    blocks.append(Block(kind="heading", text="O que já está certo"))
    if positive_results:
        blocks.append(Block(kind="paragraph", text=(
            "Aprovações declaradas pelo avaliador com cobertura completa no escopo indicado. "
            "Preserve estes resultados nas correções.")))
        blocks.append(Block(kind="list", items=[
            f"{item['criterion']} — {item['remarks']}. Escopo: {item['scope']}." for item in positive_results
        ]))
    else:
        blocks.append(Block(kind="paragraph", text=(
            "Nenhuma aprovação com cobertura completa e evidência foi registrada. "
            "Executar uma sonda ou não registrar achados não comprova aprovação.")))

    # 4. Como a avaliacao foi feita: so o que rodou de fato.
    blocks.append(Block(kind="heading", text="Como a avaliação foi feita"))
    method_items: list[str] = []
    if coverage.get("page_map"):
        method_items.append(
            "Leitura da estrutura: títulos, marcos, listas, formulários, imagens e links foram lidos elemento por "
            "elemento, como o leitor de tela os recebe — não apenas o que aparece na tela.")
    if "tab_walk" in probes:
        method_items.append(
            "Navegação por teclado: foi percorrida a amostra de paradas registrada com a tecla Tab, observando onde o foco "
            "para, se ele fica visível e se fica coberto por outro elemento.")
    if "target_size" in probes:
        method_items.append(
            "Tamanho de alvo: a área clicável de cada elemento interativo foi medida em pixels, junto com a distância "
            "até o vizinho mais próximo.")
    if "reflow_320" in stresses:
        method_items.append(
            "Reorganização: a página foi reduzida a 320 pixels de largura para ver se o conteúdo se adapta sem rolagem lateral.")
    if "text_spacing" in stresses:
        method_items.append(
            "Espaçamento de texto: o espaçamento foi aumentado para ver se o texto continua legível e sem cortes.")
    tools = str(report_context.get("evaluation_tools") or "")
    if tools:
        method_items.append(f"Ferramentas de verificação: {tools}.")
    if method_items:
        blocks.append(Block(kind="list", items=method_items))
        blocks.append(Block(kind="paragraph", text=(
            "As medições registradas descrevem o escopo executado. Revisão manual e testes com tecnologia assistiva "
            "só estão comprovados quando documentados com suas próprias evidências.")))
    else:
        blocks.append(Block(kind="paragraph", text=(
            "O método executado não foi registrado nesta execução: não é possível afirmar quais testes rodaram.")))
    interactive = coverage.get("interactive") or {}
    if coverage:
        probed = interactive.get("probed_by_behavior", "não registrado")
        probed_text = "nenhum foi sondado por comportamento" if probed in (0, "0") else f"{probed} foram sondados por comportamento"
        blocks.append(Block(kind="paragraph", text=(
            f"Nesta execução, {interactive.get('discovered', 'não registrado')} elementos interativos foram descobertos, "
            f"{interactive.get('listed', 'não registrado')} foram listados e {probed_text}; ao todo, "
            f"{coverage.get('actions_taken', 'não registrado')} ações foram realizadas.")))

    # 5. Problemas encontrados, agrupados pelos quatro principios.
    blocks.append(Block(kind="heading", text="Problemas encontrados"))
    if not findings:
        blocks.append(Block(kind="paragraph", text=(
            "Nenhum problema foi registrado nesta execução. Nenhum critério foi aprovado por ausência de achado.")))
    else:
        blocks.append(Block(kind="paragraph", text=(
            f"Os {len(findings)} achados estão agrupados por tela testada, na mesma ordem das abas da planilha. Cada ficha traz o "
            "critério, a prioridade, o lugar exato na página, a medição, os passos para quem enxerga e para quem usa leitor de tela, "
            "o código problemático, a correção recomendada e o código corrigido sugerido.")))
        for screen_name, screen_description, screen_findings, screen_items in screen_groups(record, occurrence_records(findings)):
            blocks.append(Block(kind="heading", level=3, text=screen_name))
            if screen_description:
                blocks.append(Block(kind="paragraph", text=screen_description))
            if not screen_findings:
                if screen_items:
                    blocks.append(Block(kind="table", text=f"Tela testada: {screen_name}", headers=["Item", "Detalhe"],
                                        rows=[[entry["item"], entry["detail"]] for entry in screen_items]))
                else:
                    blocks.append(Block(kind="paragraph", text="Tela sem achados registrados."))
                continue
            ordered_occurrences = sorted(screen_findings, key=lambda f: ({"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(str(f.get("priority") or "unrated"), 4),
                                                                         str(f.get("criterion") or "")))
            for occurrence in ordered_occurrences:
                identifier = str(occurrence.get("id") or "").upper()
                number = str(occurrence.get("criterion") or "")
                title_text = _short_title(str(occurrence.get("claim") or "Descrição não informada"), 120)
                blocks.append(Block(kind="heading", level=4, text=f"{identifier} · {title_text}"))
                blocks.append(Block(kind="table", text=f"Ficha do achado {identifier}",
                                    headers=["Campo", "Valor"], rows=finding_facts(occurrence)))
                details = occurrence.get("report_details") or {}
                for label, body in issue_narrative(occurrence):
                    if label in (VISUAL_STEPS_LABEL, SCREEN_READER_STEPS_LABEL):
                        blocks.append(Block(kind="paragraph", text=f"{label}."))
                        sections = (reproduction_visual_sections(details) if label == VISUAL_STEPS_LABEL
                                    else reproduction_screen_reader_sections(details))
                        if not sections:
                            blocks.append(Block(kind="paragraph", text=body))
                        for note, steps in sections:
                            if note:
                                blocks.append(Block(kind="paragraph", text=note))
                            blocks.append(Block(kind="list", ordered=True, items=steps))
                    elif label in CODE_LABELS:
                        blocks.append(Block(kind="paragraph", text=f"{label}."))
                        blocks.append(Block(kind="table", text=label, headers=["Código"],
                                            rows=[[line] for line in body.splitlines() if line.strip()]))
                    else:
                        blocks.append(Block(kind="paragraph", text=f"{label}. {body}."))
                if number:
                    blocks.append(Block(kind="paragraph", text=(
                        f"Referência do critério: {number} — {wcag.name_pt_of(number)} — {wcag.url_of(number)}")))

    # 6. Tabela de conformidade: todos os criterios A/AA, sem transformar ausencia em aprovacao.
    blocks.append(Block(kind="heading", text="Tabela de conformidade com a WCAG 2.2"))
    blocks.append(Block(kind="paragraph", text=(
        "A tabela abaixo cobre todos os critérios de nível A e AA da WCAG 2.2. \"Não avaliado\" não significa aprovado: "
        "significa que aquele ponto não foi testado nesta execução. A tabela não é uma declaração de conformidade do produto.")))
    declaration_rows = []
    matrix_numbers = {n for n in wcag.CRITERIA if wcag.level_of(n) in ("A", "AA")} | set(by_criterion)
    matrix_numbers.update(item["criterion"] for item in (record.get("report_context") or {}).get("criteria", []))
    for number in sorted(matrix_numbers, key=lambda n: tuple(int(p) for p in n.split("."))):
        declaration_rows.append([
            f"{number} — {wcag.name_pt_of(number) or 'critério'}", wcag.level_of(number) or "—",
            *criterion_result(record, number, findings),
        ])
    if declaration_rows:
        for start in range(0, len(declaration_rows), 12):
            blocks.append(Block(kind="table", text=f"Tabela de conformidade com a WCAG 2.2 — parte {start // 12 + 1}",
                                headers=["Critério", "Nível", "Resultado", "Base do resultado"],
                                rows=declaration_rows[start:start + 12]))
    blocks.append(Block(kind="paragraph", text=(
        "Critérios sem resultado registrado permanecem não avaliados. Aprovação e inaplicabilidade exigem escopo, "
        "justificativa, evidência e cobertura completa declarados pelo avaliador. A matriz não equivale a uma "
        "declaração de conformidade do produto.")))

    # 7. O que corrigir primeiro e como confirmar.
    if findings:
        ordered = sorted(findings, key=lambda f: ({"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(str(f.get("priority") or "unrated"), 4),
                                                   str(f.get("criterion") or "")))
        blocks.append(Block(kind="heading", text="O que corrigir primeiro"))
        blocks.append(Block(kind="paragraph", text=(
            "A ordem abaixo prioriza o impacto nas pessoas, não a facilidade da correção. Corrigir um item de "
            "prioridade alta primeiro evita que quem usa tecnologia assistiva continue bloqueado.")))
        blocks.append(Block(kind="list", ordered=True, items=[
            f"{_PRIORITY_LABELS.get(str(f.get('priority') or 'unrated'), 'A definir')} — "
            f"{str(f.get('recommendation') or 'correção não registrada')[:180]} "
            f"(achado {str(f.get('id') or '').upper()}, critério {f.get('criterion') or 'não identificado'})"
            for f in ordered
        ]))
        blocks.append(Block(kind="heading", text="Como confirmar que foi corrigido"))
        blocks.append(Block(kind="paragraph", text=(
            "A correção está confirmada quando a medição descrita em \"O que foi medido\" passa a atender ao critério "
            "citado — não quando o código muda. Repita o mesmo teste, no mesmo ambiente, e compare com o resultado anterior.")))
        retest_items = []
        for f in ordered:
            details = f.get("report_details") or {}
            method = " ".join(str(details.get("testing_method") or "").split())
            if not method:
                continue
            number = str(f.get("criterion") or "")
            retest_items.append(
                f"{str(f.get('id') or '').upper()} — repita o teste: {method}; o resultado deve atender ao critério "
                f"{number} — {wcag.name_pt_of(number)}.")
        if retest_items:
            blocks.append(Block(kind="list", items=retest_items))

    # 8. Limites: o que este relatorio nao prova.
    blocks.append(Block(kind="heading", text="Limites desta avaliação"))
    limits = [
        "O servidor mede fatos; não substitui teste com pessoas com deficiência nem com leitor de tela real (NVDA, JAWS, VoiceOver).",
        "Verificação automatizada cobre apenas parte dos critérios; os itens não medidos permanecem não avaliados.",
        "O conteúdo pode mudar depois da data da avaliação; o resultado vale para o estado observado.",
        "Um resultado sem achados não é declaração de conformidade.",
    ]
    gaps = [str(gap) for gap in (coverage.get("gaps") or [])]
    if gaps:
        limits.append("Lacunas registradas nesta execução: " + "; ".join(gaps) + ".")
    blocks.append(Block(kind="list", items=limits))
    monitoring = str(report_context.get("monitoring_plan") or "")
    if monitoring:
        blocks.append(Block(kind="heading", text="Acompanhamento e novas avaliações"))
        blocks.append(Block(kind="paragraph", text=monitoring))

    # 9. Ficha tecnica: quem avaliou, com o que e quando.
    blocks.append(Block(kind="heading", text="Ficha técnica"))
    metadata = dict(context_rows(record))
    result_text = (
        f"Não conforme com o nível AA da WCAG 2.2 nesta data ({len(findings)} {'achado' if len(findings) == 1 else 'achados'})"
        if findings else "Nenhum problema registrado nesta execução; isso não é declaração de conformidade"
    )
    ficha_rows = [
        ["Produto avaliado", product],
        ["Endereço", url],
        ["Padrão de referência", str(report_context.get("conformance_target") or "WCAG 2.2, níveis A e AA")],
        ["Data da avaliação", period],
        ["Versão do relatório", metadata.get("Versão do relatório", "Não registrado")],
        ["Avaliador", metadata.get("Avaliador", "Não registrado")],
        ["Organização responsável", metadata.get("Organização do avaliador", "Não registrado")],
        ["Contato", metadata.get("Contato do avaliador", "Não registrado")],
        ["Especialidade do avaliador", metadata.get("Especialidade do avaliador", "Não registrado")],
        ["Idiomas dos avaliadores", metadata.get("Idiomas dos avaliadores", "Não registrado")],
        ["Idioma do conteúdo", metadata.get("Idiomas do produto", "Não registrado")],
        ["Ambiente", str(report_context.get("environment") or coverage.get("browser") or "Não registrado")],
        ["Ferramentas e versões", str(report_context.get("evaluation_tools") or "Não registrado")],
        ["Resultado", result_text],
    ]
    blocks.append(Block(kind="table", text="Dados da avaliação", headers=["Campo", "Registro"], rows=ficha_rows))

    # 10. Referencias e anexos.
    blocks.append(Block(kind="heading", text="Referências"))
    blocks.append(Block(kind="list", items=[f"{name}: {link}" for name, link in REFERENCIAS]))
    return DocumentSpec(title=title, language=language, author=str(report_context.get("evaluator") or ""),
                        toc=True, subject="Avaliação de acessibilidade WCAG 2.2", blocks=blocks)
