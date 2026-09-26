"""
Centralized Authorization Policy Engine
=======================================
Implements RBAC + ABAC + Resource-Level Ownership with strict precedence:
  DENY > ASK > ALLOW

Evaluates:
  decision = policy_engine.authorize(subject, action, resource, context)
"""

from enum import Enum
from typing import Any

from app.security.context import AuthContext


class AuthorizationDecision(str, Enum):
    ALLOW = "ALLOW"
    ASK = "ASK"
    DENY = "DENY"

    @property
    def allowed(self) -> bool:
        return self == AuthorizationDecision.ALLOW

    @property
    def decision(self) -> str:
        return self.value


# Role-to-Permissions Mapping
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "SUPER_ADMIN": {
        "*"  # Unrestricted platform administration
    },
    "ORG_ADMIN": {
        "project.read", "project.write", "repository.read", "repository.write",
        "mission.create", "mission.execute", "mission.stop", "terminal.execute",
        "file.read", "file.write", "file.delete", "git.read", "git.commit", "git.push",
        "database.read", "database.write", "database.migrate",
        "model.list", "model.use", "model.use.premium", "model.configure",
        "provider.configure", "secret.read", "secret.rotate",
        "agent.register", "agent.execute", "artifact.read", "artifact.write"
    },
    "PROJECT_ADMIN": {
        "project.read", "project.write", "repository.read", "repository.write",
        "mission.create", "mission.execute", "mission.stop", "terminal.execute",
        "file.read", "file.write", "file.delete", "git.read", "git.commit", "git.push",
        "database.read", "database.write",
        "model.list", "model.use", "model.use.premium",
        "agent.register", "agent.execute", "artifact.read", "artifact.write"
    },
    "DEVELOPER": {
        "project.read", "repository.read", "repository.write",
        "mission.create", "mission.execute", "mission.stop", "terminal.execute",
        "file.read", "file.write", "git.read", "git.commit",
        "database.read",
        "model.list", "model.use",
        "agent.execute", "artifact.read", "artifact.write"
    },
    "MEMBER": {
        "project.read", "repository.read", "mission.create", "mission.execute",
        "file.read", "git.read", "model.list", "model.use", "artifact.read"
    },
    "VIEWER": {
        "project.read", "repository.read", "file.read", "git.read",
        "model.list", "artifact.read"
    },
    "AGENT": {
        "repository.read", "repository.write", "file.read", "file.write",
        "terminal.execute", "git.read", "artifact.read", "artifact.write"
    },
    "SERVICE": {
        "model.use", "artifact.read", "artifact.write"
    },
}

# Operations that inherently require human approval (ASK)
HIGH_RISK_ACTIONS = {
    "git.push",
    "database.migrate",
    "database.write",
    "secret.rotate",
    "secret.read",
    "model.use.premium",
    "file.delete",
}

# Actions that are strictly denied to non-superadmins
CRITICAL_ACTIONS = {
    "git.force_push",
    "database.drop",
    "system.root_shell",
}


class PolicyEngine:
    """Evaluates fine-grained multi-level authorization policies."""

    def authorize(
        self,
        context: AuthContext | None = None,
        action: str = "",
        resource_tenant_id: str | None = None,
        resource_id: str | None = None,
        is_production: bool = False,
        subject: AuthContext | None = None,
        resource: Any = None,
        environment: str = "development",
        is_destructive: bool = False,
    ) -> AuthorizationDecision:
        """
        Authorize action with DENY > ASK > ALLOW precedence.
        Enforces tenant isolation, RBAC role permissions, and risk gating.
        """
        effective_context = subject or context
        if not effective_context:
            return AuthorizationDecision.DENY

        if environment.lower() == "production" or is_destructive:
            is_production = True

        if resource and isinstance(resource, dict):
            resource_tenant_id = resource.get("organization_id", resource_tenant_id)
            resource_id = resource.get("id", resource_id)

        # 1. Hard DENY check for prohibited actions
        if action in CRITICAL_ACTIONS:
            return AuthorizationDecision.DENY

        # 2. Tenant Isolation check: user tenant must match resource tenant
        if resource_tenant_id and resource_tenant_id != effective_context.organization_id:
            if not effective_context.has_role("SUPER_ADMIN"):
                return AuthorizationDecision.DENY

        # 3. Super Admin bypass (except for critical blocked actions)
        if effective_context.has_role("SUPER_ADMIN"):
            return AuthorizationDecision.ALLOW

        # 4. Check if user's roles grant the required permission
        user_permissions: set[str] = set()
        for role in effective_context.roles:
            perms = ROLE_PERMISSIONS.get(role, set())
            if "*" in perms:
                user_permissions.add("*")
            user_permissions.update(perms)

        # Include direct permissions or scopes
        user_permissions.update(effective_context.permissions)
        user_permissions.update(effective_context.scopes)

        has_perm = ("*" in user_permissions) or (action in user_permissions)
        if not has_perm:
            return AuthorizationDecision.DENY

        # 5. Production operations require explicit ASK approval
        if is_production and action in ("database.write", "database.migrate", "terminal.execute"):
            return AuthorizationDecision.ASK

        # 6. High-risk operations require interactive approval (ASK)
        if action in HIGH_RISK_ACTIONS:
            return AuthorizationDecision.ASK

        # 7. Allowed
        return AuthorizationDecision.ALLOW


policy_engine = PolicyEngine()
