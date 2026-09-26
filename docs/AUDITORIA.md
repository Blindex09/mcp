# Auditoria do MCP de acessibilidade (setembro de 2026)

Auditoria do projeto inteiro contra a regra do dono: **o servidor não pode ser determinismo, heurística nem
palavra-chave.** Tudo que é julgamento (o que um elemento é, onde o usuário travou, o que melhorar, que guia serve)
é do **modelo**, em texto corrido, com visão; o código só **age, mede fatos e impõe limites** (permissão,
segurança, teto de custo). Aqui estão a pesquisa que orientou as decisões, o que a auditoria achou, o que foi
corrigido, o que ficou (com justificativa) e o que vem a seguir.

## 1. Pesquisa (o que o estado da arte diz)

| Achado | Fonte | Decisão |
|---|---|---|
| Automação pega só ~30–40% dos problemas WCAG; o resto exige julgamento, teclado e tecnologia assistiva. Nenhuma das 13 ferramentas testadas pegou ordem de leitura, foco invisível e uso de cor dependente de contexto. Uma ferramenta com IA chegou a 62,8% numa auditoria manual de referência. | [TestParty](https://testparty.ai/blog/automated-accessibility-testing-guide), [TestGuild](https://testguild.com/accessibility-testing-tools-automation/) | O axe virou uma medição entre várias; o centro passou a ser o teste **como usuário** e o relatório com "NÃO VERIFICADO". |
| Agentes web confiáveis leem a **árvore de acessibilidade** (papel/nome/estado computados pelo navegador), com captura de tela como **segundo canal de evidência**. | [Playwright MCP](https://playwright.dev/mcp/snapshots), [DEV](https://dev.to/pointchecknote/browser-automation-with-claude-playwright-mcp-why-accessibility-snapshots-beat-screenshots-2pke) | Dossiê e descoberta passaram a usar a árvore e o DOMSnapshot **do Chromium**; o agente recebe árvore + screenshot. |
| Papel, nome e estados "reais" vêm de `Accessibility.getFullAXTree` (CDP), não de uma reconstrução a partir do HTML/ARIA. | [CDP Accessibility](https://chromedevtools.github.io/devtools-protocol/tot/Accessibility/), [Chrome DevTools](https://developer.chrome.com/blog/full-accessibility-tree) | Removida a aproximação própria do nome acessível. |
| A especificação MCP de **2026-07-28** tornou o núcleo *stateless* e **descontinuou o sampling** (substituído por chamar a API do provedor direto), além de roots e logging. | [MCP 2026-07-28](https://blog.modelcontextprotocol.io/posts/2026-07-28/), [WorkOS](https://workos.com/blog/mcp-stateless-spec-2026-07-28) | O modelo do servidor (provedor direto) virou o caminho principal; o sampling do cliente é bônus. Claude Code nunca ofereceu sampling. |
| Leitores de tela reais podem ser automatizados: **Guidepup** dirige NVDA (Windows) e VoiceOver (macOS) e devolve o *log de fala*; o W3C tem o **AT Driver** em formação. Mas cobre "estreito e profundo" (≈6 de 55 critérios WCAG sozinho); combinado com teclado, ponteiro e visual chega a ~80%. | [Guidepup](https://github.com/guidepup/guidepup), [Assistiv Labs](https://assistivlabs.com/articles/automating-screen-readers-for-accessibility-testing) | Não implementado nesta rodada (ver §5): mexe na configuração do sistema e não dá para provar aqui sem a sua autorização. |

## 2. Achados da auditoria e o que foi feito

### 2.1 Determinismo/heurística/palavra-chave removidos

| # | Achado | Correção |
|---|---|---|
| 1 | O catálogo era resumido por **regex** (primeiro parágrafo, comentário de abertura). | `a11y/content/catalog.json`: descrições "quando usar" **escritas por IA**, em texto corrido. Um teste falha se um guia/exemplo não tiver descrição ou se sobrar descrição órfã. As funções de regex foram apagadas. |
| 2 | O dossiê **adivinhava** o que era interativo (lista de tags + `cursor: pointer`). | A descoberta vem do **Chromium**: focável pela árvore de acessibilidade e clicável pelo `DOMSnapshot.isClickable` (inclui quem só tem `addEventListener`). Um elemento customizado como `<x-chip tabindex=0>` entra sem que eu o conheça; um `div` "Comprar agora" só de mouse entra como *clicável, não focável, sem papel, sem nome* — o achado que importa. |
| 3 | O nome acessível era **aproximado** por mim (label/aria-label/placeholder). | Passa a ser o nome **computado pelo navegador** (`computed.name`), com os atributos crus ao lado como fonte. |
| 4 | `editable` vinha de uma lista de tipos de `<input>`. | Vem da propriedade `editable` do navegador. |
| 5 | `focus_indicator: true/false` (outline ou box-shadow) — um **veredito** feito por regra, impreciso. | Removido. `a11y_focus_style` mede o que o `:focus` muda (pseudo-estado forçado pelo CDP, sem disparar eventos) e devolve os fatos; se é suficiente é do modelo. |
| 6 | Esperas **fixas** (0,15 s / 3 s) após cada ação. | Espera **adaptativa**: navegação concluída + nenhuma requisição em voo + DOM quieto; só há um teto de segurança. |
| 7 | Modelo **padrão** embutido (Haiku). | Removido: `A11Y_MCP_MODEL` é obrigatório; a escolha é sua. |
| 8 | Dependência do **sampling**, que a especificação descontinuou. | Provedor direto primeiro (Anthropic, OpenAI, compatíveis com OpenAI como xAI/OpenRouter/LM Studio, Ollama), sampling depois. Imagens (visão) aceitas em todos os caminhos. |
| 9 | Scripts de página como *strings* Python (escapes frágeis, difíceis de revisar). | Arquivos `.js` reais em `a11y/js/`. |
| 10 | Resíduo do servidor antigo: variáveis `SKILLS_MCP_*`. | Renomeadas para `A11Y_MCP_*`. |

### 2.2 Autonomia e independência

- **Instala sozinho** o pacote `playwright` e o Chromium, em segundo plano no início do servidor
  (`A11Y_MCP_AUTO_INSTALL=0` desliga). Testado de verdade: o Chromium que faltava foi baixado em 21 s. Se uma ferramenta chegar
  antes de terminar, espera até 50 s e responde "instalando, tente em instantes" em vez de travar.
- **`a11y_walkthrough`** e **`a11y_review`**: um agente (modelo + harness) opera a página como uma pessoa da persona escolhida.
  O modelo decide cada passo vendo a tela e a árvore, e escreve o relatório; o harness impõe persona, formato, tetos de
  passos/tempo/chamadas, parada em laço e fechamento da sessão.
- **`a11y_close` interrompe** um teste em andamento e devolve o relatório parcial (antes travava esperando o fim).
- **`a11y_status`**: mostra se o navegador e o modelo estão prontos, sem revelar chaves.

### 2.3 Segurança e confiabilidade (revisão)

Já estavam certos e foram mantidos/testados: só `http/https`; downloads recusados; diálogos e popups dispensados e
registrados; uma sessão por vez com expiração em 10 min; nenhum JavaScript arbitrário exposto; `preview_css` sem
`url()`/`@`/HTML; leitura de guias só por nome do catálogo; chave só do ambiente e fora de logs; personas impostas pelo
servidor. Acrescentado: URL base de provedor compatível validada (só `http(s)`), instalação sem checagem de versão do pip,
e cancelamento cooperativo.

### 2.4 O que ficou determinístico, e por quê (não é julgamento)

| Onde | Por que é aceitável |
|---|---|
| Fórmula de contraste WCAG; níveis A/AA/AAA → tags do axe | Definição normativa / configuração, não interpretação. |
| `a11y_stress` (reflow em 320 px; espaçamento de texto 1.4.12) | Procedimentos que o próprio WCAG define; devolvem fatos de overflow/corte. |
| Persona sem mouse; teto de passos/tempo/chamadas; parada com a mesma ação 3× no mesmo estado | **Harness**: impõe o permitido e protege o custo; não opina sobre o que o usuário deveria fazer. |
| Validação de esquema de URL, de CSS do preview, do nome devolvido pelo modelo (existe no catálogo?) | Fato objetivo / proteção. |
| Lista de papéis de *landmark* e de cabeçalhos no `dossier.js` | Definição do ARIA, para contexto; o modelo decide o significado. |
| `_split_markdown`, extração de JSON da resposta do modelo | Estrutura/parsing, não semântica. |

### 2.5 Limitações conhecidas (não escondidas)

- **iframes** e **Shadow DOM**: o dossiê não os percorre (o `DOMSnapshot` os vê, mas os ids ficam fora do `document.querySelector`).
- Elemento **focável escondido por `aria-hidden`** não aparece no dossiê (a árvore o ignora); o `a11y_audit` (regra `aria-hidden-focus`) cobre.
- Não é leitor de tela real: a árvore de acessibilidade é um **substituto**.
- Fluxos com login não foram exercitados; use contas de teste.
- **Nenhum passo com modelo real foi rodado nesta máquina** (não há chave nem Ollama). O harness do agente foi provado com um modelo
  roteirizado (limites, persona, laços, fechamento, cancelamento, visão, provedores) e os provedores com HTTP simulado. A qualidade do
  julgamento depende do modelo que você escolher.

## 3. O que passou a ser possível

O fluxo completo, sem intervenção: abrir a página → o navegador diz o que é focável/clicável e como cada coisa é exposta →
o modelo prova o comportamento agindo (efeito: foco, árvore, anúncios) → decide o que cada componente é naquele site →
mede a linguagem de design real → testa uma proposta com `a11y_preview_css` + `a11y_screenshot` → escreve o relatório com o
que **não** foi verificado. Tudo com persona imposta (teclado, leitor de tela, baixa visão, celular…).

## 4. Validação em sites reais

Descoberta, papéis calculados, foco, design e reflow em páginas do W3C, Wikipédia e GOV.UK (1–5 s cada). Exemplos do que os fatos
já mostram: `input list` → papel calculado `combobox "Buscar"`; 37 elementos clicáveis fora do teclado na Wikipédia; dois `div`
focáveis sem nome no GOV.UK; foco do GOV.UK com contorno transparente + `box-shadow` (padrão para alto contraste).

## 5. Próximos passos recomendados (em ordem)

1. **Leitor de tela real (NVDA) via Guidepup.** É o maior salto de fidelidade: a fala real do NVDA como evidência. Nesta máquina
   o NVDA e o Node 24 já existem; falta `@guidepup/setup`, que baixa os ativos para `%LOCALAPPDATA%\guidepup` e configura o ambiente
   para automação (mexe em configuração do sistema — **preciso da sua autorização**). O suporte oficial do Guidepup no Windows é o
   Windows Server 2022/2025; no Windows 11 é não oficial, então validar antes de prometer.
2. **Shadow DOM e iframes** no dossiê (descoberta por frame; ids atravessando raízes).
3. **Migração para o SDK MCP v2** (o `FastMCP` virou `MCPServer`; sampling sai). Hoje o projeto fixa `mcp<2`.
4. **Fluxos autenticados**: estado de sessão fornecido por você (sem digitar credenciais reais no teste).
5. **Varredura de várias páginas** (sitemap) com relatório consolidado e exportação (WCAG-EM).
6. **W3C AT Driver**, quando houver implementação estável, como alternativa portátil ao Guidepup.
7. Rodar o `a11y_walkthrough`/`a11y_review` de verdade com o seu modelo e comparar o relatório com uma auditoria manual, para calibrar prompts e guias.

## 6. Vários navegadores (Chromium, Firefox, WebKit)

O Playwright roda os três; o MCP passou a aceitar `browser` na sessão, nas medições e nos testes autônomos, e ganhou
`a11y_compare_browsers`. O que muda por navegador está na tabela do README e no guia `cross-browser-a11y`:

- **Chromium** mantém a descoberta exata (CDP: árvore de acessibilidade + `DOMSnapshot.isClickable`).
- **Firefox e WebKit** não têm CDP: focável vem do `tabIndex` calculado pelo navegador, `cursor: pointer` entra como sinal **mais fraco**,
  e papel/nome vêm do aria snapshot do Playwright. **Não detectam clicável só por `addEventListener`** (um botão só de mouse sem
  `cursor: pointer` passa despercebido) e o `a11y_focus_style` foca de verdade (dispara eventos). Tudo isso é declarado em `limits`
  no resultado; o agente autônomo o recebe e o relatório deve dizer o que não foi medido.
- Firefox não emula `is_mobile`: a persona de celular usa viewport e toque, e avisa.
- Motivo de existir: Firefox + NVDA é a combinação mais comum entre usuários de NVDA; a mesma página pode expor a acessibilidade de forma diferente.
- Validado de verdade: Firefox nas 11 verificações da suíte; WebKit baixado sozinho em 8 s e a sessão abriu nele (o resto do WebKit segue o
  mesmo caminho do Firefox, mas não tem suíte própria).
