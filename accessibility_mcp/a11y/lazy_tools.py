"""Ferramentas sob demanda: o cliente recebe so um punhado de ferramentas ao iniciar e as demais aparecem quando a conversa precisa delas.

Por que: as 60+ ferramentas somam ~95 KB de descricoes e esquemas. Carregar tudo no inicio engorda o contexto do modelo e atrasa a conversa.
Como: `tools/list` devolve o NUCLEO (abrir, fechar, estado) mais as que o modelo ja pediu. `a11y_find_tools(query)` procura nas demais, devolve nome,
descricao e esquema e as ATIVA (avisa o cliente com `tools/list_changed`). `a11y_call` chama qualquer ferramenta pelo nome, para clientes que nao
reagem a esse aviso. Nada e' removido: toda ferramenta continua registrada e chamavel. A11Y_MCP_LAZY_TOOLS=0 volta a listar tudo."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations

CORE = ("a11y_find_tools", "a11y_call", "a11y_open", "a11y_close", "a11y_status")
_ACTIVE: set[str] = set()
_STOP = {"a", "o", "de", "da", "do", "e", "the", "to", "of", "for", "and", "um", "uma", "para", "com"}


def enabled() -> bool:
    return os.environ.get("A11Y_MCP_LAZY_TOOLS", "1").strip().lower() not in ("0", "false", "no", "off")


def _words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2 and w not in _STOP]


def rank(query: str, tools: list[Any], limit: int = 6) -> list[Any]:
    """Nome exato primeiro; depois pontua palavras da busca no nome (peso 4) e na descricao (peso 1)."""
    wanted = [n.strip() for n in query.replace("select:", "").split(",") if n.strip()]
    by_name = {t.name: t for t in tools}
    if wanted and all(n in by_name for n in wanted):
        return [by_name[n] for n in wanted]
    terms = set(_words(query.replace("_", " ")))
    scored = []
    for tool in tools:
        name_words = set(_words(tool.name.replace("_", " ")))
        desc_words = set(_words(tool.description or ""))
        score = 4 * len(terms & name_words) + len(terms & desc_words) + (3 if query.strip().lower() in tool.name else 0)
        if score:
            scored.append((score, tool.name, tool))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [tool for _, _, tool in scored[:limit]]


def install(mcp: Any) -> None:
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False))
    async def a11y_find_tools(query: str, ctx: Context, limit: int = 6) -> str:
        """FIND AND LOAD ACCESSIBILITY TOOLS. Only a few tools are listed at start to keep things fast; this finds the others by what you want to do
        (e.g. "contrast", "nvda speech", "create report xlsx", "verify code", "tab order", "crawl site") or by exact names ("a11y_dossier,a11y_act").
        Returns each match with its description and input schema and ACTIVATES it: it appears in the tool list from now on. If your client does not refresh the
        list, call the tool through a11y_call(name, arguments) with the schema returned here."""
        everything = [t for t in await mcp.list_tools() if t.name not in CORE]
        found = rank(query, everything, max(1, min(limit, 12)))
        fresh = [t.name for t in found if t.name not in _ACTIVE]
        _ACTIVE.update(t.name for t in found)
        if fresh:
            try:
                await ctx.session.send_tool_list_changed()
            except Exception:  # noqa: BLE001,S110 - o cliente pode nao aceitar o aviso; a11y_call cobre esse caso
                pass
        return json.dumps({
            "ativadas": [t.name for t in found],
            "ferramentas": [{"name": t.name, "description": (t.description or "")[:1200], "input_schema": t.inputSchema} for t in found],
            "total_disponivel": len(everything),
            "dica": "Nada encontrado? Tente outra palavra (em ingles ou portugues) ou liste por nome." if not found else "Chame direto, ou por a11y_call(name, arguments).",
        }, ensure_ascii=False)

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True))
    async def a11y_call(name: str, arguments: dict[str, Any] | None = None) -> str:
        """CALL ANY ACCESSIBILITY TOOL BY NAME, even one that is not listed yet. Use it when a11y_find_tools returned the tool but your client did not refresh its list.
        arguments: the tool's own arguments as an object. The tool's own rules (approval, lint, persona) apply unchanged."""
        if name in ("a11y_call", "a11y_find_tools"):
            return json.dumps({"error": "Chame a11y_find_tools e a11y_call diretamente."}, ensure_ascii=False)
        try:
            result = await mcp.call_tool(name, arguments or {})
        except Exception as e:  # noqa: BLE001 - fronteira MCP com erro explicito
            return json.dumps({"error": f"{type(e).__name__}: {e}", "dica": "Confira o nome e os argumentos com a11y_find_tools."}, ensure_ascii=False)
        content = result[0] if isinstance(result, tuple) else result
        parts = [getattr(item, "text", None) for item in (content if isinstance(content, (list, tuple)) else [content])]
        return "\n".join(p for p in parts if p) or json.dumps(result, ensure_ascii=False, default=str)

    if not enabled():
        return
    full_list = mcp.list_tools

    async def lean_list() -> list[Any]:
        return [t for t in await full_list() if t.name in CORE or t.name in _ACTIVE]

    # o protocolo usa este; mcp.list_tools() continua devolvendo tudo (testes e a11y_find_tools dependem disso)
    mcp._mcp_server.list_tools()(lean_list)
