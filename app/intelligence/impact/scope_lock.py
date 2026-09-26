"""
Task Scope Lock & Containment Engine
=====================================
Enforces impermeable boundaries around agent tasks, preventing the agent
from wandering through the codebase or making unintended modifications to
unrelated features.
"""

import os
from typing import Any

from pydantic import BaseModel, Field

from app.core.exceptions import ScopeViolationError


class TaskScope(BaseModel):
    """Encapsulates the explicit boundaries of an active agent mission."""

    task_id: str
    primary_feature: str = "general"
    allowed_edit_files: set[str] = Field(
        default_factory=set, description="Files explicitly authorized for modification"
    )
    read_only_dependency_files: set[str] = Field(
        default_factory=set, description="Context reference files (read-only)"
    )
    target_test_files: set[str] = Field(
        default_factory=set,
        description="Test files authorized for creation/modification",
    )
    primary_files: set[str] | None = None
    test_files: set[str] | None = None
    expansion_count: int = 0
    max_expansions: int = 1

    def model_post_init(self, context: Any, /) -> None:
        if self.primary_files:
            self.allowed_edit_files.update(self.primary_files)
        if self.test_files:
            self.target_test_files.update(self.test_files)

    def _normalize(self, path: str) -> str:
        """Normalize path for consistent set membership comparison."""
        return os.path.normpath(path).replace("\\", "/")

    def validate_edit(self, file_path: str) -> bool:
        """
        Validate whether a file can be legally modified under the current scope.
        Raises ScopeViolationError if the file is outside authorized boundaries.
        """
        clean_path = self._normalize(file_path)
        normalized_allowed = {
            self._normalize(f) for f in self.allowed_edit_files | self.target_test_files
        }

        # Check exact or suffix match
        is_allowed = clean_path in normalized_allowed or any(
            clean_path.endswith(f) for f in normalized_allowed
        )

        if not is_allowed:
            raise ScopeViolationError(
                f"🛑 Scope Lock Violation: Attempted to edit '{file_path}' which is outside "
                f"the authorized task scope for feature '{self.primary_feature}'.\n"
                f"Authorized files: {sorted(self.allowed_edit_files | self.target_test_files)}\n"
                f"To modify this file, the agent must submit an explicit Scope Expansion Request."
            )
        return True

    def request_expansion(self, file_path: str, reason: str, evidence: str) -> bool:
        """
        Request authorized expansion of scope with mandatory justification.
        Limited to max_expansions to prevent runaway agent wandering.
        """
        if self.expansion_count >= self.max_expansions:
            return False

        clean_path = self._normalize(file_path)
        self.allowed_edit_files.add(clean_path)
        self.expansion_count += 1
        return True
