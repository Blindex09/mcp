"""Fixtures compartilhadas."""
import os
import sys
from pathlib import Path

import pytest

# Permite importar mcp_server e a11y a partir de tests/
sys.path.insert(0, str(Path(__file__).parent.parent))

# As ferramentas de edicao de arquivos ficam desligadas por padrao; os testes delas precisam delas registradas.
os.environ.setdefault("A11Y_MCP_ALLOW_EDITS", "1")


@pytest.fixture(autouse=True)
def isolated_learning_home(monkeypatch, tmp_path):
    """Nenhum teste pode ler ou escrever nos aprendizados reais da pessoa."""
    monkeypatch.setenv("A11Y_MCP_HOME", str(tmp_path / "a11y-home"))
    monkeypatch.delenv("A11Y_MCP_DOCUMENTS_DIR", raising=False)  # documentos dos testes ficam na pasta temporaria, nunca na pasta dos relatorios
