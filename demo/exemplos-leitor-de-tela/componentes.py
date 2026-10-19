"""Mais componentes do catalogo do MCP, em JavaScript puro e Web Components: carrossel, dica (tooltip), lista de opcoes, arvore, tabela ordenavel,
elemento personalizado e resposta de IA em streaming. Cada um tem o exemplo ruim e o bom, medidos pela sonda que existe para ele.
Os ids terminam em -ruim / -bom (os exemplos de um cenario vivem na mesma pagina).
"""

from __future__ import annotations

from typing import Any

COMPONENTES: list[dict[str, Any]] = [
    {
        "slug": "carrossel",
        "nome": "Carrossel",
        "resumo": "Um carrossel precisa ser anunciado como carrossel, dizer em que slide está e avisar quando o slide muda. Controles sem nome (só uma seta) não dizem o que fazem. Este cenário não tem rotação automática; se tivesse, precisaria de um botão de pausa como primeiro controle e respeitar prefers-reduced-motion (WCAG 2.2.2).",
        "exemplos": [
            {
                "tipo": "ruim", "titulo": "Setas sem nome e troca de slide calada",
                "sonda": ("status_update", "css:#car-ruim-prox"),
                "html": '<div id="car-ruim"><div class="slide-ruim">Slide 1: chá verde</div><div class="slide-ruim" hidden>Slide 2: chá preto</div><div class="slide-ruim" hidden>Slide 3: chá branco</div></div>'
                        '<button type="button" id="car-ruim-ant">&#9664;</button> <button type="button" id="car-ruim-prox">&#9654;</button>'
                        "<script>(function(){var s=Array.prototype.slice.call(document.querySelectorAll('#car-ruim .slide-ruim')),a=0;"
                        "function ir(d){a=(a+d+s.length)%s.length;s.forEach(function(e,i){e.hidden=i!==a;});}"
                        "document.getElementById('car-ruim-ant').addEventListener('click',function(){ir(-1);});document.getElementById('car-ruim-prox').addEventListener('click',function(){ir(1);});})();</script>",
                "porque": "Os botões se chamam só &#9664; e &#9654;, o leitor de tela diz o símbolo ou nada. O slide muda, mas nenhuma região avisa: quem não vê não sabe que mudou nem qual é.",
                "corrigir": "Nomeie os botões (Slide anterior, Próximo slide), marque o conjunto com aria-roledescription=\"carousel\" e cada slide com aria-roledescription=\"slide\" e \"1 de 3\", e avise a troca numa região de status que já exista.",
            },
            {
                "tipo": "bom", "titulo": "Carrossel no padrão do APG, sem rotação automática",
                "sonda": ("status_update", "css:#car-bom-prox"),
                "html": '<section aria-roledescription="carousel" aria-label="Chás em destaque"><div id="car-bom">'
                        '<div class="slide-bom" role="group" aria-roledescription="slide" aria-label="1 de 3">Slide 1: chá verde</div>'
                        '<div class="slide-bom" role="group" aria-roledescription="slide" aria-label="2 de 3" hidden>Slide 2: chá preto</div>'
                        '<div class="slide-bom" role="group" aria-roledescription="slide" aria-label="3 de 3" hidden>Slide 3: chá branco</div></div>'
                        '<button type="button" id="car-bom-ant" aria-controls="car-bom">Slide anterior</button> <button type="button" id="car-bom-prox" aria-controls="car-bom">Próximo slide</button>'
                        '<div role="status" id="car-bom-aviso"></div></section>'
                        "<script>(function(){var s=Array.prototype.slice.call(document.querySelectorAll('#car-bom .slide-bom')),a=0;"
                        "function ir(d){a=(a+d+s.length)%s.length;s.forEach(function(e,i){e.hidden=i!==a;});document.getElementById('car-bom-aviso').textContent='Slide '+(a+1)+' de '+s.length;}"
                        "document.getElementById('car-bom-ant').addEventListener('click',function(){ir(-1);});document.getElementById('car-bom-prox').addEventListener('click',function(){ir(1);});})();</script>",
                "porque": "O conjunto é anunciado como carrossel, cada slide como slide com a posição, os botões têm nome e a região de status que já estava na página fala Slide 2 de 3.",
                "corrigir": "Nada a corrigir.",
            },
        ],
    },
    {
        "slug": "dica",
        "nome": "Dica (tooltip)",
        "resumo": "Uma dica precisa aparecer também quando o controle recebe o foco, estar ligada ao controle por aria-describedby e fechar com Escape sem tirar o foco. O atributo title sozinho não aparece para quem usa teclado.",
        "exemplos": [
            {
                "tipo": "ruim", "titulo": "Dica só com title",
                "sonda": ("tooltip", "css:#dica-ruim-btn"),
                "html": '<button type="button" id="dica-ruim-btn" title="Salva o rascunho sem publicar">Salvar</button>',
                "porque": "Com o mouse o navegador mostra a dica depois de um instante. Com o teclado ela não aparece, e leitores de tela leem o title de forma inconstante.",
                "corrigir": "Use um elemento role=tooltip ligado ao botão por aria-describedby, mostrado no foco e no mouse, e fechado com Escape.",
            },
            {
                "tipo": "ruim", "titulo": "Dica que só aparece com o mouse",
                "sonda": ("tooltip", "css:#dica-mouse-btn"),
                "html": '<button type="button" id="dica-mouse-btn" aria-describedby="dica-mouse-tip">Salvar</button><span role="tooltip" id="dica-mouse-tip" hidden>Salva o rascunho sem publicar</span>'
                        "<script>(function(){var b=document.getElementById('dica-mouse-btn'),t=document.getElementById('dica-mouse-tip');"
                        "b.addEventListener('mouseenter',function(){t.hidden=false;});b.addEventListener('mouseleave',function(){t.hidden=true;});})();</script>",
                "porque": "A ligação por aria-describedby está certa, mas a dica só abre no mouse: quem navega com Tab nunca a vê (WCAG 1.4.13 e 2.1.1).",
                "corrigir": "Abra também no focus e feche no blur e no Escape.",
            },
            {
                "tipo": "bom", "titulo": "Dica no foco, ligada ao botão e fechada com Escape",
                "sonda": ("tooltip", "css:#dica-bom-btn"),
                "html": '<button type="button" id="dica-bom-btn" aria-describedby="dica-bom-tip">Salvar</button><span role="tooltip" id="dica-bom-tip" hidden>Salva o rascunho sem publicar</span>'
                        "<script>(function(){var b=document.getElementById('dica-bom-btn'),t=document.getElementById('dica-bom-tip');"
                        "function abre(){t.hidden=false;}function fecha(){t.hidden=true;}"
                        "b.addEventListener('focus',abre);b.addEventListener('blur',fecha);b.addEventListener('mouseenter',abre);b.addEventListener('mouseleave',fecha);"
                        "b.addEventListener('keydown',function(e){if(e.key==='Escape')fecha();});})();</script>",
                "porque": "A dica aparece no foco e no mouse, o botão a descreve por aria-describedby e o Escape a fecha sem mover o foco.",
                "corrigir": "Nada a corrigir.",
            },
        ],
    },
    {
        "slug": "lista-de-opcoes",
        "nome": "Lista de opções (listbox)",
        "resumo": "Uma lista em que se escolhe uma opção precisa de role=listbox, opções com role=option, uma única parada de Tab e setas, Home e End para andar. Quem escolhe entre opções conhecidas usa as setas; nunca um campo para adivinhar.",
        "exemplos": [
            {
                "tipo": "ruim", "titulo": "Opções feitas de divs que só respondem ao mouse",
                "sonda": ("listbox", "css:#lb-ruim"),
                "html": '<div id="lb-ruim"><div class="op-ruim">Curitiba</div><div class="op-ruim">Recife</div><div class="op-ruim">Salvador</div></div>'
                        "<script>Array.prototype.forEach.call(document.querySelectorAll('.op-ruim'),function(o){o.style.cursor='pointer';o.addEventListener('click',function(){o.style.fontWeight='700';});});</script>",
                "porque": "Para quem vê é uma lista de opções. Para o leitor de tela são três linhas de texto, sem papel, sem nome, sem foco e sem teclado.",
                "corrigir": "Use role=listbox com nome, role=option nas opções, tabindex=0 na lista com aria-activedescendant (ou tabindex rotativo nas opções), setas, Home, End e aria-selected.",
            },
            {
                "tipo": "bom", "titulo": "Listbox no padrão do APG",
                "sonda": ("listbox", "css:#lb-bom"),
                "html": '<ul id="lb-bom" role="listbox" aria-label="Cidades" tabindex="0" aria-activedescendant="lb-bom-1" class="lista-opcoes">'
                        '<li role="option" id="lb-bom-1" aria-selected="false">Curitiba</li><li role="option" id="lb-bom-2" aria-selected="false">Recife</li><li role="option" id="lb-bom-3" aria-selected="false">Salvador</li></ul>'
                        "<script>(function(){var lb=document.getElementById('lb-bom'),op=Array.prototype.slice.call(lb.children),a=0;"
                        "function ir(i){a=i;lb.setAttribute('aria-activedescendant',op[i].id);}"
                        "function marcar(i){op.forEach(function(o,j){o.setAttribute('aria-selected',String(j===i));});}"
                        "lb.addEventListener('keydown',function(e){if(e.key==='ArrowDown'){e.preventDefault();ir(Math.min(a+1,op.length-1));}"
                        "else if(e.key==='ArrowUp'){e.preventDefault();ir(Math.max(a-1,0));}else if(e.key==='Home'){e.preventDefault();ir(0);}"
                        "else if(e.key==='End'){e.preventDefault();ir(op.length-1);}else if(e.key===' '||e.key==='Enter'){e.preventDefault();marcar(a);}});"
                        "op.forEach(function(o,i){o.addEventListener('click',function(){ir(i);marcar(i);});});})();</script>",
                "porque": "A lista é anunciada pelo nome, com a opção atual por aria-activedescendant; as setas andam, Home e End vão às pontas e Espaço ou Enter escolhem, com aria-selected.",
                "corrigir": "Nada a corrigir.",
            },
        ],
    },
    {
        "slug": "arvore",
        "nome": "Árvore (tree view)",
        "resumo": "Uma árvore de pastas e arquivos precisa de role=tree, itens treeitem, aria-expanded nos pais e as setas: para baixo e para cima andam, para a direita abre, para a esquerda fecha. Uma lista aninhada comum não faz nada disso.",
        "exemplos": [
            {
                "tipo": "ruim", "titulo": "Listas aninhadas abertas só com clique",
                "sonda": ("tree", "css:#arv-ruim"),
                "html": '<ul id="arv-ruim"><li><span class="pasta-ruim">Documentos</span><ul hidden><li>contrato.pdf</li><li>nota.txt</li></ul></li><li>leia-me.md</li></ul>'
                        "<script>Array.prototype.forEach.call(document.querySelectorAll('.pasta-ruim'),function(p){p.style.cursor='pointer';p.addEventListener('click',function(){var u=p.nextElementSibling;u.hidden=!u.hidden;});});</script>",
                "porque": "Só o mouse abre a pasta. O leitor de tela ouve uma lista, a pasta não é um controle, não diz se está aberta e o teclado não alcança nada.",
                "corrigir": "Use role=tree, role=treeitem, aria-expanded nas pastas, tabindex rotativo e as setas (direita abre, esquerda fecha, Home e End).",
            },
            {
                "tipo": "bom", "titulo": "Tree view no padrão do APG",
                "sonda": ("tree", "css:#arv-bom-doc"),
                "html": '<style>#arv-bom [role=group]{display:none;list-style:none;padding-left:1.25rem}#arv-bom [aria-expanded=true]>[role=group]{display:block}#arv-bom,#arv-bom ul{list-style:none;padding-left:1rem}'
                        '#arv-bom [role=treeitem]{padding:0.35rem 0.25rem}</style>'
                        '<ul id="arv-bom" role="tree" aria-label="Arquivos"><li role="treeitem" aria-expanded="false" tabindex="0" id="arv-bom-doc">Documentos'
                        '<ul role="group"><li role="treeitem" tabindex="-1">contrato.pdf</li><li role="treeitem" tabindex="-1">nota.txt</li></ul></li>'
                        '<li role="treeitem" tabindex="-1">leia-me.md</li></ul>'
                        "<script>(function(){var t=document.getElementById('arv-bom');"
                        "function vis(){return Array.prototype.slice.call(t.querySelectorAll('[role=treeitem]')).filter(function(e){var r=e.getBoundingClientRect();return r.width>0&&r.height>0;});}"
                        "function ir(el){t.querySelectorAll('[role=treeitem]').forEach(function(e){e.tabIndex=-1;});el.tabIndex=0;el.focus();}"
                        "t.addEventListener('keydown',function(e){var v=vis(),i=v.indexOf(document.activeElement),el=document.activeElement;e.stopPropagation();"
                        "if(e.key==='ArrowDown'){e.preventDefault();ir(v[Math.min(i+1,v.length-1)]);}else if(e.key==='ArrowUp'){e.preventDefault();ir(v[Math.max(i-1,0)]);}"
                        "else if(e.key==='Home'){e.preventDefault();ir(v[0]);}else if(e.key==='End'){e.preventDefault();ir(v[v.length-1]);}"
                        "else if(e.key==='ArrowRight'&&el.getAttribute('aria-expanded')==='false'){e.preventDefault();el.setAttribute('aria-expanded','true');}"
                        "else if(e.key==='ArrowRight'&&el.getAttribute('aria-expanded')==='true'){e.preventDefault();ir(v[i+1]);}"
                        "else if(e.key==='ArrowLeft'&&el.getAttribute('aria-expanded')==='true'){e.preventDefault();el.setAttribute('aria-expanded','false');}});"
                        "t.addEventListener('click',function(e){var it=e.target.closest('[role=treeitem]');if(it){ir(it);if(it.hasAttribute('aria-expanded')&&e.target===it)it.setAttribute('aria-expanded',String(it.getAttribute('aria-expanded')!=='true'));}});})();</script>",
                "porque": "O leitor de tela anuncia árvore, item, nível e se está aberto ou fechado. As setas andam, abrem e fecham, e há uma única parada de Tab.",
                "corrigir": "Nada a corrigir.",
            },
        ],
    },
    {
        "slug": "tabela-ordenavel",
        "nome": "Tabela ordenável",
        "resumo": "Em uma tabela que ordena, cada coluna ordenável precisa de um botão dentro do cabeçalho, com aria-sort na coluna ordenada, e a mudança precisa ser anunciada.",
        "exemplos": [
            {
                "tipo": "ruim", "titulo": "Cabeçalho clicável que só o mouse alcança",
                "sonda": ("status_update", "css:#tab-ruim-preco"),
                "html": '<table><caption>Chás</caption><thead><tr><th scope="col">Nome</th><th scope="col" id="tab-ruim-preco" style="cursor:pointer">Preço</th></tr></thead>'
                        '<tbody id="tab-ruim-corpo"><tr><td>Sencha</td><td>30</td></tr><tr><td>Matcha</td><td>50</td></tr><tr><td>Gyokuro</td><td>80</td></tr></tbody></table>'
                        "<script>document.getElementById('tab-ruim-preco').addEventListener('click',function(){var c=document.getElementById('tab-ruim-corpo');"
                        "Array.prototype.slice.call(c.rows).reverse().forEach(function(r){c.appendChild(r);});});</script>",
                "porque": "O cabeçalho ordena, mas não é um botão: o teclado não chega, o leitor de tela não sabe que ordena, e nada diz a coluna nem o sentido.",
                "corrigir": "Ponha um button dentro do th, atualize aria-sort e avise numa região de status (Ordenado por Preço, crescente).",
            },
            {
                "tipo": "bom", "titulo": "Botão no cabeçalho, aria-sort e aviso",
                "sonda": ("status_update", "css:#tab-bom-preco"),
                "html": '<table><caption>Chás</caption><thead><tr><th scope="col">Nome</th><th scope="col" id="tab-bom-th" aria-sort="none"><button type="button" id="tab-bom-preco">Preço</button></th></tr></thead>'
                        '<tbody id="tab-bom-corpo"><tr><td>Sencha</td><td>30</td></tr><tr><td>Matcha</td><td>50</td></tr><tr><td>Gyokuro</td><td>80</td></tr></tbody></table><div role="status" id="tab-bom-aviso"></div>'
                        "<script>(function(){var d=true;document.getElementById('tab-bom-preco').addEventListener('click',function(){var c=document.getElementById('tab-bom-corpo');"
                        "var l=Array.prototype.slice.call(c.rows).sort(function(a,b){return (a.cells[1].textContent-b.cells[1].textContent)*(d?-1:1);});l.forEach(function(r){c.appendChild(r);});"
                        "document.getElementById('tab-bom-th').setAttribute('aria-sort',d?'descending':'ascending');"
                        "document.getElementById('tab-bom-aviso').textContent='Ordenado por Preço, '+(d?'decrescente':'crescente');d=!d;});})();</script>",
                "porque": "O leitor de tela encontra o botão Preço, ouve a coluna ordenada pelo aria-sort e a região de status fala Ordenado por Preço, decrescente.",
                "corrigir": "Nada a corrigir.",
            },
        ],
    },
    {
        "slug": "web-components",
        "nome": "Web Components (elemento personalizado)",
        "resumo": "Um elemento personalizado com Shadow DOM aberto continua sendo medido pelo MCP. O defeito comum é o mesmo de sempre, só que escondido dentro do shadow: um div clicável. O bom entrega um botão de verdade, ou usa ElementInternals para dar o papel e o estado ao próprio elemento.",
        "exemplos": [
            {
                "tipo": "ruim", "titulo": "Elemento personalizado com div clicável no shadow",
                "sonda": ("disclosure", "css:#wc-ruim-gatilho"),
                "html": '<meu-acordeao-ruim></meu-acordeao-ruim>'
                        "<script>customElements.define('meu-acordeao-ruim',class extends HTMLElement{connectedCallback(){var r=this.attachShadow({mode:'open'});"
                        "r.innerHTML='<div id=\"wc-ruim-gatilho\" style=\"cursor:pointer\">Prazo de entrega</div><p id=\"wc-ruim-painel\" hidden>Cinco dias úteis.</p>';"
                        "r.getElementById('wc-ruim-gatilho').addEventListener('click',function(){var p=r.getElementById('wc-ruim-painel');p.hidden=!p.hidden;});}});</script>",
                "porque": "O shadow DOM não muda a regra: a div dentro dele não é botão, não recebe foco e não tem estado.",
                "corrigir": "Dentro do shadow, use um button com aria-expanded e aria-controls (ids dentro do mesmo shadow root).",
            },
            {
                "tipo": "bom", "titulo": "Elemento personalizado com button no shadow",
                "sonda": ("disclosure", "css:#wc-bom-gatilho"),
                "html": '<meu-acordeao-bom></meu-acordeao-bom>'
                        "<script>customElements.define('meu-acordeao-bom',class extends HTMLElement{connectedCallback(){var r=this.attachShadow({mode:'open'});"
                        "r.innerHTML='<style>button{min-height:44px;min-width:44px;padding:0.5rem 1rem;font:inherit}</style><button type=\"button\" id=\"wc-bom-gatilho\" aria-expanded=\"false\" aria-controls=\"wc-bom-painel\">Prazo de entrega</button><div id=\"wc-bom-painel\" hidden><p>Cinco dias úteis.</p></div>';"
                        "var b=r.getElementById('wc-bom-gatilho'),p=r.getElementById('wc-bom-painel');"
                        "b.addEventListener('click',function(){var a=b.getAttribute('aria-expanded')!=='true';b.setAttribute('aria-expanded',String(a));p.hidden=!a;});}});</script>",
                "porque": "O botão dentro do shadow é exposto ao leitor de tela com seu estado, e aria-controls funciona porque os dois ids estão no mesmo shadow root.",
                "corrigir": "Nada a corrigir.",
            },
            {
                "tipo": "ruim", "titulo": "Caixa de seleção personalizada sem papel nem teclado",
                "html": '<caixa-ruim>Receber novidades</caixa-ruim>'
                        "<script>customElements.define('caixa-ruim',class extends HTMLElement{connectedCallback(){var r=this.attachShadow({mode:'open'});"
                        "r.innerHTML='<span class=\"marca\" style=\"display:inline-block;width:1.25rem;height:1.25rem;border:2px solid currentColor;vertical-align:middle\"></span> <slot></slot>';"
                        "r.querySelector('.marca').addEventListener('click',function(e){e.target.textContent=e.target.textContent?'':'✓';});}});</script>",
                "porque": "Parece uma caixa de seleção, mas para o leitor de tela é só um texto. Não tem papel de checkbox, não tem estado marcado, não recebe foco.",
                "corrigir": "Use ElementInternals: role checkbox, ariaChecked, tabindex 0 e a tecla Espaço (veja o exemplo web-component-element-internals do MCP), ou simplesmente um input type=checkbox.",
            },
            {
                "tipo": "bom", "titulo": "Caixa de seleção personalizada com ElementInternals",
                "html": '<caixa-bom>Receber novidades</caixa-bom>'
                        "<script>customElements.define('caixa-bom',class extends HTMLElement{static get formAssociated(){return true;}"
                        "constructor(){super();this.i=this.attachInternals();this.i.role='checkbox';this.i.ariaChecked='false';this.attachShadow({mode:'open'}).innerHTML='<style>:host{display:inline-flex;align-items:center;gap:0.5rem;min-height:44px}</style><span style=\"display:inline-block;width:1.25rem;height:1.25rem;border:2px solid currentColor;vertical-align:middle\"></span> <slot></slot>';}"
                        "connectedCallback(){this.tabIndex=0;var t=this;function alterna(){var on=t.i.ariaChecked!=='true';t.i.ariaChecked=String(on);t.shadowRoot.querySelector('span').textContent=on?'✓':'';}"
                        "this.addEventListener('click',alterna);this.addEventListener('keydown',function(e){if(e.key===' '){e.preventDefault();alterna();}});}});</script>",
                "porque": "O elemento ganha o papel checkbox, o estado marcado, foco e a tecla Espaço, tudo no próprio host.",
                "corrigir": "Nada a corrigir. Se um input type=checkbox resolver, prefira ele.",
            },
        ],
    },
    {
        "slug": "chat-ia",
        "nome": "Resposta de IA em streaming",
        "resumo": "Uma resposta que chega aos poucos não pode ser uma região viva atualizada a cada palavra: o leitor de tela fica falando por cima de si mesmo. O padrão do MCP é escrever a resposta numa área que não anuncia e avisar uma vez, no fim, numa região de status. O número de anúncios abaixo é medido, sem veredito.",
        "exemplos": [
            {
                "tipo": "ruim", "titulo": "Cada palavra numa região assertiva",
                "extra": ("anuncios", "css:#chat-ruim-btn"),
                "html": '<button type="button" id="chat-ruim-btn">Perguntar</button><div id="chat-ruim-resp" aria-live="assertive"></div>'
                        "<script>document.getElementById('chat-ruim-btn').addEventListener('click',function(){var r=document.getElementById('chat-ruim-resp');r.textContent='';"
                        "'O chá verde deve ser preparado com água abaixo de oitenta graus'.split(' ').forEach(function(p,i){setTimeout(function(){r.textContent+=p+' ';},i*40);});});</script>",
                "porque": "Cada palavra que entra é uma mudança numa região assertiva: o leitor de tela interrompe e repete, e quem usa se perde antes de a resposta acabar.",
                "corrigir": "Escreva a resposta num elemento sem aria-live, mantenha o foco no campo e avise uma vez, no fim, numa região de status (Resposta pronta).",
            },
            {
                "tipo": "bom", "titulo": "Resposta sem região viva e um aviso no fim",
                "extra": ("anuncios", "css:#chat-bom-btn"),
                "html": '<button type="button" id="chat-bom-btn">Perguntar</button><div id="chat-bom-resp" aria-busy="false"></div><div role="status" id="chat-bom-aviso"></div>'
                        "<script>document.getElementById('chat-bom-btn').addEventListener('click',function(){var r=document.getElementById('chat-bom-resp'),a=document.getElementById('chat-bom-aviso');r.textContent='';r.setAttribute('aria-busy','true');"
                        "var t='O chá verde deve ser preparado com água abaixo de oitenta graus'.split(' ');t.forEach(function(p,i){setTimeout(function(){r.textContent+=p+' ';"
                        "if(i===t.length-1){r.setAttribute('aria-busy','false');a.textContent='Resposta pronta';}},i*40);});});</script>",
                "porque": "A resposta aparece sem interromper ninguém. Um único aviso, Resposta pronta, chega no fim, e a pessoa lê o texto quando quiser.",
                "corrigir": "Nada a corrigir.",
            },
        ],
    },
]
