"""
Constitution Module Schemas
===========================
"""

from typing import Any
from pydantic import BaseModel, Field


class ScaffoldResponse(BaseModel):
    success: bool = True
    created_files: dict[str, str] = Field(default_factory=dict)
    message: str = ""


class RuleDetailResponse(BaseModel):
    rule_name: str
    content: str
