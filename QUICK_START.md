## 🚀 Quick Start - Skills MCP em 5 minutos

### 1️⃣ **Instalar & Ativar**

```powershell
cd c:\mcp
# Recomendado (uv)
uv sync
python setup.py

# Alternativa (pip)
python -m pip install -r requirements.txt
python setup.py
```

### 2️⃣ **Reiniciar Claude Desktop**

- Feche Claude Desktop completamente (Alt+F4)
- Abra novamente

### 3️⃣ **Usar as Skills**

#### No Chat do Claude Desktop:

```
Usuário: quais skills estão disponíveis?
Claude: [invoca list_categories / find_skills - o modelo acha pelo sentido]

Usuário: /invoke_skill agent-customization "quero configurar uma skill de MCP"
Claude: [retorna SKILL.md + contexto]

Usuário: me ajuda com refatoração de código
Claude: [invoca find_skills("refatoração de código") e depois invoke_skill]
```

#### Acessibilidade (a11y_*)

```
Usuário: audita https://meusite.com em WCAG AA
Claude: [invoca a11y_audit -> axe-core em Chromium headless]

Usuário: como faço um modal acessível?
Claude: [a11y_find escolhe os guias/exemplos; a11y_get_example traz o código]
```

Para a auditoria: `python -m playwright install chromium` (uma vez).

#### Primeira vez: classificar as skills

`classify_skills()` pede ao modelo (MCP sampling) que categorize as skills sem pasta de categoria.
Resultado em cache (`skills_classification.json`); só reclassifica o que mudou.

#### No VSCode/Cursor:

Mesma coisa - aparecem em "Available Tools" no chat.

### 📋 Exemplo de saída

```
✅ Skills MCP Server
├── 1300+ pastas descobertas
├── skills com SKILL.md carregadas
└── Todas registradas como ferramentas MCP
```

### ⚙️ Configuração manual (se precisar)

**Claude Desktop** (já feito automaticamente):
```json
// %APPDATA%\Claude\claude_desktop_config.json
{
  "mcpServers": {
    "skills": {
      "command": "uv",
      "args": ["--directory", "c:\\mcp", "run", "mcp_server.py"]
    }
  }
}
```

**Cursor** (já feito automaticamente):
```json
// ~/.cursor/mcp.json
{
  "mcpServers": {
    "skills": {
      "command": "uv",
      "args": ["--directory", "c:\\mcp", "run", "mcp_server.py"]
    }
  }
}
```

### 🆘 Se não funcionar

```bash
# Verifique dependências e skills
python c:\mcp\test.py

# Veja logs do servidor
uv --directory c:\mcp run mcp_server.py
```

---

**Criado:** 26 de março de 2026  
**Atualizado:** 25 de setembro de 2026  
**Status:** ✅ Pronto
