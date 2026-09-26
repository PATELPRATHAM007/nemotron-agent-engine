# ADR-002: Token Strategy & Refresh Token Family Rotation

- **Status**: ACCEPTED
- **Date**: 2026-09-26

## Context
Long-lived JWT tokens stored in browser `localStorage` expose applications to token theft via XSS. Long-lived access tokens cannot be easily revoked without distributed blocklists.

## Decision
Implement short-lived access tokens (15 minutes) paired with rotating refresh tokens and server-side session tracking (RFC 6749 / RFC 9700). Refresh tokens are single-use; each refresh request invalidates the old refresh token and issues a new one. If an already consumed refresh token is presented, family reuse detection triggers, instantly revoking the entire token family and terminating the associated user session. For browser clients, refresh tokens are stored in `HttpOnly`, `SameSite=Lax`, `Secure` cookies.

## Alternatives Considered
1. *Long-lived JWTs (24h - 30d)*: Rejected due to inability to revoke compromised tokens promptly.
2. *Stateful database session lookup on every API call*: Rejected due to high database load on high-frequency streaming turns. Short-lived JWTs balance performance and security.

## Security Implications
Reduces exposure window to at most 15 minutes if an access token is leaked. Automatic token family revocation neutralizes token replay attacks.

## Consequences
- Requires frontend clients to handle periodic token refresh or transparent cookie forwarding.
- Database must maintain the `security_refresh_tokens` table.
