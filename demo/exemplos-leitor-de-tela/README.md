Leitor de tela: exemplos bons e ruins (feito e medido com o próprio MCP)

Trinta cenários: oito de estrutura (títulos, listas, links, botões, campos de formulário, imagens, tabelas e avisos), CSS e AJAX, sete de comportamento (diálogo, acordeão, abas, menu de ações, combobox, erro de formulário e mudança de tela), sete de componentes (carrossel, dica, lista de opções, árvore, tabela ordenável, Web Components e resposta de IA em streaming), quatro frameworks reais (React, Vue, Svelte e Angular, os mesmos cinco componentes em cada um) e dois de mobile (Android Compose e iOS SwiftUI, só código e regra, não executados), cada um com um exemplo ruim, um bom e, quando existe, um que parece estranho mas não precisa de correção. Os exemplos estão vivos na página, para ouvir no seu leitor de tela e comparar. Embaixo de cada um: por que é ruim ou bom, o que corrigir, o que o navegador entrega ao leitor de tela e o que o axe acha.

Como gerar: python demo/exemplos-leitor-de-tela/construir.py. O texto dos exemplos está em exemplos.py. A árvore de acessibilidade e o resultado do axe não são escritos à mão: o gerador abre cada exemplo no Chromium e mede com o código do próprio MCP.

O que os testes garantem (tests/test_demo_exemplos.py): todo cenário tem um exemplo ruim e um bom; todo exemplo bom ou "não precisa corrigir" passa no axe sem violação; o exemplo ruim entrega ao leitor de tela uma árvore diferente da do bom; e a lista de cartões com título dentro do item (exemplo ruim) entrega o título com o nível do próprio h3, dentro do item da lista, nunca nível 1. É ruim porque a mesma informação sai duas vezes (lista e títulos), contra o guia aria-rules-dos-and-donts; o exemplo bom é a lista de links com descrição.

O que se descobriu testando este site com o MCP, e já foi corrigido, está na seção 22 de docs/AUDITORIA.md. Nos exemplos de títulos os títulos vivos começam em h3, porque a própria página já usa h1 e h2.

Não foi ouvido com o NVDA de verdade (depende da VM, nvda/vm/LEIAME.md). Os exemplos ruins são ruins de propósito: o rastreamento (a11y_crawl) acha neles só o esperado, label em campos, image-alt em imagens e o salto de nível nos títulos.

Cenários interativos: cada exemplo traz o código com o próprio script e a sonda do MCP que o mede (interativos.py). Embaixo de cada exemplo aparece o que a sonda mediu apertando as teclas num navegador de verdade, esperado contra observado. Os testes estão em tests/test_demo_interativos.py. A auditoria ao vivo, com a página servida, as outras personas e o Firefox e o WebKit, está na seção 23 de docs/AUDITORIA.md.

Frameworks: o código de cada componente fica em frameworks/src (react.jsx, vue.js, svelte/*.svelte, angular.ts) e é compilado por frameworks/build.mjs (npm install e node build.mjs dentro de frameworks) para os pacotes app-*.js, que ficam versionados para os testes não dependerem de npm. O gerador mede a página já montada pelo framework e mostra, no Svelte, os avisos de acessibilidade que o próprio compilador emitiu.

Categorias de exemplo: ruim, bom, não precisa corrigir e, quando o MCP não consegue provar o defeito aqui, "depende do navegador, não medido aqui". Mobile fica sempre como código e regra, com a frase "Não executado aqui".

Copiar código: todo bloco de código tem, logo abaixo do título Código, o botão "Copiar código para a área de transferência" (copiar.js). Ele copia o texto do bloco, mantém o foco no botão, mostra o selo "Código copiado" enquanto o foco fica ali e avisa o leitor de tela numa região de status que já está na página; se o navegador recusar, avisa que não foi possível e orienta a copiar à mão. O nome acessível do botão começa pelo texto visível e termina com o título do exemplo, para os vários botões da página não terem o mesmo nome.

