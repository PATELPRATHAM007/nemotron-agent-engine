"""
Master Command System Test Battery
==================================
Tests first-class agent commands: parser, registry, metadata, permission integration,
lifecycle event emission, and execution across all 16 commands.
"""

import os
import tempfile
import pytest
from pathlib import Path

from app.modules.agent.commands.models import (
    CommandDefinition,
    CommandRisk,
    ExecutionMode,
    ParsedCommand,
)
from app.modules.agent.commands.parser import CommandParser
from app.modules.agent.commands.registry import CommandRegistry, command_registry
from app.modules.agent.tools.process_runner import ExecutionResult, process_runner



class TestCommandParser:
    """Tests for CommandParser syntax, quotes, flags, unicode, and shortcuts."""

    def test_parse_simple_command(self):
        cmd = CommandParser.parse("/status")
        assert cmd.is_command is True
        assert cmd.command == "/status"
        assert cmd.args == []
        assert cmd.flags == {}

    def test_parse_command_with_positional_args(self):
        cmd = CommandParser.parse("/test backend")
        assert cmd.is_command is True
        assert cmd.command == "/test"
        assert cmd.args == ["backend"]
        assert cmd.query_string == "backend"

    def test_parse_command_with_quoted_strings(self):
        cmd = CommandParser.parse('/plan "implement OAuth authentication with Google"')
        assert cmd.is_command is True
        assert cmd.command == "/plan"
        assert cmd.args == ["implement OAuth authentication with Google"]
        assert cmd.query_string == '"implement OAuth authentication with Google"'

    def test_parse_command_with_flags(self):
        cmd = CommandParser.parse("/init --full --refresh -v")
        assert cmd.is_command is True
        assert cmd.command == "/init"
        assert cmd.flags.get("full") is True
        assert cmd.flags.get("refresh") is True
        assert cmd.flags.get("v") is True

    def test_parse_command_with_key_value_flags(self):
        cmd = CommandParser.parse("/test --target=backend --coverage")
        assert cmd.is_command is True
        assert cmd.command == "/test"
        assert cmd.flags.get("target") == "backend"
        assert cmd.flags.get("coverage") is True

    def test_parse_command_with_unicode_and_emojis(self):
        cmd = CommandParser.parse('/search 🚀 "precio > 100" 日本語')
        assert cmd.is_command is True
        assert cmd.command == "/search"
        assert "🚀" in cmd.args
        assert "precio > 100" in cmd.args
        assert "日本語" in cmd.args

    def test_parse_terminal_shortcut(self):
        cmd = CommandParser.parse("!git status -s")
        assert cmd.is_command is True
        assert cmd.command == "!"
        assert cmd.query_string == "git status -s"

    def test_parse_natural_language_not_command(self):
        nl1 = CommandParser.parse("What is the architecture of the app?")
        assert nl1.is_command is False
        assert nl1.command == ""

        nl2 = CommandParser.parse("// This is a comment")
        assert nl2.is_command is False

        nl3 = CommandParser.parse("")
        assert nl3.is_command is False


class TestCommandRegistry:
    """Tests for centralized CommandRegistry indexing, search, and metadata."""

    def test_all_16_core_commands_registered(self):
        expected_commands = {
            "/init", "/plan", "/review", "/test", "/debug", "/fix",
            "/explain", "/search", "/inspect", "/status", "/diff",
            "/commit", "/undo", "/reset", "/clear", "/help",
        }
        registered = {c.command for c in command_registry.list_commands()}
        assert expected_commands.issubset(registered), f"Missing commands: {expected_commands - registered}"

    def test_command_metadata_invariants(self):
        for cmd in command_registry.list_commands():
            assert cmd.command.startswith("/")
            assert len(cmd.description) > 5
            assert cmd.syntax.startswith(cmd.command)
            assert cmd.risk_level in [CommandRisk.LOW, CommandRisk.MEDIUM, CommandRisk.HIGH, CommandRisk.SPECIAL]
            assert 0 <= cmd.permission_level <= 5
            assert len(cmd.examples) >= 1

    def test_high_risk_commands_require_approval(self):
        commit_cmd = command_registry.get("/commit")
        assert commit_cmd is not None
        assert commit_cmd.risk_level == CommandRisk.HIGH
        assert commit_cmd.supports_approval is True

        reset_cmd = command_registry.get("/reset")
        assert reset_cmd is not None
        assert reset_cmd.risk_level == CommandRisk.HIGH
        assert reset_cmd.supports_approval is True

        undo_cmd = command_registry.get("/undo")
        assert undo_cmd is not None
        assert undo_cmd.risk_level == CommandRisk.HIGH

    def test_search_and_autocomplete(self):
        plan_hits = command_registry.search("pl")
        assert any(c.command == "/plan" for c in plan_hits)

        test_hits = command_registry.search("te")
        assert any(c.command == "/test" for c in test_hits)

        init_hits = command_registry.search("init")
        assert any(c.command == "/init" for c in init_hits)


@pytest.mark.asyncio
class TestCommandHandlersExecution:
    """Integration execution tests for command handlers."""

    async def test_help_handler_all_and_specific(self):
        # Full help table
        p_all = CommandParser.parse("/help")
        events_all = []
        async for ev in command_registry.dispatch(p_all, workspace_root="."):
            events_all.append(ev)

        tokens = [ev["content"] for ev in events_all if ev.get("type") == "token"]
        assert any("Nemotron Agent Engine: Available Commands" in t for t in tokens)

        # Specific command help
        p_plan = CommandParser.parse("/help plan")
        events_plan = []
        async for ev in command_registry.dispatch(p_plan, workspace_root="."):
            events_plan.append(ev)

        tokens_plan = [ev["content"] for ev in events_plan if ev.get("type") == "token"]
        assert any("Command Help: `/plan`" in t for t in tokens_plan)

    async def test_init_handler_executes_safely(self):
        p_init = CommandParser.parse("/init --refresh")
        events = []
        async for ev in command_registry.dispatch(p_init, workspace_root="."):
            events.append(ev)

        event_types = [ev.get("type") for ev in events]
        assert "command.started" in event_types
        assert "command.completed" in event_types

        tokens = "".join([ev.get("content", "") for ev in events if ev.get("type") == "token"])
        assert "Project" in tokens
        assert "Languages" in tokens

    async def test_plan_handler_produces_plan_without_file_modification(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            initial_files = set(os.listdir(tmpdir))

            p_plan = CommandParser.parse('/plan "Add multi-tenant authentication"')
            events = []
            async for ev in command_registry.dispatch(p_plan, workspace_root=tmpdir, mission_id="test_mission"):
                events.append(ev)

            # Assert NO files were created or modified
            assert set(os.listdir(tmpdir)) == initial_files

            # Assert structured plan event was emitted
            plan_ev = next((ev for ev in events if ev.get("type") == "plan_created"), None)
            assert plan_ev is not None
            assert len(plan_ev["steps"]) > 0
            assert "Add multi-tenant authentication" in plan_ev["summary"]

    async def test_review_handler_clean_working_tree(self):
        p_rev = CommandParser.parse("/review")
        events = []
        async for ev in command_registry.dispatch(p_rev, workspace_root="."):
            events.append(ev)

        event_types = [ev.get("type") for ev in events]
        assert "command.started" in event_types
        assert "command.completed" in event_types

    async def test_test_handler_resolves_and_runs(self, monkeypatch):
        async def mock_run(cmd, cwd=None, timeout=30, env_vars=None):
            return ExecutionResult(
                success=True,
                exit_code=0,
                stdout="202 passed in 1.2s",
                stderr="",
                duration_ms=1200,
                command=cmd,
            )

        monkeypatch.setattr(process_runner, "run", mock_run)

        p_test = CommandParser.parse("/test")
        events = []
        async for ev in command_registry.dispatch(p_test, workspace_root="."):
            events.append(ev)

        tool_started = next((ev for ev in events if ev.get("type") == "command.tool_started"), None)
        assert tool_started is not None
        assert tool_started.get("tool") == "process_runner"

    async def test_debug_handler_diagnoses_symptom(self):
        p_debug = CommandParser.parse('/debug "ValueError: invalid literal for int() with base 10"')
        events = []
        async for ev in command_registry.dispatch(p_debug, workspace_root="."):
            events.append(ev)

        tokens = "".join([ev.get("content", "") for ev in events if ev.get("type") == "token"])
        assert "Root Cause Diagnosis" in tokens
        assert "ValueError" in tokens

    async def test_explain_handler_with_file_target(self):
        p_exp = CommandParser.parse("/explain app/core/permissions.py")
        events = []
        async for ev in command_registry.dispatch(p_exp, workspace_root="."):
            events.append(ev)

        tokens = "".join([ev.get("content", "") for ev in events if ev.get("type") == "token"])
        assert "Structural Analysis" in tokens or "Architectural Overview" in tokens

    async def test_search_handler_executes_ripgrep(self):
        p_search = CommandParser.parse('/search "CommandRegistry"')
        events = []
        async for ev in command_registry.dispatch(p_search, workspace_root="."):
            events.append(ev)

        tokens = "".join([ev.get("content", "") for ev in events if ev.get("type") == "token"])
        assert "Found" in tokens or "matches" in tokens

    async def test_inspect_handler_with_directory(self):
        p_insp = CommandParser.parse("/inspect app/core")
        events = []
        async for ev in command_registry.dispatch(p_insp, workspace_root="."):
            events.append(ev)

        tokens = "".join([ev.get("content", "") for ev in events if ev.get("type") == "token"])
        assert "Directory Inspection" in tokens

    async def test_status_handler_masks_secrets(self):
        p_stat = CommandParser.parse("/status")
        events = []
        async for ev in command_registry.dispatch(p_stat, workspace_root="."):
            events.append(ev)

        tokens = "".join([ev.get("content", "") for ev in events if ev.get("type") == "token"])
        assert "Git Branch" in tokens
        assert "Secrets masked" in tokens

    async def test_diff_handler_outputs_structured_diff(self):
        p_diff = CommandParser.parse("/diff")
        events = []
        async for ev in command_registry.dispatch(p_diff, workspace_root="."):
            events.append(ev)

        event_types = [ev.get("type") for ev in events]
        assert "command.started" in event_types
        assert "command.completed" in event_types

    async def test_reset_command_guards_against_unconfirmed_execution(self):
        p_reset_unconfirmed = CommandParser.parse("/reset")
        events = []
        async for ev in command_registry.dispatch(p_reset_unconfirmed, workspace_root="."):
            events.append(ev)

        # Must trigger approval / confirmation requirement
        approval_req = next((ev for ev in events if ev.get("type") == "command.approval_required"), None)
        assert approval_req is not None
        assert approval_req["payload"]["risk_level"] == "HIGH"

        tokens = "".join([ev.get("content", "") for ev in events if ev.get("type") == "token"])
        assert "HIGH RISK COMMAND: /reset" in tokens

    async def test_unknown_command_emits_structured_failure(self):
        p_unknown = CommandParser.parse("/nonexistent_cmd_xyz")
        events = []
        async for ev in command_registry.dispatch(p_unknown, workspace_root="."):
            events.append(ev)

        fail_ev = next((ev for ev in events if ev.get("type") == "command.failed"), None)
        assert fail_ev is not None
        assert "Unknown command" in fail_ev["payload"]["reason"]

    async def test_undo_command_execution(self, monkeypatch):
        from unittest.mock import AsyncMock
        from app.modules.agent.tools.git_tool import git_tool

        monkeypatch.setattr(git_tool, "status", AsyncMock(return_value={
            "success": True, "branch": "main", "clean": False, "modified": ["dummy.py"], "staged": [], "untracked": []
        }))
        monkeypatch.setattr(git_tool, "rollback", lambda files=None: {"success": True, "checkpoint_name": "undo"})

        p_undo = CommandParser.parse("/undo")
        events = []
        async for ev in command_registry.dispatch(p_undo, workspace_root="."):
            events.append(ev)

        event_types = [ev.get("type") for ev in events]
        assert "command.started" in event_types
        assert "command.completed" in event_types
        tokens = "".join([ev.get("content", "") for ev in events if ev.get("type") == "token"])
        assert "Reverted uncommitted changes" in tokens

    async def test_reset_confirmed_execution_with_mocked_runner(self, monkeypatch):
        from unittest.mock import AsyncMock
        from app.modules.agent.tools.process_runner import ExecutionResult, ProcessRunner

        mock_run = AsyncMock(return_value=ExecutionResult(
            success=True,
            exit_code=0,
            stdout="HEAD is now at 1234567",
            stderr="",
            duration_ms=10,
            command="git reset --hard HEAD",
        ))
        monkeypatch.setattr(ProcessRunner, "run", mock_run)

        p_reset_confirmed = CommandParser.parse("/reset --confirm")
        events = []
        async for ev in command_registry.dispatch(p_reset_confirmed, workspace_root="."):
            events.append(ev)

        event_types = [ev.get("type") for ev in events]
        assert "command.completed" in event_types
        tokens = "".join([ev.get("content", "") for ev in events if ev.get("type") == "token"])
        assert "hard reset to clean HEAD state" in tokens

    async def test_process_runner_working_directory_and_run_command(self):
        from app.modules.agent.tools.process_runner import ProcessRunner
        runner = ProcessRunner(working_directory=".")
        res = await runner.run_command("echo 'test runner compatibility'")
        assert res.success is True
        assert "test runner compatibility" in res.stdout

    async def test_init_handler_validation_report_formatting(self):
        from app.modules.agent.commands.handlers.init_handler import InitCommandHandler

        identity = {"name": "test-repo", "root": "/test", "git_branch": "main", "is_git_clean": True}
        tech_stack = {"languages": ["Python"], "frameworks": ["FastAPI"], "package_managers": ["pip"]}
        entry_points = {"main": "main.py"}

        # Case 1: 0 broken imports / 0 invalid exports
        audit_clean = {
            "source_files_count": 10,
            "test_files_count": 2,
            "broken_imports_count": 0,
            "export_errors_count": 0,
            "circular_dependencies_count": 0,
        }
        report_clean = InitCommandHandler._render_validation_report(
            identity, tech_stack, audit_clean, entry_points, 12, "full"
        )
        assert "✓ Healthy (0 broken imports)" in report_clean
        assert "✓ Healthy (0 invalid exports)" in report_clean

        # Case 2: >0 broken imports / >0 invalid exports
        audit_issues = {
            "source_files_count": 10,
            "test_files_count": 2,
            "broken_imports_count": 3,
            "export_errors_count": 2,
            "circular_dependencies_count": 1,
        }
        report_issues = InitCommandHandler._render_validation_report(
            identity, tech_stack, audit_issues, entry_points, 12, "full"
        )
        assert "⚠️ 3 broken imports" in report_issues
        assert "⚠️ 2 invalid exports" in report_issues
