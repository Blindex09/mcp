"""Acesso ao modelo que faz todo o julgamento do servidor.

Todo julgamento - que skill serve a uma tarefa, em que categoria uma skill cai - e feito por
um modelo, nunca por palavra-chave, regex ou ranking lexical. Este modulo so entrega o pedido
ao modelo e le a resposta; a unica validacao fixa e sobre fato objetivo (o nome devolvido
existe no catalogo?).

Ordem de quem responde (o servidor continua sendo um MCP standalone, sem depender de outro projeto):
1. O modelo do proprio cliente, via MCP sampling (nao custa nada extra ao usuario).
2. Um modelo de apoio configurado por variavel de ambiente, para clientes sem sampling:
   - SKILLS_MCP_BACKEND = "anthropic" | "ollama" (opcional; se ausente, detecta pelo que estiver configurado)
   - SKILLS_MCP_MODEL   = id do modelo (anthropic: padrao claude-haiku-4-5-20251001; ollama: obrigatorio)
   - ANTHROPIC_API_KEY  = chave (so lida do ambiente, nunca registrada em log)
   - OLLAMA_HOST        = endereco do Ollama (padrao http://localhost:11434)
Escolher qual backend usar e configuracao, nao julgamento.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_DEFAULT_MODEL = "claude-haiku-4-5-20251001"
OLLAMA_DEFAULT_HOST = "http://localhost:11434"
BACKEND_TIMEOUT_S = 90.0


async def _http_post(url: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=BACKEND_TIMEOUT_S) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, dict) else {}


def configured_backend() -> str | None:
    """Backend de apoio configurado no ambiente (None = nenhum)."""
    explicit = os.environ.get("SKILLS_MCP_BACKEND", "").strip().lower()
    if explicit in ("anthropic", "ollama"):
        return explicit
    if explicit:
        logger.warning("SKILLS_MCP_BACKEND invalido: %r (use anthropic ou ollama)", explicit)
        return None
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OLLAMA_HOST") or os.environ.get("SKILLS_MCP_MODEL"):
        return "ollama"
    return None


async def _ask_backend(prompt: str, max_tokens: int) -> str | None:
    backend = configured_backend()
    try:
        if backend == "anthropic":
            key = os.environ.get("ANTHROPIC_API_KEY")
            if not key:
                logger.warning("backend anthropic sem ANTHROPIC_API_KEY")
                return None
            data = await _http_post(
                ANTHROPIC_URL,
                {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                {
                    "model": os.environ.get("SKILLS_MCP_MODEL") or ANTHROPIC_DEFAULT_MODEL,
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text") or None
        if backend == "ollama":
            model = os.environ.get("SKILLS_MCP_MODEL")
            if not model:
                logger.warning("backend ollama exige SKILLS_MCP_MODEL")
                return None
            host = os.environ.get("OLLAMA_HOST") or OLLAMA_DEFAULT_HOST
            if not host.startswith(("http://", "https://")):
                host = f"http://{host}"
            data = await _http_post(
                f"{host.rstrip('/')}/api/chat",
                {"content-type": "application/json"},
                {
                    "model": model,
                    "stream": False,
                    "options": {"num_predict": max_tokens},
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            return str(data.get("message", {}).get("content", "")) or None
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("backend %s falhou: %s", backend, type(e).__name__)  # nunca loga chave/corpo
    return None


async def _ask_client(ctx: Any, prompt: str, max_tokens: int) -> str | None:
    try:
        from mcp.types import SamplingMessage, TextContent

        result = await ctx.session.create_message(
            messages=[SamplingMessage(role="user", content=TextContent(type="text", text=prompt))],
            max_tokens=max_tokens,
        )
        content = result.content
        return content.text if isinstance(content, TextContent) else None
    except Exception:  # noqa: BLE001 - sem sampling/erro do cliente: cai para o modelo de apoio
        return None


async def ask_model(ctx: Any, prompt: str, max_tokens: int = 800) -> str | None:
    """Pergunta ao modelo: 1) cliente (sampling), 2) modelo de apoio do ambiente. None = nenhum respondeu."""
    if ctx is not None:
        reply = await _ask_client(ctx, prompt, max_tokens)
        if reply is not None:
            return reply
    return await _ask_backend(prompt, max_tokens)


NO_MODEL_HELP = (
    "Nenhum modelo disponivel: o cliente nao oferece sampling e nao ha modelo de apoio configurado "
    "(defina ANTHROPIC_API_KEY, ou SKILLS_MCP_BACKEND=ollama com SKILLS_MCP_MODEL)."
)


def extract_json(raw: str | None, kind: str = "array") -> Any | None:
    """Le o JSON (array ou object) de uma resposta, tolerando texto em volta."""
    if not raw:
        return None
    open_ch, close_ch = ("[", "]") if kind == "array" else ("{", "}")
    i, j = raw.find(open_ch), raw.rfind(close_ch)
    if i == -1 or j <= i:
        return None
    try:
        return json.loads(raw[i : j + 1])
    except ValueError:
        return None
