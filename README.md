# ♿ Accessibility MCP Server

Servidor MCP **somente de acessibilidade** (web, mobile e interfaces de IA/agentes) para Claude Desktop, VS Code, Cursor e qualquer cliente MCP.

Ele dá à IA quatro coisas: **conhecimento** (guias e exemplos de acessibilidade), **escolha inteligente** do que ler para cada tarefa, **medição** de uma página (axe-core, foco, contraste) e — o mais importante — **teste como usuário de verdade**: uma sessão de navegador que a IA opera (só teclado, leitor de tela, zoom, celular…) para descobrir o que o site realmente faz, porque *verde no audit não significa acessível*.

## O que faz

- 📚 **Base de conhecimento embutida** (`a11y/content/`): 27 guias (WCAG 2.2, ARIA, NVDA/VoiceOver/TalkBack, checklist de auditoria, IA conversacional acessível, mobile, frameworks, XR…), 42 exemplos de componentes acessíveis (modal, abas, combobox, treegrid, chat de IA…) e o template React (10 arquivos) de chat/agente acessível.
- 🧠 **Escolha pelo modelo**: `a11y_find` recebe a tarefa em linguagem natural, em qualquer idioma, e o modelo escolhe os guias e exemplos certos pelo sentido. Nada de palavra-chave, regex ou ranking lexical.
- 🔬 **Medição de fatos**: contraste WCAG, auditoria axe-core num navegador real, árvore de acessibilidade e ordem de foco por teclado.

## Ferramentas (20)

### Conhecimento e escolha

| Ferramenta | O que faz |
|---|---|
| `a11y_list_content` | Catálogo compacto (resumo + seções) de todos os guias, exemplos, arquivos do template e scripts |
| `a11y_find(task)` | O modelo escolhe guias/exemplos para a tarefa |
| `a11y_get_reference(name, section)` | Lê um guia inteiro ou só uma seção |
| `a11y_get_example(name)` | Devolve o código de um exemplo de componente |
| `a11y_get_template(name)` | Arquivo do template React de chat/agente acessível (`assets/…`) ou dos scripts (`scripts/…`) |

### Testar como usuário (sessão de navegador persistente)

O modelo do cliente é quem **julga**; estas ferramentas **agem e devolvem fatos**. Guias que ensinam a julgar:
`component-identity-guide`, `ux-persona-testing`, `design-language-review`.

| Ferramenta | O que faz |
|---|---|
| `a11y_open(url \| html, persona)` | Abre a sessão. Personas **impostas pelo servidor**: `keyboard` e `screen_reader` não têm mouse; `screen_reader` também não vê a tela; `low_vision` = 320 px (zoom 400%); `mobile_touch`; `reduced_motion`; `forced_colors` |
| `a11y_dossier(scope, max_elements)` | **Fatos** de cada elemento interativo: papel declarado, nomes, estados, opções/popup, editável, landmark/heading, foco, estilo. Não classifica: o modelo decide se é campo de texto, combobox, menu, acordeão… |
| `a11y_act(action, target, value)` | Faz o que o usuário faz (click, hover, focus, select, press, type, wait) e devolve o **efeito**: foco antes/depois, linhas da árvore que apareceram/sumiram, o que foi anunciado, URL, diálogos/popups |
| `a11y_reach(target)` | Quantos Tab até chegar ao elemento e o caminho do foco (inalcançável? em loop?) |
| `a11y_announce(target)` | O que um leitor de tela receberia para o elemento |
| `a11y_observe()` | Estado atual: foco, árvore de acessibilidade, anúncios recentes |
| `a11y_stress(kind)` | `reflow_320` (WCAG 1.4.10) e `text_spacing` (1.4.12): fatos de overflow e texto cortado |
| `a11y_design_tokens()` | A **linguagem de design real** do site: estilos de texto em uso, escala de tamanhos, cores, espaçamentos, raios, variáveis `:root` |
| `a11y_screenshot(target, full_page)` | Captura JPEG da página ou de um elemento (recusada para `screen_reader`) |
| `a11y_preview_css(target, css, revert)` | Testa uma mudança de design **temporariamente** (só na sessão; o site não é alterado) |
| `a11y_close()` | Encerra a sessão (também expira após 10 min parada) |

Fluxo: `a11y_open` → `a11y_dossier` → `a11y_act`/`a11y_reach` para provar o comportamento → julgar (o que é, onde o
usuário trava, o que melhorar mantendo o design) → `a11y_preview_css` + `a11y_screenshot` para testar a proposta.
O relatório deve listar o **que não foi verificado** (leitores de tela reais, dispositivos reais, fluxos não testados).

### Medição rápida (sem sessão)

| Ferramenta | O que faz |
|---|---|
| `a11y_contrast(foreground, background, size_px, bold)` | Razão de contraste WCAG e aprovação AA/AAA |
| `a11y_audit(url \| html, level)` | Auditoria axe-core (A/AA/AAA) em Chromium headless; violações por impacto |
| `a11y_aria_snapshot(url \| html)` | Árvore de acessibilidade: o que o leitor de tela recebe |
| `a11y_tab_order(url \| html, max_steps)` | Ordem de foco com Tab, nome acessível e indicador de foco |

Recursos MCP: `a11y://reference/{name}` e `a11y://example/{name}`.

> **Verde não é acessível.** O axe e as demais medições só dizem que nenhuma regra conhecida falhou. Só o teste como
> usuário mostra se a tarefa é possível e como é a experiência. Use os dois, e diga sempre o que ficou sem verificar.

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

- Navegação só em `http://` e `https://` (nunca `file:`, `javascript:`, `chrome:`); na sessão, requisições de outros esquemas são abortadas, downloads recusados, diálogos JS dispensados (e registrados), popups fechados (e registrados).
- Uma sessão por vez, expira após 10 min parada; nenhum JavaScript arbitrário é exposto ao cliente; `a11y_preview_css` aceita só declarações (sem `url()`, `@` ou HTML).
- Personas são impostas pelo servidor (ex.: `keyboard` não tem mouse), não pela boa vontade do modelo.
- Não digite credenciais reais em páginas testadas; use contas de teste.
- Leitura de guias/exemplos só por nome do catálogo — texto do cliente nunca vira caminho de arquivo.
- Chave de API só do ambiente, fora de logs.

## Estrutura

```
c:\mcp\
├── mcp_server.py        ← servidor FastMCP (entrada)
├── sampling.py          ← quem faz o julgamento: modelo do cliente ou modelo de apoio
├── a11y/
│   ├── tools.py         ← ferramentas de conhecimento/medição e os recursos MCP
│   ├── tools_ux.py      ← ferramentas de sessão: dossiê, ações, personas, design
│   ├── session.py       ← sessão de navegador persistente (personas impostas, efeitos, estresse)
│   ├── page_scripts.py  ← scripts que coletam FATOS dentro da página (nunca classificam)
│   ├── audit.py         ← contraste, axe-core, árvore de acessibilidade, ordem de foco
│   ├── content_index.py ← catálogo dos guias/exemplos (leitura só por nome)
│   ├── content/         ← guias, exemplos, template React (origem: repo web-accessibility)
│   └── vendor/          ← axe-core 4.12.1 (MPL-2.0)
├── tests/               ← testes com Chromium real (auditoria e sessão de usuário)
├── setup.py / setup.ps1 / mcp.json / test.py
└── requirements.txt / pyproject.toml
```

Os guias e exemplos são editáveis em `a11y/content/`; o `SKILL.md` de lá explica como usar cada ferramenta.

## Desenvolvimento

```bash
python -m pytest -q          # inclui testes com navegador real (~1 min)
ruff check a11y sampling.py mcp_server.py tests
mypy a11y sampling.py mcp_server.py --ignore-missing-imports
```

Os testes nunca chamam modelo real: interceptam o HTTP e usam um cliente simulado.
