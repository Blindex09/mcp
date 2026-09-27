# Auditoria do MCP de acessibilidade (setembro de 2026)

Auditoria do projeto inteiro contra a regra do dono: o servidor não pode ser determinismo, heurística nem
palavra-chave. Tudo que é julgamento (o que um elemento é, onde o usuário travou, o que melhorar, que guia serve)
é do modelo, em texto corrido, com visão; o código só age, mede fatos e impõe limites (permissão,
segurança, teto de custo). Aqui estão a pesquisa que orientou as decisões, o que a auditoria achou, o que foi
corrigido, o que ficou (com justificativa) e o que vem a seguir.

## 1. Pesquisa (o que o estado da arte diz)

| Achado | Fonte | Decisão |
|---|---|---|
| Automação pega só ~30–40% dos problemas WCAG; o resto exige julgamento, teclado e tecnologia assistiva. Nenhuma das 13 ferramentas testadas pegou ordem de leitura, foco invisível e uso de cor dependente de contexto. Uma ferramenta com IA chegou a 62,8% numa auditoria manual de referência. | [TestParty](https://testparty.ai/blog/automated-accessibility-testing-guide), [TestGuild](https://testguild.com/accessibility-testing-tools-automation/) | O axe virou uma medição entre várias; o centro passou a ser o teste como usuário e o relatório com "NÃO VERIFICADO". |
| Agentes web confiáveis leem a árvore de acessibilidade (papel/nome/estado computados pelo navegador), com captura de tela como segundo canal de evidência. | [Playwright MCP](https://playwright.dev/mcp/snapshots), [DEV](https://dev.to/pointchecknote/browser-automation-with-claude-playwright-mcp-why-accessibility-snapshots-beat-screenshots-2pke) | Dossiê e descoberta passaram a usar a árvore e o DOMSnapshot do Chromium; o agente recebe árvore + screenshot. |
| Papel, nome e estados "reais" vêm de `Accessibility.getFullAXTree` (CDP), não de uma reconstrução a partir do HTML/ARIA. | [CDP Accessibility](https://chromedevtools.github.io/devtools-protocol/tot/Accessibility/), [Chrome DevTools](https://developer.chrome.com/blog/full-accessibility-tree) | Removida a aproximação própria do nome acessível. |
| A especificação MCP de 2026-07-28 tornou o núcleo stateless e descontinuou o sampling (substituído por chamar a API do provedor direto), além de roots e logging. | [MCP 2026-07-28](https://blog.modelcontextprotocol.io/posts/2026-07-28/), [WorkOS](https://workos.com/blog/mcp-stateless-spec-2026-07-28) | O modelo do servidor (provedor direto) virou o caminho principal; o sampling do cliente é bônus. Claude Code nunca ofereceu sampling. |
| Leitores de tela reais podem ser automatizados: Guidepup dirige NVDA (Windows) e VoiceOver (macOS) e devolve o log de fala; o W3C tem o AT Driver em formação. Mas cobre "estreito e profundo" (≈6 de 55 critérios WCAG sozinho); combinado com teclado, ponteiro e visual chega a ~80%. | [Guidepup](https://github.com/guidepup/guidepup), [Assistiv Labs](https://assistivlabs.com/articles/automating-screen-readers-for-accessibility-testing) | Não implementado nesta rodada (ver §5): mexe na configuração do sistema e não dá para provar aqui sem a sua autorização. |

## 2. Achados da auditoria e o que foi feito

### 2.1 Determinismo/heurística/palavra-chave removidos

| # | Achado | Correção |
|---|---|---|
| 1 | O catálogo era resumido por regex (primeiro parágrafo, comentário de abertura). | `a11y/content/catalog.json`: descrições "quando usar" escritas por IA, em texto corrido. Um teste falha se um guia/exemplo não tiver descrição ou se sobrar descrição órfã. As funções de regex foram apagadas. |
| 2 | O dossiê adivinhava o que era interativo (lista de tags + `cursor: pointer`). | A descoberta vem do Chromium: focável pela árvore de acessibilidade e clicável pelo `DOMSnapshot.isClickable` (inclui quem só tem `addEventListener`). Um elemento customizado como `<x-chip tabindex=0>` entra sem que eu o conheça; um `div` "Comprar agora" só de mouse entra como clicável, não focável, sem papel, sem nome — o achado que importa. |
| 3 | O nome acessível era aproximado por mim (label/aria-label/placeholder). | Passa a ser o nome computado pelo navegador (`computed.name`), com os atributos crus ao lado como fonte. |
| 4 | `editable` vinha de uma lista de tipos de `<input>`. | Vem da propriedade `editable` do navegador. |
| 5 | `focus_indicator: true/false` (outline ou box-shadow) — um veredito feito por regra, impreciso. | Removido. `a11y_focus_style` mede o que o `:focus` muda (pseudo-estado forçado pelo CDP, sem disparar eventos) e devolve os fatos; se é suficiente é do modelo. |
| 6 | Esperas fixas (0,15 s / 3 s) após cada ação. | Espera adaptativa: navegação concluída + nenhuma requisição em voo + DOM quieto; só há um teto de segurança. |
| 7 | Modelo padrão embutido (Haiku). | Removido: `A11Y_MCP_MODEL` é obrigatório; a escolha é sua. |
| 8 | Dependência do sampling, que a especificação descontinuou. | Provedor direto primeiro (Anthropic, OpenAI, compatíveis com OpenAI como xAI/OpenRouter/LM Studio, Ollama), sampling depois. Imagens (visão) aceitas em todos os caminhos. |
| 9 | Scripts de página como strings Python (escapes frágeis, difíceis de revisar). | Arquivos `.js` reais em `a11y/js/`. |
| 10 | Resíduo do servidor antigo: variáveis `SKILLS_MCP_*`. | Renomeadas para `A11Y_MCP_*`. |

### 2.2 Autonomia e independência

- Instala sozinho o pacote `playwright` e o Chromium, em segundo plano no início do servidor
  (`A11Y_MCP_AUTO_INSTALL=0` desliga). Testado de verdade: o Chromium que faltava foi baixado em 21 s. Se uma ferramenta chegar
  antes de terminar, espera até 50 s e responde "instalando, tente em instantes" em vez de travar.
- `a11y_walkthrough` e `a11y_review`: um agente (modelo + harness) opera a página como uma pessoa da persona escolhida.
  O modelo decide cada passo vendo a tela e a árvore, e escreve o relatório; o harness impõe persona, formato, tetos de
  passos/tempo/chamadas, parada em laço e fechamento da sessão.
- `a11y_close` interrompe um teste em andamento e devolve o relatório parcial (antes travava esperando o fim).
- `a11y_status`: mostra se o navegador e o modelo estão prontos, sem revelar chaves.

### 2.3 Segurança e confiabilidade (revisão)

Já estavam certos e foram mantidos/testados: só `http/https`; downloads recusados; diálogos e popups dispensados e
registrados; uma sessão por vez com expiração em 10 min; nenhum JavaScript arbitrário exposto; `preview_css` sem
`url()`/`@`/HTML; leitura de guias só por nome do catálogo; chave só do ambiente e fora de logs; personas impostas pelo
servidor. Acrescentado: URL base de provedor compatível validada (só `http(s)`), instalação sem checagem de versão do pip,
e cancelamento cooperativo.

### 2.4 O que ficou determinístico, e por quê (não é julgamento)

| Onde | Por que é aceitável |
|---|---|
| Fórmula de contraste WCAG; níveis A/AA/AAA, depois tags do axe | Definição normativa / configuração, não interpretação. |
| `a11y_stress` (reflow em 320 px; espaçamento de texto 1.4.12) | Procedimentos que o próprio WCAG define; devolvem fatos de overflow/corte. |
| Persona sem mouse; teto de passos/tempo/chamadas; parada com a mesma ação 3× no mesmo estado | Harness: impõe o permitido e protege o custo; não opina sobre o que o usuário deveria fazer. |
| Validação de esquema de URL, de CSS do preview, do nome devolvido pelo modelo (existe no catálogo?) | Fato objetivo / proteção. |
| Lista de papéis de landmark e de cabeçalhos no `dossier.js` | Definição do ARIA, para contexto; o modelo decide o significado. |
| `_split_markdown`, extração de JSON da resposta do modelo | Estrutura/parsing, não semântica. |

### 2.5 Limitações conhecidas (não escondidas)

- iframes e Shadow DOM: o dossiê não os percorre (o `DOMSnapshot` os vê, mas os ids ficam fora do `document.querySelector`).
- Elemento focável escondido por `aria-hidden` não aparece no dossiê (a árvore o ignora); o `a11y_audit` (regra `aria-hidden-focus`) cobre.
- Não é leitor de tela real: a árvore de acessibilidade é um substituto.
- Fluxos com login não foram exercitados; use contas de teste.
- Nenhum passo com modelo real foi rodado nesta máquina (não há chave nem Ollama). O harness do agente foi provado com um modelo
  roteirizado (limites, persona, laços, fechamento, cancelamento, visão, provedores) e os provedores com HTTP simulado. A qualidade do
  julgamento depende do modelo que você escolher.

## 3. O que passou a ser possível

O fluxo completo, sem intervenção: abrir a página, depois o navegador diz o que é focável/clicável e como cada coisa é exposta para
o modelo prova o comportamento agindo (efeito: foco, árvore, anúncios), depois decide o que cada componente é naquele site para
mede a linguagem de design real, depois testa uma proposta com `a11y_preview_css` + `a11y_screenshot`, depois escreve o relatório com o
que não foi verificado. Tudo com persona imposta (teclado, leitor de tela, baixa visão, celular…).

## 4. Validação em sites reais

Descoberta, papéis calculados, foco, design e reflow em páginas do W3C, Wikipédia e GOV.UK (1–5 s cada). Exemplos do que os fatos
já mostram: `input list`, depois papel calculado `combobox "Buscar"`; 37 elementos clicáveis fora do teclado na Wikipédia; dois `div`
focáveis sem nome no GOV.UK; foco do GOV.UK com contorno transparente + `box-shadow` (padrão para alto contraste).

## 5. Próximos passos recomendados (em ordem)

1. Leitor de tela real (NVDA) via Guidepup. É o maior salto de fidelidade: a fala real do NVDA como evidência. Nesta máquina
   o NVDA e o Node 24 já existem; falta `@guidepup/setup`, que baixa os ativos para `%LOCALAPPDATA%\guidepup` e configura o ambiente
   para automação (mexe em configuração do sistema — preciso da sua autorização). O suporte oficial do Guidepup no Windows é o
   Windows Server 2022/2025; no Windows 11 é não oficial, então validar antes de prometer.
2. Shadow DOM e iframes no dossiê (descoberta por frame; ids atravessando raízes).
3. Migração para o SDK MCP v2 (o `FastMCP` virou `MCPServer`; sampling sai). Hoje o projeto fixa `mcp<2`.
4. Fluxos autenticados: estado de sessão fornecido por você (sem digitar credenciais reais no teste).
5. Varredura de várias páginas (sitemap) com relatório consolidado e exportação (WCAG-EM).
6. W3C AT Driver, quando houver implementação estável, como alternativa portátil ao Guidepup.
7. Rodar o `a11y_walkthrough`/`a11y_review` de verdade com o seu modelo e comparar o relatório com uma auditoria manual, para calibrar prompts e guias.

## 6. Vários navegadores (Chromium, Firefox, WebKit)

O Playwright roda os três; o MCP passou a aceitar `browser` na sessão, nas medições e nos testes autônomos, e ganhou
`a11y_compare_browsers`. O que muda por navegador está na tabela do README e no guia `cross-browser-a11y`:

- Chromium mantém a descoberta exata (CDP: árvore de acessibilidade + `DOMSnapshot.isClickable`).
- Firefox e WebKit não têm CDP: focável vem do `tabIndex` calculado pelo navegador, `cursor: pointer` entra como sinal mais fraco,
  e papel/nome vêm do aria snapshot do Playwright. Não detectam clicável só por `addEventListener` (um botão só de mouse sem
  `cursor: pointer` passa despercebido) e o `a11y_focus_style` foca de verdade (dispara eventos). Tudo isso é declarado em `limits`
  no resultado; o agente autônomo o recebe e o relatório deve dizer o que não foi medido.
- Firefox não emula `is_mobile`: a persona de celular usa viewport e toque, e avisa.
- Motivo de existir: Firefox + NVDA é a combinação mais comum entre usuários de NVDA; a mesma página pode expor a acessibilidade de forma diferente.
- Validado de verdade: Firefox nas 11 verificações da suíte; WebKit baixado sozinho em 8 s e a sessão abriu nele (o resto do WebKit segue o
  mesmo caminho do Firefox, mas não tem suíte própria).

## 7. Cobertura total

Pergunta do dono: "esse julgamento serve para todos os elementos de uma página?". Resposta antes: só para os interativos da página principal. O que mudou:

| Lacuna | Como foi coberta |
|---|---|
| Conteúdo não interativo (títulos, imagens, links, formulários, tabelas, mídia, ordem de leitura) | `a11y_page_map`: fatos de todo o conteúdo; guia `page-structure-review` para julgar; o agente autônomo recebe o mapa a cada página nova |
| Shadow DOM e iframes | O `DOMSnapshot` do Chromium já inclui shadow roots (abertos e fechados) e documentos de iframes; o dossiê e o mapa os atravessam; ações e `a11y_reach` alcançam esses elementos (Shadow DOM fechado é medido, mas marcado `actionable=false`) |
| Firefox/WebKit só viam `cursor: pointer` | Gancho em `addEventListener` (init script em todos os frames): clicável por listener; ações delegadas a `document`/`window` são reportadas como "alvo real desconhecido" |
| Menus abertos só por hover | `hover_reveals`: regras `:hover` das folhas de estilo que mudam exibição/visibilidade (dado, não opinião); o dossiê marca o gatilho |
| Estados que só existem depois de agir | O agente lista primeiro o que ainda não foi sondado e vê a cobertura a cada passo; exploração protegida (abaixo) |
| Padrões fora dos 11 clássicos | guia `more-component-patterns` (toolbar, slider, switch, radio, seletor de data, breadcrumbs, paginação, busca, toast, popover, stepper, upload, carregamento) |
| Uma página por vez | `a11y_crawl`: várias páginas, fatos consolidados |
| O relatório não dizia o que foi coberto | `a11y_coverage` e `coverage` no resultado do agente: lista de lacunas (elementos nunca sondados, mapa não lido, iframes sem mapa, requisições não enviadas) |

Exploração segura. Cobrir mais significa clicar mais. Em sites que não são de desenvolvimento local, requisições que alteram dados
(POST/PUT/PATCH/DELETE, envio de formulário) ficam retidas e o servidor mostra o que mudariam, até a pessoa aprovar (seção 8).
`allow_mutations=allow` só quando o dono pediu.

Bugs achados no caminho: o foco por teclado não atravessava Shadow DOM/iframes (`document.activeElement` devolve o host); a ordem de leitura usava limiar
e lista de tags (agora inversões exatas entre pares); o mapa não detectava o `order` do flexbox por causa dessa lista.

Limites que permanecem: Shadow DOM fechado não recebe ações; Firefox/WebKit não detectam clique delegado; a bateria completa segue em Chromium; não é leitor de tela real;
o julgamento autônomo por um modelo real ainda não foi exercitado (sem modelo configurado nesta máquina).

## 8. Conformidade com as regras mestras

Conferência do MCP contra o documento de regras mestras do dono do projeto. Onde havia violação, foi corrigida; o que ainda não cumpre está dito.

Regra 1, agente é modelo mais harness. Cumpre. O modelo decide o conteúdo; o código impõe persona, formato, teto de orçamento, aprovação, cancelamento e fechamento.

Regra 2, IA semântica sem heurística. Cumpre com as exceções justificadas da seção 2.4. Não há palavra-chave, regex nem ranking para julgamento. Ainda existem faixas de 8 px para agrupar linhas na ordem de leitura, declaradas como aritmética do mapa da página.

Regra 3, conversa corrida e humana. Cumpre no que o MCP entrega: o usuário autônomo narra cada passo em texto corrido e os prompts pedem português sem asteriscos nem markdown. Não se aplica o token a token, porque ferramentas MCP devolvem resultados completos; o progresso segue por notificações.

Regra 4, interface e leitor de tela. Não se aplica, o MCP não tem interface própria.

Regra 5, autonomia. Cumpre: instala Playwright e os navegadores sozinho, refaz a ação que falha e, desde a seção 12, resolve o modelo sozinho a partir só de uma chave (roteador nativo do provedor, ou o catálogo real lido por um modelo). Limite: sem nenhuma chave configurada não há o que resolver; também não inicia um Ollama parado.

Regra 6, contexto. Cumpre em parte: os aprendizados persistem entre execuções. Não consulta conversas de outros agentes.

Regra 7, aprovação ligada ou desligada, nunca bloqueio. Estava violada com um bloqueio seco; corrigido. Site local tem aprovação desligada; em site real a requisição que altera dados fica retida com o que mudaria (nomes e tamanhos, nunca valores) até a pessoa decidir com a11y_approve. block existe só como modo estrito escolhido pela pessoa. As restrições de persona (teclado sem mouse) são limites do harness, não aprovação.

Regra 8, tempo adaptativo. Estava violada: havia relógios fixos de 420 s, 240 s, 90 s, 120 s e 3 s. Corrigido em duas rodadas. Primeiro, o que demora é tentado de novo com mais tempo, sem repetir ações com efeito (o clique roda uma vez). Depois, a pedido do dono, os últimos números fixos viraram tempos que se adaptam: a espera por elemento segue enquanto a página progride (rede ou DOM mudando) e desiste só quando ela para; a espera por página assentar aguarda toda requisição realmente em andamento, ignora as que nunca terminam (event stream, long-poll) com um limite que acompanha a lentidão já vista no site, e esse ritmo é reiniciado a cada sessão; a sessão parada só fecha depois de dez vezes o maior intervalo da conversa; as tentativas de modelo escalam sem teto prático. O teste autônomo para por falta de progresso, cancelamento ou pelo orçamento de passos da pessoa.

Regra 9, economia, qualidade e roteamento. Cumpre. Não há modelo padrão embutido no código, e desde a seção 12 a pessoa também não precisa mais escolher um id de modelo à mão: só a chave já resolve, pelo roteador nativo do provedor ou pelo catálogo real lido por um modelo, nunca por uma tabela nossa. A escolha entre modelo leve e pesado é um classificador semântico (router.py): um modelo barato lê a finalidade de cada chamada, o contexto e fatos objetivos e decide a camada, com lições de roteamento no prompt (aprendizado em contexto). A cascata sobe de camada por fato objetivo ou por um verificador independente, nunca pela confiança autodeclarada. A captura de tela só vai no primeiro passo, ao mudar de página ou quando o modelo pede. Limites: só há duas camadas (A11Y_MCP_MODEL_FAST e A11Y_MCP_MODEL); o verificador lê só texto, sem imagens; a resolução automática de modelo só cobre a camada principal, não a rápida; e a qualidade de ambas as decisões, ainda não medida com um modelo real.

Regra 10, aprendizado sempre. Estava ausente; implementado (a11y/learn.py). Limite: o conhecimento que muda no mundo, como o WCAG, não se atualiza sozinho a partir de fontes confiáveis; os guias são atualizados por revisão.

Regra 11, verde não é funcionando. Cumpre no espírito do projeto inteiro e na prova ponta a ponta pelo protocolo. Limite: quem executa o teste autônomo também julga; o harness verifica os fatos (cobertura, aprovação, limites), mas não há um verificador independente do julgamento do modelo.

Regra 12, engenharia de qualidade. ruff, mypy e pytest passam. Removidos do projeto os arquivos extras (capturas de tela e JSON gerado no demo), o relatório virou README, e os scripts de instalação ficaram sem emojis, que quebravam no console do Windows. Todo bug corrigido ganhou teste de regressão.

Regra 13, acessibilidade e visão de UX. É o objetivo do projeto.

Regra 14, paridade entre interfaces. Não se aplica aos chats do projeto principal. Há paridade entre navegadores com os limites declarados.

Regra 15, processo de trabalho. Documentação junto do código, commits por etapa, nenhum merge feito sem autorização, documentos para o usuário sem negrito, emoji nem setas.

Regra 16, supervisão calibrada. Cumpre: a pessoa é consultada nas ações que alteram dados em site real e fica fora do caminho no resto.

## 9. Prova ponta a ponta pelo protocolo

O teste tests/test_e2e_protocol.py sobe o servidor MCP como processo separado, como o Claude faz, e chama todas as ferramentas registradas, uma por uma, contra um mini-site de várias páginas com defeitos de todo tipo (Shadow DOM, iframe, vídeo sem legenda, tabela sem cabeçalho, formulário, menu só de hover, botões só de mouse, aviso mudo, robots.txt e sitemap). O modelo é um servidor falso compatível com OpenAI, então o usuário autônomo, a escolha de guias e o aprendizado passam por HTTP de verdade. A matriz falha se qualquer ferramenta registrada ficar sem ser exercitada. Essa prova achou dois bugs que os testes unitários não acharam: o foco por estilo não funcionava dentro de iframes e Shadow DOM, e o envio de formulário com aprovação travava a página.

## 10. Correções achadas ao testar uma loja de exemplo (setembro de 2026)

Um site de propósito inacessível, com várias páginas, foi testado com todas as ferramentas. Dois erros do servidor apareceram e foram corrigidos, cada um com teste de regressão.

Ordem de Tab. a11y_tab_order e a11y_compare_browsers decidiam que o foco tinha parado de mover comparando a descrição do elemento (tag, nome, estilo). Quatro links com o mesmo texto e sem id pareciam um só, e a varredura terminava no primeiro. O a11y_reach tinha o mesmo defeito latente, escondido pelos ids do dossiê. Agora cada parada é identificada pelo nó real (índice do frame e número do nó), a lógica está numa função só (audit.tab_stops) e atravessa iframes e Shadow DOM. Consequência: o compare_browsers passou a mostrar uma diferença que sempre existiu, o Firefox parar no próprio iframe antes do conteúdo dele, e o teste de ponta a ponta foi corrigido para afirmar isso em vez de "idêntica".

Ações delegadas. Depois de qualquer ação, o Playwright registra listeners em window na página, e o gancho os reportava como se fossem da página. Cada entrada de delegated_listeners agora traz source, o endereço do script que registrou, ou null quando o código não tem endereço (avaliado, como o do Playwright, ou HTML passado direto no Chromium). Nada é filtrado no gancho: quem lê decide. O prompt do agente e o aviso do dossiê e da cobertura só usam entradas com origem confirmada. O dossiê continua sem listar elementos clicáveis por delegação, porque só cursor: pointer os apontaria e isso é heurística; ele agora avisa, como fato, que a página usa delegação.

Ollama Cloud. OLLAMA_API_KEY envia Authorization Bearer e, sem OLLAMA_HOST, usa https://ollama.com. No acesso direto o modelo é o nome da lista de tags, sem o sufixo -cloud. A chave nunca vai para log e o conftest a remove do ambiente dos testes.

Limite que permanece: em Chromium com HTML passado direto não há endereço de script, então a proveniência dos listeners é desconhecida nesse modo.

## 11. Roteador semântico de modelos (setembro de 2026)

Pesquisa. Roteamento aprende uma política a partir de preferências (RouteLLM), cascata consulta modelos em sequência e para quando a resposta basta (FrugalGPT), e a verificação da própria resposta decide a escalada (AutoMix). Trabalhos recentes mostram que a confiança verbalizada pelo modelo é quase independente da resposta, o que a torna um gatilho frágil, e que os sinais mais fortes (margem de token calibrada, sondas de estado oculto, aprendizado por reforço) exigem rótulos ou acesso interno que a API não oferece. Roteadores que recebem políticas em linguagem natural e as aplicam em contexto (Arch-Router) dispensam retreino. O survey de 2026 recomenda combinar pré-roteamento, verificação e escalada, com feedback online.

Decisão. Pré-roteador semântico com política em contexto, cascata por fatos com verificador independente, e aprendizado guardado na memória que já existia. Nada de palavra-chave, regex, tabela de dificuldade ou limiar; um teste guarda o código-fonte contra isso.

O que é fato e não julgamento: o resultado do roteador ter uma camada que existe; a resposta ter vindo; a validação objetiva de quem chamou (JSON legível, nome existente no catálogo); a configuração (qual modelo é cada camada). Tudo o mais é do modelo.

Falha segura. Roteador ilegível, ausente ou com erro de rede: camada forte. Verificador ilegível: aceita a resposta barata, que já foi paga. Camada forte sem resposta depois de uma subida: devolve a resposta barata, que vale mais que nenhuma.

Fontes. Survey de roteamento e cascata dinâmicos: https://arxiv.org/html/2603.04445v2. UCCI, incerteza calibrada em cascata, que exige rótulos: https://arxiv.org/html/2605.18796. RLCascadeRouter, cascata sem estimador de qualidade, que exige recompensas: https://arxiv.org/pdf/2608.15817. Arch-Router, políticas em linguagem natural aplicadas em contexto: https://arxiv.org/abs/2506.16655. Confiança verbalizada quase independente da resposta em modelos de visão: https://arxiv.org/html/2609.18453.

## 12. Resolução automática de modelo: só a chave basta (setembro de 2026)

Pergunta do dono: por que exigir A11Y_MCP_MODEL se o roteamento tem que ser automático, e por que o classificador e o modelo não decidem sozinhos, sem heurística, palavra-chave nem determinismo?

Pesquisa. A indústria resolve isso de duas formas. Serviços agregadores publicam um modelo "auto" que eles mesmos operam: OpenRouter tem openrouter/auto (classifica o pedido, ranqueia por gasto real da comunidade, escolhe), e a própria OpenAI tem gpt-5-auto na sua API direta (um roteador em tempo real, treinado com sinais reais como troca manual de modelo e taxa de preferência). Fora desses dois, não existe hoje um "auto" nativo em api.anthropic.com nem em servidores Ollama: essas APIs exigem um id de modelo em toda chamada, sem exceção, o que não é uma escolha de projeto nossa, é um fato do provedor. Ferramentas como RouteLLM, Not Diamond e Martian resolvem isso por fora, com um classificador treinado sobre um catálogo de modelos conhecido.

Decisão. Nenhuma tabela de "qual modelo é bom" no código, em nenhuma hipótese. Quatro fontes, nesta ordem, a primeira que existir vale: a escolha explícita da pessoa (A11Y_MCP_MODEL, sempre por cima); uma escolha já feita antes, guardada como aprendizado; o roteador nativo do próprio provedor, um fato que ele documenta, nunca uma opinião nossa; e, só quando nada disso existe, o catálogo real da conta, buscado ao vivo, com a escolha entre os nomes reais feita por um modelo, o do cliente, via MCP sampling, porque ainda não há modelo do servidor para perguntar. A única validação é um fato objetivo, o nome devolvido existe de fato no catálogo, e a escolha fica guardada, então isso acontece uma vez por provedor, não a cada chamada.

O que é fato e não julgamento: o endereço configurado ser literalmente o da OpenRouter; o nome devolvido existir no catálogo real; a lista de modelos que o provedor devolve. O resto, incluindo qual dos modelos reais atende melhor a finalidade do servidor, é sempre de um modelo.

Falha segura. Sem chave nenhuma, ou com um cliente sem sampling e nada resolvido ainda, a_status e a11y_find devolvem o catálogo real para a pessoa decidir, nunca um palpite silencioso, o que é a própria regra 6 (ambiguidade material gera pergunta cedo), não uma falha da regra 9.

Limite. Cobre só a camada principal; a camada rápida sem escolha própria usa a mesma resolvida para a principal. A escolha feita pelo modelo do cliente ainda não foi testada com um modelo real, só com um cliente simulado.

Fontes. Roteador nativo da OpenAI, gpt-5-auto: https://openai.com/index/introducing-gpt-5-5/. Roteador nativo da OpenRouter: https://openrouter.ai/docs/guides/routing/routers/auto-router. Comparação de roteadores de 2026, RouteLLM, Not Diamond, Martian: https://dev.to/lukas85/top-model-routing-tools-in-2026-llm-routers-compared-3neo. Endpoint real de modelos da Anthropic: https://platform.claude.com/docs/en/api/models/list.

## 13. Papéis fixos (visão, raciocínio, relatório) além do roteador (setembro de 2026)

Pedido do dono: usar os modelos reais da conta em papéis fixos — o mais leve responde só texto e relatório (gpt-oss:120b escreve o relatório final), um modelo pensa (deepseek-v4.1-flash raciocina; flash está ok, não precisa ser "pro"), e um modelo de visão captura e descreve a tela (gemma4:31b, o único confirmado multimodal na conta, conforme a documentação oficial do Ollama). Depois disso tudo se cruza e o modelo de relatório monta o resultado.

Por que isso não contradiz a regra 9 (sem heurística/keyword para julgamento). Há uma diferença entre uma decisão de CUSTO/QUALIDADE (que modelo é bom o bastante para esta tarefa, o roteador semântico decide isso lendo a finalidade real) e uma exigência de CAPACIDADE/CONFIGURAÇÃO (esta etapa do pipeline sempre precisa de visão; esta etapa sempre escreve o relatório final). A primeira é julgamento e continua sempre do modelo, via router.py. A segunda é um fato de papel fixo no pipeline, não uma opinião sobre "qual modelo é melhor" — é o próprio dono do projeto quem decide a forma do pipeline, não uma tabela de heurística no código adivinhando isso.

Implementação. router.ask_routed ganhou um parâmetro tier opcional que, quando presente, ignora classificador/verificador/escalada e chama llm.ask_model direto (router.py, _STATS["forced_calls"]). models.py e llm.py generalizaram "camada" (main/fast) em "papel" nomeado: cada papel tem sua env var própria (A11Y_MCP_MODEL_VISION, A11Y_MCP_MODEL_WRITE, ...), resolvida nesta ordem: env explícita do papel, escolha persistida daquele papel, e só então herda a resolução (4 passos da seção 12) da camada main — um papel nunca dispara seu próprio bootstrap de catálogo. Em a11y/agent.py, ao tirar uma captura de tela o agente primeiro chama tier="vision" para obter uma descrição em texto corrido, sem julgamento, do que está visível; essa descrição entra na observação enviada ao passo de raciocínio (tier="main", forçado), e só a imagem crua é enviada de volta caso a chamada de visão falhe (graceful degradation). O relatório final usa tier="write". A decisão de o que vale a pena lembrar (aprendizado, a11y/learn.py) continua sendo uma decisão de custo/qualidade genuína e continua passando pelo classificador (hint=), não um papel fixo.

Bug encontrado ao implementar: _model_for(tier), usado por router.py, tinha um fallback interno para A11Y_MCP_MODEL sempre que a camada não fosse "main" — isso mascarava a escolha persistida específica do papel. Corrigido com um helper separado, _explicit_role_env(tier), sem fallback, usado só por _resolve_model (llm.py); _model_for ficou como estava, para não afetar router.py.

Persistido de verdade (não teste): ollama → deepseek-v4.1-flash (papel main), ollama:vision → gemma4:31b, ollama:write → gpt-oss:120b, em ~/.a11y-mcp/learnings.json, pelo mesmo mecanismo de aprendizado que já existia para a escolha única anterior.

Limite. O pipeline de 3 papéis é fixo pela decisão do dono, não descoberto automaticamente; não há hoje um roteamento genuíno entre os 17 modelos do catálogo por tarefa, só entre fast/main dentro do que já não tem papel fixo, e entre os papéis nomeados quando o pipeline os invoca. Se o dono quiser N-way routing real entre todo o catálogo, é uma decisão nova, ainda não pedida de forma explícita.

## 14. Tempo adaptativo também na verificação de acessibilidade (setembro de 2026)

Pergunta do dono: a verificação de acessibilidade (a11y_audit e as ferramentas que abrem página) usa tempo adaptativo, sem relógio fixo que desista de um site lento?

Bug real encontrado (não era o caso). a11y/audit.py::_with_page envolvia a navegação inteira num with_patience(run, TOTAL_TIMEOUT_S) por fora — uma espera que crescia a cada tentativa — mas a navegação de dentro (page.goto) sempre usava o MESMO NAV_TIMEOUT_MS fixo (30s) via set_default_timeout, porque a espera "adaptativa" só envolvia a chamada por fora, sem repassar o tempo maior para dentro. Um site que sempre demora mais que 30s nunca teria sucesso, não importa quantas tentativas por fora acontecessem. a11y/session.py::Session.open() tinha o mesmo tipo de bug, mas pior: nenhuma tentativa adicional, nenhum with_patience, um único timeout fixo e qualquer falha subia na hora.

Correção. Os dois agora usam patient() (a11y/patience.py) diretamente sobre uma função attempt(timeout_s) que recebe o tempo crescente (3x, 9x, 27x...) e o repassa DIRETO para page.goto/page.set_content via timeout=, o mesmo padrão que a11y/crawl.py já usava corretamente. Em session.py, cada tentativa falha limpa os recursos abertos (fecha o navegador) antes de patient() tentar de novo com mais tempo.

O que é fato e não julgamento: o valor de NAV_TIMEOUT_MS/ACTION_TIMEOUT_MS é configuração, não heurística; o crescimento (3x por tentativa) é o mesmo mecanismo já usado em todo o resto do projeto (a11y/patience.py), não uma regra nova.

Teste de regressão. tests/test_patience.py ganhou um teste que prova que patient() é chamado com o tempo da 1a tentativa passado direto para a navegação (não um relógio único por fora), e um teste com um servidor HTTP local de verdade, lento de propósito (1,2s), com NAV_TIMEOUT_MS reduzido para 0,3s só nesse teste: a 1a tentativa estoura de verdade, e só a 2a/3a (tempo maior) tem sucesso — provando que o mecanismo funciona de ponta a ponta, não só que a função foi chamada.

Limite. Não há hoje um teste de regressão equivalente, com servidor lento real, para a11y/session.py::Session.open() (só a prova unitária de que patient() e o padrão attempt(timeout_s) estão no lugar, via os testes de test_patience.py que já cobrem SESSION.act e envio de formulário retido).
