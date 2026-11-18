"""Controles e navegacao Word: estrutura nativa, sem macros ou dependencia de Word."""
from __future__ import annotations

from typing import Any

from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from .document_schema import Block


def element(parent: Any, tag: str, **attrs: str) -> Any:
    child = OxmlElement(tag)
    for name, value in attrs.items():
        child.set(qn(name), value)
    parent.append(child)
    return child


def destinations(blocks: list[Block]) -> list[tuple[Block, str]]:
    used = {block.id for block in blocks if block.id}
    entries = []
    for index, block in enumerate(blocks, 1):
        if block.kind != "heading":
            continue
        ident = block.id or f"sec_{index}"
        while not block.id and ident in used:
            ident += "x"
        used.add(ident)
        entries.append((block, ident))
    return entries


def bookmark(paragraph: Any, ident: str, number: int) -> None:
    start = OxmlElement("w:bookmarkStart")
    start.set(qn("w:id"), str(number))
    start.set(qn("w:name"), ident)
    paragraph._p.insert(1 if paragraph._p.pPr is not None else 0, start)
    element(paragraph._p, "w:bookmarkEnd", **{"w:id": str(number)})


def internal_link(paragraph: Any, ident: str, text: str) -> None:
    link = element(paragraph._p, "w:hyperlink", **{"w:anchor": ident, "w:history": "1"})
    run = element(link, "w:r")
    props = element(run, "w:rPr")
    element(props, "w:color", **{"w:val": "000080"})
    element(props, "w:u", **{"w:val": "single"})
    element(run, "w:t").text = text


def table_of_contents(doc: Any, entries: list[tuple[Block, str]], portuguese: bool) -> None:
    style = doc.styles.add_style("MCP Contents Heading", WD_STYLE_TYPE.PARAGRAPH)
    style.base_style = doc.styles["Heading 2"]
    element(style.element.get_or_add_pPr(), "w:outlineLvl", **{"w:val": "9"})
    # Nivel direto torna o titulo navegavel; o estilo fora do outline impede
    # que o Word inclua o proprio Sumario ao recalcular TOC \\o, sem \\u.
    heading = doc.add_paragraph("Sumário" if portuguese else "Contents", style)
    element(heading._p.get_or_add_pPr(), "w:outlineLvl", **{"w:val": "1"})
    begin = doc.add_paragraph()
    run = element(begin._p, "w:r")
    element(run, "w:fldChar", **{"w:fldCharType": "begin", "w:dirty": "true"})
    instruction = element(element(begin._p, "w:r"), "w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = ' TOC \\o "2-6" \\h \\z '
    element(element(begin._p, "w:r"), "w:fldChar", **{"w:fldCharType": "separate"})
    for block, ident in entries:
        paragraph = doc.add_paragraph()
        internal_link(paragraph, ident, block.text)
    end = doc.add_paragraph()
    element(element(end._p, "w:r"), "w:fldChar", **{"w:fldCharType": "end"})
    # O resultado inicial ja tem links; F9 recalcula titulos e paginas apos edicoes.
    element(doc.settings.element, "w:updateFields", **{"w:val": "true"})


def field_label(block: Block, portuguese: bool) -> str:
    suffix = "obrigatório" if portuguese else "required"
    return block.text + (f" ({suffix})" if block.required else "")


def word_field(doc: Any, block: Block, number: int, portuguese: bool) -> None:
    label = field_label(block, portuguese)
    doc.add_paragraph(label)
    doc.add_paragraph(block.help_text)
    paragraph = doc.add_paragraph()
    control = element(paragraph._p, "w:sdt")
    properties = element(control, "w:sdtPr")
    element(properties, "w:alias", **{"w:val": label + ". " + block.help_text})
    element(properties, "w:tag", **{"w:val": block.field_name})
    element(properties, "w:id", **{"w:val": str(number)})
    if block.field_type == "text":
        element(properties, "w:text", **{"w:multiLine": "1" if block.multiline else "0"})
    elif block.field_type == "choice":
        choices = element(properties, "w:dropDownList")
        for option in block.options:
            element(choices, "w:listItem", **{"w:displayText": option, "w:value": option})
    else:
        checkbox = element(properties, "w14:checkbox")
        element(checkbox, "w14:checked", **{"w14:val": "1" if block.checked else "0"})
        element(checkbox, "w14:checkedState", **{"w14:val": "2612", "w14:font": "Segoe UI Symbol"})
        element(checkbox, "w14:uncheckedState", **{"w14:val": "2610", "w14:font": "Segoe UI Symbol"})
    content = element(control, "w:sdtContent")
    if block.field_type == "checkbox":
        text = "☒" if block.checked else "☐"
    else:
        text = block.value
        if not text:
            element(properties, "w:showingPlcHdr")
            text = ("Selecione uma opção" if block.field_type == "choice" else "Digite aqui") if portuguese else ("Select an option" if block.field_type == "choice" else "Enter text")
    element(element(content, "w:r"), "w:t").text = text
