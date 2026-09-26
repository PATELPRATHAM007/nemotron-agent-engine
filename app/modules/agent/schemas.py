"""
Pydantic Schemas for Agent Module
"""

from pydantic import BaseModel, Field


class MissionRequest(BaseModel):
    goal: str = Field(
        ..., description="The objective for the autonomous agent to solve"
    )
    max_iterations: int | None = Field(
        15, ge=1, le=50, description="Max autonomous reasoning loops"
    )


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


class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of the speaker: user, assistant, system")
    content: str = Field(..., description="Message text")


class ChatStreamRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., description="Chat conversation history")
    temperature: float = Field(default=0.6, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=16384)
    enable_thinking: bool = Field(default=True)

