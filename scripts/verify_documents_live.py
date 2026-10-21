"""Verificacao real de geracao, validacao e download pelo protocolo MCP.

Uso: python scripts/verify_documents_live.py
Os arquivos ficam na pasta do usuario; nenhum artefato descartavel entra no projeto.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import sys
import tempfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent


async def main() -> None:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "mcp_server.py")], env=env)
    with tempfile.TemporaryDirectory(prefix="a11y-documents-live-") as temp:
        workspace = Path(temp)
        Image.new("RGB", (300, 100), "navy").save(workspace / "figura.png")
        async with stdio_client(params) as (r, w), ClientSession(r, w) as client:
            await client.initialize()

            async def call(name: str, **args: object) -> dict:
                result = await client.call_tool(name, args)
                assert not result.isError, result
                data = json.loads(result.content[0].text)
                assert "error" not in data, data
                return data

            await call("a11y_set_workspace", path=temp)
            records = []
            for title, blocks in [
                ("Guia de testes acessíveis", [
                    {"kind": "paragraph", "text": "Guia para testar a navegação por teclado e registrar evidências."},
                    {"kind": "heading", "text": "Procedimento"},
                    {"kind": "list", "ordered": True, "items": ["Percorrer o formulário", "Registrar foco e anúncios"]},
                    {"kind": "list", "ordered": True, "items": ["Repetir após a correção", "Comparar as evidências"]},
                    {"kind": "table", "text": "Registro dos testes", "headers": ["Teste", "Situação"], "rows": [["Teclado", "Não avaliado"], ["NVDA", "Não executado"]]},
                    {"kind": "image", "source": "figura.png", "alt": "Retângulo azul usado como figura de demonstração"},
                    {"kind": "link", "text": "Referências de acessibilidade do W3C", "url": "https://www.w3.org/WAI/"},
                ]),
                ("Registro de testes em várias páginas", [
                    {"kind": "paragraph", "text": "Registro de testes de navegação em páginas e formulários."},
                    {"kind": "table", "text": "Acompanhamento dos testes", "headers": ["Caso", "Procedimento", "Situação"],
                     "rows": [[str(i), f"Verificar o foco no campo {i} e registrar o resultado observado.", "Não avaliado"] for i in range(1, 65)]},
                ]),
            ]:
                created = await call("a11y_create_document", document={"title": title, "language": "pt-BR", "author": "Equipe de acessibilidade", "blocks": blocks})
                for output in created["files"]:
                    check = await call("a11y_validate_document", path=output["path"])
                    assert check["status"] == "automated_checks_passed", check
                    if check["format"] == "pdf":
                        assert check["pdf_ua"]["status"] == "passed", check
                    resource = await client.read_resource(output["uri"])
                    blob = base64.b64decode(resource.contents[0].blob)
                    assert blob == Path(output["path"]).read_bytes()
                records.append(created)
            await call("a11y_open", html='<html lang="pt-BR"><title>Cadastro</title><main><h1>Cadastro</h1><label>Nome<input></label><button>Enviar</button></main></html>', persona="keyboard")
            try:
                await call("a11y_page_map")
                await call("a11y_probe", kind="tab_walk")
                report = await call("a11y_create_report")
                assert len(report["files"]) == 2
                for output in report["files"]:
                    assert output["validation"]["status"] == "automated_checks_passed", output
                    if output["path"].endswith(".pdf"):
                        assert output["validation"]["pdf_ua"]["status"] == "passed", output
                records.append(report)
            finally:
                await call("a11y_close")
            home = Path(os.environ.get("A11Y_MCP_HOME", str(Path.home() / ".a11y-mcp")))
            evidence = home / "documents" / "live-verification.json"
            evidence.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps({"generated": len(records), "files": [f["path"] for record in records for f in record["files"]], "evidence": str(evidence)}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
