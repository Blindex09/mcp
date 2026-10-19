"""Aprendizado sempre: o servidor guarda o que o modelo do cliente aprendeu testando, entre sessoes, sem fila de aprovacao.

O MODELO DO CLIENTE decide o que vale lembrar (`a11y_learn`), por significado. O codigo so guarda, valida o formato, limita o tamanho,
marca a origem e impede duplicata de MESMO assunto (igualdade de texto normalizado e' fato objetivo). Fica na pasta do usuario
(A11Y_MCP_HOME, padrao ~/.a11y-mcp), nunca no projeto. Desligar: A11Y_MCP_LEARN=0.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

GENERAL = "geral"
MAX_PER_SCOPE = 30
MAX_LEARNING_CHARS = 400
PROMPT_CHARS = 2500
ORIGIN = "cliente"  # quem escreveu: o modelo do cliente, a partir do que mediu; nunca vira instrucao


def enabled() -> bool:
    return os.environ.get("A11Y_MCP_LEARN", "1").strip().lower() not in ("0", "false", "no", "off")


def store_path() -> Path:
    home = os.environ.get("A11Y_MCP_HOME")
    return Path(home) if home else Path.home() / ".a11y-mcp"


def _file() -> Path:
    return store_path() / "learnings.json"


def host_of(url: str | None) -> str:
    return (urlparse(url or "").hostname or "html-local").lower()


def load_all() -> list[dict[str, Any]]:
    try:
        data = json.loads(_file().read_text(encoding="utf-8"))
        return [e for e in data.get("entries", []) if isinstance(e, dict) and e.get("topic") and e.get("learning")]
    except (OSError, ValueError):
        return []


def _save(entries: list[dict[str, Any]]) -> None:
    folder = store_path()
    folder.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=folder, suffix=".tmp")  # escrita atomica: nunca deixa o arquivo pela metade
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"entries": entries}, f, ensure_ascii=False, indent=1)
    os.replace(tmp, _file())


def relevant(host: str) -> list[dict[str, Any]]:
    """Aprendizados gerais + os deste site."""
    return [e for e in load_all() if e.get("scope") in (GENERAL, host)]


def remember(scope: str, topic: str, learning: str) -> dict[str, Any] | None:
    """Grava um aprendizado (mesmo assunto = atualiza, nunca duplica) e devolve a entrada gravada; None se desligado ou invalido."""
    if not enabled():
        return None
    topic, learning, scope = topic.strip(), learning.strip(), scope.strip().lower()
    if not topic or not learning or not scope:
        return None
    merged = merge_changes(load_all(), [{"topic": topic, "learning": learning, "scope": scope}], {scope})
    _save(merged)
    return next((e for e in merged if e["scope"] == scope and _norm(e["topic"]) == _norm(topic)), None)


def render_for_prompt(entries: list[dict[str, Any]]) -> str:
    lines = [f"- [{e['scope']}] {e['topic']}: {e['learning']}" for e in entries]
    return "\n".join(lines)[:PROMPT_CHARS]


def _norm(text: str) -> str:
    return " ".join(str(text).lower().split())


def merge_changes(existing: list[dict[str, Any]], changes: list[Any], scopes: set[str]) -> list[dict[str, Any]]:
    """Aplica as MUDANCAS: cada item novo/atualizado entra (mesmo assunto = atualiza, nunca duplica);
    remocao so quando pedida de forma EXPLICITA. Omitir um aprendizado nunca o apaga."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    table: dict[tuple[str, str], dict[str, Any]] = {(e["scope"], _norm(e["topic"])): e for e in existing if e.get("scope") and e.get("topic")}
    for item in changes:
        if not isinstance(item, dict):
            continue
        topic, scope = str(item.get("topic") or "").strip(), item.get("scope")
        if not topic or scope not in scopes:
            continue
        key = (scope, _norm(topic))
        if item.get("remove") is True:
            table.pop(key, None)
            continue
        learning = str(item.get("learning") or "").strip()
        if learning:
            table[key] = {"topic": topic[:80], "learning": learning[:MAX_LEARNING_CHARS], "scope": scope, "origin": ORIGIN, "updated": now}
    out: list[dict[str, Any]] = []
    per_scope: dict[str, list[dict[str, Any]]] = {}
    for e in table.values():
        per_scope.setdefault(e["scope"], []).append(e)
    for entries in per_scope.values():
        entries.sort(key=lambda e: e.get("updated", ""), reverse=True)  # o teto descarta os mais antigos
        out.extend(entries[:MAX_PER_SCOPE])
    return out


def forget(topic: str, scope: str = "") -> int:
    """Controle da pessoa: remove um aprendizado."""
    entries = load_all()
    keep = [e for e in entries if not (_norm(e["topic"]) == _norm(topic) and (not scope or e.get("scope") == scope))]
    removed = len(entries) - len(keep)
    if removed:
        _save(keep)
    return removed
