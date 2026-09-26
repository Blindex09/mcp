# ♿ Accessibility MCP Server

Servidor MCP **somente de acessibilidade** (web, mobile e interfaces de IA/agentes) para Claude Desktop, VS Code, Cursor e qualquer cliente MCP.

Ele dá à IA quatro coisas: **conhecimento** (guias e exemplos de acessibilidade), **escolha inteligente** do que ler para cada tarefa, **medição** de uma página (axe-core, foco, contraste) e — o mais importante — **teste como usuário de verdade**: uma sessão de navegador que a IA opera (só teclado, leitor de tela, zoom, celular…) para descobrir o que o site realmente faz, porque *verde no audit não significa acessível*.

## O que faz

- 📚 **Base de conhecimento embutida** (`a11y/content/`): 27 guias (WCAG 2.2, ARIA, NVDA/VoiceOver/TalkBack, checklist de auditoria, IA conversacional acessível, mobile, frameworks, XR…), 42 exemplos de componentes acessíveis (modal, abas, combobox, treegrid, chat de IA…) e o template React (10 arquivos) de chat/agente acessível.
- 🧠 **Escolha pelo modelo**: `a11y_find` recebe a tarefa em linguagem natural, em qualquer idioma, e o modelo escolhe os guias e exemplos certos pelo sentido. Nada de palavra-chave, regex ou ranking lexical.
- 🔬 **Medição de fatos**: contraste WCAG, auditoria axe-core num navegador real, árvore de acessibilidade e ordem de foco por teclado.

## Ferramentas (25)

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
| `a11y_open(url \| html, persona, browser)` | Abre a sessão em `chromium` (padrão, o mais preciso), `firefox` ou `webkit` (baixados sozinhos na primeira vez; o resultado lista os limites de cada um). Personas **impostas pelo servidor**: `keyboard` e `screen_reader` não têm mouse; `screen_reader` também não vê a tela; `low_vision` = 320 px (zoom 400%); `mobile_touch`; `reduced_motion`; `forced_colors` |
| `a11y_dossier(scope, max_elements)` | **Fatos** de cada elemento que o **navegador** aponta como focável ou clicável (inclui quem só tem `addEventListener`): papel e nome **calculados pelo Chromium**, foco, clicável, estados, opções/popup, landmark/heading, estilo. Não classifica: o modelo decide se é campo de texto, combobox, menu, acordeão… |
| `a11y_act(action, target, value)` | Faz o que o usuário faz (click, hover, focus, select, press, type, wait) e devolve o **efeito**: foco antes/depois, linhas da árvore que apareceram/sumiram, o que foi anunciado, URL, diálogos/popups |
| `a11y_reach(target)` | Quantos Tab até chegar ao elemento e o caminho do foco (inalcançável? em loop?) |
| `a11y_focus_style(target)` | Fatos do que o `:focus` muda no elemento (medido pelo Chromium sem disparar eventos); se é um indicador suficiente é julgamento do modelo |
| `a11y_announce(target)` | O que um leitor de tela receberia para o elemento |
| `a11y_observe()` | Estado atual: foco, árvore de acessibilidade, anúncios recentes |
| `a11y_stress(kind)` | `reflow_320` (WCAG 1.4.10) e `text_spacing` (1.4.12): fatos de overflow e texto cortado |
| `a11y_design_tokens()` | A **linguagem de design real** do site: estilos de texto em uso, escala de tamanhos, cores, espaçamentos, raios, variáveis `:root` |
| `a11y_screenshot(target, full_page)` | Captura JPEG da página ou de um elemento (recusada para `screen_reader`) |
| `a11y_preview_css(target, css, revert)` | Testa uma mudança de design **temporariamente** (só na sessão; o site não é alterado) |
| `a11y_close()` | Encerra a sessão; se um teste autônomo está rodando, **o interrompe** e devolve o relatório parcial. Expira após 10 min parada |

Fluxo: `a11y_open` → `a11y_dossier` → `a11y_act`/`a11y_reach` para provar o comportamento → julgar (o que é, onde o
usuário trava, o que melhorar mantendo o design) → `a11y_preview_css` + `a11y_screenshot` para testar a proposta.
O relatório deve listar o **que não foi verificado** (leitores de tela reais, dispositivos reais, fluxos não testados).

### Usuário autônomo (o modelo opera a página sozinho)

| Ferramenta | O que faz |
|---|---|
| `a11y_walkthrough(task, url \| html, persona, max_steps, vision)` | Um modelo faz o papel de uma pessoa **da persona** tentando cumprir a tarefa, passo a passo, **vendo a tela** (screenshot) e a árvore de acessibilidade, e escreve um relatório em texto corrido: o que aconteceu, onde travou, achados por gravidade com a correção que mantém o design e o que **não** foi verificado |
| `a11y_review(focus, url \| html, persona, max_steps, vision)` | Revisão de UX: o modelo explora, **prova o comportamento** de cada componente importante, decide o que ele realmente é naquele site e revisa tipografia/espaçamento contra a linguagem de design do próprio site |
| `a11y_status()` | Prontidão: navegador instalado/instalando e modelo configurado (nunca mostra chaves) |

O modelo decide **tudo que é julgamento**; o servidor só impõe limites: persona (teclado e leitor de tela sem mouse), formato da
ação, no máximo 60 passos, tempo, parada se repetir a mesma ação no mesmo estado, e fechamento da sessão. Precisa do modelo do servidor
(veja abaixo) ou de um cliente com sampling. Cada passo é narrado; `a11y_close` interrompe sem perder o progresso.

### Vários navegadores

| Ferramenta | O que faz |
|---|---|
| `a11y_compare_browsers(url \| html, browsers)` | A mesma página em 2+ navegadores, lado a lado, **só fatos**: diferenças na árvore de acessibilidade, violações do axe que aparecem em um só e ordem de foco por navegador. Se a diferença é bug da página ou modo de o navegador expor, é julgamento do modelo (guia `cross-browser-a11y`) |

Todas as medições (`a11y_audit`, `a11y_aria_snapshot`, `a11y_tab_order`), a sessão e os testes autônomos aceitam `browser`.

| Recurso | Chromium | Firefox / WebKit |
|---|---|---|
| Papel/nome/estado | calculados pelo navegador (CDP) | aria snapshot do Playwright, elemento a elemento |
| Focável | árvore de acessibilidade | `tabIndex` calculado pelo navegador |
| Clicável (inclui só `addEventListener`) | sim (`DOMSnapshot.isClickable`) | **não** (só `cursor: pointer`, sinal mais fraco) |
| `a11y_focus_style` | `:focus` forçado, sem eventos | foca de verdade (dispara focus/blur) |

Cada resultado diz qual navegador o produziu e o que ele não mede. Nenhum é leitor de tela real.

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

Toda decisão de sentido (que guia serve, o que uma tela mostra, qual o próximo passo de um usuário) é de um **modelo**; o servidor só
valida fatos objetivos (o nome devolvido existe no catálogo?). Não há palavra-chave, regex nem ranking lexical.

A especificação MCP de 2026-07-28 **descontinuou o sampling** (o servidor deve chamar o provedor direto). Por isso:

1. **Provedor configurado por ambiente (caminho principal)**, chamado direto, com suporte a imagens:

| Variável | Uso |
|---|---|
| `A11Y_MCP_MODEL` | **obrigatória**: id do modelo. Não há modelo padrão embutido; a escolha é sua |
| `ANTHROPIC_API_KEY` | ativa o provedor Anthropic |
| `OPENAI_API_KEY` | ativa o provedor OpenAI |
| `A11Y_MCP_BASE_URL` (+ `A11Y_MCP_API_KEY`) | qualquer servidor compatível com OpenAI (xAI, OpenRouter, LM Studio, Ollama `/v1`…) |
| `A11Y_MCP_BACKEND` | `anthropic` \| `openai` \| `openai-compatible` \| `ollama` (opcional; senão detecta pelo ambiente) |
| `OLLAMA_HOST` | Ollama nativo (padrão `http://localhost:11434`; use um modelo com visão para as capturas) |

Exemplo no JSON do cliente: `"env": {"ANTHROPIC_API_KEY": "...", "A11Y_MCP_MODEL": "<seu modelo>"}` na entrada do servidor.

2. **Sampling do cliente**, se ele ainda oferecer (bônus; o Claude Code não oferece).
3. Sem nenhum dos dois: `a11y_find` devolve o catálogo para o modelo que chamou escolher, e `a11y_walkthrough`/`a11y_review` explicam como configurar.
   As ferramentas de sessão (`a11y_open`, `a11y_dossier`, `a11y_act`…) funcionam sempre, porque aí o modelo do próprio cliente conduz.

As ferramentas de medição não usam modelo: reportam fatos, e interpretar e corrigir fica com quem chamou.
A auditoria completa (pesquisa, o que foi removido por ser heurística e o que ficou, com justificativa) está em `docs/AUDITORIA.md`.

## Instalação

```bash
cd c:\mcp
pip install -r requirements.txt            # ou: uv sync
python setup.py                            # registra no Claude Desktop e Cursor (entrada "accessibility")
```

O **Playwright e o navegador pedido (Chromium por padrão; Firefox/WebKit na primeira vez que forem usados) são instalados sozinhos** em segundo plano na primeira vez que o servidor sobe (leva alguns minutos e ~150 MB;
`a11y_status` mostra o andamento). Para desligar: `A11Y_MCP_AUTO_INSTALL=0` (aí rode `python -m playwright install chromium`).

Reinicie o Claude Desktop / Cursor. Para VS Code, o `setup.py` imprime o trecho para o `settings.json`. O `setup.ps1` faz tudo isso no Windows.
Dependências: `mcp>=1.2,<2` (o mcp 2.x renomeou o `FastMCP`), `playwright`. O `httpx` já vem com o `mcp`.

## Segurança

- Navegação só em `http://` e `https://` (nunca `file:`, `javascript:`, `chrome:`); na sessão, requisições de outros esquemas são abortadas, downloads recusados, diálogos JS dispensados (e registrados), popups fechados (e registrados).
- Uma sessão por vez, expira após 10 min parada; nenhum JavaScript arbitrário é exposto ao cliente; `a11y_preview_css` aceita só declarações (sem `url()`, `@` ou HTML).
- Personas são impostas pelo servidor (ex.: `keyboard` não tem mouse), não pela boa vontade do modelo.
- Não digite credenciais reais em páginas testadas; use contas de teste.
- Leitura de guias/exemplos só por nome do catálogo — texto do cliente nunca vira caminho de arquivo.
- Chave de API só do ambiente, fora de logs; URL base de provedor validada (só `http(s)`).

## Estrutura

```
c:\mcp\
├── mcp_server.py        ← servidor FastMCP (entrada)
├── llm.py               ← acesso ao modelo: provedores diretos (com visão) e sampling do cliente
├── a11y/
│   ├── tools.py         ← ferramentas de conhecimento/medição e os recursos MCP
│   ├── tools_ux.py      ← ferramentas de sessão: dossiê, ações, personas, design
│   ├── session.py       ← sessão de navegador persistente (personas impostas, descoberta pelo Chromium, efeitos, estresse)
│   ├── agent.py         ← usuário autônomo: o modelo decide, o harness impõe limites
│   ├── provisioning.py  ← instala Playwright e Chromium/Firefox/WebKit sozinho
│   ├── compare.py       ← mesma página em vários navegadores (fatos lado a lado)
│   ├── page_scripts.py + js/ ← scripts que coletam FATOS dentro da página (nunca classificam)
│   ├── audit.py         ← contraste, axe-core, árvore de acessibilidade, ordem de foco
│   ├── content_index.py ← catálogo dos guias/exemplos (leitura só por nome)
│   ├── content/         ← guias, exemplos, template React (origem: repo web-accessibility) + catalog.json (descrições escritas por IA)
│   └── vendor/          ← axe-core 4.12.1 (MPL-2.0)
├── docs/AUDITORIA.md    ← pesquisa, auditoria e próximos passos
├── tests/               ← testes com Chromium real (auditoria, sessão, agente, provedores)
├── setup.py / setup.ps1 / mcp.json / test.py
└── requirements.txt / pyproject.toml
```

Os guias e exemplos são editáveis em `a11y/content/`; o `SKILL.md` de lá explica como usar cada ferramenta.

## Desenvolvimento

```bash
python -m pytest -q          # inclui testes com navegador real (~1 min)
ruff check a11y llm.py mcp_server.py tests
mypy a11y llm.py mcp_server.py --ignore-missing-imports
```

Os testes nunca chamam modelo real: interceptam o HTTP e usam um cliente simulado.
