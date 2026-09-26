"""
Identity & Authentication Service
=================================
Implements:
  - Argon2id password hashing
  - Short-lived Access Tokens (HMAC-SHA256 JWTs) with cryptographic claims:
      sub, session_id, tenant_id, roles, scopes, iss, aud, iat, exp, jti
  - Rotating Refresh Tokens with family tracking and reuse detection (RFC 6749 / 9700)
  - Server-side User Session lifecycle management (create, validate, revoke)
"""

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import secrets
from typing import Any
import uuid

import argon2
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import select

from app.core.config import settings
from app.core.logging_config import get_logger
from app.db.session import DatabaseService
from app.security.models import RefreshToken, User, UserSession

logger = get_logger(__name__)

# Argon2id password hasher with NIST / OWASP recommended parameters
password_hasher = argon2.PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MB
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=argon2.Type.ID,
)

# Configuration defaults
ACCESS_TOKEN_LIFETIME_SECONDS = 900       # 15 minutes
REFRESH_TOKEN_LIFETIME_DAYS = 7          # 7 days
JWT_ISSUER = "nemotron-identity-service"
JWT_AUDIENCE = "nemotron-platform"
JWT_SECRET_KEY = getattr(settings, "JWT_SECRET_KEY", "nemotron-production-grade-secret-key-32b-min")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AuthenticationService:
    """Manages passwords, cryptographic tokens, sessions, and rotation."""

    # -------------------------------------------------------------------------
    # Password Hashing & Verification
    # -------------------------------------------------------------------------
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a plaintext password using Argon2id."""
        return password_hasher.hash(password)

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """Verify password against Argon2id hash with constant-time protection."""
        try:
            return password_hasher.verify(hashed_password, password)
        except VerifyMismatchError:
            return False
        except Exception:
            return False

    # -------------------------------------------------------------------------
    # Short-Lived Access Token (JWT)
    # -------------------------------------------------------------------------
    @staticmethod
    def create_access_token(
        user_id: str,
        session_id: str,
        tenant_id: str = "default-tenant",
        roles: list[str] | None = None,
        scopes: list[str] | None = None,
        lifetime_seconds: int = ACCESS_TOKEN_LIFETIME_SECONDS,
    ) -> str:
        """
        Generate short-lived signed access token containing standard claims.
        """
        now = int(utc_now().timestamp())
        exp = now + lifetime_seconds
        jti = str(uuid.uuid4())

        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": user_id,
            "session_id": session_id,
            "tenant_id": tenant_id,
            "roles": roles or ["DEVELOPER"],
            "scopes": scopes or ["model.use", "repository.read", "mission.create", "mission.execute"],
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
            "iat": now,
            "nbf": now,
            "exp": exp,
            "jti": jti,
        }

        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        unsigned_token = f"{header_b64}.{payload_b64}"

        signature = hmac.new(
            JWT_SECRET_KEY.encode(), unsigned_token.encode(), hashlib.sha256
        ).digest()
        sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")

        return f"{unsigned_token}.{sig_b64}"

    @staticmethod
    def verify_access_token(token: str) -> dict[str, Any]:
        """
        Validate signature, expiration, issuer, audience, and structure of access token.
        Raises ValueError on validation failure.
        """
        parts = token.strip().split(".")
        if len(parts) != 3:
            raise ValueError("Malformed access token structure")

        unsigned_token = f"{parts[0]}.{parts[1]}"
        expected_sig = hmac.new(
            JWT_SECRET_KEY.encode(), unsigned_token.encode(), hashlib.sha256
        ).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")

        if not hmac.compare_digest(parts[2], expected_sig_b64):
            raise ValueError("Invalid access token cryptographic signature")

        # Decode payload
        payload_b64 = parts[1]
        rem = len(payload_b64) % 4
        if rem:
            payload_b64 += "=" * (4 - rem)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode()).decode())

        now = int(utc_now().timestamp())
        if payload.get("exp", 0) < now:
            raise ValueError("Access token has expired")

        if payload.get("iss") != JWT_ISSUER:
            raise ValueError(f"Invalid token issuer: {payload.get('iss')}")

        if payload.get("aud") != JWT_AUDIENCE:
            raise ValueError(f"Invalid token audience: {payload.get('aud')}")

        return payload

    # -------------------------------------------------------------------------
    # Server-Side Session Management
    # -------------------------------------------------------------------------
    @classmethod
    def create_session(
        cls,
        user: User,
        device_info: str = "browser",
        ip_address: str = "127.0.0.1",
        user_agent: str = "",
    ) -> tuple[UserSession, str, str]:
        """
        Creates server-side session and issues access token + rotating refresh token.
        Returns: (session, access_token, raw_refresh_token)
        """
        session_id = str(uuid.uuid4())
        session_token = secrets.token_urlsafe(32)
        session_token_hash = hashlib.sha256(session_token.encode()).hexdigest()

        now = utc_now()
        expires_at = now + timedelta(days=REFRESH_TOKEN_LIFETIME_DAYS)

        # Issue rotating refresh token
        raw_refresh_token = secrets.token_urlsafe(48)
        refresh_hash = hashlib.sha256(raw_refresh_token.encode()).hexdigest()
        family_id = str(uuid.uuid4())

        with DatabaseService.get_session() as session:
            db_session = UserSession(
                id=session_id,
                user_id=user.id,
                session_token_hash=session_token_hash,
                device_info=device_info,
                ip_address=ip_address,
                user_agent=user_agent,
                is_active=True,
                expires_at=expires_at,
            )
            session.add(db_session)

            db_refresh = RefreshToken(
                id=str(uuid.uuid4()),
                session_id=session_id,
                user_id=user.id,
                token_hash=refresh_hash,
                family_id=family_id,
                is_revoked=False,
                expires_at=expires_at,
            )
            session.add(db_refresh)
            session.commit()
            session.refresh(db_session)

        # Issue access token
        access_token = cls.create_access_token(
            user_id=user.id,
            session_id=session_id,
            tenant_id=user.tenant_id,
            roles=user.roles or ["DEVELOPER"],
        )

        return db_session, access_token, raw_refresh_token

    @classmethod
    def rotate_refresh_token(cls, raw_refresh_token: str) -> tuple[str, str]:
        """
        Rotates refresh token. Implements family reuse detection (RFC 6749 / 9700):
        If an already revoked token is used, revokes all tokens in the family.
        Returns: (new_access_token, new_refresh_token)
        """
        token_hash = hashlib.sha256(raw_refresh_token.encode()).hexdigest()

        with DatabaseService.get_session() as session:
            stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
            rt = session.scalars(stmt).first()
            if not rt:
                raise ValueError("Invalid refresh token")

            if rt.is_revoked or rt.expires_at < utc_now():
                # Potential token reuse attack: revoke entire family
                logger.warning(
                    f"Refresh token reuse detected for family {rt.family_id}. Revoking family."
                )
                session.query(RefreshToken).filter(RefreshToken.family_id == rt.family_id).update(
                    {"is_revoked": True}
                )
                session.commit()
                raise ValueError("Refresh token reuse detected. Session terminated.")

            # Invalidate current refresh token
            rt.is_revoked = True

            # Verify session is active
            user_session = session.get(UserSession, rt.session_id)
            if not user_session or not user_session.is_active or user_session.expires_at < utc_now():
                raise ValueError("User session is inactive or expired")

            user = session.get(User, rt.user_id)
            if not user or not user.is_active:
                raise ValueError("User account is disabled")

            # Generate new rotating refresh token in same family
            new_raw_refresh = secrets.token_urlsafe(48)
            new_hash = hashlib.sha256(new_raw_refresh.encode()).hexdigest()
            new_expires = utc_now() + timedelta(days=REFRESH_TOKEN_LIFETIME_DAYS)

            new_rt = RefreshToken(
                id=str(uuid.uuid4()),
                session_id=user_session.id,
                user_id=user.id,
                token_hash=new_hash,
                family_id=rt.family_id,
                is_revoked=False,
                expires_at=new_expires,
            )
            session.add(new_rt)
            user_session.last_active_at = utc_now()
            session.commit()

            new_access_token = cls.create_access_token(
                user_id=user.id,
                session_id=user_session.id,
                tenant_id=user.tenant_id,
                roles=user.roles or ["DEVELOPER"],
            )

            return new_access_token, new_raw_refresh

    @classmethod
    def revoke_session(cls, session_id: str) -> bool:
        """Revoke a server-side session and all associated refresh tokens."""
        with DatabaseService.get_session() as session:
            user_session = session.get(UserSession, session_id)
            if user_session:
                user_session.is_active = False
                session.query(RefreshToken).filter(RefreshToken.session_id == session_id).update(
                    {"is_revoked": True}
                )
                session.commit()
                return True
        return False


auth_service = AuthenticationService()
