"""Cenarios de CSS e de AJAX do site de exemplos (JavaScript puro).

CSS: o mesmo conteudo, mas o estilo muda o que o leitor de tela recebe, o que o teclado alcanca e o que o usuario le.
AJAX: o conteudo chega depois do clique; quem nao ve a tela precisa saber que carregou, que falhou e que chegou mais.
Os ids terminam em -ruim / -bom. A chave "extra" diz que medida a mais o gerador faz (construir.py): foco, espacamento, alcance, WebKit, movimento.
"""

from __future__ import annotations

from typing import Any

CSS_AJAX: list[dict[str, Any]] = [
    {
        "slug": "css",
        "nome": "CSS",
        "resumo": "O CSS muda o que o leitor de tela recebe (texto escondido, lista sem marcador), o que o teclado alcança (menu aberto só com mouse), o que se vê no foco, no espaçamento de texto e no movimento. Cada exemplo é medido pelo MCP.",
        "exemplos": [
            {
                "tipo": "ruim", "titulo": "Foco do teclado removido",
                "extra": ("focus_style", "css:#foco-ruim-btn"),
                "html": '<style>#foco-ruim-btn{outline:none !important}</style><button type="button" id="foco-ruim-btn">Comprar</button>',
                "porque": "Quem navega com Tab não vê onde está. O outline:none apaga o anel de foco e nada o substitui; a medida mostra que o :focus não muda nenhuma propriedade visível.",
                "corrigir": "Não remova o outline. Se o anel padrão não combina com o design, troque por um :focus-visible com contraste (anel de 2 px ou mais, com 3:1 contra o fundo).",
            },
            {
                "tipo": "bom", "titulo": "Foco visível",
                "extra": ("focus_style", "css:#foco-bom-btn"),
                "html": '<button type="button" id="foco-bom-btn">Comprar</button>',
                "porque": "O botão mantém o anel de foco. A medida mostra o que o :focus muda.",
                "corrigir": "Nada a corrigir.",
            },
            {
                "tipo": "ruim", "titulo": "Texto para leitor de tela escondido com display:none",
                "html": '<style>.so-leitor-ruim{display:none}</style><p><a href="#relatorio">Relatório<span class="so-leitor-ruim"> (abre em nova janela)</span></a></p>',
                "porque": "Quem enxerga não vê o aviso, e quem usa leitor de tela também não: display:none tira o elemento da árvore de acessibilidade. O nome do link continua só Relatório.",
                "corrigir": "Use a técnica de ocultar só visualmente (clip, 1 px, posição absoluta), que mantém o texto na árvore.",
            },
            {
                "tipo": "bom", "titulo": "Texto só para leitor de tela",
                "html": '<style>.so-leitor-bom{position:absolute;width:1px;height:1px;margin:-1px;padding:0;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0}</style>'
                        '<p><a href="#relatorio">Relatório<span class="so-leitor-bom"> (abre em nova janela)</span></a></p>',
                "porque": "O texto fica fora da vista mas dentro da árvore: o nome do link passa a ser Relatório (abre em nova janela).",
                "corrigir": "Nada a corrigir.",
            },
            {
                "tipo": "incerto", "titulo": "Lista sem marcador e sem role",
                "extra": ("webkit_tree", None),
                "html": '<ul style="list-style:none;padding:0;margin:0"><li>Sencha</li><li>Matcha</li><li>Gyokuro</li></ul>',
                "porque": "O guia do MCP registra que o Safari com VoiceOver já deixou de anunciar como lista a ul com list-style:none. Esta medida não consegue provar isso: no Chromium e no WebKit do Playwright a lista continua sendo lista (veja as duas árvores abaixo). Quem tem um Mac deve ouvir no Safari.",
                "corrigir": "Por precaução, acrescente role=\"list\" na ul sem marcador. Não custa nada e vale em todos os navegadores.",
            },
            {
                "tipo": "bom", "titulo": "Lista sem marcador com role=list",
                "extra": ("webkit_tree", None),
                "html": '<ul role="list" style="list-style:none;padding:0;margin:0"><li>Sencha</li><li>Matcha</li><li>Gyokuro</li></ul>',
                "porque": "O role=list devolve a semântica onde o estilo a tira.",
                "corrigir": "Nada a corrigir.",
            },
            {
                "tipo": "ruim", "titulo": "Submenu que só abre com o mouse (:hover)",
                "extra": ("alcance", None),
                "html": '<style>.menu-ruim{list-style:none;margin:0;padding:0}.menu-ruim ul{display:none;list-style:none;margin:0;padding:0 0 0 1rem}.menu-ruim li:hover>ul{display:block}</style>'
                        '<ul class="menu-ruim"><li><a href="#produtos">Produtos</a><ul><li><a href="#chas">Chás</a></li><li><a href="#bules">Bules</a></li></ul></li></ul>',
                "porque": "Com o mouse o submenu aparece. Com o teclado, o submenu fica em display:none e os links de dentro não recebem foco: Chás e Bules são inalcançáveis.",
                "corrigir": "Mostre o submenu também com :focus-within, ou use um botão de disclosure com aria-expanded.",
            },
            {
                "tipo": "bom", "titulo": "Submenu que abre também com o foco",
                "extra": ("alcance", None),
                "html": '<style>.menu-bom{list-style:none;margin:0;padding:0}.menu-bom ul{display:none;list-style:none;margin:0;padding:0 0 0 1rem}.menu-bom li:hover>ul,.menu-bom li:focus-within>ul{display:block}</style>'
                        '<ul class="menu-bom"><li><a href="#produtos">Produtos</a><ul><li><a href="#chas">Chás</a></li><li><a href="#bules">Bules</a></li></ul></li></ul>',
                "porque": "O :focus-within mostra o submenu quando o foco entra no item, e o Tab alcança todos os links.",
                "corrigir": "Nada a corrigir (para menu de comandos ou submenu longo, prefira o botão com aria-expanded).",
            },
            {
                "tipo": "ruim", "titulo": "Altura fixa que corta o texto com o espaçamento do usuário",
                "extra": ("stress", "text_spacing"),
                "html": '<p style="width:34rem;max-width:100%;height:1.5em;overflow:hidden;line-height:1.5;margin:0">Frete grátis para todo o Brasil em compras acima de cem reais</p>',
                "porque": "Quem aumenta o espaçamento entre letras, palavras e linhas (WCAG 1.4.12) vê a segunda linha cortada: a altura é fixa e o excesso fica escondido.",
                "corrigir": "Use min-height (ou nenhuma altura) e não esconda o excesso com overflow:hidden.",
            },
            {
                "tipo": "bom", "titulo": "Altura que cresce com o texto",
                "extra": ("stress", "text_spacing"),
                "html": '<p style="width:34rem;max-width:100%;min-height:1.5em;line-height:1.5;margin:0">Frete grátis para todo o Brasil em compras acima de cem reais</p>',
                "porque": "A caixa cresce com o texto e nada é cortado com o espaçamento do usuário.",
                "corrigir": "Nada a corrigir.",
            },
            {
                "tipo": "ruim", "titulo": "Texto cinza claro sobre branco",
                "html": '<p style="color:#9a9a9a;background:#ffffff;margin:0;padding:0.5rem">Entrega em até cinco dias úteis</p>',
                "porque": "O contraste é de cerca de 2,8 para 1; o mínimo do WCAG para texto comum é 4,5 para 1. Pessoas com baixa visão não leem.",
                "corrigir": "Use uma cor de texto mais escura (por exemplo #595959, perto de 7 para 1). Meça com a ferramenta de contraste do MCP.",
            },
            {
                "tipo": "bom", "titulo": "Texto com contraste suficiente",
                "html": '<p style="color:#595959;background:#ffffff;margin:0;padding:0.5rem">Entrega em até cinco dias úteis</p>',
                "porque": "Cerca de 7 para 1 sobre branco: passa o nível AA e o AAA.",
                "corrigir": "Nada a corrigir.",
            },
            {
                "tipo": "ruim", "titulo": "Animação que ignora a preferência por menos movimento",
                "extra": ("movimento", "css:#mov-ruim"),
                "html": '<style>@keyframes gira-ruim{to{transform:rotate(360deg)}}#mov-ruim{display:inline-block;animation:gira-ruim 2s linear infinite}</style><p><span id="mov-ruim">&#9679;</span> Atualizando</p>',
                "porque": "Quem pede menos movimento no sistema (prefers-reduced-motion) continua vendo o giro infinito. Para algumas pessoas isso causa náusea ou tontura.",
                "corrigir": "Dentro de @media (prefers-reduced-motion: reduce) desligue ou reduza a animação.",
            },
            {
                "tipo": "bom", "titulo": "Animação que respeita a preferência",
                "extra": ("movimento", "css:#mov-bom"),
                "html": '<style>@keyframes gira-bom{to{transform:rotate(360deg)}}#mov-bom{display:inline-block;animation:gira-bom 2s linear infinite}@media (prefers-reduced-motion: reduce){#mov-bom{animation:none}}</style><p><span id="mov-bom">&#9679;</span> Atualizando</p>',
                "porque": "Com a preferência ligada a animação some; a medida abaixo emula a preferência e confere.",
                "corrigir": "Nada a corrigir.",
            },
        ],
    },
    {
        "slug": "ajax",
        "nome": "AJAX (conteúdo que chega depois)",
        "resumo": "Quando o conteúdo chega depois do clique, o leitor de tela não ouve nada se a página não avisar. Os três casos: carregar resultados, falhar com nova tentativa e carregar mais. Cada exemplo é medido apertando Enter no botão.",
        "exemplos": [
            {
                "tipo": "ruim", "titulo": "Resultados que aparecem em silêncio",
                "sonda": ("status_update", "css:#aj1-ruim-btn"),
                "html": '<button type="button" id="aj1-ruim-btn">Buscar chás</button><ul id="aj1-ruim-lista"></ul>'
                        "<script>(function(){var l=document.getElementById('aj1-ruim-lista');document.getElementById('aj1-ruim-btn').addEventListener('click',function(){"
                        "fetch('data:application/json,%5B%22Sencha%22,%22Matcha%22,%22Gyokuro%22%5D').then(function(r){return r.json();}).then(function(chas){"
                        "setTimeout(function(){l.innerHTML=chas.map(function(c){return '<li>'+c+'</li>';}).join('');},150);});});})();</script>",
                "porque": "A lista aparece, mas ninguém fala nada: não há aviso de carregando nem de quantos resultados chegaram, e o foco continua no botão.",
                "corrigir": "Mantenha uma região role=status na página, escreva nela Carregando e depois a quantidade de resultados, e marque a lista com aria-busy enquanto carrega.",
            },
            {
                "tipo": "bom", "titulo": "Carregando e resultados anunciados",
                "sonda": ("status_update", "css:#aj1-bom-btn"),
                "html": '<button type="button" id="aj1-bom-btn">Buscar chás</button><div role="status" id="aj1-bom-status"></div><ul id="aj1-bom-lista" aria-busy="false"></ul>'
                        "<script>(function(){var l=document.getElementById('aj1-bom-lista'),s=document.getElementById('aj1-bom-status');document.getElementById('aj1-bom-btn').addEventListener('click',function(){"
                        "s.textContent='Carregando chás…';l.setAttribute('aria-busy','true');"
                        "fetch('data:application/json,%5B%22Sencha%22,%22Matcha%22,%22Gyokuro%22%5D').then(function(r){return r.json();}).then(function(chas){"
                        "setTimeout(function(){l.innerHTML=chas.map(function(c){return '<li>'+c+'</li>';}).join('');l.setAttribute('aria-busy','false');s.textContent=chas.length+' chás encontrados';},150);});});})();</script>",
                "porque": "A região de status já estava na página: o leitor de tela fala Carregando chás e depois 3 chás encontrados.",
                "corrigir": "Nada a corrigir.",
            },
            {
                "tipo": "ruim", "titulo": "Falha sem aviso e sem nova tentativa",
                "sonda": ("status_update", "css:#aj2-ruim-btn"),
                "html": '<button type="button" id="aj2-ruim-btn">Carregar pedidos</button><div id="aj2-ruim-msg" class="erro-visual"></div>'
                        "<script>document.getElementById('aj2-ruim-btn').addEventListener('click',function(){new Promise(function(_,no){setTimeout(function(){no(new Error('rede'));},150);})"
                        ".catch(function(){document.getElementById('aj2-ruim-msg').textContent='Falhou.';});});</script>",
                "porque": "A falha aparece como texto vermelho solto: nenhuma região viva a anuncia, a frase não diz o que fazer e não há como tentar de novo.",
                "corrigir": "Mostre a falha numa região role=alert que já exista, diga o que aconteceu e ofereça o botão Tentar de novo.",
            },
            {
                "tipo": "bom", "titulo": "Falha anunciada, com nova tentativa",
                "sonda": ("status_update", "css:#aj2-bom-btn"),
                "html": '<button type="button" id="aj2-bom-btn">Carregar pedidos</button><div id="aj2-bom-msg" class="erro-visual" role="alert"></div>'
                        "<script>(function(){var b=document.getElementById('aj2-bom-btn');b.addEventListener('click',function(){new Promise(function(_,no){setTimeout(function(){no(new Error('rede'));},150);})"
                        ".catch(function(){document.getElementById('aj2-bom-msg').textContent='Não foi possível carregar os pedidos. Verifique a conexão e tente de novo.';b.textContent='Tentar de novo';});});})();</script>",
                "porque": "A região role=alert já estava na página, a mensagem diz o que fazer e o botão passa a se chamar Tentar de novo, com o foco ainda nele.",
                "corrigir": "Nada a corrigir.",
            },
            {
                "tipo": "ruim", "titulo": "Carregar mais que faz o foco desaparecer",
                "sonda": ("status_update", "css:#aj3-ruim-btn"),
                "html": '<ul id="aj3-ruim-lista"><li>Chá 1</li><li>Chá 2</li><li>Chá 3</li></ul><div id="aj3-ruim-host"><button type="button" id="aj3-ruim-btn">Carregar mais</button></div>'
                        "<script>document.getElementById('aj3-ruim-btn').addEventListener('click',function(){setTimeout(function(){"
                        "document.getElementById('aj3-ruim-lista').insertAdjacentHTML('beforeend','<li>Chá 4</li><li>Chá 5</li><li>Chá 6</li>');document.getElementById('aj3-ruim-host').innerHTML='';},150);});</script>",
                "porque": "O botão é apagado ao carregar: o foco cai no corpo da página e quem usa teclado precisa começar de novo. Nada anuncia que chegaram mais itens.",
                "corrigir": "Não remova o botão em que o foco está. Mantenha-o (ou mova o foco para o primeiro item novo) e anuncie a quantidade numa região de status.",
            },
            {
                "tipo": "bom", "titulo": "Carregar mais com foco mantido e quantidade anunciada",
                "sonda": ("status_update", "css:#aj3-bom-btn"),
                "html": '<ul id="aj3-bom-lista"><li>Chá 1</li><li>Chá 2</li><li>Chá 3</li></ul><button type="button" id="aj3-bom-btn">Carregar mais</button><div role="status" id="aj3-bom-status"></div>'
                        "<script>document.getElementById('aj3-bom-btn').addEventListener('click',function(){setTimeout(function(){"
                        "document.getElementById('aj3-bom-lista').insertAdjacentHTML('beforeend','<li>Chá 4</li><li>Chá 5</li><li>Chá 6</li>');document.getElementById('aj3-bom-status').textContent='3 itens a mais, 6 no total';},150);});</script>",
                "porque": "O botão fica onde está, com o foco, e a região de status fala 3 itens a mais, 6 no total.",
                "corrigir": "Nada a corrigir.",
            },
        ],
    },
]
