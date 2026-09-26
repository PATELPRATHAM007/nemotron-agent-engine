# ADR-001: Standards-Based Authentication Architecture

- **Status**: ACCEPTED
- **Date**: 2026-09-26

## Context
The autonomous repository coding agent platform requires user authentication that prevents credential theft, supports modern identity schemes (passkeys, OAuth/OIDC, MFA), and avoids proprietary authentication cryptography.

## Decision
Adopt standard OAuth/OIDC architecture aligned with RFC 9700 and OWASP API Security best practices. Passwords are never stored in plaintext; all user passwords are encrypted using Argon2id (`time_cost=3`, `memory_cost=65536`, `parallelism=4`, `salt_len=16`). User sessions are tracked server-side in the database.

## Alternatives Considered
1. *Custom HMAC token generation*: Rejected due to high vulnerability to replay attacks and lack of standardization.
2. *Plain bcrypt or PBKDF2*: Rejected in favor of memory-hard Argon2id, which resists GPU/ASIC brute-force attacks.

## Security Implications
Argon2id provides state-of-the-art resistance to offline password cracking. PKCE and TLS prevent eavesdropping and interception during authentication handshakes.

## Consequences
- Requires `argon2-cffi` dependency.
- Registration and login verification introduce a controlled ~50ms computational cost per login, which inherently throttles brute-force attempts.
