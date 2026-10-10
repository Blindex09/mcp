"""Sondas de comportamento: cada uma contra um par BOM/RUIM, no Chromium de verdade. As sondas devolvem fatos (esperado x observado);
o par prova que ela distingue o componente correto do defeituoso, em vez de aprovar tudo ou reprovar tudo."""
import pytest

from a11y.probes import PROBES, run_probe
from a11y.session import SESSION, SessionError

HEAD = '<!doctype html><html lang="pt"><head><title>Teste</title></head><body>'


async def probe(html, kind, target=None, container=None):
    await SESSION.open(None, HEAD + html + "</body></html>")
    try:
        return await run_probe(SESSION, kind, target, container)
    finally:
        await SESSION.close()


def met(result):
    return {c["check"]: c["met"] for c in result["checks"]}


GOOD_DIALOG = """
<button id="open">Abrir</button>
<dialog id="d" aria-labelledby="t"><h2 id="t">Confirmar</h2><button id="x">Fechar</button><button>Ok</button></dialog>
<script>
 document.getElementById('open').addEventListener('click', () => document.getElementById('d').showModal());
 document.getElementById('x').addEventListener('click', () => document.getElementById('d').close());
</script>"""

BAD_DIALOG = """
<button id="open">Abrir</button><a href="#">Link de fundo</a><button>Outro fundo</button>
<div id="d" role="dialog" hidden style="position:fixed;top:20px;left:20px;background:#fff;border:1px solid"><p>Sem nome</p><button id="x">Fechar</button></div>
<script>
 document.getElementById('open').addEventListener('click', () => { document.getElementById('d').hidden = false; });
 document.getElementById('x').addEventListener('click', () => { document.getElementById('d').hidden = true; });
</script>"""


async def test_dialog_good_native_modal_meets_the_whole_contract():
    r = await probe(GOOD_DIALOG, "dialog", "css:#open")
    assert r["unmet"] == [], r["checks"]
    m = met(r)
    assert m["foco_vai_para_dentro"] and m["tab_fica_dentro"] and m["escape_fecha"] and m["foco_volta_ao_gatilho"]


async def test_dialog_bad_custom_reports_every_broken_expectation_as_facts():
    r = await probe(BAD_DIALOG, "dialog", "css:#open")
    m = met(r)
    assert m["abre_com_teclado"] is True
    assert m["foco_vai_para_dentro"] is False  # o foco ficou no botao de fundo
    assert m["tem_nome_acessivel"] is False and m["declara_modal"] is False
    assert m["tab_fica_dentro"] is False  # o Tab vaza para a pagina
    assert m["escape_fecha"] is False
    assert m["foco_volta_ao_gatilho"] is None  # nao testavel: nao fechou
    assert r["summary"].startswith("5 de ") and "observed" in r["checks"][0]


async def test_dialog_probe_says_when_nothing_opens():
    r = await probe('<button id="b">Nada</button>', "dialog", "css:#b")
    assert met(r)["abre_com_teclado"] is False and len(r["checks"]) == 2


GOOD_DISC = """<button id="b" aria-expanded="false" aria-controls="p">Detalhes</button><div id="p" hidden>Conteudo</div>
<script>const b=document.getElementById('b'),p=document.getElementById('p');
 b.addEventListener('click',()=>{const o=b.getAttribute('aria-expanded')==='true';b.setAttribute('aria-expanded',String(!o));p.hidden=o;});</script>"""
BAD_DISC = """<div id="b" tabindex="0" style="cursor:pointer">Detalhes</div><div id="p" hidden>Conteudo</div>
<script>document.getElementById('b').addEventListener('click',()=>{const p=document.getElementById('p');p.hidden=!p.hidden;});</script>"""


async def test_disclosure_good_vs_mouse_only():
    good = await probe(GOOD_DISC, "disclosure", "css:#b")
    assert good["unmet"] == [], good["checks"]
    bad = await probe(BAD_DISC, "disclosure", "css:#b")
    m = met(bad)
    assert m["expoe_estado"] is False and m["enter_alterna"] is False and m["espaco_alterna"] is False


GOOD_MENU = """<button id="mb" aria-haspopup="menu" aria-expanded="false" aria-controls="mm">Acoes</button>
<ul id="mm" role="menu" hidden><li role="menuitem" tabindex="-1">Um</li><li role="menuitem" tabindex="-1">Dois</li><li role="menuitem" tabindex="-1">Tres</li></ul>
<script>const mb=document.getElementById('mb'),mm=document.getElementById('mm'),it=[...mm.children];
 const open=(i)=>{mm.hidden=false;mb.setAttribute('aria-expanded','true');it[i].focus();};
 const close=()=>{mm.hidden=true;mb.setAttribute('aria-expanded','false');mb.focus();};
 mb.addEventListener('click',()=>open(0));
 mm.addEventListener('keydown',(e)=>{const i=it.indexOf(document.activeElement);
  if(e.key==='ArrowDown'){e.preventDefault();it[(i+1)%it.length].focus();}
  else if(e.key==='ArrowUp'){e.preventDefault();it[(i+it.length-1)%it.length].focus();}
  else if(e.key==='Home'){e.preventDefault();it[0].focus();}
  else if(e.key==='End'){e.preventDefault();it[it.length-1].focus();}
  else if(e.key==='Escape'){close();}});</script>"""
BAD_MENU = """<div id="mb" role="button" tabindex="0" aria-haspopup="true">Categorias</div><ul id="mm" hidden><li><a href="/a">A</a></li></ul>
<script>document.getElementById('mb').addEventListener('click',()=>{document.getElementById('mm').hidden=false;});</script>"""


async def test_menu_button_good_vs_click_only():
    good = await probe(GOOD_MENU, "menu", "css:#mb")
    assert good["unmet"] == [], good["checks"]
    bad = await probe(BAD_MENU, "menu", "css:#mb")
    assert met(bad)["abre_com_teclado"] is False and met(bad)["expoe_estado"] is False


GOOD_TABS = """<div role="tablist" aria-label="Secoes">
<button role="tab" id="t1" aria-selected="true" aria-controls="p1" tabindex="0">Um</button>
<button role="tab" id="t2" aria-selected="false" aria-controls="p2" tabindex="-1">Dois</button>
<button role="tab" id="t3" aria-selected="false" aria-controls="p3" tabindex="-1">Tres</button></div>
<div role="tabpanel" id="p1" tabindex="0">Painel um</div><div role="tabpanel" id="p2" tabindex="0" hidden>Painel dois</div><div role="tabpanel" id="p3" tabindex="0" hidden>Painel tres</div>
<script>const tabs=[...document.querySelectorAll('[role=tab]')];
 const sel=(i)=>tabs.forEach((t,j)=>{t.setAttribute('aria-selected',String(i===j));t.tabIndex=i===j?0:-1;document.getElementById(t.getAttribute('aria-controls')).hidden=i!==j;if(i===j)t.focus();});
 document.querySelector('[role=tablist]').addEventListener('keydown',(e)=>{const i=tabs.indexOf(document.activeElement);
  if(e.key==='ArrowRight'){e.preventDefault();sel((i+1)%tabs.length);}
  else if(e.key==='ArrowLeft'){e.preventDefault();sel((i+tabs.length-1)%tabs.length);}
  else if(e.key==='Home'){e.preventDefault();sel(0);}
  else if(e.key==='End'){e.preventDefault();sel(tabs.length-1);}});
 tabs.forEach((t,i)=>t.addEventListener('click',()=>sel(i)));</script>"""
BAD_TABS = """<div role="tablist"><div role="tab" id="t1" aria-selected="true">Um</div><div role="tab" id="t2" aria-selected="false">Dois</div></div>
<div id="p1">Painel</div>
<script>document.querySelectorAll('[role=tab]').forEach((t)=>t.addEventListener('click',()=>{}));</script>"""


async def test_tabs_good_vs_unreachable_by_keyboard():
    good = await probe(GOOD_TABS, "tabs", "css:#t1")
    assert good["unmet"] == [], good["checks"]
    assert met(good)["ativacao"] is None  # automatica ou manual: ambas validas, so fato
    bad = await probe(BAD_TABS, "tabs", "css:#t1")
    m = met(bad)
    assert m["uma_parada_de_tab"] is False and m["seta_move_o_foco"] is False


GOOD_COMBO = """<label for="cb">Cidade</label>
<input id="cb" role="combobox" aria-expanded="false" aria-controls="lb" aria-autocomplete="list" aria-activedescendant="">
<ul id="lb" role="listbox" hidden><li role="option" id="o1">Rio</li><li role="option" id="o2">Sao Paulo</li><li role="option" id="o3">Recife</li></ul>
<script>const cb=document.getElementById('cb'),lb=document.getElementById('lb'),op=[...lb.children];let idx=-1;
 const setA=(i)=>{idx=i;op.forEach((o,j)=>o.setAttribute('aria-selected',String(j===i)));cb.setAttribute('aria-activedescendant',i>=0?op[i].id:'');};
 const open=()=>{lb.hidden=false;cb.setAttribute('aria-expanded','true');};
 const close=()=>{lb.hidden=true;cb.setAttribute('aria-expanded','false');setA(-1);};
 cb.addEventListener('keydown',(e)=>{
  if(e.key==='ArrowDown'){e.preventDefault();if(lb.hidden){open();setA(0);}else setA((idx+1)%op.length);}
  else if(e.key==='Enter'){if(idx>=0){e.preventDefault();cb.value=op[idx].textContent;close();}}
  else if(e.key==='Escape'){close();}});</script>"""
BAD_COMBO = """<label for="cb">Cidade</label><input id="cb" type="text"><ul id="lb" hidden><li>Rio</li></ul>
<script>document.getElementById('cb').addEventListener('input',()=>{document.getElementById('lb').hidden=false;});</script>"""


async def test_combobox_good_vs_plain_text_field():
    good = await probe(GOOD_COMBO, "combobox", "css:#cb")
    assert good["unmet"] == [], good["checks"]
    bad = await probe(BAD_COMBO, "combobox", "css:#cb")
    m = met(bad)
    assert m["papel_combobox"] is False and m["abre_com_seta"] is False


async def test_combobox_with_native_datalist_is_not_misreported_as_broken():
    r = await probe('<label for="c">Cat</label><input id="c" list="d"><datalist id="d"><option value="A"><option value="B"></datalist>', "combobox", "css:#c")
    assert met(r)["abre_a_lista"] is None and r["unmet"] == []  # popup nativo nao e observavel: nao afirma falha


FORM_GOOD = """<form id="f" novalidate><label for="em">Email</label><input id="em" type="email" required aria-describedby="err"><span id="err"></span>
<button id="go" type="submit">Enviar</button></form>
<script>document.getElementById('f').addEventListener('submit',(e)=>{e.preventDefault();const em=document.getElementById('em');
 if(!em.checkValidity()){em.setAttribute('aria-invalid','true');document.getElementById('err').textContent='Informe um e-mail valido';em.focus();}});</script>"""
FORM_BAD = """<form id="f" novalidate onsubmit="return false"><label for="em">Email</label><input id="em" type="email" required><button id="go" type="submit">Enviar</button></form>"""


async def test_form_errors_good_vs_silent_form():
    good = await probe(FORM_GOOD, "form_errors", "css:#go")
    assert good["unmet"] == [], good["checks"]
    bad = await probe(FORM_BAD, "form_errors", "css:#go")
    m = met(bad)
    assert m["campo_invalido_marcado"] is False and m["erro_descrito_no_campo"] is False and m["foco_vai_ao_erro"] is False and m["erro_anunciado"] is False


ROUTE_GOOD = """<nav><a href="#/sobre" id="lnk">Sobre</a></nav><h1 id="h" tabindex="-1">Inicio</h1><div id="live" role="status"></div>
<script>document.getElementById('lnk').addEventListener('click',(e)=>{e.preventDefault();history.pushState({},'','#/sobre');
 document.title='Sobre';const h=document.getElementById('h');h.textContent='Sobre';h.focus();document.getElementById('live').textContent='Pagina Sobre';});</script>"""
ROUTE_BAD = """<nav><a href="#/sobre" id="lnk">Sobre</a></nav><h1>Inicio</h1>
<script>document.getElementById('lnk').addEventListener('click',(e)=>{e.preventDefault();history.pushState({},'','#/sobre');document.body.innerHTML='<h1>Sobre</h1>';});</script>"""


async def test_route_change_good_vs_silent_spa_navigation():
    good = await probe(ROUTE_GOOD, "route_change", "css:#lnk")
    assert good["unmet"] == [], good["checks"]
    bad = await probe(ROUTE_BAD, "route_change", "css:#lnk")
    m = met(bad)
    assert m["titulo_muda"] is False and m["foco_nao_se_perde"] is False and m["troca_perceptivel"] is False


async def test_tab_walk_finds_the_keyboard_trap_and_a_clean_page_has_none():
    trap = '<a href="#">Antes</a><div id="t" tabindex="0">Preso</div><a href="#">Depois</a><script>document.getElementById("t").addEventListener("keydown",(e)=>{if(e.key==="Tab")e.preventDefault();});</script>'
    r = await probe(trap, "tab_walk")
    assert r["stuck_at"] and r["stuck_at"][0]["tag"] == "div" and "armadilha" in r["ended_because"]
    clean = await probe('<a href="#">Um</a><button>Dois</button><a href="#">Tres</a>', "tab_walk")
    assert clean["stuck_at"] == [] and clean["stops_total"] == 3 and "saiu da pagina" in clean["ended_because"]


async def test_focus_obscured_finds_a_link_under_a_fixed_header():
    page = '<style>#bar{position:fixed;top:0;left:0;right:0;height:60px;background:#222;z-index:10}</style><div id="bar">cabecalho</div><a href="#" style="position:absolute;top:10px;left:10px">Link coberto</a><a href="#" style="position:absolute;top:200px;left:10px">Link livre</a>'
    r = await probe(page, "focus_obscured")
    assert len(r["obscured"]) == 1 and r["obscured"][0]["name"] == "Link coberto" and r["obscured"][0]["obscured"]["by"]["position"] == "fixed"
    assert r["stops_checked"] == 2


async def test_target_size_flags_tiny_adjacent_targets_but_not_spaced_or_big_ones():
    page = ('<button style="width:10px;height:10px;padding:0">a</button><button style="width:10px;height:10px;padding:0">b</button>'
            '<button style="width:10px;height:10px;padding:0;margin-left:300px">c</button><button style="width:44px;height:44px;margin-left:300px">grande</button>')
    r = await probe(page, "target_size")
    names = {o["name"] for o in r["fail_spacing_exception"]}
    assert names == {"a", "b"}  # o "c" e' pequeno mas isolado: escapa pela excecao de espacamento
    assert r["smaller_than_24px"] == 3 and any("10x10" in x for x in r["small_but_spaced"])


async def test_probe_validation_and_registry():
    assert set(PROBES) >= {"tab_walk", "focus_obscured", "target_size", "dialog", "disclosure", "menu", "tabs", "combobox", "form_errors", "route_change"}
    await SESSION.open(None, HEAD + "<button id='b'>x</button></body></html>")
    try:
        with pytest.raises(SessionError):
            await run_probe(SESSION, "inexistente")
        with pytest.raises(SessionError):
            await run_probe(SESSION, "dialog")  # precisa de target
        await run_probe(SESSION, "tab_walk")
        assert "tab_walk" in SESSION.coverage_report()["probes_run"] and SESSION.trace[-1]["kind"] == "probe:tab_walk"
    finally:
        await SESSION.close()
