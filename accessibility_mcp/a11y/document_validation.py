"""Verificacoes estruturais de arquivos; nunca certifica qualidade semantica ou WCAG."""

from __future__ import annotations

import asyncio
import os
import shutil
from collections import Counter
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import httpx
from defusedxml import ElementTree as ET
from pypdf import PdfReader

from . import verapdf_runtime

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
NS = {"w": W[1:-1], "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"}
HUMAN_REVIEW = [
    "Conferir sentido dos textos alternativos, nomes de links e hierarquia de titulos.",
    "Conferir ordem de leitura, tabelas, contraste e aparencia em todas as paginas.",
    "Percorrer o arquivo com teclado e leitor de tela no aplicativo de destino.",
]


def _result(kind: str, issues: list[dict[str, str]], facts: dict[str, Any]) -> dict[str, Any]:
    return {"format": kind, "status": "issues_found" if issues else "automated_checks_passed",
            "issues": issues, "facts": facts, "human_review_required": HUMAN_REVIEW,
            "conformance": "not_determined", "complete_validation": False}


def validate_docx(path: Path) -> dict[str, Any]:
    issues: list[dict[str, str]] = []

    def issue(code: str, location: str) -> None:
        issues.append({"code": code, "location": location})

    with ZipFile(path) as package:
        # Limite de descompressao protege o parser de arquivos hostis; nao limita uma tarefa em progresso.
        if sum(i.file_size for i in package.infolist()) > 100 * 1024 * 1024:
            raise ValueError("Pacote DOCX excede o limite de seguranca de descompressao de 100 MiB.")
        document = ET.fromstring(package.read("word/document.xml"))
        styles = ET.fromstring(package.read("word/styles.xml"))
        core = ET.fromstring(package.read("docProps/core.xml"))
        title = core.findtext("{http://purl.org/dc/elements/1.1/}title", "")
        lang = styles.find(f".//{W}docDefaults//{W}lang")
        language = lang.get(W + "val", "") if lang is not None else ""
        if not title.strip():
            issue("missing_title", "docProps/core.xml")
        if not language:
            issue("missing_language", "word/styles.xml")
        outlines: dict[str, int] = {}
        for style in styles.findall(W + "style"):
            outline = style.find(f"{W}pPr/{W}outlineLvl")
            if outline is not None:
                outlines[style.get(W + "styleId", "")] = int(outline.get(W + "val", "9")) + 1
        headings, images, tables, links = [], 0, 0, 0
        previous = 0
        for index, para in enumerate(document.findall(f".//{W}p"), 1):
            pstyle = para.find(f"{W}pPr/{W}pStyle")
            direct = para.find(f"{W}pPr/{W}outlineLvl")
            level = int(direct.get(W + "val", "9")) + 1 if direct is not None else outlines.get(pstyle.get(W + "val", "") if pstyle is not None else "", 0)
            if 0 < level <= 6:
                headings.append(level)
                if level > previous + 1:
                    issue("heading_level_skipped", f"paragrafo {index}")
                previous = level
        if not headings or headings[0] != 1:
            issue("missing_heading_one", "word/document.xml")
        for member in package.namelist():
            if not (member.startswith("word/") and member.endswith(".xml")):
                continue
            tree = ET.fromstring(package.read(member))
            for image in tree.findall(".//wp:docPr", NS):
                images += 1
                if not image.get("descr", "").strip():
                    issue("image_missing_alt", member)
            for table in tree.findall(f".//{W}tbl"):
                tables += 1
                first = table.find(W + "tr")
                if first is None or first.find(f"{W}trPr/{W}tblHeader") is None:
                    issue("table_missing_header", member)
                if table.find(f".//{W}gridSpan") is not None or table.find(f".//{W}vMerge") is not None:
                    issue("complex_table_requires_review", member)
            for link in tree.findall(f".//{W}hyperlink"):
                links += 1
                if not "".join(link.itertext()).strip():
                    issue("link_missing_text", member)
        return _result("docx", issues, {"title": title, "language": language, "heading_levels": headings,
                                       "images": images, "tables": tables, "links": links})


def validate_pdf(path: Path) -> dict[str, Any]:
    reader = PdfReader(path)
    if reader.is_encrypted:
        raise ValueError("PDF criptografado: forneca uma copia desbloqueada para avaliar a estrutura.")
    issues: list[dict[str, str]] = []

    def issue(code: str, location: str) -> None:
        issues.append({"code": code, "location": location})

    root = reader.root_object
    title = reader.metadata.title if reader.metadata is not None else ""
    if not str(title).strip():
        issue("missing_title", "catalogo")
    language = root.get("/Lang", "")
    if not language:
        issue("missing_language", "catalogo")
    marked = root.get("/MarkInfo", {}).get("/Marked", False)
    struct = root.get("/StructTreeRoot")
    if not marked or struct is None:
        issue("missing_tags", "catalogo")
    tags: Counter[str] = Counter()
    headings: list[int] = []
    seen: set[int] = set()

    def walk(node: Any) -> None:
        if hasattr(node, "get_object"):
            node = node.get_object()
        if isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, dict) and id(node) not in seen:
            seen.add(id(node))
            role = str(node.get("/S", ""))
            if role:
                tags[role] += 1
            if role in ("/H1", "/H2", "/H3", "/H4", "/H5", "/H6"):
                level = int(role[-1])
                if level > (headings[-1] if headings else 0) + 1:
                    issue("heading_level_skipped", role)
                headings.append(level)
            if role == "/Figure" and not str(node.get("/Alt", "")).strip():
                issue("image_missing_alt", "Figure")
            if "/K" in node:
                walk(node["/K"])

    if struct is not None:
        walk(struct)
        if not tags:
            issue("empty_tag_tree", "StructTreeRoot")
    if not headings or headings[0] != 1:
        issue("missing_heading_one", "StructTreeRoot")
    if tags["/Table"] and not tags["/TH"]:
        issue("table_missing_header", "StructTreeRoot")
    for index, page in enumerate(reader.pages, 1):
        location = f"pagina {index}"
        if not (page.extract_text() or "").strip():
            issue("page_without_extractable_text", location)
        for font_ref in page.get("/Resources", {}).get("/Font", {}).values():
            font = font_ref.get_object()
            descendants = font.get("/DescendantFonts", [])
            for entry in descendants or [font]:
                f = entry.get_object()
                descriptor = f.get("/FontDescriptor")
                descriptor = descriptor.get_object() if descriptor is not None else {}
                if not any(key in descriptor for key in ("/FontFile", "/FontFile2", "/FontFile3")):
                    issue("font_not_embedded", location)
            if font.get("/Subtype") == "/Type0" and "/ToUnicode" not in font:
                issue("font_missing_unicode_map", location)
        for annotation in page.get("/Annots", []):
            annot = annotation.get_object()
            if annot.get("/Subtype") == "/Link" and "/StructParent" not in annot:
                issue("link_not_tagged", location)
    return _result("pdf", issues, {"title": str(title), "language": str(language), "pages": len(reader.pages),
                                  "marked": bool(marked), "tags": dict(tags), "heading_levels": headings})


async def verapdf(path: Path, profile: str = "ua1") -> dict[str, Any]:
    """Validador normativo externo; a ausencia nunca vira aprovacao."""
    executable = os.environ.get("A11Y_MCP_VERAPDF", "") or shutil.which("verapdf")
    if not executable:
        try:
            cached = await verapdf_runtime.ensure()
            executable = str(cached) if cached is not None else None
        except (OSError, ValueError, RuntimeError, httpx.HTTPError) as e:
            return {"status": "not_run", "reason": f"Nao foi possivel preparar o veraPDF: {e}"}
    if not executable:
        return {"status": "not_run", "reason": "veraPDF indisponivel: confira Java no PATH e A11Y_MCP_AUTO_INSTALL; verificacoes PDF/UA normativas pendentes."}
    if profile not in ("ua1", "ua2"):
        raise ValueError("O perfil deve ser ua1 ou ua2.")
    if Path(executable).suffix.lower() in (".bat", ".cmd"):
        jars = sorted((Path(executable).parent / "bin").glob("cli-*.jar"))
        if not jars:
            return {"status": "not_run", "reason": "Use A11Y_MCP_VERAPDF com o JAR executavel do veraPDF, sem shell."}
        executable = str(jars[-1])
    command = [executable]
    if Path(executable).suffix.lower() == ".jar":
        java = shutil.which("java")
        if not java:
            return {"status": "not_run", "reason": "Java nao encontrado para executar o veraPDF."}
        command = [java, "-jar", executable]
    process = await asyncio.create_subprocess_exec(*command, "--format", "xml", "--flavour", profile, str(path),
                                                   stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        stdout, _ = await process.communicate()
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()
    try:
        report = ET.fromstring(stdout)
        validations = [e for e in report.iter() if e.tag.rsplit("}", 1)[-1] == "validationReport"]
        if not validations:
            raise ValueError("Sem validationReport.")
        passed = all(e.get("isCompliant") == "true" for e in validations)
        status = "passed" if passed and process.returncode == 0 else "error" if passed else "failed"
        return {"status": status,
                "profile": profile, "exit_code": process.returncode, "report": stdout.decode("utf-8", errors="replace")}
    except (ValueError, ET.ParseError):
        return {"status": "error", "profile": profile, "exit_code": process.returncode,
                "reason": "veraPDF nao devolveu um relatorio de validacao reconhecido."}


async def validate(path: Path, external: bool = True) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return validate_docx(path)
    if suffix != ".pdf":
        raise ValueError("Formato aceito: DOCX ou PDF.")
    result = validate_pdf(path)
    result["pdf_ua"] = await verapdf(path) if external else {"status": "not_run", "reason": "Nao solicitado."}
    if result["pdf_ua"]["status"] in ("failed", "error"):
        result["status"] = "issues_found"
    elif external and result["pdf_ua"]["status"] == "not_run" and not result["issues"]:
        result["status"] = "partial"
    return result
