#!/usr/bin/env python3
"""
Categoriza skills baseado no nome da pasta.
Abordagem: tokens exatos > prefixes > substrings, com exclusões.

Categorias:
  accessibility, ai, backend, frontend, devops, security, testing,
  mobile, data, automation, architecture, language, content,
  gamedev, business, web3, other
"""

import json
from pathlib import Path

SKILLS_PATH = Path("c:/skills")
OUTPUT_FILE = Path(__file__).parent / "categories.json"


# ─── Regras por categoria ───────────────────────────────────────────────────
# tokens:     match exato em tokens separados por "-" (ex: "ai" em "ai-product")
# substrings: match parcial no nome completo (ex: "agent" em "multi-agent-patterns")
# prefixes:   match no início do nome (ex: "azure-ai-" em "azure-ai-vision-...")
# excludes:   nomes que NÃO devem entrar nesta categoria mesmo com match

NAME_RULES: dict[str, dict] = {
    # ─── ACCESSIBILITY ───────────────────────────────────────────────
    "accessibility": {
        "tokens": ["accessibility", "a11y", "wcag", "aria", "accessible"],
        "substrings": ["accessibility", "a11y", "wcag"],
        "prefixes": [],
        "excludes": [],
    },

    # ─── AI & AGENTES ────────────────────────────────────────────────
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
            "bullmq-specialist",        # é backend queue, não AI
            "fp-ts-pragmatic",           # fp-ts, não "rag"
            "brand-guidelines-anthropic", # branding, não AI tech
            "internal-comms-anthropic",   # comunicação interna
        ],
    },

    # ─── BACKEND ─────────────────────────────────────────────────────
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

    # ─── FRONTEND ────────────────────────────────────────────────────
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
            # Linux skills NÃO são frontend
            "linux-privilege-escalation",
            "linux-shell-scripting",
            "linux-troubleshooting",
            # C4 architecture != frontend
            "c4-component",
            # Security testing != frontend
            "html-injection-testing",
            "xss-html-injection",
        ],
    },

    # ─── DEVOPS & CLOUD ──────────────────────────────────────────────
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
        "excludes": [
            # OpenTelemetry exporters NÃO são mobile
            # (tratado no mobile excludes)
        ],
    },

    # ─── SECURITY ────────────────────────────────────────────────────
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
            "seo-forensic-incident-response",  # SEO, não security
        ],
    },

    # ─── TESTING & QA ────────────────────────────────────────────────
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
            "backtesting-frameworks",  # finanças, não QA
        ],
    },

    # ─── MOBILE ──────────────────────────────────────────────────────
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
            # opentelemetry exporter NÃO é mobile
            "azure-monitor-opentelemetry-exporter-java",
            "azure-monitor-opentelemetry-exporter-py",
        ],
    },

    # ─── DATA ENGINEERING (NOVA) ─────────────────────────────────────
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
            # azure-data-tables é mais devops/cloud
            "azure-data-tables-java",
            "azure-data-tables-py",
        ],
    },

    # ─── AUTOMATION (NOVA) ───────────────────────────────────────────
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
            # Azure-specific automations stay in devops
            "azure-communication-callautomation-java",
        ],
    },

    # ─── ARCHITECTURE (NOVA) ─────────────────────────────────────────
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

    # ─── LANGUAGE-SPECIFIC (NOVA) ────────────────────────────────────
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
        "excludes": [
            # Azure SDK skills por linguagem ficam em devops, não language
            # Excluir qualquer azure-*
        ],
        # Special: skip azure-* skills for this category
        "skip_prefix": ["azure-"],
    },

    # ─── CONTENT & MARKETING (NOVA) ──────────────────────────────────
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


def categorize_by_name(skill_name: str) -> list[str]:
    """Detecta categorias usando o nome da pasta"""
    name_lower = skill_name.lower()
    tokens = set(name_lower.split("-"))
    categories: list[str] = []

    for category, rules in NAME_RULES.items():
        # Check excludes first
        if skill_name in rules.get("excludes", []):
            continue

        # Check skip_prefix (e.g., azure-* skills skip "language" category)
        skip = False
        for sp in rules.get("skip_prefix", []):
            if name_lower.startswith(sp):
                skip = True
                break
        if skip:
            continue

        matched = False

        # 1. Tokens exatos do nome (highest priority)
        for token in rules.get("tokens", []):
            if token in tokens:
                matched = True
                break

        # 2. Prefixes do nome
        if not matched:
            for prefix in rules.get("prefixes", []):
                if name_lower.startswith(prefix):
                    matched = True
                    break

        # 3. Substrings no nome completo
        if not matched:
            for sub in rules.get("substrings", []):
                if sub in name_lower:
                    matched = True
                    break

        if matched:
            categories.append(category)

    return sorted(categories) if categories else ["other"]


def main():
    print("Categorizando skills por nome de pasta...")
    print(f"Categorias: {list(NAME_RULES.keys())}")

    if not SKILLS_PATH.exists():
        print(f"ERRO: {SKILLS_PATH} nao existe")
        return 1

    categories_map: dict[str, list[str]] = {}

    skill_dirs = sorted(
        [d for d in SKILLS_PATH.iterdir() if d.is_dir() and not d.name.startswith(".")],
        key=lambda d: d.name,
    )

    for skill_dir in skill_dirs:
        if (skill_dir / "SKILL.md").exists():
            cats = categorize_by_name(skill_dir.name)
            categories_map[skill_dir.name] = cats

    # Salva
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(categories_map, f, indent=2, ensure_ascii=False)

    # Estatísticas
    total = len(categories_map)
    cat_count: dict[str, int] = {}
    for cats in categories_map.values():
        for c in cats:
            cat_count[c] = cat_count.get(c, 0) + 1

    print(f"\n{total} skills categorizadas\n")
    print("Distribuicao:")
    for cat, count in sorted(cat_count.items(), key=lambda x: x[1], reverse=True):
        pct = count * 100 / total
        bar = "#" * int(pct / 2)
        print(f"  {cat:20s}: {count:4d} ({pct:5.1f}%) {bar}")

    # Preview de cada categoria
    for cat in sorted(NAME_RULES.keys()):
        examples = [name for name, cats in categories_map.items() if cat in cats]
        if examples:
            print(f"\n'{cat}' ({len(examples)} total) — primeiras 5:")
            for s in examples[:5]:
                print(f"  - {s}")

    print(f"\nSalvo em: {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    exit(main())
