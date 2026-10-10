"""Bancada de avaliacao: mede o quanto as ferramentas (e o agente) realmente acham, em vez de supor.

Parte de uma pagina CORRETA (`evals/boa.html`) e injeta UM defeito conhecido por vez (mutacao, como o Ma11y propoe), cada um com o
gabarito do criterio WCAG que ele viola. Dois modos:

- `facts` (sem modelo, determinista): o defeito aparece nos FATOS das ferramentas? Compara o axe sozinho com o conjunto (axe + mapa da
  pagina + dossie + sondas de comportamento) e confere que a pagina boa NAO dispara alarme. Roda na integracao continua.
- `agent` (precisa de um modelo configurado): o agente autonomo acha o defeito e o escreve como achado verificado? Mede recall e falso
  positivo (achados `failed` na pagina boa) por modelo, para saber se uma mudanca de prompt ou de modelo melhorou de verdade.

O gabarito e' MEU (de quem escreveu a mutacao): a bancada mede contra defeitos plantados, nao contra todos os defeitos possiveis de um site real.
Uso: `python -m a11y.bench facts` | `python -m a11y.bench agent [--persona keyboard] [--only sem_alt,sem_lang] [--json saida.json]`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import audit, wcag
from .session import SESSION, Session

BASE_PATH = Path(__file__).parent.parent / "evals" / "boa.html"
Detector = Callable[[Session], Awaitable[bool]]


def base_html() -> str:
    return BASE_PATH.read_text(encoding="utf-8")


def _swap(*pairs: tuple[str, str]) -> Callable[[str], str]:
    def apply(html: str) -> str:
        for old, new in pairs:
            if old not in html:
                raise ValueError(f"a mutacao nao encontrou o trecho esperado na pagina boa: {old[:60]!r}")
            html = html.replace(old, new, 1)
        return html

    return apply


async def _page_map(s: Session) -> dict[str, Any]:
    return (await s.page_map())["main"]


async def _by_text(s: Session, text: str) -> dict[str, Any] | None:
    for e in (await s.dossier("", 200))["elements"]:
        if ((e.get("computed") or {}).get("name") or e.get("text")) == text:
            return e
    return None


async def _d_alt(s: Session) -> bool:
    return any(i["tag"] == "img" and i["alt"] is None for i in (await _page_map(s))["images"]["items"])


async def _d_label(s: Session) -> bool:
    return (await _page_map(s))["forms"]["fields_without_any_name"] > 0


async def _d_unnamed_button(s: Session) -> bool:
    return any(e["tag"] == "button" and not (e.get("computed") or {}).get("name") for e in (await s.dossier("", 200))["elements"])


async def _d_div_button(s: Session) -> bool:
    e = await _by_text(s, "Comprar cha verde")
    return bool(e and not e["focusable"] and e["clickable"])


async def _d_lang(s: Session) -> bool:
    return (await _page_map(s))["document"]["lang"] is None


async def _d_title(s: Session) -> bool:
    return not (await _page_map(s))["document"]["title"]


async def _d_heading_jump(s: Session) -> bool:
    return bool((await _page_map(s))["headings"]["level_jumps"])


async def _d_small_targets(s: Session) -> bool:
    from .probes import run_probe

    return bool((await run_probe(s, "target_size"))["fail_spacing_exception"])


async def _d_trap(s: Session) -> bool:
    from .probes import run_probe

    return bool((await run_probe(s, "tab_walk"))["stuck_at"])


async def _d_dialog(s: Session) -> bool:
    from .probes import run_probe

    return "tab_fica_dentro" in (await run_probe(s, "dialog", "css:#abrir"))["unmet"]


async def _d_no_state(s: Session) -> bool:
    from .probes import run_probe

    return "expoe_estado" in (await run_probe(s, "disclosure", "css:#faq"))["unmet"]


async def _d_silent_status(s: Session) -> bool:
    e = await _by_text(s, "Comprar cha verde")
    if e is None:
        return False
    r = await s.act("click", e["id"])
    return not r["announcements"] and any("Adicionado" in x for x in r["tree_added"])


@dataclass(frozen=True)
class Mutation:
    name: str
    criteria: frozenset[str]  # criterios WCAG que o defeito viola (gabarito)
    hints: tuple[str, ...]  # palavras que um achado correto costuma citar (so para a pontuacao estrita do agente)
    apply: Callable[[str], str]
    detect: Detector | None  # fato das ferramentas que revela o defeito (None: so o axe cobre)
    about: str


MUTATIONS: tuple[Mutation, ...] = (
    Mutation("sem_alt", frozenset({"1.1.1"}), ("logo", "imagem", "alt"), _swap((' alt="Logo da Casa do Cha"', "")), _d_alt, "imagem sem texto alternativo"),
    Mutation("sem_rotulo", frozenset({"1.3.1", "3.3.2", "4.1.2"}), ("busca", "campo", "rotulo", "label"), _swap(('<label for="busca">Buscar cha</label>', "")), _d_label, "campo sem rotulo"),
    Mutation("botao_sem_nome", frozenset({"4.1.2"}), ("carrinho", "sem nome", "botao"), _swap((' aria-label="Abrir carrinho"', "")), _d_unnamed_button, "botao de icone sem nome acessivel"),
    Mutation("div_vira_botao", frozenset({"2.1.1", "4.1.2"}), ("comprar", "teclado", "div"), _swap((
        '<button id="comprar" type="button">Comprar cha verde</button>',
        '<div id="comprar" style="display:inline-block;padding:12px;background:#286;color:#fff;cursor:pointer">Comprar cha verde</div>',
    )), _d_div_button, "controle que so funciona com mouse (div clicavel)"),
    Mutation("sem_lang", frozenset({"3.1.1"}), ("idioma", "lang"), _swap(('<html lang="pt-BR">', "<html>")), _d_lang, "pagina sem idioma"),
    Mutation("contraste_baixo", frozenset({"1.4.3"}), ("contraste", "cinza", "cor"), _swap((".muted { color: #555; }", ".muted { color: #bbb; }")), None, "texto com contraste insuficiente"),
    Mutation("titulo_pulado", frozenset({"1.3.1"}), ("titulo", "heading", "h4", "nivel"), _swap(("<h2>Produtos</h2>", "<h4>Produtos</h4>")), _d_heading_jump, "salto de nivel de titulo (h1 para h4)"),
    Mutation("alvo_pequeno", frozenset({"2.5.8"}), ("alvo", "pequeno", "carrinho", "tamanho"), _swap(("nav { display: flex;", "#carrinho { min-width: 0; min-height: 0; width: 14px; height: 14px; padding: 0; margin: 0 -16px; }\n nav { display: flex;")), _d_small_targets, "alvo de toque menor que 24 px encostado em outro"),
    Mutation("armadilha_teclado", frozenset({"2.1.2"}), ("armadilha", "tab", "preso", "busca"), _swap(("</script>\n</body>", "document.getElementById('busca').addEventListener('keydown', (e) => { if (e.key === 'Tab') e.preventDefault(); });\n</script>\n</body>")), _d_trap, "campo que prende o foco do teclado"),
    Mutation("dialogo_sem_foco", frozenset({"2.4.3", "4.1.2"}), ("dialogo", "modal", "foco"), _swap(("dlg.showModal()", "dlg.show()")), _d_dialog, "dialogo que nao e modal: o Tab vaza para a pagina"),
    Mutation("sem_estado_expandido", frozenset({"4.1.2"}), ("expandido", "aria-expanded", "entrega", "estado"), _swap(
        (' aria-expanded="false" aria-controls="faq-resp"', ""), ("   faq.setAttribute('aria-expanded', String(!o));\n", ""),
    ), _d_no_state, "botao que abre/fecha sem expor o estado"),
    Mutation("sem_titulo", frozenset({"2.4.2"}), ("titulo da pagina", "title"), _swap(("<title>Casa do Cha - Inicio</title>", "")), _d_title, "pagina sem titulo"),
    Mutation("status_mudo", frozenset({"4.1.3"}), ("status", "anunc", "carrinho", "adicionado"), _swap(('<p id="status" role="status"></p>', '<p id="status"></p>')), _d_silent_status, "mensagem de status que nao e anunciada"),
)


# ----------------------------------------------------------------------------- modo facts (sem modelo)
async def _axe_criteria(html: str) -> set[str]:
    raw = await audit.run_axe(html=html, level="AA")
    return {c for v in raw["violations"] for t in v["wcag_tags"] if (c := wcag.from_axe_tag(t))}


async def _detect(html: str, detector: Detector | None) -> bool | None:
    if detector is None:
        return None
    await SESSION.open(None, html)
    try:
        return await detector(SESSION)
    finally:
        await SESSION.close()


async def run_facts(only: set[str] | None = None) -> dict[str, Any]:
    """Cada defeito plantado aparece nos fatos? O axe sozinho x o conjunto de ferramentas, e a pagina boa nao pode disparar nada."""
    base = base_html()
    base_axe = await _axe_criteria(base)
    rows: list[dict[str, Any]] = []
    for m in MUTATIONS:
        if only and m.name not in only:
            continue
        html = m.apply(base)
        axe_hit = bool(await _axe_criteria(html) & m.criteria)
        facts_hit = await _detect(html, m.detect)
        clean_alarm = bool(await _detect(base, m.detect)) or bool(base_axe & m.criteria)
        rows.append({
            "mutation": m.name, "about": m.about, "criteria": sorted(m.criteria), "axe_detects": axe_hit, "facts_detect": facts_hit,
            "toolset_detects": axe_hit or bool(facts_hit), "false_alarm_on_clean_page": clean_alarm,
        })
    n = len(rows)
    summary = {
        "mutations": n, "axe_alone": sum(r["axe_detects"] for r in rows), "toolset": sum(r["toolset_detects"] for r in rows),
        "only_the_behavior_and_fact_tools_caught": [r["mutation"] for r in rows if r["toolset_detects"] and not r["axe_detects"]],
        "missed_by_everything": [r["mutation"] for r in rows if not r["toolset_detects"]],
        "false_alarms_on_clean_page": [r["mutation"] for r in rows if r["false_alarm_on_clean_page"]],
        "axe_recall": round(sum(r["axe_detects"] for r in rows) / n, 2) if n else None,
        "toolset_recall": round(sum(r["toolset_detects"] for r in rows) / n, 2) if n else None,
    }
    return {
        "summary": summary, "rows": rows,
        "note": "defeitos plantados por quem escreveu a bancada: mede o que as ferramentas acham desses, nao de todos os defeitos de um site real",
    }


# ----------------------------------------------------------------------------- modo agent (com modelo)
def score_findings(findings: list[dict[str, Any]], m: Mutation | None) -> dict[str, Any]:
    """Pontua os achados do agente numa pagina com UM defeito plantado (m) ou na pagina boa (m=None).

    lenient: algum achado `failed` cita um criterio do gabarito. strict: alem disso o texto cita uma das palavras do defeito.
    Qualquer achado `failed` fora do gabarito (ou qualquer um na pagina boa) e' falso positivo."""
    failed = [f for f in findings if f.get("outcome") == "failed"]
    if m is None:
        return {"hit_lenient": None, "hit_strict": None, "false_positives": len(failed), "failed": len(failed), "cantTell": sum(f.get("outcome") == "cantTell" for f in findings)}
    on_target = [f for f in failed if f.get("criterion") in m.criteria]
    strict = [f for f in on_target if any(h in f"{f.get('claim', '')} {(f.get('element') or {}).get('name') or ''}".lower() for h in m.hints)]
    return {
        "hit_lenient": bool(on_target), "hit_strict": bool(strict), "false_positives": len(failed) - len(on_target), "failed": len(failed),
        "cantTell": sum(f.get("outcome") == "cantTell" for f in findings),
    }


async def run_agent_bench(ask: Callable[..., Awaitable[str | None]], persona: str = "keyboard", only: set[str] | None = None, max_steps: int = 30, include_clean: bool = True) -> dict[str, Any]:
    from .agent import run_agent

    base = base_html()
    cases: list[tuple[Mutation | None, str]] = [(m, m.apply(base)) for m in MUTATIONS if not only or m.name in only]
    if include_clean:
        cases.append((None, base))
    rows: list[dict[str, Any]] = []
    for m, html in cases:
        result = await run_agent(
            session=SESSION, ask=ask, mode="review", goal="acessibilidade completa por teclado e leitor de tela: varra a pagina com tab_walk e prove cada componente importante agindo",
            url=None, html=html, persona=persona, max_steps=max_steps, vision=False,
        )
        rows.append({"case": m.name if m else "pagina_boa", "stopped_by": result["stopped_by"], "model_calls": result["facts"]["model_calls"],
                     "rejected_by_verifier": len(result["rejected_findings"]), **score_findings(result["findings"], m)})
    planted = [r for r in rows if r["case"] != "pagina_boa"]
    clean = next((r for r in rows if r["case"] == "pagina_boa"), None)
    n = len(planted)
    return {
        "persona": persona, "rows": rows,
        "summary": {
            "defects": n, "recall_lenient": round(sum(bool(r["hit_lenient"]) for r in planted) / n, 2) if n else None,
            "recall_strict": round(sum(bool(r["hit_strict"]) for r in planted) / n, 2) if n else None,
            "false_positives_planted_pages": sum(r["false_positives"] for r in planted),
            "false_positives_clean_page": clean["false_positives"] if clean else None,
            "refuted_by_verifier": sum(r["rejected_by_verifier"] for r in rows),
        },
    }


def _print(report: dict[str, Any]) -> None:
    print(json.dumps(report["summary"], ensure_ascii=False, indent=1))
    for r in report["rows"]:
        print(" ", {k: v for k, v in r.items() if k not in ("about",)})


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m a11y.bench", description=__doc__.split("\n")[0])
    ap.add_argument("mode", choices=["facts", "agent"])
    ap.add_argument("--persona", default="keyboard")
    ap.add_argument("--only", default="", help="nomes de mutacoes separados por virgula")
    ap.add_argument("--max-steps", type=int, default=30)
    ap.add_argument("--json", default="", help="grava o relatorio neste arquivo")
    args = ap.parse_args(argv)
    only = {x.strip() for x in args.only.split(",") if x.strip()} or None

    async def go() -> dict[str, Any]:
        if args.mode == "facts":
            return await run_facts(only)
        from router import ask_routed

        async def ask(prompt: str, images: list[bytes] | None, max_tokens: int, hint: Any = None, tier: str | None = None) -> str | None:
            return await ask_routed(None, prompt, images=images, max_tokens=max_tokens, hint=hint, tier=tier)

        return await run_agent_bench(ask, args.persona, only, args.max_steps)

    report = asyncio.run(go())
    _print(report)
    if args.json:
        Path(args.json).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
