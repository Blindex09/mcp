"""Cenarios interativos do site de exemplos: componentes que mudam de estado com o teclado.

Cada exemplo traz o HTML vivo (com o proprio script) e a sonda do MCP que mede o comportamento. Os ids sao unicos na pagina
(sufixo -ruim / -bom / -ok) porque os exemplos de um cenario vivem juntos. O resultado das sondas e medido pelo gerador.
"""

from __future__ import annotations

from typing import Any


def _pagina_rota(titulo_muda: bool, foco_e_aviso: bool) -> str:
    """Mini aplicacao de uma pagina so (SPA): o botao troca o conteudo sem recarregar. So a versao boa muda o titulo, move o foco e avisa."""
    extra = (
        "document.title='Contato | Loja de chás';"
        "var h=document.getElementById('h1');h.tabIndex=-1;h.focus();document.getElementById('aviso').textContent='Página Contato carregada';"
        if foco_e_aviso else ""
    )
    titulo = "document.title='Contato | Loja de chás';" if titulo_muda and not foco_e_aviso else ""
    return (
        '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Início | Loja de chás</title>'
        "<style>body{font:1.1rem system-ui;margin:1rem;max-width:40rem} button{min-height:44px;padding:.5rem 1rem;font:inherit}</style></head><body>"
        '<p><button type="button" id="ir-contato">Contato</button></p>'
        '<main id="app"><h1 id="h1">Início</h1><p>Bem-vindo à loja de chás.</p></main>'
        '<div id="aviso" role="status" class="so-leitor" style="position:absolute;left:-9999px"></div>'
        "<script>document.getElementById('ir-contato').addEventListener('click',function(){"
        "document.getElementById('app').innerHTML='<h1 id=\"h1\">Contato</h1><p>Escreva para contato@loja.example.</p>';"
        + titulo + extra + "});</script></body></html>"
    )


ROTAS: dict[str, str] = {"rota-ruim": _pagina_rota(False, False), "rota-bom": _pagina_rota(True, True)}

INTERATIVOS: list[dict[str, Any]] = [
    {
        "slug": "dialogo",
        "nome": "Diálogo (janela modal)",
        "resumo": "Ao abrir um diálogo, o foco do teclado precisa entrar nele, ficar preso lá dentro, e voltar ao botão que o abriu quando ele fecha. O leitor de tela anuncia o nome do diálogo.",
        "exemplos": [
            {
                "tipo": "ruim", "titulo": "Caixa que aparece, mas o foco fica para trás",
                "sonda": ("dialog", "css:#abrir-dlg-ruim"),
                "html": '<button type="button" id="abrir-dlg-ruim">Excluir projeto</button>'
                        '<div id="dlg-ruim" class="caixa-falsa" hidden><p>Excluir este projeto?</p><button type="button" id="fechar-dlg-ruim">Cancelar</button></div>'
                        "<script>(function(){var d=document.getElementById('dlg-ruim');"
                        "document.getElementById('abrir-dlg-ruim').addEventListener('click',function(){d.hidden=false;});"
                        "document.getElementById('fechar-dlg-ruim').addEventListener('click',function(){d.hidden=true;});})();</script>",
                "porque": "Para quem vê, abriu uma janela. Para o teclado e o leitor de tela, não é um diálogo: a caixa não tem papel de diálogo nem nome, o foco continua no botão de trás, o Tab vaza para a página e o Escape não fecha. A sonda do MCP nem reconhece uma janela aberta.",
                "corrigir": "Use o elemento dialog aberto com showModal(): ele dá papel, foco preso, Escape e fundo inerte. Dê nome com aria-labelledby apontando para o título.",
            },
            {
                "tipo": "bom", "titulo": "dialog nativo com showModal()",
                "sonda": ("dialog", "css:#abrir-dlg-bom"),
                "html": '<button type="button" id="abrir-dlg-bom">Excluir projeto</button>'
                        '<dialog id="dlg-bom" aria-labelledby="dlg-bom-titulo"><h3 id="dlg-bom-titulo">Excluir este projeto?</h3>'
                        '<p>Isso não pode ser desfeito.</p><button type="button" id="cancelar-dlg-bom">Cancelar</button> <button type="button">Excluir</button></dialog>'
                        "<script>(function(){var d=document.getElementById('dlg-bom');"
                        "document.getElementById('abrir-dlg-bom').addEventListener('click',function(){d.showModal();});"
                        "document.getElementById('cancelar-dlg-bom').addEventListener('click',function(){d.close();});})();</script>",
                "porque": "O navegador coloca o foco dentro, prende o Tab, fecha com Escape, devolve o foco ao botão e anuncia o diálogo pelo nome do título.",
                "corrigir": "Nada a corrigir.",
            },
        ],
    },
    {
        "slug": "acordeao",
        "nome": "Acordeão (mostrar e ocultar)",
        "resumo": "O leitor de tela precisa ouvir se a seção está aberta ou fechada e conseguir alternar com Enter e Espaço. O elemento details já faz tudo isso sem JavaScript.",
        "exemplos": [
            {
                "tipo": "ruim", "titulo": "div clicável sem estado e sem teclado",
                "sonda": ("disclosure", "css:#gatilho-acd-ruim"),
                "html": '<div id="gatilho-acd-ruim" class="fake-botao">Prazo de entrega</div><div id="painel-acd-ruim" hidden><p>Cinco dias úteis.</p></div>'
                        "<script>document.getElementById('gatilho-acd-ruim').addEventListener('click',function(){var p=document.getElementById('painel-acd-ruim');p.hidden=!p.hidden;});</script>",
                "porque": "Só o mouse alterna. A div não recebe foco, não é anunciada como botão e não diz se está aberta ou fechada.",
                "corrigir": "Use button com aria-expanded e aria-controls, atualizando aria-expanded a cada clique. Ou use details e summary.",
            },
            {
                "tipo": "bom", "titulo": "button com aria-expanded e aria-controls",
                "sonda": ("disclosure", "css:#gatilho-acd-bom"),
                "html": '<button type="button" id="gatilho-acd-bom" aria-expanded="false" aria-controls="painel-acd-bom">Prazo de entrega</button><div id="painel-acd-bom" hidden><p>Cinco dias úteis.</p></div>'
                        "<script>(function(){var b=document.getElementById('gatilho-acd-bom'),p=document.getElementById('painel-acd-bom');"
                        "b.addEventListener('click',function(){var abrir=b.getAttribute('aria-expanded')!=='true';b.setAttribute('aria-expanded',String(abrir));p.hidden=!abrir;});})();</script>",
                "porque": "O leitor de tela anuncia botão, recolhido ou expandido. Enter e Espaço alternam e o foco fica no botão.",
                "corrigir": "Nada a corrigir.",
            },
            {
                "tipo": "ok", "titulo": "details e summary",
                "sonda": ("disclosure", "css:#resumo-acd-ok"),
                "html": '<details id="detalhes-acd-ok"><summary id="resumo-acd-ok">Prazo de entrega</summary><p>Cinco dias úteis.</p></details>',
                "porque": "Parece simples demais para ser acessível, mas o navegador entrega o estado aberto ou fechado e alterna com Enter e Espaço sem uma linha de JavaScript.",
                "corrigir": "Nada a corrigir. Prefira details quando não precisar de aria-controls.",
            },
        ],
    },
    {
        "slug": "abas",
        "nome": "Abas",
        "resumo": "Abas têm uma única parada de Tab; as setas, Home e End andam entre elas, e o Tab seguinte leva ao painel. O leitor de tela anuncia a aba e a posição, como segunda de três.",
        "exemplos": [
            {
                "tipo": "ruim", "titulo": "Abas feitas de divs",
                "sonda": ("tabs", "css:#aba-ruim-1"),
                "html": '<div class="abas-falsas"><div id="aba-ruim-1" class="fake-botao" data-p="painel-aba-ruim-1">Perfil</div><div id="aba-ruim-2" class="fake-botao" data-p="painel-aba-ruim-2">Segurança</div></div>'
                        '<div id="painel-aba-ruim-1"><p>Dados do perfil.</p></div><div id="painel-aba-ruim-2" hidden><p>Senha e acesso.</p></div>'
                        "<script>(function(){['aba-ruim-1','aba-ruim-2'].forEach(function(id){var a=document.getElementById(id);a.addEventListener('click',function(){"
                        "['painel-aba-ruim-1','painel-aba-ruim-2'].forEach(function(p){document.getElementById(p).hidden=(p!==a.dataset.p);});});});})();</script>",
                "porque": "Só o mouse troca de aba. Não há papel de aba, nem lista de abas, nem teclado.",
                "corrigir": "Use role=tablist, role=tab com aria-selected e aria-controls e role=tabpanel. Faça tabindex 0 só na aba ativa e as setas, Home e End movendo o foco.",
            },
            {
                "tipo": "bom", "titulo": "Abas no padrão do APG",
                "sonda": ("tabs", "css:#aba-bom-1"),
                "html": '<div role="tablist" aria-label="Conta">'
                        '<button type="button" role="tab" id="aba-bom-1" aria-selected="true" aria-controls="painel-aba-bom-1" tabindex="0">Perfil</button>'
                        '<button type="button" role="tab" id="aba-bom-2" aria-selected="false" aria-controls="painel-aba-bom-2" tabindex="-1">Segurança</button>'
                        '<button type="button" role="tab" id="aba-bom-3" aria-selected="false" aria-controls="painel-aba-bom-3" tabindex="-1">Cobrança</button></div>'
                        '<div role="tabpanel" id="painel-aba-bom-1" aria-labelledby="aba-bom-1" tabindex="0"><p>Dados do perfil.</p></div>'
                        '<div role="tabpanel" id="painel-aba-bom-2" aria-labelledby="aba-bom-2" tabindex="0" hidden><p>Senha e acesso.</p></div>'
                        '<div role="tabpanel" id="painel-aba-bom-3" aria-labelledby="aba-bom-3" tabindex="0" hidden><p>Forma de pagamento.</p></div>'
                        "<script>(function(){var abas=['aba-bom-1','aba-bom-2','aba-bom-3'].map(function(i){return document.getElementById(i);});"
                        "function ativar(t){abas.forEach(function(a){var on=a===t;a.setAttribute('aria-selected',String(on));a.tabIndex=on?0:-1;"
                        "document.getElementById(a.getAttribute('aria-controls')).hidden=!on;});t.focus();}"
                        "abas.forEach(function(a,i){a.addEventListener('click',function(){ativar(a);});a.addEventListener('keydown',function(e){var n=null;"
                        "if(e.key==='ArrowRight')n=(i+1)%abas.length;else if(e.key==='ArrowLeft')n=(i+abas.length-1)%abas.length;else if(e.key==='Home')n=0;else if(e.key==='End')n=abas.length-1;"
                        "if(n!==null){e.preventDefault();ativar(abas[n]);}});});})();</script>",
                "porque": "O leitor de tela anuncia aba, selecionada e a posição. Uma parada de Tab, setas, Home e End, e o Tab seguinte entra no painel.",
                "corrigir": "Nada a corrigir.",
            },
        ],
    },
    {
        "slug": "menu",
        "nome": "Menu de ações",
        "resumo": "Um botão que abre uma lista de comandos precisa avisar que abre um menu e se está aberto. O foco entra no primeiro item, as setas andam, o Escape fecha e devolve o foco ao botão.",
        "exemplos": [
            {
                "tipo": "ruim", "titulo": "Menu que só abre com o mouse",
                "sonda": ("menu", "css:#menu-ruim-btn"),
                "html": '<div id="menu-ruim-btn" class="fake-botao">Ações</div><ul id="menu-ruim-lista" hidden><li>Renomear</li><li>Duplicar</li><li>Excluir</li></ul>'
                        "<script>document.getElementById('menu-ruim-btn').addEventListener('click',function(){var l=document.getElementById('menu-ruim-lista');l.hidden=!l.hidden;});</script>",
                "porque": "Não recebe foco, não diz que abre um menu, e os itens não são comandos acionáveis pelo teclado.",
                "corrigir": "Use button com aria-haspopup e aria-expanded; a lista com role=menu e os itens com role=menuitem; mova o foco com as setas; Escape fecha e devolve o foco ao botão.",
            },
            {
                "tipo": "bom", "titulo": "Botão de menu no padrão do APG",
                "sonda": ("menu", "css:#menu-bom-btn"),
                "html": '<button type="button" id="menu-bom-btn" aria-haspopup="menu" aria-expanded="false" aria-controls="menu-bom-lista">Ações</button>'
                        '<ul role="menu" id="menu-bom-lista" aria-labelledby="menu-bom-btn" hidden>'
                        '<li role="none"><button type="button" role="menuitem" tabindex="-1">Renomear</button></li>'
                        '<li role="none"><button type="button" role="menuitem" tabindex="-1">Duplicar</button></li>'
                        '<li role="none"><button type="button" role="menuitem" tabindex="-1">Excluir</button></li></ul>'
                        "<script>(function(){var b=document.getElementById('menu-bom-btn'),l=document.getElementById('menu-bom-lista');"
                        "var it=Array.prototype.slice.call(l.querySelectorAll('[role=menuitem]'));"
                        "function abrir(){l.hidden=false;b.setAttribute('aria-expanded','true');it[0].focus();}"
                        "function fechar(){l.hidden=true;b.setAttribute('aria-expanded','false');b.focus();}"
                        "b.addEventListener('click',function(){if(l.hidden)abrir();else fechar();});"
                        "b.addEventListener('keydown',function(e){if(e.key==='ArrowDown'){e.preventDefault();abrir();}});"
                        "l.addEventListener('keydown',function(e){var i=it.indexOf(document.activeElement);"
                        "if(e.key==='ArrowDown'){e.preventDefault();it[(i+1)%it.length].focus();}"
                        "else if(e.key==='ArrowUp'){e.preventDefault();it[(i+it.length-1)%it.length].focus();}"
                        "else if(e.key==='Home'){e.preventDefault();it[0].focus();}"
                        "else if(e.key==='End'){e.preventDefault();it[it.length-1].focus();}"
                        "else if(e.key==='Escape'){e.preventDefault();fechar();}"
                        "else if(e.key==='Tab'){l.hidden=true;b.setAttribute('aria-expanded','false');}});})();</script>",
                "porque": "O botão diz que abre um menu e se está aberto. O foco entra no primeiro item, as setas, Home e End andam, Escape fecha e o foco volta ao botão.",
                "corrigir": "Nada a corrigir.",
            },
        ],
    },
    {
        "slug": "combobox",
        "nome": "Campo com lista de opções (combobox)",
        "resumo": "O campo precisa ser anunciado como caixa de combinação, dizer se a lista está aberta e expor qual opção está ativa enquanto as setas andam, sem tirar o foco do campo.",
        "exemplos": [
            {
                "tipo": "ruim", "titulo": "Campo com lista de divs que só responde ao mouse",
                "sonda": ("combobox", "css:#cb-ruim"),
                "html": '<label for="cb-ruim">Cidade</label><input id="cb-ruim" type="text" autocomplete="off"><div id="cb-ruim-lista" hidden><div class="opcao-falsa">Curitiba</div><div class="opcao-falsa">Recife</div></div>'
                        "<script>(function(){var c=document.getElementById('cb-ruim'),l=document.getElementById('cb-ruim-lista');"
                        "c.addEventListener('focus',function(){l.hidden=false;});Array.prototype.forEach.call(l.children,function(o){o.addEventListener('click',function(){c.value=o.textContent;l.hidden=true;});});})();</script>",
                "porque": "O campo é só um texto. A lista abre ao receber o foco, mas não tem papel de listbox, o campo não diz que está aberto e as setas não escolhem nada.",
                "corrigir": "Dê role=combobox, aria-expanded, aria-controls e aria-activedescendant ao campo; a lista com role=listbox e as opções com role=option; setas, Enter e Escape.",
            },
            {
                "tipo": "bom", "titulo": "Combobox com aria-activedescendant",
                "sonda": ("combobox", "css:#cb-bom"),
                "html": '<label for="cb-bom">Cidade</label><input id="cb-bom" type="text" role="combobox" aria-expanded="false" aria-controls="cb-bom-lista" aria-autocomplete="list" autocomplete="off">'
                        '<ul role="listbox" id="cb-bom-lista" aria-label="Cidades" hidden><li role="option" id="cb-bom-o1">Curitiba</li><li role="option" id="cb-bom-o2">Recife</li><li role="option" id="cb-bom-o3">Salvador</li></ul>'
                        "<script>(function(){var c=document.getElementById('cb-bom'),l=document.getElementById('cb-bom-lista');"
                        "var op=Array.prototype.slice.call(l.children),a=-1;"
                        "function marca(i){a=i;op.forEach(function(o,j){o.setAttribute('aria-selected',String(j===i));});"
                        "if(i>=0)c.setAttribute('aria-activedescendant',op[i].id);else c.removeAttribute('aria-activedescendant');}"
                        "function abre(){l.hidden=false;c.setAttribute('aria-expanded','true');}"
                        "function fecha(){l.hidden=true;c.setAttribute('aria-expanded','false');marca(-1);}"
                        "c.addEventListener('keydown',function(e){"
                        "if(e.key==='ArrowDown'){e.preventDefault();if(l.hidden){abre();marca(0);}else marca((a+1)%op.length);}"
                        "else if(e.key==='ArrowUp'){e.preventDefault();if(l.hidden){abre();marca(op.length-1);}else marca((a+op.length-1)%op.length);}"
                        "else if(e.key==='Enter'&&!l.hidden&&a>=0){e.preventDefault();c.value=op[a].textContent;fecha();}"
                        "else if(e.key==='Escape'&&!l.hidden){e.preventDefault();fecha();}});"
                        "op.forEach(function(o,i){o.addEventListener('click',function(){c.value=o.textContent;fecha();c.focus();});});})();</script>",
                "porque": "O leitor de tela anuncia caixa de combinação, recolhida ou expandida, e lê a opção ativa a cada seta, enquanto o foco continua no campo.",
                "corrigir": "Nada a corrigir.",
            },
        ],
    },
    {
        "slug": "erros-de-formulario",
        "nome": "Erro de formulário",
        "resumo": "Quem não vê a tela precisa ouvir que há erro, em qual campo e o que fazer. O campo inválido é marcado, o texto do erro fica ligado a ele e o foco vai para lá.",
        "exemplos": [
            {
                "tipo": "ruim", "titulo": "Texto vermelho solto",
                "sonda": ("form_errors", "css:#enviar-form-ruim"),
                "html": '<form id="form-ruim" novalidate><label for="email-ruim">E-mail</label><input id="email-ruim" type="email" required> <span id="msg-ruim" class="erro-visual"></span>'
                        '<p><button type="submit" id="enviar-form-ruim">Enviar</button></p></form>'
                        "<script>(function(){var f=document.getElementById('form-ruim');f.addEventListener('submit',function(e){e.preventDefault();"
                        "document.getElementById('msg-ruim').textContent=document.getElementById('email-ruim').value?'':'Informe o e-mail.';});})();</script>",
                "porque": "Aparece uma frase vermelha ao lado. O campo não é marcado como inválido, a frase não está ligada a ele, o foco não se move e nada é anunciado. Quem usa leitor de tela fica sem saber que falhou.",
                "corrigir": "Marque o campo com aria-invalid=true, ligue o texto do erro com aria-describedby, mova o foco para o primeiro campo com erro e anuncie com role=alert.",
            },
            {
                "tipo": "bom", "titulo": "Campo marcado, erro ligado e foco no campo",
                "sonda": ("form_errors", "css:#enviar-form-bom"),
                "html": '<form id="form-bom" novalidate><label for="email-bom">E-mail</label><input id="email-bom" type="email" required aria-describedby="msg-bom"> <span id="msg-bom" class="erro-visual" role="alert"></span>'
                        '<p><button type="submit" id="enviar-form-bom">Enviar</button></p></form>'
                        "<script>(function(){var f=document.getElementById('form-bom'),c=document.getElementById('email-bom'),m=document.getElementById('msg-bom');"
                        "f.addEventListener('submit',function(e){e.preventDefault();if(!c.value){c.setAttribute('aria-invalid','true');m.textContent='Informe o e-mail.';c.focus();}"
                        "else{c.removeAttribute('aria-invalid');m.textContent='';}});})();</script>",
                "porque": "O leitor de tela lê o campo, inválido, com a mensagem do erro junto, e o foco já está lá.",
                "corrigir": "Nada a corrigir.",
            },
        ],
    },
    {
        "slug": "mudanca-de-tela",
        "nome": "Mudança de tela em aplicação de uma página só",
        "resumo": "Quando o conteúdo troca sem recarregar a página, o navegador não anuncia nada. A aplicação precisa mudar o título da aba, levar o foco ao novo conteúdo e avisar o leitor de tela.",
        "exemplos": [
            {
                "tipo": "ruim", "titulo": "A tela muda e ninguém é avisado",
                "documento": "rota-ruim", "sonda": ("route_change", "css:#ir-contato"),
                "html": '<p><a href="rota-ruim.html">Abrir a aplicação de exemplo (ruim)</a></p>',
                "porque": "O conteúdo vira Contato, mas o título da aba continua Início, o foco permanece no botão e não há aviso. Quem usa leitor de tela não sabe que a tela mudou.",
                "corrigir": "Ao trocar a tela: atualize document.title, mova o foco para o novo título (h1 com tabindex -1) e avise numa região role=status.",
            },
            {
                "tipo": "bom", "titulo": "Título, foco e aviso acompanham a troca",
                "documento": "rota-bom", "sonda": ("route_change", "css:#ir-contato"),
                "html": '<p><a href="rota-bom.html">Abrir a aplicação de exemplo (boa)</a></p>',
                "porque": "O título da aba muda para Contato, o foco vai ao novo título e o leitor de tela ouve Página Contato carregada.",
                "corrigir": "Nada a corrigir.",
            },
        ],
    },
]
