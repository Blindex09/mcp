# Inspeção do elemento pelo CDP (a11y_inspect)

Data: 24/11/2026. Pedido do dono depois de um teste real na página /contato da WeCover: a medição do código da página tinha de ser a do painel de inspeção do navegador.

## O que o módulo entrega

A ferramenta `a11y_inspect(target, properties, states)` mede um elemento pelo CDP do Chromium e devolve só fatos. O modelo do cliente julga. Cada chamada grava um passo no rastro, devolvido como `trace_step`, para citar em `a11y_finding`.

- O `outerHTML` completo do elemento, com os atributos `style` e os svg inteiros. Só a marca `data-a11y-id`, posta pela própria ferramenta, é retirada. Prova: `test_inspect_returns_what_devtools_shows_for_an_element`.
- Todos os atributos e o estilo inline. Prova: o mesmo teste.
- As regras de CSS que se aplicam e as herdadas, cada uma com origem, folha, linha, coluna e o texto original da regra, lido da própria folha. A linha de uma folha embutida no HTML é somada à linha em que o `style` abre no documento. Prova: o mesmo teste (a regra `.cta` na linha 3 do documento).
- O estilo calculado, com um conjunto padrão de propriedades de leitura, foco, alvo de toque e visibilidade, ou as propriedades que a pessoa pedir. Prova: o mesmo teste e `test_listeners_and_technology_markers_are_reported_as_facts`.
- O que muda sob `:hover`, `:focus`, `:focus-visible` e `:active` forçados no navegador. Prova: `test_forced_states_show_what_changes_on_hover_and_focus_visible`.
- Os ouvintes de evento do elemento, com arquivo, linha, coluna e o início do código do ouvinte, lido por `Debugger.getScriptSource`. Em script embutido, o CDP dá a posição no documento e o módulo a converte para a posição no texto do script. Prova: `test_listeners_and_technology_markers_are_reported_as_facts`.
- A caixa do elemento (conteúdo, padding, borda e margem) e a entrada de acessibilidade (papel, nome, origem do nome, propriedades). Prova: `test_inspect_returns_what_devtools_shows_for_an_element`.
- As tecnologias da página: marcas de React, Vue, Angular, Svelte, Next, Nuxt, jQuery e web components, e quais arquivos servidos declaram source map. Prova: `test_listeners_and_technology_markers_are_reported_as_facts`.
- Elemento que não existe é recusado com a mensagem de sempre. Prova: `test_inspect_refuses_a_missing_element`.
- A ferramenta está registrada, devolve `trace_step` e a lista de ferramentas do servidor a inclui. Prova: `test_the_tool_is_registered_and_leaves_a_trace_step` e `test_server.py`.

O alvo é resolvido por `Session.cdp_node`, extraído de `focus_style` para os dois usarem o mesmo caminho. O caminho atravessa iframes e Shadow DOM quando o dossiê já numerou o elemento.

## O que foi medido de verdade

Em 24/11/2026, em https://wecover.travel/contato, com o cartão do WhatsApp e o texto legal do rodapé: React encontrado, nenhum dos 10 arquivos servidos com source map, estilo inline do cartão completo (inclusive `outline:none`) e `:focus` forçado sem mudança, porque o estilo de foco do cartão é aplicado por JavaScript em `onFocus`.

## O que não está provado e os limites

- Estado forçado não dispara eventos da página. Estilo aplicado por JavaScript em `onFocus` ou `onMouseEnter` não aparece em `state_changes`; confirmar com Tab real e `a11y_screenshot`. Isso já enganou uma medição de foco e está dito no resultado da ferramenta.
- React delega ouvintes ao elemento raiz ou ao `document`: o ouvinte do elemento fica vazio e os delegados aparecem em `a11y_page_map`.
- O CDP situa a função do ouvinte na lista de parâmetros, então o trecho do código começa ali.
- Marca de biblioteca é vestígio: ausência de marca não prova que a biblioteca não é usada. Marca de React é lida nos primeiros 400 elementos do corpo.
- A lista de regras herdadas inclui as regras padrão do navegador e fica longa. Pendência de apresentação.
- Só Chromium. Em Firefox e WebKit a ferramenta diz que a inspeção usa o CDP.
- Os textos que ensinam o modelo citam `a11y_inspect`: `testing-playbook-for-ai`, `report-writing-style`, o fluxo `a11y_deliver_audit` e as instruções do servidor, inclusive o limite do estado forçado e a regra de que todo achado leva um alvo que exista na página. Por ser mudança de instrução ao modelo, o portão da regra 15 (conjunto amplo, tentativas repetidas e ablação) exige um modelo e não foi rodado; fica como pendência declarada.
