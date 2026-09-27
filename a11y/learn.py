"""Aprendizado sempre: o servidor lembra o que aprendeu testando, entre execucoes, sem fila de aprovacao.

O MODELO decide o que vale lembrar e como fundir com o que ja existe (por significado). O codigo so guarda, valida o formato,
limita o tamanho e impede duplicata de MESMO assunto (igualdade de texto normalizado e' fato objetivo). Fica na pasta do usuario
(A11Y_MCP_HOME, padrao ~/.a11y-mcp), nunca no projeto. Desligar: A11Y_MCP_LEARN=0.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from llm import Hint, extract_json

GENERAL = "geral"
ROUTING = "roteamento"  # licoes do roteador de modelos (router.py); nao entram no prompt do agente
MAX_PER_SCOPE = 30
MAX_LEARNING_CHARS = 400
PROMPT_CHARS = 2500

AskFn = Callable[..., Awaitable[str | None]]


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


def remember(scope: str, topic: str, learning: str) -> None:
    """Grava um FATO direto (sem passar por modelo), reaproveitando a mesma fusao/dedup/limite dos aprendizados
    normais. Usado para coisas decididas uma vez e reaproveitadas (ex.: qual modelo um provedor resolveu ser),
    nao para julgamento de execucao."""
    merged = merge_changes(load_all(), [{"topic": topic, "learning": learning, "scope": scope}], {scope})
    _save(merged)


def render_for_prompt(entries: list[dict[str, Any]]) -> str:
    lines = [f"- [{e['scope']}] {e['topic']}: {e['learning']}" for e in entries]
    return "\n".join(lines)[:PROMPT_CHARS]


def _norm(text: str) -> str:
    return " ".join(str(text).lower().split())


def merge_changes(existing: list[dict[str, Any]], changes: list[Any], scopes: set[str]) -> list[dict[str, Any]]:
    """Aplica as MUDANCAS devolvidas pelo modelo: cada item novo/atualizado entra (mesmo assunto = atualiza, nunca duplica);
    remocao so quando o modelo pede de forma EXPLICITA. Omitir um aprendizado nunca o apaga."""
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
            table[key] = {"topic": topic[:80], "learning": learning[:MAX_LEARNING_CHARS], "scope": scope, "updated": now}
    out: list[dict[str, Any]] = []
    per_scope: dict[str, list[dict[str, Any]]] = {}
    for e in table.values():
        per_scope.setdefault(e["scope"], []).append(e)
    for entries in per_scope.values():
        entries.sort(key=lambda e: e.get("updated", ""), reverse=True)  # o teto descarta os mais antigos
        out.extend(entries[:MAX_PER_SCOPE])
    return out


async def learn_from_run(ask: AskFn, host: str, run_digest: str, routing: str = "") -> list[str]:
    """Pede ao modelo (nivel leve) as MUDANCAS nos aprendizados; aplica e grava na hora. Nunca derruba a execucao."""
    if not enabled():
        return []
    try:
        existing = load_all()
        current = [e for e in existing if e.get("scope") in (GENERAL, host, ROUTING)]
        prompt = (
            "Voce mantem a memoria de um testador de acessibilidade. Abaixo estao os aprendizados ATUAIS (gerais e deste site) e o resumo "
            "de uma execucao que acabou de terminar. Devolva SOMENTE AS MUDANCAS: itens novos ou atualizados. Se algo novo trata do "
            "mesmo assunto de um aprendizado existente, reescreva o existente com o MESMO topic (nunca crie duplicata). Para remover algo "
            'que a execucao provou errado, devolva {"topic": "...", "scope": "...", "remove": true}; o que voce nao mencionar continua '
            "como esta. Vale registrar o que funcionou, o que enganou, como este site se comporta, que sondagem revelou o problema e "
            "falsos positivos. Nada de dados pessoais, credenciais ou valores digitados. Cada item: "
            f'{{"topic": "assunto curto", "learning": "o que lembrar, em ate {MAX_LEARNING_CHARS} caracteres, em portugues corrido sem markdown", '
            f'"scope": "{GENERAL}" ou "{host}" ou "{ROUTING}"}}. O escopo "{ROUTING}" e so para licoes sobre qual camada de modelo '
            "(fast ou main) atendeu bem cada tipo de pedido e quando foi preciso subir. Responda SOMENTE com um array JSON (pode ser vazio).\n\n"
            f"APRENDIZADOS ATUAIS:\n{json.dumps(current, ensure_ascii=False)[:6000]}\n\nRESUMO DA EXECUCAO:\n{run_digest[:5000]}"
            + (f"\n\nROTEAMENTO DESTA EXECUCAO (camada usada em cada chamada e se precisou subir):\n{routing[:3000]}" if routing else "")
        )
        hint = Hint(
            purpose="atualizar a memoria de aprendizados a partir do resumo de uma execucao de teste",
            brief=f"{len(current)} aprendizados atuais; resumo de {len(run_digest)} caracteres",
            validate=lambda r: isinstance(extract_json(r, "array"), list),
        )
        raw = await ask(prompt, None, 1500, hint=hint)
        returned = extract_json(raw, "array")
        if not isinstance(returned, list):
            return []
        merged = merge_changes(existing, returned, {GENERAL, host, ROUTING})
        _save(merged)
        return sorted({e["topic"] for e in merged if e.get("scope") in (GENERAL, host)})
    except Exception:  # noqa: BLE001 - aprender e' bonus: falha aqui nunca derruba o teste
        return []


def forget(topic: str, scope: str = "") -> int:
    """Controle da pessoa: remove um aprendizado."""
    entries = load_all()
    keep = [e for e in entries if not (_norm(e["topic"]) == _norm(topic) and (not scope or e.get("scope") == scope))]
    removed = len(entries) - len(keep)
    if removed:
        _save(keep)
    return removed
