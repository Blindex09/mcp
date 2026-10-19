"""Achados com evidencia: validacao de fatos, verificador, exportacao (EARL/SARIF), execucoes salvas e comparacao."""
import json

from accessibility_mcp.a11y import findings, runs, wcag
from accessibility_mcp.a11y.session import SESSION
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


# --------------------------------------------------------------------------- ferramentas MCP
async def test_manual_tools_probe_finding_trace_and_report_formats():
    from accessibility_mcp import server as mcp_server

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
    from accessibility_mcp import server as mcp_server

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
