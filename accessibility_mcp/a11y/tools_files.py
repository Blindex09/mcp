"""Ferramentas MCP do editor de arquivos (ler, editar com aprovacao, desfazer). Regras e limites: ver files.py."""

from __future__ import annotations

import json
from typing import Any

from . import files


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=1)


def register_files(mcp: Any) -> None:
    @mcp.tool()
    async def a11y_read_file(path: str, offset: int = 0, limit: int = 0) -> str:
        """Read a text file of the person's project (inside the workspace folder A11Y_MCP_WORKSPACE) with line numbers, so you can fix
        accessibility problems in the source without a terminal. offset: lines to skip; limit: how many lines (0 = to the end). Secrets
        (.env, keys), .git and anything outside the workspace are refused with the reason."""
        try:
            return _json(files.read_file(path, offset, limit))
        except files.FileError as e:
            return _json({"error": str(e)})

    @mcp.tool()
    async def a11y_edit_file(path: str, old_string: str, new_string: str, replace_all: bool = False) -> str:
        """Edit a file of the person's project by replacing an EXACT piece of text (old_string must appear once, or use replace_all), or
        create a new file (old_string empty). Read the file first with a11y_read_file and copy the piece exactly. A JSON or Python file
        that was valid cannot become invalid. A backup is kept before every write (undo with a11y_undo_edit). With approval ON (default,
        A11Y_MCP_EDIT_APPROVAL) the edit is HELD and shown as a diff until the person answers: show them the diff and then call
        a11y_approve_edit with THEIR answer, never on your own. With approval OFF the edit is applied at once."""
        try:
            return _json(files.edit_file(path, old_string, new_string, replace_all))
        except files.FileError as e:
            return _json({"error": str(e)})

    @mcp.tool()
    async def a11y_approve_edit(decision: str, approval_id: str = "") -> str:
        """Answer the person's approval for edits that a11y_edit_file is HOLDING. decision: allow | deny. approval_id: the held edit
        (empty = every held edit). If the file changed while waiting, the edit is not applied and you are told to redo it. Only call this
        with the person's actual answer."""
        try:
            return _json(files.decide(decision, approval_id))
        except files.FileError as e:
            return _json({"error": str(e)})

    @mcp.tool()
    async def a11y_undo_edit(edit_id: str = "") -> str:
        """Undo an applied edit from this session by restoring the backup (the last one if edit_id is empty). An edit that created a file
        is undone by removing that file."""
        try:
            return _json(files.undo_edit(edit_id))
        except files.FileError as e:
            return _json({"error": str(e)})
