"""Cobertura total: Shadow DOM, iframes, mapa da pagina (todo o conteudo) e relatorio do que ficou de fora."""
import json

import pytest

from accessibility_mcp.a11y.session import SESSION

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
    assert any(d["on"] == "document" and d["type"] == "click" for d in m["delegated_listeners"])  # acao delegada: alvo real desconhecido


async def test_reading_order_same_visual_line_is_not_a_false_inversion_just_because_boxes_differ_in_height():
    """Regressao real (achada testando um site proprio ao vivo): dois elementos na MESMA linha visual, um mais
    alto que o outro (padding maior), tinham a borda superior separada por mais de 8px - o bucket fixo antigo
    os jogava em "linhas" diferentes e acusava uma inversao de ordem de leitura que nao existe: da esquerda pra
    direita, quem vem primeiro no DOM tambem aparece primeiro na tela."""
    html = (
        "<!doctype html><html lang='pt'><title>t</title><body>"
        "<button style='padding:1px 6px'>Primeiro</button>"
        "<span style='display:inline-block;padding:8px 16px'>Segundo</span>"
        "</body></html>"
    )
    await SESSION.open(None, html)
    try:
        d = (await SESSION.page_map())["main"]
        assert d["reading_order"]["inverted_pairs"] == 0
    finally:
        await SESSION.close()


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
    from accessibility_mcp import server as mcp_server

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


async def test_focus_style_works_for_elements_inside_shadow_dom_and_iframes(rich):
    """Regressao (achada pela prova ponta a ponta): focus_style procurava so no documento principal."""
    d = await rich.dossier("", 100)
    by_text = {e["text"]: e for e in d["elements"] if e["text"]}
    for text in ("Botao no shadow", "Botao do iframe", "Principal"):
        fs = await rich.focus_style(by_text[text]["id"])
        assert "changed_on_focus" in fs and "outline_when_focused" in fs, text


async def test_reading_an_element_does_not_count_as_probing_its_behavior(rich):
    """Regressao real (achada varrendo o site de pesquisas com todas as ferramentas): announce, screenshot, focus_style e preview_css
    marcavam o elemento como 'sondado por comportamento', e o relatorio dizia ao mesmo tempo 'nenhuma acao foi executada'. Ler a arvore
    de um elemento nao e provar como ele se comporta; o relatorio existe para impedir confianca falsa."""
    d = await rich.dossier("", 100)
    alvo = next(e["id"] for e in d["elements"] if e["actionable"] and e["focusable"])
    await rich.announce(alvo)
    await rich.focus_style(alvo)
    await rich.screenshot(alvo)
    lido = rich.coverage_report()
    assert lido["interactive"]["probed_by_behavior"] == 0
    assert any("nenhuma acao, sonda ou alcance" in g for g in lido["gaps"])

    await rich.reach(alvo)  # Tab ate o alvo e' comportamento de teclado
    alcancado = rich.coverage_report()
    assert alcancado["interactive"]["probed_by_behavior"] == 1 and "reach" in alcancado["probes_run"]
    assert not any("nenhuma acao" in g for g in alcancado["gaps"])  # ja houve prova por comportamento, mesmo sem a11y_act


async def test_page_map_tells_what_lives_inside_list_items_and_whether_the_marker_was_removed():
    """Pedido do dono (visto ouvindo o site): o leitor diz "lista com N itens" e depois o titulo de cada item. Antes o mapa so contava listas
    (ul, ol); nao mostrava que titulos moram dentro dos itens, nem de que nivel, nem se o marcador foi removido (o WebKit deixa de tratar
    como lista). Sao fatos; julgar se incomoda e' do modelo."""
    html = (
        "<!doctype html><html lang='pt'><title>t</title><body><main><h1>Pagina</h1>"
        "<ul id='cartoes' style='list-style:none'><li><h2><a href='/a'>Um</a></h2><p>x</p></li><li><h2><a href='/b'>Dois</a></h2></li></ul>"
        "<ol><li>passo um</li><li>passo dois</li><li>passo tres</li></ol></main></body></html>"
    )
    await SESSION.open(None, html)
    try:
        d = (await SESSION.page_map())["main"]["lists"]
        cartoes, passos = d["details"]
        assert (d["ul"], d["ol"], d["lists_with_headings_in_items"]) == (1, 1, 1)
        assert cartoes["items"] == 2 and cartoes["items_with_heading"] == 2 and cartoes["marker_removed"] is True
        assert [h["level"] for h in cartoes["headings_in_items"]] == [2, 2] and cartoes["headings_in_items"][0]["text"] == "Um"
        assert passos["items"] == 3 and passos["items_with_heading"] == 0 and passos["marker_removed"] is False
        from accessibility_mcp.a11y.agent import page_map_text

        texto = page_map_text(await SESSION.page_map())
        assert "ul[2 itens, titulos nos itens=['h2', 'h2'], marcador removido]" in texto and "ol[3 itens]" in texto
    finally:
        await SESSION.close()


async def test_reading_order_does_not_compare_an_element_with_its_own_descendant():
    """Regressao real (achada rastreando o site de exemplos: 2 a 3 'inversoes' em todas as paginas): um h2 e o span DENTRO dele eram contados
    como dois itens da ordem de leitura, e o texto do span ('Exemplo ruim:') vem antes do resto do texto do h2, entao parecia invertido.
    Elemento e descendente se entrelacam por definicao; a ordem de leitura compara itens que nao estao um dentro do outro."""
    html = (
        "<!doctype html><html lang='pt'><title>t</title><body><main><h1>Pagina</h1>"
        "<h2 style='font-size:20px;line-height:1'><span style='font-weight:700;font-size:22px'>Exemplo ruim:</span> Div que faz o papel de botao</h2><p>texto</p></main></body></html>"
    )
    await SESSION.open(None, html)
    try:
        d = (await SESSION.page_map())["main"]["reading_order"]
        assert d["inverted_pairs"] == 0, d["adjacent_inversions_examples"]
    finally:
        await SESSION.close()


async def test_reading_order_ignores_the_content_of_a_closed_details():
    """Regressao real (rodada ao vivo no site de exemplos): o paragrafo dentro de <details> fechado nao e renderizado mas tem retangulo, e virava inversao falsa."""
    await SESSION.open(
        None,
        "<!doctype html><html lang='pt'><head><title>t</title></head><body><main><h1>Titulo</h1>"
        "<details><summary>Prazo</summary><p>Cinco dias uteis.</p></details><h2>Depois</h2><p>Texto de depois.</p></main></body></html>",
    )
    try:
        mapa = await SESSION.page_map()
    finally:
        await SESSION.close()
    ordem = mapa["main"]["reading_order"]
    # h1, summary, h2 e o paragrafo de depois: o paragrafo do <details> fechado nao e renderizado e nao entra na comparacao
    assert ordem["items_compared"] == 4 and ordem["inverted_pairs"] == 0, ordem
