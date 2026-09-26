# ADR-006: Local Execution Agent Independent Identity & Authentication

- **Status**: ACCEPTED
- **Date**: 2026-09-26

## Context
When executing terminal commands, filesystem operations, and Git workflows on local machines, the local execution agent must authenticate independently from human users. Local agents must never receive human passwords or master provider keys.

## Decision
Create distinct `Agent` entities in the database (`security_agents`). Agents register their device ID, project binding, public key, and declared execution capabilities (`terminal`, `filesystem`, `git`, `browser`, `docker`). The server issues short-lived agent session tokens. Two-level security is enforced: cloud policy decides what the user permits; the local agent sandbox enforces directory and command boundaries locally.

## Alternatives Considered
1. *Sharing user credentials with the local daemon*: Rejected; violates principle of least privilege and prevents distinguishing automated actions from user actions.
2. *Unauthenticated local agent daemon*: Rejected; any process on the machine could impersonate the agent.

## Security Implications
Sender-constrained public-key authentication ensures local agent sessions cannot be hijacked or used to access other tenants or projects.

## Consequences
- Requires agent enrollment endpoint `/api/v1/auth/agents/register`.
- Audit logs clearly attribute actions to the specific agent and device.
