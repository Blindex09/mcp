Leitor de tela: o que a pessoa ouve (site de pesquisas, feito e testado com o próprio MCP)

Este site mostra as 6 pesquisas sobre o comportamento do leitor de tela: elementos HTML, estrutura e navegação, ARIA, CSS e modos de leitura, ações do teclado e conteúdo dinâmico. As páginas são geradas das pesquisas que o MCP guarda em accessibility_mcp/a11y/content/references, com o comando python demo/leitor-de-tela/construir.py. Para ver, abra index.html no navegador ou sirva a pasta (python -m http.server).

Foi feito seguindo o que o próprio MCP recomenda (a11y_get_example html-semantic-foundation e css-accessibility) e depois testado com ele, para achar defeitos no site e no MCP. O que foi provado, com a ferramenta que provou:
- Auditoria automática até o nível AAA nas 7 páginas, sem violações (a11y_crawl).
- Teclado: 22 paradas lógicas na página mais longa, nenhuma presa, foco sempre visível, nada coberto, todos os alvos com 24 px ou mais (a11y_probe tab_walk, target_size, focus_obscured). O link de pular leva o foco ao conteúdo (a11y_probe route_change).
- Zoom em 320 px sem rolagem horizontal e espaçamento de texto sem corte (a11y_stress).
- Contraste dos links e do tema escuro acima de 7:1 (a11y_contrast).
- Mesma árvore de acessibilidade no Chromium, no Firefox e no WebKit (a11y_compare_browsers).

O que o teste achou no site e foi corrigido: landmarks demais (cada seção virou uma região, de 18 para 6 por página), contraste dos links abaixo de 7:1, e título da aba com até 25 palavras.

O que não foi provado: o site não foi ouvido com o NVDA de verdade. Isso depende da VM (nvda/vm/LEIAME.md).
