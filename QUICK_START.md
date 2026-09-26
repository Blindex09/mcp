## 🚀 Quick Start - Accessibility MCP em 5 minutos

### 1️⃣ Instalar

O Playwright e o Chromium são instalados sozinhos na primeira vez (alguns minutos; `a11y_status` mostra o andamento).

```powershell
cd c:\mcp
python -m pip install -r requirements.txt      # ou: uv sync
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

Você:   revisa a estrutura da página inteira (títulos, imagens, links, formulários, ordem de leitura)
Claude: [a11y_page_map → fatos de todo o conteúdo → julga com o guia page-structure-review → a11y_coverage mostra o que ficou de fora]

Você:   varre o site todo (até 20 páginas)
Claude: [a11y_crawl → axe por página e por regra, títulos repetidos, páginas sem h1/lang — só fatos, respeitando o robots.txt]

Você:   compara essa página no Chrome e no Firefox
Claude: [a11y_compare_browsers → o que a árvore, o axe e o foco têm de diferente em cada navegador]

Você:   #767676 sobre #ffffff passa no AA?
Claude: [a11y_contrast → razão e aprovação para texto normal/grande e componentes]
```

O que o automático não cobre (teclado de ponta a ponta, leitor de tela, toque) o Claude lembra de testar à mão, seguindo o guia `nvda-testing-guide`.

### 🧠 Dê um modelo ao servidor (para o usuário autônomo e o `a11y_find`)

A especificação MCP de 2026 descontinuou o sampling, então o servidor chama o provedor direto. Na entrada do servidor no JSON, em `"env"`:

```json
"env": { "ANTHROPIC_API_KEY": "sk-ant-...", "A11Y_MCP_MODEL": "<o modelo que você escolher>" }
```

Não há modelo padrão: `A11Y_MCP_MODEL` é sua escolha. Outros provedores (OpenAI, xAI/OpenRouter/LM Studio via `A11Y_MCP_BASE_URL`, Ollama)
estão no `README.md`. Confira com `a11y_status`. Sem modelo, as ferramentas de sessão (`a11y_open`, `a11y_dossier`, `a11y_act`…) continuam
funcionando com o modelo do próprio cliente; só `a11y_walkthrough`/`a11y_review` e a escolha automática do `a11y_find` precisam dele.

### 🤖 Deixe o servidor testar sozinho

```
Você:   simula uma pessoa só de teclado tentando se cadastrar em https://meusite.com
Claude: [a11y_walkthrough persona=keyboard → relatório com atritos, gravidade, correções e o que NÃO foi verificado]

Você:   revisa os componentes e o design dessa página
Claude: [a11y_review → prova o comportamento de cada componente e propõe dentro do design do site]
```

`a11y_close` interrompe um teste em andamento e devolve o relatório parcial.

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

Navegador não sobe: veja `a11y_status`. Se a instalação automática estiver desligada (`A11Y_MCP_AUTO_INSTALL=0`), rode `python -m playwright install chromium`.
