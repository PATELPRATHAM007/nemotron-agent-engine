"""
Backward compatibility re-export. Real module lives in app.modules.constitution.
"""
from app.modules.constitution.service import ConstitutionScaffolder

__all__ = ["ConstitutionScaffolder"]
