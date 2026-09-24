"""
Pydantic Schemas for Agent Module
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class MissionRequest(BaseModel):
    goal: str = Field(..., description="The objective for the autonomous agent to solve")
    max_iterations: Optional[int] = Field(15, ge=1, le=50, description="Max autonomous reasoning loops")


class MissionResponse(BaseModel):
    success: bool
    mission_id: str
    goal: str
    stream_url: str


class AgentConfigResponse(BaseModel):
    nemotron_model: str
    nemotron_api_base: str
    thinking_enabled: bool
    gemini_model: str
    gemini_active: bool
