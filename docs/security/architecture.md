# Secure Identity, Model Gateway & Autonomous Mission Security Architecture

## 1. Overview & Trust Boundary

The Autonomous Repository Coding Agent implements a zero-trust, defense-in-depth architecture. 
The browser frontend, external clients, and local execution agents **NEVER receive raw provider API keys** (OpenAI, Anthropic, Google, Azure, vLLM). All model access is brokered through a centralized, policy-gated backend **Model Gateway**.

```
Browser / UI / Local Agent
         │
         │  Short-lived Access Token / HttpOnly Session Cookie (NEVER Provider Secrets)
         ▼
┌────────────────────────────────────────────────────────┐
│                      API Gateway                       │
│  - TLS Termination                                     │
│  - Token Validation & Signature Verification           │
│  - Rate Limiting & SSRF Prevention Filter              │
│  - Request ID / Trace ID Generation                    │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│             Authoritative AuthContext                  │
│  - User ID, Tenant ID, Roles, Scopes, Session State    │
│  - Cannot be forged by arbitrary client payloads       │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│           Centralized PolicyEngine (ABAC/RBAC)         │
│  - Precedence: DENY > ASK > ALLOW                      │
│  - Tenant Isolation Verification                       │
│  - Capability & Risk-Gated Evaluation                  │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                     MODEL GATEWAY                      │
│  - 18-Step Request Verification Pipeline               │
│  - Model Routing by Capability & Context Window        │
│  - Quota & Budget Verification                         │
│  - In-flight Secret Redaction                          │
└──────────────┬───────────────────────────┬─────────────┘
               │                           │
   Provider Reference (vault://...)        │ Decrypted In-Memory Only
               ▼                           ▼
┌───────────────────────────────┐ ┌──────────────────────────────────────┐
│  SecretManager (KMS Envelope) │ │ Provider Adapters (Backend Encrypted)│
│  - Encrypted At Rest          │ │ - Google Vertex / Gemini API         │
│  - Ephemeral Decryption Scope │ │ - OpenAI / Anthropic / Bedrock       │
│  - Key Versioning & Rotation  │ │ - Self-Hosted vLLM / Ollama / TGI    │
└───────────────────────────────┘ └──────────────────┬───────────────────┘
                                                     │
                                                     ▼
                                            AI Model Providers
```

---

## 2. Authentication Architecture

- **Password Hashing**: Uses modern **Argon2id** algorithm (`$argon2id$v=19$m=65536,t=3,p=4$`) via `argon2-cffi`. No custom crypto or plaintext passwords.
- **Short-Lived Access Tokens**: Signed HMAC-SHA256 JWTs with a 15-minute expiration (`exp`), containing authoritative claims: `sub`, `session_id`, `tenant_id`, `roles`, `scopes`, `iss`, `aud`, `iat`.
- **Rotating Refresh Tokens (RFC 6749 / RFC 9700)**: Single-use cryptographic tokens with family reuse detection. If a previously exchanged refresh token is presented, the entire token family is immediately revoked, and active sessions are terminated.
- **Session Lifecycle**: Server-side `UserSession` tracking with active status, IP address, user-agent metadata, and remote session revocation capabilities.
- **Cookie Security**: `HttpOnly`, `SameSite=Lax` (or `Strict`), and `Secure` cookies for browser-based session identification.

---

## 3. Authorization Architecture & Policy Engine

- **Authoritative Identity**: The backend derives an immutable `AuthContext` solely from validated tokens and database sessions. Client request bodies cannot set `roles` or `user_id`.
- **Precedence Hierarchy**: `DENY > ASK > ALLOW`. Security constraints at any layer immediately veto permissive lower layers.
- **Roles**:
  - `SUPER_ADMIN`: Full system administrative capabilities.
  - `ORG_ADMIN`: Organization management, provider configuration, quota administration.
  - `PROJECT_ADMIN`: Project settings and permissions.
  - `DEVELOPER`: Read/write repository, autonomous mission execution, terminal execution with approval gates.
  - `MEMBER`: General team access.
  - `VIEWER`: Read-only access to missions and repository diffs.
  - `AGENT`: Local execution agent identity bound to a registered device.
  - `SERVICE`: Service-to-service machine identity.
- **Granular Permissions**:
  - `project.read`, `project.write`
  - `repository.read`, `repository.write`
  - `mission.create`, `mission.execute`, `mission.stop`
  - `terminal.execute`
  - `database.read`, `database.write`, `database.migrate`
  - `model.list`, `model.use`, `model.use.premium`, `model.configure`
  - `secret.read`, `secret.rotate`
  - `agent.register`, `agent.execute`

---

## 4. Model Gateway & Provider Credential Management

- **Model Registry**: Database-driven catalog (`ModelProvider`, `RegisteredModel`, `ModelCredential`, `ModelQuota`, `ModelUsage`).
- **No Hard-coded Models**: Routing matches requested tasks with capabilities (`text`, `vision`, `tools`, `code`, `reasoning`) and context sizes.
- **Credential Storage**: Secrets are stored in `SecretManager` using KMS envelope encryption (Fernet derived from cryptographic master seeds and unique salts).
- **Vault References**: Database stores references such as `vault://models/google/default-key` rather than raw plaintext secrets.
- **Ephemeral Resolution**: Plaintext provider credentials exist in memory only during the immediate provider HTTP invocation and are never saved to disk, PostgreSQL, logs, or sent to the browser.
- **Secret Redaction**: Automated `SecretRedactor` scrubs Bearer tokens, JWTs, OpenAI/Anthropic/Google keys, passwords, connection strings, and private keys from all structured logs, events, and error messages.

---

## 5. Defense in Depth & Execution Protections

- **SSRF Filter**: `SSRFFilter` validates outbound URLs, resolves DNS, and strictly blocks loopback (`127.0.0.1`), link-local metadata (`169.254.169.254`), and RFC 1918 private IP subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`).
- **File Upload Safety**: Filename path-traversal sanitization (`os.path.basename`), 15MB file size limit, and cryptographic magic-byte verification (PNG, JPEG, WebP, GIF, BMP, SVG). Disguised executables and scripts are rejected before hitting storage.
- **Immutable Auditing**: `SecurityAuditService` records all critical events (`login.success`, `login.failed`, `token.rotated`, `session.revoked`, `agent.registered`, `model.generated`, `security.violation`) with structured metadata and actor attribution.
