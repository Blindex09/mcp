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

Regra 5, autonomia. Cumpre: instala Playwright e os navegadores sozinho e refaz a ação que falha. Limite: se o modelo não está configurado, o servidor não pode escolher um por conta própria, porque a regra 9 proíbe modelo padrão; ele diz exatamente o que definir. Também não inicia um Ollama parado.

Regra 6, contexto. Cumpre em parte: os aprendizados persistem entre execuções. Não consulta conversas de outros agentes.

Regra 7, aprovação ligada ou desligada, nunca bloqueio. Estava violada com um bloqueio seco; corrigido. Site local tem aprovação desligada; em site real a requisição que altera dados fica retida com o que mudaria (nomes e tamanhos, nunca valores) até a pessoa decidir com a11y_approve. block existe só como modo estrito escolhido pela pessoa. As restrições de persona (teclado sem mouse) são limites do harness, não aprovação.

Regra 8, tempo adaptativo. Estava violada: havia relógios fixos de 420 s, 240 s, 90 s, 120 s e 3 s. Corrigido em duas rodadas. Primeiro, o que demora é tentado de novo com mais tempo, sem repetir ações com efeito (o clique roda uma vez). Depois, a pedido do dono, os últimos números fixos viraram tempos que se adaptam: a espera por elemento segue enquanto a página progride (rede ou DOM mudando) e desiste só quando ela para; a espera por página assentar aguarda toda requisição realmente em andamento, ignora as que nunca terminam (event stream, long-poll) com um limite que acompanha a lentidão já vista no site, e esse ritmo é reiniciado a cada sessão; a sessão parada só fecha depois de dez vezes o maior intervalo da conversa; as tentativas de modelo escalam sem teto prático. O teste autônomo para por falta de progresso, cancelamento ou pelo orçamento de passos da pessoa.

Regra 9, economia, qualidade e roteamento. Cumpre em parte. Não há modelo padrão embutido. A11Y_MCP_MODEL_FAST atende às chamadas leves, e a captura de tela só vai no primeiro passo, ao mudar de página ou quando o modelo pede. Limite: a escolha entre modelo leve e pesado é por propósito da chamada, definida no código, e não por um classificador semântico entre vários modelos.

Regra 10, aprendizado sempre. Estava ausente; implementado (a11y/learn.py). Limite: o conhecimento que muda no mundo, como o WCAG, não se atualiza sozinho a partir de fontes confiáveis; os guias são atualizados por revisão.

Regra 11, verde não é funcionando. Cumpre no espírito do projeto inteiro e na prova ponta a ponta pelo protocolo. Limite: quem executa o teste autônomo também julga; o harness verifica os fatos (cobertura, aprovação, limites), mas não há um verificador independente do julgamento do modelo.

Regra 12, engenharia de qualidade. ruff, mypy e pytest passam. Removidos do projeto os arquivos extras (capturas de tela e JSON gerado no demo), o relatório virou README, e os scripts de instalação ficaram sem emojis, que quebravam no console do Windows. Todo bug corrigido ganhou teste de regressão.

Regra 13, acessibilidade e visão de UX. É o objetivo do projeto.

Regra 14, paridade entre interfaces. Não se aplica aos chats do projeto principal. Há paridade entre navegadores com os limites declarados.

Regra 15, processo de trabalho. Documentação junto do código, commits por etapa, nenhum merge feito sem autorização, documentos para o usuário sem negrito, emoji nem setas.

Regra 16, supervisão calibrada. Cumpre: a pessoa é consultada nas ações que alteram dados em site real e fica fora do caminho no resto.

## 9. Prova ponta a ponta pelo protocolo

O teste tests/test_e2e_protocol.py sobe o servidor MCP como processo separado, como o Claude faz, e chama todas as ferramentas registradas, uma por uma, contra um mini-site de várias páginas com defeitos de todo tipo (Shadow DOM, iframe, vídeo sem legenda, tabela sem cabeçalho, formulário, menu só de hover, botões só de mouse, aviso mudo, robots.txt e sitemap). O modelo é um servidor falso compatível com OpenAI, então o usuário autônomo, a escolha de guias e o aprendizado passam por HTTP de verdade. A matriz falha se qualquer ferramenta registrada ficar sem ser exercitada. Essa prova achou dois bugs que os testes unitários não acharam: o foco por estilo não funcionava dentro de iframes e Shadow DOM, e o envio de formulário com aprovação travava a página.
