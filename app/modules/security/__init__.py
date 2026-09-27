"""
Security Module
===============
Compatibility re-export of app.modules.auth.
"""
from app.modules.auth import *  # noqa: F401, F403
from app.modules.auth.auditing import security_audit
from app.modules.auth.service import auth_service
from app.modules.auth.context import AuthContext, ModelAccessContext
from app.modules.auth.policy_engine import AuthorizationDecision, policy_engine
from app.modules.auth.secrets import secret_manager, secret_redactor
from app.modules.auth.ssrf import SSRFFilter, SSRFProtectionError, ssrf_filter

__all__ = [
    "auth_service",
    "security_audit",
    "AuthContext",
    "ModelAccessContext",
    "policy_engine",
    "AuthorizationDecision",
    "secret_manager",
    "secret_redactor",
    "ssrf_filter",
    "SSRFFilter",
    "SSRFProtectionError",
]
