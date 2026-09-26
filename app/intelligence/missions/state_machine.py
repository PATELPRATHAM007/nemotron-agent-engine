"""
Mission State Machine & Execution Phases
========================================
Formalizes the 13 discrete execution states:
  IDLE -> UNDERSTANDING -> PLANNING -> WAITING_FOR_SELECTION ->
  WAITING_FOR_PERMISSION -> EXECUTING -> TESTING -> VERIFYING ->
  COMPLETED / FAILED / BLOCKED / PAUSED / CANCELLED
"""

from enum import Enum
from typing import Any


class MissionState(str, Enum):
    """Discrete finite states of an Autonomous Mission."""

    IDLE = "IDLE"
    UNDERSTANDING = "UNDERSTANDING"
    PLANNING = "PLANNING"
    WAITING_FOR_SELECTION = "WAITING_FOR_SELECTION"
    WAITING_FOR_PERMISSION = "WAITING_FOR_PERMISSION"
    EXECUTING = "EXECUTING"
    TESTING = "TESTING"
    VERIFYING = "VERIFYING"
    BLOCKED = "BLOCKED"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


VALID_TRANSITIONS: dict[MissionState, set[MissionState]] = {
    MissionState.IDLE: {
        MissionState.UNDERSTANDING,
        MissionState.PLANNING,
        MissionState.EXECUTING,
        MissionState.CANCELLED,
    },
    MissionState.UNDERSTANDING: {
        MissionState.PLANNING,
        MissionState.WAITING_FOR_SELECTION,
        MissionState.WAITING_FOR_PERMISSION,
        MissionState.EXECUTING,
        MissionState.COMPLETED,
        MissionState.FAILED,
        MissionState.CANCELLED,
    },
    MissionState.PLANNING: {
        MissionState.WAITING_FOR_SELECTION,
        MissionState.WAITING_FOR_PERMISSION,
        MissionState.EXECUTING,
        MissionState.BLOCKED,
        MissionState.PAUSED,
        MissionState.FAILED,
        MissionState.CANCELLED,
    },
    MissionState.WAITING_FOR_SELECTION: {
        MissionState.PLANNING,
        MissionState.EXECUTING,
        MissionState.WAITING_FOR_PERMISSION,
        MissionState.PAUSED,
        MissionState.CANCELLED,
    },
    MissionState.WAITING_FOR_PERMISSION: {
        MissionState.EXECUTING,
        MissionState.PLANNING,
        MissionState.BLOCKED,
        MissionState.PAUSED,
        MissionState.CANCELLED,
    },
    MissionState.EXECUTING: {
        MissionState.TESTING,
        MissionState.WAITING_FOR_PERMISSION,
        MissionState.WAITING_FOR_SELECTION,
        MissionState.VERIFYING,
        MissionState.PAUSED,
        MissionState.BLOCKED,
        MissionState.FAILED,
        MissionState.CANCELLED,
    },
    MissionState.TESTING: {
        MissionState.EXECUTING,  # Re-execute/debug
        MissionState.VERIFYING,
        MissionState.FAILED,
        MissionState.PAUSED,
        MissionState.CANCELLED,
    },
    MissionState.VERIFYING: {
        MissionState.COMPLETED,
        MissionState.EXECUTING,  # Remediation
        MissionState.FAILED,
        MissionState.CANCELLED,
    },
    MissionState.BLOCKED: {
        MissionState.WAITING_FOR_PERMISSION,
        MissionState.PLANNING,
        MissionState.EXECUTING,
        MissionState.CANCELLED,
    },
    MissionState.PAUSED: {
        MissionState.UNDERSTANDING,
        MissionState.PLANNING,
        MissionState.EXECUTING,
        MissionState.TESTING,
        MissionState.CANCELLED,
    },
    MissionState.COMPLETED: {
        MissionState.UNDERSTANDING,  # New turn in same mission
        MissionState.PLANNING,
        MissionState.IDLE,
    },
    MissionState.FAILED: {
        MissionState.UNDERSTANDING,
        MissionState.PLANNING,
        MissionState.IDLE,
    },
    MissionState.CANCELLED: {
        MissionState.UNDERSTANDING,
        MissionState.PLANNING,
        MissionState.IDLE,
    },
}


class MissionStateMachine:
    """Manages verified state transitions and yields audit records."""

    def __init__(self, initial_state: MissionState = MissionState.IDLE):
        self.current_state = initial_state

    def can_transition_to(self, target_state: MissionState) -> bool:
        allowed = VALID_TRANSITIONS.get(self.current_state, set())
        return target_state in allowed

    def transition(self, target_state: MissionState, reason: str = "") -> dict[str, Any]:
        """Perform transition and return transition event payload."""
        prev = self.current_state
        self.current_state = target_state
        return {
            "type": "state_change",
            "previous_state": prev.value,
            "current_state": target_state.value,
            "reason": reason,
        }
