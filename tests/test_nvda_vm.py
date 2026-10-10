"""Fala real do NVDA pela VM: o contrato entre o MCP (Python) e o agente (Node) e o cliente, tudo sem ligar o NVDA."""
import asyncio
import http.server
import json
import os
import shutil
import subprocess
import threading
from pathlib import Path

import pytest

from a11y import nvda_vm

ROOT = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")
TOKEN = "token-de-teste-com-mais-de-16"
needs_node = pytest.mark.skipif(NODE is None, reason="Node.js nao esta instalado")


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in (nvda_vm.ENV_URL, nvda_vm.ENV_TOKEN, nvda_vm.ENV_HOST_ADDR):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture()
def simulated_agent():
    """O agente de verdade (agent.mjs), com um NVDA simulado por tras."""
    proc = subprocess.Popen(
        [NODE, str(ROOT / "nvda" / "vm" / "simulado.mjs")], stdout=subprocess.PIPE, text=True,
        env={**os.environ, "NVDA_AGENT_TOKEN": TOKEN},
    )
    line = proc.stdout.readline()
    assert line.startswith("PORTA "), line
    yield f"http://127.0.0.1:{line.split()[1]}"
    proc.kill()
    proc.wait()


def test_node_side_tests_pass():
    """Os testes do agente e do percurso (com NVDA, navegador e janela simulados)."""
    if NODE is None:
        pytest.skip("Node.js nao esta instalado")
    done = subprocess.run([NODE, "--test", str(ROOT / "nvda" / "vm" / "agent.test.mjs")], capture_output=True, text=True, timeout=120, check=False)
    assert done.returncode == 0, done.stdout[-1500:] + done.stderr[-500:]


async def test_not_configured_explains_how_instead_of_failing_silently():
    with pytest.raises(nvda_vm.NvdaVmError) as e:
        await nvda_vm.run("http://exemplo.com")
    assert "A11Y_MCP_NVDA_VM" in str(e.value) and "A11Y_MCP_NVDA_TOKEN" in str(e.value)


def test_loopback_urls_are_translated_only_when_the_host_address_is_configured(monkeypatch):
    assert nvda_vm.translate_url("http://127.0.0.1:8080/a?x=1") == "http://127.0.0.1:8080/a?x=1"
    monkeypatch.setenv(nvda_vm.ENV_HOST_ADDR, "192.168.100.1")
    assert nvda_vm.translate_url("http://127.0.0.1:8080/a?x=1") == "http://192.168.100.1:8080/a?x=1"
    assert nvda_vm.translate_url("http://localhost/b") == "http://192.168.100.1/b"
    assert nvda_vm.translate_url("https://exemplo.com/c") == "https://exemplo.com/c"  # site de verdade nao muda
    for bad in ("file:///c:/x", "javascript:alert(1)", "ftp://x.com", "sem-esquema"):
        with pytest.raises(nvda_vm.NvdaVmError):
            nvda_vm.translate_url(bad)


@needs_node
async def test_full_round_trip_with_the_real_agent_and_a_simulated_nvda(simulated_agent, monkeypatch):
    monkeypatch.setenv(nvda_vm.ENV_URL, simulated_agent)
    monkeypatch.setenv(nvda_vm.ENV_TOKEN, TOKEN)
    monkeypatch.setenv(nvda_vm.ENV_HOST_ADDR, "127.0.0.1")
    result = await nvda_vm.run("http://localhost:9999/loja", tabs=3, reads=2, poll=0.05)
    out = nvda_vm.facts(result, "http://localhost:9999/loja")
    assert [x["fala"] for x in out["tab_walk"]] == ["Tab 1 em 127.0.0.1", "Tab 2 em 127.0.0.1", "Tab 3 em 127.0.0.1"]
    assert [x["fala"] for x in out["reading_mode"]] == ["item 1", "item 2"]
    assert out["error"] is None and out["muted"] == "volume"  # a VM silencia por padrao
    assert "NAO sao os do NVDA da pessoa" in " ".join(out["notes"])
    assert TOKEN not in json.dumps(out)


@needs_node
async def test_wrong_token_and_busy_vm_get_clear_messages_and_never_leak_the_token(simulated_agent, monkeypatch):
    monkeypatch.setenv(nvda_vm.ENV_URL, simulated_agent)
    monkeypatch.setenv(nvda_vm.ENV_TOKEN, "um-token-errado-bem-longo")
    with pytest.raises(nvda_vm.NvdaVmError) as e:
        await nvda_vm.run("http://exemplo.com", tabs=1, reads=0)
    assert "token" in str(e.value) and "um-token-errado-bem-longo" not in str(e.value)

    monkeypatch.setenv(nvda_vm.ENV_TOKEN, TOKEN)
    first = asyncio.create_task(nvda_vm.run("http://exemplo.com", tabs=20, reads=0, poll=0.05))
    await asyncio.sleep(0.15)
    with pytest.raises(nvda_vm.NvdaVmError) as busy:
        await nvda_vm.run("http://exemplo.com", tabs=1, reads=0)
    assert "ja esta fazendo um teste" in str(busy.value)
    assert len((await first)["tab"]) == 20  # o primeiro nao foi atrapalhado nem repetido


@needs_node
async def test_invalid_requests_are_refused_by_the_agent(simulated_agent, monkeypatch):
    monkeypatch.setenv(nvda_vm.ENV_URL, simulated_agent)
    monkeypatch.setenv(nvda_vm.ENV_TOKEN, TOKEN)
    with pytest.raises(nvda_vm.NvdaVmError) as e:
        await nvda_vm.run("http://exemplo.com", tabs=5000, reads=0)
    assert "recusou o pedido" in str(e.value)


async def test_unreachable_vm_says_what_to_check(monkeypatch):
    monkeypatch.setenv(nvda_vm.ENV_URL, "http://127.0.0.1:1")
    monkeypatch.setenv(nvda_vm.ENV_TOKEN, TOKEN)
    with pytest.raises(nvda_vm.NvdaVmError) as e:
        await nvda_vm.run("http://exemplo.com")
    assert "firewall" in str(e.value)


class _Stuck(http.server.BaseHTTPRequestHandler):
    """Aceita o pedido e depois diz 'executando' no mesmo passo para sempre."""

    def _send(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        self.rfile.read(int(self.headers.get("content-length", 0)))
        self._send(202, {"id": "00000000-0000-0000-0000-000000000000"})

    def do_GET(self):
        self._send(200, {"estado": "executando", "passos": 4})

    def log_message(self, *a, **k):
        return


async def test_a_run_that_stops_making_progress_is_reported_not_waited_forever(monkeypatch):
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Stuck)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setenv(nvda_vm.ENV_URL, f"http://127.0.0.1:{srv.server_address[1]}")
    monkeypatch.setenv(nvda_vm.ENV_TOKEN, TOKEN)
    monkeypatch.setattr(nvda_vm, "STALL_FLOOR_S", 0.4)  # o piso e' configuracao; em producao sao 120 s e cresce com o ritmo visto
    try:
        with pytest.raises(nvda_vm.NvdaVmError) as e:
            await nvda_vm.run("http://exemplo.com", poll=0.05)
        assert "sem progresso" in str(e.value) and "passo 4" in str(e.value)
    finally:
        srv.shutdown()
