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

import re
import sys
import json
import logging
import time
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import Context, FastMCP

from a11y.tools import register as register_a11y

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
        "Skills server with 1300+ skills in 18 categories. "
        "Workflow: 1) list_<category>_skills() to browse by category, "
        "2) semantic_search_skills(query) for cross-category semantic search, "
        "3) invoke_skill(name) to read full SKILL.md content. "
        "Use list_categories() to see all available categories with skill counts."
    ),
)


# ---------------------------------------------------------------------------
# REGRAS DE CATEGORIZACAO (inline, sem depender de arquivo externo)
# ---------------------------------------------------------------------------

CATEGORY_RULES: dict[str, dict] = {
    "accessibility": {
        "tokens": ["accessibility", "a11y", "wcag", "aria", "accessible"],
        "substrings": ["accessibility", "a11y", "wcag"],
        "prefixes": [],
        "excludes": [],
    },
    "ai": {
        "tokens": [
            "ai", "agent", "agents", "llm", "ml", "gpt", "rag",
            "prompt", "embedding", "chatbot", "nlp", "copilot",
            "crewai", "langfuse", "langgraph", "mlops", "imagen",
        ],
        "substrings": [
            "agent", "llm", "ai-", "-ai-", "-ai",
            "machine-learning", "multi-agent", "autonomous-agent",
            "subagent", "voice-ai", "computer-use", "agentfolio",
            "prompt-", "-prompt", "rag-", "-rag",
            "embedding", "vector-index", "fine-tun",
            "claude-", "anthropic", "openai-", "gemini-",
            "copilot-", "chatbot", "nlp-", "neural",
            "context-compress", "context-window", "context-manager",
            "context-driven", "context-fundamental", "context-optimiz",
            "conversation-memory", "computer-vision", "bdi-mental",
            "exa-search", "deep-research", "tavily", "notebooklm",
            "langfuse", "crewai", "langgraph", "mlops-",
            "transcrib", "behavioral-mode", "hugging-face",
            "fal-generate", "fal-image", "fal-audio", "fal-upscale",
            "fal-workflow", "fal-platform",
            "mcp-builder", "mcp-builder-ms", "memory-systems",
            "research-engineer",
            # personas & AI researchers
            "yann-lecun", "andrej-karpathy", "ilya-sutskever",
            "geoffrey-hinton", "sam-altman", "bill-gates",
            "elon-musk", "steve-jobs", "warren-buffett",
            "matematico-tao", "lex-fridman",
            # AI tools & frameworks
            "comfyui", "bdistill-", "videodb",
            "image-studio", "seek-and-analyze-video",
            "tool-use-guardian", "algorithmic-art",
            # quantum computing
            "qiskit", "cirq-",
        ],
        "prefixes": ["ai-", "azure-ai-", "m365-agents", "llm-", "context-", "fal-", "hugging-face-"],
        "excludes": [
            "bullmq-specialist",
            "fp-ts-pragmatic",
            "brand-guidelines-anthropic",
            "internal-comms-anthropic",
        ],
    },
    "backend": {
        "tokens": [
            "api", "server", "backend", "database", "db", "sql",
            "graphql", "grpc", "webhook", "middleware", "nosql",
        ],
        "substrings": [
            "api-", "-api", "backend", "database", "serverless",
            "microservice", "fastapi", "express-", "django", "flask",
            "nestjs", "graphql", "rest-api", "grpc", "prisma",
            "postgres", "mysql", "mongodb", "redis-",
            "kafka-", "rabbitmq", "bullmq", "supabase",
            "webhook", "cron-", "scheduler",
            "algolia", "convex", "using-neon", "neon-",
            "cloudflare-workers", "plaid-",
            "laravel", "pydantic", "hybrid-search",
            "similarity-search", "file-upload", "schema-markup",
            "payment-integration",
            "odoo-", "hono", "drizzle-orm", "trpc-",
            "new-rails-project", "zod-validation", "pakistan-payments",
        ],
        "prefixes": ["api-", "database-", "sql-"],
        "excludes": [],
    },
    "frontend": {
        "tokens": [
            "react", "vue", "angular", "css", "html", "ui", "ux",
            "svelte", "tailwind", "theme", "storybook", "frontend",
            "remotion", "threejs",
        ],
        "substrings": [
            "react-", "-react", "angular", "vue-", "-vue",
            "svelte", "nextjs", "nuxt", "tailwind", "css-", "-css",
            "html-", "design-system", "storybook", "figma",
            "avalonia", "3d-web", "radix-ui", "ui-ux",
            "ui-visual", "ui-skills", "theme-",
            "app-builder", "web-design", "canvas-design",
            "remotion", "interactive-portfolio", "frontend-design",
            "chrome-extension", "browser-extension", "i18n-",
            "multi-platform-", "zustand",
            "astro", "shadcn", "scroll-experience", "spline-3d",
            "progressive-web-app", "chat-widget", "favicon",
            "magic-animator", "fixing-motion-", "animejs",
            "tanstack-query", "electron-develop",
        ],
        "prefixes": ["react-", "angular-", "vue-", "ui-", "hig-", "makepad-", "robius-"],
        "excludes": [
            "linux-privilege-escalation",
            "linux-shell-scripting",
            "linux-troubleshooting",
            "c4-component",
            "html-injection-testing",
            "xss-html-injection",
        ],
    },
    "devops": {
        "tokens": [
            "devops", "docker", "k8s", "terraform", "aws", "azure",
            "gcp", "ci", "cd", "helm", "ansible", "github",
        ],
        "substrings": [
            "devops", "docker", "kubernetes", "terraform", "aws-",
            "github-actions", "ci-cd", "deploy", "infra",
            "cloud-", "helm", "ansible", "azd-",
            "pipeline-", "-pipeline", "observability",
            "monitoring-", "-monitor", "container",
            "registry", "gitlab-ci",
            "git-", "gitops", "linux-", "posix-",
            "powershell", "incident-", "performance-",
            "slo-", "grafana-", "prometheus-",
            "service-mesh", "istio-", "linkerd-",
            "distributed-", "on-call", "bazel-", "busybox",
            "github-issue", "create-pr", "git-push", "iterate-pr",
            "using-git", "github-", "os-script",
            "cloudformation", "cdk-", "monorepo-", "turborepo",
            "nx-workspace", "shellcheck", "dependency-upgrade",
            "environment-setup", "network-",
            "finishing-a-development-branch", "create-branch",
            "windows-shell", "uv-package-manager",
        ],
        "prefixes": [
            "aws-", "azure-", "gcp-", "k8s-", "docker-",
            "terraform-", "deployment-",
        ],
        "excludes": [],
    },
    "security": {
        "tokens": [
            "security", "pentest", "auth", "encryption", "vulnerability",
            "vulnerabilities", "hacking", "malware", "forensic", "threat", "owasp",
        ],
        "substrings": [
            "security", "pentest", "penetration", "vulnerability", "vulnerabilities",
            "attack", "auth-", "oauth", "jwt", "gdpr", "compliance",
            "crypto-", "anti-reversing", "api-security",
            "active-directory", "authentication", "hacking",
            "malware", "forensic", "threat", "privilege-escalation",
            "privilege-esc", "exploit", "xss", "csrf", "injection",
            "phish", "sanitiz", "firewall",
            "red-team", "metasploit", "shodan", "binary-analysis",
            "protocol-reverse", "scanning", "sast-",
            "web-severity", "memory-safety", "wireshark",
            "secrets-manag", "web-scanning",
            "traversal", "mtls", "reverse-engineer",
            "burpsuite", "ffuf-", "semgrep-",
            "privacy-by-design", "varlock",
        ],
        "prefixes": ["security-"],
        "excludes": [
            "seo-forensic-incident-response",
        ],
    },
    "testing": {
        "tokens": [
            "test", "tests", "testing", "e2e", "qa", "spec",
            "playwright", "pytest", "jest", "vitest",
            "tdd", "debug", "debugger",
        ],
        "substrings": [
            "test-", "-test", "testing", "playwright", "pytest",
            "jest-", "vitest", "cucumber", "e2e-", "-e2e",
            "qa-", "-qa", "evaluation", "audit",
            "lint-", "coverage", "static-analysis",
            "tdd-", "debug-", "debugg", "find-bugs",
            "error-detective", "error-debug", "error-diagnostic",
            "fix-review", "code-review", "systematic-debug",
            "comprehensive-review", "postmortem", "quality-nonconform",
            "verification-before", "pr-enhance",
            "bug-hunter", "differential-review",
            "lighthouse-scanner", "gdb-cli", "codex-review",
        ],
        "prefixes": ["test-"],
        "excludes": [
            "backtesting-frameworks",
        ],
    },
    "mobile": {
        "tokens": [
            "mobile", "ios", "android", "flutter",
            "swiftui", "kotlin", "expo",
        ],
        "substrings": [
            "mobile", "react-native", "flutter", "ios-", "-ios",
            "android", "jetpack", "swiftui", "kotlin-",
            "macos-spm", "macos-menubar", "tuist-",
        ],
        "prefixes": ["expo-", "mobile-"],
        "excludes": [
            "azure-monitor-opentelemetry-exporter-java",
            "azure-monitor-opentelemetry-exporter-py",
        ],
    },
    "data": {
        "tokens": [
            "data", "etl", "analytics", "warehouse", "lakehouse",
            "dbt", "spark", "airflow",
        ],
        "substrings": [
            "data-engineering", "data-pipeline", "data-lake",
            "data-warehouse", "dbt-", "etl-", "spark-",
            "airflow-", "analytics-", "bigquery", "snowflake",
            "databricks", "redshift", "quant-", "backtesting",
            "matplotlib", "networkx", "plotly", "polars",
            "seaborn", "statsmodels", "sympy", "scikit-learn",
            "scanpy", "alpha-vantage", "xvary-stock",
            "astropy", "biopython", "molykit",
            "geo-fundamental", "clickhouse",
        ],
        "prefixes": ["data-"],
        "excludes": [
            "azure-data-tables-java",
            "azure-data-tables-py",
        ],
    },
    "automation": {
        "tokens": ["automation", "telegram"],
        "substrings": [
            "automation", "automate-", "auto-",
            "workflow", "zapier", "n8n",
            "firebase", "hubspot", "stripe-",
            "paypal", "salesforce", "shopify",
            "slack-", "telegram-", "twilio",
            "wordpress", "inngest", "segment-",
            "trigger-dev", "upstash", "conductor-",
            "firecrawl", "scraper", "report-gen",
            "automat",
            "apify-", "linkedin-cli", "observe-whatsapp",
            "amazon-alexa", "x-article-publisher", "instagram",
            "unsplash-integration",
        ],
        "prefixes": [],
        "excludes": [
            "azure-communication-callautomation-java",
        ],
    },
    "architecture": {
        "tokens": ["architecture", "architect"],
        "substrings": [
            "architecture", "architect", "design-pattern",
            "system-design", "c4-", "microservice",
            "event-driven", "domain-driven", "ddd-",
            "clean-architecture", "hexagonal",
            "cqrs-", "event-store", "saga-", "projection-",
            "refactor", "tech-debt", "clean-code",
            "codebase-cleanup", "legacy-", "code-refact",
            "framework-migration", "error-handling",
            "design-orchestrat", "coding-standard", "design-md",
            "concise-planning", "executing-plans", "full-stack-orchestration",
            "senior-fullstack", "uncle-bob", "composition-pattern",
            "progressive-estimation", "analyze-project", "blueprint",
            "closed-loop-delivery", "tool-design", "plan-writing",
            "planning-with-files", "clarity-gate", "dx-optimizer",
            "simplify-code", "product-design", "project-development",
            "acceptance-orchestrator",
        ],
        "prefixes": ["c4-"],
        "excludes": [],
    },
    "language": {
        "tokens": [
            "python", "golang", "go", "rust", "java", "typescript",
            "csharp", "ruby", "elixir", "swift", "php", "lua",
            "cpp", "dotnet", "bash",
            "javascript", "haskell", "scala", "julia", "c", "bun",
        ],
        "substrings": [
            "python-", "golang-", "rust-", "typescript-",
            "ruby-", "elixir-", "php-", "lua-",
            "dotnet-", "csharp-", "bash-",
            "javascript-", "haskell-", "scala-", "julia-",
            "bun-", "nodejs-", "modern-javascript",
        ],
        "prefixes": [
            "python-", "go-", "rust-", "typescript-",
            "java-", "dotnet-", "ruby-", "bash-",
            "fp-ts-", "fp-",
        ],
        "excludes": [],
        "skip_prefix": ["azure-"],
    },
    "content": {
        "tokens": [
            "seo", "copywriting", "branding", "marketing",
            "blog", "newsletter", "content", "prose",
        ],
        "substrings": [
            "seo-", "copywriting", "brand-", "marketing",
            "blog-", "newsletter", "content-", "editorial",
            "social-media", "landing-page",
            "wiki-", "obsidian-", "readme", "documentation",
            "writing-", "copy-editing", "podcast",
            "youtube-", "screenshot", "email-sequence", "email-system",
            "docx-", "pptx-", "xlsx-", "pdf-official",
            "app-store-optim", "beautiful-prose",
            "-cro", "paid-ads", "referral-",
            "professional-proofreader", "scientific-writing",
            "lead-magnets", "app-store-changelog",
            "ad-creative", "viral-generator", "cold-email",
            "nanobanana-ppt", "citation-management",
        ],
        "prefixes": ["seo-", "brand-", "wiki-"],
        "excludes": [],
    },

    # ─── GAMEDEV (2026) ──────────────────────────────────────────────
    "gamedev": {
        "tokens": ["game", "unity", "godot", "bevy", "shader", "minecraft"],
        "substrings": [
            "game-", "unity-", "godot-", "bevy-", "shader-",
            "game-development", "bukkit-",
        ],
        "prefixes": [],
        "excludes": [],
    },

    # ─── BUSINESS & STARTUPS (2026) ───────────────────────────────────
    "business": {
        "tokens": ["startup", "business", "analyst"],
        "substrings": [
            "startup-", "business-analyst", "competitive-landscape",
            "market-sizing", "cost-optimization", "pricing-strategy",
            "financial-modeling", "financial-projection", "kpi-",
            "product-manager", "risk-manager", "risk-metrics",
            "customer-support", "launch-strategy",
            "hr-", "legal-", "logistics-", "employment-",
            "inventory-", "returns-", "carrier-",
            "churn-prevention", "competitor-alternative",
            "growth-engine", "jobgpt", "monetization", "revops",
            "sales-enablement", "production-scheduling",
            "saas-mvp-launcher", "micro-saas-", "interview-coach",
            "energy-procurement", "free-tool-strategy",
            "team-collaboration", "team-composition",
            "product-inventor", "sred-", "oss-hunter",
        ],
        "prefixes": ["startup-", "revops-"],
        "excludes": [],
    },

    # ─── WEB3 & BLOCKCHAIN (2026) ─────────────────────────────────────
    "web3": {
        "tokens": ["blockchain", "solidity", "defi", "nft", "web3", "crypto"],
        "substrings": [
            "blockchain", "solidity", "defi-", "nft-",
            "web3", "ethereum", "bitcoin", "blockrun",
            "smart-contract",
        ],
        "prefixes": [],
        "excludes": [],
    },

    # ─── HEALTH & WELLNESS (2026) ─────────────────────────────────────
    "health": {
        "tokens": ["health", "nutrition", "fitness", "wellness", "medical", "clinical"],
        "substrings": [
            "health-analyzer", "health-trend", "nutrition-", "fitness-analyzer",
            "sleep-analyzer", "weightloss-", "rehabilitation-",
            "tcm-constitution", "yes-md", "wellally",
            "mental-health", "skin-health", "oral-health",
            "sexual-health", "travel-health", "occupational-health",
            "family-health",
        ],
        "prefixes": [],
        "excludes": [],
    },

    # ─── LEGAL & JURÍDICO (2026) ──────────────────────────────────────
    "legal": {
        "tokens": ["advogado", "juridico"],
        "substrings": [
            "leiloeiro", "advogado-", "juridico",
            "junta-leiloeiro",
        ],
        "prefixes": ["advogado-", "leiloeiro-"],
        "excludes": [],
    },
}

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
    "other": "📦",
}


def categorize_skill_name(skill_name: str) -> list[str]:
    """Categoriza uma skill pelo nome da pasta — roda em tempo real, sem arquivo externo."""
    name_lower = skill_name.lower()
    tokens = set(name_lower.split("-"))
    categories: list[str] = []

    for category, rules in CATEGORY_RULES.items():
        if skill_name in rules.get("excludes", []):
            continue

        skip = False
        for sp in rules.get("skip_prefix", []):
            if name_lower.startswith(sp):
                skip = True
                break
        if skip:
            continue

        matched = False

        for token in rules.get("tokens", []):
            if token in tokens:
                matched = True
                break

        if not matched:
            for prefix in rules.get("prefixes", []):
                if name_lower.startswith(prefix):
                    matched = True
                    break

        if not matched:
            for sub in rules.get("substrings", []):
                if sub in name_lower:
                    matched = True
                    break

        if matched:
            categories.append(category)

    return sorted(categories) if categories else ["other"]


# ---------------------------------------------------------------------------
# SKILL DISCOVERY & METADATA
# ---------------------------------------------------------------------------

# Conjunto de categorias reconhecidas como pastas de categoria no SKILLS_PATH
_KNOWN_CATEGORIES: frozenset[str] = frozenset(CATEGORY_RULES.keys()) | {"other"}


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

        if folder_category:
            # Pasta como fonte de verdade: categoria primaria = pasta pai.
            # Categorias secundarias vem da analise do nome (sem duplicar a primaria).
            secondary = [c for c in categorize_skill_name(skill_name) if c != folder_category]
            categories = [folder_category] + secondary
        else:
            categories = categorize_skill_name(skill_name)

        return {
            "name": skill_name,
            "description": description or "Advanced skill",
            "path": str(skill_dir),
            "skill_md_preview": content[:1000],
            "full_content_path": str(skill_md),
            "categories": categories,
        }
    except Exception as e:
        logger.error(f"Erro ao ler skill {skill_dir.name}: {e}")
        return None


def discover_skills() -> list[dict[str, Any]]:
    """Descobre e categoriza TODAS as skills em c:\\skills em tempo real.

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
            # Layout flat — skill direto na raiz, usa analise de nome
            skill_info = get_skill_info(item)
            if skill_info:
                skills.append(skill_info)
        elif item.name in _KNOWN_CATEGORIES:
            # Layout categorizado — pasta pai e' a categoria primaria
            for subitem in item.iterdir():
                if subitem.is_dir() and not subitem.name.startswith("."):
                    skill_info = get_skill_info(subitem, folder_category=item.name)
                    if skill_info:
                        skills.append(skill_info)
        else:
            # Pasta desconhecida sem SKILL.md — ignora
            logger.debug(f"Pasta ignorada (nao e categoria conhecida): {item.name}")

    logger.debug(f"Descobertas {len(skills)} skills com categorizacao automatica")
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
    """Busca e lista skills por palavra-chave, ou lista todas as categorias disponíveis"""
    if query:
        return [{"role": "user", "content": f"Use search_skills('{query}') e me mostre as skills encontradas."}]
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
        partial = [s for s in skills if skill_name.lower() in s["name"].lower()]
        if partial:
            names = "\n".join(f"  - {s['name']} [{', '.join(s.get('categories',[]))}]" for s in partial[:10])
            return f"Skill '{skill_name}' nao encontrada.\n\nVoce quis dizer:\n{names}"
        return f"Skill '{skill_name}' nao encontrada. Use list_categories() ou search_skills() para encontrar."

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


@mcp.tool()
async def search_skills(query: str) -> str:
    """
    Busca skills por nome, descricao ou categoria. Busca textual em todo o catalogo.

    Args:
        query: Termo de busca (ex: 'typescript', 'performance', 'database', 'react', 'prompt', 'security')
    """
    skills = get_skills()
    q = query.lower()

    matching = [
        s for s in skills
        if q in s["name"].lower()
        or q in s["description"].lower()
        or q in " ".join(s.get("categories", []))
    ]

    if not matching:
        return f"Nenhuma skill encontrada para '{query}'. Tente termos mais genericos."

    response = f"Busca: '{query}' - {len(matching)} resultado(s)\n\n"

    for idx, skill in enumerate(matching[:30], 1):
        cats = ", ".join(skill.get("categories", ["other"]))
        response += f"{idx}. **{skill['name']}** [{cats}]\n"
        response += f"   {skill['description']}\n\n"

    if len(matching) > 30:
        response += f"_...e mais {len(matching) - 30} resultados_"

    return response


# ---------------------------------------------------------------------------
# BM25 index cache
# ---------------------------------------------------------------------------
_bm25_index: Any = None
_bm25_skills: list[dict] = []
_bm25_built_at: float = 0.0
_BM25_TTL = 300  # segundos


def _build_bm25_index(skills: list[dict]) -> Any:
    """Constrói índice BM25 sobre nomes + primeiras linhas dos SKILL.md."""
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        return None

    corpus: list[list[str]] = []
    for skill in skills:
        # Tokenizar nome (substitui hífens por espaços, split)
        name_tokens = skill["name"].replace("-", " ").replace("_", " ").split()
        # Adicionar categoria como tokens extras
        cat_tokens: list[str] = []
        for cat in skill.get("categories", []):
            cat_tokens.extend(cat.split("-"))
        # Ler primeiras linhas do SKILL.md para mais contexto
        skill_dir = SKILLS_PATH / skill["name"]
        skill_md = skill_dir / "SKILL.md"
        content_tokens: list[str] = []
        if skill_md.exists():
            try:
                first_lines = skill_md.read_text(encoding="utf-8", errors="ignore")[:400]
                # Tokenizar: só palavras alfanuméricas
                import re
                content_tokens = re.findall(r"[a-zA-Z0-9]+", first_lines.lower())
            except Exception:
                pass

        all_tokens = name_tokens + cat_tokens + content_tokens
        corpus.append([t.lower() for t in all_tokens if len(t) > 1])

    return BM25Okapi(corpus)


def _get_bm25(skills: list[dict]) -> Any:
    """Retorna índice BM25 construído (com cache TTL)."""
    global _bm25_index, _bm25_skills, _bm25_built_at
    now = time.time()
    if _bm25_index is None or (now - _bm25_built_at) > _BM25_TTL or len(skills) != len(_bm25_skills):
        logger.info("Construindo índice BM25 para %d skills...", len(skills))
        _bm25_index = _build_bm25_index(skills)
        _bm25_skills = skills
        _bm25_built_at = now
    return _bm25_index


@mcp.tool()
async def semantic_search_skills(query: str, top_k: int = 15) -> str:
    """
    Busca semântica por relevância usando BM25. Vai MUITO além do substring match —
    entende contexto, sinônimos parciais e relevância multi-token.

    Use isso quando search_skills não encontrar o que você quer.
    Exemplos: 'deploy container cloud', 'autenticação jwt api', 'machine learning pipeline',
              'scraping web automation', 'pagamentos stripe checkout'.

    Args:
        query: Consulta em linguagem natural (ex: 'deploy agent on Azure', 'react state management')
        top_k: Número de resultados (padrão: 15, máximo: 30)
    """
    skills = get_skills()
    if not skills:
        return "Nenhuma skill disponível."

    top_k = min(max(top_k, 1), 30)

    bm25 = _get_bm25(skills)
    if bm25 is None:
        return (
            "❌ rank_bm25 não instalado. Execute: pip install rank-bm25\n"
            "   Por enquanto, use search_skills() para busca por substring."
        )

    # Tokenizar a query
    query_tokens = [t.lower() for t in re.findall(r"[a-zA-Z0-9]+", query) if len(t) > 1]
    if not query_tokens:
        return "Query inválida. Use palavras como: 'deploy azure', 'react hooks', 'ml pipeline'."

    scores = bm25.get_scores(query_tokens)

    # Combinar score com índice e ordenar
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    top_results = [(skills[i], score) for i, score in ranked[:top_k] if score > 0]

    if not top_results:
        return (
            f"Nenhum resultado relevante para '{query}'.\n"
            f"Tente search_skills('{query}') para busca por substring,\n"
            f"ou list_categories() para ver todas as categorias."
        )

    response = f"🔍 Busca semântica (BM25): **'{query}'** → {len(top_results)} resultado(s)\n\n"
    for idx, (skill, score) in enumerate(top_results, 1):
        cats = ", ".join(skill.get("categories", ["other"]))
        response += f"{idx}. **{skill['name']}** [{cats}] _(score: {score:.2f})_\n"
        if skill.get("description"):
            response += f"   {skill['description']}\n"
        response += "\n"

    response += "---\n"
    response += f"_Para invocar uma skill: `invoke_skill('nome-da-skill')`_"
    return response


@mcp.tool()
async def list_categories() -> str:
    """
    Lista todas as 18 categorias disponiveis com contagem de skills.
    Categorias: accessibility, ai, backend, frontend, devops, security, testing, mobile, data, automation, architecture, language, content, gamedev, business, web3, health, legal.
    Para busca avancada use semantic_search_skills(query).
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
    for cat in sorted(CATEGORY_RULES.keys()):
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
