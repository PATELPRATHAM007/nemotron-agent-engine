"""
Cost Module Validation
======================
Validates token count ranges, positive costs, and budget bounds.
"""

from app.modules.cost import messages


class CostValidator:
    """Validates token counts and cost values against negative or anomalous numbers."""

    @staticmethod
    def validate_positive_tokens(tokens: int) -> int:
        if tokens < 0:
            raise ValueError("Token counts cannot be negative")
        return tokens

    @staticmethod
    def validate_positive_cost(cost: float) -> float:
        if cost < 0.0:
            raise ValueError("Cost values cannot be negative")
        return round(cost, 6)
