"""Achados com evidencia: validacao de fatos, verificador, exportacao (EARL/SARIF), execucoes salvas e comparacao."""
import json

from a11y import findings, runs, wcag
from a11y.session import SESSION
from tests.test_agent import FINISH, Script, decision, run
from tests.test_probes import BAD_DIALOG, HEAD

SEEN = {"e1": {"descriptor": {"tag": "button", "role": "button", "name": "Comprar"}, "brief": {"tag": "button"}}}


def build(raw, step=3, seen_steps=(1, 2), persona="keyboard"):
    return findings.build(raw, step=step, steps_seen=set(seen_steps), elements_seen=SEEN, persona=persona)


# --------------------------------------------------------------------------- fatos objetivos
def test_wcag_table_is_the_2_2_list():
    assert len(wcag.CRITERIA) == 86 and "4.1.1" not in wcag.CRITERIA  # Parsing saiu no 2.2
    assert wcag.normalize("WCAG 2.1.2 No Keyboard Trap") == "2.1.2" and wcag.normalize("9.9.9") is None and wcag.normalize("sem numero") is None
    assert wcag.normalize("1.4.10") == "1.4.10" and wcag.normalize("11.4.10") is None
    assert wcag.from_axe_tag("wcag412") == "4.1.2" and wcag.from_axe_tag("wcag1410") == "1.4.10" and wcag.from_axe_tag("best-practice") is None
    assert wcag.slug_of("2.1.2") == "no-keyboard-trap" and wcag.url_of("1.4.3").endswith("#contrast-minimum")


def test_build_validates_only_objective_facts():
    f, notes = build({"claim": "Botao sem nome", "criterion": "WCAG 4.1.2", "severity": "SERIOUS", "target": "e1", "evidence_steps": [1, 2]})
    assert f["criterion"] == "4.1.2" and f["criterion_name"] == "Name, Role, Value" and f["level"] == "A"
    assert f["severity"] == "serious" and f["element"]["name"] == "Comprar" and f["evidence_steps"] == [1, 2] and notes == []

    f, notes = build({"claim": "x", "criterion": "7.7.7", "severity": "enorme", "target": "e99", "evidence_steps": [2, 9]})
    assert f["criterion"] is None and f["severity"] == "unrated"  # criterio inexistente e gravidade fora da escala: nada inventado
    assert f["target"] is None and f["evidence_steps"] == [2]  # elemento nunca visto e passo futuro: descartados
    assert len(notes) == 3 and any("nao existe no WCAG 2.2" in n for n in notes) and any("nunca apareceu" in n for n in notes)

    assert build({"claim": "  "})[0] is None and build("texto solto")[0] is None
    f, _ = build({"claim": "ok"})
    assert f["evidence_steps"] == [2]  # sem evidencia citada: o que o modelo acabou de ver (passo anterior)
    f, _ = build({"claim": "ok"}, step=1, seen_steps=())
    assert f["evidence_steps"] == []


def test_fingerprint_survives_element_ids_but_not_a_different_criterion_or_element():
    a, _ = build({"claim": "x", "criterion": "4.1.2", "target": "e1"})
    b = dict(a, target="e77", id="f9", claim="outra redacao")  # o id do dossie muda entre execucoes; papel e nome do elemento nao
    c, _ = build({"claim": "x", "criterion": "2.1.1", "target": "e1"})
    assert findings.fingerprint(a) == findings.fingerprint(b) != findings.fingerprint(c)


def _mk(outcome="failed", crit="2.1.2", name="Menu", claim="o foco fica preso", sev="blocker"):
    return {"id": "f1", "criterion": crit, "severity": sev, "claim": claim, "outcome": outcome, "persona": "keyboard", "element": {"tag": "div", "role": None, "name": name}, "target": "e3", "evidence_steps": [1], "verification": None}


def test_diff_new_fixed_persisting_and_ignores_refuted():
    base = [_mk(name="A"), _mk(name="B"), _mk("unsupported", name="Z")]
    head = [_mk(name="B"), _mk(name="C"), _mk("cantTell", name="D")]
    d = findings.diff(base, head)
    assert d["counts"] == {"new": 2, "fixed": 1, "persisting": 1}
    assert {x["element"]["name"] for x in d["new"]} == {"C", "D"} and d["fixed"][0]["element"]["name"] == "A"


def test_earl_and_sarif_shapes():
    items = [_mk(), _mk("cantTell", crit="4.1.2", name="Botao", claim="talvez sem nome"), _mk("unsupported", name="Z"), {**_mk(crit=None, name="Q"), "criterion": None}]
    earl = findings.to_earl(items, "https://x.test/", created="2026-10-09")
    graph = earl["@graph"]
    assert len(graph) == 3  # o refutado nao entra
    assert graph[0]["earl:result"]["earl:outcome"] == {"@id": "earl:failed"} and graph[1]["earl:result"]["earl:outcome"] == {"@id": "earl:cantTell"}
    assert graph[0]["earl:test"]["@id"].endswith("#no-keyboard-trap") and graph[2]["earl:test"]["@id"] == "a11y:unmapped"
    assert graph[0]["earl:subject"]["dct:source"] == "https://x.test/" and earl["dct:created"] == "2026-10-09"
    json.dumps(earl)

    sarif = findings.to_sarif(items, "https://x.test/")
    run_ = sarif["runs"][0]
    assert sarif["version"] == "2.1.0" and len(run_["results"]) == 3
    assert {r["id"] for r in run_["tool"]["driver"]["rules"]} == {"WCAG-2.1.2", "WCAG-4.1.2", "A11Y-unmapped"}
    first, second = run_["results"][0], run_["results"][1]
    assert (first["kind"], first["level"]) == ("fail", "error") and (second["kind"], second["level"]) == ("review", "note")
    assert first["partialFingerprints"]["a11yFingerprint/v1"] == findings.fingerprint(items[0])


# --------------------------------------------------------------------------- no agente
def verdicts(*pairs):
    return json.dumps({"verdicts": [{"id": i, "verdict": v, "reason": r} for i, v, r in pairs]})


def with_finding(action, finding, thought="penso"):
    return json.dumps({"thought": thought, "friction": None, "finding": finding, "action": action})


PRESS = decision({"type": "press", "value": "Tab"})
FINDING = {"criterion": "2.4.7", "severity": "serious", "target": "e1", "claim": "o primeiro controle nao mostra foco", "evidence_steps": [1]}


async def test_supported_finding_becomes_failed_and_reaches_the_report_with_its_evidence():
    s = Script(PRESS, with_finding({"type": "finish", "outcome": "completed_with_friction", "summary": "x"}, FINDING),
               verdicts(("f1", "supported", "o passo 1 mostra o foco sem mudanca")), "Relatorio")
    r = await run(s, persona="keyboard")
    assert [f["outcome"] for f in r["findings"]] == ["failed"] and r["rejected_findings"] == []
    f = r["findings"][0]
    assert f["criterion"] == "2.4.7" and f["verification"]["verdict"] == "supported" and f["evidence_steps"] == [1]
    verifier = s.prompts[2]
    assert "ACHADO f1" in verifier and "passo 1: press" in verifier and "fatos do elemento e1" in verifier  # o pacote de evidencia vai ao verificador
    report_prompt = next(p for p in s.prompts if "RELATORIO desta sessao" in p)
    assert "ACHADOS CONFERIDOS" in report_prompt and "f1 WCAG 2.4.7 serious failed" in report_prompt
    assert r["run_id"] and runs.load(r["run_id"])["findings"][0]["claim"] == FINDING["claim"]


async def test_refuted_finding_is_dropped_from_the_report_but_kept_on_record():
    wrong = {**FINDING, "claim": "falta aria-modal no dialogo", "criterion": "4.1.2"}
    s = Script(PRESS, with_finding({"type": "finish", "outcome": "completed", "summary": "x"}, wrong),
               verdicts(("f1", "unsupported", "o fato do elemento mostra aria-modal=true")), "Relatorio")
    r = await run(s, persona="keyboard")
    assert r["findings"] == [] and r["rejected_findings"][0]["outcome"] == "unsupported"
    report_prompt = next(p for p in s.prompts if "RELATORIO desta sessao" in p)
    assert "AFIRMACOES REFUTADAS" in report_prompt and "falta aria-modal" in report_prompt and "ACHADOS CONFERIDOS" not in report_prompt
    assert runs.load(r["run_id"])["findings"][0]["outcome"] == "unsupported"  # fica registrado, so nao entra nas exportacoes


async def test_finding_without_any_evidence_is_cantTell_with_no_model_call():
    no_ev = {"criterion": "1.1.1", "severity": "minor", "claim": "imagem sem alternativa", "evidence_steps": []}
    s = Script(with_finding({"type": "finish", "outcome": "completed", "summary": "x"}, no_ev), "Relatorio")
    r = await run(s)
    assert r["findings"][0]["outcome"] == "cantTell" and "nenhuma evidencia" in r["findings"][0]["verification"]["reason"]
    assert s.tiers == ["main", "write", None]  # sem pacote de evidencia nao ha chamada de verificacao


async def test_verifier_silence_or_garbage_never_turns_a_finding_into_a_failure():
    base = [PRESS, with_finding({"type": "finish", "outcome": "completed", "summary": "x"}, FINDING)]
    r = await run(Script(*base, None, None, "Relatorio"), persona="keyboard")  # modelo indisponivel nas duas tentativas do verificador
    assert r["findings"][0]["outcome"] == "cantTell" and "nao respondeu" in r["findings"][0]["verification"]["reason"]
    r = await run(Script(*base, "lixo", verdicts(("f1", "talvez", "x"), ("f7", "supported", "x")), "Relatorio"), persona="keyboard")
    assert r["findings"][0]["outcome"] == "cantTell"  # veredito fora do vocabulario e id inexistente sao ignorados


async def test_invalid_references_are_reported_as_notes_not_crashes():
    bad = {"criterion": "13.1.1", "severity": "x", "target": "e999", "claim": "algo", "evidence_steps": [1]}
    s = Script(PRESS, with_finding({"type": "finish", "outcome": "completed", "summary": "x"}, [bad, "lixo", None]), verdicts(("f1", "cantTell", "sem fato")), "Relatorio")
    r = await run(s, persona="keyboard")
    assert len(r["findings"]) == 1 and r["findings"][0]["criterion"] is None and r["findings"][0]["target"] is None
    assert any("nao existe no WCAG 2.2" in n for n in r["finding_notes"]) and any("e999" in n for n in r["finding_notes"])


async def test_probe_action_runs_in_the_agent_and_its_facts_become_evidence():
    s = Script(decision({"type": "probe", "value": "tab_walk"}), decision({"type": "probe", "value": "dialog"}),
               decision({"type": "probe", "value": "inexistente"}),
               with_finding({"type": "finish", "outcome": "completed", "summary": "x"}, {**FINDING, "target": None, "criterion": "2.1.2", "claim": "Tab percorre a pagina", "evidence_steps": [1]}),
               verdicts(("f1", "supported", "ok")), "Relatorio")
    r = await run(s, persona="keyboard")
    assert r["steps"][0]["effect"].startswith("sonda tab_walk:") and r["steps"][0]["facts"]["summary"]
    assert "precisa de target" in r["steps"][1]["refused"] and "uma sonda" in r["steps"][2]["refused"]
    assert "SONDAS:" in s.prompts[0] and "tab_walk" in s.prompts[0] and "wcag-evidence-and-probes" not in s.prompts[0]  # o guia entra pelo conteudo, nao pelo nome
    assert "Which probe proves which criterion" in s.prompts[0]
    assert "fatos do passo 1" in s.prompts[4]
    assert "tab_walk" in r["coverage"]["probes_run"] and not any("tab_walk" in g for g in r["coverage"]["gaps"])


# --------------------------------------------------------------------------- ferramentas MCP
async def test_manual_tools_probe_finding_trace_and_report_formats():
    import mcp_server

    tools = mcp_server.mcp._tool_manager
    call = lambda name, **kw: tools.get_tool(name).fn(**kw)
    assert "nenhuma sessao" in json.loads(await call("a11y_trace"))["error"]
    await call("a11y_open", html=HEAD + BAD_DIALOG + "</body></html>")
    try:
        d = json.loads(await call("a11y_dossier"))
        opener = next(e for e in d["elements"] if e["text"] == "Abrir")
        probe = json.loads(await call("a11y_probe", kind="dialog", target=opener["id"]))
        assert "foco_vai_para_dentro" in probe["unmet"] and "escape_fecha" in probe["unmet"]
        trace = json.loads(await call("a11y_trace"))
        assert trace["total"] == 1 and trace["steps"][0]["kind"] == "probe:dialog"

        ok = json.loads(await call("a11y_finding", claim="o foco nao entra no dialogo ao abrir", criterion="2.4.3", severity="serious", target=opener["id"], evidence_steps="1"))
        assert ok["recorded"]["outcome"] == "failed" and ok["recorded"]["verification"]["verdict"] == "recorded" and ok["recorded"]["element"]["name"] == "Abrir"
        weak = json.loads(await call("a11y_finding", claim="algo parece estranho", criterion="9.9.9"))
        assert weak["recorded"]["outcome"] == "cantTell" and weak["recorded"]["criterion"] is None
        assert "sem afirmacao" in json.loads(await call("a11y_finding", claim=""))["error"]

        earl = json.loads(await call("a11y_report", format="earl"))
        assert [g["earl:result"]["earl:outcome"]["@id"] for g in earl["@graph"]] == ["earl:failed", "earl:cantTell"]
        sarif = json.loads(await call("a11y_report", format="sarif"))
        assert sarif["runs"][0]["results"][0]["ruleId"] == "WCAG-2.4.3"
        js = json.loads(await call("a11y_report", format="json"))
        assert js["counts"]["failed"] == 1 and js["counts"]["cantTell"] == 1
        assert "format" in json.loads(await call("a11y_report", format="xml"))["error"]
        assert "invalida" in json.loads(await call("a11y_probe", kind="zzz"))["error"]
    finally:
        await call("a11y_close")
    assert SESSION.page is None


async def test_saved_runs_can_be_listed_exported_and_diffed():
    import mcp_server

    tools = mcp_server.mcp._tool_manager
    call = lambda name, **kw: tools.get_tool(name).fn(**kw)
    rid1 = runs.save("loja.test", {"url": "https://loja.test/", "persona": "keyboard", "mode": "task", "goal": "comprar", "outcome": "not_completed",
                                   "findings": [_mk(name="Menu"), _mk(name="Busca", crit="4.1.2", claim="sem nome")]})
    rid2 = runs.save("loja.test", {"url": "https://loja.test/", "persona": "keyboard", "mode": "task", "goal": "comprar", "outcome": "completed",
                                   "findings": [_mk(name="Menu"), _mk(name="Carrinho", crit="1.1.1", claim="icone sem alt")]})
    listing = json.loads(await call("a11y_runs"))
    assert [r["run_id"] for r in listing["runs"]] == [rid2, rid1] and listing["runs"][0]["findings"] == {"failed": 2}
    sarif = json.loads(await call("a11y_export", run_id=rid1, format="sarif"))
    assert len(sarif["runs"][0]["results"]) == 2 and sarif["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "https://loja.test/"
    diff = json.loads(await call("a11y_diff", base_run_id=rid1, head_run_id=rid2))
    assert diff["counts"] == {"new": 1, "fixed": 1, "persisting": 1} and diff["fixed"][0]["element"]["name"] == "Busca"
    assert "nao encontrada" in json.loads(await call("a11y_export", run_id="../../etc/passwd"))["error"]  # texto do cliente nunca vira caminho
    assert "nao encontrada" in json.loads(await call("a11y_diff", base_run_id=rid1, head_run_id="nao-existe"))["error"]


def test_runs_can_be_turned_off(monkeypatch):
    monkeypatch.setenv("A11Y_MCP_RUNS", "0")
    assert runs.save("x.test", {"findings": []}) is None and runs.list_runs() == []
    assert FINISH  # (formato usado pelos outros testes)
