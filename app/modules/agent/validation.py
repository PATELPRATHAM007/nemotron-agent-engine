"""
Agent Module Request Validation & Sanitization
==============================================
"""

import re
from typing import Any
from fastapi import HTTPException, status
from app.modules.agent import messages


class AgentValidator:
    """Validates agent prompts, model limits, and parameters."""

    @staticmethod
    def validate_goal(goal: str) -> str:
        """Validate agent mission objective."""
        if not goal or not goal.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=messages.GOAL_REQUIRED,
            )
        return goal.strip()

    @staticmethod
    def validate_iterations(max_iterations: int) -> int:
        """Verify max autonomous steps within safe boundaries."""
        if not (1 <= max_iterations <= 100):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=messages.MAX_ITERATIONS_INVALID,
            )
        return max_iterations

    @staticmethod
    def sanitize_prompt(prompt: str) -> str:
        """Strip control characters and excess whitespace."""
        return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", prompt).strip()
