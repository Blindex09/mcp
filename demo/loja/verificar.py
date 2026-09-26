"""Verifica as 3 versoes do site de demonstracao com as MESMAS medicoes do MCP.

Duas camadas separadas, como pedido:
  1. GENERICA  - regras automaticas (axe-core): o que uma ferramenta de scan acha.
  2. JULGAMENTO - o que so aparece agindo como usuario: tarefas so de teclado (persona imposta pelo servidor,
     sem mouse), anuncio de leitor de tela, foco visivel, reflow, espacamento de texto e a linguagem de design.

Uso:  python demo/loja/verificar.py          (imprime o quadro de resultados)
"""

from __future__ import annotations

import asyncio
import functools
import http.server
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent.parent))

from a11y import audit
from a11y.session import SESSION

VERSIONS = ["v1-original", "v2-axe-verde", "v3-corrigido"]
OPTIONS = {"Chá verde", "Chá preto", "Chá branco", "Chá de ervas", "Chá mate"}


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args, **kwargs) -> None:
        return


def serve() -> tuple[http.server.ThreadingHTTPServer, int]:
    handler = functools.partial(QuietHandler, directory=str(ROOT))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


async def focused(page) -> dict:
    return await page.evaluate("""() => { const e = document.activeElement; if (!e || e === document.body) return null;
      return {tag: e.tagName.toLowerCase(), text: (e.innerText || e.value || '').trim().slice(0, 40), role: e.getAttribute('role'),
              expanded: e.getAttribute('aria-expanded'), cls: e.className || ''}; }""")


async def tab_until(match, limit: int = 40, from_top: bool = True) -> tuple[bool, int]:
    """Aperta Tab (como um usuario de teclado) ate o foco satisfazer `match`; from_top=False continua de onde o foco esta."""
    if from_top:
        await SESSION.page.evaluate("() => { const b = document.body; b.setAttribute('tabindex','-1'); b.focus(); b.removeAttribute('tabindex'); }")
    for i in range(1, limit + 1):
        await SESSION.act("press", "", "Tab")
        f = await focused(SESSION.page)
        if f and match(f):
            return True, i
        if f is None:
            return False, i
    return False, limit


async def keyboard_tasks(base: str) -> dict:
    out: dict = {}
    await SESSION.open(base, None, "keyboard")  # persona de teclado: o servidor RECUSA mouse
    try:
        # T1: escolher uma categoria so com o teclado
        # o campo de categoria e o 1o input; digita "ch" e tenta escolher com setas + Enter
        reached, n = await tab_until(lambda f: f["tag"] == "input")
        if reached:
            await SESSION.act("type", "", "ch")
            await SESSION.act("press", "", "ArrowDown")
            await SESSION.act("press", "", "Enter")
            value = await SESSION.page.evaluate("() => document.getElementById('cat').value")
            out["T1 escolher categoria (teclado)"] = (value in OPTIONS, f"{n} Tab; valor final: {value!r}")
        else:
            out["T1 escolher categoria (teclado)"] = (False, "campo inalcançável")
    finally:
        await SESSION.close()

    async def task(label, opener):
        await SESSION.open(base, None, "keyboard")
        try:
            out[label] = await opener()
        finally:
            await SESSION.close()

    async def t2():
        ok, n = await tab_until(lambda f: "Produtos" in f["text"])
        if not ok:
            return (False, "o item 'Produtos' nao recebe foco: menu inalcançável pelo teclado")
        await SESSION.act("press", "", "Enter")
        ok2, _ = await tab_until(lambda f: f["text"] == "Chás", 5, from_top=False)
        return (ok2, f"{n} Tab até 'Produtos'; Enter abre; 'Chás' recebe foco: {ok2}")

    async def t3():
        ok, n = await tab_until(lambda f: "prazo" in f["text"])
        if not ok:
            return (False, "a pergunta do FAQ não recebe foco")
        await SESSION.act("press", "", "Enter")
        shown = await SESSION.page.evaluate("() => { const a = document.querySelector('.faq-a'); return !!a && a.offsetParent !== null; }")
        return (bool(shown), f"{n} Tab; Enter; resposta visível: {shown}")

    async def t4():
        ok, n = await tab_until(lambda f: f["text"].startswith("Comprar"))
        if not ok:
            return (False, "o botão 'Comprar' não recebe foco (é um <div>)")
        await SESSION.act("press", "", "Enter")
        msg = await SESSION.page.evaluate("() => document.getElementById('toast').textContent")
        return (bool(msg), f"{n} Tab; Enter; aviso: {msg!r}")

    await task("T2 abrir o menu Produtos (teclado)", t2)
    await task("T3 abrir a 1ª pergunta do FAQ (teclado)", t3)
    await task("T4 comprar o 1º chá (teclado)", t4)
    return out


async def other_facts(base: str) -> dict:
    out: dict = {}
    await SESSION.open(base, None, "default")
    try:
        d = await SESSION.dossier("", 100)
        els = d["elements"]
        mouse_only = [e for e in els if e["clickable"] and not e["focusable"] and (e["computed"] or {}).get("role") in ("generic", None)]
        cat = next((e for e in els if e["tag"] == "input" and (e["computed"] or {}).get("name") == "Categoria"), None)
        out["dossie: controles só de mouse"] = (len(mouse_only) == 0, f"{len(mouse_only)} elemento(s) clicável(is), sem foco e sem papel")
        out["dossie: papel do campo Categoria"] = (
            bool(cat and cat["computed"]["role"] == "combobox"), f"papel calculado pelo navegador: {cat['computed']['role'] if cat else '?'}"
        )
        # T5: o aviso de compra e' anunciado?
        target = next((e for e in els if e["text"] and e["text"].startswith("Comprar")), None)
        if target:
            r = await SESSION.act("click", target["id"])
            out["T5 aviso de compra anunciado"] = (bool(r["announcements"]), f"anunciado: {[a['text'] for a in r['announcements']][:1] or 'nada (silencioso)'}")
        # T6: foco visivel
        first = next((e for e in els if e["focusable"] and e["tag"] in ("a", "button")), None)
        cart = next((e for e in els if e["tag"] == "button" and not (e["text"] or "").strip()), first)
        if cart:
            fs = await SESSION.focus_style(cart["id"])
            visible = "none" not in fs["outline_when_focused"].split()[0:1] and not fs["outline_when_focused"].startswith("none")
            out["T6 foco visível (botão do carrinho)"] = (visible, f"outline ao focar: {fs['outline_when_focused'].strip()}")
        st = await SESSION.stress("reflow_320")
        out["T7 reflow em 320px"] = (not st["horizontal_scroll"], f"rolagem horizontal: {st['horizontal_scroll']}; {st['overflowing_total']} elemento(s) passam da tela")
        ts = await SESSION.stress("text_spacing")
        out["T8 texto cortado com espaçamento do usuário"] = (len(ts["newly_clipped_with_user_spacing"]) == 0, f"{len(ts['newly_clipped_with_user_spacing'])} novo(s)")
        tk = await SESSION.design_tokens()
        base_size = float(tk["base"]["body_size"].replace("px", ""))
        lh = tk["base"]["body_line_height"]
        ratio = round(float(lh.replace("px", "")) / base_size, 2) if lh.endswith("px") else lh
        out["design: corpo do texto"] = (base_size >= 16 and (isinstance(ratio, float) and ratio >= 1.5), f"{base_size:g}px, entrelinha {ratio}")
        fam = [f["value"] for f in tk["font_families"]]
        out["design: famílias de fonte"] = (len(fam) <= 2, f"{len(fam)}: {', '.join(fam)}")
        out["design: tamanhos de fonte distintos"] = (len(tk["font_sizes"]) <= 6, f"{len(tk['font_sizes'])}: {', '.join(x['value'] for x in tk['font_sizes'][:8])}")
        out["design: valores de espaçamento distintos"] = (len(tk["spacing_values"]) <= 8, f"{len(tk['spacing_values'])} (escala de 8px?)")
    finally:
        await SESSION.close()
    return out


async def main() -> None:
    srv, port = serve()
    results: dict = {}
    for v in VERSIONS:
        base = f"http://127.0.0.1:{port}/{v}/index.html"
        axe = await audit.run_axe(url=base, level="AA")
        entry = {"axe": (len(axe["violations"]) == 0, f"{len(axe['violations'])} violação(ões): {', '.join(x['id'] for x in axe['violations']) or '-'}")}
        entry.update(await keyboard_tasks(base))
        entry.update(await other_facts(base))
        results[v] = entry
    srv.shutdown()

    labels = list(next(iter(results.values())))
    print(f"{'VERIFICAÇÃO':<50}" + "".join(f"{v:<16}" for v in VERSIONS))
    for lab in labels:
        row = f"{('CAMADA GENÉRICA  ' if lab == 'axe' else '') + lab if lab == 'axe' else lab:<50}"
        for v in VERSIONS:
            ok, _ = results[v].get(lab, (None, ""))
            row += f"{'passa' if ok else 'FALHA':<16}"
        print(row)
    print()
    for v in VERSIONS:
        print(f"--- {v}")
        for lab in labels:
            ok, detail = results[v].get(lab, (None, ""))
            print(f"  [{'ok' if ok else '!!'}] {lab}: {detail}")


if __name__ == "__main__":
    asyncio.run(main())
