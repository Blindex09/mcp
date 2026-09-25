# 🎯 Skills MCP Server - Global Command Integration

> Expõe 1334 skills como ferramentas MCP globais em Claude Desktop, VSCode, Cursor e qualquer cliente compatível

## O que faz

- 📚 Descobre automaticamente todas as skills em `c:\skills` (ao vivo, sem rebuild)
- 🧠 **Todo julgamento é do modelo**: achar a skill certa e classificar em categorias é feito pelo modelo do cliente (MCP sampling) — sem palavra-chave, regex nem ranking lexical
- 🗂️ Categorias = pasta pai (fato estrutural) + classificação do modelo, com cache
- 🔧 Ferramentas MCP: `find_skills`, `classify_skills`, listagens por categoria, `invoke_skill` e as de acessibilidade (`a11y_*`)
- 🌐 Funciona em Claude Desktop, VSCode Copilot, Cursor, GitHub Copilot

## Arquitetura

```
c:\skills\                    ← 1300+ skills (cada uma com SKILL.md)
         ├── agent-customization/
         │   └── SKILL.md
         ├── react-best-practices/
         │   └── SKILL.md
         └── ...

c:\mcp\                       ← MCP Server
     ├── mcp_server.py          ← Servidor principal (24 tools, FastMCP)
     ├── sampling.py            ← Ponte para o modelo do cliente (MCP sampling)
     ├── a11y/                  ← Acessibilidade embutida (guias, exemplos, auditoria axe)
     ├── sync_cursor_rules.py   ← Sincroniza CLAUDE.md → Cursor User Rules
     ├── setup.py               ← Configura clientes automaticamente
     ├── pyproject.toml         ← Dependências (uv)
     ├── requirements.txt       ← Dependências (pip)
     └── README.md
```

## Acessibilidade turbinada (`a11y/`)

Incorpora a skill `web-accessibility` (referencias WCAG 2.2/ARIA/NVDA, ~50 exemplos de
componentes, template React de IA acessivel) e adiciona 8 ferramentas + recursos MCP:

| Ferramenta | O que faz |
|---|---|
| `a11y_list_content` | Catálogo (resumo + seções) dos guias e exemplos embutidos |
| `a11y_find` | O modelo escolhe guias/exemplos pela tarefa (sampling; sem sampling devolve o catálogo) |
| `a11y_get_reference` / `a11y_get_example` | Le um guia (opcional: so uma secao) ou um exemplo |
| `a11y_contrast` | Contraste WCAG entre duas cores |
| `a11y_audit` | Auditoria axe-core em URL http(s) ou HTML (Chromium headless) |
| `a11y_aria_snapshot` | Arvore de acessibilidade (o que o leitor de tela recebe) |
| `a11y_tab_order` | Ordem de foco por Tab, nome acessivel e indicador de foco |

Recursos: `a11y://reference/{name}` e `a11y://example/{name}`.
Auditoria exige `pip install playwright` + `python -m playwright install chromium`.
So navega em http/https, com timeout de 90 s. axe-core 4.12.1 (MPL-2.0) vendorizado em `a11y/vendor/`.

## Setup - 3 passos rápidos

### 1️⃣ Instalar dependências

```bash
# Recomendado (uv)
cd c:\mcp
uv sync

# Alternativa (pip)
pip install -r requirements.txt
```

### 2️⃣ Executar setup

```bash
cd c:\mcp
python setup.py
```

Ou usando o script PowerShell (recomendado para Windows):

```powershell
.\setup.ps1
```

Isso configura automaticamente:
- ✅ Claude Desktop (`%APPDATA%\Claude\claude_desktop_config.json`)
- ✅ Cursor (`~\.cursor\mcp.json`)
- 📝 Exibe instruções para VSCode

### 3️⃣ Reiniciar as aplicações

Reinicie Claude Desktop, Cursor e/ou VSCode para carregar o servidor.

---

## Ferramentas disponíveis (24 total)

### Por categoria (18 tools)

Cada tool lista **somente** as skills da categoria, com ícone e contagem.

| Tool | Categoria | Skills |
|------|-----------|--------|
| `list_accessibility_skills` | ♿ Acessibilidade | 9 |
| `list_ai_skills` | 🤖 AI & Agentes | 191 |
| `list_backend_skills` | ⚙️ Backend | 123 |
| `list_frontend_skills` | 🎨 Frontend | 122 |
| `list_devops_skills` | 🚀 DevOps & Cloud | 238 |
| `list_security_skills` | 🔒 Segurança | 89 |
| `list_testing_skills` | ✅ Testing & QA | 114 |
| `list_mobile_skills` | 📱 Mobile | 29 |
| `list_data_skills` | 📊 Data Engineering | 38 |
| `list_automation_skills` | 🔄 Automação | 171 |
| `list_architecture_skills` | 🏗️ Arquitetura | 79 |
| `list_language_skills` | 💻 Linguagens | 75 |
| `list_content_skills` | 📝 Conteúdo & Marketing | 97 |
| `list_gamedev_skills` | 🎮 GameDev | 8 |
| `list_business_skills` | 💼 Negócios & Startups | 53 |
| `list_web3_skills` | 🔗 Web3 & Blockchain | 8 |
| `list_health_skills` | 🏥 Saúde & Bem-estar | 17 |
| `list_legal_skills` | ⚖️ Jurídico & Legal | 9 |

> Todas aceitam parâmetro `limit: int = 0` (0 = retorna todas da categoria)

### Gerais (6 tools)

| Tool | O que faz |
|------|-----------|
| `invoke_skill(skill_name, params)` | Lê e retorna o SKILL.md completo de uma skill |
| `find_skills(task)` | **O modelo escolhe** as skills pela tarefa (sampling, em lotes; sem palavra-chave) |
| `classify_skills()` | O modelo classifica skills sem categoria; resultado em cache |
| `list_categories()` | Lista todas as categorias disponíveis com contagens |
| `list_all_skills(page, per_page)` | Lista todas as 1334 skills com paginação |
| `refresh_skills()` | Força reload imediato do cache (sem restart) |

---

## Exemplos de uso

```
# Listar skills de AI
list_ai_skills()
→ 🤖 AI & Agentes — 129 skills: agent-evaluation, agent-memory-mcp, ...

# Invocar uma skill específica
invoke_skill("react-best-practices", "como usar hooks corretamente?")
→ [retorna conteúdo completo do SKILL.md]

# Buscar por palavra
find_skills("subir containers com docker em produção")
→ [lista todas as skills com "docker" no nome]

# Ver todas as categorias
list_categories()
→ ♿ accessibility (8) | 🤖 ai (129) | ⚙️ backend (80) | ...
```

---

## Categorização e busca (por modelo)

Nada aqui usa regras de nome, palavra-chave, regex ou BM25:

- **Categoria** = pasta pai da skill (fato estrutural) + o que o modelo decidir em `classify_skills()`
  (resultado em `skills_classification.json`, só reclassifica o que mudou). O que o modelo não souber
  classificar fica `unclassified` — nada é chutado por nome.
- **Busca** = `find_skills(task)`: o modelo do cliente lê o catálogo (nome + descrição, em lotes) e escolhe
  pelo sentido; nomes inventados são descartados (única checagem fixa: o nome existe?).
- **Cliente sem sampling**: as ferramentas dizem isso e o modelo que chamou lê o catálogo
  (`list_all_skills`, `list_categories`) e decide; não existe plano B por palavra-chave.

---

## Estrutura de uma SKILL.md

```markdown
# Nome da Skill

Descrição brevíssima do que a skill faz.

## Uso

Como usar, exemplos, contexto...
```

O servidor lê o título (H1), extrai metadados e usa o conteúdo completo como contexto.

---

## Adicionar uma nova skill

1. Crie a pasta: `c:\skills\{nome-da-skill}\`
2. Crie o arquivo: `c:\skills\{nome-da-skill}\SKILL.md`
3. (Opcional) chame `classify_skills()` para o modelo categorizar a nova skill
4. O servidor já descobre a skill na próxima chamada (sem restart)

---

## Troubleshooting

### Skills não aparecem
```bash
python -c "from mcp_server import get_skills; print(len(get_skills()))"
```

### Claude Desktop / Cursor não conecta
1. Verifique `uv` no PATH: `uv --version`
2. Verifique o config: `%APPDATA%\Claude\claude_desktop_config.json`
3. Reinicie completamente o cliente

### VSCode não reconhece as tools
- Verifique `settings.json` (ver output do `python setup.py`)
- Reinicie o VSCode

---

## Slash Commands por Cliente

| Cliente | Sintaxe | Status |
|---------|---------|--------|
| Claude Desktop | `/ai`, `/backend`, `/oliverplan` | ✅ nativo |
| Claude Code | `/ai`, `/backend`, `/oliverplan` | ✅ nativo |
| VS Code Copilot | `/skills.ai`, `/skills.backend`, `/skills.oliverplan` | ✅ funciona |
| Cursor | não suporta MCP Prompts | ❌ use linguagem natural |

## Memória Global Dinâmica

| Cliente | Mecanismo | Como atualizar |
|---------|-----------|----------------|
| Claude Desktop / Code | `~/.claude/CLAUDE.md` | edite e salve |
| VS Code Copilot | `~/.claude/CLAUDE.md` (auto-detectado) | edite e salve |
| Cursor | `Cursor Settings → Rules` (SQLite) | `python c:/mcp/sync_cursor_rules.py` |

### Sincronizar regras com o Cursor

```bash
# Ver o que será gravado (dry-run)
python c:/mcp/sync_cursor_rules.py --show

# Sincronizar (feche o Cursor antes)
python c:/mcp/sync_cursor_rules.py

# Limpar
python c:/mcp/sync_cursor_rules.py --clear
```

---

## Links

- 📖 [MCP Spec 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25)
- 🚀 [FastMCP Docs](https://gofastmcp.com)
- 🧩 [VSCode MCP Guide](https://code.visualstudio.com/docs/copilot/chat/mcp-servers)
- 🖱️ [Cursor MCP Guide](https://cursor.com/docs/context/mcp)

---

**Criado:** 26 de março de 2026  
**Atualizado:** 29 de março de 2026  
**Versão:** 2.2  
**Skills:** 1334 | **Categorias:** 18 | **Tools MCP:** 24  
**Status:** ✅ Pronto para produção
