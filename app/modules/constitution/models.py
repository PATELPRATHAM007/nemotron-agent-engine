"""
Constitution Module Data Models
===============================
"""

from typing import Any
from pydantic import BaseModel, Field


class ConstitutionRule(BaseModel):
    name: str
    description: str
    content: str
