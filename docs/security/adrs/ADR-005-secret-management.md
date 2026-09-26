# ADR-005: KMS Envelope Encryption and Secret Redaction

- **Status**: ACCEPTED
- **Date**: 2026-09-26

## Context
Raw provider API keys, database credentials, and service tokens must not be stored in plaintext in PostgreSQL, committed to source control, or output in debug logs.

## Decision
Implement a dedicated `SecretManager` that stores secrets encrypted using KMS envelope encryption (AES-256 via Fernet derived from master cryptographic seeds and salts). The database stores reference identifiers (e.g. `vault://models/google/default-key`). Provider credentials are decrypted only into ephemeral local variables in memory during the outbound HTTP request. Furthermore, a centralized `SecretRedactor` automatically scrubs Bearer tokens, JWTs, OpenAI/Anthropic/Google keys, passwords, database URLs, and private keys from all logging outputs, exceptions, and event streams.

## Alternatives Considered
1. *Plaintext database columns with restricted access*: Rejected; vulnerable to SQL dump theft or accidental logging.
2. *Environment variables only*: Insufficient for dynamic multi-tenant provider keys and rotation.

## Security Implications
Even if database backups are leaked, raw provider credentials remain encrypted. Automated redaction prevents accidental credential leakage into observability platforms.

## Consequences
- Requires KMS or master encryption seed management.
- Dynamic key rotation is supported through versioned secret references without downtime.
