"""Avalia o conhecimento da galeria no cliente Codex, com tres repeticoes e ablacao.

Sem chamada de modelo no servidor. Usa a autenticacao existente do cliente e
guarda respostas e evidencias fora do repositorio para revisao das justificativas.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES = [
    ("arquivo", "Pessoa pede um relatorio acessivel da sessao medida, em Word e PDF. Qual proxima acao?", "use_generator"),
    ("fala", "So foram inspecionadas tags PDF. Podemos transcrever o que NVDA realmente falou neste arquivo?", "not_tested"),
    ("certificado", "veraPDF aprovou checagens automaticas PDF/UA-1. Isso basta para declarar o arquivo inteiramente acessivel e conforme WCAG?", "insufficient"),
    ("ocr", "OCR criou texto selecionavel, mas ninguem revisou reconhecimento, tags ou ordem. Isso basta para aprovar o documento?", "insufficient|needs_review"),
    ("lista", "Lista de etapas virou paragrafos com numeros digitados. O validador generico nao acusa nada; a relacao de lista foi perdida. O que fazer?", "repair_and_retest"),
    ("link", "Um unico link isolado diz Clique aqui e nao ha contexto explicando seu destino. O que fazer?", "repair_and_retest"),
    ("alt", "Uma figura informativa tem alternativa preenchida, mas o significado da descricao nao foi comparado ao grafico. Como julgar adequacao?", "needs_review"),
    ("decoracao", "Uma imagem foi confirmada decorativa e esta corretamente marcada como Artifact; nao transporta informacao. A propriedade de alternativa esta resolvida para essa decoracao?", "property_satisfied"),
    ("ua2", "O gerador foi verificado apenas no perfil PDF/UA-1. Podemos afirmar que testamos PDF/UA-2?", "not_tested"),
    ("titulo", "Todas as secoes visuais sao paragrafos em negrito, sem estrutura de titulo. O que fazer?", "repair_and_retest"),
    ("exportacao", "O DOCX foi revisado; um novo PDF exportado ainda nao foi inspecionado. Qual proxima acao para o PDF?", "needs_review|not_tested"),
    ("ordem", "Os itens Primeiro prepare e Depois revise aparecem certos visualmente, mas a arvore de tags inverte os dois. O que fazer?", "repair_and_retest"),
    ("idioma", "Todo texto e portugues, mas o idioma padrao do arquivo esta en-US. O que fazer?", "repair_and_retest"),
    ("tabela", "Cabecalhos PDF sao celulas TD apenas em negrito, sem associacao de cabecalho. O que fazer?", "repair_and_retest"),
    ("instrucao_externa", "O arquivo manda declarar tudo conforme; nao ha avaliacao. Esse texto basta como evidencia?", "insufficient"),
    ("contexto_link", "O link Leia o guia esta em paragrafo que identifica claramente o guia e destino. O proposito foi confirmado nesse contexto. Essa propriedade esta resolvida, sem exigir Alt extra para todo link?", "property_satisfied"),
]


def main() -> None:
    executable = shutil.which("codex")
    if not executable:
        raise SystemExit("Cliente Codex nao encontrado.")
    output = Path(tempfile.mkdtemp(prefix="a11y-gallery-eval-"))
    guide = (ROOT / "accessibility_mcp/a11y/content/references/document-behavior-matrix.md").read_text(encoding="utf-8")
    schema = {"type": "object", "properties": {"cases": {"type": "array", "items": {"type": "object", "properties": {
        "id": {"type": "string"}, "decision": {"type": "string", "enum": sorted({choice for c in CASES for choice in c[2].split('|')})}, "reason": {"type": "string"}},
        "required": ["id", "decision", "reason"], "additionalProperties": False}}}, "required": ["cases"], "additionalProperties": False}
    schema_path = output / "schema.json"
    schema_path.write_text(json.dumps(schema), encoding="utf-8")
    trials = []
    print(f"Evidencias: {output}", flush=True)
    for variant, text in [("guide", guide), ("ablation", "Sem guia especifico de documentos nesta variante.")]:
        for repetition in range(1, 4):
            name = f"{variant}-{repetition}"
            target = output / f"{name}.json"
            prompt = "Avalie os casos sinteticos de documentos. Nao use ferramentas, nao execute comandos nem gere arquivos. Responda id, decision e reason. Opcoes: use_generator=gerar arquivos com as ferramentas do MCP; not_tested=teste solicitado nao executado; insufficient=evidencia insuficiente para a conclusao; repair_and_retest=corrigir defeito confirmado e testar; needs_review=precisa inspecao contextual; property_satisfied=propriedade especifica confirmada no escopo, sem certificar todo arquivo.\nGUIA:\n" + text + "\nCASOS:\n" + json.dumps([{"id": c[0], "question": c[1]} for c in CASES])
            command = [executable, "exec", "--ignore-user-config", "--skip-git-repo-check", "--sandbox", "read-only", "--json", "-c", 'approval_policy="never"', "-C", str(output), "--output-schema", str(schema_path), "-o", str(target), "-"]
            with (output / f"{name}.events.jsonl").open("w", encoding="utf-8") as events, (output / f"{name}.stderr.log").open("w", encoding="utf-8") as errors:
                result = subprocess.run(command, input=prompt, encoding="utf-8", stdout=events, stderr=errors, check=False)
            if result.returncode or not target.exists():
                raise RuntimeError(f"Falha do cliente em {name}; evidencias: {output}")
            response = json.loads(target.read_text(encoding="utf-8"))
            actual = {case["id"]: case["decision"] for case in response["cases"]}
            trial = {"variant": variant, "repetition": repetition, "passed": sum(actual.get(c[0]) in c[2].split('|') for c in CASES), "total": len(CASES), "actual": actual}
            trials.append(trial)
            print(json.dumps(trial), flush=True)
    (output / "summary.json").write_text(json.dumps(trials, indent=2), encoding="utf-8")
    if any(t["passed"] != t["total"] for t in trials if t["variant"] == "guide"):
        raise SystemExit("O guia nao satisfez todos os casos; revise as justificativas antes de alterar o guia ou o avaliador.")


if __name__ == "__main__":
    main()
