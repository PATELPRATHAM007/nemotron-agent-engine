"""
Auth Module Pydantic Schemas
============================
Request and response validation models for the authentication subsystem.
"""

from typing import Any
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    full_name: str = ""
    tenant_id: str = "default-tenant"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class AgentRegisterRequest(BaseModel):
    name: str
    project_id: str = "default-project"
    device_id: str
    public_key: str
    capabilities: dict[str, Any] = Field(
        default_factory=lambda: {
            "terminal": True,
            "filesystem": True,
            "git": True,
            "browser": False,
            "docker": False,
        }
    )


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 900
    session_id: str | None = None
    user: dict[str, Any] | None = None
