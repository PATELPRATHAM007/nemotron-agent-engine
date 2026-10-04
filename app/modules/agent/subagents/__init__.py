"""
Subagents Module
================
Isolated specialized subagents for repository development:
  - Researcher: Read-only exploration and architecture mapping
  - Coder: Surgical diff editing under scope locks
  - Reviewer: Constitutional audit and boundary verification
  - Tester: Isolated test execution and diagnosis
"""

from app.modules.agent.subagents.coordinator import (
    SubagentCoordinator,
    SubagentResult,
    SubagentRole,
    subagent_coordinator,
)

__all__ = [
    "SubagentCoordinator",
    "SubagentResult",
    "SubagentRole",
    "subagent_coordinator",
]
