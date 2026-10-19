Leitor de tela: exemplos bons e ruins (feito e medido com o próprio MCP)

Oito cenários (títulos, listas, links, botões, campos de formulário, imagens, tabelas e avisos que aparecem sem recarregar), cada um com um exemplo ruim, um bom e, quando existe, um que parece estranho mas não precisa de correção. Os exemplos estão vivos na página, para ouvir no seu leitor de tela e comparar. Embaixo de cada um: por que é ruim ou bom, o que corrigir, o que o navegador entrega ao leitor de tela e o que o axe acha.

Como gerar: python demo/exemplos-leitor-de-tela/construir.py. O texto dos exemplos está em exemplos.py. A árvore de acessibilidade e o resultado do axe não são escritos à mão: o gerador abre cada exemplo no Chromium e mede com o código do próprio MCP.

O que os testes garantem (tests/test_demo_exemplos.py): todo cenário tem um exemplo ruim e um bom; todo exemplo bom ou "não precisa corrigir" passa no axe sem violação; o exemplo ruim entrega ao leitor de tela uma árvore diferente da do bom; e a lista de cartões com título dentro do item (exemplo ruim) entrega o título com o nível do próprio h3, dentro do item da lista, nunca nível 1. É ruim porque a mesma informação sai duas vezes (lista e títulos), contra o guia aria-rules-dos-and-donts; o exemplo bom é a lista de links com descrição.

O que se descobriu testando este site com o MCP, e já foi corrigido, está na seção 22 de docs/AUDITORIA.md. Nos exemplos de títulos os títulos vivos começam em h3, porque a própria página já usa h1 e h2.

Não foi ouvido com o NVDA de verdade (depende da VM, nvda/vm/LEIAME.md). Os exemplos ruins são ruins de propósito: o rastreamento (a11y_crawl) acha neles só o esperado, label em campos, image-alt em imagens e o salto de nível nos títulos.
