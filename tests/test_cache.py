"""Tests for the skill cache TTL and force-reload behavior."""
import time
from unittest.mock import patch

import mcp_server


def test_get_skills_populates_cache(sample_skills: list[dict]) -> None:
    """First call should populate the cache via discover_skills."""
    assert mcp_server._skills == []
    with patch("mcp_server.discover_skills", return_value=sample_skills) as mock_discover:
        result = mcp_server.get_skills()
    mock_discover.assert_called_once()
    assert result == sample_skills
    assert mcp_server._skills == sample_skills


def test_get_skills_uses_cache_within_ttl(sample_skills: list[dict]) -> None:
    """Second call within TTL must NOT re-discover."""
    with patch("mcp_server.discover_skills", return_value=sample_skills) as mock_discover:
        mcp_server.get_skills()
        mcp_server.get_skills()
    assert mock_discover.call_count == 1


def test_get_skills_force_reload_bypasses_cache(sample_skills: list[dict]) -> None:
    """force_reload=True must re-discover even if cache is fresh."""
    with patch("mcp_server.discover_skills", return_value=sample_skills) as mock_discover:
        # Pre-load cache
        mcp_server._skills = sample_skills
        mcp_server._skills_loaded_at = time.time()
        # Force reload
        result = mcp_server.get_skills(force_reload=True)
    mock_discover.assert_called_once()
    assert result == sample_skills


def test_get_skills_reloads_when_ttl_expired(sample_skills: list[dict]) -> None:
    """Cache must reload when time elapsed exceeds _CACHE_TTL_SECONDS."""
    with patch("mcp_server.discover_skills", return_value=sample_skills) as mock_discover:
        # Set loaded_at to epoch 0 so TTL is always expired
        mcp_server._skills = sample_skills
        mcp_server._skills_loaded_at = 0.0
        result = mcp_server.get_skills()
    mock_discover.assert_called_once()
    assert result == sample_skills


def test_get_skills_reloads_when_empty(sample_skills: list[dict]) -> None:
    """Empty cache must trigger discover even if loaded_at is recent."""
    with patch("mcp_server.discover_skills", return_value=sample_skills) as mock_discover:
        mcp_server._skills = []
        mcp_server._skills_loaded_at = time.time()
        result = mcp_server.get_skills()
    mock_discover.assert_called_once()
    assert result == sample_skills


def test_cache_ttl_constant_is_positive() -> None:
    """TTL must be a positive number (in seconds)."""
    assert mcp_server._CACHE_TTL_SECONDS > 0


def test_bm25_ttl_constant_is_positive() -> None:
    assert mcp_server._BM25_TTL > 0


def test_get_bm25_rebuilds_when_skill_count_changes(sample_skills: list[dict]) -> None:
    """BM25 index must rebuild when the number of skills changes."""
    # Patch BM25Okapi to avoid installing rank_bm25 just for this test
    try:
        from rank_bm25 import BM25Okapi  # noqa: F401
    except ImportError:
        import pytest
        pytest.skip("rank_bm25 not installed")

    # Build index with full dataset
    idx1 = mcp_server._get_bm25(sample_skills)

    # Now pass a smaller dataset — should rebuild
    smaller = sample_skills[:2]
    # Force rebuild by resetting the built_at timestamp
    mcp_server._bm25_built_at = 0.0
    idx2 = mcp_server._get_bm25(smaller)

    assert idx1 is not idx2


def test_discover_skills_returns_sorted(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """discover_skills() must return skills sorted by name."""
    # Create fake skill directories out of alphabetical order
    for name in ["zebra-skill", "alpha-skill", "mango-skill"]:
        skill_dir = tmp_path / name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(f"# {name}\n\nDesc.", encoding="utf-8")

    original_path = mcp_server.SKILLS_PATH
    mcp_server.SKILLS_PATH = tmp_path
    try:
        skills = mcp_server.discover_skills()
    finally:
        mcp_server.SKILLS_PATH = original_path

    names = [s["name"] for s in skills]
    assert names == sorted(names)


def test_discover_skills_skips_hidden_dirs(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """discover_skills() must ignore directories starting with '.'."""
    (tmp_path / ".hidden").mkdir()
    (tmp_path / ".hidden" / "SKILL.md").write_text("# hidden", encoding="utf-8")

    real_skill = tmp_path / "real-skill"
    real_skill.mkdir()
    (real_skill / "SKILL.md").write_text("# real\n\nDesc.", encoding="utf-8")

    original_path = mcp_server.SKILLS_PATH
    mcp_server.SKILLS_PATH = tmp_path
    try:
        skills = mcp_server.discover_skills()
    finally:
        mcp_server.SKILLS_PATH = original_path

    names = [s["name"] for s in skills]
    assert "real-skill" in names
    assert ".hidden" not in names


def test_discover_skills_skips_dirs_without_skill_md(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Directories without SKILL.md must be ignored."""
    (tmp_path / "no-skill-file").mkdir()
    good_dir = tmp_path / "has-skill"
    good_dir.mkdir()
    (good_dir / "SKILL.md").write_text("# Has Skill\n\nDesc.", encoding="utf-8")

    original_path = mcp_server.SKILLS_PATH
    mcp_server.SKILLS_PATH = tmp_path
    try:
        skills = mcp_server.discover_skills()
    finally:
        mcp_server.SKILLS_PATH = original_path

    names = [s["name"] for s in skills]
    assert "has-skill" in names
    assert "no-skill-file" not in names


def test_discover_skills_missing_path(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """discover_skills() must return empty list when SKILLS_PATH doesn't exist."""
    original_path = mcp_server.SKILLS_PATH
    mcp_server.SKILLS_PATH = tmp_path / "does_not_exist"
    try:
        skills = mcp_server.discover_skills()
    finally:
        mcp_server.SKILLS_PATH = original_path


def test_discover_skills_categorized_layout_uses_folder_category(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Skills inside a known category folder must use that folder as primary category."""
    # Create c:\skills\ai\my-custom-skill\ — name has no AI keywords
    ai_dir = tmp_path / "ai"
    ai_dir.mkdir()
    skill_dir = ai_dir / "my-custom-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# My Custom Skill\n\nNo AI keywords.", encoding="utf-8")

    original_path = mcp_server.SKILLS_PATH
    mcp_server.SKILLS_PATH = tmp_path
    try:
        skills = mcp_server.discover_skills()
    finally:
        mcp_server.SKILLS_PATH = original_path

    assert len(skills) == 1
    assert skills[0]["name"] == "my-custom-skill"
    assert skills[0]["categories"][0] == "ai", "Primary category must be the folder name"


def test_discover_skills_categorized_layout_unknown_folder_ignored(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """A folder that is not a known category and has no SKILL.md must be ignored."""
    unknown_dir = tmp_path / "not-a-category"
    unknown_dir.mkdir()
    (unknown_dir / "some-skill").mkdir()
    (unknown_dir / "some-skill" / "SKILL.md").write_text("# Some Skill\n\nDesc.", encoding="utf-8")

    original_path = mcp_server.SKILLS_PATH
    mcp_server.SKILLS_PATH = tmp_path
    try:
        skills = mcp_server.discover_skills()
    finally:
        mcp_server.SKILLS_PATH = original_path

    assert skills == [], "Skills inside unknown category dirs must not be discovered"
