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


__all__ = [
    "Agent",
    "AuditEvent",
    "AuthContext",
    "AuthenticationService",
    "AuthorizationDecision",
    "ModelAccessContext",
    "Organization",
    "Project",
    "RefreshToken",
    "SSRFFilter",
    "SSRFProtectionError",
    "SecurityEvent",
    "User",
    "UserSession",
    "auth_service",
    "policy_engine",
    "secret_manager",
    "secret_redactor",
    "security_audit",
    "ssrf_filter",
]
