"""
Backward compatibility re-export. Real service lives in app.modules.auth.service.
"""
from app.modules.auth.service import (
    AuthenticationService,
    auth_service,
    password_hasher,
    utc_now,
    ACCESS_TOKEN_LIFETIME_SECONDS,
    REFRESH_TOKEN_LIFETIME_DAYS,
    JWT_ISSUER,
    JWT_AUDIENCE,
    JWT_SECRET_KEY,
)

__all__ = [
    "AuthenticationService",
    "auth_service",
    "password_hasher",
    "utc_now",
    "ACCESS_TOKEN_LIFETIME_SECONDS",
    "REFRESH_TOKEN_LIFETIME_DAYS",
    "JWT_ISSUER",
    "JWT_AUDIENCE",
    "JWT_SECRET_KEY",
]
