## 🚀 Quick Start - Accessibility MCP em 5 minutos

### 1️⃣ Instalar

```powershell
cd c:\mcp
python -m pip install -r requirements.txt      # ou: uv sync
python -m playwright install chromium          # uma vez (auditoria no navegador)
python setup.py                                # registra no Claude Desktop e Cursor
```

### 2️⃣ Reiniciar o Claude Desktop / Cursor

Feche por completo e abra de novo. O servidor aparece como **accessibility**.

### 3️⃣ Usar

```
Você:   como faço um modal acessível?
Claude: [a11y_find escolhe os guias/exemplos → a11y_get_example traz o código]

Você:   audita https://meusite.com em WCAG AA
Claude: [a11y_audit → violações por impacto, com o trecho de HTML e a correção]

Você:   o foco do teclado nessa página está certo?
Claude: [a11y_tab_order → ordem, nomes e indicador de foco de cada parada]

Você:   testa o cadastro como um usuário só de teclado
Claude: [a11y_open persona=keyboard → a11y_dossier → a11y_reach/a11y_act press Tab/Enter…
         relata onde travou, quantos Tab foram, o que foi anunciado — e o que NÃO conseguiu verificar]

Você:   esse campo com várias opções é o quê? e esse "dropdown" do menu?
Claude: [a11y_dossier + a11y_act: decide pelo comportamento e pelo contexto do site
         (combobox? lista de seleção? menu de navegação?) e propõe a correção sem mudar o visual]

Você:   essa fonte e esse espaçamento estão bons?
Claude: [a11y_design_tokens mede a escala do site → propõe dentro dela → a11y_preview_css + a11y_screenshot
         para mostrar antes/depois, sem tocar no site]

Você:   #767676 sobre #ffffff passa no AA?
Claude: [a11y_contrast → razão e aprovação para texto normal/grande e componentes]
```

O que o automático não cobre (teclado de ponta a ponta, leitor de tela, toque) o Claude lembra de testar à mão, seguindo o guia `nvda-testing-guide`.

### 🧠 Cliente sem sampling? Configure um modelo de apoio

`a11y_find` pede ao modelo do cliente (MCP sampling) que escolha os guias. Se o cliente não suporta, o servidor usa um modelo do ambiente (em `"env"` na entrada do servidor no JSON):

```json
"env": { "ANTHROPIC_API_KEY": "sk-ant-..." }
```

ou, para Ollama: `"env": { "SKILLS_MCP_BACKEND": "ollama", "SKILLS_MCP_MODEL": "llama3" }`.
Sem nenhum modelo, `a11y_find` devolve o catálogo e o próprio Claude escolhe. As demais variáveis estão no `README.md`.

### ⚙️ Configuração manual

```json
// %APPDATA%\Claude\claude_desktop_config.json  (ou ~/.cursor/mcp.json)
{
  "mcpServers": {
    "accessibility": {
      "command": "uv",
      "args": ["--directory", "c:\\mcp", "run", "mcp_server.py"]
    }
  }
}
```

### 🆘 Se não funcionar

```bash
python c:\mcp\test.py          # confere dependências, conteúdo embutido e inicialização
python c:\mcp\mcp_server.py    # roda o servidor e mostra o log no stderr
```

Auditoria falhando com "Chromium indisponível": `python -m playwright install chromium`.
