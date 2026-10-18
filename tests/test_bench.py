"""Bancada de avaliacao: mutacoes na pagina boa, o axe sozinho x o conjunto de ferramentas, e a pontuacao do agente."""
import json

import pytest

from accessibility_mcp.a11y import bench
from tests.test_agent import FINISH, Script, decision


def test_every_mutation_changes_exactly_the_page_it_claims_and_names_real_wcag_criteria():
    from accessibility_mcp.a11y import wcag

    base = bench.base_html()
    names = [m.name for m in bench.MUTATIONS]
    assert len(names) == len(set(names)) >= 12
    for m in bench.MUTATIONS:
        mutated = m.apply(base)
        assert mutated != base, m.name
        assert m.criteria and all(c in wcag.CRITERIA for c in m.criteria), m.name
    with pytest.raises(ValueError):
        bench._swap(("trecho que nao existe", "x"))(base)  # mutacao desatualizada falha alto, nao em silencio


async def test_facts_bench_toolset_beats_axe_alone_and_the_clean_page_raises_no_alarm():
    report = await bench.run_facts()
    s = report["summary"]
    assert s["false_alarms_on_clean_page"] == []  # a pagina boa nao pode disparar nenhum detector
    assert s["missed_by_everything"] == []
    assert s["toolset_recall"] == 1.0 and s["axe_recall"] < s["toolset_recall"]
    # o que so o comportamento e os fatos enxergam: controle so de mouse, titulos, alvo pequeno, armadilha, dialogo, estado e status
    assert set(s["only_the_behavior_and_fact_tools_caught"]) >= {"div_vira_botao", "armadilha_teclado", "dialogo_sem_foco", "sem_estado_expandido", "status_mudo", "alvo_pequeno"}
    assert {"sem_alt", "sem_lang", "botao_sem_nome"}.isdisjoint(s["only_the_behavior_and_fact_tools_caught"])  # o axe tambem acha esses


def test_scoring_separates_hits_wrong_criteria_and_clean_page_false_positives():
    m = next(x for x in bench.MUTATIONS if x.name == "sem_lang")
    ok = {"outcome": "failed", "criterion": "3.1.1", "claim": "A pagina nao declara o idioma", "element": None}
    wrong = {"outcome": "failed", "criterion": "1.4.3", "claim": "contraste", "element": None}
    unsure = {"outcome": "cantTell", "criterion": "3.1.1", "claim": "talvez", "element": None}
    refuted = {"outcome": "unsupported", "criterion": "3.1.1", "claim": "x", "element": None}
    assert bench.score_findings([ok, wrong, unsure, refuted], m) == {"hit_lenient": True, "hit_strict": True, "false_positives": 1, "failed": 2, "cantTell": 1}
    right_criterion_vague_text = {"outcome": "failed", "criterion": "3.1.1", "claim": "problema geral", "element": None}
    scored = bench.score_findings([right_criterion_vague_text], m)
    assert scored["hit_lenient"] is True and scored["hit_strict"] is False
    assert bench.score_findings([unsure], m)["hit_lenient"] is False  # cantTell nao e' acerto
    assert bench.score_findings([ok, wrong], None) == {"hit_lenient": None, "hit_strict": None, "false_positives": 2, "failed": 2, "cantTell": 0}


async def test_agent_bench_wiring_with_a_scripted_model():
    finding = {"criterion": "3.1.1", "severity": "serious", "target": None, "claim": "A pagina nao declara o idioma", "evidence_steps": [1]}
    finish_with_finding = json.dumps({"thought": "achei", "friction": None, "finding": finding, "action": {"type": "finish", "outcome": "completed_with_friction", "summary": "x"}})
    verdict = json.dumps({"verdicts": [{"id": "f1", "verdict": "supported", "reason": "o mapa mostra lang=null"}]})
    s = Script(
        decision({"type": "probe", "value": "tab_walk"}), finish_with_finding, verdict, "Relatorio", "[]",  # pagina sem idioma
        FINISH, "Relatorio", "[]",  # pagina boa: nada a achar
    )
    report = await bench.run_agent_bench(s, only={"sem_lang"}, max_steps=5)
    assert [r["case"] for r in report["rows"]] == ["sem_lang", "pagina_boa"]
    assert report["rows"][0]["hit_strict"] is True and report["rows"][1]["false_positives"] == 0
    assert report["summary"]["recall_lenient"] == 1.0 and report["summary"]["false_positives_clean_page"] == 0
