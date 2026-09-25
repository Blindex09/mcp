# ♿ Accessibility MCP Server

Servidor MCP **somente de acessibilidade** (web, mobile e interfaces de IA/agentes) para Claude Desktop, VS Code, Cursor e qualquer cliente MCP.

Ele dá à IA três coisas: **conhecimento** (guias e exemplos de acessibilidade), **escolha inteligente** do que ler para cada tarefa e **ferramentas de medição** que auditam uma página de verdade.

## O que faz

- 📚 **Base de conhecimento embutida** (`a11y/content/`): 24 guias (WCAG 2.2, ARIA, NVDA/VoiceOver/TalkBack, checklist de auditoria, IA conversacional acessível, mobile, frameworks, XR…), 42 exemplos de componentes acessíveis (modal, abas, combobox, treegrid, chat de IA…) e o template React (10 arquivos) de chat/agente acessível.
- 🧠 **Escolha pelo modelo**: `a11y_find` recebe a tarefa em linguagem natural, em qualquer idioma, e o modelo escolhe os guias e exemplos certos pelo sentido. Nada de palavra-chave, regex ou ranking lexical.
- 🔬 **Medição de fatos**: contraste WCAG, auditoria axe-core num navegador real, árvore de acessibilidade e ordem de foco por teclado.

## Ferramentas (9)

| Ferramenta | O que faz |
|---|---|
| `a11y_list_content` | Catálogo (resumo + seções) de todos os guias e exemplos |
| `a11y_find(task)` | O modelo escolhe guias/exemplos para a tarefa |
| `a11y_get_reference(name, section)` | Lê um guia inteiro ou só uma seção |
| `a11y_get_example(name)` | Devolve o código de um exemplo de componente |
| `a11y_get_template(name)` | Arquivo do template React de chat/agente acessível (`assets/…`) ou dos scripts de auditoria (`scripts/…`) |
| `a11y_contrast(foreground, background, size_px, bold)` | Razão de contraste WCAG e aprovação AA/AAA |
| `a11y_audit(url \| html, level)` | Auditoria axe-core (A/AA/AAA) em Chromium headless; violações por impacto |
| `a11y_aria_snapshot(url \| html)` | Árvore de acessibilidade: o que o leitor de tela recebe |
| `a11y_tab_order(url \| html, max_steps)` | Ordem de foco com Tab, nome acessível e indicador de foco |

Recursos MCP: `a11y://reference/{name}` e `a11y://example/{name}`.

Fluxo típico: `a11y_find("modal acessível")` → `a11y_get_reference` / `a11y_get_example` → implementar → `a11y_audit` + `a11y_tab_order` + `a11y_aria_snapshot` → testar à mão com teclado e leitor de tela (o automático cobre só parte do WCAG).

## Como o julgamento funciona

Toda decisão de "isso serve para aquilo" é de um modelo; o servidor só valida fatos objetivos (o nome devolvido existe no catálogo?). Quem responde:

1. **O modelo do próprio cliente**, via MCP sampling.
2. Senão, um **modelo de apoio** configurado por ambiente:

| Variável | Uso |
|---|---|
| `ANTHROPIC_API_KEY` | ativa o backend Anthropic (lida só do ambiente, nunca logada) |
| `SKILLS_MCP_BACKEND` | `anthropic` ou `ollama` (opcional; senão detecta pelo que estiver configurado) |
| `SKILLS_MCP_MODEL` | id do modelo (Anthropic: padrão `claude-haiku-4-5-20251001`; Ollama: obrigatório) |
| `OLLAMA_HOST` | endereço do Ollama (padrão `http://localhost:11434`) |

Exemplo no JSON do cliente: `"env": {"ANTHROPIC_API_KEY": "..."}` na entrada do servidor.

3. Sem nenhum dos dois, `a11y_find` avisa como configurar e devolve o catálogo para o modelo que chamou escolher. Não há plano B por palavra-chave.

As ferramentas de medição (`a11y_contrast`, `a11y_audit`, `a11y_aria_snapshot`, `a11y_tab_order`) não usam modelo: reportam fatos, e interpretar e corrigir fica com quem chamou.

## Instalação

```bash
cd c:\mcp
pip install -r requirements.txt            # ou: uv sync
python -m playwright install chromium      # uma vez; só para auditoria/árvore/foco no navegador
python setup.py                            # registra no Claude Desktop e Cursor (entrada "accessibility")
```

Reinicie o Claude Desktop / Cursor. Para VS Code, o `setup.py` imprime o trecho para o `settings.json`. O `setup.ps1` faz tudo isso no Windows.

Dependências: `mcp>=1.2,<2` (o mcp 2.x renomeou o `FastMCP`), `playwright`. O `httpx` já vem com o `mcp`.

## Segurança

- Navegação só em `http://` e `https://` (nunca `file:`, `javascript:`, `chrome:`), navegador descartável por chamada e timeout de 90 s.
- Leitura de guias/exemplos só por nome do catálogo — texto do cliente nunca vira caminho de arquivo.
- Chave de API só do ambiente, fora de logs.

## Estrutura

```
c:\mcp\
├── mcp_server.py        ← servidor FastMCP (entrada)
├── sampling.py          ← quem faz o julgamento: modelo do cliente ou modelo de apoio
├── a11y/
│   ├── tools.py         ← as 8 ferramentas e os recursos MCP
│   ├── audit.py         ← contraste, axe-core, árvore de acessibilidade, ordem de foco
│   ├── content_index.py ← catálogo dos guias/exemplos (leitura só por nome)
│   ├── content/         ← guias, exemplos, template React (origem: repo web-accessibility)
│   └── vendor/          ← axe-core 4.12.1 (MPL-2.0)
├── tests/               ← 44 testes (inclui navegador real)
├── setup.py / setup.ps1 / mcp.json / test.py
└── requirements.txt / pyproject.toml
```

Os guias e exemplos são editáveis em `a11y/content/`; o `SKILL.md` de lá explica como usar cada ferramenta.

## Desenvolvimento

```bash
python -m pytest -q          # 44 testes
ruff check a11y sampling.py mcp_server.py tests
mypy a11y sampling.py mcp_server.py --ignore-missing-imports
```

Os testes nunca chamam modelo real: interceptam o HTTP e usam um cliente simulado.
