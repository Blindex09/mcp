"""Ponte para o modelo do cliente (MCP sampling).

Todo julgamento do servidor - que skill serve a uma tarefa, em que categoria uma skill
cai - e feito pelo modelo, nunca por palavra-chave, regex ou ranking lexical. Este modulo
so entrega o pedido ao modelo e le a resposta; a unica validacao fixa e sobre fato
objetivo (o nome devolvido existe no catalogo?).
"""

from __future__ import annotations

import json
from typing import Any


async def ask_model(ctx: Any, prompt: str, max_tokens: int = 800) -> str | None:
    """Envia o prompt ao modelo do cliente. None = cliente sem sampling ou falha."""
    try:
        from mcp.types import SamplingMessage, TextContent

        result = await ctx.session.create_message(
            messages=[SamplingMessage(role="user", content=TextContent(type="text", text=prompt))],
            max_tokens=max_tokens,
        )
        content = result.content
        return content.text if isinstance(content, TextContent) else None
    except Exception:  # noqa: BLE001 - sem sampling/erro do cliente: quem chama decide o plano B
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
