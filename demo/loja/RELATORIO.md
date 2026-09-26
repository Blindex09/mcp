# Casa do Chá — relatório de acessibilidade e design (v1 → v3)

Site de demonstração com **três versões**, verificadas com as mesmas medições do MCP (`python demo/loja/verificar.py`):

| Versão | O que é |
|---|---|
| `v1-original` | Como um site real costuma nascer: visual bonito, funciona com mouse, defeitos genéricos e de julgamento. |
| `v2-axe-verde` | **Só** o que o axe-core apontou foi corrigido (lang, alt, nome do botão do carrinho, contraste). |
| `v3-corrigido` | Correção de verdade: semântica certa, teclado, leitor de tela, foco, reflow e escala de design — **mantendo o visual**. |

> **Quem julgou aqui:** o julgamento abaixo (o que é cada componente, o que mudar no design) foi feito pelo Claude desta sessão, lendo os **fatos** e as
> **provas de comportamento** que o MCP devolve. O modo autônomo (`a11y_walkthrough`/`a11y_review`) **não foi rodado**: não há modelo configurado nesta máquina.
> O MCP não edita arquivos do site: ele mede, prova e recomenda; quem aplica a correção é o agente de código, e o MCP **verifica** o resultado.

## 1. As duas camadas são coisas separadas

**Camada genérica (scan automático — axe-core).** Acha o que tem regra mecânica.

| Versão | Violações do axe |
|---|---|
| v1 | 4 regras: `button-name` (carrinho sem nome), `image-alt` (4 imagens), `color-contrast` (5 textos), `html-has-lang` |
| v2 | **0** |
| v3 | **0** |

**Camada de julgamento (agir como usuário).** Só aparece usando o site. Resultado (mesma bateria em cada versão):

| Verificação | v1 | v2 (axe verde) | v3 |
|---|---|---|---|
| T1 escolher categoria só com teclado | falha | **falha** | passa |
| T2 abrir o menu "Produtos" só com teclado | falha | **falha** | passa |
| T3 abrir uma pergunta do FAQ só com teclado | falha | **falha** | passa |
| T4 comprar um chá só com teclado | falha | **falha** | passa |
| Controles só de mouse (clicáveis, sem foco, sem papel) | 5 | **5** | 0 |
| Papel do campo "Categoria" (calculado pelo navegador) | textbox | **textbox** | combobox |
| T5 o aviso de compra é anunciado a um leitor de tela | nada | **nada** | anunciado |
| T6 foco visível | nenhum | **nenhum** | contorno de 3 px |
| T7 reflow em 320 px | rolagem horizontal | **rolagem horizontal** | sem rolagem |
| Corpo do texto | 13 px, entrelinha 1,1 | **igual** | 16 px, 1,5 |
| Famílias de fonte / tamanhos / espaçamentos | 3 / 8 / 13 | **igual** | 2 / 5 / 8 |

**A v2 é o "verde que engana":** o scan diz que está acessível e um usuário de teclado não consegue escolher categoria, abrir o menu, ler o FAQ nem comprar.
A persona de teclado é **imposta pelo servidor** (sem mouse), então o teste não pode "trapacear".

## 2. O que cada componente é, naquele site (julgamento)

| Elemento (v1) | Evidência (fatos + provas) | O que é para as pessoas | Correção (visual mantido) |
|---|---|---|---|
| **Campo "Categoria"** + lista | Papel calculado `textbox`, editável; ao focar e digitar, aparecem 5 opções (`<div>` clicáveis, sem foco, sem papel) que filtram pelo que se digita; ArrowDown/Enter não fazem nada | **Combobox editável com lista** (digita *e* escolhe) — não um campo de texto simples nem um `<select>` | `role="combobox"` + `aria-expanded/controls/autocomplete`, lista `role="listbox"` com `role="option"`, setas/Enter/Escape/Home/End, clique mantido. Resultado no navegador: papel `combobox` |
| **"Produtos ▾"** | Não é focável nem clicável (só `:hover` no CSS); ao passar o mouse aparecem 3 links; por teclado os links nunca recebem foco (menu com `display:none`) | **Navegação com submenu (disclosure de links)** — os itens *levam a páginas*; **não** é `role="menu"` (menu é para comandos) | `<button aria-expanded aria-controls>` + `<ul>` de links em `<nav>`; Enter/Espaço abrem, Tab entra nos links, Escape fecha e devolve o foco; o hover continua abrindo |
| **Perguntas do FAQ** | `<div>` clicável, sem foco, papel `generic`; ao clicar, a resposta aparece | **Acordeão** | `<h3><button aria-expanded aria-controls>` + painel `hidden`; Enter/Espaço |
| **"Comprar" (×3)** | `<div>` clicável, sem foco, papel `generic`, nome só pelo texto | **Botão** | `<button>` com nome único (`Comprar` + nome do chá oculto visualmente) e alvo de 44 px |
| **Aviso "Adicionado ao carrinho"** | O texto aparece na árvore, mas **nenhum anúncio** é emitido | **Mensagem de status** | `role="status" aria-live="polite"` presente desde o carregamento |
| **Botão do carrinho** | Botão sem nome (o axe também pega) | Botão "Carrinho" | `aria-label`, ícone `aria-hidden` |
| **Foco** | `*:focus{outline:none}`: ao focar, 0 propriedades mudam | — | `:focus-visible` com contorno de 3 px na cor da marca (tirada dos próprios tokens do site) |
| **Campo de e-mail** | O axe aceita o *placeholder* como nome; sem rótulo visível quando some | Campo de e-mail | `<label>` visível + `autocomplete="email"` |

## 3. Design (sugestões dentro da linguagem do próprio site)

Medido em `a11y_design_tokens` na v1: corpo em **13 px com entrelinha 1,1**, **3 famílias** (Arial, Georgia e Trebuchet MS — esta só no `h3`), **8 tamanhos**
(13, 14, 12, 17, 18, 15, 22, 13,33) e **13 valores de espaçamento** soltos (2, 5, 6, 7, 9, 12, 13, 22 px…).

O que fiz, mantendo a identidade (verde da marca, títulos em Georgia, corpo em Arial, cards arredondados):

- **Escala** 14 / 16 / 20 / 24 / 32 px (corpo 16 px, entrelinha 1,5) e espaçamento em múltiplos de 8 (variáveis CSS).
- **`h3` em Georgia**, como `h1` e `h2` (a Trebuchet era a exceção sem motivo aparente).
- Texto secundário `#595959` (contraste ≥ 4,5:1) em vez de cinzas claros.
- **Testei antes de recomendar** (`a11y_preview_css` + captura de tela): a proposta melhorava a leitura, **mas o teste de reflow acusou rolagem horizontal em 320 px**
  porque os três cards não quebravam de linha; por isso a v3 usa `flex-wrap` nos cards.
- A captura de tela mostrou um detalhe que nenhuma medição pegou: o botão "Comprar" ficava mais alto no card cujo título quebrava em duas linhas → alinhei os botões na base.

Isto são **sugestões de design com motivo**, não uma verdade de gosto; as falhas com critério normativo (nome, teclado, foco, reflow) estão acima, separadas.

## 4. O que deu errado no caminho (e virou correção no MCP)

1. **Bug no MCP encontrado pela comparação de navegadores.** `a11y_tab_order` e `a11y_compare_browsers` só detectavam "deu a volta ao primeiro elemento". No Firefox, o Tab no último
   elemento **não sai da página**, então o último botão era repetido 47 vezes e a ordem de foco parecia "diferente" do Chromium. Corrigido (para quando o foco **não se move**), com teste de regressão;
   agora a ordem é idêntica nos dois navegadores (13 × 13 na v3).
2. **Erro do meu verificador (não do site).** O T2 falhou na v3 porque o teste reiniciava o foco no topo antes do segundo Tab. Conferi manualmente (Tab chega em "Chás",
   Escape fecha e devolve o foco ao botão) e corrigi o verificador. Lição: **testar o testador**.
3. **Limite da ferramenta:** `a11y_design_tokens` mede valores *calculados*. Um `margin-top: auto` vira um número em pixels e aparece como "espaçamento novo" que o design não tem;
   troquei o CSS por `flex: 1`. Vale interpretar a contagem de espaçamentos com essa ressalva.
4. **Limite da descoberta:** o gatilho "Produtos ▾" da v1 **não aparece no dossiê** (não é focável, não tem listener: só `:hover` em CSS). Foi achado pela **prova de comportamento** (passar o mouse
   e ver a árvore mudar) e pela captura de tela. Menus só de hover exigem visão ou sondagem — por isso o modo autônomo recebe a captura de tela a cada passo.

## 5. Ainda não verificado

- Leitor de tela **real** (NVDA/JAWS/VoiceOver): a árvore de acessibilidade é um substituto; o texto anunciado e a experiência real podem variar.
- Dispositivo móvel real, comando de voz, lupa, outras páginas do site e outros breakpoints.
- Firefox foi verificado na ordem de foco, na árvore, no axe e no combobox por teclado; a bateria completa T1–T8 rodou em Chromium.
- O julgamento feito por um **modelo autônomo** (sem mim no circuito) ainda não foi exercitado.
