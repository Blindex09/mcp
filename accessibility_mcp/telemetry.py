"""Observabilidade das ferramentas com OpenTelemetry, nas convencoes de GenAI (regra 18).

Cada chamada de ferramenta vira um span `execute_tool <nome>` com `gen_ai.operation.name`, `gen_ai.tool.name` e o resultado
(ok ou erro). Os argumentos e os resultados NUNCA entram no span: podem ter dados da pessoa e o registro nao guarda segredo.
Sem o pacote do OpenTelemetry ou sem exportador configurado e como se nao existisse: nada muda para quem nao usa.

As convencoes de GenAI do OpenTelemetry estao em estagio Development: os nomes de atributo podem mudar.
Ligar: instalar `opentelemetry-sdk` e `opentelemetry-exporter-otlp` e definir OTEL_EXPORTER_OTLP_ENDPOINT.
"""

from __future__ import annotations

import functools
import inspect
import logging
import os
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

SERVICE = "accessibility-mcp"
_configured = False


def _tracer() -> Any | None:
    """O tracer, se o OpenTelemetry existir. Configura o exportador OTLP na primeira vez se houver endpoint."""
    global _configured
    try:
        from opentelemetry import trace
    except ImportError:
        return None
    if not _configured:
        _configured = True
        endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
        if endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                    OTLPSpanExporter,
                )
                from opentelemetry.sdk.resources import Resource
                from opentelemetry.sdk.trace import TracerProvider
                from opentelemetry.sdk.trace.export import BatchSpanProcessor

                provider = TracerProvider(resource=Resource.create({"service.name": os.environ.get("OTEL_SERVICE_NAME", SERVICE)}))
                provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
                trace.set_tracer_provider(provider)
                logger.info("OpenTelemetry ligado -> %s", endpoint)
            except Exception as exc:  # noqa: BLE001 - telemetria nunca derruba o servidor
                logger.warning("OpenTelemetry nao configurado (%s); seguindo sem telemetria", exc)
    return trace.get_tracer(SERVICE)


def traced(name: str, fn: Callable[..., Any]) -> Callable[..., Any]:
    """Embrulha uma ferramenta num span. Preserva a assinatura (o FastMCP monta o esquema dela)."""
    if not inspect.iscoroutinefunction(fn):
        return fn

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        tracer = _tracer()
        if tracer is None:
            return await fn(*args, **kwargs)
        with tracer.start_as_current_span(
            f"execute_tool {name}", attributes={"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": name}
        ) as span:
            try:
                return await fn(*args, **kwargs)
            except BaseException as exc:
                span.set_attribute("error.type", type(exc).__name__)
                raise

    return wrapper


def instrument(mcp: Any) -> None:
    """Faz toda ferramenta registrada depois daqui passar por `traced`. Chamar antes de registrar as ferramentas."""
    original = mcp.tool

    def tool(*targs: Any, **tkwargs: Any) -> Callable[[Callable[..., Any]], Any]:
        decorator = original(*targs, **tkwargs)

        def apply(fn: Callable[..., Any]) -> Any:
            return decorator(traced(tkwargs.get("name") or fn.__name__, fn))

        return apply

    mcp.tool = tool
