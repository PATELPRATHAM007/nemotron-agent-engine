"""
Security Audit & Threat Event Logging Subsystem
===============================================
Maintains immutable records of security-sensitive operations:
  - User Logins, Logouts, MFA, Passkeys, Session Revocations
  - Model Gateway Requests, Denials, Quota Breaches
  - Terminal & Tool Execution Approvals / Denials
  - SSRF Violations and Security Threats
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
import uuid

from app.core.logging_config import get_logger
from app.db.session import DatabaseService
from app.security.models import AuditEvent, SecurityEvent
from app.security.secrets import secret_redactor

logger = get_logger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SecurityAuditService:
    """Manages recording of immutable security events and audit streams."""

    def __init__(self, workspace_root: str = "."):
        self._fallback_dir = Path(workspace_root) / ".agent" / "audit"
        self._fallback_dir.mkdir(parents=True, exist_ok=True)

    def record_audit(
        self,
        actor_type: str,
        actor_id: str,
        action: str,
        resource_type: str,
        result: str = "SUCCESS",
        reason: str = "",
        resource_id: str | None = None,
        organization_id: str | None = None,
        project_id: str | None = None,
        mission_id: str | None = None,
        request_id: str | None = None,
        source_ip: str = "127.0.0.1",
        user_agent: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Record a security-critical audit event.
        Automatically redacts any sensitive credential fields before persistence.
        """
        event_id = str(uuid.uuid4())
        sanitized_meta = secret_redactor.redact_dict(metadata or {})
        sanitized_reason = secret_redactor.redact(reason)

        record = {
            "id": event_id,
            "timestamp": utc_now().isoformat(),
            "actor_type": actor_type,
            "actor_id": actor_id,
            "organization_id": organization_id,
            "project_id": project_id,
            "mission_id": mission_id,
            "request_id": request_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "result": result,
            "reason": sanitized_reason,
            "source_ip": source_ip,
            "metadata": sanitized_meta,
        }

        try:
            with DatabaseService.get_session() as session:
                ev = AuditEvent(
                    id=event_id,
                    actor_type=actor_type,
                    actor_id=actor_id,
                    organization_id=organization_id,
                    project_id=project_id,
                    mission_id=mission_id,
                    request_id=request_id,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    result=result,
                    reason=sanitized_reason,
                    source_ip=source_ip,
                    user_agent=user_agent,
                    event_metadata=sanitized_meta,
                )
                session.add(ev)
                session.commit()
                return record
        except Exception as e:
            logger.warning(f"Database audit write fallback to disk: {e}")

        # Fallback to local append-only JSON file
        try:
            with open(self._fallback_dir / "audit_events.jsonl", "a") as f:
                f.write(json.dumps(record) + "\n")
        except Exception:
            pass

        return record

    def record_security_violation(
        self,
        event_type: str,
        severity: str = "WARNING",
        actor_id: str | None = None,
        source_ip: str = "127.0.0.1",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record high-priority security anomaly (e.g. SSRF breach attempt, token tampering)."""
        event_id = str(uuid.uuid4())
        sanitized_details = secret_redactor.redact_dict(details or {})

        record = {
            "id": event_id,
            "timestamp": utc_now().isoformat(),
            "event_type": event_type,
            "severity": severity,
            "actor_id": actor_id,
            "source_ip": source_ip,
            "details": sanitized_details,
        }

        logger.error(
            f"SECURITY ALERT [{severity}]: {event_type} (actor={actor_id}, ip={source_ip}) -> {sanitized_details}"
        )

        try:
            with DatabaseService.get_session() as session:
                ev = SecurityEvent(
                    id=event_id,
                    event_type=event_type,
                    severity=severity,
                    actor_id=actor_id,
                    source_ip=source_ip,
                    details=sanitized_details,
                )
                session.add(ev)
                session.commit()
                return record
        except Exception as e:
            logger.warning(f"Database security event fallback to disk: {e}")

        try:
            with open(self._fallback_dir / "security_alerts.jsonl", "a") as f:
                f.write(json.dumps(record) + "\n")
        except Exception:
            pass

        return record


security_audit = SecurityAuditService()
