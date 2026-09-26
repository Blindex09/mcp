"""Acesso ao modelo que faz todo o julgamento do servidor.

Toda decisao de sentido - que guia serve a uma tarefa, o que uma tela mostra, qual o proximo passo de um
usuario - e de um modelo, nunca de palavra-chave, regex ou ranking lexical. Este modulo so entrega o pedido
ao modelo e le a resposta; a unica validacao fixa e sobre fato objetivo (o nome devolvido existe no catalogo?).

Quem responde (o servidor e um MCP standalone, sem depender de outro projeto):
1. Um modelo configurado por ambiente, chamando o provedor DIRETO (caminho principal: o MCP de 2026-07-28
   descontinuou o sampling em favor de chamar a API do provedor):
   - A11Y_MCP_BACKEND  = anthropic | openai | openai-compatible | ollama (opcional; senao detecta pelo ambiente)
   - A11Y_MCP_MODEL    = id do modelo. OBRIGATORIO: nao ha modelo padrao embutido, a escolha e sua.
   - A11Y_MCP_MODEL_FAST = (opcional) modelo mais barato para o que e leve (escolher guias, resumir aprendizados); o julgamento
                        pesado (usuario autonomo, relatorio) usa sempre A11Y_MCP_MODEL. Sem ele, tudo usa A11Y_MCP_MODEL.
   - ANTHROPIC_API_KEY / OPENAI_API_KEY / A11Y_MCP_API_KEY = chave (so do ambiente, nunca registrada)
   - A11Y_MCP_BASE_URL = endereco de um servidor compativel com OpenAI (xAI, OpenRouter, LM Studio, Ollama /v1...)
   - OLLAMA_HOST       = endereco do Ollama nativo (padrao http://localhost:11434)
2. O modelo do proprio cliente via MCP sampling, se o cliente ainda oferecer (bonus; nao conte com ele).
Imagens (visao) sao aceitas nos dois caminhos; modelo sem visao simplesmente nao as usa bem - isso e da sua escolha.
"""

from __future__ import annotations

import base64
import json
import logging
import os
from typing import Any

import httpx

from a11y.patience import patient

logger = logging.getLogger(__name__)

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
OPENAI_BASE = "https://api.openai.com/v1"
OLLAMA_DEFAULT_HOST = "http://localhost:11434"
BACKEND_TIMEOUT_S = 120.0  # so a 1a espera; se estourar, o mesmo pedido e' repetido com 3x, 9x, 27x...
BACKENDS = ("anthropic", "openai", "openai-compatible", "ollama")

NO_MODEL_HELP = (
    "Nenhum modelo disponivel: defina A11Y_MCP_MODEL e a chave do provedor (ANTHROPIC_API_KEY, OPENAI_API_KEY, "
    "A11Y_MCP_BASE_URL+A11Y_MCP_API_KEY para compativeis com OpenAI, ou A11Y_MCP_BACKEND=ollama). "
    "O cliente tambem nao oferece sampling."
)


async def _http_post(url: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    """Chamada ao provedor. Se demorar, repete o MESMO pedido com mais tempo (regra: nenhum relogio fixo mata trabalho em andamento)."""

    async def once(timeout: float) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, dict) else {}

    return await patient(once, BACKEND_TIMEOUT_S, attempts=6)  # 2 min, 6, 18, 54 min...: quem encerra e' o cancelamento


def configured_backend() -> str | None:
    """Backend configurado no ambiente (None = nenhum). Escolher o backend e configuracao, nao julgamento."""
    explicit = os.environ.get("A11Y_MCP_BACKEND", "").strip().lower()
    if explicit in BACKENDS:
        return explicit
    if explicit:
        logger.warning("A11Y_MCP_BACKEND invalido: %r (use %s)", explicit, ", ".join(BACKENDS))
        return None
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("A11Y_MCP_BASE_URL"):
        return "openai-compatible"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("OLLAMA_HOST"):
        return "ollama"
    return None


def backend_status() -> dict[str, Any]:
    """Estado do modelo de apoio para diagnostico (nunca inclui chaves)."""
    backend = configured_backend()
    model = os.environ.get("A11Y_MCP_MODEL") or None
    return {
        "backend": backend,
        "model": model, "model_fast": os.environ.get("A11Y_MCP_MODEL_FAST") or None,
        "ready": bool(backend and model),
        "problem": None if (backend and model) else (
            "defina A11Y_MCP_MODEL" if backend else "nenhum backend configurado"
        ),
    }


def _b64(images: list[bytes] | None) -> list[str]:
    return [base64.b64encode(i).decode() for i in (images or [])]


def _ollama_host() -> str | None:
    raw = os.environ.get("OLLAMA_HOST", "").strip()
    if not raw:
        return OLLAMA_DEFAULT_HOST
    return _base_url(raw if raw.startswith(("http://", "https://")) else f"http://{raw}")


def _base_url(raw: str) -> str | None:
    raw = raw.strip().rstrip("/")
    return raw if raw.startswith(("http://", "https://")) else None


def _model_for(tier: str) -> str | None:
    """Roteamento por PROPOSITO da chamada (economia com qualidade): leve -> modelo barato, se a pessoa configurou um."""
    if tier == "fast":
        return os.environ.get("A11Y_MCP_MODEL_FAST") or os.environ.get("A11Y_MCP_MODEL")
    return os.environ.get("A11Y_MCP_MODEL")


async def _ask_backend(prompt: str, max_tokens: int, images: list[bytes] | None, tier: str = "main") -> str | None:
    backend = configured_backend()
    model = _model_for(tier)
    if not backend:
        return None
    if not model:
        logger.warning("backend %s sem A11Y_MCP_MODEL: nao ha modelo padrao, defina o seu", backend)
        return None
    pics = _b64(images)
    try:
        if backend == "anthropic":
            key = os.environ.get("ANTHROPIC_API_KEY")
            if not key:
                logger.warning("backend anthropic sem ANTHROPIC_API_KEY")
                return None
            content: list[dict[str, Any]] = [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": p}} for p in pics
            ]
            content.append({"type": "text", "text": prompt})
            data = await _http_post(
                ANTHROPIC_URL,
                {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                {"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": content}]},
            )
            return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text") or None
        if backend in ("openai", "openai-compatible"):
            base = _base_url(os.environ.get("A11Y_MCP_BASE_URL", "")) if backend == "openai-compatible" else OPENAI_BASE
            if not base:
                logger.warning("backend openai-compatible exige A11Y_MCP_BASE_URL http(s)")
                return None
            key = os.environ.get("A11Y_MCP_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
            parts: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
            parts += [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{p}"}} for p in pics]
            headers = {"content-type": "application/json"}
            if key:
                headers["authorization"] = f"Bearer {key}"
            data = await _http_post(
                f"{base}/chat/completions", headers,
                {"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": parts if pics else prompt}]},
            )
            choices = data.get("choices") or [{}]
            return str(choices[0].get("message", {}).get("content") or "") or None
        if backend == "ollama":
            host = _ollama_host()
            if not host:
                return None
            msg: dict[str, Any] = {"role": "user", "content": prompt}
            if pics:
                msg["images"] = pics
            data = await _http_post(
                f"{host}/api/chat", {"content-type": "application/json"},
                {"model": model, "stream": False, "options": {"num_predict": max_tokens}, "messages": [msg]},
            )
            return str(data.get("message", {}).get("content", "")) or None
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("backend %s falhou: %s", backend, type(e).__name__)  # nunca loga chave nem corpo
    return None


async def _ask_client(ctx: Any, prompt: str, max_tokens: int, images: list[bytes] | None) -> str | None:
    try:
        from mcp.types import ImageContent, SamplingMessage, TextContent

        messages = [
            SamplingMessage(role="user", content=ImageContent(type="image", data=p, mimeType="image/jpeg"))
            for p in _b64(images)
        ]
        messages.append(SamplingMessage(role="user", content=TextContent(type="text", text=prompt)))
        result = await ctx.session.create_message(messages=messages, max_tokens=max_tokens)
        content = result.content
        return content.text if isinstance(content, TextContent) else None
    except Exception:  # noqa: BLE001 - cliente sem sampling/erro: quem chama decide o plano B
        return None


async def ask_model(
    ctx: Any, prompt: str, max_tokens: int = 800, images: list[bytes] | None = None, tier: str = "main"
) -> str | None:
    """Pergunta ao modelo: 1) provedor configurado (direto), 2) sampling do cliente. None = nenhum respondeu.
    tier: main (julgamento pesado) | fast (tarefa leve; usa A11Y_MCP_MODEL_FAST se a pessoa configurou)."""
    if configured_backend() is not None:
        reply = await _ask_backend(prompt, max_tokens, images, tier)
        if reply is not None:
            return reply
    if ctx is not None:
        return await _ask_client(ctx, prompt, max_tokens, images)
    return None


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
