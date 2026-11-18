# Como escrever o relatório: linguagem simples com rigor de QA

Como usar aqui: este guia vale para quem registra achados com `a11y_finding` e pede o relatório com
`a11y_create_report`. O servidor mede e organiza; o texto que ele cita vem do que você registra. Se o
registro for técnico demais, o relatório sai técnico demais — não há mágica depois.

A regra de ouro: o relatório é lido por duas pessoas ao mesmo tempo, quem vai corrigir o código e quem foi
prejudicado pelo problema. Toda frase precisa servir às duas.

## O título do achado: uma frase, o lugar na tela, sem código

O `claim` vira o título da ficha. Ele nomeia o lugar exato, em palavras que existem na tela.

| Ruim | Bom |
|---|---|
| Falha 1.4.3 — contraste insuficiente em `#clockbox` | O texto da faixa azul do topo quase desaparece no fundo |
| `.font-control a` sem `:focus-visible` | Os botões de tamanho de texto não mostram onde o foco está |
| `html` sem atributo `lang` | A página não diz em que idioma está escrita |

O seletor CSS não some: ele aparece em "Onde está", no fim, como detalhe para quem programa.

## A ficha tem sempre as mesmas cinco partes

1. **Onde está** — a região da tela em palavras (a faixa azul do topo, o rodapé, o bloco "Popular on BHP"),
   o elemento e, por último, o seletor.
2. **O que foi medido** — o número, o tamanho, a cor, a contagem. Não é opinião: é medição.
3. **Por que reprova** — o que a norma exige e por que a medição não atende.
4. **Como reproduzir** — só quando os passos foram registrados.
5. **Como corrigir** — a mudança concreta, com valor quando existe (cor, pixel, atributo).

A ordem não é decorativa: ela responde, na sequência, "onde", "quanto", "por quê" e "o que fazer".

## Preencha os campos que o relatório cita

| Campo de `a11y_finding` | O que escrever | Exemplo |
|---|---|---|
| `claim` | o problema em uma frase, com o lugar | "O texto da faixa azul do topo quase desaparece no fundo" |
| `observed` | a medição, com número | "Cinza #424242 sobre azul #396ec6: 2,02:1; o mínimo é 4,5:1 para 14 px" |
| `expected` | o que a norma pede | "4,5:1 para texto abaixo de 24 px" |
| `rationale` | por que a medição reprova | "A melhor combinação da faixa chega a menos da metade do mínimo" |
| `recommendation` | a correção concreta | "Trocar o texto da faixa para branco: 4,98:1, sem mudar o desenho" |

Sem `observed`, o relatório escreve "a medição não foi registrada" e cai para o próprio `claim`. Sem
`rationale`, ele diz que a justificativa não foi registrada. Ele nunca inventa número.

`impact` não entra em nenhum formato do relatório. Ele continua sendo dado de trabalho no registro do
achado (útil para triagem), mas não é citado no Word, no PDF, na planilha nem na apresentação.

## Cada dado em sua própria célula

Planilha, Word e PDF não juntam tudo em um parágrafo: site, sistema operacional, navegadores, princípio,
diretriz, criticidade, prioridade e roteiro aparecem em campos separados. Na planilha, Site fica em A1, Sistema operacional em B1, Navegadores em C1 e os demais cabeçalhos seguem na linha 1; cada ocorrência fica em uma linha abaixo. Word e PDF mantêm fichas por ocorrência, com campo à esquerda e valor à direita, seguidas da narrativa e dos passos numerados.

| Campo no relatório | De onde vem | Se faltar |
|---|---|---|
| Site | host da URL da página | sai vazio e a planilha escreve "Não registrado" |
| Sistema operacional | `operating_system` do contexto do relatório ou do achado | "Não registrado" |
| Navegadores | `browsers` do contexto, do achado ou o navegador medido na sessão | "Não informado" |
| Princípio e diretriz | derivados do número do critério WCAG | "Não identificado" |
| Criticidade | rótulo de gravidade do achado (Bloqueadora, Séria, Moderada, Leve) | "Não definida" |
| Prioridade | prioridade definida na triagem | "A definir" |
| Roteiro | `problem_location` (página, região, elemento e nome exato observados) | "Não registrado" |

Registre `operating_system` e `browsers` no contexto do relatório quando valem para a avaliação inteira, e no achado quando mudam. Registre `problem_location` por ocorrência; `journey` permanece apenas como contexto da tarefa. O relatório não deduz sistema operacional a partir
do navegador nem inventa um roteiro: campo vazio fica visivelmente vazio.

## Termos técnicos: só quando precisam existir, e sempre explicados

- "Marcos" em vez de *landmarks*; "alvos" explicado como "a área clicável"; "foco" explicado como "onde o teclado está parado".
- Nome do critério em português ("Contraste (mínimo)", "Idioma da página"), com o número ao lado para o QA.
- Uma sigla só entra depois de escrita por extenso na primeira vez.

## O que o relatório nunca faz

- Chama de "passa" o que não foi testado: critério sem resultado fica "não avaliado".
- Converte ausência de achado em conformidade.
- Inventa prazo a partir da prioridade: prazo é acordo, não consequência.
- Usa severidade como decisão de conformidade: severidade ordena o trabalho, não aprova critério.
- Escreve o nome de uma classe CSS no título do achado.

## A ordem do relatório (W3C WAI e WCAG-EM, passo 5)

Resumo → O que já está certo → Escopo → Ambiente, ferramentas e período → Como a avaliação foi
feita → Problemas encontrados (agrupados por princípio) → Tabela de conformidade → O que corrigir primeiro →
Como confirmar que foi corrigido → Limites → Ficha técnica → Referências → Anexos.

O Word e o PDF saem nessa ordem; a planilha NÃO tem aba de resumo nem de escopo: traz só uma aba por tela testada (inclusive "Todas as telas" para o que se repete).
Não gera Matriz WCAG, Correções e retestes nem Referências.

## Roteiro e passos precisos, acessíveis a quem vê e a quem não vê

Roteiro é a localização exata observada: URL/página, região ou formulário, tipo do elemento e seu texto ou nome acessível. Diferencie nomes repetidos com a seção, o formulário ou o conteúdo adjacente. Uma posição visual como "à direita" não basta para localizar algo sem visão. Se o nome acessível estiver ausente ou diferente do texto visível, registre essa diferença real e uma referência estrutural observada. CSS é complemento para quem programa, não o único endereço do problema.

Os passos são ações numeradas que partem de uma URL e estado inicial identificados, chegam ao elemento sem ambiguidade, acionam o comportamento e dizem o que conferir. Registre separadamente o observado e o esperado. Para problema estático, indique o elemento e a propriedade a inspecionar, sem inventar uma interação. Evite só "navegue até o problema", "clique aqui", "use Tab" ou "veja a imagem".

Use reproduction_steps_visual para o percurso com visão, reproduction_steps_keyboard para o percurso por teclado e reproduction_steps_screen_reader para o percurso com leitor de tela. reproduction_steps conserva passos gerais antigos. Esses campos estão disponíveis tanto no registro do achado quanto no contexto do relatório; são apresentados em subseções do mesmo campo Passos para reproduzir. Informe apenas percursos realmente observados. Não fabrique um percurso alternativo para preencher os três campos.

- Com visão: identifique a região, texto visível do controle, ação e sinal visual do defeito. Não dependa somente de cor ou posição.
- Por teclado: indique ponto de partida, teclas efetivamente usadas e como reconhecer o alvo. Não invente contagem de Tab. Se o alvo não recebe foco, descreva o caminho percorrido, os controles anterior e seguinte observados e a falha de alcance, sem mandar focar um alvo inalcançável.
- Sem visão: identifique o leitor/navegador e o modo, comandos e nomes usados somente quando registrados. Não dependa de screenshot, cor ou posição. Só transcreva fala real se o leitor foi executado; árvore de acessibilidade é uma medição diferente. Se não houve teste real, mantenha essa limitação explícita no método/cobertura, sem apresentar um roteiro proposto como executado.

Exemplo de localização: Página de contato > formulário Fale conosco > campo E-mail, antes de Enviar; distinto do campo E-mail da newsletter no rodapé. Exemplo de passo de teclado, quando medido: a partir do início da página de contato, use Tab até E-mail no formulário Fale conosco; digite abc; avance até Enviar e pressione Enter; confira a identificação do campo com erro. Os comandos de leitor de tela para o mesmo caso só podem ser descritos como testados se foram efetivamente usados.


Representação dos passos nos arquivos (29/10/2026)

O gerador representa os passos de reprodução como listas numeradas nativas no Word e listas com tags no PDF. Cada modalidade inicia sua própria sequência. Na planilha, os passos são texto numerado com quebras de linha na célula correspondente; a célula não possui a semântica de lista do Word. A estrutura do arquivo deve ser inspecionada, além da aparência.


## Roteiro sem coluna redundante e resultados com funções distintas

A localização detalhada fica em Roteiro. Área da página não é uma coluna ou seção separada dos relatórios. Registros antigos podem conservar page_area como dado de origem; o gerador pode usá-lo como fato disponível no roteiro quando falta problem_location, sem afirmar que esse dado incompleto seja uma localização exata.

expected_result descreve o comportamento ou a propriedade que deveria ser observado na condição testada. criterion_rationale explica por que os fatos observados descumprem o critério citado. Não basta copiar o esperado para a justificativa. Exemplo didático: esperado — ao receber foco por Tab, o botão Enviar apresenta indicação visual; justificativa — o botão recebeu foco, mas não apresentou indicação visual no teste, contrariando o critério 2.4.7. Esse exemplo não é evidência de uma execução real. Sem fatos suficientes, registre a limitação e não invente o motivo da falha.


## Percurso com visão e orientação com leitor de tela

Quando a pessoa pedir as duas formas, mantenha o percurso com visão e prepare também a navegação com leitor de tela usando a estrutura observada na página e os guias do leitor escolhido. O percurso realmente executado continua em reproduction_steps_screen_reader. Uma orientação ainda não executada fica exclusivamente em reproduction_steps_screen_reader_proposed, exibida como Sem visão — orientação de navegação não executada. Esse campo não confirma teste, fala ou conformidade e não muda a cobertura.

A orientação informa URL, leitor, navegador, modo e ponto inicial; descreve comandos concretos e o nome e contexto reais do alvo. No NVDA em modo de navegação, use H para títulos existentes, K para links, F para campos de formulário e C para caixas de combinação quando o papel correspondente foi observado. F não significa ir ao começo de um formulário. Não atribua atalhos do NVDA ao VoiceOver, JAWS ou outros leitores sem conferir a documentação correspondente. Não invente títulos, formulários, nomes, contagens de Tab ou fala. Se faltar informação para uma rota, declare a limitação.

Localizar o elemento não significa perceber toda barreira pelo leitor. Contraste, tamanho de alvo e indicador visual de foco exigem a medição ou revisão apropriada. A orientação deve dizer como chegar ao elemento e indicar essa verificação separada. Exemplo didático: NVDA e Chromium, modo de navegação; início do documento; H até o título Contato, K até o link Política de privacidade, conferir o contexto. Só use essa sequência se esses elementos foram realmente encontrados. A orientação proposta não deve afirmar que o leitor anunciou essas palavras em uma execução.

Fonte dos comandos NVDA, consultada em 30/10/2026: https://download.nvaccess.org/documentation/en/userGuide.html#SingleLetterNavigation .

## Modelo do relatório (planilha, Word e PDF)

O mesmo modelo vale para os três formatos. O que o relatório mostra vem só do que foi registrado em `a11y_finding` e em `report_context`:

- **Uma tela, uma aba (xlsx) e uma seção (Word e PDF).** Registre `screen` em cada achado ("Todas as telas" para o que se repete em toda a página) e liste as telas testadas em `report_context.screens`, na ordem das abas. Tela testada sem achado ganha a própria aba, com o que foi testado, o que não foi testado e o que foi observado. Não existe uma aba única de achados.
- **Passos em duas células.** "Com visão" é para pessoa com baixa visão ou QA de acessibilidade: o que abrir, olhar, clicar e apertar no teclado olhando o contorno de foco. "Sem visão" é para quem de fato usa leitor de tela e não enxerga a tela: cada passo com a tecla apertada (Tab, Shift+Tab, Enter, setas, letras do modo de navegação como D, B, K, E, H e Ctrl+Home) e a fala exata do leitor. Só entra como executado o que foi executado e lido no leitor real; o resto vai em `reproduction_steps_screen_reader_proposed` e sai rotulado como roteiro sugerido.
- **Teclas e falas conferidas.** Antes de escrever um passo, rode as teclas no leitor e copie a fala. A mesma tecla pode falar diferente em outro modo (por exemplo, Tab fala "botão de alternância, não pressionado" e a letra B fala "botão, não marcado").
- **Código em duas células.** `code_snippet` é o código real do problema (HTML, JS ou CSS), copiado da página ou do arquivo observado com a origem (URL do arquivo e posição aproximada). `fixed_code` é o código corrigido sugerido, escrito a partir dele; é sugestão, não aplicada nem testada no site.
- **Elemento e seletor descritos em palavras** que o desenvolvedor encontra na página; não use seletores que só a ferramenta entende (como `:has-text`).
