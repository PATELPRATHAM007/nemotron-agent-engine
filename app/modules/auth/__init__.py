"""
Auth Module
===========
Provides identity, authentication, session lifecycle, security policy, secrets, and agent enrollment.
"""
from app.modules.auth.auditing import security_audit
from app.modules.auth.context import AuthContext, ModelAccessContext
from app.modules.auth.models import (
    Agent,
    AuditEvent,
    Organization,
    Project,
    RefreshToken,
    SecurityEvent,
    User,
    UserSession,
)
from app.modules.auth.policy_engine import AuthorizationDecision, policy_engine
from app.modules.auth.secrets import secret_manager, secret_redactor
from app.modules.auth.service import AuthenticationService, auth_service
from app.modules.auth.ssrf import SSRFFilter, SSRFProtectionError, ssrf_filter


def __getattr__(name: str):
    if name == "router":
        from app.modules.auth.router import router
        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "User",
    "Organization",
    "Project",
    "UserSession",
    "RefreshToken",
    "Agent",
    "AuditEvent",
    "SecurityEvent",
    "AuthContext",
    "ModelAccessContext",
    "auth_service",
    "AuthenticationService",
    "policy_engine",
    "AuthorizationDecision",
    "secret_manager",
    "secret_redactor",
    "ssrf_filter",
    "SSRFFilter",
    "SSRFProtectionError",
    "security_audit",
    "router",
]
