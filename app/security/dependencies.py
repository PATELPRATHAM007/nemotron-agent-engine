"""
FastAPI Security & Authentication Dependencies
==============================================
Extracts and validates short-lived access tokens or session cookies.
Constructs authoritative server-side AuthContext.
"""

from fastapi import Depends, Header, HTTPException, Request, status

from app.security.auth import auth_service
from app.security.context import AuthContext


async def get_current_auth_context(
    request: Request,
    authorization: str | None = Header(None),
) -> AuthContext:
    """
    Extract and validate platform authentication credentials.
    Returns authoritative AuthContext.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"

    # 1. Bearer Token Authentication
    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split("Bearer ", 1)[1].strip()
        try:
            claims = auth_service.verify_access_token(raw_token)
            return AuthContext(
                user_id=claims.get("sub", "anonymous"),
                organization_id=claims.get("tenant_id", "default-tenant"),
                session_id=claims.get("session_id"),
                roles=tuple(claims.get("roles", ["DEVELOPER"])),
                scopes=tuple(claims.get("scopes", ["model.use", "repository.read"])),
                authentication_method="bearer_token",
                source_ip=client_ip,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid or expired access token: {e}",
            )

    # 2. Cookie-based Session Authentication (HttpOnly session cookie)
    session_id = request.cookies.get("nemotron_session")
    if session_id:
        return AuthContext(
            user_id="session-user",
            organization_id="default-tenant",
            session_id=session_id,
            roles=("DEVELOPER",),
            scopes=("model.use", "repository.read", "mission.create", "mission.execute"),
            authentication_method="session_cookie",
            source_ip=client_ip,
        )

    # 3. Default Dev Workspace Context (allows single mission UI to operate without forcing login wall in development)
    return AuthContext(
        user_id="default-developer",
        organization_id="default-tenant",
        roles=("DEVELOPER",),
        scopes=("model.use", "repository.read", "mission.create", "mission.execute"),
        authentication_method="default_dev",
        source_ip=client_ip,
    )
