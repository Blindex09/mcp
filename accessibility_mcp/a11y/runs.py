"""Execucoes salvas: cada teste autonomo guarda seus achados na pasta do usuario (A11Y_MCP_HOME), para exportar (EARL/SARIF) e comparar.

Fica fora do projeto, como os aprendizados. Desligar: A11Y_MCP_RUNS=0. Guarda so as ultimas MAX_RUNS execucoes.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import learn

MAX_RUNS = 100


def enabled() -> bool:
    return os.environ.get("A11Y_MCP_RUNS", "1").strip().lower() not in ("0", "false", "no", "off")


def _folder() -> Path:
    return learn.store_path() / "runs"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "local"


def save(host: str, record: dict[str, Any]) -> str | None:
    """Grava a execucao e devolve o run_id (ou None se desligado)."""
    if not enabled():
        return None
    now = datetime.now(timezone.utc)
    base_id = f"{now.strftime('%Y%m%d-%H%M%S')}-{_slug(host)}"
    folder = _folder()
    folder.mkdir(parents=True, exist_ok=True)
    run_id, n = base_id, 1
    while (folder / f"{run_id}.json").exists():  # duas execucoes no mesmo segundo nunca se sobrescrevem
        n += 1
        run_id = f"{base_id}-{n}"
    body = {"run_id": run_id, "created": now.isoformat(timespec="seconds"), "host": host, **record}
    fd, tmp = tempfile.mkstemp(dir=folder, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False, indent=1)
    os.replace(tmp, folder / f"{run_id}.json")
    for old in sorted(folder.glob("*.json"), key=lambda q: q.stem)[:-MAX_RUNS]:  # so os arquivos desta pasta, so alem do limite
        old.unlink(missing_ok=True)
    return run_id


def load(run_id: str) -> dict[str, Any] | None:
    """Le uma execucao PELO ID (so letras, numeros e hifen: texto do cliente nunca vira caminho de arquivo)."""
    if not re.fullmatch(r"[a-z0-9-]{1,80}", run_id or ""):
        return None
    path = _folder() / f"{run_id}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def list_runs(limit: int = 30) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for path in sorted(_folder().glob("*.json"), key=lambda q: q.stem, reverse=True)[:limit]:
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        counts: dict[str, int] = {}
        for f in d.get("findings", []):
            counts[f.get("outcome", "?")] = counts.get(f.get("outcome", "?"), 0) + 1
        out.append({k: d.get(k) for k in ("run_id", "created", "host", "url", "persona", "mode", "goal", "outcome")} | {"findings": counts})
    return out
