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
Claude: [invoca list_skills - mostra 969 skills!]

Usuário: /invoke_skill agent-customization "quero configurar uma skill de MCP"
Claude: [retorna SKILL.md + contexto]

Usuário: me ajuda com refatoração de código
Claude: [invoca automaticamente skill_code_simplifier]
```

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
**Status:** ✅ Pronto
