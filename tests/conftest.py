"""Shared fixtures and configuration for all test modules."""
import sys
from pathlib import Path

import pytest

# Make mcp_server importable from the tests directory
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture()
def sample_skills() -> list[dict]:
    """Minimal fake skill dataset covering multiple categories for unit tests."""
    return [
        {
            "name": "agent-customization",
            "description": "Configure VS Code agents and MCP prompts",
            "categories": ["ai"],
            "path": "/skills/agent-customization",
            "skill_md_preview": "# Agent Customization\n\nMCP server instructions.",
            "full_content_path": "/skills/agent-customization/SKILL.md",
        },
        {
            "name": "docker-compose",
            "description": "Docker Compose container orchestration guide",
            "categories": ["devops"],
            "path": "/skills/docker-compose",
            "skill_md_preview": "# Docker Compose\n\nOrchestration guide.",
            "full_content_path": "/skills/docker-compose/SKILL.md",
        },
        {
            "name": "graphql-api",
            "description": "GraphQL API design and implementation patterns",
            "categories": ["backend"],
            "path": "/skills/graphql-api",
            "skill_md_preview": "# GraphQL API\n\nAPI design patterns.",
            "full_content_path": "/skills/graphql-api/SKILL.md",
        },
        {
            "name": "pytest-best-practices",
            "description": "Python testing with pytest framework",
            "categories": ["testing", "language"],
            "path": "/skills/pytest-best-practices",
            "skill_md_preview": "# Pytest\n\nTest automation guide.",
            "full_content_path": "/skills/pytest-best-practices/SKILL.md",
        },
        {
            "name": "react-best-practices",
            "description": "React patterns and hooks guide",
            "categories": ["frontend"],
            "path": "/skills/react-best-practices",
            "skill_md_preview": "# React Best Practices\n\nGuide for React development.",
            "full_content_path": "/skills/react-best-practices/SKILL.md",
        },
        {
            "name": "react-native-expo",
            "description": "React Native app development with Expo",
            "categories": ["mobile"],
            "path": "/skills/react-native-expo",
            "skill_md_preview": "# React Native\n\nMobile development guide.",
            "full_content_path": "/skills/react-native-expo/SKILL.md",
        },
        {
            "name": "security-owasp-testing",
            "description": "OWASP security testing methodology",
            "categories": ["security"],
            "path": "/skills/security-owasp-testing",
            "skill_md_preview": "# OWASP Testing\n\nSecurity audit guide.",
            "full_content_path": "/skills/security-owasp-testing/SKILL.md",
        },
        {
            "name": "data-pipeline",
            "description": "Data engineering pipeline patterns",
            "categories": ["data"],
            "path": "/skills/data-pipeline",
            "skill_md_preview": "# Data Pipeline\n\nETL guide.",
            "full_content_path": "/skills/data-pipeline/SKILL.md",
        },
        {
            "name": "python-type-hints",
            "description": "Python strict typing and MyPy configuration",
            "categories": ["language"],
            "path": "/skills/python-type-hints",
            "skill_md_preview": "# Python Typing\n\nType safety guide.",
            "full_content_path": "/skills/python-type-hints/SKILL.md",
        },
    ]


@pytest.fixture(autouse=True)
def reset_skill_cache():
    """Reset global skill cache state before and after each test."""
    import mcp_server

    mcp_server._skills = []
    mcp_server._skills_loaded_at = 0.0
    mcp_server._bm25_index = None
    mcp_server._bm25_skills = []
    mcp_server._bm25_built_at = 0.0
    yield
    mcp_server._skills = []
    mcp_server._skills_loaded_at = 0.0
    mcp_server._bm25_index = None
    mcp_server._bm25_skills = []
    mcp_server._bm25_built_at = 0.0
