"""Dados de auditoria declarados pelo avaliador, sem inferir resultados."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import wcag


class CriterionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    criterion: str
    outcome: Literal["passed", "failed", "cantTell", "inapplicable", "untested"]
    complete: bool = False
    scope: str = Field(min_length=1)
    evidence: list[str] = Field(default_factory=list)
    remarks: str = Field(min_length=1)

    @model_validator(mode="after")
    def check_result(self) -> CriterionResult:
        if self.criterion not in wcag.CRITERIA:
            raise ValueError("Critério WCAG inexistente.")
        if not self.scope.strip() or not self.remarks.strip():
            raise ValueError("Informe escopo e justificativa.")
        if self.outcome in ("passed", "failed", "inapplicable") and not any(item.strip() for item in self.evidence):
            raise ValueError("Resultado conclusivo exige evidência.")
        if self.outcome in ("passed", "inapplicable") and not self.complete:
            raise ValueError("Aprovação ou inaplicabilidade exige cobertura completa declarada.")
        return self


class FindingDetails(BaseModel):
    model_config = ConfigDict(extra="forbid")
    finding_id: str
    preconditions: str = ""
    reproduction_steps: list[str] = Field(default_factory=list)
    reproduction_steps_visual: list[str] = Field(default_factory=list, description="Percurso visual observado: início, alvo identificado por texto e contexto, ações e verificação do defeito.")
    reproduction_steps_keyboard: list[str] = Field(default_factory=list, description="Percurso de teclado observado: início, alvo e contexto, teclas realmente usadas e resultado a conferir; sem contagem de Tab inventada.")
    reproduction_steps_screen_reader: list[str] = Field(default_factory=list, description="Percurso realmente executado com leitor de tela: ambiente, modo/comandos registrados, alvo e resultado; não deduza fala da árvore de acessibilidade.")
    reproduction_steps_screen_reader_proposed: list[str] = Field(default_factory=list, description="Orientação ainda não executada com leitor: indique leitor, navegador, modo, ponto inicial, comandos documentados e alvo com nome/papel observados. Não é evidência de teste; não invente fala nem contagens.")
    expected_result: str = Field(default="", description="Comportamento ou propriedade que deveria ser observado no elemento, na condição de teste registrada.")
    actual_result: str = ""
    evidence: str = ""
    environment: str = ""
    operating_system: str = ""
    browsers: str = ""
    owner: str = ""
    due_date: str = ""
    ticket: str = ""
    retest: str = ""
    code_snippet: str = Field(default="", description="Código real do problema (HTML, JS ou CSS), copiado da página ou do arquivo observado, com a origem (URL do arquivo e posição aproximada). Nunca invente código: sem trecho observado, deixe vazio.")
    fixed_code: str = Field(default="", description="Código corrigido sugerido (HTML, JS ou CSS), em campo separado do código problemático, escrito a partir do trecho observado. É sugestão: diga que não foi aplicada nem testada no site.")
    design_impact: str = Field(default="", description="Impacto da correção sugerida no design e no layout do site: 'Nenhum' (correção invisível, como nome acessível, ordem de foco, texto alternativo) ou 'Visual mínimo' com a descrição exata do que muda (por exemplo, cor do texto de #8A8A8A para #6B6B6B, dentro da paleta do site). Nunca proponha trocar layout, estrutura ou identidade visual.")
    screen: str = Field(default="", description="Nome da tela ou etapa em que o problema ocorre (vira uma aba da planilha, por exemplo 'Home', 'Cotação 3 - Datas e cidadania'). Use 'Todas as telas' para o que se repete em toda a página. Sem nome, a aba é derivada da URL.")
    detected_on: str = ""
    fix_applied: str = ""
    page_title: str = ""
    problem_location: str = Field(default="", description=(
        "Local exato da barreira em linguagem humana: página, seção ou formulário, tipo de elemento "
        "e nome/texto do link, título ou campo. Diferencie elementos repetidos pelo contexto. "
        "Use fatos observados; não descreva aqui a tarefa nem os passos de reprodução."))
    journey: str = ""
    page_area: str = ""
    testing_method: str = ""
    criterion_rationale: str = Field(default="", description="Relacione o resultado observado ao requisito WCAG: explique por que os fatos registrados o descumprem. Repetir apenas o resultado esperado não justifica a falha; não invente evidência.")
    status: Literal["", "Aberta", "Em correção", "Aguardando reteste", "Validada no reteste", "Reaberta", "Rejeitada", "A confirmar"] = ""
    retest_date: str = ""
    retest_version: str = ""
    retest_evaluator: str = ""
    retest_result: str = ""
    retest_evidence: str = ""


class ScopeSample(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str
    title: str = ""
    journey: str = ""
    selection_reason: str = ""
    testing_method: str = ""
    environment: str = ""


class ScreenItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item: str
    detail: str = ""


class ScreenNote(BaseModel):
    """Tela testada que vira aba própria na planilha, mesmo sem achados (o que foi testado, não testado e observado)."""
    model_config = ConfigDict(extra="forbid")
    name: str
    description: str = ""
    items: list[ScreenItem] = Field(default_factory=list)


class ReportContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    screens: list[ScreenNote] = Field(default_factory=list, description="Telas testadas, na ordem das abas da planilha. Uma aba por tela; telas sem achado listam o que foi testado, o que não foi testado e o que foi observado.")
    evaluator: str = ""
    commissioner: str = ""
    product_version: str = ""
    report_version: str = ""
    evaluation_period: str = ""
    methodology: str = ""
    environment: str = ""
    operating_system: str = ""
    browsers: str = ""
    sampling: str = ""
    complete_processes: str = ""
    exclusions: str = ""
    product_name: str = ""
    product_description: str = ""
    report_date: str = ""
    report_modified: str = ""
    evaluation_goal: str = ""
    evaluator_organization: str = ""
    evaluator_contact: str = ""
    evaluator_expertise: str = ""
    content_languages: str = ""
    evaluator_languages: str = ""
    conformance_target: str = ""
    accessibility_support_baseline: str = ""
    technologies_relied_upon: str = ""
    evaluation_tools: str = ""
    product_exploration: str = ""
    random_sample: str = ""
    monitoring_plan: str = ""
    samples: list[ScopeSample] = Field(default_factory=list)
    findings: list[FindingDetails] = Field(default_factory=list)
    criteria: list[CriterionResult] = Field(default_factory=list)


def apply_context(record: dict[str, Any], context: ReportContext | None) -> dict[str, Any]:
    """Enriquece cópia; exige ID inequívoco e não altera a evidência da sessão."""
    if context is None:
        return record
    criteria = [item.criterion for item in context.criteria]
    if len(criteria) != len(set(criteria)):
        raise ValueError("Critério repetido no contexto do relatório.")
    for assessment in context.criteria:
        outcomes = {item.get("outcome") for item in record.get("findings", []) if item.get("criterion") == assessment.criterion}
        contradicts_failure = "failed" in outcomes and assessment.outcome != "failed"
        contradicts_uncertainty = "cantTell" in outcomes and assessment.outcome in ("passed", "inapplicable", "untested")
        if contradicts_failure or contradicts_uncertainty:
            raise ValueError("Conclusão contradiz achados no relatório; resolva o escopo antes de exportar.")
    result = {**record, "report_context": context.model_dump(exclude={"findings"})}
    findings = [dict(item) for item in record.get("findings", [])]
    seen = set()
    for details in context.findings:
        matches = [item for item in findings if str(item.get("id")) == details.finding_id]
        if len(matches) != 1 or details.finding_id in seen:
            raise ValueError(f"ID de achado ausente, repetido ou ambíguo: {details.finding_id}")
        seen.add(details.finding_id)
        matches[0]["report_details"] = {
            **(matches[0].get("report_details") or {}),
            **details.model_dump(exclude={"finding_id"}, exclude_unset=True),
        }
    result["findings"] = findings
    return result


CONTEXT_LABELS = {
    "product_name": "Produto avaliado",
    "product_description": "Descrição do produto",
    "product_version": "Versão do produto / build",
    "report_version": "Versão do relatório",
    "report_date": "Data de emissão do relatório",
    "report_modified": "Última atualização do relatório",
    "evaluation_goal": "Objetivo da avaliação",
    "evaluator": "Avaliador",
    "evaluator_organization": "Organização do avaliador",
    "evaluator_contact": "Contato do avaliador",
    "evaluator_expertise": "Especialidade do avaliador",
    "commissioner": "Solicitante da avaliação",
    "evaluation_period": "Período da avaliação",
    "methodology": "Método efetivamente executado",
    "environment": "Ambiente, versões e tecnologias assistivas",
    "operating_system": "Sistema operacional",
    "browsers": "Navegadores",
    "sampling": "Seleção e justificativa da amostra",
    "complete_processes": "Jornadas e processos completos avaliados",
    "exclusions": "Exclusões do escopo",
    "content_languages": "Idiomas do produto",
    "evaluator_languages": "Idiomas dos avaliadores",
    "conformance_target": "Norma e nível pretendidos",
    "accessibility_support_baseline": "Base de suporte de acessibilidade",
    "technologies_relied_upon": "Tecnologias das quais o produto depende",
    "evaluation_tools": "Ferramentas de avaliação e versões",
    "product_exploration": "Exploração do produto e funcionalidades essenciais",
    "random_sample": "Amostra aleatória e comparação com a estruturada",
    "monitoring_plan": "Plano de acompanhamento e novas avaliações",
}


def context_rows(record: dict[str, Any]) -> list[list[str]]:
    context = record.get("report_context") or {}
    return [[label, str(context.get(key) or "Não registrado")] for key, label in CONTEXT_LABELS.items()]


def reproduction_groups(details: dict[str, Any]) -> list[tuple[str, list[str]]]:
    """Organiza rotas declaradas, sem deduzir teclas, posições ou fala de leitor."""
    groups = []
    for key, label in (
        ("reproduction_steps", "Passos gerais"),
        ("reproduction_steps_visual", "Com visão"),
        ("reproduction_steps_keyboard", "Por teclado"),
        ("reproduction_steps_screen_reader", "Sem visão"),
        ("reproduction_steps_screen_reader_proposed", "Sem visão — orientação de navegação não executada"),
    ):
        steps = [str(step).strip() for step in details.get(key, []) if str(step).strip()]
        if steps:
            groups.append((label, steps))
    return groups


SCREEN_READER_NOT_RUN = "Não executado com leitor de tela nesta ocorrência."
SCREEN_READER_PROPOSED_NOTE = ("Roteiro sugerido: NÃO foi executado com leitor de tela e a fala do leitor não foi lida. "
                               "Os passos são o que a pessoa faria; o resultado esperado é o que conferir.")
SCREEN_READER_EXECUTED_NOTE = ("Executado com leitor de tela real. Quem testa: pessoa que usa leitor de tela e não enxerga a tela. "
                               "Cada fala citada foi a que o leitor disse no teste.")


def _numbered(steps: list[str]) -> str:
    return "\n".join(f"{index}. {step}" for index, step in enumerate(steps, 1))


def _clean_steps(details: dict[str, Any], key: str) -> list[str]:
    return [str(step).strip() for step in details.get(key, []) if str(step).strip()]


def reproduction_visual_sections(details: dict[str, Any]) -> list[tuple[str, list[str]]]:
    """Passos de quem enxerga (baixa visão ou QA de acessibilidade); os passos de teclado feitos olhando a tela entram rotulados."""
    sections = []
    for key, label in (("reproduction_steps", ""), ("reproduction_steps_visual", ""), ("reproduction_steps_keyboard", "Por teclado (com visão)")):
        steps = _clean_steps(details, key)
        if steps:
            sections.append((label, steps))
    return sections


def reproduction_screen_reader_sections(details: dict[str, Any]) -> list[tuple[str, list[str]]]:
    """Passos de quem usa leitor de tela e não enxerga. Executado e proposto ficam rotulados; nunca se inventa fala."""
    sections = []
    executed = _clean_steps(details, "reproduction_steps_screen_reader")
    proposed = _clean_steps(details, "reproduction_steps_screen_reader_proposed")
    if executed:
        sections.append((SCREEN_READER_EXECUTED_NOTE, executed))
    if proposed:
        sections.append((SCREEN_READER_PROPOSED_NOTE, proposed))
    return sections


def _sections_text(sections: list[tuple[str, list[str]]]) -> str:
    return "\n\n".join((f"{label}\n" if label else "") + _numbered(steps) for label, steps in sections)


def reproduction_visual_text(details: dict[str, Any]) -> str:
    return _sections_text(reproduction_visual_sections(details))


def reproduction_screen_reader_text(details: dict[str, Any]) -> str:
    return _sections_text(reproduction_screen_reader_sections(details)) or SCREEN_READER_NOT_RUN


def reproduction_text(details: dict[str, Any]) -> str:
    groups = reproduction_groups(details)
    return "\n\n".join(
        (f"{label}\n" if len(groups) > 1 or label != "Passos gerais" else "")
        + "\n".join(f"{index}. {step}" for index, step in enumerate(steps, 1))
        for label, steps in groups
    )


def missing_report_data(record: dict[str, Any]) -> list[list[str]]:
    """Lista somente ausência objetiva de registro; não julga a qualidade do conteúdo."""
    context = record.get("report_context") or {}
    rows = [["Avaliação", label] for key, label in CONTEXT_LABELS.items()
            if not str(context.get(key) or "").strip()]
    fields = {
        "problem_location": "Roteiro: localização exata do problema",
        "testing_method": "Método do teste", "environment": "Ambiente do teste",
        "reproduction_steps": "Passos para reproduzir", "expected_result": "Resultado esperado",
        "actual_result": "Resultado observado",
        "criterion_rationale": "Justificativa do enquadramento WCAG",
    }
    for key, label in fields.items():
        identifiers = [str(item.get("id") or "Sem ID") for item in record.get("findings", [])
                       if not (reproduction_groups(item.get("report_details") or {}) if key == "reproduction_steps"
                               else (item.get("report_details") or {}).get(key))]
        if identifiers:
            rows.append(["Achados: " + ", ".join(identifiers), label])
    return rows


def report_pages(record: dict[str, Any]) -> list[str]:
    """URLs declaradas ou registradas, sem limitar o escopo à URL inicial da execução."""
    candidates = [record.get("url"), *(record.get("urls") or []),
                  *((record.get("coverage") or {}).get("pages_visited") or []),
                  *[item.get("page_url") for item in record.get("findings", [])],
                  *[item.get("url") for item in (record.get("report_context") or {}).get("samples", [])]]
    return list(dict.fromkeys(str(value) for value in candidates if value))


def criterion_result(record: dict[str, Any], number: str, findings: list[dict[str, Any]]) -> tuple[str, str]:
    """Apresenta conclusão explícita do avaliador ou os limites dos achados registrados."""
    assessments = (record.get("report_context") or {}).get("criteria", [])
    for assessment in assessments:
        if assessment["criterion"] == number:
            labels = {"passed": "Atende no escopo avaliado", "failed": "Falha registrada", "cantTell": "Inconclusivo",
                      "inapplicable": "Não aplicável", "untested": "Não avaliado"}
            return labels[assessment["outcome"]], (
                f"Escopo: {assessment['scope']}. {assessment['remarks']}"
            )
    items = [item for item in findings if str(item.get("criterion")) == number]
    if items:
        return ("Falha registrada" if any(item.get("outcome") == "failed" for item in items) else "Inconclusivo",
                "Achados: " + ", ".join(str(item.get("id") or "Não registrado") for item in items) + ". Não determina suporte do produto.")
    return "Não avaliado", "Sem teste documentado."
