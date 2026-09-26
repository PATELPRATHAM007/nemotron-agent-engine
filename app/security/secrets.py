"""
Provider Secrets Management & Sensitive Data Redactor
=====================================================
Implements:
  - SecretManager: Resolves credentials via vault references (vault://...)
    or KMS-backed envelope encryption at execution scope only.
  - SecretRedactor: Scrubbing of API keys, JWTs, Bearer tokens, passwords,
    private keys, connection strings, and cookies from logs, traces, and events.
"""

import base64
import os
import re
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Derive a consistent KMS-like envelope key from settings
KMS_MASTER_SALT = b"nemotron-secret-manager-kms-salt-2026"
KMS_MASTER_SEED = getattr(settings, "SECRET_KEY", "nemotron-production-master-kms-seed-32bytes")

kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=KMS_MASTER_SALT,
    iterations=100000,
)
ENVELOPE_KEY = base64.urlsafe_b64encode(kdf.derive(KMS_MASTER_SEED.encode()))
fernet = Fernet(ENVELOPE_KEY)


class SecretManager:
    """Secure credential resolver. Never exposes raw credentials to frontend or logs."""

    def __init__(self):
        # In-memory secure vault for references (e.g. vault://models/google/key-01)
        self._vault_store: dict[str, bytes] = {}
        self._initialize_default_credentials()

    def _initialize_default_credentials(self) -> None:
        """Seed vault store with environment secrets if present."""
        if getattr(settings, "GEMINI_API_KEY", None):
            self.store_secret(
                "vault://models/google/default-key",
                settings.GEMINI_API_KEY,
            )
        if getattr(settings, "NEMOTRON_API_KEY", None):
            self.store_secret(
                "vault://models/nemotron/default-key",
                settings.NEMOTRON_API_KEY,
            )

    def store_secret(self, secret_ref: str, raw_secret: str) -> str:
        """Encrypts raw credential with KMS envelope key and stores under reference."""
        if not secret_ref.startswith("vault://"):
            secret_ref = f"vault://{secret_ref.lstrip('/')}"
        encrypted_bytes = fernet.encrypt(raw_secret.encode())
        self._vault_store[secret_ref] = encrypted_bytes
        return secret_ref

    def resolve_credential(self, secret_reference: str) -> str:
        """
        Resolves credential reference into temporary in-memory plaintext.
        Raises ValueError if reference not found.
        """
        if not secret_reference.startswith("vault://"):
            secret_reference = f"vault://{secret_reference.lstrip('/')}"

        if secret_reference not in self._vault_store:
            # Fallback to direct environment check if reference matches pattern
            if "google" in secret_reference.lower() and getattr(settings, "GEMINI_API_KEY", None):
                return settings.GEMINI_API_KEY
            if "nemotron" in secret_reference.lower() and getattr(settings, "NEMOTRON_API_KEY", None):
                return settings.NEMOTRON_API_KEY
            raise ValueError(f"Secret reference '{secret_reference}' not found in secret vault")

        encrypted = self._vault_store[secret_reference]
        return fernet.decrypt(encrypted).decode("utf-8")

    resolve_secret = resolve_credential


class SecretRedactor:
    """Automatic redaction of sensitive credentials from logs, payloads, and traces."""

    PATTERNS = [
        # Bearer tokens & JWTs
        (re.compile(r"Bearer\s+([a-zA-Z0-9_\-\.]{20,})", re.IGNORECASE), "Bearer [REDACTED_TOKEN]"),
        (re.compile(r"eyJ[a-zA-Z0-9_\-]{10,}\.eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}"), "[REDACTED_JWT]"),
        # OpenAI, Anthropic, Google keys
        (re.compile(r"sk-[a-zA-Z0-9]{20,T3BlbkFJ[a-zA-Z0-9]{20,}"), "[REDACTED_OPENAI_KEY]"),
        (re.compile(r"sk-ant-[a-zA-Z0-9_\-]{20,}"), "[REDACTED_ANTHROPIC_KEY]"),
        (re.compile(r"AIza[0-9A-Za-z-_]{35}"), "[REDACTED_GOOGLE_KEY]"),
        # Generic API keys, passwords, secrets
        (re.compile(r'(?i)(api[_-]?key|password|secret|token|private[_-]?key)\s*[:=]\s*["\']?([^"\'\s,;]{8,})["\']?'), r'\1="[REDACTED]"'),
        # Database connection strings
        (re.compile(r"://([^:@]+):([^@]+)@"), r"://\1:[REDACTED_PASSWORD]@"),
        # Private keys
        (re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+ PRIVATE KEY-----"), "[REDACTED_PRIVATE_KEY]"),
    ]

    @classmethod
    def redact(cls, text: str) -> str:
        """Apply all redaction rules to text."""
        if not text:
            return text
        sanitized = text
        for pattern, replacement in cls.PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)
        return sanitized

    redact_text = redact

    @classmethod
    def redact_dict(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Recursively redact dictionary fields."""
        sanitized = {}
        for k, v in data.items():
            if any(term in k.lower() for term in ["password", "secret", "token", "key", "cookie", "authorization"]):
                sanitized[k] = "[REDACTED_SECRET]"
            elif isinstance(v, dict):
                sanitized[k] = cls.redact_dict(v)
            elif isinstance(v, list):
                sanitized[k] = [cls.redact_dict(item) if isinstance(item, dict) else (cls.redact(str(item)) if isinstance(item, str) else item) for item in v]
            elif isinstance(v, str):
                sanitized[k] = cls.redact(v)
            else:
                sanitized[k] = v
        return sanitized


secret_manager = SecretManager()
secret_redactor = SecretRedactor()
