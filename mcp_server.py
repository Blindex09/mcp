#!/usr/bin/env python3
"""
Universal Skills MCP Server v2.0
Expoe todas as skills de c:\\skills como ferramentas globais para Claude, VSCode, Cursor.

Best practices MCP 2026:
- ~15-20 tools max (nao sobrecarregar o LLM)
- Descricoes claras e detalhadas (influenciam decisao do LLM)
- Async handlers
- Validacao de inputs
- Paginacao para large datasets
- Categorização dinâmica no startup (zero config para novas skills)
- Retornar SKILL.md completo no invoke
"""

import hashlib
import re
import sys
import json
import logging
import time
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from a11y.tools import register as register_a11y
from sampling import ask_model, extract_json

# Setup logging (stderr so, nunca stdout em MCP!)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# Paths
SKILLS_PATH = Path("c:/skills")
MCP_PATH = Path(__file__).parent

# Initialize FastMCP server
mcp = FastMCP(
    "skills",
    instructions=(
        "Skills server with 1300+ skills. Categories come from the folder layout and model classification (classify_skills). "
        "Workflow: 1) list_<category>_skills() to browse by category, "
        "2) find_skills(task) - the model picks skills by meaning, no keywords, "
        "3) invoke_skill(name) to read full SKILL.md content. "
        "Use list_categories() to see all available categories with skill counts."
    ),
)


# ---------------------------------------------------------------------------
# TAXONOMIA (opcoes oferecidas ao modelo classificador - NAO sao regras de match)
# ---------------------------------------------------------------------------

CATEGORIES: tuple[str, ...] = (
    "accessibility", "ai", "backend", "frontend", "devops", "security", "testing",
    "mobile", "data", "automation", "architecture", "language", "content",
    "gamedev", "business", "web3", "health", "legal",
)

CATEGORY_ICONS = {
    "accessibility": "♿",
    "ai": "🤖",
    "backend": "⚙️",
    "frontend": "🎨",
    "devops": "🚀",
    "security": "🔒",
    "testing": "✅",
    "mobile": "📱",
    "data": "📊",
    "automation": "🔄",
    "architecture": "🏗️",
    "language": "💻",
    "content": "📝",
    "gamedev": "🎮",
    "business": "💼",
    "web3": "🔗",
    "health": "🏥",
    "legal": "⚖️",
    "unclassified": "📦",
}


# ---------------------------------------------------------------------------
# SKILL DISCOVERY & METADATA
# ---------------------------------------------------------------------------

# Classificacao feita pelo modelo (classify_skills), persistida para nao repetir custo.
CLASSIFICATION_CACHE = MCP_PATH / "skills_classification.json"


def _description_hash(description: str) -> str:
    return hashlib.sha1(description.encode("utf-8")).hexdigest()[:12]


def load_classification() -> dict[str, dict[str, Any]]:
    try:
        data = json.loads(CLASSIFICATION_CACHE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_classification(data: dict[str, dict[str, Any]]) -> None:
    CLASSIFICATION_CACHE.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def skill_categories(name: str, description: str, folder_category: str | None) -> list[str]:
    """Pasta pai (fato estrutural) + categorias decididas pelo modelo. Nada por nome/palavra."""
    cats: list[str] = [folder_category] if folder_category else []
    entry = load_classification().get(name)
    if entry and entry.get("h") == _description_hash(description):
        cats += [c for c in entry.get("cats", []) if c not in cats]
    return cats or ["unclassified"]


def get_skill_info(
    skill_dir: Path,
    folder_category: str | None = None,
) -> dict[str, Any] | None:
    """Le SKILL.md e extrai metadados da skill.

    Args:
        skill_dir: Pasta da skill que contem SKILL.md.
        folder_category: Categoria determinada pela pasta pai (layout categorizado).
            Quando fornecida, e' usada como categoria primaria, tornando a estrutura
            de pastas a fonte de verdade da categoria.
    """
    skill_md = skill_dir / "SKILL.md"

    if not skill_md.exists():
        return None

    try:
        content = skill_md.read_text(encoding="utf-8")
        skill_name = skill_dir.name
        lines = [line.strip() for line in content.split("\n") if line.strip()]

        description_lines = []
        for line in lines:
            if line.startswith("#"):
                description_lines.append(line.replace("#", "").strip())
            elif not line.startswith("[") and description_lines and len(description_lines) < 3:
                description_lines.append(line)
            if len(description_lines) >= 2:
                break

        description = " ".join(description_lines)[:200]

        description = description or "Advanced skill"
        categories = skill_categories(skill_name, description, folder_category)

        return {
            "name": skill_name,
            "description": description,
            "path": str(skill_dir),
            "skill_md_preview": content[:1000],
            "full_content_path": str(skill_md),
            "categories": categories,
        }
    except Exception as e:
        logger.error(f"Erro ao ler skill {skill_dir.name}: {e}")
        return None


def discover_skills() -> list[dict[str, Any]]:
    """Descobre TODAS as skills em c:\\skills em tempo real.

    Suporta dois layouts:
    - Flat:        c:\\skills\\<skill-name>\\SKILL.md  (legado)
    - Categorizado: c:\\skills\\<categoria>\\<skill-name>\\SKILL.md  (atual)

    Qualquer subdiretorio sem SKILL.md diretamente e' tratado como uma
    pasta de categoria e tem seus filhos iterados um nivel a mais.
    """
    skills: list[dict[str, Any]] = []

    if not SKILLS_PATH.exists():
        logger.warning(f"Skills path nao existe: {SKILLS_PATH}")
        return skills

    for item in SKILLS_PATH.iterdir():
        if not item.is_dir() or item.name.startswith("."):
            continue
        if (item / "SKILL.md").exists():
            # Layout flat — skill direto na raiz
            skill_info = get_skill_info(item)
            if skill_info:
                skills.append(skill_info)
        else:
            # Layout categorizado — pasta pai e' a categoria (fato estrutural)
            for subitem in item.iterdir():
                if subitem.is_dir() and not subitem.name.startswith("."):
                    skill_info = get_skill_info(subitem, folder_category=item.name)
                    if skill_info:
                        skills.append(skill_info)

    logger.debug(f"Descobertas {len(skills)} skills ")
    return sorted(skills, key=lambda s: s["name"])


# Cache com TTL — recarrega automaticamente a cada 5 minutos
# Garante que novas pastas em c:\skills aparecem sem reiniciar o servidor
_CACHE_TTL_SECONDS = 300  # 5 minutos
_skills: list[dict[str, Any]] = []
_skills_loaded_at: float = 0.0


def get_skills(force_reload: bool = False) -> list[dict[str, Any]]:
    """Retorna skills do cache. Recarrega se TTL expirou ou force_reload=True."""
    global _skills, _skills_loaded_at
    age = time.time() - _skills_loaded_at
    if force_reload or not _skills or age >= _CACHE_TTL_SECONDS:
        _skills = discover_skills()
        _skills_loaded_at = time.time()
        logger.debug(f"Cache recarregado: {len(_skills)} skills")
    return _skills


def build_category_response(
    skills: list[dict[str, Any]],
    category: str,
    icon: str,
    label: str,
    limit: int = 0,
) -> str:
    filtered = [s for s in skills if category in s.get("categories", [])]

    if not filtered:
        return f"Nenhuma skill de {label} encontrada."

    display = filtered[:limit] if limit > 0 else filtered

    response = f"{icon} **Skills de {label}** ({len(filtered)} encontradas)\n\n"
    for idx, skill in enumerate(display, 1):
        cats = ", ".join(skill.get("categories", []))
        response += f"{idx}. **{skill['name']}** [{cats}]\n"
        response += f"   {skill['description']}\n\n"

    if limit > 0 and len(filtered) > limit:
        response += f"\n_...e mais {len(filtered) - limit} skills. Use limit=0 para ver todas._"

    return response


# ---------------------------------------------------------------------------
# TOOLS POR CATEGORIA (16 categorias)
# Cada tool retorna SOMENTE as skills daquela categoria
# ---------------------------------------------------------------------------

@mcp.tool()
async def list_accessibility_skills(limit: int = 0) -> str:
    """
    /accessibility - Lista SOMENTE skills de Acessibilidade: WCAG, a11y, ARIA, screen reader, audit, compliance.
    Retorna skills focadas exclusivamente em acessibilidade web e mobile.

    Args:
        limit: Numero de resultados (0 = todos)
    """
    return build_category_response(get_skills(), "accessibility", "♿", "Acessibilidade", limit)


@mcp.tool()
async def list_ai_skills(limit: int = 0) -> str:
    """
    /ai - Lista SOMENTE skills de Inteligencia Artificial e Agentes: LLM, Claude, GPT, MCP, agents, prompt engineering, RAG, embeddings, vector search, fine-tuning, chatbots, NLP, copilot, multi-agent orchestration.
    Retorna skills focadas exclusivamente em IA, machine learning e agentes autonomos.

    Args:
        limit: Numero de resultados (0 = todos)
    """
    return build_category_response(get_skills(), "ai", "🤖", "IA & Agentes", limit)


@mcp.tool()
async def list_backend_skills(limit: int = 0) -> str:
    """
    /backend - Lista SOMENTE skills de Backend: API, banco de dados, microsservicos, serverless, FastAPI, Django, NestJS, GraphQL, gRPC, Prisma, PostgreSQL, Redis, Kafka, webhooks.
    Retorna skills focadas exclusivamente em desenvolvimento backend e APIs.

    Args:
        limit: Numero de resultados (0 = todos)
    """
    return build_category_response(get_skills(), "backend", "⚙️", "Backend", limit)


@mcp.tool()
async def list_frontend_skills(limit: int = 0) -> str:
    """
    /frontend - Lista SOMENTE skills de Frontend: React, Vue, Angular, Svelte, Next.js, CSS, Tailwind, UI/UX, design system, Storybook, themes.
    Retorna skills focadas exclusivamente em desenvolvimento frontend e interfaces.

    Args:
        limit: Numero de resultados (0 = todos)
    """
    return build_category_response(get_skills(), "frontend", "🎨", "Frontend", limit)


@mcp.tool()
async def list_devops_skills(limit: int = 0) -> str:
    """
    /devops - Lista SOMENTE skills de DevOps e Cloud: Terraform, AWS, Azure, GCP, Docker, Kubernetes, CI/CD, GitHub Actions, deploy, monitoring, observability, pipelines, infrastructure as code.
    Retorna skills focadas exclusivamente em infraestrutura, cloud e operacoes.

    Args:
        limit: Numero de resultados (0 = todos)
    """
    return build_category_response(get_skills(), "devops", "🚀", "DevOps & Cloud", limit)


@mcp.tool()
async def list_security_skills(limit: int = 0) -> str:
    """
    /security - Lista SOMENTE skills de Seguranca: Pentest, Auth, GDPR, vulnerabilidades, hacking etico, malware analysis, threat modeling, digital forensics, privilege escalation, XSS, CSRF, SQL injection, OWASP.
    Retorna skills focadas exclusivamente em seguranca cibernetica e testes de penetracao.

    Args:
        limit: Numero de resultados (0 = todos)
    """
    return build_category_response(get_skills(), "security", "🔒", "Seguranca", limit)


@mcp.tool()
async def list_testing_skills(limit: int = 0) -> str:
    """
    /testing - Lista SOMENTE skills de Testes e QA: unit, e2e, integration, Playwright, pytest, Jest, Vitest, coverage, lint, audit, evaluation, test automation.
    Retorna skills focadas exclusivamente em qualidade de software e testes automatizados.

    Args:
        limit: Numero de resultados (0 = todos)
    """
    return build_category_response(get_skills(), "testing", "✅", "Testes & QA", limit)


@mcp.tool()
async def list_mobile_skills(limit: int = 0) -> str:
    """
    /mobile - Lista SOMENTE skills de Mobile: React Native, Flutter, iOS, Android, SwiftUI, Kotlin, Expo, Jetpack Compose.
    Retorna skills focadas exclusivamente em desenvolvimento mobile nativo e cross-platform.

    Args:
        limit: Numero de resultados (0 = todos)
    """
    return build_category_response(get_skills(), "mobile", "📱", "Mobile", limit)


@mcp.tool()
async def list_data_skills(limit: int = 0) -> str:
    """
    /data - Lista SOMENTE skills de Data Engineering e Analytics: ETL, pipelines, data warehouse, dbt, Spark, Airflow, BigQuery, Snowflake, Databricks, data lake.
    Retorna skills focadas exclusivamente em engenharia de dados e analytics.

    Args:
        limit: Numero de resultados (0 = todos)
    """
    return build_category_response(get_skills(), "data", "📊", "Data Engineering", limit)


@mcp.tool()
async def list_automation_skills(limit: int = 0) -> str:
    """
    /automation - Lista SOMENTE skills de Automacao: workflows, Zapier, n8n, browser automation, WhatsApp, Airtable, HubSpot, Salesforce, CRM, integracao de ferramentas SaaS.
    Retorna skills focadas exclusivamente em automacao de processos e integracoes.

    Args:
        limit: Numero de resultados (0 = todos)
    """
    return build_category_response(get_skills(), "automation", "🔄", "Automacao", limit)


@mcp.tool()
async def list_architecture_skills(limit: int = 0) -> str:
    """
    /architecture - Lista SOMENTE skills de Arquitetura de Software: design patterns, system design, C4, microservices, event-driven, DDD, clean architecture, hexagonal, CQRS.
    Retorna skills focadas exclusivamente em arquitetura e design de sistemas.

    Args:
        limit: Numero de resultados (0 = todos)
    """
    return build_category_response(get_skills(), "architecture", "🏗️", "Arquitetura", limit)


@mcp.tool()
async def list_language_skills(limit: int = 0) -> str:
    """
    /language - Lista SOMENTE skills especificas por Linguagem de Programacao: Python, Go, Rust, TypeScript, Java, C#, Ruby, Elixir, PHP, Bash, Lua, .NET.
    Retorna skills focadas em boas praticas e patterns de linguagens especificas.

    Args:
        limit: Numero de resultados (0 = todos)
    """
    return build_category_response(get_skills(), "language", "💻", "Linguagens", limit)


@mcp.tool()
async def list_content_skills(limit: int = 0) -> str:
    """
    /content - Lista SOMENTE skills de Conteudo e Marketing: SEO, copywriting, branding, blog, newsletter, social media, landing pages, editorial, marketing digital.
    Retorna skills focadas exclusivamente em criacao de conteudo e marketing.

    Args:
        limit: Numero de resultados (0 = todos)
    """
    return build_category_response(get_skills(), "content", "📝", "Conteudo & Marketing", limit)


@mcp.tool()
async def list_gamedev_skills(limit: int = 0) -> str:
    """
    /gamedev - Lista SOMENTE skills de Desenvolvimento de Games: Unity, Godot, Bevy, shaders, ECS, game design, game engines.
    Retorna skills focadas exclusivamente em desenvolvimento de jogos.

    Args:
        limit: Numero de resultados (0 = todos)
    """
    return build_category_response(get_skills(), "gamedev", "🎮", "GameDev", limit)


@mcp.tool()
async def list_business_skills(limit: int = 0) -> str:
    """
    /business - Lista SOMENTE skills de Negocios e Startups: analise de mercado, KPIs, product management, growth, pricing, fundraising.
    Retorna skills focadas exclusivamente em negocios e empreendedorismo.

    Args:
        limit: Numero de resultados (0 = todos)
    """
    return build_category_response(get_skills(), "business", "💼", "Negocios & Startups", limit)


@mcp.tool()
async def list_web3_skills(limit: int = 0) -> str:
    """
    /web3 - Lista SOMENTE skills de Web3 e Blockchain: Solidity, DeFi, NFT, smart contracts, tokenomics, wallets.
    Retorna skills focadas exclusivamente em blockchain e tecnologias descentralizadas.

    Args:
        limit: Numero de resultados (0 = todos)
    """
    return build_category_response(get_skills(), "web3", "🔗", "Web3 & Blockchain", limit)


@mcp.tool()
async def list_health_skills(limit: int = 0) -> str:
    """
    /health - Lista SOMENTE skills de Saúde e Bem-estar: analísadores de saúde, nutrição, fitness, saúde mental, medicina, reabilitação.
    Retorna skills focadas exclusivamente em saúde, bem-estar e análise clínica.

    Args:
        limit: Numero de resultados (0 = todos)
    """
    return build_category_response(get_skills(), "health", "🏥", "Saúde & Bem-estar", limit)


@mcp.tool()
async def list_legal_skills(limit: int = 0) -> str:
    """
    /legal - Lista SOMENTE skills Jurídicas: advogado, leiloeiro, contratos, direito, jurídico.
    Retorna skills focadas exclusivamente em direito e serviços jurídicos.

    Args:
        limit: Numero de resultados (0 = todos)
    """
    return build_category_response(get_skills(), "legal", "⚖️", "Jurídico & Legal", limit)


# ---------------------------------------------------------------------------
# PROMPTS MCP — aparecem como /comando no Claude Desktop e clientes compatíveis
# Cada prompt injeta uma mensagem que aciona a tool correspondente
# ---------------------------------------------------------------------------

@mcp.prompt()
def oliverplan(contexto: str = "") -> list[dict]:
    """Planeja uma feature completa antes de codar (usa skill concise-planning)"""
    task = f' para: {contexto}' if contexto else ''
    return [{"role": "user", "content": f"Use invoke_skill('concise-planning', '{contexto}') para obter as instruções e crie um plano claro, atômico e detalhado{task}. Inclua: entendimento do problema, abordagem técnica, subtarefas, riscos e dependências."}]

@mcp.prompt()
def oliverreview(contexto: str = "") -> list[dict]:
    """Revisão profunda de código — bugs, segurança, performance (usa skill code-review-excellence)"""
    task = f' para: {contexto}' if contexto else ''
    return [{"role": "user", "content": f"Use invoke_skill('code-review-excellence', '{contexto}') para obter as instruções e realize uma revisão profunda{task}. Analise: bugs, segurança (OWASP Top 10), performance, tipagem, duplicação e legibilidade."}]

@mcp.prompt()
def oliverdeploy(contexto: str = "") -> list[dict]:
    """Checklist de deploy seguro (usa skill deployment-validation-config-validate)"""
    task = f' para: {contexto}' if contexto else ''
    return [{"role": "user", "content": f"Use invoke_skill('deployment-validation-config-validate', '{contexto}') para obter o checklist e conduza um deploy seguro{task}. Verifique: env vars, secrets, migrations, rollback, health checks e logs."}]

@mcp.prompt()
def oliverdebug(contexto: str = "") -> list[dict]:
    """Workflow estruturado de debug (usa skill debugging-toolkit-smart-debug)"""
    task = f' para: {contexto}' if contexto else ''
    return [{"role": "user", "content": f"Use invoke_skill('debugging-toolkit-smart-debug', '{contexto}') para obter as instruções e conduza o debug{task}. Siga: hipótese → evidência → isolamento → correção → validação."}]

@mcp.prompt()
def olivercommit(contexto: str = "") -> list[dict]:
    """Gera commit semântico perfeito (feat/fix/chore/refactor/docs/test)"""
    task = f' para: {contexto}' if contexto else ''
    return [{"role": "user", "content": f"Analise as mudanças recentes no código{task} e gere um commit semântico perfeito. Formato: tipo(escopo): descrição em inglês. Tipos: feat, fix, chore, refactor, docs, test. Seja preciso e conciso."}]

@mcp.prompt()
def accessibility() -> list[dict]:
    """Lista skills de Acessibilidade (WCAG, a11y, ARIA)"""
    return [{"role": "user", "content": "Use list_accessibility_skills() e me mostre todas as skills de acessibilidade disponíveis."}]

@mcp.prompt()
def ai() -> list[dict]:
    """Lista skills de IA & Agentes (LLM, RAG, agents, prompt engineering)"""
    return [{"role": "user", "content": "Use list_ai_skills() e me mostre todas as skills de IA e agentes disponíveis."}]

@mcp.prompt()
def backend() -> list[dict]:
    """Lista skills de Backend (API, banco de dados, microsserviços, serverless)"""
    return [{"role": "user", "content": "Use list_backend_skills() e me mostre todas as skills de backend disponíveis."}]

@mcp.prompt()
def frontend() -> list[dict]:
    """Lista skills de Frontend (React, Vue, CSS, UI/UX, design system)"""
    return [{"role": "user", "content": "Use list_frontend_skills() e me mostre todas as skills de frontend disponíveis."}]

@mcp.prompt()
def devops() -> list[dict]:
    """Lista skills de DevOps & Cloud (Docker, K8s, Terraform, AWS, CI/CD)"""
    return [{"role": "user", "content": "Use list_devops_skills() e me mostre todas as skills de DevOps e Cloud disponíveis."}]

@mcp.prompt()
def security() -> list[dict]:
    """Lista skills de Segurança (pentest, auth, OWASP, vulnerabilidades)"""
    return [{"role": "user", "content": "Use list_security_skills() e me mostre todas as skills de segurança disponíveis."}]

@mcp.prompt()
def testing() -> list[dict]:
    """Lista skills de Testing & QA (e2e, unitários, Playwright, debug, TDD)"""
    return [{"role": "user", "content": "Use list_testing_skills() e me mostre todas as skills de testing e QA disponíveis."}]

@mcp.prompt()
def mobile() -> list[dict]:
    """Lista skills de Mobile (iOS, Android, Flutter, React Native, Expo)"""
    return [{"role": "user", "content": "Use list_mobile_skills() e me mostre todas as skills de mobile disponíveis."}]

@mcp.prompt()
def data() -> list[dict]:
    """Lista skills de Data Engineering (ETL, pipelines, dbt, Spark, analytics)"""
    return [{"role": "user", "content": "Use list_data_skills() e me mostre todas as skills de data engineering disponíveis."}]

@mcp.prompt()
def automation() -> list[dict]:
    """Lista skills de Automação (workflows, integrações, Zapier, n8n, SaaS)"""
    return [{"role": "user", "content": "Use list_automation_skills() e me mostre todas as skills de automação disponíveis."}]

@mcp.prompt()
def architecture() -> list[dict]:
    """Lista skills de Arquitetura (system design, DDD, clean arch, refactor)"""
    return [{"role": "user", "content": "Use list_architecture_skills() e me mostre todas as skills de arquitetura disponíveis."}]

@mcp.prompt()
def language() -> list[dict]:
    """Lista skills de Linguagens (Python, TypeScript, Rust, Go, Java, etc.)"""
    return [{"role": "user", "content": "Use list_language_skills() e me mostre todas as skills por linguagem de programação disponíveis."}]

@mcp.prompt()
def content() -> list[dict]:
    """Lista skills de Conteúdo & Marketing (SEO, copywriting, docs, CRO)"""
    return [{"role": "user", "content": "Use list_content_skills() e me mostre todas as skills de conteúdo e marketing disponíveis."}]

@mcp.prompt()
def gamedev() -> list[dict]:
    """Lista skills de GameDev (Unity, Godot, Bevy, shaders, ECS)"""
    return [{"role": "user", "content": "Use list_gamedev_skills() e me mostre todas as skills de desenvolvimento de games disponíveis."}]

@mcp.prompt()
def business() -> list[dict]:
    """Lista skills de Negócios & Startups (KPIs, produto, growth, finanças)"""
    return [{"role": "user", "content": "Use list_business_skills() e me mostre todas as skills de negócios e startups disponíveis."}]

@mcp.prompt()
def web3() -> list[dict]:
    """Lista skills de Web3 & Blockchain (Solidity, DeFi, NFT, smart contracts)"""
    return [{"role": "user", "content": "Use list_web3_skills() e me mostre todas as skills de Web3 e blockchain disponíveis."}]

@mcp.prompt()
def health() -> list[dict]:
    """Lista skills de Saúde & Bem-estar (saúde mental, nutrição, fitness, medicina)"""
    return [{"role": "user", "content": "Use list_health_skills() e me mostre todas as skills de saúde e bem-estar disponíveis."}]

@mcp.prompt()
def legal() -> list[dict]:
    """Lista skills Jurídicas (advogado, leiloeiro, direito, contratos)"""
    return [{"role": "user", "content": "Use list_legal_skills() e me mostre todas as skills jurídicas disponíveis."}]

@mcp.prompt()
def skills(query: str = "") -> list[dict]:
    """Acha skills para uma tarefa (o modelo escolhe pelo sentido), ou lista as categorias"""
    if query:
        return [{"role": "user", "content": f"Use find_skills('{query}') e me mostre as skills encontradas."}]
    return [{"role": "user", "content": "Use list_categories() e me mostre todas as categorias de skills disponíveis com suas contagens."}]


# ---------------------------------------------------------------------------
# TOOLS GERAIS
# ---------------------------------------------------------------------------

@mcp.tool()
async def invoke_skill(skill_name: str, params: str = "") -> str:
    """
    Invoca uma skill especifica pelo nome e retorna o conteudo COMPLETO do SKILL.md.
    Use este comando para ler e aplicar uma skill especifica.

    Args:
        skill_name: Nome exato da skill (ex: 'agent-customization', 'prompt-engineer', 'react-best-practices')
        params: Contexto adicional ou pergunta especifica sobre a skill
    """
    skills = get_skills()
    matching = [s for s in skills if s["name"].lower() == skill_name.lower()]

    if not matching:
        return f"Skill '{skill_name}' nao encontrada. Use find_skills(task) para o modelo achar a skill certa."

    skill = matching[0]

    # Le o SKILL.md COMPLETO
    full_content = ""
    try:
        skill_md_path = Path(skill["full_content_path"])
        if skill_md_path.exists():
            full_content = skill_md_path.read_text(encoding="utf-8")
    except Exception as e:
        full_content = skill.get("skill_md_preview", "Erro ao ler conteudo")
        logger.error(f"Erro ao ler SKILL.md completo de {skill_name}: {e}")

    response = f"**{skill['name']}**\n\n"
    response += f"Categorias: {', '.join(skill.get('categories', ['other']))}\n"
    response += f"Caminho: {skill['path']}\n\n"

    if params:
        response += f"Contexto do usuario: {params}\n\n"

    response += f"---\n\n{full_content}"

    return response


_FIND_BATCH = 250   # skills por chamada ao modelo (limite de contexto, nao de relevancia)
_FIND_MAX_RESULTS = 10
_CLASSIFY_BATCH = 60


def _catalog_line(skill: dict[str, Any]) -> str:
    return f"{skill['name']} :: {skill['description'][:100]}"


@mcp.tool()
async def find_skills(task: str, ctx: Context) -> str:  # type: ignore[type-arg]
    """
    Acha as skills certas para uma tarefa descrita em linguagem natural (qualquer idioma).
    Quem escolhe e o MODELO do cliente (MCP sampling) lendo o catalogo - sem palavra-chave,
    regex nem ranking lexical. Entende intencao, sinonimos e contexto.

    Args:
        task: O que voce precisa fazer (ex: 'subir um agente no Azure com CI', 'tela de chat acessivel')
    """
    skills = get_skills()
    if not skills:
        return "Nenhuma skill disponivel."
    known = {s["name"]: s for s in skills}

    picked: list[str] = []
    for i in range(0, len(skills), _FIND_BATCH):
        batch = skills[i : i + _FIND_BATCH]
        lines = "\n".join(_catalog_line(s) for s in batch)
        raw = await ask_model(
            ctx,
            "Voce escolhe skills para uma tarefa. Julgue pelo SENTIDO e pela intencao, nao por "
            f"palavras em comum. Escolha ate {_FIND_MAX_RESULTS} nomes deste catalogo que realmente "
            "ajudam (lista vazia se nenhum serve). Responda SOMENTE com um array JSON de nomes."
            f"\n\nTAREFA:\n{task}\n\nCATALOGO:\n{lines}",
            max_tokens=400,
        )
        if raw is None:
            return (
                "O cliente nao oferece sampling, entao a escolha por modelo nao esta disponivel aqui. "
                "Leia o catalogo com list_all_skills(page=N) ou list_categories() e escolha voce mesmo, "
                "depois use invoke_skill(nome)."
            )
        names = extract_json(raw, "array") or []
        picked += [n for n in names if isinstance(n, str) and n in known and n not in picked]

    if len(picked) > _FIND_MAX_RESULTS:  # varios lotes: o modelo desempata entre os finalistas
        lines = "\n".join(_catalog_line(known[n]) for n in picked)
        raw = await ask_model(
            ctx,
            f"Dos candidatos abaixo, escolha os {_FIND_MAX_RESULTS} mais uteis para a tarefa, "
            "do mais util ao menos. Responda SOMENTE com um array JSON de nomes."
            f"\n\nTAREFA:\n{task}\n\n{lines}",
            max_tokens=400,
        )
        final = [n for n in (extract_json(raw, "array") or []) if isinstance(n, str) and n in picked]
        picked = final or picked[:_FIND_MAX_RESULTS]

    if not picked:
        return f"O modelo nao achou skill adequada para: {task}"
    out = f"Skills para '{task}' ({len(picked)}):\n\n"
    for idx, n in enumerate(picked, 1):
        sk = known[n]
        out += f"{idx}. **{n}** [{', '.join(sk.get('categories', []))}]\n   {sk['description']}\n\n"
    return out + "_Use invoke_skill('nome') para ler a skill._"


@mcp.tool()
async def classify_skills(ctx: Context, max_batches: int = 10, force: bool = False) -> str:  # type: ignore[type-arg]
    """
    Pede ao modelo do cliente (MCP sampling) para classificar as skills sem categoria nas
    categorias de list_categories(). O resultado fica em cache (skills_classification.json)
    e so se reclassifica o que mudou. Skills que o modelo nao souber classificar ficam
    'unclassified' - nada e chutado por nome.

    Args:
        max_batches: Teto de chamadas ao modelo por execucao (retome chamando de novo)
        force: Reclassifica tudo, ignorando o cache
    """
    skills = get_skills(force_reload=True)
    cache = load_classification()
    todo = [
        s for s in skills
        if force or cache.get(s["name"], {}).get("h") != _description_hash(s["description"])
    ]
    if not todo:
        return "Todas as skills ja estao classificadas."

    done = 0
    for n_batch, i in enumerate(range(0, len(todo), _CLASSIFY_BATCH)):
        if n_batch >= max(1, max_batches):
            break
        batch = todo[i : i + _CLASSIFY_BATCH]
        raw = await ask_model(
            ctx,
            "Classifique cada skill em UMA ou MAIS destas categorias, pelo sentido do que ela faz: "
            f"{', '.join(CATEGORIES)}. Se nenhuma servir, use lista vazia. Responda SOMENTE com um "
            'objeto JSON {"nome-da-skill": ["categoria", ...]}.\n\n'
            + "\n".join(_catalog_line(s) for s in batch),
            max_tokens=2000,
        )
        if raw is None:
            if done == 0:
                return "O cliente nao oferece sampling: nao da para classificar por modelo aqui."
            break
        result = extract_json(raw, "object") or {}
        for s in batch:
            cats = result.get(s["name"])
            if isinstance(cats, list):
                cache[s["name"]] = {
                    "h": _description_hash(s["description"]),
                    "cats": [c for c in cats if c in CATEGORIES],
                }
                done += 1
    save_classification(cache)
    get_skills(force_reload=True)
    return f"Classificadas {done} skills; faltam {len(todo) - done}. Cache: {CLASSIFICATION_CACHE.name}"


@mcp.tool()
async def list_categories() -> str:
    """
    Lista as categorias em uso com contagem de skills (pasta pai + classificacao feita pelo modelo).
    Categorias: accessibility, ai, backend, frontend, devops, security, testing, mobile, data, automation, architecture, language, content, gamedev, business, web3, health, legal.
    Para achar skills por tarefa use find_skills(task). Para classificar skills sem categoria use classify_skills().
    """
    skills = get_skills()

    cat_count: dict[str, int] = {}
    for skill in skills:
        for cat in skill.get("categories", []):
            cat_count[cat] = cat_count.get(cat, 0) + 1

    if not cat_count:
        return "Nenhuma categoria disponivel"

    response = f"**{len(skills)} Skills em {len(cat_count)} Categorias**\n\n"
    for cat, count in sorted(cat_count.items(), key=lambda x: x[1], reverse=True):
        icon = CATEGORY_ICONS.get(cat, "📦")
        response += f"{icon} **{cat}** - {count} skills\n"

    response += "\n---\n"
    response += "Comandos disponiveis:\n"
    for cat in sorted(CATEGORIES):
        icon = CATEGORY_ICONS.get(cat, "📦")
        response += f"  {icon} list_{cat}_skills()\n"

    return response


@mcp.tool()
async def list_all_skills(page: int = 1, per_page: int = 50) -> str:
    """
    Lista todas as skills com paginacao. Mostra nome, categoria e descricao.

    Args:
        page: Numero da pagina (padrao: 1)
        per_page: Skills por pagina (padrao: 50, max: 100)
    """
    skills = get_skills()

    if not skills:
        return "Nenhuma skill disponivel em c:\\skills"

    per_page = min(per_page, 100)
    total = len(skills)
    total_pages = (total + per_page - 1) // per_page
    start = (page - 1) * per_page
    page_skills = skills[start : start + per_page]

    response = f"**{total} Skills** - Pagina {page}/{total_pages}\n\n"

    for idx, skill in enumerate(page_skills, start + 1):
        cats = ", ".join(skill.get("categories", ["other"]))
        response += f"{idx}. **{skill['name']}** [{cats}]\n"
        response += f"   {skill['description']}\n\n"

    response += f"\n_Pagina {page} de {total_pages} - use page=N para navegar_"

    return response


@mcp.tool()
async def refresh_skills() -> str:
    """
    Recarrega imediatamente todas as skills de c:\\skills sem reiniciar o servidor.
    Use quando adicionar novas pastas de skills e quiser que apareçam agora.
    O cache também se auto-atualiza a cada 5 minutos automaticamente.
    """
    before = len(get_skills())
    skills = get_skills(force_reload=True)
    after = len(skills)
    diff = after - before

    cat_count: dict[str, int] = {}
    for s in skills:
        for c in s.get("categories", []):
            cat_count[c] = cat_count.get(c, 0) + 1

    summary = f"**Skills recarregadas com sucesso!**\n\n"
    summary += f"- Total: **{after}** skills"
    if diff > 0:
        summary += f" (+{diff} novas)"
    elif diff < 0:
        summary += f" ({diff} removidas)"
    else:
        summary += f" (sem mudanças)"
    summary += f"\n- Categorias: {len(cat_count)}\n\n"
    summary += "Top categorias:\n"
    for cat, count in sorted(cat_count.items(), key=lambda x: x[1], reverse=True)[:5]:
        icon = CATEGORY_ICONS.get(cat, "📦")
        summary += f"  {icon} {cat}: {count}\n"

    return summary


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

register_a11y(mcp)  # ferramentas de acessibilidade embutidas (a11y/)


def main() -> None:
    """Inicia o servidor MCP."""
    try:
        logger.debug("Iniciando Skills MCP Server v2.0...")
        skills = get_skills()

        # Log de estatisticas
        cat_count: dict[str, int] = {}
        for s in skills:
            for c in s.get("categories", []):
                cat_count[c] = cat_count.get(c, 0) + 1
        logger.debug(
            f"{len(skills)} skills carregadas em {len(cat_count)} categorias: "
            + ", ".join(f"{k}={v}" for k, v in sorted(cat_count.items(), key=lambda x: -x[1]))
        )

        logger.debug("Iniciando servidor MCP via stdio...")
        mcp.run(transport="stdio")
    except Exception as e:
        logger.error(f"Erro fatal no servidor: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
