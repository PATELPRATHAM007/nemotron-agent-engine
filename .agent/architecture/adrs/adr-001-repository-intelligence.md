# ADR-001: Deterministic Repository Intelligence over Context Stuffing

**Status**: ACCEPTED  
**Date**: 2026-09-26  

## Context
Massive codebase context stuffing into LLMs causes severe hallucination, attention degradation, and wasteful token consumption.

## Decision
Adopt a deterministic Repository Intelligence engine around NVIDIA Nemotron 3 Ultra:
- Invariant AST fingerprinting
- Multi-layer directed knowledge graph
- Dynamic context budget manager strictly bounding prompts to <= 32k tokens
- 8-Gate verification battery and bounded auto-debugging

## Consequences
- 80%+ reduction in token consumption
- Zero syntax or import breakage
- Safe, bounded autonomous operations
