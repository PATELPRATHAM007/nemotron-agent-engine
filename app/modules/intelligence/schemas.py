"""
Intelligence Module Schemas
===========================
"""

from typing import Any
from pydantic import BaseModel, Field


class ImpactAnalysisPayload(BaseModel):
    changed_files: list[str] = Field(..., description="List of modified or target files")
    depth: int = Field(2, ge=1, le=5, description="Graph traversal depth")


class ImpactAnalysisResponse(BaseModel):
    success: bool = True
    affected_files: list[str] = Field(default_factory=list)
    risk_level: str = "LOW"
    message: str = ""


class QueryAnalysisPayload(BaseModel):
    sql: str = Field(..., description="SQL query string to analyze")


class ASTSymbolQueryPayload(BaseModel):
    file_path: str = Field(..., description="Relative file path in workspace")
