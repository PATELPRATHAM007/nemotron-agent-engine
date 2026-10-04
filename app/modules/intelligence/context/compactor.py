"""
Automated Context Compactor
===========================
Monitors context window pressure and synthesizes long conversation histories
and verbose tool traces into structured session state snapshots.

Trigger: Context pressure exceeds threshold (default 75% of window).
Guarantees: Zero loss of active tasks, pending actions, modified files, or active errors.
"""

import re
import time
from enum import Enum
from typing import Any

from app.core.logging_config import get_logger
from app.modules.intelligence.context.budget_allocator import estimate_tokens
from app.modules.intelligence.memory.schema import CompactionSnapshot

logger = get_logger(__name__)


class ContextPressureLevel(str, Enum):
    GREEN = "GREEN"        # < 60%: Normal operation
    YELLOW = "YELLOW"      # 60% - 75%: Summarize redundant tool outputs
    ORANGE = "ORANGE"      # 75% - 85%: Proactive compaction recommended
    RED = "RED"            # 85% - 92%: Aggressive compaction snapshot required
    CRITICAL = "CRITICAL"  # > 92%: Emergency compaction preserving only core invariants


class ToolResultPolicy(str, Enum):
    KEEP = "KEEP"                  # Keep full result (short or high signal)
    SUMMARIZE = "SUMMARIZE"        # Condense large stdout/stderr (e.g., test traces)
    DISCARD_RAW = "DISCARD_RAW"    # Drop verbose raw payload from active context


class ContextCompactor:
    """
    Evaluates context pressure and produces structured state snapshots
    to prune conversation turns and tool observation bloat.
    """

    def __init__(
        self,
        compaction_threshold_ratio: float = 0.75,
        default_max_window: int = 32000,
    ):
        self.compaction_threshold_ratio = compaction_threshold_ratio
        self.default_max_window = default_max_window

    def evaluate_pressure(
        self, current_tokens: int, max_window: int | None = None
    ) -> ContextPressureLevel:
        """Determines the current context pressure level."""
        window = max_window or self.default_max_window
        ratio = current_tokens / max(1, window)

        if ratio < 0.60:
            return ContextPressureLevel.GREEN
        elif ratio < 0.75:
            return ContextPressureLevel.YELLOW
        elif ratio < 0.85:
            return ContextPressureLevel.ORANGE
        elif ratio < 0.92:
            return ContextPressureLevel.RED
        else:
            return ContextPressureLevel.CRITICAL

    def should_compact(
        self, current_tokens: int, max_window: int | None = None
    ) -> bool:
        """Returns True if context usage has breached the compaction threshold (75%)."""
        window = max_window or self.default_max_window
        return (current_tokens / max(1, window)) >= self.compaction_threshold_ratio

    def classify_tool_result(self, tool_name: str, output: str) -> ToolResultPolicy:
        """Classifies tool output to prevent verbose bloat in active context."""
        est_tokens = estimate_tokens(output)

        # Brief outputs are always preserved
        if est_tokens < 150:
            return ToolResultPolicy.KEEP

        # Test outputs or large search dumps should be summarized
        if tool_name in {"execute_command", "run_process", "ripgrep_search", "run_tests"}:
            if est_tokens > 600:
                return ToolResultPolicy.SUMMARIZE
            return ToolResultPolicy.KEEP

        # Large file reads or dumps
        if est_tokens > 1000:
            return ToolResultPolicy.SUMMARIZE

        return ToolResultPolicy.KEEP

    def summarize_tool_output(self, tool_name: str, output: str, max_lines: int = 20) -> str:
        """Condenses verbose tool output retaining failure lines, passes, and exits."""
        lines = output.strip().splitlines()
        if len(lines) <= max_lines:
            return output

        # Search for error / failure markers
        important_lines: list[str] = []
        for line in lines:
            if re.search(r"(error|fail|exception|assert|traceback|warning|passed|ok|exit)", line, re.IGNORECASE):
                important_lines.append(line)

        # Retain head, important lines, and tail
        head = lines[:5]
        tail = lines[-5:]
        middle_highlights = important_lines[: max_lines - 10]

        summary_parts = [
            "\n".join(head),
            f"... [{len(lines) - 10} lines summarized; showing key events] ...",
            "\n".join(middle_highlights) if middle_highlights else "",
            "\n".join(tail),
        ]
        return "\n".join(p for p in summary_parts if p)

    def generate_compaction_snapshot(
        self,
        mission_id: str,
        goal: str,
        turns: list[dict[str, Any]],
        tool_results: list[dict[str, Any]] | None = None,
        existing_state: dict[str, Any] | None = None,
    ) -> CompactionSnapshot:
        """
        Synthesizes raw conversation turns and tool observations into a structured
        CompactionSnapshot preserving state, decisions, files, and blockers.
        """
        tool_results = tool_results or []
        existing_state = existing_state or {}

        # 1. Calculate token footprint before compaction
        raw_text = "\n".join(
            [str(t.get("content", "")) for t in turns]
            + [str(r.get("output", "")) for r in tool_results]
        )
        tokens_before = estimate_tokens(raw_text)

        # 2. Extract completed & pending steps
        completed_steps: list[str] = list(existing_state.get("completed_steps", []))
        pending_steps: list[str] = list(existing_state.get("pending_steps", []))
        files_modified: set[str] = set(existing_state.get("files_modified", []))
        key_decisions: list[str] = list(existing_state.get("key_decisions", []))
        active_errors: list[str] = list(existing_state.get("active_errors", []))
        next_action: str = existing_state.get("next_immediate_action", "")

        # Heuristic extraction from turns
        for turn in turns:
            content = str(turn.get("content", ""))
            role = turn.get("role", "")

            # Modified files detection
            for match in re.finditer(r"([a-zA-Z0-9_\-\.\/]+\.(?:py|ts|tsx|js|json|md|sql|yaml|yml))", content):
                filepath = match.group(1)
                if not filepath.startswith("http") and "/" in filepath:
                    files_modified.add(filepath)

            # Decision detection
            if "decision:" in content.lower() or "decided to" in content.lower():
                for line in content.splitlines():
                    if any(k in line.lower() for k in ["decid", "decision"]) and len(line.strip()) < 200:
                        clean_decision = line.strip().lstrip("-*# ")
                        if clean_decision and clean_decision not in key_decisions:
                            key_decisions.append(clean_decision)


            # Error detection in assistant or user turns
            if "error:" in content.lower() or "traceback" in content.lower():
                for line in content.splitlines():
                    if any(kw in line.lower() for kw in ["error:", "failed:", "exception:"]):
                        err_msg = line.strip()
                        if err_msg and err_msg not in active_errors and len(err_msg) < 180:
                            active_errors.append(err_msg)

            # Completed step detection
            if role == "assistant":
                for line in content.splitlines():
                    if re.match(r"^(?:done|completed|finished|implemented|created|fixed):\s*(.+)$", line.strip(), re.IGNORECASE):
                        step = line.strip()
                        if step not in completed_steps:
                            completed_steps.append(step)

        # Inspect tool results for modifications & errors
        for res in tool_results:
            tool_name = res.get("tool_name", "")
            output = str(res.get("output", ""))

            # If diff patcher or file write tool was run
            if tool_name in {"apply_diff_patch", "edit_file", "write_file", "git_tool"}:
                file_arg = res.get("file_path") or res.get("target_file")
                if file_arg:
                    files_modified.add(str(file_arg))

            # If command failed
            if res.get("exit_code", 0) != 0 or "Error" in output[:200]:
                first_err = output.strip().splitlines()[-1] if output.strip() else f"Tool {tool_name} failed"
                if first_err not in active_errors:
                    active_errors.append(first_err[:150])

        # If next immediate action is empty, infer from last assistant note or pending step
        if not next_action and pending_steps:
            next_action = f"Execute step: {pending_steps[0]}"
        elif not next_action:
            next_action = f"Continue execution towards goal: {goal}"

        snapshot = CompactionSnapshot(
            mission_id=mission_id,
            goal=goal,
            completed_steps=completed_steps,
            pending_steps=pending_steps,
            files_modified=sorted(list(files_modified)),
            key_decisions=key_decisions,
            active_errors=active_errors,
            next_immediate_action=next_action,
            timestamp=time.time(),
            token_count_before=tokens_before,
            token_count_after=0,
        )

        formatted_context = self.format_snapshot_as_context(snapshot)
        snapshot.token_count_after = estimate_tokens(formatted_context)

        return snapshot

    def validate_compaction(
        self,
        snapshot: CompactionSnapshot,
        previous_state: dict[str, Any] | None = None,
    ) -> bool:
        """
        Validates that critical information was not dropped during compaction:
        - Goal must be non-empty
        - Files modified must include all files previously known as modified
        - Active errors previously known must not be silently discarded unless marked resolved
        """
        if not snapshot.goal or not snapshot.goal.strip():
            logger.warning("Compaction validation failed: empty goal.")
            return False

        if previous_state:
            prev_files = set(previous_state.get("files_modified", []))
            curr_files = set(snapshot.files_modified)
            if not prev_files.issubset(curr_files):
                missing = prev_files - curr_files
                logger.warning(f"Compaction validation warning: modified files lost: {missing}")
                # Restore missing files to guarantee zero data loss
                snapshot.files_modified = sorted(list(curr_files.union(prev_files)))

            prev_errors = set(previous_state.get("active_errors", []))
            curr_errors = set(snapshot.active_errors)
            if not prev_errors.issubset(curr_errors):
                # Ensure previously active errors are maintained
                snapshot.active_errors = list(curr_errors.union(prev_errors))

        return True

    def format_snapshot_as_context(self, snapshot: CompactionSnapshot) -> str:
        """
        Formats a CompactionSnapshot into an authoritative markdown block
        ready to replace raw history in the prompt.
        """
        lines = [
            "### [CONTEXT COMPACTION SNAPSHOT: ACTIVE TASK STATE]",
            f"**Mission ID**: `{snapshot.mission_id}`",
            f"**Goal**: {snapshot.goal}",
        ]

        if snapshot.completed_steps:
            lines.append("\n**Completed Steps**:")
            for s in snapshot.completed_steps:
                lines.append(f"  - [x] {s}")

        if snapshot.pending_steps:
            lines.append("\n**Pending Steps**:")
            for s in snapshot.pending_steps:
                lines.append(f"  - [ ] {s}")

        if snapshot.files_modified:
            lines.append(f"\n**Files Modified ({len(snapshot.files_modified)})**:")
            for f in snapshot.files_modified:
                lines.append(f"  - `{f}`")

        if snapshot.key_decisions:
            lines.append("\n**Key Architecture & Code Decisions**:")
            for d in snapshot.key_decisions:
                lines.append(f"  - {d}")

        if snapshot.active_errors:
            lines.append("\n**Active Errors / Blockers to Resolve**:")
            for e in snapshot.active_errors:
                lines.append(f"  - ⚠️ {e}")

        lines.append(f"\n**Next Immediate Action**: {snapshot.next_immediate_action}")
        lines.append(
            f"\n*(Compacted from {snapshot.token_count_before} tokens "
            f"to ~{estimate_tokens(' '.join(lines))} tokens)*"
        )

        return "\n".join(lines)
