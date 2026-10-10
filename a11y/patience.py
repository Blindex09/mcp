"""Paciencia adaptativa: nenhum relogio fixo mata trabalho em andamento.

Quando algo demora, tenta de novo com MAIS tempo (mesma acao, mesmo nivel de raciocinio) em vez de desistir. O que encerra e
estar travado (sem progresso), o cancelamento pela pessoa ou o orcamento que ela configurou; nunca um numero fixo de segundos.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

T = TypeVar("T")

PATIENCE_FACTOR = 3  # cada nova tentativa espera esse tanto a mais
PATIENCE_ATTEMPTS = 5  # 1x, 3x, 9x, 27x, 81x: na pratica sem teto; quem encerra e' o cancelamento


def _timeout_types() -> tuple[type[BaseException], ...]:
    types: list[type[BaseException]] = [TimeoutError, asyncio.TimeoutError]
    try:
        from playwright.async_api import TimeoutError as PlaywrightTimeout

        types.append(PlaywrightTimeout)
    except ImportError:  # playwright ainda nao instalado
        pass
    try:
        import httpx

        types.append(httpx.TimeoutException)
    except ImportError:
        pass
    return tuple(types)


async def patient(factory: Callable[[float], Awaitable[T]], first: float, attempts: int = PATIENCE_ATTEMPTS) -> T:
    """Chama factory(timeout); se estourar o tempo, repete com timeout maior. So a ULTIMA falha sobe."""
    timeouts = _timeout_types()
    wait = first
    last: BaseException | None = None
    for i in range(max(1, attempts)):
        try:
            return await factory(wait)
        except timeouts as e:
            last = e
            wait *= PATIENCE_FACTOR
            if i == attempts - 1:
                break
    assert last is not None
    raise last


async def with_patience(coro_factory: Callable[[], Awaitable[Any]], first: float, attempts: int = PATIENCE_ATTEMPTS) -> Any:
    """Variante para trabalho que nao aceita timeout proprio: envolve em asyncio.wait_for com espera crescente."""

    async def run(t: float) -> Any:
        return await asyncio.wait_for(coro_factory(), timeout=t)

    return await patient(run, first, attempts)
