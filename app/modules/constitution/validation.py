"""
Constitution Module Validation
==============================
"""

import re
from fastapi import HTTPException, status
from app.modules.constitution import messages


class ConstitutionValidator:
    """Validates rule names and prevents path traversal."""

    @staticmethod
    def validate_rule_name(rule_name: str) -> str:
        """Ensure rule name contains only alphanumeric characters and dashes."""
        if not re.match(r"^[a-zA-Z0-9_\-]+$", rule_name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=messages.INVALID_RULE_NAME,
            )
        return rule_name
