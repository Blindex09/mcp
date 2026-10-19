"""Os cenarios do site de exemplos: cada um tem exemplos ruins, bons e "nao precisa corrigir", com o porque e o que corrigir.

Texto e HTML escritos a mao; o que o navegador entrega ao leitor de tela e o que o axe acha NAO esta aqui: o gerador mede isso
com o proprio MCP (construir.py), para ninguem precisar acreditar em afirmacao de cabeca.
"""

from __future__ import annotations

from typing import Any

RUIM, BOM, OK = "ruim", "bom", "ok"
ROTULO = {RUIM: "Exemplo ruim", BOM: "Exemplo bom", OK: "Não precisa corrigir"}

CENARIOS: list[dict[str, Any]] = [
    {
        "slug": "titulos",
        "nome": "Títulos",
        "resumo": "Quem usa leitor de tela navega a página de título em título. Sem título de verdade, não existe mapa. Nos exemplos vivos desta página os títulos começam em h3, porque a própria página já usa h1 e h2; a regra vale em qualquer nível: não pular.",
        "exemplos": [
            {
                "tipo": RUIM, "titulo": "Títulos só no visual",
                "html": '<div class="vt1">Casa do Chá</div><div class="vt2">Chás verdes</div><p>Sencha, matcha e gyokuro.</p>'
                        '<div class="vt2">Chás pretos</div><p>Earl Grey e Assam.</p>',
                "porque": "A pessoa que enxerga vê quatro blocos com cara de título. A árvore de acessibilidade não tem nenhum título: o leitor de tela não consegue listar os títulos nem pular entre eles.",
                "corrigir": "Troque cada div por título de verdade (h3 para o assunto, h4 para as partes) e mantenha o tamanho e o peso da letra no CSS.",
            },
            {
                "tipo": RUIM, "titulo": "Títulos que pulam de nível",
                "html": '<h3>Casa do Chá</h3><h5>Chás verdes</h5><p>Sencha, matcha e gyokuro.</p><h5>Chás pretos</h5><p>Earl Grey e Assam.</p>',
                "porque": "Os títulos são de verdade, mas o exemplo pula do nível 3 para o 5. Quem navega por nível fica sem saber se faltou um nível 4.",
                "corrigir": "Use h4 onde está h5. O tamanho da letra vem do CSS, não do número do título.",
            },
            {
                "tipo": BOM, "titulo": "Hierarquia sem saltos",
                "html": '<h3>Casa do Chá</h3><h4>Chás verdes</h4><p>Sencha, matcha e gyokuro.</p><h4>Chás pretos</h4><p>Earl Grey e Assam.</p>',
                "porque": "Um título de nível 3 para o assunto do bloco e títulos de nível 4 para as partes, sem pular nível.",
                "corrigir": "Nada a corrigir.",
            },
        ],
    },
    {
        "slug": "listas",
        "nome": "Listas",
        "resumo": "O leitor de tela anuncia uma lista com a quantidade de itens e a posição de cada um. Lista só no visual não é anunciada.",
        "exemplos": [
            {
                "tipo": RUIM, "titulo": "Lista falsa feita de divs com bolinha no texto",
                "html": '<div>• Sencha</div><div>• Matcha</div><div>• Gyokuro</div>',
                "porque": "Para quem vê é uma lista. Para o leitor de tela são três linhas soltas, sem \"lista com 3 itens\" e sem posição. A bolinha ainda pode ser lida como símbolo.",
                "corrigir": "Use ul e li. O marcador (bolinha) vem do CSS e não do texto.",
            },
            {
                "tipo": BOM, "titulo": "Lista de verdade",
                "html": '<ul><li>Sencha</li><li>Matcha</li><li>Gyokuro</li></ul>',
                "porque": "O navegador entrega uma lista com 3 itens. O leitor de tela anuncia o total e a posição de cada item.",
                "corrigir": "Nada a corrigir.",
            },
            {
                "tipo": RUIM, "titulo": "Lista de cartões com um título dentro de cada item",
                "html": '<ul class="cartoes"><li><h3><a href="#sencha">Sencha</a></h3><p>Chá verde japonês.</p></li>'
                        '<li><h3><a href="#matcha">Matcha</a></h3><p>Chá verde em pó.</p></li></ul>',
                "porque": "É HTML válido, mas a mesma informação aparece duas vezes: o leitor de tela anuncia \"lista com 2 itens\" e, em cada item, um título com o nível do h3. Quem navega por títulos passa a encontrar rótulos de cartão no lugar da estrutura da página. O guia aria-rules-dos-and-donts do MCP diz para usar título na estrutura do documento e não em título visual de cartão, e para expor cada informação uma só vez.",
                "corrigir": "Troque por uma lista de links com descrição: ul, li e, dentro do item, o link com o nome do cartão e o parágrafo. A lista dá a contagem e os saltos; o link já é o nome. Se cada cartão for mesmo uma seção que merece estar no mapa da página, deixe os títulos e tire a lista, nunca os dois.",
            },
            {
                "tipo": BOM, "titulo": "Lista de cartões como lista de links com descrição",
                "html": '<ul class="cartoes"><li><a href="#sencha">Sencha</a><p>Chá verde japonês.</p></li>'
                        '<li><a href="#matcha">Matcha</a><p>Chá verde em pó.</p></li></ul>',
                "porque": "Uma só estrutura: o leitor de tela anuncia a lista com o total de itens e, em cada item, o link com o nome do cartão e a descrição. A lista de títulos da página continua só com os títulos de verdade.",
                "corrigir": "Nada a corrigir.",
            },
        ],
    },
    {
        "slug": "links",
        "nome": "Links",
        "resumo": "Quem usa leitor de tela costuma ouvir a lista de links da página, sem o texto em volta. O nome do link precisa dizer para onde ele leva.",
        "exemplos": [
            {
                "tipo": RUIM, "titulo": "\"Clique aqui\" e \"Leia mais\" repetidos",
                "html": '<p>Sencha, chá verde japonês. <a href="#a">Clique aqui</a></p><p>Matcha, chá verde em pó. <a href="#b">Clique aqui</a></p>'
                        '<p>Gyokuro, chá sombreado. <a href="#c">Clique aqui</a></p>',
                "porque": "Na lista de links, a pessoa ouve três vezes \"Clique aqui\" e não sabe qual leva a qual chá.",
                "corrigir": "O texto do link diz o destino: \"Conheça o Sencha\". Se o design exige \"Leia mais\", acrescente o nome oculto visualmente ou aria-label com o destino.",
            },
            {
                "tipo": BOM, "titulo": "Links que dizem para onde levam",
                "html": '<p>Sencha, chá verde japonês. <a href="#a">Conheça o Sencha</a></p><p>Matcha, chá verde em pó. <a href="#b">Conheça o Matcha</a></p>'
                        '<p>Gyokuro, chá sombreado. <a href="#c">Conheça o Gyokuro</a></p>',
                "porque": "Cada link tem um nome único e descritivo, mesmo fora do parágrafo.",
                "corrigir": "Nada a corrigir.",
            },
        ],
    },
    {
        "slug": "botoes",
        "nome": "Botões",
        "resumo": "Botão precisa ser alcançado pelo Tab, ser anunciado como botão e ter um nome.",
        "exemplos": [
            {
                "tipo": RUIM, "titulo": "Div que faz o papel de botão",
                "html": '<div class="fake-botao" onclick="this.textContent = \'Adicionado\'">Comprar</div>',
                "porque": "O mouse funciona. Pelo teclado, o Tab passa direto, e o leitor de tela não anuncia botão: é um texto qualquer na página.",
                "corrigir": "Use um elemento button. Enter e Espaço passam a funcionar sozinhos e o foco aparece.",
            },
            {
                "tipo": BOM, "titulo": "Botão de verdade",
                "html": '<button type="button" class="botao" onclick="this.textContent = \'Adicionado\'">Comprar</button>',
                "porque": "O Tab chega nele, o leitor anuncia \"botão\" e o nome \"Comprar\", e Enter e Espaço acionam.",
                "corrigir": "Nada a corrigir.",
            },
            {
                "tipo": OK, "titulo": "Botão só com ícone, com nome por aria-label",
                "html": '<button type="button" class="botao" aria-label="Abrir o carrinho"><span aria-hidden="true">&#128722;</span></button>',
                "porque": "O ícone é decorativo e fica escondido do leitor; o nome vem de aria-label. O leitor anuncia \"Abrir o carrinho, botão\".",
                "corrigir": "Não precisa corrigir. Só lembre de manter o nome igual ao texto que aparece, quando houver texto visível.",
            },
        ],
    },
    {
        "slug": "campos",
        "nome": "Campos de formulário",
        "resumo": "O leitor de tela anuncia o nome do campo quando o foco chega nele. Sem nome, a pessoa não sabe o que digitar.",
        "exemplos": [
            {
                "tipo": RUIM, "titulo": "Campo sem rótulo associado",
                "html": '<p>Seu e-mail</p><input type="email" name="email-ruim">',
                "porque": "O texto \"Seu e-mail\" está perto do campo, mas não está ligado a ele. Quando o foco chega, o leitor diz só \"campo de edição\".",
                "corrigir": "Use label com for apontando para o id do campo, ou envolva o campo no label.",
            },
            {
                "tipo": BOM, "titulo": "Campo com label associado",
                "html": '<label for="email-bom">Seu e-mail</label><br><input type="email" id="email-bom" name="email-bom" autocomplete="email">',
                "porque": "O foco chega e o leitor diz o nome do campo, \"Seu e-mail\", e que é um campo de edição.",
                "corrigir": "Nada a corrigir.",
            },
            {
                "tipo": OK, "titulo": "Label que envolve o campo",
                "html": '<label>Seu nome <input type="text" name="nome-ok" autocomplete="name"></label>',
                "porque": "Também é uma associação válida. O nome do campo é o texto do label.",
                "corrigir": "Não precisa corrigir; só é mais difícil de estilizar do que o for com id.",
            },
        ],
    },
    {
        "slug": "imagens",
        "nome": "Imagens",
        "resumo": "Imagem com informação precisa de texto alternativo. Imagem decorativa precisa ser ignorada de propósito.",
        "exemplos": [
            {
                "tipo": RUIM, "titulo": "Imagem de conteúdo sem alt",
                "html": '<img src="data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%2780%27 height=%2780%27%3E%3Crect width=%2780%27 height=%2780%27 fill=%27%23557%27/%3E%3C/svg%3E" width="80" height="80">',
                "porque": "Sem alt, alguns leitores falam o nome do arquivo ou só \"imagem\". A informação da imagem se perde.",
                "corrigir": "Acrescente alt descrevendo o que a imagem mostra, por exemplo \"Folhas de Sencha em uma xícara\".",
            },
            {
                "tipo": BOM, "titulo": "Imagem com alt descritivo",
                "html": '<img alt="Folhas de Sencha em uma xícara branca" src="data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%2780%27 height=%2780%27%3E%3Crect width=%2780%27 height=%2780%27 fill=%27%23557%27/%3E%3C/svg%3E" width="80" height="80">',
                "porque": "O leitor anuncia \"gráfico\" ou \"imagem\" e o texto alternativo.",
                "corrigir": "Nada a corrigir.",
            },
            {
                "tipo": OK, "titulo": "Imagem decorativa com alt vazio",
                "html": '<img alt="" src="data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%2780%27 height=%2780%27%3E%3Crect width=%2780%27 height=%2780%27 fill=%27%23557%27/%3E%3C/svg%3E" width="80" height="80">',
                "porque": "alt vazio diz ao leitor de tela para ignorar a imagem, e é o certo para um enfeite sem informação. Não é a mesma coisa que alt ausente.",
                "corrigir": "Não precisa corrigir, se a imagem for mesmo só enfeite.",
            },
        ],
    },
    {
        "slug": "tabelas",
        "nome": "Tabelas",
        "resumo": "Em tabela, o leitor de tela diz a que coluna e a que linha cada célula pertence, se houver células de cabeçalho.",
        "exemplos": [
            {
                "tipo": RUIM, "titulo": "Tabela sem células de cabeçalho",
                "html": '<table><tr><td>Chá</td><td>Preço</td></tr><tr><td>Sencha</td><td>R$ 39,90</td></tr><tr><td>Matcha</td><td>R$ 59,90</td></tr></table>',
                "porque": "Visualmente a primeira linha parece cabeçalho. Para o leitor de tela, todas as células são iguais: ao ler R$ 39,90 não se ouve \"Preço\".",
                "corrigir": "Use th com scope=\"col\" no cabeçalho, e uma legenda (caption) dizendo o assunto da tabela.",
            },
            {
                "tipo": BOM, "titulo": "Tabela com cabeçalho e legenda",
                "html": '<table><caption>Preço por chá</caption><thead><tr><th scope="col">Chá</th><th scope="col">Preço</th></tr></thead>'
                        '<tbody><tr><td>Sencha</td><td>R$ 39,90</td></tr><tr><td>Matcha</td><td>R$ 59,90</td></tr></tbody></table>',
                "porque": "A legenda dá o assunto e os th ligam cada preço à coluna \"Preço\".",
                "corrigir": "Nada a corrigir.",
            },
        ],
    },
    {
        "slug": "avisos",
        "nome": "Avisos que aparecem sem recarregar",
        "resumo": "Quando a página muda sozinha, quem não vê a tela só fica sabendo se a mudança for anunciada.",
        "exemplos": [
            {
                "tipo": RUIM, "titulo": "Mensagem que muda em silêncio",
                "html": '<button type="button" class="botao" onclick="document.getElementById(\'aviso-ruim\').textContent = \'Adicionado ao carrinho\'">Comprar</button>'
                        '<p id="aviso-ruim"></p>',
                "porque": "O botão é de verdade, então o Tab funciona. Mas o texto aparece sem ninguém avisar: o leitor de tela fica em silêncio e a pessoa não sabe se a compra deu certo.",
                "corrigir": "Coloque a mensagem numa região de status (role=\"status\") que já exista na página antes do clique, e troque só o texto dentro dela.",
            },
            {
                "tipo": BOM, "titulo": "Mensagem numa região de status",
                "html": '<button type="button" class="botao" onclick="document.getElementById(\'aviso-bom\').textContent = \'Adicionado ao carrinho\'">Comprar</button>'
                        '<p id="aviso-bom" role="status"></p>',
                "porque": "A região de status já está na página, vazia. Quando o texto entra, o leitor de tela o anuncia sem tirar o foco do botão.",
                "corrigir": "Nada a corrigir.",
            },
        ],
    },
]

from interativos import INTERATIVOS

CENARIOS.extend(INTERATIVOS)
