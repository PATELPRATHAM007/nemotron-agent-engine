"""
Auth Module Business Logic Service
==================================
Handles user authentication, Argon2id verification, short-lived JWT token issuance,
and rotating refresh token family reuse detection (RFC 6749 / 9700).
"""

from app.security.auth import (
    AuthenticationService,
    auth_service,
    password_hasher,
)

__all__ = [
    "AuthenticationService",
    "auth_service",
    "password_hasher",
]
