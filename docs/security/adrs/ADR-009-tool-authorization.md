# ADR-009: Tool Authorization & Risk Classification Matrix

- **Status**: ACCEPTED
- **Date**: 2026-09-26

## Context
Autonomous agents have access to terminal commands, file systems, Git repositories, and web search. Blindly executing LLM-generated shell commands can lead to unintended data loss or system compromise.

## Decision
Implement a centralized tool authorization policy with granular risk classifications:
1. `SAFE`: Read-only queries, status checks (`git status`, `git diff`, `ls`, `pytest`). Auto-executed under developer policy.
2. `LOW`: File modifications within project boundary with automated git checkpoints.
3. `MEDIUM`: Package installations (`pip install`, `npm install`), test harness execution.
4. `HIGH`: Git branch modifications, database schema adjustments, network operations. Requires interactive human confirmation in Autonomous Mission Chat.
5. `CRITICAL`: System root commands (`sudo`), file deletions outside workspace (`rm -rf /`), `git push --force`, database drop. Strictly DENIED or requiring dual authorization.

Users can choose approval scopes: `Allow Once`, `Allow for Mission`, `Allow for Project`, or `Deny`.

## Alternatives Considered
1. *Unrestricted autonomous terminal execution*: Rejected; intolerable risk for production and developer machines.
2. *Prompting user on every single read operation*: Rejected; creates alert fatigue and makes agent unusable.

## Security Implications
Ensures safe autonomy while keeping human engineers firmly in the loop for risky side effects.

## Consequences
- The Autonomous Mission Chat UI renders interactive permission cards for HIGH risk actions.
- Decisions are persisted to `mission_permissions`.
