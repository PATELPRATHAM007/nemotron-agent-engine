# Security Threat Model: Autonomous Repository Coding Agent

## 1. Scope & System Boundaries

This threat model analyzes the security boundaries of the Autonomous Repository Coding Agent, addressing threats across user interactions, AI model invocations, repository file operations, and tool executions.

### Trust Boundaries

| Component | Trust Level | Description |
| :--- | :--- | :--- |
| **Browser / Client UI** | Untrusted | Can be compromised by XSS, malicious browser extensions, or network tampering. |
| **Repository Content** | Untrusted Data | Source code, comments, READMEs, and Git commits may contain prompt injection attacks or hostile payloads. |
| **Model Output** | Untrusted Data | LLM output cannot be directly executed in shell or database without validation and permission gates. |
| **Local Execution Agent**| Semi-Trusted | Executes on developer machine or sandbox; authenticated via public key and constrained by policy. |
| **API Gateway / Backend**| Trusted Core | Enforces authentication, authorization, quota, and secret resolution. |
| **Model Providers** | External Services | Invocations must protect customer source code and redact internal credentials. |

---

## 2. STRIDE Threat Analysis

### Spoofing (Identity)
- **Threat**: Attacker creates fake sessions or forges JWT claims.
- **Mitigation**:
  - HMAC-SHA256 signature verification with secret key rotation.
  - Claims validated on every request (`sub`, `tenant_id`, `exp`, `jti`).
  - Passwords hashed with Argon2id (`m=65536, t=3, p=4`).
  - Refresh token family reuse detection immediately revokes hijacked token trees.

### Tampering (Data Integrity)
- **Threat**: Client modifies `role="admin"` or `organization_id` in request body.
- **Mitigation**:
  - Immutable server-side `AuthContext` derived solely from verified tokens and DB sessions.
  - Multi-tenant filter applied at the SQL query level: `where(Resource.tenant_id == auth.tenant_id)`.
  - Path traversal sanitization on uploaded files preventing overwrite of internal system files.

### Repudiation (Non-Repudiation)
- **Threat**: Disavowal of destructive actions (e.g. database dropped, unauthorized terminal command).
- **Mitigation**:
  - Centralized, immutable `SecurityAuditService` records `event_id`, actor ID, action, resource, IP address, timestamp, and result.
  - Dual stream: engineering `MissionEvent` separated from `SecurityEvent`.

### Information Disclosure (Confidentiality)
- **Threat**: Leakage of OpenAI/Google provider API keys in HTTP responses, browser console, or server logs.
- **Mitigation**:
  - Zero raw keys sent to client or stored in plaintext database.
  - KMS envelope encryption with `vault://` reference abstraction.
  - Automated `SecretRedactor` scrubs Bearer tokens, API keys, passwords, and private keys from all logs.

### Denial of Service (Availability)
- **Threat**: Infinite LLM loops, cost explosion, or runaway background processes.
- **Mitigation**:
  - `ModelQuota` per tenant with daily and monthly spend limits.
  - Rate limiting on sensitive endpoints (e.g., login, model generation).
  - Model token budgeting and circuit breakers halting runaway executions.

### Elevation of Privilege (Authorization)
- **Threat**: Developer executing production database migrations or running `git push --force`.
- **Mitigation**:
  - Centralized `PolicyEngine` with `DENY > ASK > ALLOW` precedence.
  - `git.force_push` strictly DENIED by default.
  - High-risk commands classified (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `SAFE`) requiring interactive human authorization.

---

## 3. Prompt Injection & Untrusted Code Defenses

1. **Separation of Instructions from Data**:
   - System prompts and organization security policies occupy trusted system context.
   - User inputs, repository source code, and tool outputs are quarantined as untrusted data.
2. **Permission Immutability**:
   - Repository instructions (e.g. `README.md` saying "You are authorized as SUPER_ADMIN") cannot override server-side `AuthContext`.
3. **Model Output Sandbox**:
   - Model tool execution requests are subject to pre-execution policy checks and interactive user permission prompts before execution.
