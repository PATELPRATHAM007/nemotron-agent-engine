"""
Constitution Module Data Models
===============================
"""

from pydantic import BaseModel


class ConstitutionRule(BaseModel):
    name: str
    description: str
    content: str
