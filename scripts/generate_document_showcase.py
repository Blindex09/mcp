"""Gera demonstracao Word/PDF pelo MCP real e entrega copias na pasta solicitada.

Uso: python scripts/generate_document_showcase.py --output-dir CAMINHO
Usa somente dados didaticos e imagem local criada para o exemplo. Nao sobrescreve arquivos.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent


def copy_artifact(source: Path, target: Path) -> None:
    with source.open('rb') as original, target.open('xb') as copy:
        shutil.copyfileobj(original,copy)


def content(image: str) -> dict:
    return {"title":"Demonstração de documento acessível", "language":"pt-BR", "author":"Projeto MCP de acessibilidade", "toc":True, "blocks":[
        {"kind":"paragraph", "text":"Este documento demonstra navegação, listas, tabelas, imagens e campos preenchíveis gerados pelo MCP. Os dados são didáticos. Use o sumário para chegar às seções e preencha os controles no aplicativo de sua preferência. A validação automática não substitui revisão com tecnologia assistiva."},
        {"kind":"heading", "id":"orientacoes", "text":"Como usar este exemplo"},
        {"kind":"list", "ordered":True, "items":["Ative uma entrada do sumário para conferir o destino.","Percorra os títulos e leia os dados da tabela.","Preencha o nome, escolha uma área e alterne a caixa de seleção.","Salve uma cópia e reabra para conferir os valores."]},
        {"kind":"paragraph", "text":"No Word, atualize o campo do sumário depois de alterar títulos ou páginas. O PDF tem sumário clicável e marcadores. Os comandos e anúncios variam entre aplicativos e leitores; este exemplo não contém envio de dados nem macros."},
        {"kind":"heading", "id":"dados", "text":"Dados e imagem de exemplo"},
        {"kind":"table", "text":"Participação fictícia nos testes", "headers":["Mês","Participantes"], "rows":[["Setembro","12"],["Outubro","18"]]},
        {"kind":"image", "source":image, "alt":"Participação fictícia nos testes: 12 pessoas em setembro e 18 em outubro. Os mesmos valores estão na tabela anterior."},
        {"kind":"heading", "id":"formulario", "text":"Formulário para experimentar"},
        {"kind":"paragraph", "text":"Campos com a indicação obrigatório devem ser preenchidos para este exercício. No Word essa indicação é textual; no PDF há também a propriedade Required. O exemplo não verifica entradas nem envia respostas automaticamente."},
        {"kind":"field", "field_name":"nome", "field_type":"text", "text":"Nome completo", "help_text":"Digite um nome de teste, sem informações pessoais reais.", "required":True},
        {"kind":"field", "field_name":"area", "field_type":"choice", "text":"Área de interesse", "help_text":"Escolha uma das três opções disponíveis.", "options":["Web","Documentos","Ambos"], "value":"Documentos"},
        {"kind":"field", "field_name":"participar", "field_type":"checkbox", "text":"Quero participar da demonstração", "help_text":"Marque ou desmarque para experimentar a alteração de estado.", "checked":False},
        {"kind":"field", "field_name":"observacoes", "field_type":"text", "text":"Observações", "help_text":"Escreva um comentário curto sobre o teste.", "multiline":True},
        {"kind":"heading", "id":"fontes", "text":"Fontes e revisão"},
        {"kind":"link", "text":"Orientações da Microsoft sobre formulários no Word", "url":"https://support.microsoft.com/en-us/word/create-a-form-in-word-that-users-can-complete-or-print"},
        {"kind":"link", "text":"Técnica W3C sobre nome, papel e valor em formulários PDF", "url":"https://www.w3.org/WAI/WCAG22/Techniques/pdf/PDF12"},
        {"kind":"link", "text":"Voltar às orientações deste documento", "url":"#orientacoes"},
        {"kind":"paragraph", "text":"Confira nomes dos campos, instruções, valores, estados, ordem de leitura e navegação no aplicativo. A captura de fala real do NVDA neste documento ainda não foi executada. Não há garantia de comportamento idêntico em todos os leitores."},
    ]}


async def main(output_dir: Path) -> None:
    if not output_dir.is_dir():
        raise ValueError("A pasta de destino precisa existir.")
    with tempfile.TemporaryDirectory(prefix="a11y-showcase-") as temporary:
        workspace = Path(temporary)
        image = Image.new('RGB',(700,220),'white')
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default(size=24)
        for y,name,width,value in [(40,'Setembro',240,'12'),(125,'Outubro',360,'18')]:
            draw.text((10,y),name,font=font,fill='black')
            draw.rectangle((160,y,160+width,y+38),fill='#173c63')
            draw.text((175+width,y),value,font=font,fill='black')
        image.save(workspace/'grafico.png')
        parameters = StdioServerParameters(command=sys.executable,args=[str(ROOT/'mcp_server.py')],cwd=str(ROOT),env=dict(os.environ))
        async with stdio_client(parameters) as (read,write), ClientSession(read,write) as client:
            await client.initialize()

            async def call(name: str, arguments: dict) -> dict:
                result = await client.call_tool(name,arguments)
                text = ''.join(block.text for block in result.content if block.type == 'text')
                parsed = json.loads(text)
                if result.isError or 'error' in parsed:
                    raise RuntimeError(text)
                return parsed
            await call('a11y_set_workspace',{'path':str(workspace)})
            result = await call('a11y_create_document',{'document':content('grafico.png'),'formats':'both'})
            copies = []
            stem = 'Demonstracao_acessivel_MCP_' + datetime.now(timezone.utc).astimezone().strftime('%Y%m%d_%H%M%S')
            for output in result['files']:
                source = Path(output['path'])
                check = await call('a11y_validate_document',{'path':str(source)})
                if check['status'] != 'automated_checks_passed':
                    raise RuntimeError(f'Verificacao pendente: {json.dumps(check,ensure_ascii=False)}')
                target = output_dir/(stem+source.suffix)
                await asyncio.to_thread(copy_artifact,source,target)
                copies.append({'path':str(target),'validation':check})
            manifest = Path(result['files'][0]['path']).parent/'downloads.json'
            manifest.write_text(json.dumps(copies,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps({'files':[entry['path'] for entry in copies],'evidence':str(manifest)},ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir',type=Path,required=True)
    asyncio.run(main(parser.parse_args().output_dir.expanduser().resolve()))
