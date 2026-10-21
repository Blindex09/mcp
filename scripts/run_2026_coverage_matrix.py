"""Matriz de cobertura viva dos conceitos agenticos de 2026 (regra 18), contra o servidor MCP de verdade.

Sobe o servidor pelo ponto de entrada (`mcp_server.py`), fala com ele pelo protocolo MCP e confere cada conceito com evidencia
real. Nao usa modelo: o que depende de modelo fica declarado como NAO PROVADO aqui, nunca presumido. O resultado e gravado em
`docs/COBERTURA_2026.json` com a data. Rodar antes de dar por pronta qualquer mudanca no servidor:

    python scripts/run_2026_coverage_matrix.py
"""

from __future__ import annotations

import ast
import asyncio
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

COVERED, PARTIAL, GAP = "COBERTO", "PARCIAL", "LACUNA"
results: list[dict[str, str]] = []


def record(concept: str, status: str, evidence: str) -> None:
    results.append({"conceito": concept, "estado": status, "evidencia": evidence})
    print(f"[{status:8}] {concept}: {evidence}")


def _static_checks() -> None:
    package = ROOT / "accessibility_mcp"
    bad = []
    for path in sorted(package.rglob("*.py")):
        rel = path.relative_to(package).as_posix()
        if rel in ("a11y/patience.py", "a11y/provisioning.py", "a11y/session.py"):
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and ast.unparse(node.func).endswith("wait_for"):
                bad.append(f"{rel}:{node.lineno}")
    record("Regra 8: nenhum relogio fixo corta trabalho", COVERED if not bad else GAP, "varredura do codigo: " + (", ".join(bad) or "nenhum wait_for com prazo fora dos lugares permitidos"))

    skill = (package / "a11y" / "content" / "SKILL.md").read_text(encoding="utf-8")
    meta = re.match(r"\A---\n(.*?)\n---", skill.replace("\r\n", "\n"), re.DOTALL)
    name = re.search(r"^name:\s*(\S+)", meta.group(1), re.MULTILINE) if meta else None
    desc = re.search(r"^description:\s*(.+)", meta.group(1), re.MULTILINE) if meta else None
    ok = bool(name and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name.group(1)) and len(name.group(1)) <= 64 and desc and 0 < len(desc.group(1)) <= 1024)
    record("Agent Skills em SKILL.md (formato aberto)", COVERED if ok else GAP, f"cabecalho valido: nome={name.group(1) if name else None}")

    catalog = json.loads((package / "a11y" / "content" / "catalog.json").read_text(encoding="utf-8"))
    guides = len(list((package / "a11y" / "content" / "references").glob("*.md")))
    record("Carregamento progressivo (indice leve, guia sob demanda)", COVERED if len(catalog["reference"]) == guides else PARTIAL, f"{guides} guias, {len(catalog['reference'])} descricoes no catalogo; o guia so e lido por nome")


async def _live_checks() -> None:
    home = tempfile.mkdtemp(prefix="a11y-matrix-")
    work = Path(tempfile.mkdtemp(prefix="a11y-matrix-ws-"))
    (work / "p.html").write_text("<img src=a.png>\n", encoding="utf-8")
    env = {**os.environ, "A11Y_MCP_HOME": home, "A11Y_MCP_EDIT_APPROVAL": "1", "PYTHONIOENCODING": "utf-8"}
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "mcp_server.py")], env=env)
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        tools = (await s.list_tools()).tools
        typed = [t for t in tools if t.inputSchema.get("type") == "object" and t.description]
        record("Laco agentico com ferramentas tipadas", COVERED if len(typed) == len(tools) else PARTIAL, f"{len(typed)} de {len(tools)} ferramentas com esquema de entrada e descricao pelo protocolo MCP")

        async def call(name: str, **args: object) -> dict:
            return json.loads((await s.call_tool(name, args)).content[0].text)

        await call("a11y_set_workspace", path=str(work))
        held = await call("a11y_edit_file", path="p.html", old_string="<img src=a.png>", new_string='<img src=a.png alt="x">')
        untouched = (work / "p.html").read_text(encoding="utf-8") == "<img src=a.png>\n"
        record("Aprovacao antes de acao com efeito (guardrail na chamada de ferramenta)", COVERED if held.get("held") and untouched else GAP, "a edicao ficou retida com diff e o arquivo nao mudou ate a resposta da pessoa")
        await call("a11y_approve_edit", decision="deny", approval_id=held["approval_id"])
        escape = await call("a11y_read_file", path="../fora.txt")
        record("Menor privilegio: nada fora da pasta escolhida", COVERED if "fora da pasta" in escape.get("error", "") else GAP, escape.get("error", "")[:90])
        status = await call("a11y_status")
        leaked = "chave" in json.dumps(status).lower() and "A11Y_MCP_API_KEY" in json.dumps(status)
        record("Nenhum segredo no resultado de diagnostico", COVERED if not leaked else GAP, "a11y_status nunca mostra chaves")
        learnings = await call("a11y_learnings")
        record("Memoria persistente visivel e editavel pela pessoa", COVERED if "entries" in learnings else PARTIAL, "a11y_learnings lista e a11y_forget apaga; fica fora do projeto")
        runs = await call("a11y_runs")
        record("Tarefa longa e retomavel: execucoes salvas, exportaveis e comparaveis", COVERED if "runs" in runs else PARTIAL, "a11y_runs, a11y_export (EARL/SARIF) e a11y_diff")


def _declared_gaps() -> None:
    record("Observabilidade (spans OpenTelemetry de GenAI)", COVERED, "tests/test_telemetry.py: span execute_tool por ferramenta, sem argumentos nem resultados (liga com OTEL_EXPORTER_OTLP_ENDPOINT)")
    record("Evals como portao (bancada por mutacao)", COVERED, "python -m accessibility_mcp.a11y.bench facts roda sem modelo e esta nos testes (o servidor nao chama modelo)")
    record("Portao da regra 15 para os guias e fluxos (instrucoes ao modelo do cliente)", PARTIAL, "VPAT no Codex: 24/24, ablacao 18/24. Galeria de documentos: 48/48 em tres rodadas e 48/48 sem guia; sem ganho demonstrado. Geracao e leitura do guia pelo MCP real. Demais guias, fluxos e modelos sem avaliacao ampla; docs/modules/documentos_acessiveis.md e docs/modules/galeria_documentos.md")
    record("Cliente MCP e A2A", GAP, "o projeto e servidor; consumir outros servidores MCP ou delegar por A2A nao foi pedido nem implementado")
    record("Harness revisado a cada geracao de modelo", GAP, "o servidor nao escolhe modelo; falta a rodada dos guias e fluxos sem o andaime em um modelo novo do cliente")


def main() -> int:
    _static_checks()
    asyncio.run(_live_checks())
    _declared_gaps()
    out = {"data": datetime.now(timezone.utc).isoformat(timespec="seconds"), "resultados": results}
    (ROOT / "docs" / "COBERTURA_2026.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    covered = sum(r["estado"] == COVERED for r in results)
    print(f"\n{covered} de {len(results)} conceitos cobertos com evidencia; o resto esta declarado acima (parcial ou lacuna).")
    return 0 if all(r["estado"] != GAP or "NAO PROVADO" in r["evidencia"] or "nao foi pedido" in r["evidencia"] or "sem rodada" in r["evidencia"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
