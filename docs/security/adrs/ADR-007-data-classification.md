# ADR-007: Repository Data Classification & Provider Boundaries

- **Status**: ACCEPTED
- **Date**: 2026-09-26

## Context
Repositories may contain proprietary algorithms, trade secrets, customer data, or confidential code. Sending confidential code to unapproved external public AI models violates privacy requirements and enterprise compliance.

## Decision
Establish four data classification levels:
1. `PUBLIC`: Open-source or public code; can be routed to standard external model providers.
2. `INTERNAL`: Internal company code; allowed only on approved external providers with zero data-retention agreements.
3. `CONFIDENTIAL`: Sensitive business logic; restricted to approved enterprise providers with explicit data boundaries.
4. `RESTRICTED`: Highly classified or regulated code; strictly confined to self-hosted models (vLLM / Ollama / TGI on private VPC infrastructure).

The Model Gateway checks repository data classification before routing. If Provider A fails, the router will never failover confidential code to an unapproved external provider.

## Alternatives Considered
1. *Unrestricted routing based purely on lowest cost/latency*: Rejected; risks exfiltration of confidential intellectual property.
2. *Blocking all external providers entirely*: Rejected; limits capabilities when processing non-sensitive code.

## Security Implications
Prevents unauthorized data transmission to third-party model providers.

## Consequences
- Repositories and projects must specify their classification tier.
- Router enforces data boundary constraints before selecting adapters.
