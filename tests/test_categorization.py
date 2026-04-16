"""Unit tests for categorize_skill_name() — the categorization engine."""
import pytest

import mcp_server


# ── Frontend ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", [
    "react-hooks",
    "react-best-practices",
    "nextjs-starter",
    "tailwind-components",
    "svelte-transition",
    "vue-composition-api",
])
def test_frontend_skills(name: str) -> None:
    assert "frontend" in mcp_server.categorize_skill_name(name)


# ── DevOps & Cloud ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", [
    "docker-compose",
    "kubernetes-deploy",
    "terraform-aws",
    "github-actions",
    "aws-lambda",
    "deployment-pipeline",
])
def test_devops_skills(name: str) -> None:
    assert "devops" in mcp_server.categorize_skill_name(name)


# ── AI & Agents ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", [
    "agent-customization",
    "llm-prompt-engineering",
    "rag-pipeline",
    "embedding-search",
    "chatbot-design",
    "multi-agent-framework",
    "claude-integration",
    "openai-tools",
])
def test_ai_skills(name: str) -> None:
    assert "ai" in mcp_server.categorize_skill_name(name)


# ── Backend ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", [
    "graphql-api",
    "fastapi-backend",
    "prisma-database",
    "rest-api-design",
    "postgres-optimization",
    "redis-caching",
    "kafka-consumer",
    "webhook-handler",
])
def test_backend_skills(name: str) -> None:
    assert "backend" in mcp_server.categorize_skill_name(name)


# ── Security ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", [
    "security-owasp-testing",
    "pentest-web",
    "auth-jwt-oauth",
    "xss-prevention",
    "security-audit",
])
def test_security_skills(name: str) -> None:
    assert "security" in mcp_server.categorize_skill_name(name)


# ── Testing & QA ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", [
    "pytest-best-practices",
    "playwright-e2e",
    "jest-unit-testing",
    "test-automation",
    "vitest-react",
    "qa-checklist",
])
def test_testing_skills(name: str) -> None:
    assert "testing" in mcp_server.categorize_skill_name(name)


# ── Mobile ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", [
    "react-native-expo",
    "flutter-mobile",
    "android-jetpack",
])
def test_mobile_skills(name: str) -> None:
    assert "mobile" in mcp_server.categorize_skill_name(name)


# ── Data Engineering ───────────────────────────────────────────────────────

@pytest.mark.parametrize("name", [
    "data-pipeline",
    "dbt-models",
    "spark-etl",
    "bigquery-analytics",
    "data-warehouse",
])
def test_data_skills(name: str) -> None:
    assert "data" in mcp_server.categorize_skill_name(name)


# ── Architecture ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", [
    "clean-architecture",
    "system-design-patterns",
    "refactor-legacy-code",
    "design-patterns-solid",
])
def test_architecture_skills(name: str) -> None:
    assert "architecture" in mcp_server.categorize_skill_name(name)


# ── Language-specific ──────────────────────────────────────────────────────

@pytest.mark.parametrize("name", [
    "python-typing",
    "typescript-patterns",
    "rust-ownership",
    "golang-concurrency",
    "python-async",
])
def test_language_skills(name: str) -> None:
    assert "language" in mcp_server.categorize_skill_name(name)


# ── Automation ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", [
    "automation-workflow",
    "n8n-integration",
    "slack-bot",
    "stripe-integration",
])
def test_automation_skills(name: str) -> None:
    assert "automation" in mcp_server.categorize_skill_name(name)


# ── Content & Marketing ────────────────────────────────────────────────────

@pytest.mark.parametrize("name", [
    "seo-optimization",
    "blog-writing",
    "copywriting-guide",
])
def test_content_skills(name: str) -> None:
    assert "content" in mcp_server.categorize_skill_name(name)


# ── Fallback to "other" ────────────────────────────────────────────────────

@pytest.mark.parametrize("name", [
    "completely-unknown-xyz-skill",
    "random-uncategorized-thing-abc",
])
def test_fallback_to_other(name: str) -> None:
    result = mcp_server.categorize_skill_name(name)
    assert result == ["other"]


# ── Type and structure contracts ───────────────────────────────────────────

def test_returns_list() -> None:
    result = mcp_server.categorize_skill_name("react-hooks")
    assert isinstance(result, list)
    assert len(result) >= 1


def test_returns_non_empty_list() -> None:
    result = mcp_server.categorize_skill_name("docker-compose")
    assert len(result) >= 1
    for item in result:
        assert isinstance(item, str)


def test_output_is_sorted() -> None:
    """Categories in result must be sorted alphabetically."""
    result = mcp_server.categorize_skill_name("python-pytest-testing")
    assert result == sorted(result)


def test_multi_category_skill() -> None:
    """Skills can belong to multiple categories."""
    result = mcp_server.categorize_skill_name("pytest-best-practices")
    assert "testing" in result
    assert len(result) >= 1


def test_exclude_rule_ai() -> None:
    """Skills in ai.excludes must not be classified as ai."""
    result = mcp_server.categorize_skill_name("bullmq-specialist")
    assert "ai" not in result


def test_all_categories_have_icons() -> None:
    """Every category defined in CATEGORY_RULES must have an entry in CATEGORY_ICONS."""
    for cat in mcp_server.CATEGORY_RULES:
        assert cat in mcp_server.CATEGORY_ICONS, f"Missing icon for category: {cat}"


def test_other_category_has_icon() -> None:
    assert "other" in mcp_server.CATEGORY_ICONS


def test_empty_string_falls_back_to_other() -> None:
    result = mcp_server.categorize_skill_name("")
    assert result == ["other"]
