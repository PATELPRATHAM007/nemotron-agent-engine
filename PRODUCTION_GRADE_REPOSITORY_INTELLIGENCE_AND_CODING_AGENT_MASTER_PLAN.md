# Production-Grade Technical Master Plan
## NVIDIA Nemotron 3 Ultra Autonomous Repository Intelligence & Coding Agent Engine

> **Version**: 2.0.0 (Production Release Architecture)  
> **Target Reasoning Brain**: NVIDIA Nemotron 3 Ultra (550B LatentMoE, 1.12 TB Sharded Weights)  
> **Status**: Comprehensive Master Plan — Architecture, Subsystems, Gap Analysis & Implementation Roadmap  
> **Core Principle**: *Deterministic engines for deterministic facts; Nemotron for frontier reasoning, planning, code synthesis, and diagnosis.*

---

## Table of Contents
1. [Executive Summary & Core Architectural Principle](#1-executive-summary--core-architectural-principle)
2. [Current Implementation Audit (Verified Components)](#2-current-implementation-audit-verified-components)
3. [Gap Analysis: Subsystems to be Implemented](#3-gap-analysis-subsystems-to-be-implemented)
4. [29 Required Areas Mapping & System Architecture](#4-29-required-areas-mapping--system-architecture)
5. [Subsystem 1: Database Intelligence, Performance & Safety](#5-subsystem-1-database-intelligence-performance--safety)
6. [Subsystem 2: 7-Level Permission Architecture & Human Approval Gates](#6-subsystem-2-7-level-permission-architecture--human-approval-gates)
7. [Subsystem 3: Modular Skills System vs. Repository Memory](#7-subsystem-3-modular-skills-system-vs-repository-memory)
8. [Subsystem 4: Multi-Stage Planning (Phases A–H) & 6-Review Loop Engine](#8-subsystem-4-multi-stage-planning-phases-ah--6-review-loop-engine)
9. [Subsystem 5: Source-of-Truth Hierarchy & Knowledge Consistency](#9-subsystem-5-source-of-truth-hierarchy--knowledge-consistency)
10. [Subsystem 6: Observability, Metrics & Audit Trails](#10-subsystem-6-observability-metrics--audit-trails)
11. [Step-by-Step Implementation Roadmap for Remaining Subsystems](#11-step-by-step-implementation-roadmap-for-remaining-subsystems)
12. [Verification, Testing & Rollback Strategy](#12-verification-testing--rollback-strategy)

---

## 1. Executive Summary & Core Architectural Principle

Large Language Models should never be treated as lossy database storage for raw source code. Storing an entire repository into model context (200k+ tokens) causes severe attention degradation, hallucinations, catastrophic context rot, and prohibitive latency.

This system establishes a **deterministic repository intelligence harness** around **NVIDIA Nemotron 3 Ultra**:

```
Deterministic Tooling (AST, Graph, DB Introspection, Git, Linters, Test Runners)
                                    │
                                    ▼
       High-Signal, Compact Structural Context (Strictly <= 32k Tokens)
                                    │
                                    ▼
       NVIDIA Nemotron 3 Ultra (Reasoning, Planning, Coding, Debugging)
                                    │
                                    ▼
8-Gate Verification Battery & Guardrails (Syntax, Imports, Types, Scope, Tests, DB Safety)
                                    │
                                    ▼
               Autonomous Healing or Automatic Rollback
```

### Deterministic Separation of Concerns
| Responsibility | Engine / Component | Guarantee |
| :--- | :--- | :--- |
| **AST & Symbol Extraction** | `PythonAstParser` / Tree-Sitter | 100% deterministic parse, syntax error capture |
| **Code Invariance Hashing** | `CodeFingerprint` (`ast_hash`) | Invariant to whitespace, comments, and line offsets |
| **Relationship Tracking** | `RepoGraph` & `FeatureMapper` | Multi-layer directed graph with cycle-safe traversal |
| **Blast Radius & Scope Lock** | `ImpactAnalyzer` & `TaskScope` | Zero unintended edits outside authorized task boundaries |
| **Context Assembly** | `ContextBudgetManager` | Strictly bounds prompt payload to $\le 32\text{k}$ tokens |
| **Database Truth** | `DatabaseIntrospectionEngine` | Real schema reflection, live index & foreign key discovery |
| **Database Safety** | `DatabaseSafetyGuard` | Hard blocks `DROP`, `TRUNCATE`, `ALTER`, `DELETE` (Read-Only default) |
| **Permissions** | `PermissionManager` | 7-Level permission model with interactive human approval gates |
| **Verification & Quality** | `VerificationPipeline` | 8-gate fail-fast battery before committing code |
| **Autonomous Healing** | `BoundedAutoDebugger` | Max 3 attempts, automatic Git rollback on persistent failure |
| **Reasoning & Synthesis** | **NVIDIA Nemotron 3 Ultra** | Plan formulation, architectural review, surgical coding, debugging |

---

## 2. Current Implementation Audit (Verified Components)

The codebase currently contains **57 fully passing unit and integration tests** verifying the core repository intelligence and agent orchestration foundation:

```bash
$ .venv/bin/pytest -v
============================== 57 passed in 1.90s ==============================
```

### Verified & Passing Modules:
1. **Phase 1: Deterministic AST & Code Fingerprinting**:
   - `app/intelligence/indexing/fingerprint.py`: File hash, invariant AST hash, and symbol hash.
   - `app/intelligence/indexing/ast_parser.py`: Classes, functions, signatures, routes, calls, imports.
   - `app/intelligence/indexing/import_resolver.py`: Relative/absolute resolution; internal vs external packages.
   - `app/intelligence/indexing/symbol_extractor.py`: Incremental $O(1)$ Symbol Catalog.
   - Tests: `test_ast_parser.py`, `test_fingerprint.py`, `test_import_resolver.py`.
2. **Phase 2: Multi-Layer Knowledge Graph & Feature Mapping**:
   - `app/intelligence/graph/schema.py`: 8 node layers (`REPOSITORY`, `MODULE`, `FILE`, `SYMBOL`, `FEATURE`, `TEST`, `ADR`, `BUG`) and 11 edge kinds.
   - `app/intelligence/graph/repo_graph.py`: Directed graph with cycle-safe BFS/DFS and subgraph extraction.
   - `app/intelligence/graph/feature_mapper.py`: Automatic feature discovery.
   - `app/intelligence/graph/graph_storage.py`: Atomic JSON persistence to `.agent/graph/`.
   - Tests: `test_repo_graph.py`.
3. **Phase 3: Change Impact Analysis & Task Scope Lock**:
   - `app/intelligence/impact/call_graph.py`: Forward and reverse caller/callee trees.
   - `app/intelligence/impact/impact_analyzer.py`: Direct/indirect blast radius, affected routes and tests.
   - `app/intelligence/impact/scope_lock.py`: `TaskScope` with `ScopeViolationError` blocking unauthorized file writes.
   - Tests: `test_impact_scope.py`.
4. **Phase 4: Context Budget Manager & Progressive Expansion**:
   - `app/intelligence/context/budget_manager.py`: Dynamic token allocation strictly enforcing $\le 32\text{k}$ tokens.
   - `app/intelligence/context/hierarchical.py`: 4-tier progressive expander (Module $\rightarrow$ Feature $\rightarrow$ Signatures $\rightarrow$ Source).
   - `app/intelligence/context/ranker.py`: Hybrid ranker ($0.4 \times \text{Proximity} + 0.3 \times \text{Symbol} + 0.2 \times \text{Semantic} + 0.1 \times \text{Lexical}$).
   - Tests: `test_context_budget.py`.
5. **Phase 5: Multi-Role Agent Orchestrator**:
   - `app/modules/agent/roles/`: `PlannerRole`, `ReviewerRole`, `CoderRole`, `TesterRole`, `DebuggerRole`.
   - `app/modules/agent/orchestrator.py`: Finite state machine (`IDLE` $\rightarrow$ `PLANNING` $\rightarrow$ `REVIEWING` $\rightarrow$ `CODING` $\rightarrow$ `TESTING` $\rightarrow$ `DEBUGGING` $\rightarrow$ `COMMITTING` $\rightarrow$ `COMPLETED`).
   - Tests: `test_orchestrator_roles.py`.
6. **Phase 6: 8-Gate Verification Battery & Auto-Debugger**:
   - `app/modules/agent/verification/gates.py`: 8-Gate fail-fast pipeline (AST, Imports, Types, Architecture, Scope, Unit Tests, Regression, Linter).
   - `app/modules/agent/verification/auto_debugger.py`: Bounded auto-debugger (max 3 attempts, auto-rollback).
   - Tests: `test_verification_gates.py`.
7. **Phase 7: Persistent Memory, ADRs & Constitution**:
   - `app/constitution/scaffold.py`: Bootstraps `.agent/` (`rules/`, `architecture/`, `adrs/`, `memory/`).
   - `app/intelligence/memory/adr_manager.py`: Markdown ADR reader/writer.
   - `app/intelligence/memory/memory_store.py`: Historical lessons store with adaptive confidence scoring (+0.1 reinforcement on success, -0.2 penalty on failure).
   - Tests: `test_memory_system.py`.
8. **Phase 8: Incremental File Watcher & E2E Mission**:
   - `app/intelligence/indexing/watcher.py`: $O(\Delta)$ incremental watcher.
   - `tests/test_e2e_agent_mission.py`: Full autonomous mission test covering all 8 phases.

---

## 3. Gap Analysis: Subsystems to be Implemented

To fulfill 100% of the expanded prompt requirements, the following components must be built and integrated:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       REMAINING GAPS TO IMPLEMENT                                      │
├────────────────────────────────┬───────────────────────────────────────────────────────────────────────┤
│ Subsystem                      │ Scope & Components to Build                                           │
├────────────────────────────────┼───────────────────────────────────────────────────────────────────────┤
│ 1. Database Intelligence &     │ - Database Introspection (PostgreSQL, MySQL, SQLite, MongoDB, Redis,  │
│    Safety Engine               │   pgvector/vector databases, Neo4j graph)                             │
│                                │ - Database Knowledge Graph (Feature -> API -> Service -> Repo ->      │
│                                │   Query -> Table/Collection -> Index)                                 │
│                                │ - Query & ORM Analyzer (N+1, SELECT *, full scans, non-sargable,      │
│                                │   large dataset offset pagination, lock contention)                   │
│                                │ - Explain Plan Intelligence (EXPLAIN, EXPLAIN ANALYZE parser & advice)│
│                                │ - Large Dataset Optimization (covering indexes, keyset pagination)    │
│                                │ - Database Safety Guard: Default READ-ONLY, hard blocks DDL/mutations │
│                                │ - Database Performance Baseline Collector                             │
├────────────────────────────────┼───────────────────────────────────────────────────────────────────────┤
│ 2. 7-Level Permission Model    │ - Level 0: Read Only, Level 1: Analyze, Level 2: Modify Source,       │
│    & Human Approval Gates      │   Level 3: Run Tests, Level 4: Git Ops, Level 5: DB Mutation,         │
│                                │   Level 6: Deployment (disabled by default)                           │
│                                │ - Interactive Human Approval Gate Engine (token, timeout, audit trail)│
├────────────────────────────────┼───────────────────────────────────────────────────────────────────────┤
│ 3. Modular Skills Engine       │ - Separation: Reusable skills in `skills/` vs Project Memory in       │
│                                │   `.agent/memory/`                                                    │
│                                │ - Modular Skill Loaders (`skills/database/*`, `skills/fastapi/`,      │
│                                │   `skills/architecture/`, `skills/python/`, `skills/testing/`, etc.)  │
│                                │ - On-demand Context Injection                                         │
├────────────────────────────────┼───────────────────────────────────────────────────────────────────────┤
│ 4. Multi-Stage Planning        │ - 8-Phase Planning Pipeline (Phases A through H: Discovery, Retrieval,│
│    & 6-Review Loop Engine      │   Architecture, Impact, Database, Implementation, Test, Risk)         │
│                                │ - Automated 6 Review Loops (Architecture, Correctness, Security,      │
│                                │   Performance, Maintainability, Best Practices)                       │
│                                │ - Plan Contract Finalizer & Verification                              │
└────────────────────────────────┴───────────────────────────────────────────────────────────────────────┘
```

---

## 4. 29 Required Areas Mapping & System Architecture

| # | Required Area | Subsystem / Component | Implementation Strategy |
| :--- | :--- | :--- | :--- |
| **1** | Repository discovery | `app/intelligence/indexing/ast_parser.py` | Directory walker, file type classification, ignore lists |
| **2** | Repository indexing | `app/intelligence/indexing/symbol_extractor.py` | Incremental catalog, file/AST hash cache |
| **3** | AST & symbol analysis | `app/intelligence/indexing/ast_parser.py` | Python AST visitor, classes, methods, routes, calls |
| **4** | Dependency analysis | `app/intelligence/indexing/import_resolver.py` | Absolute & relative resolver, internal vs third-party |
| **5** | Feature discovery | `app/intelligence/graph/feature_mapper.py` | Route-to-service clustering, boundary detection |
| **6** | Feature knowledge graphs| `app/intelligence/graph/repo_graph.py` | 8 node layers, 11 edge kinds, feature subgraph extraction |
| **7** | Repository memory | `app/intelligence/memory/memory_store.py` | Persistent lessons with adaptive confidence scoring |
| **8** | Hybrid retrieval | `app/intelligence/context/ranker.py` | Proximity + exact symbol + semantic + lexical ranker |
| **9** | Context engineering | `app/intelligence/context/budget_manager.py` | Strict $\le 32\text{k}$ ceiling, 4-tier progressive hierarchy |
| **10**| Coding-style discovery | `.agent/rules/coding_standards.md` | Conventional pattern detection vs legacy tech debt |
| **11**| Project rules & skills | `app/constitution/scaffold.py` & `skills/` | General skills (`skills/`) vs repo memory (`.agent/`) |
| **12**| Task analysis | `app/modules/agent/roles/planner.py` | Goal $\rightarrow$ Feature $\rightarrow$ Files $\rightarrow$ Scope Lock |
| **13**| Impact analysis | `app/intelligence/impact/impact_analyzer.py` | Direct & transitive blast radius, affected routes/tests |
| **14**| Implementation planning| `app/modules/agent/planning/multi_stage.py` | 8-phase planning pipeline (Phases A–H) |
| **15**| Plan review | `app/modules/agent/planning/review_loops.py`| 6 review loops (Arch, Correct, Sec, Perf, Maint, Best Pract) |
| **16**| Code implementation | `app/modules/agent/roles/coder.py` | Surgical edits strictly within `TaskScope` |
| **17**| Automatic debugging | `app/modules/agent/verification/auto_debugger.py`| Bounded root-cause diagnosis, max 3 attempts, auto-rollback |
| **18**| Test generation/exec | `app/modules/agent/roles/tester.py` | Pytest automation, boundary value and regression asserts |
| **19**| Static analysis | `app/modules/agent/verification/gates.py` | Gate 8: Ruff check with zero critical syntax/lint breaks |
| **20**| Build verification | `app/modules/agent/verification/gates.py` | Compilation and import graph sanity checks |
| **21**| Regression verification| `app/modules/agent/verification/gates.py` | Gate 7: Regression test suite on affected features |
| **22**| Git/diff verification | `app/modules/agent/verification/gates.py` | Git diff audit preventing accidental modifications |
| **23**| Database intelligence | `app/intelligence/database/schema_introspect.py`| Schema, tables, columns, indexes, foreign keys, ORM |
| **24**| DB performance analysis| `app/intelligence/database/query_analyzer.py`| N+1, full table scan, EXPLAIN plan, covering index, pagination|
| **25**| Security & permissions | `app/core/permissions.py` | 7-Level permissions, default read-only, credential safety |
| **26**| Incremental learning | `app/intelligence/indexing/watcher.py` | $O(\Delta)$ invalidation on AST change, whitespace invariant |
| **27**| Observability | `app/core/logging_config.py` & telemetry | Structured JSON logs, latency, token usage, audit trails |
| **28**| Failure recovery | `app/modules/agent/verification/auto_debugger.py`| Automatic Git checkout / stash rollback |
| **29**| Human approval gates | `app/core/permissions.py` | Mandatory approval token for DB mutations & deployment |

---

## 5. Subsystem 1: Database Intelligence, Performance & Safety

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                     DATABASE INTELLIGENCE SUBSYSTEM                                            │
├────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. Schema Introspection Engine (`app/intelligence/database/schema_introspect.py`)                             │
│    - Relational: PostgreSQL, MySQL, SQLite (via SQLAlchemy MetaData, reflection, foreign keys, indexes)        │
│    - NoSQL: MongoDB (collections, validators, indexes), Redis (keyspace patterns, TTLs)                       │
│    - Vector DBs: pgvector, Qdrant, Milvus (distance metrics, dimensions, HNSW/IVFFlat indexes)                 │
│    - Graph DBs: Neo4j (labels, relationships, constraints)                                                     │
├────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. Database Knowledge Graph Connector (`app/intelligence/database/graph_connector.py`)                        │
│    - Node Kinds: TABLE, COLUMN, INDEX, CONSTRAINT, ORM_MODEL, QUERY, REPOSITORY                             │
│    - Traversal: Feature -> API Route -> Service -> Repository -> Query -> Table/Collection -> Index           │
├────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. Query & ORM Analyzer (`app/intelligence/database/query_analyzer.py`)                                       │
│    - Static AST detection of N+1 loops (lazy relationship traversal inside for loops)                          │
│    - Detection of `SELECT *`, unindexed `WHERE` columns, non-sargable functions (`WHERE UPPER(name) = ...`)    │
│    - Pagination Pitfall Detector: Flags `OFFSET 100000` on large tables, recommends keyset/cursor pagination  │
│    - Lock Contention Warning: Long-running transactions or unbounded bulk updates                              │
├────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. Explain Plan Intelligence (`app/intelligence/database/explain_engine.py`)                                  │
│    - Read-only execution of `EXPLAIN (FORMAT JSON)` or `EXPLAIN ANALYZE` on sandboxes                          │
│    - Parsing execution tree: Sequential Scans vs. Index Scans, Hash Joins vs Nested Loops, Spills to disk      │
│    - Automated recommendation of covering indexes and predicate rewrites                                      │
├────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 5. Database Safety Guardrail (`app/intelligence/database/safety_guard.py`)                                    │
│    - Default Connection Mode: READ-ONLY (enforced at connection pool level)                                    │
│    - Hard Command Blocker: Rejects `DROP`, `TRUNCATE`, `ALTER`, `GRANT`, `REVOKE`, `DELETE/UPDATE` without    │
│      explicit WHERE clause                                                                                     │
│    - Level 5 Gate Requirement: Schema changes and migrations require an interactive human approval token      │
├────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 6. Performance Baseline & Observability (`app/intelligence/database/performance_baseline.py`)                 │
│    - Records query latency, rows examined vs rows returned ratio, slow query counts                            │
│    - Stores verified performance knowledge in `.agent/memory/`, NEVER raw production user data                │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Subsystem 2: 7-Level Permission Architecture & Human Approval Gates

The agent operates under explicit permission bounds. High-risk operations cannot execute automatically.

```
 LEVEL 0: READ ONLY
   - Inspect files, read code, view ASTs, query graph, read logs
   - Zero side-effects allowed
   
 LEVEL 1: ANALYZE
   - Run static analysis, AST linting, read-only EXPLAIN query plans
   - Run read-only introspection
   
 LEVEL 2: MODIFY SOURCE (Scope-Locked)
   - Edit authorized files in TaskScope
   - Strictly prohibited from touching unauthorized files
   
 LEVEL 3: RUN TESTS & BUILD
   - Execute pytest, ruff check, mypy, build scripts in sandbox
   
 LEVEL 4: GIT OPERATIONS
   - Create local branches, stage diffs, make conventional commits, rollback via git checkout/stash
   - Cannot push to remote master/main without human gate
   
 LEVEL 5: DATABASE MUTATION / MIGRATIONS ──► [HUMAN APPROVAL GATE REQUIRED]
   - Creating or executing Alembic / SQL migrations
   - Executing INSERT / UPDATE / DELETE on development/staging databases
   - Hard blocked until human submits authorization token
   
 LEVEL 6: DEPLOYMENT ─────────────────────────► [HUMAN APPROVAL GATE REQUIRED]
   - Triggering production releases or CI/CD deployments
   - Disabled by default; requires signed human confirmation
```

---

## 7. Subsystem 3: Modular Skills System vs. Repository Memory

A critical architectural distinction is enforced between **General Reusable Skills** and **Project-Specific Memory**:

```
skills/ (General, Reusable Across Projects)
 ├── database/
 │    ├── database-discovery/
 │    ├── schema-analysis/
 │    ├── sql-analysis/
 │    ├── nosql-analysis/
 │    ├── vector-database/
 │    ├── orm-analysis/
 │    ├── query-optimization/
 │    ├── index-analysis/
 │    ├── transaction-analysis/
 │    ├── migration-analysis/
 │    ├── explain-plan-analysis/
 │    ├── large-dataset-performance/
 │    ├── caching/
 │    └── database-safety/
 ├── architecture/
 ├── python/
 ├── fastapi/
 ├── testing/
 ├── debugging/
 ├── security/
 ├── git/
 ├── docker/
 └── kubernetes/

.agent/ (Project-Specific, Verified Institutional Knowledge)
 ├── rules/
 │    ├── coding_standards.md
 │    ├── architecture_rules.md
 │    ├── testing_rules.md
 │    └── git_rules.md
 ├── architecture/
 │    └── adrs/ (ADR-001, ADR-002, ...)
 ├── memory/
 │    ├── historical_lessons.json (learned bug fixes, gotchas, confidence scores)
 │    └── performance_baselines.json
 └── graph/
      ├── nodes.json
      └── edges.json
```

---

## 8. Subsystem 4: Multi-Stage Planning (Phases A–H) & 6-Review Loop Engine

Before modifying code, the agent executes an 8-phase planning pipeline followed by 6 targeted review loops:

### 8-Phase Planning Pipeline (Phases A through H)
1. **Phase A — Discovery**: Ingest user goal, scan repository graph, identify matching features.
2. **Phase B — Retrieval**: Hybrid retrieval (symbols, AST, graph neighbors, relevant ADRs, matching lessons).
3. **Phase C — Architecture**: Determine design pattern, layer boundaries, dependency inversion.
4. **Phase D — Impact Analysis**: Calculate blast radius, two-way call trees, affected routes, and impacted tests.
5. **Phase E — Database Analysis**: Identify affected tables, ORM entities, queries, indexes, and migration requirements.
6. **Phase F — Implementation Plan**: Formulate atomic, sequentially ordered steps with explicit target files.
7. **Phase G — Test Plan**: Define unit, integration, and regression test cases *before* writing code.
8. **Phase H — Risk Plan**: Define failure modes, boundary limits, and rollback strategy.

### The 6 Independent Review Loops
The generated plan is evaluated through 6 distinct analytical lenses:
- **Review 1: Architecture**: Component boundaries, layering, dependency direction.
- **Review 2: Correctness**: Edge cases, nullability, exceptions, concurrency.
- **Review 3: Security**: Auth, permissions, SQL injection, secrets, DB safety.
- **Review 4: Performance**: Token budget, algorithmic complexity, DB query plans.
- **Review 5: Maintainability**: Code clarity, idiomatic style, testability, docstrings.
- **Review 6: Best Practices**: Technology fit, maturity vs hype, operational overhead.

---

## 9. Subsystem 5: Source-of-Truth Hierarchy & Knowledge Consistency

```
1. Actual Current Source Code & ASTs (Absolute Truth)
                    ↓
2. Test Suite Executions & Assertions (Behavioral Truth)
                    ↓
3. Live Database Schema Introspection & Reflection (Data Truth)
                    ↓
4. Explicit Project Rules & Accepted ADRs (Intentional Truth)
                    ↓
5. Verified Repository Memory & Lessons (Historical Truth)
                    ↓
6. Generated Summaries (Heuristic Truth)
                    ↓
7. Model Speculation / Hallucination (Zero Authority - Rejected)
```

---

## 10. Subsystem 6: Observability, Metrics & Audit Trails

The engine emits real-time structured telemetry:
- **Token Telemetry**: Tokens allocated vs consumed per role.
- **Latency Tracking**: Time spent in AST parsing, graph traversal, retrieval, LLM streaming, test execution.
- **Verification Metrics**: Status and execution time of each of the 8 validation gates.
- **Auto-Debug Tracker**: Exact failure traces, diagnosis hypotheses, patches applied, attempt count (1/3, 2/3, 3/3).
- **Audit Log**: Immutable append-only log in `.agent/memory/audit_log.jsonl`.

---

## 11. Step-by-Step Implementation Roadmap for Remaining Subsystems

### Milestone 1: Database Intelligence & Safety Engine
- [ ] Create `app/intelligence/database/schema_introspect.py` (SQLAlchemy reflection + Mongo/Redis metadata).
- [ ] Create `app/intelligence/database/graph_connector.py` (map tables/indexes into `RepoGraph`).
- [ ] Create `app/intelligence/database/query_analyzer.py` (N+1, `SELECT *`, non-sargable, keyset pagination).
- [ ] Create `app/intelligence/database/explain_engine.py` (EXPLAIN JSON parser, recommendations).
- [ ] Create `app/intelligence/database/safety_guard.py` (Read-only default, DDL/destructive DML blocker).
- [ ] Create `app/intelligence/database/performance_baseline.py`.
- [ ] Create `tests/test_database_intelligence.py`.

### Milestone 2: 7-Level Permission Architecture & Human Approval Gates
- [ ] Create `app/core/permissions.py` (Levels 0–6, ApprovalGateManager).
- [ ] Update `app/modules/agent/orchestrator.py` with approval pause/resume hooks.
- [ ] Create `tests/test_permissions_and_gates.py`.

### Milestone 3: Modular Skills System
- [ ] Create `skills/` directory with reusable knowledge (`skills/database/`, `skills/fastapi/`, etc.).
- [ ] Create `app/intelligence/skills/loader.py`.
- [ ] Create `tests/test_skills_engine.py`.

### Milestone 4: Multi-Stage Planning (Phases A–H) & 6-Review Loop Engine
- [ ] Create `app/modules/agent/planning/multi_stage.py` (Phases A through H).
- [ ] Create `app/modules/agent/planning/review_loops.py` (Reviews 1 through 6).
- [ ] Create `tests/test_multi_stage_planning.py`.

### Milestone 5: Full Integration & Regression Run
- [ ] Run full test battery (`pytest -v`) across all existing 57 tests + new subsystem tests.
- [ ] Verify 100% test pass rate and clean linter hygiene.
