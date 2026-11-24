"""Compressao deterministica de snapshots YAML de acessibilidade para paginas grandes.

Preserva integralmente papeis interativos e estruturais protegidos, dobrando apenas irmaos repetitivos
nao-interativos quando um pai supera o limiar (padrao >100 irmaos, mantendo os primeiros 10).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_ROLE_PREFIX_RE = re.compile(r"^\s*-\s*([a-z][a-z0-9-]*)\b", re.IGNORECASE)
_HAS_REF_RE = re.compile(r"\[ref=[^\]]+\]")
_QUOTED_DQ_RE = re.compile(r'"[^"]*"')
_QUOTED_SQ_RE = re.compile(r"'[^']*'")
_DIGITS_RE = re.compile(r"\b\d+\b")

_PROTECTED_LINE_ROLES = frozenset({
    "alert", "banner", "button", "checkbox", "columnheader", "combobox", "dialog",
    "form", "grid", "gridcell", "heading", "input", "link", "listbox", "main",
    "menu", "menuitem", "menuitemcheckbox", "menuitemradio", "navigation", "option",
    "radio", "rowheader", "search", "searchbox", "select", "slider", "spinbutton",
    "status", "switch", "tab", "textbox", "tree", "treegrid", "treeitem", "region",
})
_REF_PROTECTED_LINE_ROLES = frozenset({"grid", "gridcell", "scrollbar", "separator", "treegrid"})
_REF_PROTECTED_DESCENDANT_ROLES = frozenset({"columnheader", "gridcell", "rowheader", "scrollbar", "separator"})
_PROTECTED_SUBTREE_ROLES = frozenset({
    "button", "checkbox", "combobox", "input", "link", "listbox", "menu",
    "menuitem", "menuitemcheckbox", "menuitemradio", "option", "radio", "searchbox",
    "select", "slider", "spinbutton", "switch", "tab", "textbox", "tree", "treeitem",
})
_ROW_CONTAINER_ROLES = frozenset({"grid", "treegrid"})


@dataclass
class _Group:
    total: int = 0
    seen: int = 0


@dataclass
class _Line:
    text: str
    indent: int
    parent_index: int
    protected_line: bool
    contains_protected_subtree: bool
    under_row_container: bool
    group: _Group | None = None

    @property
    def is_candidate(self) -> bool:
        return self.indent != len(self.text) and not self.protected_line and not self.contains_protected_subtree


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" \t"))


def _role_of(line: str) -> str | None:
    m = _ROLE_PREFIX_RE.match(line)
    return m.group(1).lower() if m else None


def _signature(line: str) -> str:
    s = _HAS_REF_RE.sub("[ref=?]", line.rstrip())
    s = _QUOTED_DQ_RE.sub('""', s)
    s = _QUOTED_SQ_RE.sub("''", s)
    s = _DIGITS_RE.sub("N", s)
    return s.lstrip()[:80]


def compress_aria_snapshot(yaml_text: str, threshold: int = 100, keep_n: int = 10) -> tuple[str, int]:
    """Dobra listas repetitivas nao protegidas (> threshold irmaos identicos) mantendo keep_n e preservando controles."""
    raw_lines = yaml_text.split("\n")
    if len(raw_lines) <= threshold:
        return yaml_text, 0

    lines: list[_Line] = []
    stack: list[int] = []
    for text in raw_lines:
        indent = _indent_of(text)
        blank = indent == len(text)
        if not blank:
            while stack and lines[stack[-1]].indent >= indent:
                stack.pop()
        parent_idx = stack[-1] if stack else -1
        parent = lines[parent_idx] if parent_idx >= 0 else None
        role = _role_of(text)
        has_ref = bool(_HAS_REF_RE.search(text))
        has_pointer = has_ref and "[cursor=pointer]" in text
        protected_row = role == "row" and has_ref and bool(parent and parent.under_row_container)
        protected_sub = (
            bool(parent and parent.contains_protected_subtree)
            or protected_row
            or (role in _PROTECTED_SUBTREE_ROLES if role else False)
            or (has_ref and role in _REF_PROTECTED_DESCENDANT_ROLES if role else False)
            or has_pointer
        )
        protected_line = (
            bool(role and (role in _PROTECTED_LINE_ROLES or (has_ref and role in _REF_PROTECTED_LINE_ROLES)))
        )
        under_row = bool(parent and parent.under_row_container) or (role in _ROW_CONTAINER_ROLES if role else False)
        if not blank:
            stack.append(len(lines))
        lines.append(_Line(text, indent, parent_idx, protected_line, protected_sub, under_row))

    for i in range(len(lines) - 1, -1, -1):
        ln = lines[i]
        if ln.contains_protected_subtree and ln.parent_index != -1:
            lines[ln.parent_index].contains_protected_subtree = True

    cand_counts: dict[int, int] = {}
    for ln in lines:
        if ln.is_candidate:
            cand_counts[ln.parent_index] = cand_counts.get(ln.parent_index, 0) + 1
    if not any(c > threshold for c in cand_counts.values()):
        return yaml_text, 0

    groups: dict[tuple[int, int, str], _Group] = {}
    max_group = 0
    for ln in lines:
        if not ln.is_candidate or cand_counts.get(ln.parent_index, 0) <= threshold:
            continue
        key = (ln.parent_index, ln.indent, _signature(ln.text))
        grp = groups.get(key)
        if grp is None:
            grp = _Group()
            groups[key] = grp
        ln.group = grp
        grp.total += 1
        max_group = max(max_group, grp.total)

    if max_group <= threshold:
        return yaml_text, 0

    out: list[str] = []
    removed = 0
    skip_below_indent: int | None = None
    for ln in lines:
        if ln.indent == len(ln.text):
            if skip_below_indent is None:
                out.append(ln.text)
            else:
                removed += 1
            continue
        if skip_below_indent is not None and ln.indent <= skip_below_indent:
            skip_below_indent = None
        if skip_below_indent is not None:
            removed += 1
            continue
        grp = ln.group
        if grp is None:
            out.append(ln.text)
            continue
        if grp.total > threshold:
            grp.seen += 1
            if grp.seen > keep_n:
                removed += 1
                skip_below_indent = ln.indent
                continue
        out.append(ln.text)

    if removed == 0:
        return yaml_text, 0
    note = f"\n# ... ({removed} nos ARIA repetitivos omitidos pela compressao; use compress=False para arvore completa)"
    return "\n".join(out) + note, removed
