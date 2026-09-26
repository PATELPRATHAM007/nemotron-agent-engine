"""
Backward compatibility re-export. Real service lives in app.modules.constitution.service.
"""
from app.modules.constitution.service import (
    ConstitutionScaffolder,
    CODING_STANDARDS_MD,
    ARCHITECTURE_RULES_MD,
    TESTING_RULES_MD,
    GIT_RULES_MD,
    ADR_001_MD,
)

__all__ = [
    "ConstitutionScaffolder",
    "CODING_STANDARDS_MD",
    "ARCHITECTURE_RULES_MD",
    "TESTING_RULES_MD",
    "GIT_RULES_MD",
    "ADR_001_MD",
]
