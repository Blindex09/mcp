"""Cobertura total: Shadow DOM, iframes, mapa da pagina (todo o conteudo) e relatorio do que ficou de fora."""
import json

import pytest

from a11y.session import SESSION

IFRAME_DOC = (
    "<html><body><h1>Dentro</h1><button id='ib'>Botao do iframe</button><div id='idiv'>div do iframe</div>"
    "<script>document.getElementById('idiv').addEventListener('click',()=>{document.title='clicou'})</script></body></html>"
)
RICH = """<!doctype html><html lang="pt"><head><title>Rica</title>
<style>.dd:hover .menu { display: block } .menu { display: none } .fx { display: flex }</style></head><body>
<header><nav aria-label="Principal"><a href="/a">Inicio</a><a href="/b">Inicio</a></nav></header>
<main>
 <h1>Titulo</h1><h3>Pulou o h2</h3>
 <img src="a.png"><img src="b.png" alt=""><figure><img src="c.png" alt="Grafico de vendas"><figcaption>Vendas</figcaption></figure>
 <form aria-label="Busca"><input name="q" placeholder="Buscar"><label for="e">E-mail</label><input id="e" name="e" autocomplete="email"></form>
 <table><tr><td>a</td><td>b</td></tr></table>
 <div class="dd"><span>Menu</span><div class="menu">itens</div></div>
 <div class="fx"><div style="order:2">segundo</div><div style="order:1">primeiro</div></div>
 <button id="main-btn">Principal</button>
 <x-open id="ho"></x-open><x-closed id="hc"></x-closed>
 <iframe title="Quadro" srcdoc="__IFRAME__"></iframe>
</main>
<script>
 const o = document.getElementById('ho').attachShadow({mode: 'open'});
 o.innerHTML = '<h2>Titulo no shadow</h2><button id="sb">Botao no shadow</button><div id="sdiv">div no shadow</div>';
 o.getElementById('sdiv').addEventListener('click', () => { window.shadowClicked = true; });
 const c = document.getElementById('hc').attachShadow({mode: 'closed'});
 c.innerHTML = '<button id="cb">Botao no shadow fechado</button>';
 document.addEventListener('click', () => {});
</script></body></html>""".replace("__IFRAME__", IFRAME_DOC.replace('"', "&quot;"))


@pytest.fixture()
async def rich():
    await SESSION.open(None, RICH)
    yield SESSION
    await SESSION.close()


async def test_page_map_gives_facts_about_all_the_content(rich):
    m = await rich.page_map()
    d = m["main"]
    assert d["document"]["lang"] == "pt" and d["document"]["shadow_hosts_open"] == 1
    heads = [(h["level"], h["text"]) for h in d["headings"]["outline"]]
    assert (1, "Titulo") in heads and (2, "Titulo no shadow") in heads  # atravessa Shadow DOM aberto
    assert {"from": 1, "to": 3, "text": "Pulou o h2"} in d["headings"]["level_jumps"]
    alts = [i["alt"] for i in d["images"]["items"]]
    assert None in alts and "" in alts and "Grafico de vendas" in alts  # ausente, vazio e descritivo sao fatos distintos
    assert d["links"]["same_text_different_destination"] == [{"text": "inicio", "distinct_destinations": 2}]
    assert d["forms"]["fields_without_any_name"] == 1 and d["forms"]["fields_total"] == 2
    assert d["tables"]["items"][0]["header_cells"] == 0
    assert d["iframes"][0]["title"] == "Quadro"
    assert d["hover_reveals"]["items"][0]["rule"] == ".dd:hover .menu"
    assert d["reading_order"]["inverted_pairs"] >= 1 and d["reading_order"]["css_order_used"] >= 2
    assert d["landmarks"]["total"] >= 3
    assert m["frames"][0]["map"]["headings"]["outline"][0]["text"] == "Dentro"  # cada iframe tem o seu mapa
    assert {"on": "document", "type": "click"} in m["delegated_listeners"]  # acao delegada: alvo real desconhecido


async def test_page_map_scope_error_and_fact_only_output(rich):
    assert "scope nao encontrado" in (await rich.page_map("#nao-existe"))["error"]
    text = json.dumps(await rich.page_map())
    assert "verdict" not in text and "veredito" not in text


async def test_dossier_crosses_shadow_dom_and_iframes(rich):
    d = await rich.dossier("", 100)
    by_text = {e["text"]: e for e in d["elements"] if e["text"]}
    sh = by_text["Botao no shadow"]
    assert sh["where"]["in_shadow"] is True and sh["where"]["shadow_host"] == "x-open" and sh["actionable"] is True
    assert sh["computed"]["role"] == "button"
    div_shadow = by_text["div no shadow"]
    assert div_shadow["clickable"] is True and div_shadow["focusable"] is False and div_shadow["computed"]["role"] == "generic"
    closed = by_text["Botao no shadow fechado"]
    assert closed["where"]["in_shadow"] is True and closed["actionable"] is False  # medido, mas nao da para agir
    ifr = by_text["Botao do iframe"]
    assert ifr["where"]["frame_url"].startswith("about:srcdoc") and ifr["actionable"] is True
    assert by_text["div do iframe"]["clickable"] is True
    assert any("Shadow DOM fechado" in x for x in d["limits"])


async def test_actions_reach_elements_inside_shadow_dom_and_iframes(rich):
    d = await rich.dossier("", 100)
    by_text = {e["text"]: e for e in d["elements"] if e["text"]}
    await rich.act("click", by_text["div no shadow"]["id"])
    assert await rich.page.evaluate("() => window.shadowClicked === true")
    await rich.act("focus", by_text["Botao do iframe"]["id"])
    assert await rich.page.frames[1].evaluate("() => document.activeElement && document.activeElement.id") == "ib"
    await rich.act("click", by_text["div do iframe"]["id"])
    assert await rich.page.frames[1].evaluate("() => document.title") == "clicou"
    assert (await rich.reach(by_text["Botao no shadow"]["id"]))["reached"] is True  # Tab atravessa o shadow


async def test_coverage_report_lists_gaps_then_closes_them(rich):
    first = rich.coverage_report()
    assert first["interactive"]["listed"] == 0
    assert any("dossie nao foi consultado" in g for g in first["gaps"])
    assert any("mapa da pagina" in g for g in first["gaps"])
    d = await rich.dossier("", 100)
    await rich.page_map()
    await rich.design_tokens()
    await rich.stress("reflow_320")
    await rich.stress("text_spacing")
    mid = rich.coverage_report()
    assert mid["interactive"]["listed"] == len(d["elements"]) and mid["frames"] == {"total": 2, "mapped": 2}
    assert any("nunca foram sondados" in g for g in mid["gaps"]) and any("nenhuma acao" in g for g in mid["gaps"])
    actionable = [e for e in d["elements"] if e["actionable"]]
    for e in actionable:
        await rich.act("focus", e["id"])
    done = rich.coverage_report()
    assert done["interactive"]["probed_by_behavior"] == len(actionable)
    assert done["design_measured"] is True and done["stress_run"] == ["reflow_320", "text_spacing"] and done["actions_taken"] > 0
    assert set(done["interactive"]["listed_never_probed"]) == {e["id"] for e in d["elements"] if not e["actionable"]}


async def test_coverage_reports_truncation_instead_of_hiding_it(rich):
    d = await rich.dossier("", 3)
    assert len(d["elements"]) == 3 and d["not_listed_over_limit"] > 0
    assert any("nao foram listados" in g for g in rich.coverage_report()["gaps"])


async def test_shadow_and_iframe_also_work_without_cdp():
    await SESSION.open(None, RICH, browser="firefox")
    try:
        d = await SESSION.dossier("", 100)
        by_text = {e["text"]: e for e in d["elements"] if e["text"]}
        assert by_text["Botao no shadow"]["where"]["in_shadow"] is True
        assert by_text["Botao do iframe"]["where"]["frame_url"].startswith("about:srcdoc")
        assert by_text["div no shadow"]["clickable"] is True  # listener visto pelo gancho
        assert "Botao no shadow fechado" not in by_text  # Shadow DOM fechado: JS nao alcanca
        await SESSION.act("focus", by_text["Botao do iframe"]["id"])
        assert await SESSION.page.frames[1].evaluate("() => document.activeElement.id") == "ib"
        m = await SESSION.page_map()
        assert m["frames"][0]["map"]["headings"]["outline"][0]["text"] == "Dentro"
    finally:
        await SESSION.close()


async def test_tools_registered_and_json():
    import mcp_server

    tools = mcp_server.mcp._tool_manager
    assert "nenhuma sessao" in json.loads(await tools.get_tool("a11y_page_map").fn())["error"]
    assert "nenhuma sessao" in json.loads(await tools.get_tool("a11y_coverage").fn())["error"]
    await tools.get_tool("a11y_open").fn(html=RICH)
    try:
        pm = json.loads(await tools.get_tool("a11y_page_map").fn())
        assert pm["main"]["document"]["lang"] == "pt"
        cov = json.loads(await tools.get_tool("a11y_coverage").fn())
        assert cov["page_map"] is True and cov["gaps"]
    finally:
        await tools.get_tool("a11y_close").fn()
