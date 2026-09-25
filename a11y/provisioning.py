"""Autonomia: o servidor instala sozinho o que falta para operar um navegador (Playwright + Chromium).

Sem "nao da": se faltar o pacote ou o navegador, instala e segue. A instalacao roda em segundo plano
no inicio do servidor; se uma ferramenta chegar antes de terminar, ela espera um pouco e, se ainda nao
acabou, responde que a instalacao esta em andamento (sem travar o cliente).

Opt-out: A11Y_MCP_AUTO_INSTALL=0 (ambientes que nao podem baixar nada).
Instala apenas: o pacote PyPI `playwright` e o Chromium oficial do Playwright (`playwright install chromium`).
"""

from __future__ import annotations

import asyncio
import importlib
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

PIP_TIMEOUT_S = 300
BROWSER_TIMEOUT_S = 900
WAIT_FOR_INSTALL_S = 50  # abaixo do timeout tipico de ferramentas dos clientes


class ProvisioningError(RuntimeError):
    """Nao foi possivel deixar o navegador pronto (mensagem para o cliente)."""


class ProvisioningInProgress(ProvisioningError):
    """A instalacao ainda esta rodando: tentar de novo em instantes."""


def auto_install_enabled() -> bool:
    return os.environ.get("A11Y_MCP_AUTO_INSTALL", "1").strip().lower() not in ("0", "false", "no", "off")


async def _run(*cmd: str, timeout: float) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except TimeoutError:
        proc.kill()
        await proc.wait()
        return 124, f"tempo esgotado apos {timeout:.0f}s"
    return proc.returncode or 0, out.decode(errors="replace")[-600:]


def playwright_importable() -> bool:
    try:
        importlib.import_module("playwright.async_api")
    except ImportError:
        return False
    return True


async def chromium_present() -> bool:
    """O Chromium que ESTA versao do Playwright espera existe no disco?"""
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        return Path(pw.chromium.executable_path).exists()


class Provisioner:
    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self.state = "unknown"  # unknown | checking | installing | ready | failed
        self.detail = ""

    async def _provision(self) -> None:
        self.state = "checking"
        try:
            if not playwright_importable():
                if not auto_install_enabled():
                    raise ProvisioningError("Playwright ausente e A11Y_MCP_AUTO_INSTALL=0. Rode: pip install playwright")
                self.state = "installing"
                logger.info("Instalando o pacote playwright (pip)...")
                code, out = await _run(sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "playwright", timeout=PIP_TIMEOUT_S)
                importlib.invalidate_caches()
                if code != 0 or not playwright_importable():
                    raise ProvisioningError(f"falha ao instalar o pacote playwright: {out.strip()[-200:]}")
            if not await chromium_present():
                if not auto_install_enabled():
                    raise ProvisioningError("Chromium ausente e A11Y_MCP_AUTO_INSTALL=0. Rode: python -m playwright install chromium")
                self.state = "installing"
                logger.info("Baixando o Chromium do Playwright...")
                code, out = await _run(sys.executable, "-m", "playwright", "install", "chromium", timeout=BROWSER_TIMEOUT_S)
                if code != 0 or not await chromium_present():
                    raise ProvisioningError(f"falha ao instalar o Chromium: {out.strip()[-200:]}")
            self.state, self.detail = "ready", ""
        except ProvisioningError as e:
            self.state, self.detail = "failed", str(e)
            logger.warning("provisionamento do navegador falhou: %s", e)
        except Exception as e:  # noqa: BLE001 - qualquer falha inesperada vira estado, nao derruba o servidor
            self.state, self.detail = "failed", f"{type(e).__name__}: {e}"
            logger.warning("provisionamento do navegador falhou: %s", self.detail)

    def start_background(self) -> None:
        """Dispara o provisionamento sem bloquear (chamado no inicio do servidor)."""
        if self._task is None or (self._task.done() and self.state != "ready"):
            self._task = asyncio.create_task(self._provision())

    async def ensure(self) -> None:
        """Garante navegador pronto; instala se preciso; nunca trava alem de WAIT_FOR_INSTALL_S."""
        if self.state == "ready":
            return
        self.start_background()
        assert self._task is not None
        try:
            await asyncio.wait_for(asyncio.shield(self._task), timeout=WAIT_FOR_INSTALL_S)
        except TimeoutError as e:
            raise ProvisioningInProgress(
                "Instalando o navegador (Playwright/Chromium) automaticamente; isso leva alguns minutos na primeira vez. "
                "Tente de novo em instantes."
            ) from e
        if self.state == "failed":
            raise ProvisioningError(self.detail)


PROVISIONER = Provisioner()
