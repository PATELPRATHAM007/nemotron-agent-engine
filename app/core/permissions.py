"""
7-Level Permission Architecture & Human Approval Gates
======================================================
Defines strict permission tiers:
  LEVEL 0 — Read Only (Default sandbox)
  LEVEL 1 — Analyze (Static analysis, read-only EXPLAIN query plans)
  LEVEL 2 — Modify Source (TaskScope contained code modifications)
  LEVEL 3 — Run Tests & Build (Subprocess execution in sandboxes)
  LEVEL 4 — Git Operations (Local branches, stashes, conventional commits)
  LEVEL 5 — Database Mutation & Migrations (Requires interactive human approval)
  LEVEL 6 — Deployment (Production deployments - disabled by default, requires signed approval)
"""

import time
import uuid
from enum import IntEnum

from pydantic import BaseModel, Field

from app.core.exceptions import PermissionDeniedError
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class PermissionLevel(IntEnum):
    LEVEL_0_READ_ONLY = 0
    LEVEL_1_ANALYZE = 1
    LEVEL_2_MODIFY_SOURCE = 2
    LEVEL_3_RUN_TESTS = 3
    LEVEL_4_GIT_OPS = 4
    LEVEL_5_DB_MUTATION = 5
    LEVEL_6_DEPLOYMENT = 6


class ApprovalRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    operation_type: str
    description: str
    required_level: PermissionLevel
    created_at: float = Field(default_factory=time.time)
    expires_at: float
    status: str = "PENDING"  # PENDING, APPROVED, REJECTED, EXPIRED
    approval_token: str | None = None
    reviewer_notes: str = ""


class PermissionManager:
    """Enforces active permission levels across all agent activities."""

    def __init__(
        self, current_level: PermissionLevel = PermissionLevel.LEVEL_2_MODIFY_SOURCE
    ):
        self.current_level = current_level

    def assert_permitted(
        self, required_level: PermissionLevel, operation_name: str
    ) -> bool:
        """Asserts that current permission level is greater than or equal to required level."""
        if self.current_level < required_level:
            raise PermissionDeniedError(
                f"🛑 Permission Denied: Operation '{operation_name}' requires "
                f"PermissionLevel.{required_level.name} ({required_level.value}), but the active "
                f"agent level is PermissionLevel.{self.current_level.name} ({self.current_level.value})."
            )
        return True


class ApprovalGateManager:
    """Manages interactive human-in-the-loop approval workflows for high-risk operations."""

    def __init__(self, default_timeout_seconds: int = 900):  # 15 minute default timeout
        self.default_timeout_seconds = default_timeout_seconds
        self._requests: dict[str, ApprovalRequest] = {}
        self._active_tokens: dict[str, ApprovalRequest] = {}

    def create_request(
        self,
        task_id: str,
        operation_type: str,
        description: str,
        required_level: PermissionLevel,
        timeout_seconds: int | None = None,
    ) -> ApprovalRequest:
        """Create a new pending human approval request."""
        timeout = (
            timeout_seconds
            if timeout_seconds is not None
            else self.default_timeout_seconds
        )
        req = ApprovalRequest(
            task_id=task_id,
            operation_type=operation_type,
            description=description,
            required_level=required_level,
            expires_at=time.time() + timeout,
        )
        self._requests[req.request_id] = req
        logger.warning(
            f"Approval gate created [ID: {req.request_id}] for {operation_type} requiring {required_level.name}"
        )
        return req

    def submit_decision(
        self, request_id: str, approved: bool, notes: str = ""
    ) -> ApprovalRequest:
        """Record human reviewer's decision on a pending request."""
        if request_id not in self._requests:
            raise KeyError(f"Approval request '{request_id}' not found.")

        req = self._requests[request_id]
        if time.time() > req.expires_at:
            req.status = "EXPIRED"
            raise TimeoutError(f"Approval request '{request_id}' has expired.")

        req.reviewer_notes = notes
        if approved:
            req.status = "APPROVED"
            token = f"auth_gate_{uuid.uuid4().hex[:16]}"
            req.approval_token = token
            self._active_tokens[token] = req
            logger.info(
                f"Human approval GRANTED for request {request_id}. Issued token: {token}"
            )
        else:
            req.status = "REJECTED"
            logger.warning(
                f"Human approval REJECTED for request {request_id}. Notes: {notes}"
            )

        return req

    def verify_token(self, token: str, required_level: PermissionLevel) -> bool:
        """Verify an approval token's validity, permission level, and expiration."""
        if not token or token not in self._active_tokens:
            return False

        req = self._active_tokens[token]
        if time.time() > req.expires_at:
            req.status = "EXPIRED"
            self._active_tokens.pop(token, None)
            return False

        if req.status != "APPROVED":
            return False

        return req.required_level >= required_level

    def consume_token(self, token: str) -> bool:
        """Consumes a one-time approval token after successful execution."""
        if token in self._active_tokens:
            del self._active_tokens[token]
            return True
        return False
