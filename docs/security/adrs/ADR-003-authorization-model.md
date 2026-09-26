# ADR-003: Multi-Level Authorization Model (RBAC + ABAC + DENY > ASK > ALLOW)

- **Status**: ACCEPTED
- **Date**: 2026-09-26

## Context
A developer may have access to Project A but not Project B. Simply possessing a role (e.g. `DEVELOPER`) is insufficient for fine-grained repository, terminal, database, and model operations. Object-level and function-level authorization is essential (OWASP API Top 10).

## Decision
Create a centralized `PolicyEngine` evaluating Subject (`AuthContext`), Action (e.g. `terminal.execute`, `repository.write`, `database.migrate`), Resource (Tenant, Project, Repository), and Context (environment, risk level). Authorization decisions follow strict precedence: `DENY > ASK > ALLOW`. Tenant isolation is enforced on every request; cross-tenant operations are strictly denied unless the caller is `SUPER_ADMIN`. High-risk actions require interactive human approval (`ASK`). Prohibited actions like `git.force_push` are always `DENY`.

## Alternatives Considered
1. *Scattered controller-level checks*: Rejected due to inconsistency and risk of omission.
2. *Pure RBAC without resource checks*: Rejected because roles do not prevent cross-tenant or cross-project data access.

## Security Implications
Prevents broken object-level authorization (BOLA) and broken function-level authorization (BFLA).

## Consequences
- Every sensitive endpoint must invoke `policy_engine.authorize(...)`.
- Clear authorization audit trail is generated for every decision.
