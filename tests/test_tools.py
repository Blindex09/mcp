"""Tests for tool functions: category lists, search, invoke, pagination."""
from pathlib import Path
from unittest.mock import patch

import pytest

import mcp_server


# ── build_category_response ────────────────────────────────────────────────

def test_build_category_response_returns_matching(sample_skills: list[dict]) -> None:
    result = mcp_server.build_category_response(sample_skills, "frontend", "🎨", "Frontend", 0)
    assert "🎨" in result
    assert "Frontend" in result
    assert "react-best-practices" in result


def test_build_category_response_empty_list() -> None:
    result = mcp_server.build_category_response([], "frontend", "🎨", "Frontend", 0)
    assert "Nenhuma skill" in result


def test_build_category_response_category_not_present(sample_skills: list[dict]) -> None:
    result = mcp_server.build_category_response(sample_skills, "health", "🏥", "Saúde", 0)
    assert "Nenhuma skill" in result


def test_build_category_response_limit_truncates() -> None:
    many_skills = [
        {"name": f"ai-skill-{i}", "description": "desc", "categories": ["ai"]}
        for i in range(6)
    ]
    result = mcp_server.build_category_response(many_skills, "ai", "🤖", "AI", limit=3)
    assert "e mais 3 skills" in result


def test_build_category_response_limit_zero_returns_all(sample_skills: list[dict]) -> None:
    """limit=0 should return all skills in the category."""
    ai_skills = [s for s in sample_skills if "ai" in s["categories"]]
    result = mcp_server.build_category_response(sample_skills, "ai", "🤖", "AI", limit=0)
    for skill in ai_skills:
        assert skill["name"] in result


# ── Category list tools ────────────────────────────────────────────────────

async def test_list_ai_skills(sample_skills: list[dict]) -> None:
    with patch("mcp_server.get_skills", return_value=sample_skills):
        result = await mcp_server.list_ai_skills(limit=0)
    assert "🤖" in result
    assert "agent-customization" in result


async def test_list_frontend_skills(sample_skills: list[dict]) -> None:
    with patch("mcp_server.get_skills", return_value=sample_skills):
        result = await mcp_server.list_frontend_skills(limit=0)
    assert "react-best-practices" in result


async def test_list_devops_skills(sample_skills: list[dict]) -> None:
    with patch("mcp_server.get_skills", return_value=sample_skills):
        result = await mcp_server.list_devops_skills(limit=0)
    assert "docker-compose" in result


async def test_list_backend_skills(sample_skills: list[dict]) -> None:
    with patch("mcp_server.get_skills", return_value=sample_skills):
        result = await mcp_server.list_backend_skills(limit=0)
    assert "graphql-api" in result


async def test_list_testing_skills(sample_skills: list[dict]) -> None:
    with patch("mcp_server.get_skills", return_value=sample_skills):
        result = await mcp_server.list_testing_skills(limit=0)
    assert "pytest-best-practices" in result


async def test_list_security_skills(sample_skills: list[dict]) -> None:
    with patch("mcp_server.get_skills", return_value=sample_skills):
        result = await mcp_server.list_security_skills(limit=0)
    assert "security-owasp-testing" in result


async def test_list_mobile_skills(sample_skills: list[dict]) -> None:
    with patch("mcp_server.get_skills", return_value=sample_skills):
        result = await mcp_server.list_mobile_skills(limit=0)
    assert "react-native-expo" in result


async def test_list_data_skills(sample_skills: list[dict]) -> None:
    with patch("mcp_server.get_skills", return_value=sample_skills):
        result = await mcp_server.list_data_skills(limit=0)
    assert "data-pipeline" in result


async def test_category_with_no_matching_skills(sample_skills: list[dict]) -> None:
    """Categories not present in sample data should return empty message."""
    with patch("mcp_server.get_skills", return_value=sample_skills):
        result = await mcp_server.list_health_skills(limit=0)
    assert "Nenhuma skill" in result


async def test_category_tool_with_limit(sample_skills: list[dict]) -> None:
    # Add multiple ai skills to verify limit works
    many_ai = [
        {"name": f"ai-tool-{i}", "description": "AI skill", "categories": ["ai"],
         "path": f"/skills/ai-tool-{i}", "skill_md_preview": "", "full_content_path": ""}
        for i in range(5)
    ]
    all_skills = sample_skills + many_ai
    with patch("mcp_server.get_skills", return_value=all_skills):
        result = await mcp_server.list_ai_skills(limit=2)
    assert "e mais" in result


# ── list_categories ────────────────────────────────────────────────────────

async def test_list_categories_shows_counts(sample_skills: list[dict]) -> None:
    with patch("mcp_server.get_skills", return_value=sample_skills):
        result = await mcp_server.list_categories()
    assert "frontend" in result
    assert "ai" in result
    assert "devops" in result
    assert "backend" in result


async def test_list_categories_empty_skills() -> None:
    with patch("mcp_server.get_skills", return_value=[]):
        result = await mcp_server.list_categories()
    assert "Nenhuma" in result


async def test_list_categories_shows_total(sample_skills: list[dict]) -> None:
    with patch("mcp_server.get_skills", return_value=sample_skills):
        result = await mcp_server.list_categories()
    assert str(len(sample_skills)) in result


# ── list_all_skills ─────────────────────────────────────────────────────────

async def test_list_all_skills_first_page(sample_skills: list[dict]) -> None:
    with patch("mcp_server.get_skills", return_value=sample_skills):
        result = await mcp_server.list_all_skills(page=1, per_page=3)
    assert "Pagina 1" in result


async def test_list_all_skills_second_page(sample_skills: list[dict]) -> None:
    with patch("mcp_server.get_skills", return_value=sample_skills):
        result = await mcp_server.list_all_skills(page=2, per_page=3)
    assert "Pagina 2" in result


async def test_list_all_skills_per_page_capped_at_100() -> None:
    skills = [
        {"name": f"skill-{i}", "description": "x", "categories": ["ai"],
         "path": "", "skill_md_preview": "", "full_content_path": ""}
        for i in range(5)
    ]
    with patch("mcp_server.get_skills", return_value=skills):
        result = await mcp_server.list_all_skills(page=1, per_page=999)
    # All 5 skills fit on one page when capped at 100
    assert "Pagina 1 de 1" in result


async def test_list_all_skills_empty() -> None:
    with patch("mcp_server.get_skills", return_value=[]):
        result = await mcp_server.list_all_skills(page=1, per_page=50)
    assert "Nenhuma" in result


# ── invoke_skill ───────────────────────────────────────────────────────────

async def test_invoke_skill_found(sample_skills: list[dict], tmp_path: Path) -> None:
    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text("# React Best Practices\n\nFull content here.", encoding="utf-8")
    patched = [
        {**s, "full_content_path": str(skill_md)}
        if s["name"] == "react-best-practices"
        else s
        for s in sample_skills
    ]
    with patch("mcp_server.get_skills", return_value=patched):
        result = await mcp_server.invoke_skill("react-best-practices")
    assert "React Best Practices" in result
    assert "Full content here." in result


async def test_invoke_skill_case_insensitive(sample_skills: list[dict], tmp_path: Path) -> None:
    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text("# Content", encoding="utf-8")
    patched = [
        {**s, "full_content_path": str(skill_md)}
        if s["name"] == "agent-customization"
        else s
        for s in sample_skills
    ]
    with patch("mcp_server.get_skills", return_value=patched):
        result = await mcp_server.invoke_skill("AGENT-CUSTOMIZATION")
    assert "agent-customization" in result


async def test_invoke_skill_not_found(sample_skills: list[dict]) -> None:
    with patch("mcp_server.get_skills", return_value=sample_skills):
        result = await mcp_server.invoke_skill("nonexistent-skill-xyz-12345")
    assert "nao encontrada" in result.lower() or "não encontrada" in result.lower()


async def test_invoke_skill_miss_points_to_model_search_not_substring(sample_skills: list[dict]) -> None:
    """Nome inexato nao vira 'voce quis dizer' por substring: aponta para find_skills."""
    with patch("mcp_server.get_skills", return_value=sample_skills):
        result = await mcp_server.invoke_skill("react")
    assert "find_skills" in result and "react-best-practices" not in result


async def test_invoke_skill_with_params(sample_skills: list[dict], tmp_path: Path) -> None:
    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text("# Docker\n\nContent.", encoding="utf-8")
    patched = [
        {**s, "full_content_path": str(skill_md)}
        if s["name"] == "docker-compose"
        else s
        for s in sample_skills
    ]
    with patch("mcp_server.get_skills", return_value=patched):
        result = await mcp_server.invoke_skill("docker-compose", "como fazer rollback?")
    assert "como fazer rollback?" in result


# ── refresh_skills ─────────────────────────────────────────────────────────

async def test_refresh_skills_returns_summary(sample_skills: list[dict]) -> None:
    with patch("mcp_server.get_skills", return_value=sample_skills):
        result = await mcp_server.refresh_skills()
    assert "Skills" in result or "skills" in result


async def test_refresh_skills_calls_force_reload(sample_skills: list[dict]) -> None:
    call_args: list = []

    def mock_get_skills(force_reload: bool = False) -> list[dict]:
        call_args.append(force_reload)
        return sample_skills

    with patch("mcp_server.get_skills", side_effect=mock_get_skills):
        await mcp_server.refresh_skills()

    # One call should be with force_reload=True
    assert True in call_args
