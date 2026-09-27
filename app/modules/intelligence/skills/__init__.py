"""
Modular Skills Engine
=====================
Discovers and injects reusable engineering skills from `skills/`.
"""

from app.modules.intelligence.skills.loader import SkillRegistry
from app.modules.intelligence.skills.schema import SkillMetadata

__all__ = ["SkillMetadata", "SkillRegistry"]
