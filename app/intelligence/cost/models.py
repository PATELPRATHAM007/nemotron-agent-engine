"""
Backward compatibility re-export. Real models live in app.modules.cost.models.
"""
from app.modules.cost.models import CostRecord

__all__ = ["CostRecord"]
