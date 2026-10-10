"""Fala real do NVDA, obtida numa maquina virtual (Windows) por um agente em Node (nvda/vm/agent.mjs).

Por que numa VM: o NVDA so tem uma copia por vez e o Guidepup fecha a do usuario ao iniciar; numa VM o NVDA do
usuario, a voz e os complementos dele nunca sao tocados. So fatos: o texto que o NVDA falou, sem veredito.
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx

ENV_URL = "A11Y_MCP_NVDA_VM"
ENV_TOKEN = "A11Y_MCP_NVDA_TOKEN"
ENV_HOST_ADDR = "A11Y_MCP_NVDA_HOST_ADDR"
LOOPBACK = {"localhost", "127.0.0.1", "::1"}
STALL_FLOOR_S = 120.0  # sem avanco por pelo menos isto (e 5x o maior intervalo ja visto) = travado
OFFLINE_FLOOR_S = 60.0  # VM sem responder por pelo menos isto (e 10x o maior intervalo) = fora do ar

HELP = (
    "A fala real do NVDA roda numa VM Windows. Configure no cliente MCP: A11Y_MCP_NVDA_VM (endereco do agente, ex.: "
    "http://192.168.100.20:8765) e A11Y_MCP_NVDA_TOKEN (o token que o instalador da VM mostrou). Para testar um site que so existe "
    "no seu computador, defina tambem A11Y_MCP_NVDA_HOST_ADDR com o endereco do seu computador visto pela VM e deixe o site "
    "escutando nessa rede. Passo a passo: nvda/vm/LEIAME.md."
)


class NvdaVmError(Exception):
    """Falha ao obter a fala da VM (mensagem ja pronta para a pessoa)."""


def configured() -> tuple[str, str] | None:
    base, token = os.environ.get(ENV_URL, "").strip(), os.environ.get(ENV_TOKEN, "").strip()
    return (base.rstrip("/"), token) if base and token else None


def translate_url(url: str) -> str:
    """Dentro da VM, 127.0.0.1 e' a propria VM: se a pessoa informou o endereco do computador, troca so o host."""
    parts = urlsplit(url.strip())
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise NvdaVmError("so URLs http:// ou https:// sao permitidas")
    addr = os.environ.get(ENV_HOST_ADDR, "").strip()
    if addr and (parts.hostname or "").lower() in LOOPBACK:
        port = f":{parts.port}" if parts.port else ""
        parts = parts._replace(netloc=f"{addr}{port}")
        return urlunsplit(parts)
    return url.strip()


async def run(url: str, tabs: int = 15, reads: int = 20, silence: str | None = None, poll: float = 1.0) -> dict[str, Any]:
    cfg = configured()
    if cfg is None:
        raise NvdaVmError(HELP)
    base, token = cfg
    target = translate_url(url)
    body: dict[str, Any] = {"url": target, "tabs": tabs, "leituras": reads}
    if silence is not None:
        body["silencio"] = silence
    headers = {"authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(headers=headers, timeout=30) as client:
        try:
            resp = await client.post(f"{base}/percorrer", json=body)
        except httpx.HTTPError as e:
            raise NvdaVmError(f"nao consegui falar com a VM em {base} ({type(e).__name__}). Ela esta ligada, com o agente rodando e o firewall liberado?") from e
        if resp.status_code == 401:
            raise NvdaVmError("a VM recusou o token (A11Y_MCP_NVDA_TOKEN).")
        if resp.status_code == 409:
            raise NvdaVmError("a VM ja esta fazendo um teste; espere terminar e tente de novo.")
        if resp.status_code != 202:
            raise NvdaVmError(f"a VM recusou o pedido: {resp.text[:200]}")
        job = resp.json()["id"]
        return await _wait(client, base, job, poll)


async def _wait(client: httpx.AsyncClient, base: str, job: str, poll: float) -> dict[str, Any]:
    """Consulta o andamento ate acabar. Nao ha prazo total: so desiste se a VM parar de dar sinal ou ficar sem progresso
    por muito mais tempo do que o maior intervalo ja visto entre dois avancos (limite que cresce com o ritmo real)."""
    steps, last_change = -1, time.monotonic()
    longest_gap, interval, offline_since = 0.0, poll, None
    while True:
        try:
            resp = await client.get(f"{base}/percorrer/{job}")
            offline_since = None
        except httpx.HTTPError as e:
            offline_since = offline_since or time.monotonic()
            if time.monotonic() - offline_since > max(OFFLINE_FLOOR_S, 10 * longest_gap):
                raise NvdaVmError(f"a VM parou de responder ({type(e).__name__}).") from e
            await asyncio.sleep(interval)
            continue
        if resp.status_code != 200:
            raise NvdaVmError(f"a VM devolveu {resp.status_code} ao consultar o teste: {resp.text[:200]}")
        data = resp.json()
        if data.get("estado") == "concluido":
            result = data.get("resultado")
            if not isinstance(result, dict):
                raise NvdaVmError("a VM terminou sem devolver resultado.")
            return result
        now = time.monotonic()
        if data.get("passos", 0) != steps:
            longest_gap = max(longest_gap, now - last_change if steps >= 0 else 0.0)
            steps, last_change = data.get("passos", 0), now
            interval = poll
        elif now - last_change > max(STALL_FLOOR_S, 5 * longest_gap):
            raise NvdaVmError(f"o teste na VM ficou sem progresso por {int(now - last_change)} s (parou no passo {steps}).")
        else:
            interval = min(interval * 1.5, 5.0)
        await asyncio.sleep(interval)


def facts(result: dict[str, Any], url: str) -> dict[str, Any]:
    """Moldura em fatos: o que o NVDA falou, e de onde veio (para ninguem confundir com o NVDA da pessoa)."""
    return {
        "source": "NVDA real (Guidepup) numa VM Windows",
        "url": url,
        "tab_walk": result.get("tab", []),
        "reading_mode": result.get("leitura", []),
        "error": result.get("erro"),
        "muted": result.get("silencio"),
        "notes": [
            "A fala e' a do NVDA da VM: a voz, a velocidade e os complementos NAO sao os do NVDA da pessoa.",
            "O teste so aperta Tab e navega no modo leitura; nao ativa botoes nem envia formularios.",
            "Cobre estreito e fundo (cerca de 6 de 55 criterios WCAG sozinho): complementa o teste como usuario, nao o substitui.",
        ],
    }
