"""
Autonomous Mission Module Pydantic Schemas
==========================================
Request & response models for the Autonomous Mission Chat.
"""

from typing import Any
from pydantic import BaseModel, Field


class CreateMissionRequest(BaseModel):
    goal: str = Field(..., description="The objective or question for the autonomous agent")
    title: str | None = Field(None, description="Optional mission title")
    attachment_ids: list[str] = Field(default_factory=list, description="Associated image/screenshot IDs")
    execution_policy: dict[str, Any] = Field(
        default_factory=lambda: {"autonomy": "high", "review_policy": "interactive"}
    )


class MessageRequest(BaseModel):
    content: str = Field(..., description="Follow-up instruction, question, or approval")
    attachment_ids: list[str] = Field(default_factory=list)


class SelectionDecisionRequest(BaseModel):
    selection_id: str
    selected_option: str  # e.g. "A", "B", "C"


class PermissionDecisionRequest(BaseModel):
    request_id: str
    action: str  # "ALLOW" or "DENY"
    scope: str = "ONCE"  # "ONCE", "MISSION", "PROJECT", "ALWAYS"


class ImageUploadPayload(BaseModel):
    image_base64: str
    filename: str = "screenshot.png"
    mime_type: str = "image/png"
