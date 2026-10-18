"""Observabilidade (regra 18): cada ferramenta vira um span `execute_tool`, sem argumentos nem resultados, sem quebrar nada."""

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from accessibility_mcp import telemetry


@pytest.fixture
def exporter():
    exp = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exp))
    trace.set_tracer_provider(provider) if trace.get_tracer_provider().__class__.__name__ == "ProxyTracerProvider" else None
    telemetry._configured = True
    original = trace.get_tracer
    trace.get_tracer = lambda *_a, **_k: provider.get_tracer("teste")  # type: ignore[assignment]
    yield exp
    trace.get_tracer = original  # type: ignore[assignment]


async def test_ferramenta_vira_span_com_nome_e_operacao(exporter):
    async def a11y_exemplo(segredo: str) -> str:
        return "resultado com dado da pessoa"

    resposta = await telemetry.traced("a11y_exemplo", a11y_exemplo)("senha-da-pessoa")
    assert resposta == "resultado com dado da pessoa"
    (span,) = exporter.get_finished_spans()
    assert span.name == "execute_tool a11y_exemplo"
    assert span.attributes["gen_ai.operation.name"] == "execute_tool" and span.attributes["gen_ai.tool.name"] == "a11y_exemplo"


async def test_argumentos_e_resultados_nunca_entram_no_span(exporter):
    async def a11y_exemplo(segredo: str) -> str:
        return "resultado-sigiloso"

    await telemetry.traced("a11y_exemplo", a11y_exemplo)("senha-da-pessoa")
    texto = repr([dict(s.attributes) for s in exporter.get_finished_spans()])
    assert "senha-da-pessoa" not in texto and "resultado-sigiloso" not in texto


async def test_erro_da_ferramenta_sobe_igual_e_fica_marcado(exporter):
    async def a11y_quebra() -> str:
        raise RuntimeError("falhou")

    with pytest.raises(RuntimeError):
        await telemetry.traced("a11y_quebra", a11y_quebra)()
    assert exporter.get_finished_spans()[0].attributes["error.type"] == "RuntimeError"


def test_a_assinatura_e_preservada_para_o_esquema_do_fastmcp():
    import inspect

    async def a11y_exemplo(url: str, limite: int = 3) -> str:
        return url

    assert inspect.signature(telemetry.traced("x", a11y_exemplo)) == inspect.signature(a11y_exemplo)


def test_todas_as_ferramentas_do_servidor_passam_pelo_span():
    import asyncio

    from accessibility_mcp.server import mcp

    tools = asyncio.run(mcp.list_tools())
    assert len(tools) >= 40
    assert all(getattr(mcp._tool_manager._tools[t.name].fn, "__wrapped__", None) is not None for t in tools)
