# Accessibility MCP Server

Servidor MCP somente de acessibilidade (web, mobile e interfaces de IA/agentes) para Claude Code, Codex, VS Code, Cursor, Claude Desktop e qualquer cliente MCP.

**O servidor não chama modelo e não precisa de chave de API.** O modelo é o do cliente que você usa; o servidor dá a ele quatro coisas: conhecimento (guias e exemplos de acessibilidade), medição de uma página (axe-core, foco, contraste), teste como usuário de verdade (uma sessão de navegador que o modelo do cliente opera: só teclado, leitor de tela, zoom, celular…) e fluxos prontos de trabalho (prompts do MCP). Verde no audit não significa acessível.

## O que faz

-  Base de conhecimento embutida (`accessibility_mcp/a11y/content/`): 69 guias (WCAG 2.2, ARIA, NVDA/VoiceOver/TalkBack, o que o leitor de tela fala por elemento, tecla e evento, ordem de foco, títulos, listas e tabelas, checklist de auditoria, IA conversacional acessível, mobile, frameworks, XR, conformidade, e 28 playbooks de especialistas trazidos do Qaaccessibility), 42 exemplos de componentes acessíveis (modal, abas, combobox, treegrid, chat de IA…) e o template React (10 arquivos) de chat/agente acessível.
-  Escolha pelo modelo do cliente: `a11y_list_content` devolve o catálogo (cada item com a descrição de quando usar) e o modelo escolhe pelo sentido. Nada de palavra-chave, regex ou ranking lexical, e nenhuma chamada de modelo dentro do servidor.
-  Medição de fatos: contraste WCAG, auditoria axe-core num navegador real, árvore de acessibilidade e ordem de foco por teclado.

## Ferramentas (43) e fluxos prontos

### Conhecimento e escolha

| Ferramenta | O que faz |
|---|---|
| `a11y_list_content` | Catálogo compacto (resumo + seções) de todos os guias, exemplos, arquivos do template e scripts |
| `a11y_workflow(name, ...)` | Devolve um fluxo pronto de trabalho para o modelo do cliente seguir (o mesmo texto dos prompts do MCP, para clientes que não mostram prompts) |
| `a11y_get_reference(name, section)` | Lê um guia inteiro ou só uma seção |
| `a11y_get_example(name)` | Devolve o código de um exemplo de componente |
| `a11y_get_template(name)` | Arquivo do template React de chat/agente acessível (`assets/…`) ou dos scripts (`scripts/…`) |

### Testar como usuário (sessão de navegador persistente)

O modelo do cliente é quem julga; estas ferramentas agem e devolvem fatos. Guias que ensinam a julgar:
`component-identity-guide`, `ux-persona-testing`, `design-language-review`.

| Ferramenta | O que faz |
|---|---|
| `a11y_open(url \| html, persona, browser)` | Abre a sessão em `chromium` (padrão, o mais preciso), `firefox` ou `webkit` (baixados sozinhos na primeira vez; o resultado lista os limites de cada um). Personas impostas pelo servidor: `keyboard` e `screen_reader` não têm mouse; `screen_reader` também não vê a tela; `low_vision` = 320 px (zoom 400%); `mobile_touch`; `reduced_motion`; `forced_colors` |
| `a11y_dossier(scope, max_elements)` | Fatos de cada elemento que o navegador aponta como focável ou clicável (inclui quem só tem `addEventListener`): papel e nome calculados pelo Chromium, foco, clicável, estados, opções/popup, landmark/heading, estilo. Não classifica: o modelo decide se é campo de texto, combobox, menu, acordeão… |
| `a11y_act(action, target, value)` | Faz o que o usuário faz (click, hover, focus, select, press, type, wait) e devolve o efeito: foco antes/depois, linhas da árvore que apareceram/sumiram, o que foi anunciado, URL, diálogos/popups |
| `a11y_reach(target)` | Quantos Tab até chegar ao elemento e o caminho do foco (inalcançável? em loop?) |
| `a11y_focus_style(target)` | Fatos do que o `:focus` muda no elemento (medido pelo Chromium sem disparar eventos); se é um indicador suficiente é julgamento do modelo |
| `a11y_announce(target)` | O que um leitor de tela receberia para o elemento |
| `a11y_observe()` | Estado atual: foco, árvore de acessibilidade, anúncios recentes |
| `a11y_stress(kind)` | `reflow_320` (WCAG 1.4.10) e `text_spacing` (1.4.12): fatos de overflow e texto cortado |
| `a11y_design_tokens()` | A linguagem de design real do site: estilos de texto em uso, escala de tamanhos, cores, espaçamentos, raios, variáveis `:root` |
| `a11y_screenshot(target, full_page)` | Captura JPEG da página ou de um elemento (recusada para `screen_reader`) |
| `a11y_preview_css(target, css, revert)` | Testa uma mudança de design temporariamente (só na sessão; o site não é alterado) |
| `a11y_close()` | Encerra a sessão; se uma operação longa está rodando (varredura de Tab, sonda…), a interrompe e devolve o que mediu. Expira após 10 min parada |

Fluxo: `a11y_open`, depois `a11y_dossier`, depois `a11y_act`/`a11y_reach` para provar o comportamento, depois julgar (o que é, onde o
usuário trava, o que melhorar mantendo o design), depois `a11y_preview_css` + `a11y_screenshot` para testar a proposta.
O relatório deve listar o que não foi verificado (leitores de tela reais, dispositivos reais, fluxos não testados).

### Fluxos prontos (prompts do MCP)

O servidor não roda um "usuário autônomo": quem conduz é o modelo do seu cliente, e os fluxos abaixo dizem a ordem do trabalho, o que se pode e não se pode afirmar e como entregar. Cada um existe como **prompt do MCP** e também como a ferramenta `a11y_workflow(name, ...)` (para clientes que não mostram prompts).

| Fluxo | Para que serve |
|---|---|
| `a11y_review(url, focus)` | Revisão completa de uma página: mapa, dossiê, sondas, estresse, personas, achados com evidência e relatório |
| `a11y_walkthrough(url, task, persona)` | Cumprir uma tarefa como uma pessoa da persona e dizer onde foi difícil |
| `a11y_component(url, selector)` | Identificar um componente e conferir o contrato dele (o que deve e não deve fazer) |
| `a11y_site_scan(url, max_pages)` | Varrer várias páginas por fatos e revisar as que mais importam |
| `a11y_compare_runs(base_run_id, head_run_id)` | Conferir que uma correção funcionou e nada piorou |
| `a11y_write_accessible_code(task, stack)` | Escrever ou corrigir código acessível desde o começo e provar com as sondas |

Como chamar: no Claude Code, `/mcp__accessibility__a11y_review`; no VS Code, `/accessibility.a11y_review`; em qualquer cliente, peça "use a ferramenta a11y_workflow com name a11y_review". `a11y_status()` mostra a prontidão do navegador.

### Cobertura total (todo o conteúdo, Shadow DOM, iframes, vários navegadores)

| Ferramenta | O que faz |
|---|---|
| `a11y_page_map(scope)` | Fatos de TODO o conteúdo, não só do interativo: hierarquia de títulos e saltos de nível, landmarks, imagens (alt ausente × vazio × descritivo), links (mesmo texto p/ destinos diferentes), formulários e campos, tabelas, listas, mídia (legendas), iframes, regiões vivas, ordem de leitura × ordem visual (inversões exatas), regras `:hover` que revelam conteúdo e listeners delegados. Atravessa Shadow DOM aberto e mapeia cada iframe |
| `a11y_coverage()` | O que a sessão cobriu e o que NÃO cobriu: interativos descobertos/listados/sondados, mapa da página, iframes, design, estresse, requisições bloqueadas e a lista de lacunas. Inclua no relatório |
| `a11y_crawl(url, max_pages)` | Varre várias páginas do mesmo site (sitemap + links; respeita `robots.txt`; só GET; ritmo educado; até 30) e consolida fatos: axe por regra e por página, títulos repetidos, páginas sem `lang`/`title`/`h1`, saltos de título, imagens sem alt |

O dossiê agora atravessa Shadow DOM (aberto e fechado) e iframes; as ações e o `a11y_reach` alcançam esses elementos. No Firefox/WebKit, um gancho em
`addEventListener` detecta clicável por listener (antes só havia `cursor: pointer`).

Aprovação ligada ou desligada, nunca recusa seca. Em site local (localhost, 127.0.0.1, `*.localhost`, `*.test`) a aprovação fica desligada e tudo roda.
Em qualquer outro site, requisições que alteram dados (POST, PUT, PATCH, DELETE e envio de formulário) ficam retidas e o servidor mostra o que elas mudariam
(método, endereço e os nomes e tamanhos dos campos, nunca os valores). Elas só seguem quando a pessoa aprova com `a11y_approve` (allow, deny ou allow_all).
Um envio de formulário retido deixa a página onde está; se a pessoa aprovar, a ação dela é refeita uma única vez. `allow_mutations` aceita auto (padrão), ask, allow e block
(modo estrito escolhido pela pessoa).

| Ferramenta | O que faz |
|---|---|
| `a11y_approve(decision, ids)` | Resposta da pessoa aos pedidos retidos: allow, deny ou allow_all (aprovação desligada pelo resto da sessão) |
| `a11y_learn(topic, learning, scope)` | O modelo do cliente grava uma lição aprendida testando (mesmo assunto atualiza, nunca duplica; marcada com a origem; sem fila de aprovação) |
| `a11y_learnings(host)` | As lições guardadas na pasta do usuário (A11Y_MCP_HOME, padrão ~/.a11y-mcp) |
| `a11y_forget(topic, scope)` | Remove uma lição (a pessoa manda no que fica) |

Aprendizado sempre: o modelo do cliente decide o que vale lembrar e grava com `a11y_learn`; omitir nunca apaga, mesmo assunto atualiza sem duplicar, vale na hora e sem fila de aprovação. Desligar: `A11Y_MCP_LEARN=0`.
Tempo adaptativo: nenhum relógio fixo encerra um trabalho em andamento. A espera por um elemento continua enquanto a página mostra sinais de progresso (rede ou DOM mudando) e só desiste quando ela para de mudar, por um tempo proporcional ao que já esperou. A espera por uma página assentar continua enquanto houver requisição realmente em andamento; requisições que não terminam por natureza (event stream, long-poll) não contam como trabalho, e o limite para reconhecê-las acompanha a lentidão que o próprio site já mostrou (cada sessão aprende o ritmo do seu site). A auditoria e o carregamento de páginas são repetidos com mais tempo a cada tentativa, e a ação com efeito (clique, envio) roda uma única vez. A sessão parada só é fechada depois de um tempo que cresce com o ritmo da conversa (dez vezes o maior intervalo já visto, no mínimo dez minutos). Uma operação longa para por falta de progresso ou por cancelamento (`a11y_close`).

### Provar o comportamento e registrar achados com evidência

O que o axe e os scanners não enxergam aparece **agindo**: armadilha de teclado, foco que se perde, modal que vaza, mensagem que ninguém anuncia. As sondas agem como o teclado de uma pessoa e devolvem fatos; o achado só vira falha se a evidência medida o sustenta.

| Ferramenta | O que faz |
|---|---|
| `a11y_probe(kind, target)` | `tab_walk` (Tab do início ao fim: paradas, foco preso, foco coberto), `focus_obscured` (2.4.11), `target_size` (2.5.8), e o contrato do APG de `dialog`, `disclosure`, `menu`, `tabs`, `combobox`, `listbox`, `tree` e `tooltip`, mais `form_errors` (erro por campo, foco e anúncio), `status_update` (a mudança chega a quem não vê a tela? a região viva já existia? o foco caiu no corpo?) e `route_change` (título, foco e anúncio da nova tela). Os contratos devolvem `esperado × observado × met` (`null` = não deu para medir, não é aprovação) |
| `a11y_nvda_speech(url, tabs, reads)` | O que o **NVDA de verdade** FALA na página, em texto (Tab e modo leitura), sem veredito. Roda numa **VM Windows** com um agente (`nvda/vm/`), nunca no seu computador, então o seu NVDA, a sua voz e os seus complementos não são tocados. Só navega: não ativa botões nem envia formulários. A voz e a velocidade são as da VM. Precisa de `A11Y_MCP_NVDA_VM` e `A11Y_MCP_NVDA_TOKEN`; passo a passo em `nvda/vm/LEIAME.md` |
| `a11y_finding(claim, criterion, severity, target, evidence_steps)` | Registra um achado com critério WCAG 2.2 (validado: número inexistente é descartado), gravidade, elemento e passos de evidência. Sem evidência válida vira `cantTell`, nunca `failed` |
| `a11y_set_workspace(path)` / `a11y_read_file(path, offset, limit)` / `a11y_edit_file(path, old_string, new_string, replace_all)` / `a11y_approve_edit(decision, approval_id)` / `a11y_undo_edit(edit_id)` | Editor de arquivos do projeto da pessoa, sem depender de terminal: lê com números de linha, troca um trecho EXATO (ou cria arquivo), mantém cópia de segurança fora do projeto e desfaz. Só dentro da pasta que a pessoa nomeia na conversa (`a11y_set_workspace`, sem configurar nada antes); nunca lê nem escreve `.env`, chaves ou `.git`; um JSON ou Python válido não pode ficar inválido. Com a aprovação ligada (padrão, `A11Y_MCP_EDIT_APPROVAL`) a edição fica RETIDA mostrando o diff até a pessoa responder; desligada, edita sem perguntar |
| `a11y_trace()` | O rastro ordenado da sessão (ações, `reach`, sondas); os números são a evidência que os achados citam |
| `a11y_report(format, save, goal)` | Os achados da sessão em `json`, `earl` (W3C EARL 1.0 JSON-LD: failed / cantTell) ou `sarif` (SARIF 2.1.0, para CI). Com `save` (padrão) guarda a execução e devolve o `run_id` |
| `a11y_runs()` / `a11y_export(run_id, format)` / `a11y_diff(base, head)` | Cada `a11y_report` guarda os achados da sessão em `~/.a11y-mcp/runs` (desligar: `A11Y_MCP_RUNS=0`). Exporta uma execução e compara duas: o que é novo, o que foi corrigido e o que persiste (a identidade é critério + persona + papel e nome do elemento, não o id) |

Quem registra o achado é o modelo do cliente (`a11y_finding`); o servidor só confere fatos: os passos citados existem no rastro, o elemento foi visto na sessão, o critério WCAG é um número real. Sem evidência válida o achado nunca vira falha. O guia `wcag-evidence-and-probes` ensina qual sonda prova qual critério.

### Bancada de avaliação

`python -m accessibility_mcp.a11y.bench facts` parte de uma página correta (`evals/boa.html`) e injeta um defeito conhecido por vez (13 mutações, cada uma com o critério WCAG que viola). Compara o axe sozinho com o conjunto de ferramentas e confere que a página boa não dispara alarme. Roda sem modelo e está nos testes. O gabarito é dos defeitos plantados, não de todos os defeitos de um site real.

### Vários navegadores

| Ferramenta | O que faz |
|---|---|
| `a11y_compare_browsers(url \| html, browsers)` | A mesma página em 2+ navegadores, lado a lado, só fatos: diferenças na árvore de acessibilidade, violações do axe que aparecem em um só e ordem de foco por navegador. Se a diferença é bug da página ou modo de o navegador expor, é julgamento do modelo (guia `cross-browser-a11y`) |

Todas as medições (`a11y_audit`, `a11y_aria_snapshot`, `a11y_tab_order`) e a sessão aceitam `browser`.

| Recurso | Chromium | Firefox / WebKit |
|---|---|---|
| Papel/nome/estado | calculados pelo navegador (CDP) | aria snapshot do Playwright, elemento a elemento |
| Focável | árvore de acessibilidade | `tabIndex` calculado pelo navegador |
| Clicável (inclui só `addEventListener`) | sim (`DOMSnapshot.isClickable`) | não (só `cursor: pointer`, sinal mais fraco) |
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

> Verde não é acessível. O axe e as demais medições só dizem que nenhuma regra conhecida falhou. Só o teste como
> usuário mostra se a tarefa é possível e como é a experiência. Use os dois, e diga sempre o que ficou sem verificar.

## Como o julgamento funciona

Toda decisão de sentido (que guia serve, o que uma tela mostra, o que um elemento é, o que corrigir) é do **modelo do cliente**. O servidor mede fatos e impõe limites (persona sem mouse, aprovação de mutações, pasta de trabalho, fechamento da sessão). Não há palavra-chave, regex nem ranking lexical, e não há chamada de modelo, chave de API, provedor ou variável de modelo para configurar. As ferramentas de medição reportam fatos; interpretar e corrigir fica com quem chamou.

O que o modelo precisa saber para testar bem está no próprio servidor: os guias `testing-playbook-for-ai` (ordem das ferramentas, o que pode e o que não pode afirmar, erros já cometidos) e `component-behavior-matrix` (o que cada componente deve e não deve fazer, o que o leitor de tela recebe e qual sonda mede), além dos fluxos prontos.

A auditoria completa (pesquisa, o que foi removido por ser heurística e o que ficou, com justificativa) está em `docs/AUDITORIA.md`.

## Instalação

```bash
cd "C:\projetos IA\mcp"
pip install -r requirements.txt            # ou: uv sync
python scripts/setup.py                    # cadastra nos clientes que encontrar
```

O `scripts/setup.py` cadastra o servidor (entrada `accessibility`) no Claude Desktop, no Claude Code, no Codex e no Cursor, e mostra como fazer no VS Code. Manualmente, em cada cliente:

| Cliente | Como cadastrar |
|---|---|
| Claude Code | `claude mcp add --transport stdio --scope user accessibility -- uv --directory "C:\projetos IA\mcp" run mcp_server.py` (ou `.mcp.json` no projeto). Fluxos: `/mcp__accessibility__a11y_review` |
| Codex | `codex mcp add accessibility -- uv --directory "C:\projetos IA\mcp" run mcp_server.py` (grava `[mcp_servers.accessibility]` em `~/.codex/config.toml`). Se o seu Codex não mostrar prompts, use a ferramenta `a11y_workflow` |
| VS Code | Paleta de comandos, `MCP: Add Server`, `Command (stdio)`, o mesmo comando e o nome `accessibility`; ou um `mcp.json` com a chave `servers`. Fluxos: `/accessibility.a11y_review` |
| Cursor | `~/.cursor/mcp.json`, chave `mcpServers`, entrada `accessibility` com `command` e `args` |
| Claude Desktop | `claude_desktop_config.json`, chave `mcpServers`, entrada `accessibility` |

O Playwright e o navegador pedido (Chromium por padrão; Firefox/WebKit na primeira vez que forem usados) são instalados sozinhos em segundo plano na primeira vez que o servidor sobe (leva alguns minutos e ~150 MB;
`a11y_status` mostra o andamento). Para desligar: `A11Y_MCP_AUTO_INSTALL=0` (aí rode `python -m playwright install chromium`).

Reinicie o cliente depois de cadastrar. O `scripts/setup.ps1` faz tudo isso no Windows.
Dependências: `mcp>=1.2,<2` (o mcp 2.x renomeou o `FastMCP`), `playwright`, `httpx`.

## Demonstração: "axe verde" não é acessível

`demo/loja/` tem um site simples em três versões (`v1-original`, `v2-axe-verde`, `v3-corrigido`) e `verificar.py`, que aplica as mesmas medições do MCP
em cada uma, separando a camada genérica (axe) da camada de julgamento (tarefas só de teclado, leitor de tela, foco, reflow, design).
A v2 passa no axe e mesmo assim um usuário de teclado não consegue escolher categoria, abrir o menu, ler o FAQ nem comprar.
O relatório (`demo/loja/README.md`) mostra o que cada componente realmente é, as correções que mantêm o design e o que deu errado no caminho.

```bash
python demo/loja/verificar.py
```

## Segurança

- Navegação só em `http://` e `https://` (nunca `file:`, `javascript:`, `chrome:`); na sessão, requisições de outros esquemas são abortadas, downloads recusados, diálogos JS dispensados (e registrados), popups fechados (e registrados).
- Uma sessão por vez, expira após 10 min parada; nenhum JavaScript arbitrário é exposto ao cliente; `a11y_preview_css` aceita só declarações (sem `url()`, `@` ou HTML).
- Personas são impostas pelo servidor (ex.: `keyboard` não tem mouse), não pela boa vontade do modelo.
- Não digite credenciais reais em páginas testadas; use contas de teste.
- Leitura de guias/exemplos só por nome do catálogo — texto do cliente nunca vira caminho de arquivo.
- Nenhuma chave de API é necessária nem lida: o servidor não chama modelo.

## Estrutura

```
C:\projetos IA\mcp\
├── mcp_server.py            ← ponto de entrada fino (a configuração do cliente continua apontando para ele)
├── accessibility_mcp/       ← o pacote do servidor
│   ├── server.py            ← servidor FastMCP
│   └── a11y/
│       ├── tools.py         ← ferramentas de conhecimento/medição e os recursos MCP
│       ├── tools_ux.py      ← ferramentas de sessão: dossiê, ações, personas, design
│       ├── session.py       ← sessão de navegador persistente (personas impostas, descoberta pelo Chromium, efeitos, estresse)
│       ├── prompts.py       ← fluxos prontos (prompts do MCP e a ferramenta a11y_workflow) para o modelo do cliente
│       ├── probes.py        ← sondas de comportamento (Tab, contratos APG, formulários, troca de tela) + js/probe_*.js
│       ├── findings.py + wcag.py + verify.py + runs.py + learn.py ← achados com evidência, EARL/SARIF, conferência de evidência, execuções salvas, diff e lições
│       ├── bench.py         ← bancada de avaliação por mutação (evals/boa.html)
│       ├── provisioning.py  ← instala Playwright e Chromium/Firefox/WebKit sozinho
│       ├── compare.py       ← mesma página em vários navegadores (fatos lado a lado)
│       ├── page_scripts.py + js/ ← scripts que coletam FATOS dentro da página (nunca classificam)
│       ├── audit.py         ← contraste, axe-core, árvore de acessibilidade, ordem de foco
│       ├── content_index.py ← catálogo dos guias/exemplos (leitura só por nome)
│       ├── content/         ← guias, exemplos, template React + catalog.json (descrições escritas por IA)
│       └── vendor/          ← axe-core 4.12.1 (MPL-2.0)
├── tests/                   ← testes com Chromium real (auditoria, sessão, sondas, protocolo MCP)
├── evals/                   ← páginas de referência da bancada de avaliação
├── demo/                    ← loja de demonstração com defeitos conhecidos
├── nvda/                    ← fala real do NVDA numa VM (Guidepup)
├── scripts/                 ← setup.py, setup.ps1 e test.py (instalação e checagem)
├── docs/                    ← AUDITORIA.md e QUICK_START.md
├── CLAUDE.md + .claude/rules/ ← regras obrigatórias do projeto
├── mcp.json / requirements.txt / pyproject.toml
└── .github/workflows/       ← CI
```

Os guias e exemplos são editáveis em `accessibility_mcp/a11y/content/`; o `SKILL.md` de lá explica como usar cada ferramenta.

## Desenvolvimento

```bash
python -m pytest -q          # inclui testes com navegador real (~1 min)
ruff check .
mypy
```

Não há modelo no servidor, então nenhum teste precisa de chave ou de modelo simulado.
