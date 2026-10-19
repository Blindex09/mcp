"""Fixtures compartilhadas."""
import sys
from pathlib import Path

import pytest

# Permite importar mcp_server e a11y a partir de tests/
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def isolated_learning_home(monkeypatch, tmp_path):
    """Nenhum teste pode ler ou escrever nos aprendizados reais da pessoa."""
    monkeypatch.setenv("A11Y_MCP_HOME", str(tmp_path / "a11y-home"))
