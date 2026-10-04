"""
Auth Module API Endpoint Handlers (Controllers)
==============================================
Processes incoming requests, applies schema and format validation,
and invokes the auth service. Uses static message constants.
"""

import uuid

from fastapi import Depends, HTTPException, Response
from sqlalchemy import select

from app.db.session import DatabaseService
from app.modules.auth import messages
from app.modules.auth.auditing import security_audit
from app.modules.auth.context import AuthContext
from app.modules.auth.dependencies import get_current_auth_context
from app.modules.auth.models import Agent, User, UserSession
from app.modules.auth.policy_engine import ROLE_PERMISSIONS
from app.modules.auth.schemas import (
    AgentRegisterRequest,
    ApiKeyGenerateRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
)
from app.modules.auth.service import auth_service
from app.modules.auth.validation import AuthValidator


async def register(payload: RegisterRequest):
    """Register a new user account with Argon2id password hashing."""
    clean_email = AuthValidator.validate_email(payload.email)
    AuthValidator.validate_password_strength(payload.password)

    with DatabaseService.get_session() as session:
        stmt = select(User).where(User.email == clean_email)
        existing = session.scalars(stmt).first()
        if existing:
            raise HTTPException(status_code=400, detail=messages.USER_ALREADY_EXISTS)

        hashed_pw = auth_service.hash_password(payload.password)
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            email=clean_email,
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
        "email": clean_email,
        "message": messages.USER_REGISTER_SUCCESS,
    }


async def login(payload: LoginRequest, response: Response):
    """Authenticate credentials and issue short-lived access token + rotating refresh token."""
    clean_email = AuthValidator.validate_email(payload.email)

    with DatabaseService.get_session() as session:
        stmt = select(User).where(User.email == clean_email)
        user = session.scalars(stmt).first()

    if not user or not auth_service.verify_password(payload.password, user.hashed_password):
        security_audit.record_audit(
            actor_type="user",
            actor_id=clean_email,
            action="login.failed",
            resource_type="user",
            result="DENIED",
            reason=messages.INVALID_CREDENTIALS,
        )
        raise HTTPException(status_code=401, detail=messages.INVALID_CREDENTIALS)

    if not user.is_active:
        raise HTTPException(status_code=403, detail=messages.ACCOUNT_INACTIVE)

    db_session, access_token, raw_refresh_token = auth_service.create_session(
        user=user,
        device_info="web-browser",
    )

    response.set_cookie(
        key="nemotron_session",
        value=db_session.id,
        httponly=True,
        samesite="lax",
        secure=False,
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
            "message": messages.REFRESH_SUCCESS,
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


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
    return {"success": True, "message": messages.LOGOUT_SUCCESS}


async def me(auth: AuthContext = Depends(get_current_auth_context)):
    """Retrieve authenticated user identity, roles, and granted permissions."""
    return auth.to_dict()


async def list_sessions(auth: AuthContext = Depends(get_current_auth_context)):
    """List active sessions for current user."""
    with DatabaseService.get_session() as session:
        stmt = (
            select(UserSession)
            .where(UserSession.user_id == auth.user_id, UserSession.is_active == True)
            .order_by(UserSession.last_active_at.desc())
        )
        sessions = session.scalars(stmt).all()
        return [s.to_dict() for s in sessions]


async def revoke_session(
    session_id: str,
    auth: AuthContext = Depends(get_current_auth_context),
):
    """Revoke a specific user session."""
    ok = auth_service.revoke_session(session_id)
    return {"success": ok, "session_id": session_id, "status": "REVOKED", "message": messages.SESSION_REVOKED}


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

    return {"success": True, "agent": agent.to_dict(), "message": messages.AGENT_REGISTER_SUCCESS}


async def generate_api_key(payload: ApiKeyGenerateRequest):
    """
    Generate a signed, shareable JWT bearer API key with custom expiration and role permissions.
    Enables administrators to grant model and agent access to collaborators or microservices.
    """
    role_upper = payload.role.upper()
    if role_upper not in ROLE_PERMISSIONS:
        role_upper = "DEVELOPER"

    scopes = payload.scopes or list(ROLE_PERMISSIONS.get(role_upper, {"model.use", "repository.read"}))
    lifetime_seconds = payload.days * 86400

    token = auth_service.create_access_token(
        user_id=payload.email,
        session_id=f"apikey-{uuid.uuid4().hex[:12]}",
        tenant_id=payload.tenant_id,
        roles=[role_upper],
        scopes=scopes,
        lifetime_seconds=lifetime_seconds,
    )

    curl_cmd = f'curl -H "Authorization: Bearer {token}" http://localhost:8000/api/v1/auth/me'
    python_snippet = (
        f'import requests\n\n'
        f'headers = {{"Authorization": "Bearer {token}"}}\n'
        f'response = requests.get("http://localhost:8000/api/v1/models", headers=headers)\n'
        f'print(response.json())'
    )

    security_audit.record_audit(
        actor_type="system",
        actor_id="superuser",
        action="api_key.generated",
        resource_type="api_key",
        resource_id=payload.email,
        organization_id=payload.tenant_id,
        metadata={"role": role_upper, "days": payload.days},
    )

    return {
        "success": True,
        "token": token,
        "email": payload.email,
        "role": role_upper,
        "days": payload.days,
        "tenant_id": payload.tenant_id,
        "scopes": scopes,
        "curl_command": curl_cmd,
        "python_snippet": python_snippet,
        "message": f"API key generated for {payload.email} valid for {payload.days} days with {role_upper} permissions.",
    }

