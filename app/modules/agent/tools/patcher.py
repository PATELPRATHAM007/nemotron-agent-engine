"""
Minimal Diff Patcher & Hunk Replacement Engine
==============================================
Applies surgical, minimal code edits to target files without rewriting entire contents.
Preserves existing formatting, comments, and unrelated functions.
Generates unified git-style diffs and detects conflict mismatches.
"""

from dataclasses import dataclass, field
import difflib
import os
from typing import Any

from app.modules.agent.tools.workspace import (
    ConcurrencyConflictError,
    WorkspaceSandbox,
    workspace_sandbox,
)


@dataclass
class PatchResult:
    """Result of an atomic patch or edit operation."""

    success: bool
    filepath: str
    diff: str = ""
    replacements_made: int = 0
    error: str | None = None
    old_sha256: str = ""
    new_sha256: str = ""


class DiffPatcher:
    """Surgical code editor and hunk replacement engine."""

    def __init__(self, sandbox: WorkspaceSandbox | None = None):
        self.sandbox = sandbox or workspace_sandbox

    def edit_file(
        self,
        filepath: str,
        target_snippet: str,
        replacement_snippet: str,
        allow_multiple: bool = False,
        expected_base_sha256: str | None = None,
    ) -> PatchResult:
        """
        Replace target_snippet with replacement_snippet in filepath.
        Performs concurrency check, applies minimal hunk edit, and returns unified diff.
        """
        try:
            abs_path = self.sandbox.resolve_path(filepath)
            rel_path = self.sandbox.get_relative_path(abs_path)

            if not os.path.exists(abs_path):
                return PatchResult(
                    success=False,
                    filepath=rel_path,
                    error=f"File not found: '{rel_path}'",
                )

            # Concurrency check
            self.sandbox.verify_no_conflict(abs_path, expected_base_sha256=expected_base_sha256)

            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                original_content = f.read()

            old_fp = self.sandbox.compute_fingerprint(abs_path)

            # Check presence of target snippet
            if target_snippet not in original_content:
                # Try normalized whitespace fallback
                norm_original = original_content.replace("\r\n", "\n")
                norm_target = target_snippet.replace("\r\n", "\n")
                if norm_target in norm_original:
                    original_content = norm_original
                    target_snippet = norm_target
                else:
                    return PatchResult(
                        success=False,
                        filepath=rel_path,
                        error=f"Target snippet not found in '{rel_path}'. Verify exact indentation and lines.",
                        old_sha256=old_fp["sha256"],
                    )

            occurrences = original_content.count(target_snippet)
            if occurrences > 1 and not allow_multiple:
                return PatchResult(
                    success=False,
                    filepath=rel_path,
                    error=f"Target snippet occurs {occurrences} times in '{rel_path}'. Provide more context lines to ensure unique replacement.",
                    old_sha256=old_fp["sha256"],
                )

            # Apply replacement
            if allow_multiple:
                new_content = original_content.replace(target_snippet, replacement_snippet)
                replacements_count = occurrences
            else:
                new_content = original_content.replace(target_snippet, replacement_snippet, 1)
                replacements_count = 1

            # Write updated content
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            new_fp = self.sandbox.compute_fingerprint(abs_path)

            # Generate unified diff
            diff = "".join(
                difflib.unified_diff(
                    original_content.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    fromfile=f"a/{rel_path}",
                    tofile=f"b/{rel_path}",
                )
            )

            return PatchResult(
                success=True,
                filepath=rel_path,
                diff=diff,
                replacements_made=replacements_count,
                old_sha256=old_fp["sha256"],
                new_sha256=new_fp["sha256"],
            )

        except ConcurrencyConflictError as cce:
            return PatchResult(
                success=False,
                filepath=filepath,
                error=str(cce),
            )
        except OSError as e:
            return PatchResult(
                success=False,
                filepath=filepath,
                error=f"Filesystem I/O error: {e!s}",
            )

    def preview_diff(self, filepath: str, new_content: str) -> str:
        """Preview unified diff between existing file on disk and proposed new content."""
        abs_path = self.sandbox.resolve_path(filepath)
        rel_path = self.sandbox.get_relative_path(abs_path)

        old_content = ""
        if os.path.exists(abs_path):
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                old_content = f.read()

        return "".join(
            difflib.unified_diff(
                old_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=f"a/{rel_path}",
                tofile=f"b/{rel_path}",
            )
        )


diff_patcher = DiffPatcher()
