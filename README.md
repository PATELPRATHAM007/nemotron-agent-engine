# ⚡ NVIDIA Nemotron 3 Ultra Autonomous Agent Engine

> **Production-Grade Repository Intelligence, Multi-Stage Planning, Verification Guardrails & Autonomous Coding Agent Harness powered by NVIDIA Nemotron 3 Ultra (550B LatentMoE) with 1M-Token Context Window.**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB?logo=python)](https://python.org/)
[![Tests](https://img.shields.io/badge/Backend%20Tests-177%20Passed-10B981?logo=pytest)](https://docs.pytest.org/)
[![Frontend Tests](https://img.shields.io/badge/Frontend%20Tests-19%20Passed-10B981?logo=vitest)](https://vitest.dev/)
[![NVIDIA](https://img.shields.io/badge/NVIDIA-Nemotron--3--Ultra-76B900?logo=nvidia)](https://huggingface.co/nvidia/Nemotron-3-Ultra)
[![Frontend](https://img.shields.io/badge/Frontend-React%2018%20%2B%20Vite%20%2B%20Tailwind-61DAFB)](http://localhost:5173)
[![Architecture](https://img.shields.io/badge/Architecture-Clean%20Modular%20Domain-FF6B6B)](app/modules/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

---

## 📑 Table of Contents

1. [Project Overview & Core Capabilities](#-project-overview--core-capabilities)
2. [End-to-End System Architecture](#-end-to-end-system-architecture)
3. [Key Workflows & Agent Lifecycle](#-key-workflows--agent-lifecycle)
4. [Implemented Subsystems Deep Dive](#-implemented-subsystems-deep-dive)
   - [Subsystem 1: Foundation Hardening & Tool Sandbox Engine](#subsystem-1-foundation-hardening--tool-sandbox-engine)
   - [Subsystem 2: Multi-Mode Repository Intelligence & Compact RepoMap](#subsystem-2-multi-mode-repository-intelligence--compact-repomap)
   - [Subsystem 3: Context Engine & Three-Tier Memory Architecture](#subsystem-3-context-engine--three-tier-memory-architecture)
   - [Subsystem 4: Agent Planning Harness & Isolated Subagents](#subsystem-4-agent-planning-harness--isolated-subagents)
   - [Subsystem 5: Visual UI Verification, Database Safety & Artifact Delivery](#subsystem-5-visual-ui-verification-database-safety--artifact-delivery)
5. [Tech Stack](#-tech-stack)
6. [Clean Modular Project Structure](#-clean-modular-project-structure)
7. [Installation & Setup](#-installation--setup)
8. [Environment Variables Reference](#-environment-variables-reference)
9. [Local Development Guide](#-local-development-guide)
10. [Comprehensive Testing Strategy & Results](#-comprehensive-testing-strategy--results)
11. [Agent Modes & Supported Workflows](#-agent-modes--supported-workflows)
12. [Tool Registry & MCP Integration](#-tool-registry--mcp-integration)
13. [Permissions, Safety Guardrails & Human Approval Gates](#-permissions-safety-guardrails--human-approval-gates)
14. [Security & Isolation Guarantees](#-security--isolation-guarantees)
15. [Troubleshooting & FAQ](#-troubleshooting--faq)
16. [Limitations & Known Constraints](#-limitations--known-constraints)

---

## 🌟 Project Overview & Core Capabilities

The **Nemotron Agent Engine** provides a full-featured, autonomous software engineering platform modeled after OpenAI Codex, Claude Code, and Google Antigravity, anchored by **NVIDIA Nemotron 3 Ultra** (550B LatentMoE) with dual-engine fallback (Groq LPU / Gemini Flash).

### The Core Mandate
> **The Model Context Window is Working Memory, NOT a Database or Permanent Storage.**

Most AI assistants fail in enterprise codebases because they dump raw dumps of entire repositories into the prompt, resulting in context rot, hallucinations, and destructive regressions. The Nemotron Agent Engine enforces a strict boundary:
- **Deterministic Tools** establish facts (AST analysis, ripgrep, Git diffs, test runners, DB reflection).
- **Nemotron 3 Ultra** reasons, plans, diagnoses, and synthesizes surgical diffs.
- **Verification Gates & Guardrails** verify code syntax, type safety, test passage, and database mutation safety before changes are accepted.

---

## 🏛️ End-to-End System Architecture

```text
                           CLIENT / WEB UI STUDIO / CLI
                                        │
                                        ▼
                         ┌──────────────────────────────┐
                         │     FASTAPI API GATEWAY      │
                         │    (/api/v1/* Domain API)    │
                         └──────────────┬───────────────┘
                                        │
              ┌─────────────────────────┼─────────────────────────┐
              ▼                         ▼                         ▼
      Task & Mission Service     Memory Service           Repo & DB Intel
              │                         │                         │
              └─────────────────────────┼─────────────────────────┘
                                        ▼
                         ┌──────────────────────────────┐
                         │     CONTEXT ORCHESTRATOR     │
                         │   L0-L10 Budget Allocator    │
                         │  Context Compactor (> 75%)   │
                         └──────────────┬───────────────┘
                                        │
              ┌─────────────────────────┼─────────────────────────┐
              ▼                         ▼                         ▼
       Compact RepoMap           Target AST Code         Three-Tier Memory
      (AST Centrality)          (Surgical Scope)        (Session/Proj/User)
              │                         │                         │
              └─────────────────────────┼─────────────────────────┘
                                        ▼
                         ┌──────────────────────────────┐
                         │   PRIMARY LLM / GATEWAY      │
                         │   NVIDIA Nemotron 3 Ultra    │
                         │ (Fallback: Gemini / Groq)    │
                         └──────────────┬───────────────┘
                                        │
                                        ▼
                         ┌──────────────────────────────┐
                         │    AGENT REACT EXECUTOR      │
                         │   Reasoning ➔ Tool ➔ Obs     │
                         │ Circuit Breakers (Max 25)    │
                         └──────────────┬───────────────┘
                                        │
         ┌──────────────────────────────┴──────────────────────────────┐
         ▼                                                             ▼
┌──────────────────────────────┐                              ┌──────────────────────────────┐
│     TOOL SANDBOX ENGINE      │                              │    8-GATE VERIFICATION       │
│ • Workspace Sandbox          │                              │ 1. Python/TS Syntax Gate     │
│ • Surgical Diff Patcher      │                              │ 2. Import & Symbol Integrity │
│ • Hardened Process Runner    │                              │ 3. Static Typecheck (mypy)   │
│ • Native Git Checkpoints     │                              │ 4. Unit & Integration Tests  │
│ • Browser UI Verification    │                              │ 5. Task Scope Lock Check     │
│ • Safe Migration Proposer    │                              │ 6. DB Mutation Safety Gate   │
└──────────────────────────────┘                              │ 7. Diff Size / Regression    │
                                                              │ 8. Visual UI Check (Browser) │
                                                              └──────────────────────────────┘
```

---

## 🔄 Key Workflows & Agent Lifecycle

The complete autonomous lifecycle executes the following stages:

```text
User Request
     ↓
1. Dynamic Task Classification (QUESTION | RESEARCH | PLAN | BUILD | DEBUG | REVIEW)
     ↓
2. Context Assembly & Three-Tier Memory Retrieval (L0–L10 Layer Budget Allocator)
     ↓
3. Repository Intelligence (Compact RepoMap, AST Search, Ripgrep)
     ↓
4. Multi-Stage Planning (Phases A–H with Dependency Ordering)
     ↓
5. Risk Assessment & Interactive Approval ([Allow Once] | [Allow Mission] | [Deny])
     ↓
6. Surgical Execution (Diff Patcher minimal hunks under TaskScope Lock)
     ↓
7. 8-Gate Verification Battery (Syntax ➔ Imports ➔ Tests ➔ DB Safety)
     ↓
8. Self-Healing Auto-Debugger (Bounded to 3 repair iterations, or rollback)
     ↓
9. Completion Artifact Delivery (Plan, Diff, Test Report, Screenshot)
```

---

## 🛠️ Implemented Subsystems Deep Dive

### Subsystem 1: Foundation Hardening & Tool Sandbox Engine
- **Workspace Sandbox (`app/modules/agent/tools/workspace.py`)**: Confines all file operations strictly to the workspace root. Blocks path traversal attempts (e.g. `../../etc/passwd`, URL-encoded `%2e%2e%2f`, and tilde `~` escapes) with `PathTraversalError`.
- **Concurrency Conflict Detection**: Computes SHA-256 and modification time fingerprints (`st_mtime`) before and after edits. If disk state changes externally, operations are aborted with `ConcurrencyConflictError` to prevent clobbering user edits.
- **Surgical Diff Patcher (`app/modules/agent/tools/patcher.py`)**: Replaces only minimal targeted code hunks rather than rewriting entire files. Handles newline differences, trailing spaces, and prevents ambiguous multi-match replacements.
- **Hardened Process Runner (`app/modules/agent/tools/process_runner.py`)**: Confined strictly to `workspace_root`. Enforces timeouts (default 30s, max 300s), terminates runaway subprocesses cleanly via process groups (`os.killpg`), and truncates stdout (32 KB) and stderr (16 KB).
- **Native Git Engine (`app/modules/agent/tools/git_tool.py`)**: Implements `git_status`, `git_diff`, `git_log`, `git_blame`, `git_checkpoint`, and `git_rollback`.

### Subsystem 2: Multi-Mode Repository Intelligence & Compact RepoMap
- **High-Speed Ripgrep Search (`app/modules/intelligence/indexing/ripgrep.py`)**: Dispatches `rg` with file-type filters, path restrictions, and Python regex fallback.
- **Compact RepoMap Generator (`app/modules/intelligence/indexing/repo_map.py`)**: Parses Python AST to extract classes, functions, and FastAPI routes ranked by centrality into a compact representation guaranteed to stay under 2,000 tokens.
- **Git History & Blame Retriever (`app/modules/intelligence/indexing/git_history.py`)**: Retrieves commit summaries and line-by-line blame metadata.

### Subsystem 3: Context Engine & Three-Tier Memory Architecture
- **L0–L10 Context Budget Allocator (`app/modules/intelligence/context/budget_allocator.py`)**: Allocates discrete token quotas across 10 layers:
  - `L0`: System Instructions (~1,000 tokens) [CRITICAL]
  - `L1`: Constitutional Rules (~800 tokens) [CRITICAL]
  - `L2`: Project Identity (~500 tokens)
  - `L3`: Task Objective (~300 tokens) [CRITICAL]
  - `L4`: Compact RepoMap (~1,500 tokens)
  - `L5`: Primary Code Snippets (~6,000 tokens) [CRITICAL]
  - `L6`: Architecture Decisions & ADRs (~1,000 tokens)
  - `L7`: Recent Turns (~2,000 tokens)
  - `L8`: Tool Observations (~2,000 tokens)
  - `L9`: Working Memory & Scratchpad (~800 tokens)
  - `L10`: Output Reservation (~4,000 tokens)
  - *Dynamic Progressive Trimming:* Non-critical layers (L8, L6, L7, L4) are trimmed during token pressure while critical layers (L0, L1, L3, L5) are strictly preserved.
- **Automated Context Compactor (`app/modules/intelligence/context/compactor.py`)**: Monitors context pressure (`GREEN`, `YELLOW`, `ORANGE`, `RED`, `CRITICAL`). Triggers at 75% window ceiling, synthesizing conversation turns and tool observations into structured `CompactionSnapshot` state snapshots with zero loss of active errors or modified files.
- **Three-Tier Memory Store (`app/modules/intelligence/memory/three_tier_store.py`)**:
  - *Tier 1 — Session Memory (Ephemeral):* Active task, working plan, staged files, transient tool outputs. Cleared upon mission completion.
  - *Tier 2 — Project Memory (Durable, per-repo):* `.agent/memory/project_memory.json`. Stores coding standards, architectural rules, database conventions, and past bug resolutions.
  - *Tier 3 — User Memory (Cross-project, per-developer):* Stores individual developer preferences.
  - *Memory Durability Gate:* Filters candidate memories; rejects transient noise ("fixed typo on line 12", "button color red") and saves only persistent, reusable engineering knowledge.

### Subsystem 4: Agent Planning Harness & Isolated Subagents
- **Iterative ReAct Execution Loop (`app/modules/agent/react_engine.py`)**: Autonomous multi-turn cycle (Reasoning ➔ Tool ➔ Observation). Features circuit breakers (max 25 iterations, loop/cycle detection for repeated tool invocations).
- **Dynamic Task Classifier (`app/modules/agent/classifier.py`)**: Accurately categorizes prompts into 6 workflows:
  - `QUESTION`: Conversational responses.
  - `RESEARCH`: Read-only repository exploration.
  - `PLAN`: Architecture evaluation and multi-stage roadmaps.
  - `BUILD`: Full autonomous engineering with verification.
  - `DEBUG`: Stack-trace diagnosis and targeted patch repair.
  - `REVIEW`: Static diff inspection and security audits.
- **Isolated Subagent Coordinator (`app/modules/agent/subagents/coordinator.py`)**: Coordinates specialized subagents with isolated context windows (`ResearcherSubagent`, `CoderSubagent`, `ReviewerSubagent`, `TesterSubagent`). Subagent traces never pollute the primary context.

### Subsystem 5: Visual UI Verification, Database Safety & Artifact Delivery
- **Browser Visual UI Tool (`app/modules/agent/tools/browser_tool.py`)**: Headless browser automation (`open`, `screenshot`, `click`, `type`, `evaluate_js`) for multimodal UI verification with offline simulated engine fallback.
- **Database EXPLAIN Intelligence & Safe Migrations (`app/modules/intelligence/database/`)**:
  - `ExplainPlanEngine`: Analyzes execution plans, detects sequential scans on large tables, and suggests indexes.
  - `SafeMigrationGenerator`: Proposes reversible Alembic migration scripts (`upgrade()` / `downgrade()`).
  - *Absolute Safety Invariant:* DDL execution or data deletion strictly requires explicit human authorization token (`MUTATION_APPROVAL_REQUIRED`).
- **Structured Artifact Delivery System (`app/modules/missions/artifacts.py`)**: Stores and serves reviewable artifacts (Plans, Diffs, Test Reports, Screenshots) via `/api/v1/missions/{id}/artifacts`.

---

## 💻 Tech Stack

| Component | Technology | Description |
|---|---|---|
| **Backend Framework** | Python 3.12 / FastAPI | High-performance async REST and SSE API gateway |
| **Primary LLM** | NVIDIA Nemotron 3 Ultra | 550B LatentMoE parameter model with 1M-token context |
| **Fallback Models** | Google Gemini 3.1 Flash / Groq LPU | Fast preprocessing, summarization, and context compaction |
| **Database & ORM** | PostgreSQL / SQLite / SQLAlchemy 2.0 | Async session management with relational audit logging |
| **Migrations** | Alembic | Version-controlled database schema migrations |
| **Indexing & Search** | Python `ast` + Ripgrep (`rg`) | Centrality-ranked symbol maps and high-speed text search |
| **Security & Cryptography** | Argon2id + PyJWT + cryptography | Secret redaction, SSRF filter, RBAC/ABAC policy engine |
| **Frontend Framework** | React 18 + Vite + Tailwind CSS | Responsive developer UI studio with real-time SSE streaming |
| **Test Runners** | Pytest (Backend) / Vitest (Frontend) | Full test suites across unit, integration, and security |

---

## 📁 Clean Modular Project Structure

```text
nemotron-agent-engine/
├── app/
│   ├── api/v1/router.py          # Unified API router mounting all modules
│   ├── core/
│   │   ├── config.py             # Pydantic v2 application settings
│   │   ├── exceptions.py         # Unified exception hierarchy
│   │   └── logging_config.py     # Rotating structured JSON logger
│   ├── db/
│   │   ├── base.py               # All 24 SQLAlchemy models registered for inspection
│   │   └── session.py            # Database connection pool and session generator
│   └── modules/
│       ├── agent/                # Agent core, ReAct loop, task classifier, subagents
│       │   ├── classifier.py     # 6-workflow dynamic task classifier
│       │   ├── react_engine.py   # Iterative ReAct loop engine with circuit breakers
│       │   ├── subagents/        # Isolated Researcher, Coder, Reviewer, Tester
│       │   ├── tools/            # Workspace sandbox, patcher, process runner, browser
│       │   └── verification/     # 8-gate verification battery & auto-debugger
│       ├── auth/                 # Authentication, Argon2id hashing, SSRF guard
│       ├── constitution/         # Quality invariants, coding standards, ADRs
│       ├── cost/                 # Token cost tracker and financial ledger
│       ├── gateway/              # Model gateway, provider router, model registry
│       ├── intelligence/         # Context budget allocator, compactor, memory store
│       │   ├── context/          # L0-L10 budget allocator & automated compactor
│       │   ├── database/         # EXPLAIN plan analyzer & safe migration generator
│       │   ├── indexing/         # Ripgrep search, compact repo map, git history
│       │   └── memory/           # Three-tier store (Session, Project, User)
│       └── missions/             # Mission state machine, permissions, artifacts
│           ├── artifacts.py      # Plan, diff, test report, screenshot artifacts
│           └── permissions.py    # Command risk classification & permission scopes
└── tests/                        # 32 test suites covering 177 automated test cases
```

---

## ⚙️ Installation & Setup

### Prerequisites
- Python 3.11 or 3.12
- Node.js 18+ and npm
- Git
- (Optional) PostgreSQL and Redis (SQLite fallback supported by default)

### 1. Clone & Setup Backend
```bash
cd /Users/mac/Desktop/nemotron-agent-engine
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Setup Frontend
```bash
cd /Users/mac/Desktop/nemotron-agent-frontend
npm install
```

---

## 🔐 Environment Variables Reference

Source of truth: `.env.example`

| Variable | Default Value | Description |
|---|---|---|
| `PROJECT_NAME` | `"Nemotron Agent Engine"` | Name of application instance |
| `ENVIRONMENT` | `"development"` | Active runtime mode (`development` or `production`) |
| `DEBUG` | `True` | Enable debug logs and tracebacks |
| `HOST` | `"0.0.0.0"` | API bind address |
| `PORT` | `8000` | API bind port |
| `DATABASE_URL` | `postgresql+psycopg2://...` | Relational database connection string (SQLite fallback supported) |
| `REDIS_URL` | `redis://localhost:6379/0` | Ephemeral caching broker |
| `NEMOTRON_API_BASE` | `http://localhost:8000/v1` | vLLM or Nemotron 3 Ultra inference endpoint |
| `NEMOTRON_API_KEY` | `EMPTY` | API authorization key for model endpoint |
| `NEMOTRON_MODEL_NAME` | `nvidia/Nemotron-3-Ultra` | Model identifier |
| `NEMOTRON_MAX_TOKENS` | `16384` | Maximum output generation token ceiling |
| `NEMOTRON_ENABLE_THINKING`| `true` | Enable latent reasoning `thought` streaming |
| `GEMINI_API_KEY` | `""` | Optional Google GenAI API key for Tier-1 fast compaction |
| `GEMINI_MODEL_NAME` | `gemini-3.1-flash-lite` | Optional Tier-1 fast summarizer model |

---

## 🚀 Local Development Guide

### Running Backend API Server
```bash
cd /Users/mac/Desktop/nemotron-agent-engine
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI Schema: `http://localhost:8000/openapi.json`

### Running Frontend Development Studio
```bash
cd /Users/mac/Desktop/nemotron-agent-frontend
npm run dev
```
Frontend Web App is accessible at `http://localhost:5173`.

---

## 🧪 Comprehensive Testing Strategy & Results

The system is tested across the entire spectrum from **EXTREMELY BAD** to **EXTREMELY GOOD**:

```text
EXTREMELY BAD (Injections, Traversal, Concurrency, Runaway Loops, Destructive Queries)
        ↓
Invalid & Boundary (Malformed JSON, Missing Fields, Empty Strings, Wrong Types)
        ↓
Stress & Concurrency (Extreme Token Overflow, Multi-Turn Compaction, Rapid Edits)
        ↓
Recovery & Normal (Self-Healing Auto-Debugger, Reversible Migrations)
        ↓
EXTREMELY GOOD (Flawless Verification, Zero Regressions, Verified Artifacts)
```

### Automated Test Summary

```text
Backend Test Results:
  Total Test Suites: 32
  Total Tests Passed: 177 / 177
  Time to Run: ~12.4 seconds
  Test Command: .venv/bin/pytest

Frontend Test Results:
  Total Test Suites: 4
  Total Tests Passed: 19 / 19
  TypeScript Checks: 0 errors (npx tsc --noEmit)
  Test Command: npm test -- --run
```

### Running Test Batteries

```bash
# Run complete backend test suite
.venv/bin/pytest

# Run master edge-case and hardening tests
.venv/bin/pytest tests/test_master_edge_cases_and_hardening.py

# Run Phase 1 tools and sandbox tests
.venv/bin/pytest tests/test_phase1_tools_and_sandbox.py

# Run Phase 2 repository intelligence tests
.venv/bin/pytest tests/test_phase2_repo_intelligence.py

# Run Phase 3 context and three-tier memory tests
.venv/bin/pytest tests/test_phase3_context_and_memory.py

# Run Phase 4 ReAct loop and subagent tests
.venv/bin/pytest tests/test_phase4_agent_harness.py

# Run Phase 5 browser and database capability tests
.venv/bin/pytest tests/test_phase5_advanced_capabilities.py
```

---

## 🧭 Agent Modes & Supported Workflows

The `DynamicTaskClassifier` automatically classifies user intents into discrete workflows:

| Workflow | Description | Primary Tools Allowed | Default Subagent |
|---|---|---|---|
| **`QUESTION`** | Direct conversational answer without workspace modifications | `read_file`, `get_repo_map` | `DirectResponder` |
| **`RESEARCH`** | Read-only exploration of repository and dependencies | `read_file`, `ripgrep_search`, `get_repo_map`, `git_history` | `ResearcherSubagent` |
| **`PLAN`** | Architecture evaluation with Option A / B / C tradeoffs | `read_file`, `get_repo_map`, `list_dir` | `PlannerSubagent` |
| **`BUILD`** | Full autonomous engineering with code synthesis and verification | `read_file`, `edit_file`, `apply_diff_patch`, `execute_command`, `browser_open` | `CoderSubagent` |
| **`DEBUG`** | Stack-trace diagnosis, reproducing bugs, and surgical repair | `read_file`, `edit_file`, `apply_diff_patch`, `execute_command` | `DebuggerSubagent` |
| **`REVIEW`** | Static analysis, diff review, and constitutional security audit | `read_file`, `ripgrep_search`, `git_diff`, `get_git_history` | `ReviewerSubagent` |

---

## 🧰 Tool Registry & MCP Integration

All tools conform to the Model Context Protocol (MCP) and OpenAI Function schemas, dispatched via `dispatch_tool`:

- **Filesystem Tools**: `read_file`, `write_file`, `edit_file`, `list_dir`
- **Search & Indexing Tools**: `ripgrep_search`, `get_repo_map`, `get_git_history`
- **Subprocess & Execution Tools**: `execute_command`, `run_process`
- **Git Tools**: `git_status`, `git_diff`, `git_checkpoint`, `git_rollback`
- **Visual UI Tools**: `browser_open`, `browser_screenshot`, `browser_click`

---

## 🛡️ Permissions, Safety Guardrails & Human Approval Gates

1. **Dangerous Command Interception**: Commands matching `CRITICAL_PATTERNS` (`rm -rf /`, `rm -rf /*`, `chmod -R 777 /`, `mkfs`, fork bombs) are unconditionally **`DENIED`**.
2. **High-Risk Command Evaluation**: Commands like `git push`, `docker run --privileged`, `curl ... | bash` require explicit human approval (`ASK`).
3. **Database Mutation Safety Gate**: Any query attempting data or schema mutation (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`) requires:
   - Level 5 Permission Gate.
   - An active human authorization token (`MUTATION_APPROVAL_REQUIRED`).
4. **Unconditional Block on Unbounded SQL**: Any `UPDATE` or `DELETE` statement missing a `WHERE` clause is strictly blocked by `DatabaseSafetyGuard` with `DatabaseSafetyViolationError`.

---

## 🔒 Security & Isolation Guarantees

- **Path Traversal Isolation**: Normalizes all incoming file paths. Detects and blocks `..`, URL-encoded `%2e%2e%2f`, and tilde `~` escapes.
- **SSRF Filter**: Model gateway rejects target URLs resolving to internal private ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.1`) and cloud metadata endpoints (`169.254.169.254`).
- **Prompt Injection Defense**: Repository content (e.g., comments or markdown containing *"IGNORE ALL PREVIOUS INSTRUCTIONS"*) is processed strictly as inert data strings and cannot override safety invariants or system instructions.
- **Secret Redaction**: API keys, tokens, and passwords are automatically redacted from error traces, logs, and prompt context.

---

## ❓ Troubleshooting & FAQ

#### Q: How does the agent handle large repositories without running out of tokens?
The engine uses the AST-based `RepoMapGenerator` to construct an architectural outline (< 2,000 tokens) and the `ContextBudgetAllocator` to strictly enforce a <= 32,000 token ceiling. When conversation history grows, the `ContextCompactor` triggers at 75% capacity to compress old turns into structured state snapshots.

#### Q: What happens if an external developer edits a file while the agent is running?
`WorkspaceSandbox` compares SHA-256 fingerprints before applying edits. If the disk fingerprint has changed since context retrieval, the patch is rejected with `ConcurrencyConflictError`, prompting the agent to re-read the latest disk state.

#### Q: Can the agent accidentally delete database tables?
No. `DatabaseSafetyGuard` blocks destructive commands (`DROP`, `TRUNCATE`, `ALTER`) unless an explicit human authorization token (`MUTATION_APPROVAL_REQUIRED`) is provided. Unbounded `UPDATE` and `DELETE` queries lacking a `WHERE` clause are rejected unconditionally.

---

## ⚠️ Limitations & Known Constraints

1. **Hardware Requirements for Nemotron 3 Ultra**: Running the full 550B LatentMoE model locally requires an 8x A100/H100 80GB GPU node with vLLM. For local development on Mac/Linux, dual-engine fallbacks (Gemini Flash or Groq LPU) are fully supported.
2. **Headless Browser in Headless Environments**: If Playwright or Chromium binaries are not installed in the operating environment, `BrowserTool` falls back gracefully to synthetic screenshot capture and simulated DOM verification.
3. **Workspace Boundary**: The sandbox strictly confines the agent to the project root. Multi-repo workflows require configuring multiple distinct workspace sandboxes.

---

## 📄 License

Licensed under the [Apache License, Version 2.0](LICENSE).
