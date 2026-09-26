"""
Auth Module Input Validation & Checksums
========================================
Dedicated validation rules, password entropy checks, and checksum logic.
"""

import hashlib
import re

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class AuthValidator:
    """Provides input validation, format checks, and payload checksums."""

    @staticmethod
    def validate_email(email: str) -> str:
        clean = (email or "").strip().lower()
        if not clean or not EMAIL_REGEX.match(clean):
            raise ValueError("Invalid email address format")
        return clean

    @staticmethod
    def validate_password_strength(password: str) -> str:
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
            raise ValueError("Password must contain at least one letter and one number")
        return password

    @staticmethod
    def compute_device_fingerprint(device_id: str, public_key: str) -> str:
        """Compute SHA256 checksum binding device ID and public key."""
        payload = f"{device_id}:{public_key}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @staticmethod
    def verify_agent_checksum(device_id: str, public_key: str, expected_checksum: str) -> bool:
        computed = AuthValidator.compute_device_fingerprint(device_id, public_key)
        return computed == expected_checksum
