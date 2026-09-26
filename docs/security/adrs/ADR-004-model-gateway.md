# ADR-004: Centralized Model Gateway Architecture

- **Status**: ACCEPTED
- **Date**: 2026-09-26

## Context
If frontend clients or local agent scripts invoke AI providers directly, provider API keys (OpenAI, Anthropic, Google) must be distributed to clients, creating severe credential leakage risks.

## Decision
All model inference must pass through a centralized backend **Model Gateway** (`/api/v1/models/*`). The gateway executes an 18-step verification pipeline (Auth, Token, Tenant, Mission, Quotas, Rate Limiting, Redaction, Provider Credential Resolution, Streaming, Auditing). Clients only supply platform credentials; provider secrets are resolved ephemerally within the gateway and never exposed to the caller.

## Alternatives Considered
1. *Client-side direct provider API calls*: Rejected; completely violates the core security boundary.
2. *Reverse proxy (e.g. Nginx proxy_pass)*: Rejected; cannot perform semantic token accounting, fine-grained capability checks, or content redaction.

## Security Implications
Ensures zero provider key leakage to browsers or Git repositories. Centralizes compliance, data boundaries, and cost tracking.

## Consequences
- All model calls incur a tiny hop through the backend gateway.
- Streaming responses require SSE forwarding through the gateway.
