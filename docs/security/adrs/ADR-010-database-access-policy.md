# ADR-010: Database Access Policy & Environment-Aware Operations

- **Status**: ACCEPTED
- **Date**: 2026-09-26

## Context
The agent contains Database Intelligence capable of analyzing schemas, tables, relationships, indexes, execution plans, and running migrations. Unrestricted agent access to production databases introduces existential data loss risks.

## Decision
Enforce strict environment-aware database authorization policies:
1. **Role Separation**: Database connections are differentiated by role: `read-only`, `read-write`, `migration`, and `administrative`.
2. **Environment Gates**:
   - `development`: Read-write and migrations permitted under standard developer authorization.
   - `staging`: Controlled access; schema migrations require plan approval.
   - `production`: Strictly read-only by default. Destructive operations (e.g. `DROP TABLE`, `TRUNCATE`, bulk deletions, or schema migrations) require explicit human approval via interactive permission gates.
3. **Query Risk Analysis**: Before query dispatch, queries are parsed and checked for destructive statements (`DROP`, `ALTER`, `DELETE WITHOUT WHERE`). Destructive queries trigger `ASK` or `DENY` regardless of user role.

## Alternatives Considered
1. *Granting standard admin connection strings to the agent*: Rejected; catastrophic risk of data loss.
2. *Excluding database capabilities entirely*: Rejected; severely impairs autonomous debugging and schema migration capabilities.

## Security Implications
Guarantees that production databases are safeguarded against accidental drops or unauthorized schema modifications.

## Consequences
- Requires environment tags (`development`, `staging`, `production`) in database configuration.
- Destructive migration actions surface interactive approval prompts in the Autonomous Mission Chat.
