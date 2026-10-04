"""
Security Module
===============
Compatibility re-export of app.modules.auth.
"""
from app.modules.auth import *
from app.modules.auth.auditing import security_audit
from app.modules.auth.context import AuthContext, ModelAccessContext
from app.modules.auth.policy_engine import AuthorizationDecision, policy_engine
from app.modules.auth.secrets import secret_manager, secret_redactor
from app.modules.auth.service import auth_service
from app.modules.auth.ssrf import SSRFFilter, SSRFProtectionError, ssrf_filter

__all__ = [
    "AuthContext",
    "AuthorizationDecision",
    "ModelAccessContext",
    "SSRFFilter",
    "SSRFProtectionError",
    "auth_service",
    "policy_engine",
    "secret_manager",
    "secret_redactor",
    "security_audit",
    "ssrf_filter",
]
