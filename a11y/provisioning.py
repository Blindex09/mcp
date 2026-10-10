"""Autonomia: o servidor instala sozinho o que falta para operar um navegador (Playwright + Chromium/Firefox/WebKit).

Sem "nao da": se faltar o pacote ou o navegador pedido, instala e segue. A instalacao roda em segundo plano
(o Chromium no inicio do servidor; Firefox/WebKit na primeira vez que forem pedidos). Se uma ferramenta chegar
antes de terminar, ela espera um pouco e, se ainda nao acabou, responde que a instalacao esta em andamento
(sem travar o cliente).

Opt-out: A11Y_MCP_AUTO_INSTALL=0 (ambientes que nao podem baixar nada).
Instala apenas: o pacote PyPI `playwright` e o navegador oficial do Playwright (`playwright install <navegador>`).
"""

from __future__ import annotations

import asyncio
import importlib
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

BROWSERS = ("chromium", "firefox", "webkit")
PIP_TIMEOUT_S = 300
BROWSER_TIMEOUT_S = 900
WAIT_FOR_INSTALL_S = 50  # abaixo do timeout tipico de ferramentas dos clientes


class ProvisioningError(RuntimeError):
    """Nao foi possivel deixar o navegador pronto (mensagem para o cliente)."""


class ProvisioningInProgress(ProvisioningError):
    """A instalacao ainda esta rodando: tentar de novo em instantes."""


def auto_install_enabled() -> bool:
    return os.environ.get("A11Y_MCP_AUTO_INSTALL", "1").strip().lower() not in ("0", "false", "no", "off")


def check_browser_name(browser: str) -> str:
    if browser not in BROWSERS:
        raise ProvisioningError(f"navegador invalido: {browser!r}. Opcoes: {', '.join(BROWSERS)}")
    return browser


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


async def browser_present(browser: str = "chromium") -> bool:
    """O navegador que ESTA versao do Playwright espera existe no disco?"""
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        return Path(getattr(pw, browser).executable_path).exists()


class Provisioner:
    def __init__(self, browser: str = "chromium") -> None:
        self.browser = check_browser_name(browser)
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
                code, out = await _run(
                    sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "playwright", timeout=PIP_TIMEOUT_S
                )
                importlib.invalidate_caches()
                if code != 0 or not playwright_importable():
                    raise ProvisioningError(f"falha ao instalar o pacote playwright: {out.strip()[-200:]}")
            if not await browser_present(self.browser):
                if not auto_install_enabled():
                    raise ProvisioningError(
                        f"{self.browser} ausente e A11Y_MCP_AUTO_INSTALL=0. Rode: python -m playwright install {self.browser}"
                    )
                self.state = "installing"
                logger.info("Baixando o %s do Playwright...", self.browser)
                code, out = await _run(sys.executable, "-m", "playwright", "install", self.browser, timeout=BROWSER_TIMEOUT_S)
                if code != 0 or not await browser_present(self.browser):
                    raise ProvisioningError(f"falha ao instalar o {self.browser}: {out.strip()[-200:]}")
            self.state, self.detail = "ready", ""
        except ProvisioningError as e:
            self.state, self.detail = "failed", str(e)
            logger.warning("provisionamento do %s falhou: %s", self.browser, e)
        except Exception as e:  # noqa: BLE001 - qualquer falha inesperada vira estado, nao derruba o servidor
            self.state, self.detail = "failed", f"{type(e).__name__}: {e}"
            logger.warning("provisionamento do %s falhou: %s", self.browser, self.detail)

    def start_background(self) -> None:
        """Dispara o provisionamento sem bloquear."""
        if self._task is None or (self._task.done() and self.state != "ready"):
            self._task = asyncio.create_task(self._provision())

    async def ensure(self) -> None:
        """Garante o navegador pronto; instala se preciso; nunca trava alem de WAIT_FOR_INSTALL_S."""
        if self.state == "ready":
            return
        self.start_background()
        assert self._task is not None
        try:
            await asyncio.wait_for(asyncio.shield(self._task), timeout=WAIT_FOR_INSTALL_S)
        except TimeoutError as e:
            raise ProvisioningInProgress(
                f"Instalando o {self.browser} (Playwright) automaticamente; isso leva alguns minutos na primeira vez. "
                "Tente de novo em instantes."
            ) from e
        if self.state == "failed":
            raise ProvisioningError(self.detail)


PROVISIONERS: dict[str, Provisioner] = {}


def provisioner_for(browser: str = "chromium") -> Provisioner:
    check_browser_name(browser)
    if browser not in PROVISIONERS:
        PROVISIONERS[browser] = Provisioner(browser)
    return PROVISIONERS[browser]


PROVISIONER = provisioner_for("chromium")  # o Chromium e' provisionado no inicio do servidor


def status_of_all() -> dict[str, dict[str, str | None]]:
    """Estado de cada navegador (os ainda nao solicitados aparecem como 'not_requested')."""
    return {
        b: {
            "state": PROVISIONERS[b].state if b in PROVISIONERS else "not_requested",
            "detail": (PROVISIONERS[b].detail or None) if b in PROVISIONERS else None,
        }
        for b in BROWSERS
    }
