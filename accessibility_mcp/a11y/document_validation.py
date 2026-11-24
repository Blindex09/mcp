"""Verificacoes estruturais de arquivos; nunca certifica qualidade semantica ou WCAG."""

from __future__ import annotations

import asyncio
import bisect
import os
import re
import shutil
from collections import Counter
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import httpx
from defusedxml import ElementTree as ET
from pypdf import PdfReader
from pypdf.generic import ContentStream

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
        bookmarks = {node.get(W + "name", "") for node in document.findall(f".//{W}bookmarkStart")}
        controls: list[dict[str, Any]] = []
        field_names: set[str] = set()
        for node in document.findall(f".//{W}sdt"):
            properties = node.find(W + "sdtPr")
            if properties is None:
                issue("form_missing_properties", "controle Word")
                continue
            alias = properties.find(W + "alias")
            label = alias.get(W + "val", "") if alias is not None else ""
            tag = properties.find(W + "tag")
            name = tag.get(W + "val", "") if tag is not None else ""
            kind = next((kind for kind in ("text", "dropDownList", "comboBox", "checkbox") if any(child.tag.rsplit("}",1)[-1] == kind for child in properties)), "other")
            if kind == "other":
                continue  # SDT tambem pode conter sumario e outros conteudos, sem ser campo.
            if not label.strip():
                issue("form_missing_label", name or "controle Word")
            if not name or name in field_names:
                issue("form_name_missing_or_duplicate", name or "controle Word")
            field_names.add(name)
            content = node.find(W + "sdtContent")
            value = "".join(content.itertext()) if content is not None and properties.find(W + "showingPlcHdr") is None else ""
            checkbox = next((child for child in properties if child.tag.rsplit("}",1)[-1] == "checkbox"), None)
            checked = None
            if checkbox is not None:
                state = next((child for child in checkbox if child.tag.rsplit("}",1)[-1] == "checked"), None)
                checked = any(val in ("1", "true", "on") for val in state.attrib.values()) if state is not None else False
            controls.append({"name": name, "label": label, "type": kind, "value": value, "checked": checked})
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
                target = link.get(W + "anchor")
                if target and target not in bookmarks:
                    issue("broken_internal_link", target)
        toc = any((node.text or "").strip().split()[:1] == ["TOC"] for node in document.findall(f".//{W}instrText"))
        return _result("docx", issues, {"title": title, "language": language, "heading_levels": headings,
                                       "images": images, "tables": tables, "links": links, "fields": controls,
                                       "toc_field": toc, "bookmarks": len(bookmarks)})


_PDF17_STANDARD_ROLES = frozenset(
    [
        "Document", "Part", "Art", "Sect", "Div", "BlockQuote", "Caption", "TOC", "TOCI", "Index",
        "NonStruct", "Private", "P", "H", "H1", "H2", "H3", "H4", "H5", "H6", "L", "LI", "Lbl",
        "LBody", "Table", "TR", "TH", "TD", "THead", "TBody", "TFoot", "Span", "Quote", "Note",
        "Reference", "BibEntry", "Code", "Link", "Annot", "Ruby", "RB", "RT", "RP", "Warichu",
        "WT", "WP", "Figure", "Formula", "Form",
    ]
)
_ROW_GROUPS = frozenset({"THead", "TBody", "TFoot"})
_TEXT_SHOW_OPS = frozenset({b"Tj", b"TJ", b"'", b'"'})


def _deref(obj: Any) -> Any:
    return obj.get_object() if hasattr(obj, "get_object") else obj


def _pdf_bool(obj: Any, default: bool = False) -> bool:
    """Converte BooleanObject/bool de PDF com seguranca (bool(BooleanObject(False)) e' True em pypdf)."""
    val = _deref(obj)
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    inner = getattr(val, "value", None)
    if isinstance(inner, bool):
        return inner
    return str(val).strip().lower() == "true"


def _ref_key(obj: Any) -> tuple[int, int] | None:
    indirect = obj if hasattr(obj, "idnum") else getattr(obj, "indirect_reference", None)
    if indirect is not None:
        return (int(indirect.idnum), int(indirect.generation))
    return None


def _read_role_map(struct_root: Any) -> dict[str, str]:
    st = _deref(struct_root)
    if not isinstance(st, dict):
        return {}
    rm = _deref(st.get("/RoleMap"))
    if not isinstance(rm, dict):
        return {}
    return {str(k).lstrip("/"): str(_deref(v)).lstrip("/") for k, v in rm.items()}


def _is_circular_role_mapping(start: str, role_map: dict[str, str]) -> bool:
    seen = {start}
    cur = start
    while cur in role_map:
        nxt = role_map[cur]
        if nxt in seen:
            return True
        seen.add(nxt)
        cur = nxt
    return False


def _resolve_role(role: str, role_map: dict[str, str]) -> tuple[str, bool]:
    raw = role.lstrip("/")
    if not raw:
        return "", False
    seen = {raw}
    cur = raw
    while cur not in _PDF17_STANDARD_ROLES and cur in role_map:
        nxt = role_map[cur]
        if nxt in seen:
            return raw, True
        seen.add(nxt)
        cur = nxt
    return cur, False


def _table_attr(node: dict[str, Any], key: str) -> Any:
    raw = _deref(node.get("/A"))
    items = raw if isinstance(raw, list) else ([raw] if raw is not None else [])
    for item in items:
        d = _deref(item)
        if not isinstance(d, dict):
            continue
        owner = str(_deref(d.get("/O", ""))).lstrip("/")
        if owner in ("", "Table") and key in d:
            return _deref(d[key])
    return None


def _pos_int(value: Any, default: int = 1) -> int:
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default


def _table_row_widths(table_node: dict[str, Any], role_map: dict[str, str]) -> list[int]:
    """Calcula colunas ocupadas por cada TR na grade (considerando ColSpan e RowSpan), sem cruzar sub-tabelas."""

    def iter_rows(parent: dict[str, Any]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        kids = _deref(parent.get("/K"))
        seq = kids if isinstance(kids, list) else ([kids] if kids is not None else [])
        for kid in seq:
            d = _deref(kid)
            if not isinstance(d, dict) or "/S" not in d:
                continue
            r, _ = _resolve_role(str(d["/S"]), role_map)
            if r == "TR":
                rows.append(d)
            elif r in _ROW_GROUPS or r == "NonStruct":
                rows.extend(iter_rows(d))
        return rows

    def iter_cells(tr_node: dict[str, Any]) -> list[dict[str, Any]]:
        cells: list[dict[str, Any]] = []
        kids = _deref(tr_node.get("/K"))
        seq = kids if isinstance(kids, list) else ([kids] if kids is not None else [])
        for kid in seq:
            d = _deref(kid)
            if not isinstance(d, dict) or "/S" not in d:
                continue
            r, _ = _resolve_role(str(d["/S"]), role_map)
            if r in ("TH", "TD"):
                cells.append(d)
            elif r == "NonStruct":
                cells.extend(iter_cells(d))
        return cells

    widths: list[int] = []
    carry: dict[int, int] = {}
    for tr in iter_rows(table_node):
        col = 0
        occupied = 0
        for cell in iter_cells(tr):
            while carry.get(col, 0) > 0:
                col += 1
                occupied += 1
            colspan = _pos_int(_table_attr(cell, "/ColSpan"))
            rowspan = _pos_int(_table_attr(cell, "/RowSpan"))
            if rowspan > 1:
                for k in range(col, col + colspan):
                    carry[k] = rowspan
            col += colspan
            occupied += colspan
        for k in list(carry):
            carry[k] -= 1
            if carry[k] <= 0:
                del carry[k]
        widths.append(occupied + sum(1 for k, v in carry.items() if k >= col and v > 0))
    return widths


def _lis_length(seq: list[int]) -> int:
    tails: list[int] = []
    for v in seq:
        idx = bisect.bisect_left(tails, v)
        if idx == len(tails):
            tails.append(v)
        else:
            tails[idx] = v
    return len(tails)


def _has_text_payload(operator: bytes, operands: list[Any]) -> bool:
    if not operands:
        return False
    if operator == b"TJ":
        arr = operands[0]
        if not isinstance(arr, list):
            return False
        for item in arr:
            if isinstance(item, (str, bytes)):
                s = item if isinstance(item, str) else item.decode("latin-1", errors="ignore")
                if s.strip(" \t\r\n"):
                    return True
        return False
    val = operands[2] if operator == b'"' and len(operands) >= 3 else operands[0]
    if isinstance(val, (str, bytes)):
        s = val if isinstance(val, str) else val.decode("latin-1", errors="ignore")
        return bool(s.strip(" \t\r\n"))
    return False


def _tounicode_has_noncharacter(raw: str) -> bool:
    """Detecta mapeamentos explicitos para U+0000, U+FEFF ou U+FFFE em tabelas ToUnicode."""
    bad = {"0000", "FEFF", "FFFE"}
    for block in re.findall(r"beginbfchar\s*(.*?)\s*endbfchar", raw, re.DOTALL):
        for _, dst in re.findall(r"<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>", block):
            if dst.upper() in bad:
                return True
    for block in re.findall(r"beginbfrange\s*(.*?)\s*endbfrange", raw, re.DOTALL):
        for lo, hi, dst in re.findall(r"<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>", block):
            dval = int(dst, 16)
            span = max(0, int(hi, 16) - int(lo, 16))
            for offset in range(min(span + 1, 256)):
                if (dval + offset) in (0, 0xFEFF, 0xFFFE):
                    return True
        for _, _, arr in re.findall(r"<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>\s*\[([^\]]+)\]", block, re.DOTALL):
            for dst in re.findall(r"<([0-9a-fA-F]+)>", arr):
                if dst.upper() in bad:
                    return True
    return False


def _xmp_title(root: Any) -> str:
    """Extrai dc:title do pacote XMP somente quando /Info /Title nao foi definido."""
    meta = _deref(root.get("/Metadata"))
    if meta is None or not hasattr(meta, "get_data"):
        return ""
    try:
        raw = meta.get_data().decode("utf-8", errors="replace")
        tree = ET.fromstring(raw)
    except Exception:  # noqa: BLE001 - XMP ausente ou invalido
        return ""
    node = tree.find(".//{http://purl.org/dc/elements/1.1/}title")
    if node is None:
        return ""
    return " ".join("".join(node.itertext()).split())


def validate_pdf(path: Path) -> dict[str, Any]:
    reader = PdfReader(path)
    if reader.is_encrypted:
        raise ValueError("PDF criptografado: forneca uma copia desbloqueada para avaliar a estrutura.")
    issues: list[dict[str, str]] = []
    seen_issues: set[tuple[str, str]] = set()

    def issue(code: str, location: str) -> None:
        key = (code, location)
        if key not in seen_issues:
            seen_issues.add(key)
            issues.append({"code": code, "location": location})

    root = reader.root_object
    has_info_title = reader.metadata is not None and "/Title" in reader.metadata
    title = (reader.metadata.title or "") if reader.metadata is not None else ""
    if not has_info_title and not str(title).strip():
        title = _xmp_title(root)
    if not str(title).strip():
        issue("missing_title", "catalogo")
    language = root.get("/Lang", "")
    if not language:
        issue("missing_language", "catalogo")
    mark_info = _deref(root.get("/MarkInfo"))
    mark_dict = mark_info if isinstance(mark_info, dict) else {}
    marked = _pdf_bool(mark_dict.get("/Marked"), default=False)
    suspects = _pdf_bool(mark_dict.get("/Suspects"), default=False)
    if suspects:
        issue("structure_marked_suspect", "catalogo")
    vp_obj = _deref(root.get("/ViewerPreferences"))
    display_doc_title = _pdf_bool(vp_obj.get("/DisplayDocTitle"), default=False) if isinstance(vp_obj, dict) else False
    if not display_doc_title:
        issue("display_doc_title_missing", "catalogo")
    struct = root.get("/StructTreeRoot")
    if not marked or struct is None:
        issue("missing_tags", "catalogo")

    role_map = _read_role_map(struct) if struct is not None else {}
    for k, v in role_map.items():
        if k in _PDF17_STANDARD_ROLES and v != k:
            issue("role_map_remaps_standard", f"/{k}->/{v}")
        if _is_circular_role_mapping(k, role_map):
            issue("role_map_circular", f"/{k}")

    page_num_by_ref = {
        page_key: idx for idx, pg in enumerate(reader.pages, 1) if (page_key := _ref_key(pg)) is not None
    }
    tags: Counter[str] = Counter()
    headings: list[int] = []
    seen_nodes: set[int] = set()
    logical_mcids: dict[int, list[int]] = {}
    mc_owners: dict[tuple[int | None, tuple[int, int] | None, int], list[int]] = {}
    tables_count = 0
    irregular_tables = 0
    th_count = 0
    th_scoped = 0

    def walk(node: Any, page_num: int | None = None, owner_id: int | None = None) -> None:
        nonlocal tables_count, irregular_tables, th_count, th_scoped
        node_obj = _deref(node)
        if isinstance(node_obj, list):
            for child in node_obj:
                walk(child, page_num, owner_id)
            return
        if isinstance(node_obj, int):
            if page_num is not None and owner_id is not None:
                logical_mcids.setdefault(page_num, []).append(int(node_obj))
                mc_owners.setdefault((page_num, None, int(node_obj)), []).append(owner_id)
            return
        if not isinstance(node_obj, dict):
            return
        if node_obj.get("/Type") == "/MCR" and "/MCID" in node_obj:
            mcr_pg = _ref_key(node_obj.get("/Pg"))
            pnum = page_num_by_ref.get(mcr_pg, page_num) if mcr_pg else page_num
            stm_key = _ref_key(node_obj.get("/Stm")) if "/Stm" in node_obj else None
            try:
                mcid = int(node_obj["/MCID"])
            except (TypeError, ValueError):
                return
            if owner_id is not None:
                mc_owners.setdefault((pnum, stm_key, mcid), []).append(owner_id)
            if pnum is not None and stm_key is None:
                logical_mcids.setdefault(pnum, []).append(mcid)
            return
        nid = id(node_obj)
        if nid in seen_nodes:
            return
        seen_nodes.add(nid)
        cur_pg = _ref_key(node_obj.get("/Pg"))
        cur_page = page_num_by_ref.get(cur_pg, page_num) if cur_pg else page_num
        raw_role = str(node_obj.get("/S", ""))
        cur_owner = owner_id
        if raw_role:
            cur_owner = nid
            tags[raw_role] += 1
            resolved, circular = _resolve_role(raw_role, role_map)
            if not circular and resolved not in _PDF17_STANDARD_ROLES:
                issue("role_map_unmapped_custom", raw_role)
            effective = f"/{resolved}" if resolved else raw_role
            if effective in ("/H1", "/H2", "/H3", "/H4", "/H5", "/H6"):
                level = int(effective[-1])
                if level > (headings[-1] if headings else 0) + 1:
                    issue("heading_level_skipped", raw_role)
                headings.append(level)
            if effective == "/Figure" and not str(node_obj.get("/Alt", "")).strip():
                issue("image_missing_alt", "Figure")
            if effective == "/TH":
                th_count += 1
                if _table_attr(node_obj, "/Scope") is not None or _table_attr(node_obj, "/Headers") is not None:
                    th_scoped += 1
            if effective == "/Table":
                tables_count += 1
                widths = _table_row_widths(node_obj, role_map)
                if len(widths) >= 2 and len(set(widths)) > 1:
                    irregular_tables += 1
                    issue("table_irregular_grid", "Table")
        if "/K" in node_obj:
            walk(node_obj["/K"], cur_page, cur_owner)

    if struct is not None:
        walk(struct)
        if not tags:
            issue("empty_tag_tree", "StructTreeRoot")
        for (pg_n, _stm, mcid), owners in mc_owners.items():
            if len(set(owners)) > 1:
                loc = f"pagina {pg_n} MCID {mcid}" if pg_n is not None else f"MCID {mcid}"
                issue("duplicate_mcid_reference", loc)
    if not headings or headings[0] != 1:
        issue("missing_heading_one", "StructTreeRoot")
    if (tags["/Table"] or tables_count) and not (tags["/TH"] or th_count):
        issue("table_missing_header", "StructTreeRoot")
    field_facts = _pdf_controls(reader, issue)

    ro_pages_checked = 0
    ro_worst_page: int | None = None
    ro_worst_ratio = 1.0
    for index, page in enumerate(reader.pages, 1):
        location = f"pagina {index}"
        if not (page.extract_text() or "").strip():
            issue("page_without_extractable_text", location)
        if marked and struct is not None and "/Contents" in page:
            paint_mcids: list[int] = []
            seen_paint: set[int] = set()
            mc_stack: list[tuple[str, int | None]] = []
            nested_art = False
            untagged_txt = False
            try:
                stream = ContentStream(page["/Contents"], reader)
                for operands, operator in stream.operations:
                    if operator in (b"BMC", b"BDC"):
                        tag = str(operands[0]) if operands else ""
                        stream_mcid: int | None = None
                        if operator == b"BDC" and len(operands) > 1:
                            props = _deref(operands[1])
                            if isinstance(props, dict) and "/MCID" in props:
                                try:
                                    stream_mcid = int(props["/MCID"])
                                except (TypeError, ValueError):
                                    stream_mcid = None
                        if stream_mcid is not None and stream_mcid not in seen_paint:
                            seen_paint.add(stream_mcid)
                            paint_mcids.append(stream_mcid)
                        if mc_stack and (
                            (tag == "/Artifact" and any(m is not None for _, m in mc_stack))
                            or (stream_mcid is not None and any(t == "/Artifact" for t, _ in mc_stack))
                        ):
                            nested_art = True
                        mc_stack.append((tag, stream_mcid))
                    elif operator == b"EMC":
                        if mc_stack:
                            mc_stack.pop()
                    elif operator in _TEXT_SHOW_OPS:
                        in_artifact = any(t == "/Artifact" for t, _ in mc_stack)
                        in_mcid = any(m is not None for _, m in mc_stack)
                        if not in_artifact and not in_mcid and _has_text_payload(operator, operands):
                            untagged_txt = True
            except Exception:  # noqa: BLE001 - stream malformado: ignora leitura de ordem/aninhamento sem quebrar
                paint_mcids = []
            if nested_art:
                issue("nested_artifact_tagged", location)
            if untagged_txt:
                issue("untagged_page_content", location)
            want = logical_mcids.get(index, [])
            if len(want) >= 4 and len(paint_mcids) >= 4:
                rank = {m: i for i, m in enumerate(want)}
                painted = [rank[m] for m in paint_mcids if m in rank]
                if len(painted) >= 4:
                    ro_pages_checked += 1
                    share = _lis_length(painted) / len(painted)
                    if share < ro_worst_ratio:
                        ro_worst_ratio = round(share, 3)
                        ro_worst_page = index
                    if share < 0.8:
                        issue("reading_order_mismatch", location)

        resources = _deref(page.get("/Resources"))
        fonts_dict = _deref(resources.get("/Font")) if isinstance(resources, dict) else {}
        if isinstance(fonts_dict, dict):
            for font_ref in fonts_dict.values():
                font = _deref(font_ref)
                if not isinstance(font, dict):
                    continue
                descendants = _deref(font.get("/DescendantFonts", [])) or []
                for entry in descendants or [font]:
                    f = _deref(entry)
                    if not isinstance(f, dict):
                        continue
                    descriptor = _deref(f.get("/FontDescriptor"))
                    desc_dict = descriptor if isinstance(descriptor, dict) else {}
                    if not any(key in desc_dict for key in ("/FontFile", "/FontFile2", "/FontFile3")):
                        issue("font_not_embedded", location)
                    if font.get("/Subtype") == "/Type0" and f.get("/Subtype") == "/CIDFontType2" and "/CIDToGIDMap" not in f:
                        issue("font_missing_cid_to_gid_map", location)
                if font.get("/Subtype") == "/Type0" and "/ToUnicode" not in font:
                    issue("font_missing_unicode_map", location)
                if "/ToUnicode" in font:
                    try:
                        tu_stream = _deref(font["/ToUnicode"])
                        raw_tu = tu_stream.get_data().decode("latin-1", errors="replace")
                    except Exception:  # noqa: BLE001 - stream ToUnicode ausente ou ilegivel
                        raw_tu = ""
                    if raw_tu and _tounicode_has_noncharacter(raw_tu):
                        issue("font_tounicode_noncharacter", location)

        annots = _deref(page.get("/Annots", [])) or []
        if annots and page.get("/Tabs") != "/S":
            issue("page_tabs_not_structure", location)
        for annotation in annots:
            annot = _deref(annotation)
            if not isinstance(annot, dict):
                continue
            if annot.get("/Subtype") == "/Link":
                if "/StructParent" not in annot:
                    issue("link_not_tagged", location)
                if not str(annot.get("/Contents", "")).strip():
                    issue("link_missing_contents", location)

    return _result(
        "pdf",
        issues,
        {
            "title": str(title),
            "language": str(language),
            "pages": len(reader.pages),
            "marked": marked,
            "suspects": suspects,
            "display_doc_title": display_doc_title,
            "role_map": role_map,
            "tags": dict(tags),
            "heading_levels": headings,
            "reading_order": {
                "pages_checked": ro_pages_checked,
                "worst_page": ro_worst_page,
                "worst_in_order_ratio": round(ro_worst_ratio, 3),
            },
            "tables": {
                "count": tables_count,
                "irregular_count": irregular_tables,
                "th_count": th_count,
                "th_with_scope_or_headers": th_scoped,
            },
            **field_facts,
        },
    )


def _pdf_controls(reader: PdfReader, issue: Any) -> dict[str, Any]:
    """Duas representacoes precisam concordar: Fields canonico, widgets e tags."""
    root = reader.root_object
    canonical: set[tuple[int, int]] = set()

    def identifier(ref: Any) -> tuple[int, int]:
        indirect = ref if hasattr(ref, 'idnum') else getattr(ref, 'indirect_reference', None)
        return (indirect.idnum, indirect.generation) if indirect else (-1, -1)

    def fields(ref: Any) -> None:
        key = identifier(ref)
        if key in canonical:
            return
        canonical.add(key)
        node = ref.get_object()
        for child in node.get('/Kids', []):
            fields(child)
    acro = root.get('/AcroForm', {})
    acro = acro.get_object() if hasattr(acro, 'get_object') else acro
    for ref in acro.get('/Fields', []):
        fields(ref)

    def inherited(node: Any, key: str) -> Any:
        seen = set()
        while isinstance(node, dict) and id(node) not in seen:
            seen.add(id(node))
            if key in node:
                return node[key]
            node = node.get('/Parent')
            node = node.get_object() if node is not None else None
        return None
    parent_values: dict[int, Any] = {}

    seen_parents: set[int] = set()

    def parents(tree: Any) -> None:
        tree = tree.get_object()
        if id(tree) in seen_parents:
            return
        seen_parents.add(id(tree))
        values = tree.get('/Nums', [])
        parent_values.update({int(key): val for key, val in zip(values[::2], values[1::2])})
        for child in tree.get('/Kids', []):
            parents(child)
    structure = root.get('/StructTreeRoot')
    if structure is not None and '/ParentTree' in structure.get_object():
        parents(structure.get_object()['/ParentTree'])
    named = reader.named_destinations
    facts = []
    for page in reader.pages:
        for ref in page.get('/Annots', []):
            node = ref.get_object()
            if node.get('/Subtype') == '/Link':
                action = node.get('/A', {})
                action = action.get_object() if hasattr(action,'get_object') else action
                target = node.get('/Dest', action.get('/D') if action.get('/S') == '/GoTo' else None)
                if isinstance(target, str) and target not in named:
                    issue('broken_internal_link', target)
            if node.get('/Subtype') != '/Widget':
                continue
            name, label, kind = (inherited(node, key) for key in ('/T','/TU','/FT'))
            location = str(name or 'campo PDF')
            if identifier(ref) not in canonical:
                issue('orphan_form_widget', location)
            if not str(label or '').strip():
                issue('form_missing_label', location)
            if not name:
                issue('form_missing_name', location)
            if kind not in ('/Tx','/Btn','/Ch','/Sig'):
                issue('form_unknown_type', location)
            parent = parent_values.get(node.get('/StructParent'))
            parent = parent.get_object() if parent is not None else {}
            kids = parent.get('/K', [])
            kids = kids if isinstance(kids,list) else [kids]
            bound = any(isinstance(child.get_object(),dict) and child.get_object().get('/Type') == '/OBJR' and identifier(child.get_object().get('/Obj')) == identifier(ref) for child in kids)
            if parent.get('/S') != '/Form' or not bound:
                issue('form_not_tagged', location)
            if '/N' not in node.get('/AP', {}):
                issue('form_missing_appearance', location)
            if page.get('/Tabs') != '/S':
                issue('form_tab_order_requires_review', location)
            facts.append({'name': location, 'label': str(label or ''), 'type': str(kind or ''),
                          'value': str(inherited(node,'/V') or ''), 'required': bool(int(inherited(node,'/Ff') or 0) & 2)})
    return {'fields': facts, 'named_destinations': len(named)}


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
    if suffix == ".xlsx":
        from .report_artifacts import validate_xlsx

        return validate_xlsx(path, report_schema=False)
    if suffix == ".pptx":
        from .report_artifacts import validate_pptx

        return validate_pptx(path)
    if suffix != ".pdf":
        raise ValueError("Formato aceito: DOCX, PDF, XLSX ou PPTX.")
    result = validate_pdf(path)
    result["pdf_ua"] = await verapdf(path) if external else {"status": "not_run", "reason": "Nao solicitado."}
    if result["pdf_ua"]["status"] in ("failed", "error"):
        result["status"] = "issues_found"
    elif external and result["pdf_ua"]["status"] == "not_run" and not result["issues"]:
        result["status"] = "partial"
    return result
