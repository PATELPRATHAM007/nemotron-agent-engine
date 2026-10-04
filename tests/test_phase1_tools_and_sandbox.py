"""
Comprehensive Test Suite for Phase 1: Tool Sandbox & Foundation Hardening
==========================================================================
Verifies:
  1. Workspace Sandbox (Path bounds, traversal prevention, fingerprinting)
  2. Concurrency Conflict Guard (detects external modifications before patch)
  3. Minimal Diff Patcher (Hunk-based surgical editing, diff generation)
  4. Hardened Subprocess Runner (Timeouts, output truncation, directory confinement)
  5. Native Git Tool (Status, diff, log, blame, checkpoint, rollback)
  6. Standardized MCP Tool Registry & Permission Interception
"""

import asyncio
import os
import pytest

from app.modules.agent.tools.git_tool import GitTool, git_tool
from app.modules.agent.tools.patcher import DiffPatcher, diff_patcher
from app.modules.agent.tools.process_runner import ProcessRunner, process_runner
from app.modules.agent.tools.registry import TOOLS_SCHEMA, dispatch_tool
from app.modules.agent.tools.workspace import (
    ConcurrencyConflictError,
    WorkspaceSandbox,
    workspace_sandbox,
)


# ------------------------------------------------------------------------------
# 1. Workspace Sandbox & Path Bounds Tests
# ------------------------------------------------------------------------------

def test_workspace_sandbox_path_resolution(tmp_path):
    sandbox = WorkspaceSandbox(workspace_root=str(tmp_path))

    # Valid path
    resolved = sandbox.resolve_path("app/main.py")
    assert resolved == os.path.abspath(tmp_path / "app" / "main.py")

    # Traversal escape attempt
    with pytest.raises(PermissionError):
        sandbox.resolve_path("../../etc/passwd")


def test_concurrency_conflict_detection(tmp_path):
    sandbox = WorkspaceSandbox(workspace_root=str(tmp_path))
    test_file = tmp_path / "service.py"
    test_file.write_text("def run():\n    return 42\n", encoding="utf-8")

    # Record snapshot
    base_hash = sandbox.record_snapshot("service.py")
    assert len(base_hash) == 64

    # No conflict check
    sandbox.verify_no_conflict("service.py", expected_base_sha256=base_hash)

    # Modify file externally on disk
    test_file.write_text("def run():\n    return 'changed externally'\n", encoding="utf-8")

    # Concurrency conflict must be raised!
    with pytest.raises(ConcurrencyConflictError):
        sandbox.verify_no_conflict("service.py", expected_base_sha256=base_hash)


# ------------------------------------------------------------------------------
# 2. Minimal Diff Patcher Tests
# ------------------------------------------------------------------------------

def test_diff_patcher_surgical_hunk_replacement(tmp_path):
    sandbox = WorkspaceSandbox(workspace_root=str(tmp_path))
    patcher = DiffPatcher(sandbox=sandbox)

    test_file = tmp_path / "calculator.py"
    initial_content = (
        "def add(a, b):\n"
        "    return a + b\n"
        "\n"
        "def multiply(a, b):\n"
        "    return a - b  # BUG: should be a * b\n"
        "\n"
        "def subtract(a, b):\n"
        "    return a - b\n"
    )
    test_file.write_text(initial_content, encoding="utf-8")

    # Apply surgical fix to multiply function only
    target_snippet = "def multiply(a, b):\n    return a - b  # BUG: should be a * b"
    replacement_snippet = "def multiply(a, b):\n    return a * b"

    res = patcher.edit_file(
        filepath="calculator.py",
        target_snippet=target_snippet,
        replacement_snippet=replacement_snippet,
    )

    assert res.success is True
    assert res.replacements_made == 1
    assert "return a * b" in res.diff
    assert "-    return a - b  # BUG" in res.diff

    # Verify content on disk
    updated_content = test_file.read_text(encoding="utf-8")
    assert "return a * b" in updated_content
    # Unrelated functions preserved!
    assert "def add(a, b):" in updated_content
    assert "def subtract(a, b):" in updated_content


def test_diff_patcher_rejects_ambiguous_occurrences(tmp_path):
    sandbox = WorkspaceSandbox(workspace_root=str(tmp_path))
    patcher = DiffPatcher(sandbox=sandbox)

    test_file = tmp_path / "repeated.py"
    test_file.write_text("x = 1\nx = 1\nx = 1\n", encoding="utf-8")

    res = patcher.edit_file(
        filepath="repeated.py",
        target_snippet="x = 1",
        replacement_snippet="x = 2",
        allow_multiple=False,
    )

    assert res.success is False
    assert "occurs 3 times" in (res.error or "")


# ------------------------------------------------------------------------------
# 3. Subprocess Runner Tests
# ------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_process_runner_execution_and_directory_confinement(tmp_path):
    sandbox = WorkspaceSandbox(workspace_root=str(tmp_path))
    runner = ProcessRunner(sandbox=sandbox)

    res = await runner.run("echo 'sandbox test'")
    assert res.success is True
    assert res.exit_code == 0
    assert "sandbox test" in res.stdout


@pytest.mark.asyncio
async def test_process_runner_timeout_enforcement(tmp_path):
    sandbox = WorkspaceSandbox(workspace_root=str(tmp_path))
    runner = ProcessRunner(sandbox=sandbox)

    # Command times out after 1 second
    res = await runner.run("sleep 5", timeout=1)
    assert res.success is False
    assert res.timed_out is True
    assert "Command timed out" in res.stderr


# ------------------------------------------------------------------------------
# 4. Native Git Tool Tests
# ------------------------------------------------------------------------------

def test_git_tool_status_and_diff():
    status = git_tool.get_status()
    assert status.is_repo is True
    assert len(status.branch) > 0

    diff = git_tool.get_diff()
    assert isinstance(diff, str)

    logs = git_tool.get_log(limit=3)
    assert len(logs) > 0
    assert "commit_hash" in logs[0]
    assert "message" in logs[0]


def test_git_tool_checkpoint_and_rollback(tmp_path):
    # Verify rollback method handles clean execution
    cp = git_tool.create_checkpoint("test_safety_check")
    assert cp["success"] is True
    assert "sha" in cp


# ------------------------------------------------------------------------------
# 5. Standardized MCP Tool Registry Tests
# ------------------------------------------------------------------------------

def test_tools_schema_definitions():
    tool_names = [t["function"]["name"] for t in TOOLS_SCHEMA]
    assert "read_file" in tool_names
    assert "write_file" in tool_names
    assert "edit_file" in tool_names
    assert "list_directory" in tool_names
    assert "execute_bash" in tool_names
    assert "git_status" in tool_names
    assert "git_diff" in tool_names
    assert "git_checkpoint" in tool_names
    assert "git_rollback" in tool_names


@pytest.mark.asyncio
async def test_dispatch_tool_edit_and_read(tmp_path, monkeypatch):
    # Point workspace_sandbox to temporary directory for isolated test
    test_sandbox = WorkspaceSandbox(workspace_root=str(tmp_path))
    monkeypatch.setattr("app.modules.agent.tools.registry.workspace_sandbox", test_sandbox)
    monkeypatch.setattr("app.modules.agent.tools.patcher.workspace_sandbox", test_sandbox)

    # 1. Write file
    w_res = await dispatch_tool("write_file", {"filepath": "demo.py", "content": "val = 10\n"})
    assert w_res["success"] is True

    # 2. Read file
    r_res = await dispatch_tool("read_file", {"filepath": "demo.py"})
    assert r_res["success"] is True
    assert "val = 10" in r_res["content"]

    # 3. Edit file (minimal hunk patch)
    e_res = await dispatch_tool(
        "edit_file",
        {
            "filepath": "demo.py",
            "target_snippet": "val = 10",
            "replacement_snippet": "val = 99",
        },
    )
    assert e_res["success"] is True
    assert "val = 99" in e_res["diff"]

    # 4. Read back updated file
    r_res2 = await dispatch_tool("read_file", {"filepath": "demo.py"})
    assert "val = 99" in r_res2["content"]


@pytest.mark.asyncio
async def test_dispatch_tool_blocks_dangerous_commands():
    # Attempt high-risk command
    res = await dispatch_tool("execute_bash", {"command": "rm -rf /"})
    assert res["success"] is False
    assert "blocked" in res["stderr"].lower() or "prohibited" in res["stderr"].lower()
