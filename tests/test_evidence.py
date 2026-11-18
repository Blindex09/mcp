"""Evidencia no rastro: NVDA real, axe, contraste, mapa da pagina e dossie viram passos citaveis, e o achado deixa de ser cantTell."""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from accessibility_mcp.a11y import evidence, nvda_vm
from accessibility_mcp.a11y.session import SESSION
from accessibility_mcp.server import mcp

ROOT = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")
TOKEN = "token-de-teste-com-mais-de-16"
PAGE = '<!doctype html><html lang="pt-BR"><head><title>Teste</title></head><body><p style="color:#8fa08f;background:#f7f3ea;font-size:9px">Travel Expert</p><button aria-pressed="false">Opcao</button></body></html>'


async def call(name: str, **args):
    content = await mcp.call_tool(name, args)
    blocks = content[0] if isinstance(content, tuple) else content
    return json.loads(blocks[0].text)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in (nvda_vm.ENV_URL, nvda_vm.ENV_TOKEN, nvda_vm.ENV_HOST_ADDR):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture()
async def session():
    await call("a11y_open", html=PAGE, persona="keyboard")
    yield
    await call("a11y_close")


async def test_axe_and_contrast_write_a_citable_step_and_the_finding_is_confirmed(session):
    audit = await call("a11y_audit", html=PAGE)
    step = audit["trace_step"]
    entry = next(t for t in (await call("a11y_trace"))["steps"] if t["n"] == step)
    assert entry["kind"] == "axe" and entry["facts"]["violacoes"][0]["regra"] == "color-contrast"
    assert "2.4" in entry["facts"]["violacoes"][0]["exemplos"][0]["medida"] or "contrast" in entry["facts"]["violacoes"][0]["exemplos"][0]["medida"].lower()
    measured = await call("a11y_contrast", foreground="#8fa08f", background="#f7f3ea", size_px=9)
    assert measured["trace_step"] > step
    found = await call("a11y_finding", claim="Texto pequeno com pouco contraste", criterion="1.4.3", severity="serious", evidence_steps=f"{step},{measured['trace_step']}")
    assert found["recorded"]["outcome"] == "failed" and found["recorded"]["evidence_steps"] == [step, measured["trace_step"]]


async def test_dossier_and_page_map_write_steps_with_names_and_regions(session):
    dossier = await call("a11y_dossier")
    page_map = await call("a11y_page_map")
    steps = {t["kind"]: t for t in (await call("a11y_trace"))["steps"]}
    assert dossier["trace_step"] == steps["dossier"]["n"] and page_map["trace_step"] == steps["page_map"]["n"]
    controls = steps["dossier"]["facts"]["controles"]
    assert any(c["nome"] == "Opcao" and c["pressionado"] == "false" for c in controls)
    assert steps["page_map"]["facts"]["regioes"]["tem_main"] is False
    found = await call("a11y_finding", claim="Sem regiao principal", criterion="1.3.1", evidence_steps=str(page_map["trace_step"]))
    assert found["recorded"]["outcome"] == "failed"


async def test_a_finding_without_any_step_is_still_cant_tell(session):
    found = await call("a11y_finding", claim="Observacao sem passo", criterion="1.3.1")
    assert found["recorded"]["outcome"] == "cantTell"


def test_evidence_without_a_session_never_breaks_the_tool():
    assert evidence.with_step({"a": 1}, None) == {"a": 1}
    assert evidence.with_step({"a": 1}, 7) == {"a": 1, "trace_step": 7}
    assert evidence.with_step("texto", 7) == "texto"
    assert len(SESSION.trace) >= 0


@pytest.mark.skipif(NODE is None, reason="Node.js nao esta instalado")
async def test_real_nvda_speech_becomes_a_citable_step(monkeypatch):
    proc = subprocess.Popen([NODE, str(ROOT / "nvda" / "vm" / "simulado.mjs")], stdout=subprocess.PIPE, text=True, env={**os.environ, "NVDA_AGENT_TOKEN": TOKEN})  # noqa: ASYNC220 - agente simulado de teste
    try:
        line = proc.stdout.readline()
        assert line.startswith("PORTA "), line
        monkeypatch.setenv(nvda_vm.ENV_URL, f"http://127.0.0.1:{line.split()[1]}")
        monkeypatch.setenv(nvda_vm.ENV_TOKEN, TOKEN)
        await call("a11y_open", html=PAGE, persona="keyboard")
        try:
            assert (await call("a11y_nvda_open", url="http://exemplo.com")).get("aberta") is True
            spoken = await call("a11y_nvda_do", action="key", key="H", repeat=2)
            step = spoken["trace_step"]
            entry = next(t for t in (await call("a11y_trace"))["steps"] if t["n"] == step)
            assert entry["kind"] == "nvda:tecla" and entry["facts"]["falas"] == ["titulo 1", "titulo 2"]
            assert entry["facts"]["fonte"].startswith("NVDA real")
            found = await call("a11y_finding", claim="O NVDA nao anuncia a mudanca", criterion="4.1.3", evidence_steps=str(step))
            assert found["recorded"]["outcome"] == "failed"
            await call("a11y_nvda_close")
        finally:
            await call("a11y_close")
    finally:
        proc.kill()
        proc.wait()
