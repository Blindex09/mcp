"""Resolucao automatica de modelo por provedor: com a chave, o servidor decide sozinho; sem chave, nao ha o que decidir.

Nada de tabela ou regra de "qual modelo e bom" no codigo. Nesta ordem, a primeira que existir vale:

1. Escolha explicita da pessoa (env A11Y_MCP_MODEL / A11Y_MCP_MODEL_FAST) - sempre vence.
2. Escolha ja feita antes (guardada como aprendizado, a11y/learn.py, escopo "modelo") - nao pergunta de novo.
3. Roteador nativo do proprio provedor - um FATO que o provedor documenta (gpt-5-auto na OpenAI; openrouter/auto
   quando o endereco configurado e literalmente o da OpenRouter): delegacao ao produto deles, nunca julgamento nosso.
4. Catalogo real da conta (busca ao vivo no provedor) mais a escolha por SIGNIFICADO de um modelo: como ainda nao ha
   modelo do servidor para perguntar, quem escolhe e o modelo do CLIENTE (MCP sampling), lendo os nomes reais e a
   finalidade do servidor. A resposta so vale se for literalmente um nome do catalogo (fato objetivo); a escolha fica
   guardada, entao isso acontece uma vez por provedor, nao a cada chamada.

Sem nenhuma das quatro (sem chave, ou cliente sem sampling): devolve o catalogo real para quem chamou mostrar a
pessoa e perguntar - nunca um palpite silencioso.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import httpx

from accessibility_mcp.a11y import learn
from accessibility_mcp.a11y.patience import patient

MODEL_SCOPE = "modelo"  # escopo de aprendizado (a11y/learn.py) reservado para a escolha de modelo por provedor
CATALOG_TIMEOUT_S = 20.0
CHOICE_TOKENS = 200

OPENAI_NATIVE_AUTO = "gpt-5-auto"  # roteador nativo da propria OpenAI (openai.com/index/introducing-gpt-5-5)
OPENROUTER_NATIVE_AUTO = "openrouter/auto"  # roteador nativo da propria OpenRouter
OPENROUTER_HOST = "openrouter.ai"


@dataclass(frozen=True)
class Resolution:
    model: str | None
    source: str  # pessoa | aprendido | nativo | escolhido-pelo-modelo | sem-escolha
    catalog: list[str] = field(default_factory=list)


def native_auto(backend: str, base_url: str | None) -> str | None:
    """Roteador nativo do provedor, quando existe. Fato documentado por eles, nao uma opiniao nossa sobre qualidade."""
    if backend == "openai":
        return OPENAI_NATIVE_AUTO
    if backend == "openai-compatible" and base_url and (urlparse(base_url).hostname or "").lower() == OPENROUTER_HOST:
        return OPENROUTER_NATIVE_AUTO
    return None


def _topic(backend: str, role: str) -> str:
    """main usa o topico historico (so o backend); outros papeis (vision, write, ...) tem o seu proprio, e caem
    para o de main quando nao tem escolha guardada (ver llm._resolve_model) - a pessoa so precisa nomear os
    papeis que quer separar."""
    return backend if role == "main" else f"{backend}:{role}"


def persisted(backend: str, role: str = "main") -> str | None:
    """Escolha guardada de uma resolucao ou de uma preferencia da pessoa para este PAPEL (aprendizado, nunca refeita a toa)."""
    topic = _topic(backend, role)
    for e in learn.load_all():
        if e.get("scope") == MODEL_SCOPE and e.get("topic") == topic:
            return str(e["learning"]) or None
    return None


def remember(backend: str, model: str, role: str = "main") -> None:
    learn.remember(MODEL_SCOPE, _topic(backend, role), model)


async def _get(url: str, headers: dict[str, str]) -> dict[str, Any] | None:
    async def once(timeout: float) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, dict) else {}

    try:
        return await patient(once, CATALOG_TIMEOUT_S, attempts=2)
    except (httpx.HTTPError, ValueError):
        return None


async def fetch_catalog(backend: str, base_url: str | None, key_env: dict[str, str]) -> list[str] | None:
    """Nomes de modelo REAIS que esta conta enxerga, buscados ao vivo no provedor. None = nao deu para buscar."""
    if backend == "anthropic":
        key = key_env.get("ANTHROPIC_API_KEY")
        if not key:
            return None
        data = await _get(
            "https://api.anthropic.com/v1/models?limit=1000",
            {"x-api-key": key, "anthropic-version": "2023-06-01"},
        )
        if data is None:
            return None
        return [str(m["id"]) for m in data.get("data", []) if m.get("id")]
    if backend in ("openai", "openai-compatible"):
        base = base_url if backend == "openai-compatible" else "https://api.openai.com/v1"
        if not base:
            return None
        key = key_env.get("A11Y_MCP_API_KEY") or key_env.get("OPENAI_API_KEY") or ""
        headers = {"authorization": f"Bearer {key}"} if key else {}
        data = await _get(f"{base.rstrip('/')}/models", headers)
        if data is None:
            return None
        return [str(m["id"]) for m in data.get("data", []) if m.get("id")]
    if backend == "ollama":
        host = key_env.get("_ollama_host") or ""
        if not host:
            return None
        headers = {"authorization": f"Bearer {key_env['OLLAMA_API_KEY']}"} if key_env.get("OLLAMA_API_KEY") else {}
        data = await _get(f"{host.rstrip('/')}/api/tags", headers)
        if data is None:
            return None
        return [str(m.get("model") or m.get("name")) for m in data.get("models", []) if m.get("model") or m.get("name")]
    return None


async def _ask_client_to_pick(ctx: Any, catalog: list[str]) -> str | None:
    from accessibility_mcp.llm import ask_client, extract_json

    prompt = (
        "Isto escolhe, uma unica vez, qual modelo desta lista o servidor MCP de acessibilidade vai usar para testar "
        "paginas como um usuario faria, revisar componentes e escrever relatorios: precisa de raciocinio forte e, "
        "quando a chamada trouxer uma captura de tela, entender imagens. Escolha pelo NOME o que atende melhor; "
        "nao ha regra fixa, julgue pelo que voce sabe de cada um.\n\n"
        f"MODELOS DISPONIVEIS NESTA CONTA:\n{chr(10).join(catalog)}\n\n"
        'Responda SOMENTE com JSON: {"model": "<um nome exatamente como na lista>"}'
    )
    raw = await ask_client(ctx, prompt, CHOICE_TOKENS)
    data = extract_json(raw, "object")
    chosen = data.get("model") if isinstance(data, dict) else None
    return str(chosen) if isinstance(chosen, str) and chosen in catalog else None


async def resolve(ctx: Any, backend: str, base_url: str | None, key_env: dict[str, str]) -> Resolution:
    """A escolha, na ordem descrita no topo do modulo. Nunca lanca por falha de rede; devolve sem-escolha."""
    if (choice := persisted(backend)) is not None:
        return Resolution(choice, "aprendido")
    if (native := native_auto(backend, base_url)) is not None:
        remember(backend, native)
        return Resolution(native, "nativo")
    catalog = await fetch_catalog(backend, base_url, key_env)
    if not catalog:
        return Resolution(None, "sem-escolha")
    if ctx is not None and (chosen := await _ask_client_to_pick(ctx, catalog)) is not None:
        remember(backend, chosen)
        return Resolution(chosen, "escolhido-pelo-modelo", catalog)
    return Resolution(None, "sem-escolha", catalog)
