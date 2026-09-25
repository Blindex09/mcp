"""Fixtures compartilhadas."""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from mcp.types import TextContent

# Permite importar mcp_server, sampling e a11y a partir de tests/
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def no_real_model_backend(monkeypatch):
    """Nenhum teste pode chamar modelo de verdade por causa de variaveis do ambiente do dev."""
    for var in ("ANTHROPIC_API_KEY", "SKILLS_MCP_BACKEND", "SKILLS_MCP_MODEL", "OLLAMA_HOST"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture()
def fake_ctx():
    """Fabrica de ctx cujo modelo responde em sequencia; None = cliente sem sampling."""

    def make(*replies: str | None):
        queue = list(replies)
        prompts: list[str] = []

        async def create_message(messages, max_tokens):
            prompts.append(messages[0].content.text)
            reply = queue.pop(0)
            if reply is None:
                raise RuntimeError("sampling nao suportado")
            return SimpleNamespace(content=TextContent(type="text", text=reply))

        return SimpleNamespace(session=SimpleNamespace(create_message=create_message)), prompts

    return make
