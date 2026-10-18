"""Editor de arquivos do projeto da pessoa: ler, editar e desfazer sem depender de terminal.

Papeis que nunca se invertem: o MODELO decide o que mudar e por que. O HARNESS (este modulo) so impoe o que e permitido:
- pasta de trabalho escolhida pela pessoa NA CONVERSA (`a11y_set_workspace`; nada para configurar antes, e a variavel
  `A11Y_MCP_WORKSPACE` e so uma pre-selecao opcional); nada fora dela, nem por link simbolico;
- arquivos de segredo e a pasta .git nunca sao lidos nem escritos;
- a edicao e uma troca EXATA de um trecho que existe uma unica vez (ou todas, se pedido), nunca uma reescrita as cegas;
- integridade: um arquivo JSON ou Python que era valido nao pode passar a ser invalido;
- copia de seguranca antes de cada escrita (fora do projeto) e escrita atomica; `undo` devolve o arquivo;
- aprovacao: ligada (padrao) a edicao fica RETIDA mostrando o que muda e so acontece quando a pessoa responde; desligada
  (`A11Y_MCP_EDIT_APPROVAL=0`) o agente edita sem perguntar. Nunca uma recusa seca.
Sem prazo nem teto de tamanho imposto pelo codigo: a pessoa escolhe o recorte de leitura com `offset` e `limit`.
"""

from __future__ import annotations

import ast
import difflib
import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any

from . import learn

SECRET_NAMES = (".env", ".npmrc", ".pypirc", ".netrc", "credentials.json", "id_rsa", "id_ed25519")
SECRET_SUFFIXES = (".pem", ".key", ".pfx", ".p12")
PROTECTED_DIRS = (".git",)


class FileError(ValueError):
    """Pedido recusado com a razao em texto (nunca uma recusa seca: diz o que fazer)."""


# ------------------------------------------------------------------------------------------------ pasta de trabalho
def approval_enabled() -> bool:
    return os.environ.get("A11Y_MCP_EDIT_APPROVAL", "1").strip().lower() not in ("0", "false", "no", "off")


_CHOSEN: Path | None = None  # pasta escolhida na conversa (a pessoa nao precisa configurar nada)


def _too_broad(root: Path) -> bool:
    """Fato objetivo e protecao: a raiz do disco e a pasta pessoal inteira nao sao um projeto."""
    return root == Path(root.anchor) or root == Path.home().resolve()


def set_workspace(path: str) -> dict[str, str]:
    """A pasta de trabalho e a que a PESSOA nomeou na conversa; o proprio cliente pede a permissao dela ao chamar a ferramenta."""
    global _CHOSEN
    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        raise FileError(f"A pasta nao existe: {root}")
    if _too_broad(root):
        raise FileError("Essa pasta e ampla demais (a raiz do disco ou a pasta pessoal inteira). Escolha a pasta do projeto.")
    _CHOSEN = root
    return {"workspace": str(root)}


def workspace() -> Path:
    if _CHOSEN is not None:
        return _CHOSEN
    raw = os.environ.get("A11Y_MCP_WORKSPACE", "").strip()  # opcional: pre-seleciona a pasta
    if not raw:
        raise FileError(
            "Ainda nao ha pasta de trabalho. Pergunte a pessoa em que pasta esta o projeto e chame a11y_set_workspace com ela. "
            "O editor nunca mexe fora dessa pasta."
        )
    root = Path(raw).expanduser().resolve()
    if not root.is_dir():
        raise FileError(f"A pasta de trabalho nao existe: {root}")
    return root


def resolve(path: str) -> Path:
    """Caminho dentro da pasta de trabalho, ja resolvido (links seguidos). Fora dela, segredo ou .git: recusado."""
    if not path or "\x00" in path:
        raise FileError("Informe o caminho do arquivo.")
    root = workspace()
    candidate = Path(path)
    full = (candidate if candidate.is_absolute() else root / candidate).resolve()
    try:
        relative = full.relative_to(root)
    except ValueError:
        raise FileError(f"O caminho esta fora da pasta de trabalho ({root}). Use um caminho dentro dela.") from None
    parts = {p.casefold() for p in relative.parts}
    if parts & {d.casefold() for d in PROTECTED_DIRS}:
        raise FileError("A pasta .git nao e editada por aqui.")
    name = full.name.casefold()
    if name in SECRET_NAMES or name.startswith(".env") or name.endswith(SECRET_SUFFIXES):
        raise FileError("Este arquivo guarda segredos (chaves, credenciais) e nao e lido nem editado por aqui.")
    return full


# ------------------------------------------------------------------------------------------------ leitura
def read_file(path: str, offset: int = 0, limit: int = 0) -> dict[str, Any]:
    full = resolve(path)
    if not full.is_file():
        raise FileError(f"Arquivo nao encontrado: {path}")
    raw = full.read_bytes()
    if b"\x00" in raw[:8192]:
        raise FileError("Arquivo binario: o editor trabalha com texto.")
    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()
    start = max(0, int(offset))
    chosen = lines[start : start + int(limit)] if int(limit) > 0 else lines[start:]
    return {
        "path": str(full.relative_to(workspace())),
        "total_lines": len(lines),
        "from_line": start + 1,
        "line_ending": "CRLF" if b"\r\n" in raw else "LF",
        "content": "\n".join(f"{start + i + 1:>6}\t{line}" for i, line in enumerate(chosen)),
    }


# ------------------------------------------------------------------------------------------------ edicao
def _integrity_error(path: Path, before: str, after: str) -> str | None:
    """Fato objetivo: um JSON ou Python valido nao pode virar invalido. Outros formatos nao sao julgados aqui."""
    suffix = path.suffix.lower()
    try:
        if suffix == ".json":
            json.loads(before)
            checker = json.loads
        elif suffix == ".py":
            ast.parse(before)
            checker = ast.parse  # type: ignore[assignment]
        else:
            return None
    except (ValueError, SyntaxError):
        return None  # ja estava quebrado: nao e a edicao que o quebra
    try:
        checker(after)
    except (ValueError, SyntaxError) as e:
        return f"a edicao deixaria o arquivo {suffix} invalido ({type(e).__name__}: {str(e)[:120]})"
    return None


def _plan(path: str, old: str, new: str, replace_all: bool) -> dict[str, Any]:
    full = resolve(path)
    creating = old == "" and not full.exists()
    if creating:
        before, after = "", new
    else:
        if not full.is_file():
            raise FileError(f"Arquivo nao encontrado: {path}. Para criar um arquivo novo, deixe old_string vazio.")
        before = full.read_bytes().decode("utf-8")
        if not old:
            raise FileError("old_string vazio so serve para criar um arquivo novo.")
        count = before.count(old)
        if count == 0:
            raise FileError("O trecho old_string nao existe no arquivo. Leia o arquivo de novo e copie o trecho exato.")
        if count > 1 and not replace_all:
            raise FileError(f"O trecho aparece {count} vezes. Inclua mais contexto para ele ser unico, ou use replace_all.")
        if old == new:
            raise FileError("old_string e new_string sao iguais: nada a mudar.")
        after = before.replace(old, new) if replace_all else before.replace(old, new, 1)
    problem = _integrity_error(full, before, after)
    if problem:
        raise FileError(problem)
    return {"full": full, "before": before, "after": after, "creating": creating}


def _diff(plan: dict[str, Any]) -> str:
    name = plan["full"].name
    return "".join(difflib.unified_diff(
        plan["before"].splitlines(keepends=True), plan["after"].splitlines(keepends=True), f"a/{name}", f"b/{name}", n=2,
    ))


def _backup_root() -> Path:
    return learn.store_path() / "edit-backups"


PENDING: dict[str, dict[str, Any]] = {}
HISTORY: list[dict[str, Any]] = []  # pilha de edicoes aplicadas (a ultima desfaz primeiro)


def _apply(plan: dict[str, Any]) -> dict[str, Any]:
    full: Path = plan["full"]
    entry: dict[str, Any] = {"id": uuid.uuid4().hex[:8], "path": str(full), "existed": not plan["creating"], "backup": None}
    if not plan["creating"]:
        folder = _backup_root() / entry["id"]
        folder.mkdir(parents=True, exist_ok=True)
        backup = folder / full.name
        backup.write_bytes(full.read_bytes())
        entry["backup"] = str(backup)
    full.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=full.parent, suffix=".a11y-tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:  # newline="": preserva CRLF/LF do arquivo
            handle.write(plan["after"])
        os.replace(tmp, full)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    HISTORY.append(entry)
    return {"applied": True, "edit_id": entry["id"], "path": str(full.relative_to(workspace())), "created": plan["creating"]}


def edit_file(path: str, old_string: str, new_string: str, replace_all: bool = False) -> dict[str, Any]:
    plan = _plan(path, old_string, new_string, replace_all)
    diff = _diff(plan)
    if not approval_enabled():
        return {**_apply(plan), "diff": diff}
    pending_id = "e" + uuid.uuid4().hex[:6]
    PENDING[pending_id] = plan
    return {
        "held": True,
        "approval_id": pending_id,
        "path": str(plan["full"].relative_to(workspace())),
        "diff": diff,
        "note": "A edicao esta RETIDA ate a pessoa responder. Mostre o diff a ela e chame a11y_approve_edit com a resposta dela; "
        "nunca aprove por conta propria.",
    }


def decide(decision: str, approval_id: str = "") -> dict[str, Any]:
    if decision not in ("allow", "deny"):
        raise FileError("decision deve ser allow ou deny.")
    ids = [approval_id] if approval_id else list(PENDING)
    if not ids:
        raise FileError("Nao ha edicao retida.")
    results: list[dict[str, Any]] = []
    for item in ids:
        plan = PENDING.pop(item, None)
        if plan is None:
            results.append({"approval_id": item, "error": "edicao retida nao encontrada"})
        elif decision == "deny":
            results.append({"approval_id": item, "denied": True, "path": str(plan["full"].relative_to(workspace()))})
        else:
            # o arquivo pode ter mudado enquanto esperava a resposta: confere de novo antes de escrever
            current = plan["full"].read_bytes().decode("utf-8") if plan["full"].exists() else ""
            if current != plan["before"]:
                results.append({"approval_id": item, "error": "o arquivo mudou enquanto a edicao esperava; refaca a edicao"})
            else:
                results.append({"approval_id": item, **_apply(plan)})
    return {"results": results, "still_held": list(PENDING)}


def undo_edit(edit_id: str = "") -> dict[str, Any]:
    if not HISTORY:
        raise FileError("Nao ha edicao para desfazer nesta sessao.")
    if edit_id:
        matches = [e for e in HISTORY if e["id"] == edit_id]
        if not matches:
            raise FileError("edit_id nao encontrado.")
        entry = matches[0]
    else:
        entry = HISTORY[-1]
    path = Path(entry["path"])
    if entry["existed"]:
        data = Path(entry["backup"]).read_bytes()
        path.write_bytes(data)
    elif path.exists():
        path.unlink()  # a edicao tinha criado o arquivo: desfazer e remove-lo
    HISTORY.remove(entry)
    return {"undone": entry["id"], "path": str(path.relative_to(workspace())), "restored_from_backup": entry["existed"]}
