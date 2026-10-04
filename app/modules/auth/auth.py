"""
Auth service compatibility re-export.
"""
from app.modules.auth.service import (
    ACCESS_TOKEN_LIFETIME_SECONDS,
    JWT_AUDIENCE,
    JWT_ISSUER,
    JWT_SECRET_KEY,
    REFRESH_TOKEN_LIFETIME_DAYS,
    AuthenticationService,
    auth_service,
    password_hasher,
    utc_now,
)

__all__ = [
    "ACCESS_TOKEN_LIFETIME_SECONDS",
    "JWT_AUDIENCE",
    "JWT_ISSUER",
    "JWT_SECRET_KEY",
    "REFRESH_TOKEN_LIFETIME_DAYS",
    "AuthenticationService",
    "auth_service",
    "password_hasher",
    "utc_now",
]
