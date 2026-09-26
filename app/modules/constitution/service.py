"""
Agent Constitution & Repository Knowledge Scaffolder
===================================================
Automatically bootstraps the `.agent/` directory structure, standard constitutional rules,
initial Architecture Decision Records (ADRs), and institutional memory stores.
"""

import json
import os

from app.core.logging_config import get_logger

logger = get_logger(__name__)

CODING_STANDARDS_MD = """# Coding Standards & Quality Constitution

1. **Type Annotations**: All public functions and classes MUST have explicit PEP 484 type hints.
2. **Immutability & Pydantic**: Use Pydantic V2 models for structured request/response and configuration schemas.
3. **Docstrings**: Public methods and classes require Google-style docstrings with arguments, returns, and raises.
4. **Error Handling**: Raise explicit custom domain exceptions instead of bare `Exception`.
5. **No Hallucinated Imports**: Only import from dependencies declared in `requirements.txt` or repository packages.
"""

ARCHITECTURE_RULES_MD = """# Repository Architecture Rules

1. **Layer Separation**:
   - `app/intelligence/`: Repository understanding, AST, graph, impact, memory. MUST NOT import from `app/modules/*/routes.py`.
   - `app/modules/`: High-level business features and API presentation routes.
   - `app/core/`: Foundation services, logging, config, LLM gateway.
2. **Direction of Dependencies**:
   - Presentation (Routes) -> Business Services -> Domain Core -> Infrastructure.
3. **Task Scope Lock**:
   - Edits are strictly restricted to files registered in the active `TaskScope`.
"""

TESTING_RULES_MD = """# Testing Constitution

1. **Test Location**: All test files must reside under `tests/` with the prefix `test_*.py`.
2. **Async Testing**: Use `pytest-asyncio` for async endpoints and services.
3. **Isolation**: Use `tmp_path` fixture for filesystem tests. Never write temporary test artifacts to repo root.
4. **Zero Flakiness**: Tests must be deterministic and runnable in parallel.
"""

GIT_RULES_MD = """# Git & Version Control Protocol

1. **Commit Messages**: Follow Conventional Commits format: `<type>(<scope>): <short description>`.
2. **Autonomous Rollback**: If an agent fails verification after 3 debug attempts, all modifications MUST be reverted via `git checkout` or `git stash`.
3. **Atomic Changes**: Each mission should result in one cohesive, self-contained changeset.
"""

ADR_001_MD = """# ADR-001: Deterministic Repository Intelligence over Context Stuffing

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
"""


class ConstitutionScaffolder:
    """Scaffolds and validates repository .agent/ constitution files."""

    def __init__(self, workspace_root: str):
        self.workspace_root = os.path.abspath(workspace_root)
        self.agent_dir = os.path.join(self.workspace_root, ".agent")
        self.rules_dir = os.path.join(self.agent_dir, "rules")
        self.arch_dir = os.path.join(self.agent_dir, "architecture")
        self.adrs_dir = os.path.join(self.arch_dir, "adrs")
        self.features_dir = os.path.join(self.agent_dir, "features")
        self.memory_dir = os.path.join(self.agent_dir, "memory")

    def scaffold(self) -> dict[str, str]:
        """Creates directory hierarchy and populates initial constitutional files."""
        os.makedirs(self.rules_dir, exist_ok=True)
        os.makedirs(self.adrs_dir, exist_ok=True)
        os.makedirs(self.features_dir, exist_ok=True)
        os.makedirs(self.memory_dir, exist_ok=True)

        created_files = {}

        def write_if_missing(path: str, content: str):
            if not os.path.exists(path):
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content.strip() + "\n")
                created_files[os.path.basename(path)] = path

        write_if_missing(
            os.path.join(self.rules_dir, "coding_standards.md"), CODING_STANDARDS_MD
        )
        write_if_missing(
            os.path.join(self.rules_dir, "architecture_rules.md"), ARCHITECTURE_RULES_MD
        )
        write_if_missing(
            os.path.join(self.rules_dir, "testing_rules.md"), TESTING_RULES_MD
        )
        write_if_missing(os.path.join(self.rules_dir, "git_rules.md"), GIT_RULES_MD)
        write_if_missing(
            os.path.join(self.adrs_dir, "adr-001-repository-intelligence.md"),
            ADR_001_MD,
        )

        lessons_file = os.path.join(self.memory_dir, "historical_lessons.json")
        if not os.path.exists(lessons_file):
            with open(lessons_file, "w", encoding="utf-8") as f:
                json.dump([], f)
            created_files["historical_lessons.json"] = lessons_file

        logger.info(
            f"Constitution scaffolded. Files created: {list(created_files.keys())}"
        )
        return created_files

    def load_rule(self, rule_name: str) -> str:
        """Read rule content by name."""
        path = os.path.join(self.rules_dir, f"{rule_name}.md")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        return ""
