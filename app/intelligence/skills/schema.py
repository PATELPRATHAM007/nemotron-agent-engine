"""
Skill Registry Schemas
======================
Data models for modular, reusable engineering skills.
"""

from pydantic import BaseModel, Field


class SkillMetadata(BaseModel):
    name: str
    category: str
    description: str
    keywords: list[str] = Field(default_factory=list)
    file_path: str
    content: str = ""
