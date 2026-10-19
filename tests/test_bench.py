"""Bancada de avaliacao: mutacoes na pagina boa e o axe sozinho x o conjunto de ferramentas (sem modelo)."""
import pytest

from accessibility_mcp.a11y import bench


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
