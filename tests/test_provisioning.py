"""Autonomia: instala Playwright/Chromium sozinho, sem travar o cliente, com opt-out."""
import asyncio

import pytest

from a11y import provisioning as pv


@pytest.fixture()
def prov(monkeypatch):
    monkeypatch.delenv("A11Y_MCP_AUTO_INSTALL", raising=False)
    return pv.Provisioner()


def fake_env(monkeypatch, *, importable, chromium):
    """importable/chromium: listas consumidas a cada checagem; devolve o log de comandos rodados."""
    calls: list[tuple[str, ...]] = []
    imp, chr_ = list(importable), list(chromium)
    monkeypatch.setattr(pv, "playwright_importable", lambda: imp.pop(0) if len(imp) > 1 else imp[0])

    async def present():
        return chr_.pop(0) if len(chr_) > 1 else chr_[0]

    async def run(*cmd, timeout):
        calls.append(cmd)
        return 0, "ok"

    monkeypatch.setattr(pv, "chromium_present", present)
    monkeypatch.setattr(pv, "_run", run)
    return calls


async def test_everything_present_installs_nothing(prov, monkeypatch):
    calls = fake_env(monkeypatch, importable=[True], chromium=[True])
    await prov.ensure()
    assert prov.state == "ready" and calls == []


async def test_missing_package_and_browser_are_installed_in_order(prov, monkeypatch):
    calls = fake_env(monkeypatch, importable=[False, True], chromium=[False, True])
    await prov.ensure()
    assert prov.state == "ready"
    assert [c[2:5] for c in calls] == [("pip", "install", "playwright"), ("playwright", "install", "chromium")]


async def test_only_browser_missing(prov, monkeypatch):
    calls = fake_env(monkeypatch, importable=[True], chromium=[False, True])
    await prov.ensure()
    assert len(calls) == 1 and calls[0][2:5] == ("playwright", "install", "chromium")


async def test_install_that_does_not_fix_it_is_reported_not_hidden(prov, monkeypatch):
    fake_env(monkeypatch, importable=[True], chromium=[False])
    with pytest.raises(pv.ProvisioningError, match="Chromium"):
        await prov.ensure()
    assert prov.state == "failed"


async def test_opt_out_never_downloads(prov, monkeypatch):
    monkeypatch.setenv("A11Y_MCP_AUTO_INSTALL", "0")
    calls = fake_env(monkeypatch, importable=[False], chromium=[False])
    with pytest.raises(pv.ProvisioningError, match="A11Y_MCP_AUTO_INSTALL=0"):
        await prov.ensure()
    assert calls == []


async def test_slow_install_answers_in_progress_and_keeps_going(prov, monkeypatch):
    fake_env(monkeypatch, importable=[True], chromium=[False, True])
    gate = asyncio.Event()

    async def slow(*cmd, timeout):
        await gate.wait()
        return 0, "ok"

    monkeypatch.setattr(pv, "_run", slow)
    monkeypatch.setattr(pv, "WAIT_FOR_INSTALL_S", 0.05)
    with pytest.raises(pv.ProvisioningInProgress):
        await prov.ensure()
    assert prov.state == "installing"  # segue instalando em segundo plano
    gate.set()
    await prov.ensure()  # a chamada seguinte encontra tudo pronto
    assert prov.state == "ready"


async def test_failed_state_can_retry_after_the_cause_is_fixed(prov, monkeypatch):
    fake_env(monkeypatch, importable=[True], chromium=[False])
    with pytest.raises(pv.ProvisioningError):
        await prov.ensure()
    fake_env(monkeypatch, importable=[True], chromium=[True])
    await prov.ensure()
    assert prov.state == "ready"


async def test_unexpected_error_becomes_state_not_crash(prov, monkeypatch):
    monkeypatch.setattr(pv, "playwright_importable", lambda: (_ for _ in ()).throw(OSError("disco cheio")))
    with pytest.raises(pv.ProvisioningError, match="OSError"):
        await prov.ensure()
