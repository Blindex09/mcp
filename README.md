# Accessibility MCP Server

Servidor MCP somente de acessibilidade (web, mobile e interfaces de IA/agentes) para Claude Desktop, VS Code, Cursor e qualquer cliente MCP.

Ele dá à IA quatro coisas: conhecimento (guias e exemplos de acessibilidade), escolha inteligente do que ler para cada tarefa, medição de uma página (axe-core, foco, contraste) e — o mais importante — teste como usuário de verdade: uma sessão de navegador que a IA opera (só teclado, leitor de tela, zoom, celular…) para descobrir o que o site realmente faz, porque verde no audit não significa acessível.

## O que faz

-  Base de conhecimento embutida (`a11y/content/`): 31 guias (WCAG 2.2, ARIA, NVDA/VoiceOver/TalkBack, checklist de auditoria, IA conversacional acessível, mobile, frameworks, XR…), 42 exemplos de componentes acessíveis (modal, abas, combobox, treegrid, chat de IA…) e o template React (10 arquivos) de chat/agente acessível.
-  Escolha pelo modelo: `a11y_find` recebe a tarefa em linguagem natural, em qualquer idioma, e o modelo escolhe os guias e exemplos certos pelo sentido. Nada de palavra-chave, regex ou ranking lexical.
-  Medição de fatos: contraste WCAG, auditoria axe-core num navegador real, árvore de acessibilidade e ordem de foco por teclado.

## Ferramentas (38)

### Conhecimento e escolha

| Ferramenta | O que faz |
|---|---|
| `a11y_list_content` | Catálogo compacto (resumo + seções) de todos os guias, exemplos, arquivos do template e scripts |
| `a11y_find(task)` | O modelo escolhe guias/exemplos para a tarefa |
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
| `a11y_close()` | Encerra a sessão; se um teste autônomo está rodando, o interrompe e devolve o relatório parcial. Expira após 10 min parada |

Fluxo: `a11y_open`, depois `a11y_dossier`, depois `a11y_act`/`a11y_reach` para provar o comportamento, depois julgar (o que é, onde o
usuário trava, o que melhorar mantendo o design), depois `a11y_preview_css` + `a11y_screenshot` para testar a proposta.
O relatório deve listar o que não foi verificado (leitores de tela reais, dispositivos reais, fluxos não testados).

### Usuário autônomo (o modelo opera a página sozinho)

| Ferramenta | O que faz |
|---|---|
| `a11y_walkthrough(task, url \| html, persona, max_steps, vision)` | Um modelo faz o papel de uma pessoa da persona tentando cumprir a tarefa, passo a passo, vendo a tela (screenshot) e a árvore de acessibilidade, e escreve um relatório em texto corrido: o que aconteceu, onde travou, achados por gravidade com a correção que mantém o design e o que não foi verificado |
| `a11y_review(focus, url \| html, persona, max_steps, vision)` | Revisão de UX: o modelo explora, prova o comportamento de cada componente importante, decide o que ele realmente é naquele site e revisa tipografia/espaçamento contra a linguagem de design do próprio site |
| `a11y_status()` | Prontidão: navegador instalado/instalando e modelo configurado (nunca mostra chaves) |

O modelo decide tudo que é julgamento; o servidor só impõe limites: persona (teclado e leitor de tela sem mouse), formato da
ação, no máximo 60 passos, tempo, parada se repetir a mesma ação no mesmo estado, e fechamento da sessão. Precisa do modelo do servidor
(veja abaixo) ou de um cliente com sampling. Cada passo é narrado; `a11y_close` interrompe sem perder o progresso.

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
| `a11y_learnings(host)` | O que o servidor aprendeu em testes anteriores, guardado na pasta do usuário (A11Y_MCP_HOME, padrão ~/.a11y-mcp) |
| `a11y_forget(topic, scope)` | Remove um aprendizado |

Aprendizado sempre: depois de cada teste autônomo o modelo decide o que vale lembrar (só as mudanças; omitir nunca apaga; mesmo assunto atualiza, sem duplicar), na hora e sem fila de aprovação.
Roteador semântico (router.py): com `A11Y_MCP_MODEL_FAST` diferente de `A11Y_MCP_MODEL`, quem escolhe a camada de cada chamada é um modelo, não uma regra. O modelo barato lê a finalidade do pedido, o contexto, fatos objetivos (tamanho, imagens anexas, saída esperada), os resultados recentes e as lições aprendidas, e decide a camada e se a resposta deve ser conferida. A resposta barata só sobe de camada quando não veio, quando a validação objetiva de quem chamou falhou (JSON ilegível, nome que não existe no catálogo) ou quando um verificador independente e mais forte a julgou inadequada; nunca pela confiança que o próprio modelo declara. Sem decisão válida do roteador, vale a camada forte. Com um só modelo não há chamada de roteamento. Os contadores aparecem em `a11y_status` (`routing`), e as lições de roteamento ficam na memória de aprendizado, no escopo `roteamento`.
Tempo adaptativo: nenhum relógio fixo encerra um trabalho em andamento. A espera por um elemento continua enquanto a página mostra sinais de progresso (rede ou DOM mudando) e só desiste quando ela para de mudar, por um tempo proporcional ao que já esperou. A espera por uma página assentar continua enquanto houver requisição realmente em andamento; requisições que não terminam por natureza (event stream, long-poll) não contam como trabalho, e o limite para reconhecê-las acompanha a lentidão que o próprio site já mostrou (cada sessão aprende o ritmo do seu site). A chamada ao modelo, a auditoria e o carregamento de páginas são repetidos com mais tempo a cada tentativa, e a ação com efeito (clique, envio) roda uma única vez. A sessão parada só é fechada depois de um tempo que cresce com o ritmo da conversa (dez vezes o maior intervalo já visto, no mínimo dez minutos). O teste autônomo para por falta de progresso, por cancelamento (`a11y_close`) ou pelo orçamento de passos que a pessoa configurou.

### Provar o comportamento e registrar achados com evidência

O que o axe e os scanners não enxergam aparece **agindo**: armadilha de teclado, foco que se perde, modal que vaza, mensagem que ninguém anuncia. As sondas agem como o teclado de uma pessoa e devolvem fatos; o achado só vira falha se a evidência medida o sustenta.

| Ferramenta | O que faz |
|---|---|
| `a11y_probe(kind, target)` | `tab_walk` (Tab do início ao fim: paradas, foco preso, foco coberto), `focus_obscured` (2.4.11), `target_size` (2.5.8), e o contrato do APG de `dialog`, `disclosure`, `menu`, `tabs`, `combobox`, mais `form_errors` (erro por campo, foco e anúncio) e `route_change` (título, foco e anúncio da nova tela). Os contratos devolvem `esperado × observado × met` (`null` = não deu para medir, não é aprovação) |
| `a11y_finding(claim, criterion, severity, target, evidence_steps)` | Registra um achado com critério WCAG 2.2 (validado: número inexistente é descartado), gravidade, elemento e passos de evidência. Sem evidência válida vira `cantTell`, nunca `failed` |
| `a11y_trace()` | O rastro ordenado da sessão (ações, `reach`, sondas); os números são a evidência que os achados citam |
| `a11y_report(format)` | Os achados da sessão em `json`, `earl` (W3C EARL 1.0 JSON-LD: failed / cantTell) ou `sarif` (SARIF 2.1.0, para CI) |
| `a11y_runs()` / `a11y_export(run_id, format)` / `a11y_diff(base, head)` | Cada teste autônomo guarda seus achados em `~/.a11y-mcp/runs` (desligar: `A11Y_MCP_RUNS=0`). Exporta uma execução e compara duas: o que é novo, o que foi corrigido e o que persiste (a identidade é critério + persona + papel e nome do elemento, não o id) |

No teste autônomo, o agente tem a ação `probe` e o campo `finding`. Antes do relatório, um **verificador** confere cada achado contra o rastro e os fatos do elemento: `supported` (vira `failed`), `unsupported` (refutado: sai do relatório, fica registrado) ou `cantTell`. Sem resposta válida do verificador, o achado nunca vira falha. O guia `wcag-evidence-and-probes` ensina qual sonda prova qual critério.

### Bancada de avaliação

`python -m a11y.bench facts` parte de uma página correta (`evals/boa.html`) e injeta um defeito conhecido por vez (13 mutações, cada uma com o critério WCAG que viola). Compara o axe sozinho com o conjunto de ferramentas e confere que a página boa não dispara alarme. Roda sem modelo e está nos testes. `python -m a11y.bench agent` roda o agente de verdade (com o modelo configurado) e mede recall e falsos positivos por modelo, para saber se uma mudança melhorou ou piorou. O gabarito é dos defeitos plantados, não de todos os defeitos de um site real.

### Vários navegadores

| Ferramenta | O que faz |
|---|---|
| `a11y_compare_browsers(url \| html, browsers)` | A mesma página em 2+ navegadores, lado a lado, só fatos: diferenças na árvore de acessibilidade, violações do axe que aparecem em um só e ordem de foco por navegador. Se a diferença é bug da página ou modo de o navegador expor, é julgamento do modelo (guia `cross-browser-a11y`) |

Todas as medições (`a11y_audit`, `a11y_aria_snapshot`, `a11y_tab_order`), a sessão e os testes autônomos aceitam `browser`.

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

Toda decisão de sentido (que guia serve, o que uma tela mostra, qual o próximo passo de um usuário) é de um modelo; o servidor só
valida fatos objetivos (o nome devolvido existe no catálogo?). Não há palavra-chave, regex nem ranking lexical.

A especificação MCP de 2026-07-28 descontinuou o sampling (o servidor deve chamar o provedor direto). Por isso:

1. Provedor configurado por ambiente (caminho principal), chamado direto, com suporte a imagens:

| Variável | Uso |
|---|---|
| `ANTHROPIC_API_KEY` | ativa o provedor Anthropic |
| `OPENAI_API_KEY` | ativa o provedor OpenAI |
| `A11Y_MCP_BASE_URL` (+ `A11Y_MCP_API_KEY`) | qualquer servidor compatível com OpenAI (xAI, OpenRouter, LM Studio, Ollama `/v1`…) |
| `A11Y_MCP_BACKEND` | `anthropic` \| `openai` \| `openai-compatible` \| `ollama` (opcional; senão detecta pelo ambiente) |
| `OLLAMA_HOST` | Ollama nativo (padrão `http://localhost:11434`; use um modelo com visão para as capturas) |
| `OLLAMA_API_KEY` | Ollama Cloud: a chave sozinha escolhe o backend `ollama` e o endereço `https://ollama.com` |
| `A11Y_MCP_MODEL` | opcional: id do modelo, se você quiser escolher você mesmo. Sobrepõe qualquer resolução automática |

**A chave sozinha costuma bastar** — `A11Y_MCP_MODEL` não é mais obrigatório. Sem ele, `models.py` resolve o modelo sozinho, nesta ordem, sem
nenhuma tabela ou opinião nossa sobre "qual é bom": (1) uma escolha já feita antes fica guardada e é reaproveitada; (2) quando o provedor tem
roteador nativo — `gpt-5-auto` na OpenAI, `openrouter/auto` quando `A11Y_MCP_BASE_URL` é literalmente o da OpenRouter —, delega para o produto
deles; (3) senão, busca ao vivo o catálogo real de modelos da conta e pede ao modelo do cliente (via MCP sampling) que escolha um, pelo
significado da tarefa; a resposta só vale se for um nome que existe de fato no catálogo, e a escolha fica guardada, então isso acontece uma vez
por provedor. Sem chave nenhuma, ou com um cliente sem sampling e nada resolvido ainda, `a11y_status` mostra o catálogo real para você escolher.

Exemplo no JSON do cliente: `"env": {"ANTHROPIC_API_KEY": "..."}` — só isso já é suficiente. Para fixar você mesmo: `"env": {"ANTHROPIC_API_KEY": "...", "A11Y_MCP_MODEL": "<seu modelo>"}`.

**Papéis nomeados, além de main/fast.** O agente autônomo (`a11y_walkthrough`/`a11y_review`) usa 3 papéis fixos, não uma decisão de custo/qualidade:
`vision` descreve em texto a captura de tela antes de qualquer raciocínio, `main` decide a próxima ação, e `write` escreve o relatório final
cruzando tudo. Cada papel tem sua própria env var opcional (`A11Y_MCP_MODEL_VISION`, `A11Y_MCP_MODEL_WRITE`); sem ela, o papel herda a mesma
resolução automática de `A11Y_MCP_MODEL` (a escolha específica do papel, se já foi feita antes, é reaproveitada primeiro). Ex.: com Ollama Cloud,
`OLLAMA_API_KEY` sozinha basta, e cada papel aprende seu próprio modelo real do catálogo (visão precisa de um modelo multimodal, como
`gemma4:31b`; main e write podem ser qualquer outro, como `deepseek-v4.1-flash` e `gpt-oss:120b`). Isso é diferente do roteador fast/main
(`router.py`), que continua sendo uma decisão de julgamento do modelo, sem papel fixo — ver seção 13 de `docs/AUDITORIA.md`.

2. Sampling do cliente, se ele ainda oferecer (bônus; o Claude Code não oferece).
3. Sem nenhum dos dois: `a11y_find` devolve o catálogo para o modelo que chamou escolher, e `a11y_walkthrough`/`a11y_review` explicam como configurar.
   As ferramentas de sessão (`a11y_open`, `a11y_dossier`, `a11y_act`…) funcionam sempre, porque aí o modelo do próprio cliente conduz.

As ferramentas de medição não usam modelo: reportam fatos, e interpretar e corrigir fica com quem chamou.
A auditoria completa (pesquisa, o que foi removido por ser heurística e o que ficou, com justificativa) está em `docs/AUDITORIA.md`.

## Instalação

```bash
cd "C:\projetos IA\mcp"
pip install -r requirements.txt            # ou: uv sync
python setup.py                            # registra no Claude Desktop e Cursor (entrada "accessibility")
```

O Playwright e o navegador pedido (Chromium por padrão; Firefox/WebKit na primeira vez que forem usados) são instalados sozinhos em segundo plano na primeira vez que o servidor sobe (leva alguns minutos e ~150 MB;
`a11y_status` mostra o andamento). Para desligar: `A11Y_MCP_AUTO_INSTALL=0` (aí rode `python -m playwright install chromium`).

Reinicie o Claude Desktop / Cursor. Para VS Code, o `setup.py` imprime o trecho para o `settings.json`. O `setup.ps1` faz tudo isso no Windows.
Dependências: `mcp>=1.2,<2` (o mcp 2.x renomeou o `FastMCP`), `playwright`. O `httpx` já vem com o `mcp`.

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
- Chave de API só do ambiente, fora de logs; URL base de provedor validada (só `http(s)`).

## Estrutura

```
C:\projetos IA\mcp\
├── mcp_server.py        ← servidor FastMCP (entrada)
├── llm.py               ← acesso ao modelo: provedores diretos (com visão) e sampling do cliente
├── a11y/
│   ├── tools.py         ← ferramentas de conhecimento/medição e os recursos MCP
│   ├── tools_ux.py      ← ferramentas de sessão: dossiê, ações, personas, design
│   ├── session.py       ← sessão de navegador persistente (personas impostas, descoberta pelo Chromium, efeitos, estresse)
│   ├── agent.py         ← usuário autônomo: o modelo decide, o harness impõe limites
│   ├── probes.py        ← sondas de comportamento (Tab, contratos APG, formulários, troca de tela) + js/probe_*.js
│   ├── findings.py + wcag.py + verify.py + runs.py ← achados com evidência, EARL/SARIF, verificador, execuções salvas e diff
│   ├── bench.py         ← bancada de avaliação por mutação (evals/boa.html)
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
