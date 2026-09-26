"""
Identity & Authentication API Endpoints
=======================================
Implements standards-based authentication:
  - User Registration & Argon2id Password Hashing
  - Login with Short-lived Access Token & Rotating Refresh Token
  - Token Refresh with Family Reuse Detection (RFC 6749 / 9700)
  - Session Inspection & Remote Revocation
  - Local Execution Agent Identity Registration
"""

from typing import Any
import uuid

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select

from app.db.session import DatabaseService
from app.security.auditing import security_audit
from app.security.auth import auth_service
from app.security.context import AuthContext
from app.security.dependencies import get_current_auth_context
from app.security.models import Agent, User, UserSession

router = APIRouter(prefix="/auth", tags=["Identity & Authentication"])


# -----------------------------------------------------------------------------
# Schemas
# -----------------------------------------------------------------------------
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


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest):
    """Register a new user account with Argon2id password hashing."""
    with DatabaseService.get_session() as session:
        stmt = select(User).where(User.email == payload.email)
        existing = session.scalars(stmt).first()
        if existing:
            raise HTTPException(status_code=400, detail="User with this email already exists")

        hashed_pw = auth_service.hash_password(payload.password)
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            email=payload.email,
            full_name=payload.full_name,
            hashed_password=hashed_pw,
            is_active=True,
            is_verified=True,
            tenant_id=payload.tenant_id,
            roles=["DEVELOPER"],
        )
        session.add(user)
        session.commit()
        session.refresh(user)

    security_audit.record_audit(
        actor_type="user",
        actor_id=user_id,
        action="user.registered",
        resource_type="user",
        resource_id=user_id,
        organization_id=payload.tenant_id,
    )

    return {
        "success": True,
        "user_id": user_id,
        "email": payload.email,
        "message": "User registered successfully",
    }


@router.post("/login")
async def login(payload: LoginRequest, response: Response):
    """Authenticate user credentials and issue short-lived access token + rotating refresh token."""
    with DatabaseService.get_session() as session:
        stmt = select(User).where(User.email == payload.email)
        user = session.scalars(stmt).first()

    if not user or not auth_service.verify_password(payload.password, user.hashed_password):
        security_audit.record_audit(
            actor_type="user",
            actor_id=payload.email,
            action="login.failed",
            resource_type="user",
            result="DENIED",
            reason="Invalid credentials",
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is inactive")

    db_session, access_token, raw_refresh_token = auth_service.create_session(
        user=user,
        device_info="web-browser",
    )

    # Set secure HttpOnly cookie for session token
    response.set_cookie(
        key="nemotron_session",
        value=db_session.id,
        httponly=True,
        samesite="lax",
        secure=False,  # in dev; True in production TLS
        max_age=7 * 86400,
    )

    security_audit.record_audit(
        actor_type="user",
        actor_id=user.id,
        action="login.success",
        resource_type="session",
        resource_id=db_session.id,
        organization_id=user.tenant_id,
    )

    return {
        "success": True,
        "access_token": access_token,
        "refresh_token": raw_refresh_token,
        "token_type": "Bearer",
        "expires_in": 900,
        "session_id": db_session.id,
        "user": user.to_dict(),
    }


@router.post("/refresh")
async def refresh_tokens(payload: RefreshRequest):
    """Rotate refresh token and issue new short-lived access token (RFC 6749 / 9700)."""
    try:
        new_access_token, new_refresh_token = auth_service.rotate_refresh_token(
            payload.refresh_token
        )
        return {
            "success": True,
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "Bearer",
            "expires_in": 900,
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/logout")
async def logout(
    response: Response,
    auth: AuthContext = Depends(get_current_auth_context),
):
    """Revoke active session and delete session cookie."""
    if auth.session_id:
        auth_service.revoke_session(auth.session_id)
        security_audit.record_audit(
            actor_type="user",
            actor_id=auth.user_id,
            action="logout",
            resource_type="session",
            resource_id=auth.session_id,
        )

    response.delete_cookie("nemotron_session")
    return {"success": True, "message": "Successfully logged out"}


@router.get("/me")
async def get_current_user_profile(auth: AuthContext = Depends(get_current_auth_context)):
    """Retrieve authenticated user identity, roles, and granted permissions."""
    return auth.to_dict()


@router.get("/sessions")
async def list_user_sessions(auth: AuthContext = Depends(get_current_auth_context)):
    """List active sessions for current user."""
    with DatabaseService.get_session() as session:
        stmt = (
            select(UserSession)
            .where(UserSession.user_id == auth.user_id, UserSession.is_active == True)
            .order_by(UserSession.last_active_at.desc())
        )
        sessions = session.scalars(stmt).all()
        return [s.to_dict() for s in sessions]


@router.delete("/sessions/{session_id}")
async def revoke_user_session(
    session_id: str,
    auth: AuthContext = Depends(get_current_auth_context),
):
    """Revoke a specific session."""
    ok = auth_service.revoke_session(session_id)
    return {"success": ok, "session_id": session_id, "status": "REVOKED"}


# -----------------------------------------------------------------------------
# Local Agent Registration (Separate Identity)
# -----------------------------------------------------------------------------
@router.post("/agents/register")
async def register_agent(
    payload: AgentRegisterRequest,
    auth: AuthContext = Depends(get_current_auth_context),
):
    """Register local execution agent identity with its public key and declared capabilities."""
    agent_id = str(uuid.uuid4())
    with DatabaseService.get_session() as session:
        agent = Agent(
            id=agent_id,
            name=payload.name,
            project_id=payload.project_id,
            device_id=payload.device_id,
            status="ACTIVE",
            public_key=payload.public_key,
            capabilities=payload.capabilities,
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)

    security_audit.record_audit(
        actor_type="user",
        actor_id=auth.user_id,
        action="agent.registered",
        resource_type="agent",
        resource_id=agent_id,
        project_id=payload.project_id,
        metadata={"capabilities": payload.capabilities},
    )

    return {"success": True, "agent": agent.to_dict()}
