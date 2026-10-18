"""Sondas de comportamento: o que so aparece AGINDO na pagina (armadilha de teclado, foco coberto, contrato de teclado de um dialogo,
menu, abas ou combobox, erros de formulario, troca de rota).

Os scanners de pagina nao enxergam isso (o axe nao verifica armadilha de foco nem retorno de foco). Aqui o servidor AGE como o
teclado de uma pessoa faria e devolve FATOS: para os contratos, uma lista `esperado x observado` por verificacao.

Divisao de papeis (regra do projeto):
- o MODELO decide qual padrao um componente e' naquele site (dialogo? menu? abas?) e escolhe a sonda;
- o CODIGO executa as teclas e mede. O `esperado` vem do WAI-ARIA Authoring Practices (APG), definicao normativa de cada padrao, nao
  opiniao; se o componente DEVERIA seguir aquele padrao e se um desvio e' defeito continua sendo julgamento do modelo.
Toda sonda usa so o teclado, entao vale para qualquer persona.
"""

from __future__ import annotations

import itertools
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urldefrag

from . import page_scripts as js


def _check(name: str, expected: str, observed: str, met: bool | None, wcag: list[str] | None = None) -> dict[str, Any]:
    """Uma verificacao: met True/False e' fato medido; None = nao deu para medir (e a razao esta em observed)."""
    return {"check": name, "expected": expected, "observed": observed, "met": met, "related_wcag": wcag or []}


def _report(kind: str, target: str | None, checks: list[dict[str, Any]], facts: dict[str, Any], source: str) -> dict[str, Any]:
    unmet = [c["check"] for c in checks if c["met"] is False]
    return {
        "probe": kind, "target": target, "checks": checks, "unmet": unmet,
        "summary": f"{len(unmet)} de {len(checks)} verificacoes do contrato nao foram atendidas" + (f": {', '.join(unmet)}" if unmet else ""),
        "contract_source": source, "facts": facts,
        "note": "esperado vem do padrao citado; se o componente deveria seguir esse padrao e se o desvio e' defeito e' julgamento do modelo",
    }


async def _key(s: Any, key: str, settle: bool = True) -> None:
    await s.page.keyboard.press(key)
    if settle:
        await s._settle()


async def _ident(s: Any) -> tuple[Any, dict[str, Any] | None]:
    f = await s._focus_probe(with_identity=True)
    return (f.get("_ident") if f else None), f


def _where(f: dict[str, Any] | None) -> str:
    return f"{f['tag']} {f['name']!r}" if f else "nenhum elemento (corpo da pagina)"


async def _focus_target(s: Any, target: str) -> tuple[Any, Any]:
    loc = s._locator(target, behavior=True)
    if await loc.count() == 0:
        from .session import SessionError

        raise SessionError("elemento nao encontrado (rode a11y_dossier de novo depois de navegar)")
    await loc.focus()
    await s._settle()
    ident, f = await _ident(s)
    return loc, (ident, f)


# ------------------------------------------------------------------------------------------------ varredura de Tab
async def tab_walk(s: Any, target: str | None = None, container: str | None = None, max_stops: int = 0) -> dict[str, Any]:
    """Aperta Tab do inicio da pagina e registra cada parada: nome, se o foco esta coberto por outro elemento, e onde o foco ficou preso."""
    page = s._need()
    await page.evaluate("() => { const b = document.body; b.setAttribute('tabindex', '-1'); b.focus(); b.removeAttribute('tabindex'); }")
    stops: list[dict[str, Any]] = []
    idents: list[Any] = []
    first = None
    stuck: list[dict[str, Any]] = []
    end = "orcamento de paradas escolhido pela pessoa"
    for i in range(1, int(max_stops) + 1) if int(max_stops) > 0 else itertools.count(1):
        if s.stop_requested:
            end = "interrompido pela pessoa"
            break
        await page.keyboard.press("Tab")
        ident, f = await _ident(s)
        if f is None:
            end = "o foco saiu da pagina (volta ao navegador)"
            break
        if first is None:
            first = ident
        elif ident == first:
            end = "o foco deu a volta ate a primeira parada (ciclo completo)"
            break
        obscured = await page.evaluate(js.PROBE_OBSCURED_JS)
        stop = {"n": i, "tag": f["tag"], "role": f.get("role"), "name": f["name"], "id": f.get("id"), "focus_style": f.get("focus_style")}
        if obscured and obscured.get("covered"):
            stop["obscured"] = {"covered_points": f"{obscured['covered']}/{obscured['points']}", "by": obscured.get("covered_by"), "rect": obscured.get("rect")}
        if obscured and obscured.get("offscreen") and obscured.get("offscreen") == obscured.get("points"):
            stop["offscreen"] = True
        stops.append(stop)
        idents.append(ident)
        if len(idents) >= 3 and idents[-1] == idents[-2] == idents[-3]:
            stuck.append({"n": i, "tag": f["tag"], "name": f["name"]})
            end = "o foco parou de mover: Tab nao sai deste elemento (possivel armadilha de teclado)"
            break
        window = idents[-12:]
        if len(idents) >= 14 and len(set(window)) <= 3:
            stuck.append({"n": i, "tag": f["tag"], "name": f["name"], "loop_of": len(set(window))})
            end = "o foco circula entre poucos elementos sem avancar (possivel armadilha de teclado)"
            break
    return {
        "probe": "tab_walk", "stops_total": len(stops), "ended_because": end, "stuck_at": stuck,
        "stops": stops[:60] + ([{"n": "...", "note": f"{len(stops) - 60} paradas omitidas"}] if len(stops) > 60 else []),
        "obscured_stops": [x for x in stops if x.get("obscured")][:20], "offscreen_stops": [x["n"] for x in stops if x.get("offscreen")][:20],
        "summary": f"{len(stops)} paradas; fim: {end}; presas: {len(stuck)}; focos cobertos: {sum(1 for x in stops if x.get('obscured'))}",
        "note": "fatos de Tab (WCAG 2.1.2 armadilha, 2.4.3 ordem, 2.4.7 visivel, 2.4.11 nao coberto); se a ordem faz sentido e' julgamento",
    }


async def focus_obscured(s: Any, target: str | None = None, container: str | None = None, max_stops: int = 0) -> dict[str, Any]:
    """So os focos cobertos por outro elemento (cabecalho fixo, banner de cookies...) durante uma varredura de Tab (WCAG 2.4.11)."""
    walk = await tab_walk(s, None, None, max_stops)
    return {
        "probe": "focus_obscured", "stops_checked": walk["stops_total"], "obscured": walk["obscured_stops"], "offscreen": walk["offscreen_stops"],
        "summary": f"{len(walk['obscured_stops'])} de {walk['stops_total']} paradas de Tab com o foco coberto por outro elemento",
        "note": "coberto = pontos do retangulo do elemento em foco em que outro elemento esta por cima; se esconde a parte relevante e' julgamento",
    }


# ------------------------------------------------------------------------------------------------ tamanho de alvo
async def target_size(s: Any, target: str | None = None, container: str | None = None, max_stops: int = 0) -> dict[str, Any]:
    """WCAG 2.5.8: alvos menores que 24x24 px CSS e se escapam pela excecao de espacamento (circulo de 24 px sem tocar outro alvo)."""
    dossier = await s.dossier("", 200)
    boxes = []
    for e in dossier["elements"]:
        r = e.get("rect") or {}
        if r.get("w", 0) > 0 and r.get("h", 0) > 0 and not e["states"].get("disabled"):
            name = ((e.get("computed") or {}).get("name") or e.get("text") or "")[:40]
            boxes.append({"id": e["id"], "tag": e["tag"], "name": name, "x": r["x"], "y": r["y"], "w": r["w"], "h": r["h"]})
    small = [b for b in boxes if b["w"] < 24 or b["h"] < 24]

    def circle(b: dict[str, Any]) -> tuple[float, float, float]:
        return b["x"] + b["w"] / 2, b["y"] + b["h"] / 2, 12.0

    def touches_box(c: tuple[float, float, float], b: dict[str, Any]) -> bool:
        nx = min(max(c[0], b["x"]), b["x"] + b["w"])
        ny = min(max(c[1], b["y"]), b["y"] + b["h"])
        return (c[0] - nx) ** 2 + (c[1] - ny) ** 2 < c[2] ** 2

    offenders = []
    for b in small:
        c = circle(b)
        near = [o["id"] for o in boxes if o["id"] != b["id"] and touches_box(c, o)]
        near += [o["id"] for o in small if o["id"] != b["id"] and o["id"] not in near and (circle(o)[0] - c[0]) ** 2 + (circle(o)[1] - c[1]) ** 2 < 24 ** 2]
        if near:
            offenders.append({"id": b["id"], "tag": b["tag"], "name": b["name"], "size": f"{b['w']}x{b['h']}", "touches": near[:6]})
    return {
        "probe": "target_size", "targets_measured": len(boxes), "smaller_than_24px": len(small), "fail_spacing_exception": offenders[:40],
        "small_but_spaced": [f"{b['id']} {b['w']}x{b['h']}" for b in small if b["id"] not in {o["id"] for o in offenders}][:20],
        "summary": f"{len(small)} de {len(boxes)} alvos medem menos de 24x24 px; {len(offenders)} deles tambem nao escapam pelo espacamento",
        "note": "fatos de geometria (WCAG 2.5.8). Excecoes que so o modelo decide: link dentro de texto corrido, controle nativo do navegador, equivalente de tamanho adequado na mesma pagina",
    }


# ------------------------------------------------------------------------------------------------ contratos APG
APG_DIALOG = "WAI-ARIA APG: padrao Dialog (Modal)"


async def dialog(s: Any, target: str | None, container: str | None = None, max_stops: int = 40) -> dict[str, Any]:
    from .session import SessionError

    page = s._need()
    _loc, (trig_ident, trig) = await _focus_target(s, str(target))
    checks = [_check("gatilho_recebe_foco", "o gatilho recebe o foco do teclado", _where(trig), trig is not None, ["2.1.1"])]
    sel = container[4:] if container and container.startswith("css:") else container
    await _key(s, "Enter")
    try:
        info = await page.evaluate(js.PROBE_DIALOG_JS, sel or None)
    except Exception as e:
        raise SessionError(f"container invalido: {str(e)[:100]}") from e
    if not info.get("found"):
        checks.append(_check("abre_com_teclado", "Enter no gatilho abre um dialogo visivel", "nenhum dialogo (papel dialog/alertdialog ou <dialog open>) visivel depois do Enter", False, ["2.1.1"]))
        return _report("dialog", target, checks, {"dialog": info}, APG_DIALOG)
    checks.append(_check("abre_com_teclado", "Enter no gatilho abre um dialogo visivel", f"abriu <{info['tag']}> role={info['role_attr']}", True, ["2.1.1"]))
    dlg = page.locator("[data-a11y-probe-dialog]").first
    checks.append(_check("foco_vai_para_dentro", "o foco entra no dialogo ao abrir", "dentro" if info["focus_inside"] else "continua fora do dialogo", bool(info["focus_inside"]), ["2.4.3"]))
    head = s.parse_snapshot_head(str(await dlg.aria_snapshot())) or {}
    name = head.get("name") or info.get("label") or ""
    checks.append(_check("tem_nome_acessivel", "o dialogo tem nome (aria-label ou aria-labelledby)", repr(name) if name else "sem nome acessivel", bool(name), ["4.1.2"]))
    declared = info.get("aria_modal") == "true" or info.get("native_modal") is True
    checks.append(_check("declara_modal", "aria-modal=true ou <dialog> aberto com showModal()", f"aria-modal={info.get('aria_modal')} :modal={info.get('native_modal')}", declared, ["4.1.2", "1.3.2"]))
    start_ident, _ = await _ident(s)
    left_at = None
    cycled = 0
    seen_idents: set[Any] = set()
    for i in range(1, int(max_stops) + 1) if int(max_stops) > 0 else itertools.count(1):
        if s.stop_requested:
            break
        await _key(s, "Tab", settle=False)
        where = await dlg.evaluate(
            "(d) => { let a = document.activeElement; while (a && a.shadowRoot && a.shadowRoot.activeElement) a = a.shadowRoot.activeElement;"
            " if (!a || a === document.body || a === document.documentElement) return 'none'; return d.contains(a) ? 'inside' : 'outside'; }"
        )
        if where == "outside":
            left_at = i
            break
        if where == "none":  # o foco foi para a interface do navegador (permitido num modal); o proximo Tab volta
            continue
        ident, _f = await _ident(s)
        if ident == start_ident:
            cycled = i
            break
        if ident in seen_idents:  # o foco voltou a um elemento ja visitado sem passar pelo inicio: nao ha mais o que descobrir
            break
        seen_idents.add(ident)
    checks.append(_check(
        "tab_fica_dentro", "Tab circula so entre os controles do dialogo (o foco nao vaza para a pagina)",
        f"o foco saiu do dialogo no {left_at}o Tab" if left_at else (f"circulou dentro e voltou ao inicio em {cycled} Tab" if cycled else "sem volta completa ao elemento inicial"),
        (left_at is None) if (left_at or cycled) else None, ["2.4.3", "2.1.2"],
    ))
    if left_at:  # devolve o foco para dentro para testar o Escape isoladamente
        await dlg.evaluate("(d) => { const f = d.querySelector('button,[href],input,select,textarea,[tabindex]:not([tabindex=\"-1\"])'); if (f) f.focus(); }")
    await _key(s, "Escape")
    closed = not await dlg.is_visible()
    checks.append(_check("escape_fecha", "Escape fecha o dialogo", "fechou" if closed else "continua aberto", closed, ["2.1.1"]))
    after_ident, after = await _ident(s)
    if closed:
        checks.append(_check("foco_volta_ao_gatilho", "ao fechar, o foco volta ao elemento que abriu o dialogo", _where(after), after_ident == trig_ident, ["2.4.3"]))
    else:
        checks.append(_check("foco_volta_ao_gatilho", "ao fechar, o foco volta ao elemento que abriu o dialogo", "nao testavel: o dialogo nao fechou com Escape", None, ["2.4.3"]))
    await page.evaluate("() => document.querySelectorAll('[data-a11y-probe-dialog]').forEach((e) => e.removeAttribute('data-a11y-probe-dialog'))")
    return _report("dialog", target, checks, {"dialog": info, "left_dialog_at_tab": left_at}, APG_DIALOG)


def _changed(a: dict[str, Any], b: dict[str, Any]) -> bool:
    keys = ("expanded", "controls_visible", "pressed", "checked", "selected")
    return any(a.get(k) != b.get(k) for k in keys)


async def disclosure(s: Any, target: str | None, container: str | None = None, max_stops: int = 0) -> dict[str, Any]:
    """Botao que mostra/oculta conteudo (acordeao, FAQ, submenu de navegacao): APG Disclosure e Accordion."""
    loc, (trig_ident, _t) = await _focus_target(s, str(target))
    f0 = await loc.evaluate(js.PROBE_EL_JS)
    checks = [_check("expoe_estado", "aria-expanded (true/false) no botao", f"aria-expanded={f0['expanded']}", f0["expanded"] in ("true", "false"), ["4.1.2"])]
    for key, label in (("Enter", "enter_alterna"), ("Space", "espaco_alterna")):
        before = await loc.evaluate(js.PROBE_EL_JS)
        await _key(s, key)
        after = await loc.evaluate(js.PROBE_EL_JS)
        changed = _changed(before, after)
        ident, f = await _ident(s)
        checks.append(_check(label, f"{key} alterna o estado do botao e o conteudo controlado", f"expanded {before['expanded']}->{after['expanded']}; conteudo visivel {before['controls_visible']}->{after['controls_visible']}", changed, ["2.1.1"]))
        checks.append(_check(f"foco_fica_no_botao_apos_{key.lower()}", "o foco continua no botao", _where(f), ident == trig_ident, ["2.4.3"]))
        if changed:
            await _key(s, key)  # volta ao estado original
        if label == "enter_alterna" and after["controls_present"] and after["expanded"] in ("true", "false"):
            follows = (after["expanded"] == "true") == bool(after["controls_visible"])
            checks.append(_check("conteudo_acompanha_o_estado", "expanded=true mostra o conteudo; false o oculta", f"expanded={after['expanded']} conteudo_visivel={after['controls_visible']}", follows if changed else None, ["4.1.2"]))
    return _report("disclosure", target, checks, {"initial": f0}, "WAI-ARIA APG: padroes Disclosure e Accordion")


async def menu(s: Any, target: str | None, container: str | None = None, max_stops: int = 0) -> dict[str, Any]:
    """Botao que abre um menu de comandos (role=menu): APG Menu Button. Para navegacao com submenu use `disclosure`."""
    loc, (trig_ident, _t) = await _focus_target(s, str(target))
    f0 = await loc.evaluate(js.PROBE_EL_JS)
    checks = [_check("expoe_estado", "aria-haspopup e aria-expanded no botao", f"haspopup={f0['haspopup']} expanded={f0['expanded']}", f0["haspopup"] is not None and f0["expanded"] in ("true", "false"), ["4.1.2"])]
    opened_with = None
    first_ident = None
    for key in ("Enter", "Space", "ArrowDown"):
        await _key(s, key)
        f1 = await loc.evaluate(js.PROBE_EL_JS)
        ident, foc = await _ident(s)
        if f1["expanded"] == "true" or f1["controls_visible"] or (ident is not None and ident != trig_ident):
            opened_with, first_ident = key, ident
            break
    checks.append(_check("abre_com_teclado", "Enter, Espaco ou Seta para baixo abrem o menu", f"abriu com {opened_with}" if opened_with else "nenhuma das teclas abriu o menu", opened_with is not None, ["2.1.1"]))
    if not opened_with:
        return _report("menu", target, checks, {"initial": f0}, "WAI-ARIA APG: padrao Menu Button")
    moved = first_ident is not None and first_ident != trig_ident
    checks.append(_check("foco_vai_para_um_item", "o foco vai para um item do menu ao abrir", _where(foc), moved, ["2.4.3"]))
    if moved:
        await _key(s, "ArrowDown", settle=False)
        second, _f2 = await _ident(s)
        checks.append(_check("seta_baixo_anda", "Seta para baixo move o foco para o proximo item", "moveu" if second != first_ident else "o foco nao mudou", second != first_ident, ["2.1.1"]))
        await _key(s, "End", settle=False)
        last, _f3 = await _ident(s)
        await _key(s, "Home", settle=False)
        home, _f4 = await _ident(s)
        checks.append(_check("home_vai_ao_primeiro", "Home leva ao primeiro item e End ao ultimo", "Home voltou ao primeiro item" if home == first_ident else "Home nao voltou ao primeiro item", home == first_ident and last != home, ["2.1.1"]))
    await _key(s, "Escape")
    f2 = await loc.evaluate(js.PROBE_EL_JS)
    ident2, f_after = await _ident(s)
    closed = f2["expanded"] != "true" and not f2["controls_visible"]
    checks.append(_check("escape_fecha", "Escape fecha o menu", "fechou" if closed else "continua aberto", closed, ["2.1.1"]))
    checks.append(_check("foco_volta_ao_botao", "ao fechar, o foco volta ao botao do menu", _where(f_after), ident2 == trig_ident if closed else None, ["2.4.3"]))
    return _report("menu", target, checks, {"opened_with": opened_with}, "WAI-ARIA APG: padrao Menu Button")


async def tabs(s: Any, target: str | None, container: str | None = None, max_stops: int = 0) -> dict[str, Any]:
    """Abas (role=tablist): APG Tabs. O alvo e' qualquer uma das abas."""
    loc, (_ti, _t) = await _focus_target(s, str(target))
    info = await loc.evaluate(js.PROBE_TABS_JS)
    tabs_ = info["tabs"]
    checks = [_check("tem_tablist", "as abas ficam dentro de um elemento com role=tablist", "sim" if info["tablist"] else "nao ha role=tablist ao redor", info["tablist"], ["1.3.1", "4.1.2"])]
    if len(tabs_) < 2:
        return _report("tabs", target, checks, {"tabs": tabs_}, "WAI-ARIA APG: padrao Tabs")
    stops = [t for t in tabs_ if t["tabbable"]]
    checks.append(_check("uma_parada_de_tab", "so a aba ativa fica na ordem de Tab (tabindex=0); as outras -1", f"{len(stops)} abas na ordem de Tab de {len(tabs_)}", len(stops) == 1, ["2.4.3"]))
    n = len(tabs_)
    start = next((t["index"] for t in tabs_ if t["focused"]), 0)
    vertical = info.get("orientation") == "vertical"
    nxt = "ArrowDown" if vertical else "ArrowRight"
    await _key(s, nxt)
    after = await loc.evaluate(js.PROBE_TABS_JS)
    idx = next((t["index"] for t in after["tabs"] if t["focused"]), None)
    checks.append(_check("seta_move_o_foco", f"{nxt} move o foco para a proxima aba", f"foco na aba {idx} (era {start})", idx == (start + 1) % n, ["2.1.1"]))
    sel_before = [t["selected"] for t in tabs_]
    sel_after = [t["selected"] for t in after["tabs"]]
    follows = sel_after != sel_before
    checks.append(_check("ativacao", "ativacao automatica (aria-selected acompanha o foco) ou manual (Enter/Espaco): ambas validas no APG", "automatica: a selecao acompanhou o foco" if follows else "manual: a selecao nao mudou so com a seta", None, ["4.1.2"]))
    await _key(s, "End", settle=False)
    end_idx = next((t["index"] for t in (await loc.evaluate(js.PROBE_TABS_JS))["tabs"] if t["focused"]), None)
    await _key(s, "Home", settle=False)
    home_idx = next((t["index"] for t in (await loc.evaluate(js.PROBE_TABS_JS))["tabs"] if t["focused"]), None)
    checks.append(_check("home_e_end", "Home vai a primeira aba e End a ultima", f"Home->{home_idx}, End->{end_idx}", home_idx == 0 and end_idx == n - 1, ["2.1.1"]))
    await loc.evaluate("(el) => { const l = el.closest('[role=tablist]'); const t = l.querySelector('[role=tab][aria-selected=true]') || l.querySelector('[role=tab]'); if (t) t.focus(); }")
    sel = next((t for t in (await loc.evaluate(js.PROBE_TABS_JS))["tabs"] if t["selected"] == "true"), None)
    checks.append(_check("aba_ligada_ao_painel", "a aba selecionada aponta o painel com aria-controls", f"aria-controls={sel['controls'] if sel else None}", bool(sel and sel["controls"]), ["1.3.1", "4.1.2"]))
    if sel and sel["controls"]:
        await _key(s, "Tab")
        inside = await s.page.evaluate("(id) => { const p = document.getElementById(id); let a = document.activeElement; while (a && a.shadowRoot && a.shadowRoot.activeElement) a = a.shadowRoot.activeElement; return !!p && p.contains(a); }", sel["controls"])
        checks.append(_check("tab_entra_no_painel", "Tab a partir da aba selecionada leva o foco para o painel", "o foco entrou no painel" if inside else "o foco nao entrou no painel", inside, ["2.4.3"]))
    return _report("tabs", target, checks, {"tabs": tabs_, "orientation": info.get("orientation")}, "WAI-ARIA APG: padrao Tabs")


async def combobox(s: Any, target: str | None, container: str | None = None, max_stops: int = 0) -> dict[str, Any]:
    """Campo com lista de sugestoes/opcoes: APG Combobox. Teclas: Seta para baixo, Enter, Escape."""
    loc, (_ti, _t) = await _focus_target(s, str(target))
    f0 = await loc.evaluate(js.PROBE_EL_JS)
    head = s.parse_snapshot_head(str(await loc.aria_snapshot())) or {}
    native = bool(f0["native_popup"])
    checks = [
        _check("papel_combobox", "o navegador expoe o campo como combobox", f"papel calculado: {head.get('role')}", head.get("role") == "combobox", ["4.1.2"]),
        _check("expoe_estado", "aria-expanded no campo", f"aria-expanded={f0['expanded']}", None if native else f0["expanded"] in ("true", "false"), ["4.1.2"]),
    ]
    if native:
        checks.append(_check("abre_a_lista", "Seta para baixo abre a lista", "popup nativo do navegador (datalist/select): nao e observavel no DOM", None, ["2.1.1"]))
        return _report("combobox", target, checks, {"initial": f0}, "WAI-ARIA APG: padrao Combobox")
    await _key(s, "ArrowDown")
    f1 = await loc.evaluate(js.PROBE_EL_JS)
    ident1, _x = await _ident(s)
    opened = f1["expanded"] == "true" or bool(f1["controls_visible"])
    checks.append(_check("abre_com_seta", "Seta para baixo abre a lista de opcoes", f"expanded={f1['expanded']} lista_visivel={f1['controls_visible']}", opened, ["2.1.1"]))
    if opened:
        await _key(s, "ArrowDown")
        f2 = await loc.evaluate(js.PROBE_EL_JS)
        ident2, _y = await _ident(s)
        moved = (f2["activedescendant"] != f1["activedescendant"]) or ident2 != ident1
        exposes = bool(f2["activedescendant_attr"]) or ident2 != ident1
        checks.append(_check("opcao_ativa_exposta", "a opcao ativa e' exposta (aria-activedescendant) ou recebe o foco", f"activedescendant={f2['activedescendant']!r}", exposes, ["4.1.2"]))
        checks.append(_check("setas_andam", "Seta para baixo move a opcao ativa", "mudou" if moved else "a opcao ativa nao mudou", moved, ["2.1.1"]))
        await _key(s, "Enter")
        f3 = await loc.evaluate(js.PROBE_EL_JS)
        picked = f3["value"] != f0["value"] or f3["expanded"] != "true"
        checks.append(_check("enter_escolhe", "Enter escolhe a opcao ativa e fecha a lista", f"valor {f0['value']!r}->{f3['value']!r}; expanded={f3['expanded']}", picked, ["2.1.1"]))
        await _key(s, "ArrowDown")
        await _key(s, "Escape")
        f4 = await loc.evaluate(js.PROBE_EL_JS)
        closed = f4["expanded"] != "true" and not f4["controls_visible"]
        checks.append(_check("escape_fecha_e_mantem_foco", "Escape fecha a lista e o foco continua no campo", f"fechou={closed}; foco no campo={f4['focused']}", closed and bool(f4["focused"]), ["2.1.1", "2.4.3"]))
    return _report("combobox", target, checks, {"initial": f0, "side_effect": "a escolha com Enter pode ter alterado o valor do campo"}, "WAI-ARIA APG: padrao Combobox")


# ------------------------------------------------------------------------------------------------ formularios e rotas
async def form_errors(s: Any, target: str | None, container: str | None = None, max_stops: int = 0) -> dict[str, Any]:
    """Tenta enviar o formulario do alvo (botao de envio ou campo) so com o teclado e mede o que a pessoa recebe: erro por campo, foco, anuncio."""
    page = s._need()
    loc, (_ti, _t) = await _focus_target(s, str(target))
    before = await loc.evaluate(js.PROBE_FORM_JS)
    if not before.get("form"):
        return {"probe": "form_errors", "summary": "o alvo nao esta dentro de um <form>", "facts": before, "checks": [], "unmet": []}
    await s._live_new()
    tree0 = await s._tree_lines()
    url0 = page.url
    await _key(s, "Enter")
    after: dict[str, Any] = await loc.evaluate(js.PROBE_FORM_JS) if await loc.count() else {"form": False}
    live = await s._live_new()
    from .session import tree_diff

    added = tree_diff(tree0, await s._tree_lines())["added"]
    _ident_after, f = await _ident(s)
    fields: list[dict[str, Any]] = after.get("fields", []) if after.get("form") else []
    invalid = [x for x in fields if not x["valid"] or x["aria_invalid"] == "true"]
    checks: list[dict[str, Any]] = []
    if page.url != url0 or not after.get("form"):
        return {"probe": "form_errors", "summary": "o envio navegou para outra pagina ou o formulario sumiu: nao ha erros para medir (campos validos ou envio aceito)",
                "facts": {"url_before": url0, "url_after": page.url}, "checks": [], "unmet": []}
    if invalid:
        checks.append(_check("campo_invalido_marcado", "cada campo com erro tem aria-invalid=true", f"{sum(1 for x in invalid if x['aria_invalid'] == 'true')} de {len(invalid)} marcados", all(x["aria_invalid"] == "true" for x in invalid), ["3.3.1", "4.1.2"]))
        checks.append(_check("erro_descrito_no_campo", "o texto do erro esta ligado ao campo (aria-describedby)", f"{sum(1 for x in invalid if x['described_by'])} de {len(invalid)} com descricao", all(bool(x["described_by"]) for x in invalid), ["3.3.1", "1.3.1"]))
        on_invalid = any(x["focused"] for x in invalid)
        checks.append(_check("foco_vai_ao_erro", "o foco vai ao primeiro campo com erro (ou a um resumo de erros)", _where(f), on_invalid or (f is not None and f.get("role") in ("alert", "alertdialog")), ["3.3.1", "2.4.3"]))
        announced = bool(live) or bool(after.get("live_text"))
        checks.append(_check("erro_anunciado", "o erro e' anunciado (regiao viva, role=alert) ou recebe o foco", f"anuncios={[a['text'][:40] for a in live][:3]} regioes={after.get('live_text')}", announced or on_invalid, ["3.3.1", "4.1.3"]))
    else:
        checks.append(_check("envio_sem_campo_invalido", "ha campos invalidos para a sonda medir", "todos os campos ja eram validos (preencha algo invalido ou deixe um obrigatorio vazio)", None, ["3.3.1"]))
    return _report("form_errors", target, checks, {"invalid_fields": invalid[:10], "tree_added": added[:8], "novalidate": after.get("novalidate")}, "WCAG 3.3.1/3.3.3 e WAI-ARIA (aria-invalid, aria-describedby)")


async def route_change(s: Any, target: str | None, container: str | None = None, max_stops: int = 0) -> dict[str, Any]:
    """Ativa um link/botao de navegacao com o teclado e mede o que a pessoa recebe numa troca de tela: titulo, foco, anuncio (SPA ou pagina nova)."""
    page = s._need()
    _loc, (ident0, f0) = await _focus_target(s, str(target))
    await page.evaluate("() => { window.__a11yRouteMarker = true; }")
    state = "() => ({title: document.title, h1: ((document.querySelector('h1') || {}).innerText || '').trim().slice(0, 80)})"
    before = await page.evaluate(state)
    url0 = page.url
    await s._live_new()
    await _key(s, "Enter")
    after = await page.evaluate(state)
    ident1, f1 = await _ident(s)
    live = await s._live_new()
    spa = bool(await page.evaluate("() => window.__a11yRouteMarker === true"))
    moved_url = page.url != url0
    # Salto para ancora na mesma pagina (link de pular, indice): so o fragmento da URL mudou e o h1 e' o mesmo. E' fato de URL, nao de intencao.
    jump = moved_url and before["h1"] == after["h1"] and urldefrag(url0)[0] == urldefrag(page.url)[0]
    facts = {"url": [url0, page.url], "title": [before["title"], after["title"]], "h1": [before["h1"], after["h1"]], "focus_before": _where(f0), "focus_after": _where(f1),
             "announced": [a["text"][:60] for a in live][:3], "same_document_navigation": spa, "fragment_jump": jump}
    checks: list[dict[str, Any]] = []
    if moved_url or before["h1"] != after["h1"]:
        if jump:
            checks.append(_check("titulo_muda", "o titulo da pagina muda com a nova tela", "salto para ancora na mesma pagina (so o fragmento da URL mudou e o h1 e' o mesmo): o titulo nao deve mudar", None, ["2.4.2"]))
        else:
            checks.append(_check("titulo_muda", "o titulo da pagina muda com a nova tela", f"{before['title']!r} -> {after['title']!r}", before["title"] != after["title"], ["2.4.2"]))
        checks.append(_check("foco_nao_se_perde", "o foco nao fica perdido no corpo da pagina", _where(f1), f1 is not None, ["2.4.3"]))
        checks.append(_check("troca_perceptivel", "a troca e' perceptivel sem ver a tela: anuncio, foco movido para o novo conteudo ou carga de pagina nova", f"anuncio={bool(live)}; foco mudou={ident1 != ident0}; mesmo documento={spa}", (not spa) or bool(live) or (f1 is not None and ident1 != ident0), ["4.1.3", "2.4.3"]))
    else:
        checks.append(_check("houve_troca", "ativar o alvo troca de tela", "nem a URL nem o titulo do h1 mudaram", None, ["2.4.2"]))
    return _report("route_change", target, checks, facts, "WCAG 2.4.2, 2.4.3 e 4.1.3 (troca de tela em SPA)")


ProbeFn = Callable[..., Awaitable[dict[str, Any]]]

# kind -> (funcao, precisa de alvo, o que mede)
PROBES: dict[str, tuple[ProbeFn, bool, str]] = {
    "tab_walk": (tab_walk, False, "Tab do inicio ao fim: paradas, armadilha de teclado, foco coberto (2.1.2, 2.4.3, 2.4.11)"),
    "focus_obscured": (focus_obscured, False, "paradas de Tab em que o foco fica coberto por cabecalho fixo, banner... (2.4.11)"),
    "target_size": (target_size, False, "alvos menores que 24x24 px e a excecao de espacamento (2.5.8)"),
    "dialog": (dialog, True, "contrato APG de dialogo modal a partir do botao que o abre (alvo = gatilho)"),
    "disclosure": (disclosure, True, "contrato APG de botao que mostra/oculta (acordeao, FAQ, submenu de navegacao) (alvo = botao)"),
    "menu": (menu, True, "contrato APG de menu de comandos aberto por botao (alvo = botao)"),
    "tabs": (tabs, True, "contrato APG de abas (alvo = uma das abas)"),
    "combobox": (combobox, True, "contrato APG de combobox (alvo = o campo)"),
    "form_errors": (form_errors, True, "envia o formulario pelo teclado e mede erro por campo, foco e anuncio (alvo = botao de envio ou campo)"),
    "route_change": (route_change, True, "ativa um link/botao e mede titulo, foco e anuncio da nova tela (alvo = o link)"),
}


async def run_probe(session: Any, kind: str, target: str | None = None, container: str | None = None, max_stops: int = 0) -> dict[str, Any]:
    from .session import SessionError

    if kind not in PROBES:
        raise SessionError(f"sonda invalida: {kind}. Opcoes: {', '.join(PROBES)}")
    fn, needs_target, _about = PROBES[kind]
    if needs_target and not target:
        raise SessionError(f"a sonda '{kind}' precisa de target (id do dossie ou css:<seletor>)")
    session._need()
    result = await fn(session, target, container, max_stops)
    session.coverage.actions += 1
    session.coverage.probes.add(kind)
    session.log_trace("probe:" + kind, target, None, {"summary": result.get("summary"), "unmet": result.get("unmet"), "checks": [
        {"check": c["check"], "observed": c["observed"], "met": c["met"]} for c in result.get("checks", [])][:12]})
    return result


__all__ = ["PROBES", "run_probe"]
