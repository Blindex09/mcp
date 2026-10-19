## Quick Start - Accessibility MCP em 5 minutos

O servidor **não chama modelo e não precisa de chave**: o modelo é o do cliente que você usa (Claude Code, Codex, VS Code, Cursor, Claude Desktop…).

### 1. Instalar

O Playwright e o Chromium são instalados sozinhos na primeira vez (alguns minutos; `a11y_status` mostra o andamento).

```powershell
cd "C:\projetos IA\mcp"
python -m pip install -r requirements.txt      # ou: uv sync
python scripts/setup.py                        # cadastra no Claude Desktop, Claude Code, Codex e Cursor (e mostra o VS Code)
```

### 2. Reiniciar o cliente

Feche por completo e abra de novo. O servidor aparece como `accessibility`. Conferir: no Claude Code, `/mcp`; no Codex, `codex mcp list`; no VS Code, `MCP: List Servers`.

Cadastro manual, se preferir:

| Cliente | Comando ou arquivo |
|---|---|
| Claude Code | `claude mcp add --transport stdio --scope user accessibility -- uv --directory "C:\projetos IA\mcp" run mcp_server.py` |
| Codex | `codex mcp add accessibility -- uv --directory "C:\projetos IA\mcp" run mcp_server.py` |
| VS Code | `MCP: Add Server`, `Command (stdio)`, o mesmo comando, nome `accessibility` (ou `mcp.json` com a chave `servers`) |
| Cursor / Claude Desktop | JSON com a chave `mcpServers`: `{"accessibility": {"command": "uv", "args": ["--directory", "C:\\projetos IA\\mcp", "run", "mcp_server.py"]}}` |

### 3. Usar

```
Você:   como faço um modal acessível?
Claude: [a11y_list_content, escolhe pelo sentido, depois a11y_get_example traz o código]

Você:   audita https://meusite.com em WCAG AA
Claude: [a11y_audit, depois violações por impacto, com o trecho de HTML e a correção]

Você:   testa o cadastro como um usuário só de teclado
Claude: [a11y_open persona=keyboard, depois a11y_dossier, a11y_reach/a11y_act, a11y_probe…
         relata onde travou, quantos Tab foram, o que foi anunciado, e o que NÃO conseguiu verificar]

Você:   esse campo com várias opções é o quê? e esse "dropdown" do menu?
Claude: [a11y_dossier + a11y_act + a11y_probe: decide pelo comportamento e pelo contexto do site, e propõe a correção sem mudar o visual]

Você:   revisa a estrutura da página inteira
Claude: [a11y_page_map, depois fatos de todo o conteúdo, depois julga com o guia page-structure-review, depois a11y_coverage mostra o que ficou de fora]

Você:   varre o site todo (até 20 páginas)
Claude: [a11y_crawl: só fatos, respeitando o robots.txt; depois revisa as páginas mais importantes]

Você:   compara essa página no Chrome, no Firefox e no WebKit
Claude: [a11y_compare_browsers: o que a árvore, o axe e o foco têm de diferente em cada navegador]
```

O que o automático não cobre (leitor de tela de verdade, toque em aparelho) o Claude diz que não foi verificado e orienta a testar à mão, seguindo o guia `nvda-testing-guide`.

### Fluxos prontos

Para não precisar explicar o método toda vez, o servidor traz fluxos prontos. No Claude Code, digite `/mcp__accessibility__a11y_review` (ou `a11y_walkthrough`, `a11y_component`, `a11y_site_scan`, `a11y_compare_runs`, `a11y_write_accessible_code`); no VS Code, `/accessibility.a11y_review`. Em qualquer cliente, peça "use a ferramenta a11y_workflow com name a11y_review e url https://meusite.com". O fluxo diz ao modelo do cliente quais guias ler, quais ferramentas e sondas usar, o que pode e não pode afirmar e como entregar o relatório.

`a11y_report` guarda a execução; `a11y_runs`, `a11y_export` e `a11y_diff` listam, exportam (EARL, SARIF) e comparam execuções para ver se uma correção funcionou. `a11y_learn` guarda uma lição para as próximas sessões.

### Se não funcionar

```bash
python "C:\projetos IA\mcp\scripts\test.py"          # confere dependências, conteúdo embutido e inicialização
python "C:\projetos IA\mcp\mcp_server.py"    # roda o servidor e mostra o log no stderr
```

Navegador não sobe: veja `a11y_status`. Se a instalação automática estiver desligada (`A11Y_MCP_AUTO_INSTALL=0`), rode `python -m playwright install chromium`.
