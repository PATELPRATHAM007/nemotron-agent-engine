"""
Comprehensive Test Suite for Phase 2: Multi-Mode Repository Intelligence & RepoMap
==================================================================================
Verifies:
  1. Fast Ripgrep & Regex Search (exact matching, file types, line numbers, bounds)
  2. Compact Repository Map Generator (token-budgeted AST outline < 2,000 tokens)
  3. Git History & Blame Retriever (file commit logs, line-level blame metadata)
  4. Tool Registry integration with ripgrep_search, get_repo_map, and get_git_history
"""

import pytest

from app.modules.agent.tools.registry import dispatch_tool
from app.modules.intelligence.context.budget_manager import estimate_tokens
from app.modules.intelligence.indexing.git_history import git_history_retriever
from app.modules.intelligence.indexing.repo_map import repo_map_generator
from app.modules.intelligence.indexing.ripgrep import ripgrep_search

# ------------------------------------------------------------------------------
# 1. Ripgrep & Regex Search Engine Tests
# ------------------------------------------------------------------------------

def test_ripgrep_search_exact_match():
    # Search for known unique class name in repo
    res = ripgrep_search.search(query="VerificationPipeline", file_types=["py"])
    assert res.success is True
    assert res.total_matches > 0

    first_match = res.matches[0]
    assert "gates.py" in first_match.filepath or "verification" in first_match.filepath
    assert first_match.line_number > 0
    assert "VerificationPipeline" in first_match.line_content


def test_ripgrep_search_file_type_filtering():
    # Search for 'import' in Python files only
    res_py = ripgrep_search.search(query="import", file_types=["py"], max_results=10)
    assert res_py.success is True
    for m in res_py.matches:
        assert m.filepath.endswith(".py")


def test_ripgrep_search_truncation_bound():
    # A very common word like 'def' with max_results=5
    res = ripgrep_search.search(query="def ", max_results=5)
    assert res.success is True
    assert len(res.matches) <= 5
    assert res.truncated is True


def test_ripgrep_empty_query_rejected():
    res = ripgrep_search.search(query="")
    assert res.success is False
    assert "cannot be empty" in (res.error or "")


# ------------------------------------------------------------------------------
# 2. Compact Repository Map Generator Tests
# ------------------------------------------------------------------------------

def test_repo_map_generator_budget_and_content():
    # Generate compact map with 1500 token ceiling
    map_text = repo_map_generator.generate_map(max_tokens=1500, force_refresh=True)
    assert len(map_text) > 0
    assert "Repository Map" in map_text

    token_cost = estimate_tokens(map_text)
    assert token_cost <= 1600  # Within slight tolerance

    # Ensure major architectural entry points are present
    assert "app/main.py" in map_text or "apis.py" in map_text
    assert "def " in map_text or "class " in map_text


# ------------------------------------------------------------------------------
# 3. Git History & Blame Retriever Tests
# ------------------------------------------------------------------------------

def test_git_history_retriever():
    history = git_history_retriever.get_recent_file_history("app/main.py", limit=3)
    assert len(history) > 0
    first = history[0]
    assert len(first.commit_hash) >= 7
    assert len(first.author) > 0
    assert len(first.message) > 0


def test_git_blame_retriever():
    blame = git_history_retriever.get_line_blame("app/main.py", line_start=1, line_end=5)
    assert len(blame) > 0
    assert "|" in blame  # Formatted author | code line


# ------------------------------------------------------------------------------
# 4. Tool Registry Dispatch for Phase 2 Tools
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dispatch_ripgrep_search_tool():
    res = await dispatch_tool("ripgrep_search", {"query": "VerificationPipeline", "file_types": ["py"]})
    assert res["success"] is True
    assert res["total_matches"] > 0
    assert any("gates.py" in m["filepath"] for m in res["matches"])


@pytest.mark.asyncio
async def test_dispatch_repo_map_tool():
    res = await dispatch_tool("get_repo_map", {"max_tokens": 1000})
    assert res["success"] is True
    assert "repo_map" in res
    assert "estimated_tokens" in res
    assert res["estimated_tokens"] <= 1200


@pytest.mark.asyncio
async def test_dispatch_git_history_tool():
    res = await dispatch_tool("get_git_history", {"filepath": "app/main.py", "limit": 2})
    assert res["success"] is True
    assert len(res["commits"]) > 0
    assert "hash" in res["commits"][0]
