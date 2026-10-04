"""
Centralized Command Registry
============================
Registers, indexes, and dispatches first-class agent commands.
Enforces permissions, structured event schemas, and lifecycle tracking.
"""

from collections.abc import AsyncGenerator, Callable
from typing import Any

from app.core.logging_config import get_logger
from app.modules.agent.commands.handlers import (
    DebugCommandHandler,
    DiffCommandHandler,
    ExplainCommandHandler,
    FixCommandHandler,
    GitCommandHandlers,
    InitCommandHandler,
    InspectCommandHandler,
    PlanCommandHandler,
    ReviewCommandHandler,
    SearchCommandHandler,
    StatusCommandHandler,
    TestCommandHandler,
    UtilityCommandHandlers,
)
from app.modules.agent.commands.models import (
    CommandDefinition,
    CommandRisk,
    ExecutionMode,
    ParsedCommand,
)

logger = get_logger(__name__)


class CommandRegistry:
    """Registry maintaining metadata and dispatchers for all agent commands."""

    def __init__(self):
        self._commands: dict[str, CommandDefinition] = {}
        self._handlers: dict[str, Callable[..., AsyncGenerator[dict[str, Any], None]]] = {}
        self._register_default_commands()

    def register(
        self,
        definition: CommandDefinition,
        handler: Callable[..., AsyncGenerator[dict[str, Any], None]],
    ) -> None:
        """Register a command definition and its asynchronous event generator handler."""
        canonical = definition.command.lower()
        self._commands[canonical] = definition
        self._handlers[canonical] = handler

    def get(self, command_name: str) -> CommandDefinition | None:
        """Retrieve command definition by name (with or without leading slash)."""
        name = command_name.lower()
        if not name.startswith("/"):
            name = "/" + name
        return self._commands.get(name)

    def list_commands(self) -> list[CommandDefinition]:
        """Return all registered command definitions in deterministic order."""
        return list(self._commands.values())

    def search(self, query: str) -> list[CommandDefinition]:
        """Search commands by prefix or substring for client autocomplete."""
        q = query.strip().lower()
        if q.startswith("/"):
            q = q[1:]

        matches = []
        for cmd_name, definition in self._commands.items():
            clean_name = cmd_name[1:]
            if clean_name.startswith(q) or q in clean_name or q in definition.description.lower():
                matches.append(definition)
        return matches

    async def dispatch(
        self,
        parsed: ParsedCommand,
        workspace_root: str,
        mission_id: str = "",
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Execute a parsed command through its registered handler."""
        canonical = parsed.command.lower()
        handler = self._handlers.get(canonical)

        if not handler:
            yield {
                "type": "command.failed",
                "command": parsed.command,
                "mission_id": mission_id,
                "payload": {"reason": f"Unknown command: {parsed.command}"},
            }
            yield {
                "type": "token",
                "content": f"❌ **Unknown command:** `{parsed.command}`\n\nType `/help` to see all available commands.\n",
            }
            return

        try:
            async for event in handler(parsed, workspace_root, mission_id):
                yield event
        except Exception as e:
            logger.exception(f"Error executing command {parsed.command}: {e}")
            yield {
                "type": "command.failed",
                "command": parsed.command,
                "mission_id": mission_id,
                "payload": {
                    "reason": f"Command execution exception: {str(e)}",
                    "error_class": type(e).__name__,
                },
            }
            yield {
                "type": "token",
                "content": f"\n💥 **Command `{parsed.command}` failed:** {str(e)}\n",
            }

    def _register_default_commands(self) -> None:
        """Register the 16 core commands."""

        # 1. /init
        self.register(
            CommandDefinition(
                command="/init",
                description="Initialize or refresh repository intelligence, AST map, and PROJECT.md",
                syntax="/init [--full] [--refresh]",
                arguments_description="--full forces complete re-index; --refresh updates changed files incrementally",
                risk_level=CommandRisk.SPECIAL,
                permission_level=1,
                required_context=["repo_map", "file_tree"],
                required_tools=["repo_map_generator", "git_tool"],
                execution_mode=ExecutionMode.DIRECT,
                supports_streaming=True,
                supports_approval=False,
                supports_cancellation=True,
                examples=["/init", "/init --full", "/init --refresh"],
            ),
            InitCommandHandler.execute,
        )

        # 2. /plan
        self.register(
            CommandDefinition(
                command="/plan",
                description="Analyze user goal and produce verifiable multi-step plan without file modification",
                syntax="/plan <goal description>",
                arguments_description="Description of the feature, refactoring, or bug to plan",
                risk_level=CommandRisk.MEDIUM,
                permission_level=0,
                required_context=["repo_map", "symbol_index"],
                required_tools=["repo_map_generator"],
                execution_mode=ExecutionMode.PLANNING,
                supports_streaming=True,
                supports_approval=True,
                supports_cancellation=True,
                examples=["/plan implement JWT authentication", "/plan optimize database queries"],
            ),
            PlanCommandHandler.execute,
        )

        # 3. /review
        self.register(
            CommandDefinition(
                command="/review",
                description="Review current working tree modifications for security, bugs, and performance",
                syntax="/review [target_path]",
                arguments_description="Optional target file or subsystem path to scope review",
                risk_level=CommandRisk.MEDIUM,
                permission_level=0,
                required_context=["git_diff", "working_tree"],
                required_tools=["git_tool"],
                execution_mode=ExecutionMode.DIRECT,
                supports_streaming=True,
                supports_approval=False,
                supports_cancellation=True,
                examples=["/review", "/review app/core/permissions.py"],
            ),
            ReviewCommandHandler.execute,
        )

        # 4. /test
        self.register(
            CommandDefinition(
                command="/test",
                description="Run appropriate test suites across detected project frameworks",
                syntax="/test [subsystem/target]",
                arguments_description="Optional subsystem (e.g. backend, frontend) or test pattern",
                risk_level=CommandRisk.MEDIUM,
                permission_level=1,
                required_context=["test_configs"],
                required_tools=["process_runner"],
                execution_mode=ExecutionMode.VERIFICATION,
                supports_streaming=True,
                supports_approval=False,
                supports_cancellation=True,
                examples=["/test", "/test backend", "/test frontend", "/test auth"],
            ),
            TestCommandHandler.execute,
        )

        # 5. /debug
        self.register(
            CommandDefinition(
                command="/debug",
                description="Investigate a failure or error message, find relevant code, and diagnose root cause",
                syntax="/debug <error message or issue>",
                arguments_description="Stack trace, error message, or description of failing behavior",
                risk_level=CommandRisk.MEDIUM,
                permission_level=0,
                required_context=["ripgrep", "repo_map"],
                required_tools=["ripgrep_search"],
                execution_mode=ExecutionMode.REACT,
                supports_streaming=True,
                supports_approval=False,
                supports_cancellation=True,
                examples=["/debug API returns 500 when creating project", "/debug failing tests"],
            ),
            DebugCommandHandler.execute,
        )

        # 6. /fix
        self.register(
            CommandDefinition(
                command="/fix",
                description="Execute end-to-end fix: inspect, formulate patch, request approval, and verify",
                syntax="/fix <issue description>",
                arguments_description="Description of the bug or problem to fix",
                risk_level=CommandRisk.HIGH,
                permission_level=3,
                required_context=["working_tree", "repo_map"],
                required_tools=["git_tool", "patcher", "process_runner"],
                execution_mode=ExecutionMode.REACT,
                supports_streaming=True,
                supports_approval=True,
                supports_cancellation=True,
                examples=["/fix handle null values in user profile", "/fix broken import in utils"],
            ),
            FixCommandHandler.execute,
        )

        # 7. /explain
        self.register(
            CommandDefinition(
                command="/explain",
                description="Explain code, files, or architecture flows using AST and repository graph",
                syntax="/explain <file_path or concept>",
                arguments_description="File path or architectural topic to explain",
                risk_level=CommandRisk.LOW,
                permission_level=0,
                required_context=["ast_parser", "repo_map", "knowledge_graph"],
                required_tools=["ast_parser", "ripgrep_search"],
                execution_mode=ExecutionMode.DIRECT,
                supports_streaming=True,
                supports_approval=False,
                supports_cancellation=True,
                examples=["/explain app/core/permissions.py", "/explain authentication flow"],
            ),
            ExplainCommandHandler.execute,
        )

        # 8. /search
        self.register(
            CommandDefinition(
                command="/search",
                description="Intelligent hybrid repository search with ripgrep exact matching and symbol indexing",
                syntax="/search <query>",
                arguments_description="Search query string or regex pattern",
                risk_level=CommandRisk.LOW,
                permission_level=0,
                required_context=["ripgrep_search"],
                required_tools=["ripgrep_search"],
                execution_mode=ExecutionMode.DIRECT,
                supports_streaming=True,
                supports_approval=False,
                supports_cancellation=True,
                examples=["/search JWT_SECRET", '/search "class ProcessRunner"'],
            ),
            SearchCommandHandler.execute,
        )

        # 9. /inspect
        self.register(
            CommandDefinition(
                command="/inspect",
                description="Deeply inspect file, directory, or module stats, AST symbols, and manifests",
                syntax="/inspect [path]",
                arguments_description="File or directory path to inspect (defaults to current workspace root)",
                risk_level=CommandRisk.LOW,
                permission_level=0,
                required_context=["ast_parser", "file_stat"],
                required_tools=["ast_parser"],
                execution_mode=ExecutionMode.DIRECT,
                supports_streaming=True,
                supports_approval=False,
                supports_cancellation=True,
                examples=["/inspect app/main.py", "/inspect tests/", "/inspect package.json"],
            ),
            InspectCommandHandler.execute,
        )

        # 10. /status
        self.register(
            CommandDefinition(
                command="/status",
                description="Display current agent, mission, Git working tree, and index state without leaking secrets",
                syntax="/status",
                arguments_description="No arguments required",
                risk_level=CommandRisk.LOW,
                permission_level=0,
                required_context=["git_status", "mission_state"],
                required_tools=["git_tool"],
                execution_mode=ExecutionMode.DIRECT,
                supports_streaming=True,
                supports_approval=False,
                supports_cancellation=True,
                examples=["/status"],
            ),
            StatusCommandHandler.execute,
        )

        # 11. /diff
        self.register(
            CommandDefinition(
                command="/diff",
                description="Show structured Git diff with additions, deletions, and risk assessment",
                syntax="/diff [target_path]",
                arguments_description="Optional target file path to inspect",
                risk_level=CommandRisk.LOW,
                permission_level=0,
                required_context=["git_diff"],
                required_tools=["git_tool"],
                execution_mode=ExecutionMode.DIRECT,
                supports_streaming=True,
                supports_approval=False,
                supports_cancellation=True,
                examples=["/diff", "/diff app/core/patcher.py"],
            ),
            DiffCommandHandler.execute,
        )

        # 12. /commit
        self.register(
            CommandDefinition(
                command="/commit",
                description="Stage changes, run tests, formulate commit message, and request approval before committing",
                syntax="/commit [custom message]",
                arguments_description="Optional commit message (generated automatically if omitted)",
                risk_level=CommandRisk.HIGH,
                permission_level=3,
                required_context=["git_diff", "git_status"],
                required_tools=["git_tool"],
                execution_mode=ExecutionMode.DIRECT,
                supports_streaming=True,
                supports_approval=True,
                supports_cancellation=True,
                examples=["/commit", '/commit "feat: implement OAuth token verification"'],
            ),
            GitCommandHandlers.handle_commit,
        )

        # 13. /undo
        self.register(
            CommandDefinition(
                command="/undo",
                description="Safely revert agent-created uncommitted changes in working tree with user confirmation",
                syntax="/undo",
                arguments_description="No arguments required",
                risk_level=CommandRisk.HIGH,
                permission_level=3,
                required_context=["git_status"],
                required_tools=["git_tool"],
                execution_mode=ExecutionMode.DIRECT,
                supports_streaming=True,
                supports_approval=True,
                supports_cancellation=True,
                examples=["/undo"],
            ),
            GitCommandHandlers.handle_undo,
        )

        # 14. /reset
        self.register(
            CommandDefinition(
                command="/reset",
                description="Hard reset working tree to clean HEAD state. HIGH RISK: requires explicit --confirm",
                syntax="/reset [--confirm]",
                arguments_description="--confirm confirms discard of all uncommitted working tree changes",
                risk_level=CommandRisk.HIGH,
                permission_level=4,
                required_context=["git_status"],
                required_tools=["git_tool", "process_runner"],
                execution_mode=ExecutionMode.DIRECT,
                supports_streaming=True,
                supports_approval=True,
                supports_cancellation=True,
                examples=["/reset", "/reset --confirm"],
            ),
            GitCommandHandlers.handle_reset,
        )

        # 15. /clear
        self.register(
            CommandDefinition(
                command="/clear",
                description="Clear chat session timeline context while keeping durable project memory intact",
                syntax="/clear",
                arguments_description="No arguments required",
                risk_level=CommandRisk.LOW,
                permission_level=0,
                required_context=[],
                required_tools=[],
                execution_mode=ExecutionMode.DIRECT,
                supports_streaming=True,
                supports_approval=False,
                supports_cancellation=False,
                examples=["/clear"],
            ),
            UtilityCommandHandlers.handle_clear,
        )

        # 16. /help
        self.register(
            CommandDefinition(
                command="/help",
                description="Display available commands, usage syntax, risk levels, and examples",
                syntax="/help [command_name]",
                arguments_description="Optional command name to view detailed documentation for",
                risk_level=CommandRisk.LOW,
                permission_level=0,
                required_context=[],
                required_tools=[],
                execution_mode=ExecutionMode.DIRECT,
                supports_streaming=True,
                supports_approval=False,
                supports_cancellation=False,
                examples=["/help", "/help init", "/help plan", "/help test"],
            ),
            UtilityCommandHandlers.handle_help,
        )


# Global singleton instance
command_registry = CommandRegistry()
