Casa do Chá: demonstração de que o axe verde não significa acessível

Este site pequeno existe em três versões, verificadas pelas mesmas medições do MCP com o comando python demo/loja/verificar.py.

Versões
- v1-original: como um site real costuma nascer. Funciona com mouse e tem defeitos genéricos e defeitos de julgamento.
- v2-axe-verde: só o que o axe apontou foi corrigido (idioma, texto alternativo, nome do botão do carrinho e contraste).
- v3-corrigido: correção de verdade, com a semântica certa, teclado, leitor de tela, foco, reflow e escala de design, mantendo o visual.

Duas camadas separadas

Camada genérica (varredura automática com o axe). Na v1 acha 4 regras: nome do botão do carrinho, texto alternativo das imagens, contraste e idioma da página. Na v2 e na v3 acha zero.

Camada de julgamento (agir como um usuário). Só aparece usando o site. A bateria roda com a persona de teclado, que o servidor impõe sem mouse:
- escolher a categoria, abrir o menu Produtos, abrir uma pergunta do FAQ e comprar um chá, tudo só com teclado;
- controles só de mouse, o papel do campo de categoria calculado pelo navegador, o aviso de compra anunciado, o foco visível, o reflow em 320 px e a linguagem de design.

Resultado: a v1 falha em quase tudo, a v2 passa no axe mas falha nas mesmas coisas da v1 (é o verde que engana), e a v3 passa em toda a bateria fixa deste script (python demo/loja/verificar.py).

O que cada componente é naquele site
- O campo Categoria com opções que filtram ao digitar é um combobox editável. Na v1 era um campo de texto com divs clicáveis. Na v3 tem papel de combobox, lista com opções, setas, Enter, Escape, Home e End.
- O item Produtos com links dentro é navegação com submenu, não um menu de comandos. Na v1 abria só com hover. Na v3 é um botão com estado expandido e uma lista de links.
- As perguntas do FAQ são um acordeão. Na v1 eram divs clicáveis. Na v3 são botões com estado expandido.
- O Comprar é um botão. Na v1 eram divs clicáveis. Na v3 são botões com nome único e alvo de 44 px.
- O aviso Adicionado ao carrinho é uma mensagem de status. Na v1 não era anunciada. Na v3 é uma região de status presente desde o carregamento.

Design
A medição da v1 mostrou corpo em 13 px com entrelinha 1,1, três famílias de fonte, oito tamanhos e treze valores de espaçamento soltos. A v3 mantém a identidade (verde da marca, títulos em Georgia, corpo em Arial) com escala de 14, 16, 20, 24 e 32 px, entrelinha 1,5 e espaçamentos em múltiplos de 8. A proposta foi testada antes com a pré-visualização do MCP, e esse teste acusou rolagem horizontal em 320 px por falta de quebra de linha nos cartões, corrigida na v3.

Limites conhecidos
- O gatilho do menu Produtos da v1 não aparece na lista do dossiê porque só reage a hover em CSS. Ele foi achado passando o mouse e vendo a árvore mudar. O mapa da página agora aponta as regras de hover das folhas de estilo.
- A medição de espaçamento conta valores calculados, então uma margem automática vira um número em pixels.
- A bateria completa roda no Chromium. Não é leitor de tela real.

Confirmação ao vivo com o agente autônomo (setembro de 2026)
Além da bateria fixa do verificar.py, a v1 e a v3 foram testadas de novo com a11y_walkthrough de verdade (ferramenta removida em 2026-10-19: o servidor deixou de chamar modelo), contra o Ollama Cloud, usando o pipeline de 3 papéis (visão descreve a tela, deepseek-v4.1-flash raciocina, gpt-oss:120b escreve o relatório), pedindo à persona de teclado para comprar um chá verde. Na v1 o agente tentou onze ações reais (tabular, digitar "Chá verde" no filtro, confirmar com Enter, sondar com announce o botão sem nome do cabeçalho) e nunca conseguiu comprar: todo caminho termina num controle sem foco. Na v3 o agente completou a compra em poucos passos, mas achou dois atritos que a bateria fixa do verificar.py não cobre, porque ela só confirma que o foco chega até "Chás" (t2), não o que acontece depois: ao abrir o menu Produtos os itens aparecem como listitem vazio na árvore (sem rótulo, e o foco não pula para o primeiro item ao expandir), e ao ativar o link "Chás" o foco se perde por completo, obrigando quem usa teclado a recomeçar a tabulação do zero. Ou seja, "a v3 passa em tudo" vale para a bateria fixa; testar com um agente que persegue um objetivo livre, sem passos fixados de antemão, achou uma fricção mais fina, que o script determinístico nunca chega a perguntar. Isso é o próprio ponto do projeto: verde automatizado (ou bateria fixa) não é o mesmo que comprovadamente usável.
