# Repository Intelligence & Autonomous Coding Agent

## 1. Purpose

This document defines the architecture, capabilities, skills, memory system, repository knowledge graph, planning workflow, code-generation workflow, debugging workflow, testing workflow, and verification system for a local AI coding agent powered by **Nemotron 3 Ultra**.

The goal is to build a system that can:

- Understand an unfamiliar repository.
- Learn its folder structure, architecture, coding style, conventions, and patterns.
- Build a persistent representation of repository knowledge.
- Understand features and map each feature to related files, symbols, tests, APIs, models, configuration, and dependencies.
- Retrieve only the relevant feature/subgraph when a developer asks for a change.
- Reduce token usage by avoiding unnecessary repository-wide context.
- Plan changes before modifying files.
- Perform dependency and impact analysis.
- Identify edge cases and risks before implementation.
- Implement code according to project-specific rules.
- Run static checks, tests, builds, and regression checks.
- Automatically investigate and fix suitable bugs.
- Learn from verified architectural decisions, bugs, and project-specific lessons.
- Keep repository knowledge incrementally updated as the code changes.
- Protect unrelated features from accidental modification.

---

# 2. Core Principle

Do **not** try to permanently "memorize the entire repository" inside the LLM.

Instead, build a **Repository Intelligence Layer** around Nemotron.

The model is the reasoning and coding engine.

The surrounding system is responsible for:

- Repository indexing
- AST analysis
- Symbol extraction
- Dependency analysis
- Feature mapping
- Graph storage
- Semantic search
- Exact code search
- Persistent memory
- Context selection
- Tool execution
- Testing
- Git operations
- Validation

The fundamental architecture is:

```text
Repository
    |
    v
Repository Intelligence
    |
    +-- AST / Symbol Index
    +-- Dependency Graph
    +-- Feature Graph
    +-- Semantic Index
    +-- Repository Memory
    +-- Architecture Knowledge
    |
    v
Context Manager
    |
    v
Nemotron 3 Ultra
    |
    v
Agent Tools
    |
    +-- Files
    +-- Git
    +-- Tests
    +-- Build
    +-- Static Analysis
    +-- Runtime
```

The repository remains the source of truth.

Memory is a retrieval aid, not the source of truth.

---

# 3. High-Level Architecture

```text
                         +----------------------+
                         |      Developer       |
                         |      Task/Request    |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |   Agent Orchestrator  |
                         +----------+-----------+
                                    |
             +----------------------+----------------------+
             |                      |                      |
             v                      v                      v
     +---------------+      +---------------+      +---------------+
     | Feature Graph |      | Code Search   |      | Memory Store  |
     +---------------+      +---------------+      +---------------+
             |                      |                      |
             +----------------------+----------------------+
                                    |
                                    v
                         +----------------------+
                         |  Context Manager     |
                         |  Scope / Ranking     |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |   Nemotron 3 Ultra   |
                         |                      |
                         | Plan / Code / Debug  |
                         | Review / Reason      |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |   Tool Orchestrator  |
                         +----------+-----------+
                                    |
             +----------------------+----------------------+
             |                      |                      |
             v                      v                      v
        File System              Git                   Tests
             |                      |                      |
             +----------------------+----------------------+
                                    |
                                    v
                           Validation Pipeline
                                    |
                                    v
                           Repository Updated
                                    |
                                    v
                     Graph + Memory Incremental Update
```

---

# 4. Major Components

## 4.1 Nemotron 3 Ultra

Nemotron is the primary reasoning and coding model.

It should be responsible for:

- Understanding code.
- Reasoning about architecture.
- Planning implementation.
- Generating code.
- Reviewing code.
- Explaining code.
- Analyzing failures.
- Performing root-cause reasoning.
- Generating tests.
- Suggesting fixes.
- Reviewing changes.
- Making decisions based on retrieved repository context.

It should **not** be treated as the permanent database for the repository.

---

## 4.2 Agent Orchestrator

The orchestrator controls the complete lifecycle.

Responsibilities:

- Receive developer task.
- Classify task.
- Identify relevant feature.
- Retrieve repository knowledge.
- Build task scope.
- Perform impact analysis.
- Ask Nemotron for a plan.
- Validate the plan.
- Execute tools.
- Apply changes.
- Run verification.
- Retry suitable failures.
- Roll back unsafe changes.
- Update repository knowledge.

Example:

```text
User Task
    |
    v
Task Classification
    |
    v
Feature Identification
    |
    v
Graph Retrieval
    |
    v
Context Construction
    |
    v
Nemotron Planning
    |
    v
Plan Validation
    |
    v
Implementation
    |
    v
Testing
    |
    v
Verification
    |
    v
Memory / Graph Update
```

---

# 5. Repository Intelligence

Repository Intelligence is the most important subsystem.

It should answer questions such as:

- What is this project?
- What framework does it use?
- Where is the backend?
- Where is the frontend?
- Where are the APIs?
- Where are the database models?
- Where are services?
- Where are repositories?
- Where are tests?
- Which files implement a particular feature?
- Which functions call another function?
- Which APIs use a service?
- Which tests cover a feature?
- Which files are likely to be affected by a change?
- Which architectural rules apply?

---

# 6. Repository Initialization / Onboarding

When a repository is added for the first time, the agent should perform an indexing phase.

## Initial Process

```text
1. Detect project type
2. Detect programming languages
3. Detect frameworks
4. Detect package managers
5. Detect entry points
6. Analyze directory structure
7. Parse source files
8. Build AST
9. Extract classes
10. Extract functions
11. Extract methods
12. Extract imports
13. Extract calls
14. Extract API endpoints
15. Extract database models
16. Detect configuration
17. Detect tests
18. Detect documentation
19. Detect build systems
20. Detect deployment configuration
21. Detect coding patterns
22. Build dependency graph
23. Build feature graph
24. Generate repository summaries
25. Run baseline tests
26. Store baseline state
```

The agent should not immediately modify code during repository onboarding.

---

# 7. Repository Structure Knowledge

The system should understand:

```text
Repository
|
+-- Backend
|   +-- API
|   +-- Services
|   +-- Repositories
|   +-- Models
|   +-- Schemas
|   +-- Middleware
|   +-- Configuration
|   +-- Tests
|
+-- Frontend
|   +-- Pages
|   +-- Components
|   +-- Services
|   +-- Hooks
|   +-- State
|   +-- Tests
|
+-- Infrastructure
|   +-- Docker
|   +-- Kubernetes
|   +-- CI/CD
|
+-- Documentation
|
+-- Scripts
|
+-- Tests
```

The exact structure should be learned from the repository rather than hard-coded.

---

# 8. AST-Based Code Understanding

Code understanding should not rely only on embeddings.

Use parsers and ASTs to extract deterministic information.

```text
Source Code
    |
    v
Parser
    |
    v
AST
    |
    +-- Classes
    +-- Functions
    +-- Methods
    +-- Imports
    +-- Calls
    +-- Variables
    +-- Decorators
    +-- Routes
    +-- Models
    +-- Tests
```

For Python, use Python AST and/or Tree-sitter.

For other languages, use Tree-sitter or language-specific parsers where appropriate.

---

# 9. Repository Knowledge Graph

A simple file-to-file graph is not enough.

The system should maintain a multi-layer graph.

## Layer 1: Repository

```text
Repository
```

## Layer 2: Modules

```text
Backend
Frontend
Authentication
Payments
Users
Notifications
```

## Layer 3: Files

```text
auth/router.py
auth/service.py
auth/model.py
```

## Layer 4: Symbols

```text
login()
logout()
refresh_token()
AuthService
UserRepository
```

## Layer 5: Features

```text
Authentication
Payment
Registration
Profile
```

## Layer 6: Tests

```text
test_login_success
test_login_failure
test_token_expired
```

## Layer 7: Documentation

```text
README
ADR
Feature documentation
API documentation
```

## Layer 8: History

```text
Commits
Previous changes
Previous bugs
Architectural decisions
```

---

# 10. Graph Relationships

Recommended relationship types:

```text
IMPORTS
CALLS
DEFINES
USES
IMPLEMENTS
TESTS
DEPENDS_ON
PART_OF_FEATURE
DOCUMENTED_BY
CONFIGURED_BY
AFFECTS
CREATED_BY
MODIFIED_BY
EXPOSES
CONSUMES
PERSISTS_TO
```

Example:

```text
Feature: Authentication
        |
        +-- PART_OF_FEATURE --> auth/router.py
        |
        +-- PART_OF_FEATURE --> auth/service.py
        |
        +-- PART_OF_FEATURE --> auth/schema.py
        |
        +-- PART_OF_FEATURE --> auth/model.py
        |
        +-- PART_OF_FEATURE --> tests/auth/test_login.py
```

And:

```text
auth/router.py
      |
      +-- CALLS --> AuthService.login()
                          |
                          +-- CALLS --> UserRepository.get_user()
                          |
                          +-- USES --> PasswordHasher
                          |
                          +-- USES --> JWTService
```

---

# 11. Feature Intelligence

Features should be first-class entities.

Example:

```text
Feature: Authentication

Files:
- auth/router.py
- auth/service.py
- auth/schema.py
- auth/model.py
- middleware/auth.py

APIs:
- POST /login
- POST /logout
- POST /refresh

Database:
- users
- refresh_tokens

Tests:
- tests/auth/test_login.py
- tests/auth/test_token.py

External services:
- Email
- OAuth provider

Known bugs:
- Token race condition

Architectural decisions:
- JWT access tokens
- Refresh-token rotation
```

This feature node should connect to all related repository objects.

---

# 12. Feature-Scoped Retrieval

This is one of the most important token-saving mechanisms.

Instead of:

```text
Task
  |
  v
Entire repository
```

Use:

```text
Task
  |
  v
Feature identification
  |
  v
Feature node
  |
  v
Relevant subgraph
  |
  v
Relevant files
  |
  v
Relevant symbols
  |
  v
Relevant tests
```

Example:

```text
User:
"Change login timeout."

            |
            v

Authentication
            |
            +-- Login
                  |
                  +-- AuthService
                  +-- Session
                  +-- JWT
                  +-- Middleware
                  +-- Tests
```

Unrelated features should not be loaded unless impact analysis identifies them.

---

# 13. Context Management

The context manager should decide what the model actually receives.

Example:

```text
Repository:
200,000 tokens

Potentially relevant:
40,000 tokens

Selected:
- Repository architecture: 2,000
- Feature graph: 1,500
- Relevant source: 18,000
- Tests: 5,000
- Project rules: 2,000
- Bug history: 2,000

Final context:
30,500 tokens
```

The goal is:

> Maximum relevant information with minimum unnecessary context.

---

# 14. Hierarchical Context

Use multiple levels of summaries.

```text
Repository Summary
       |
       v
Module Summary
       |
       v
Feature Summary
       |
       v
File Summary
       |
       v
Symbol Summary
       |
       v
Actual Source Code
```

The system should progressively expand context only when necessary.

Example:

```text
Repository
  |
  +-- Backend
       |
       +-- Authentication
            |
            +-- Login
                 |
                 +-- AuthService
                      |
                      +-- login()
                           |
                           +-- Source Code
```

---

# 15. Repository Memory

The system should have multiple memory categories.

## 15.1 Structural Memory

Answers:

> Where is everything?

Example:

```json
{
  "file": "backend/auth/service.py",
  "language": "python",
  "module": "authentication",
  "symbols": [
    "AuthService.login",
    "AuthService.logout"
  ]
}
```

---

## 15.2 Semantic Code Memory

Answers:

> What does this code do?

Example:

```text
AuthService.login()

Purpose:
Authenticate a user and create an access token.

Depends on:
- UserRepository
- PasswordHasher
- JWTService

Used by:
- POST /login
- Admin login
```

---

## 15.3 Feature Memory

Answers:

> Which repository objects implement this feature?

---

## 15.4 Architecture Memory

Stores:

- Architecture patterns.
- Service boundaries.
- Database architecture.
- API conventions.
- Integration patterns.
- Important design decisions.

---

## 15.5 Decision Memory

Stores verified developer decisions.

Example:

```text
Decision:
All API timestamps are stored in UTC.

Source:
ADR-004

Verified:
true
```

---

## 15.6 Bug Memory

Stores:

```text
Bug
Root cause
Fix
Affected feature
Affected files
Regression test
Date
Verification
```

Example:

```text
Bug:
Redis timeout.

Root cause:
A Redis connection pool was created per request.

Fix:
Use application-level async Redis client.

Regression:
test_redis_connection_reuse.
```

---

## 15.7 Lesson Memory

Stores reusable project-specific lessons.

Example:

```text
Lesson:
Do not perform database operations directly in FastAPI routers.

Preferred:
Router -> Service -> Repository.
```

---

# 16. Memory Rules

Memory must be selective.

Store:

```text
- Architecture decisions
- Verified project rules
- Important bugs
- Root causes
- Important developer decisions
- Confirmed patterns
- Feature relationships
- External integration knowledge
```

Do not store:

```text
- Every terminal output
- Every temporary error
- Every file read
- Every generated response
- Temporary debugging noise
```

---

# 17. Memory Confidence

Each memory should contain:

```text
confidence
source
created_at
updated_at
verified
```

Example:

```json
{
  "memory": "All API timestamps are UTC",
  "source": "ADR-004",
  "confidence": 1.0,
  "verified": true
}
```

Unverified observations should not be treated as hard project rules.

---

# 18. Source of Truth

The hierarchy should be:

```text
1. Actual source code
2. Tests
3. Explicit project rules / ADRs
4. Verified repository memory
5. Generated summaries
6. Model assumptions
```

Memory must be verified against the repository before high-risk changes.

---

# 19. Project Coding Rules

Create an `.agent` directory inside each repository.

Recommended structure:

```text
.agent/
|
+-- rules/
|   +-- architecture.md
|   +-- coding-style.md
|   +-- testing.md
|   +-- security.md
|   +-- database.md
|   +-- api.md
|   +-- git.md
|
+-- architecture/
|   +-- overview.md
|   +-- backend.md
|   +-- frontend.md
|   +-- decisions/
|
+-- features/
|   +-- authentication.md
|   +-- payments.md
|   +-- users.md
|
+-- memory/
|   +-- bugs/
|   +-- lessons/
|   +-- decisions/
|
+-- graph/
|
+-- repository-summary.md
```

---

# 20. Coding Principles

The agent should follow general principles such as:

1. Follow existing architecture.
2. Avoid unnecessary changes.
3. Do not modify unrelated files.
4. Prefer small, reversible changes.
5. Avoid unnecessary dependencies.
6. Preserve backward compatibility where required.
7. Validate inputs.
8. Handle errors explicitly.
9. Never hide errors just to make tests pass.
10. Add or update tests for changed behavior.
11. Preserve security boundaries.
12. Do not expose secrets.
13. Review the final diff.
14. Keep changes explainable.
15. Verify before declaring success.

Repository-specific rules have priority over generic style preferences when they are explicit and valid.

---

# 21. Skills Architecture

Do not create one giant skill called "software development."

Use specialized skills.

```text
skills/
|
+-- repository-intelligence/
|   +-- repository-discovery
|   +-- repository-indexing
|   +-- code-navigation
|   +-- feature-discovery
|   +-- dependency-analysis
|
+-- planning/
|   +-- implementation-planning
|   +-- change-impact-analysis
|   +-- risk-analysis
|   +-- verification-planning
|
+-- implementation/
|   +-- coding-principles
|   +-- safe-code-modification
|   +-- refactoring
|
+-- debugging/
|   +-- error-analysis
|   +-- stack-trace-analysis
|   +-- root-cause-analysis
|   +-- automatic-debugging
|
+-- testing/
|   +-- test-analysis
|   +-- test-generation
|   +-- regression-analysis
|
+-- verification/
|   +-- static-analysis
|   +-- diff-review
|   +-- final-validation
|
+-- git/
    +-- git-analysis
    +-- checkpoint
    +-- rollback
    +-- safe-diff
```

Only load the skills relevant to the current task.

---

# 22. Skill vs Memory vs Code

These must remain separate.

## Skill

How to perform an operation.

Example:

```text
How to perform impact analysis.
```

## Repository Memory

Project-specific information.

Example:

```text
This project uses router -> service -> repository.
```

## Feature Memory

Feature-specific information.

Example:

```text
Authentication is implemented in these files.
```

## Source Code

The actual implementation.

Example:

```text
auth/service.py
```

This separation keeps the system maintainable.

---

# 23. Coding Style Discovery

The system should analyze existing code and detect patterns.

Example:

```text
Detected patterns:

Language:
Python

Framework:
FastAPI

Async:
Async I/O functions

Architecture:
Router -> Service -> Repository

Testing:
pytest

Formatting:
ruff

Type checking:
mypy

API:
Versioned /api/v1 endpoints

Error handling:
Custom application exceptions

Logging:
Structured logging
```

These are initially observations.

They should only become hard project rules when sufficiently confirmed or explicitly approved.

---

# 24. Architecture Decision Records

Use ADRs for important decisions.

Example:

```text
.agent/architecture/decisions/ADR-001.md
```

Example content:

```markdown
# ADR-001: Service-Repository Architecture

## Decision

Use:

Router -> Service -> Repository -> Database

## Reason

Keep API transport, business logic, and persistence responsibilities separate.

## Status

Accepted
```

ADRs provide the model with architectural reasoning, not just code examples.

---

# 25. Feature Documentation

Each major feature should have a structured document.

Example:

```markdown
# Authentication

## Purpose

...

## Entry Points

...

## API Endpoints

...

## Files

...

## Symbols

...

## Dependencies

...

## Database

...

## Tests

...

## External Services

...

## Known Bugs

...

## Architecture Decisions

...
```

Feature documentation should link back to graph nodes.

---

# 26. Dependency Analysis

Before changing a symbol, determine:

```text
Who calls it?
What does it call?
Which APIs expose it?
Which tests use it?
Which features contain it?
Which database entities does it affect?
Which configuration does it depend on?
```

Example:

```text
AuthService.login()
        |
        +-- Called by:
        |     auth/router.py
        |     admin/router.py
        |
        +-- Calls:
        |     UserRepository
        |     PasswordHasher
        |     JWTService
        |
        +-- Tested by:
              test_login.py
              test_admin_login.py
```

---

# 27. Change Impact Analysis

Every non-trivial change should have impact analysis.

Example:

```text
Target:
payment_service.py

Direct dependencies:
4

Indirect dependencies:
7

Affected tests:
5

Affected API endpoints:
2

Affected database entities:
2

External integrations:
1
```

The system should use this information to construct the implementation plan.

---

# 28. Task Scope Lock

After impact analysis, establish a task scope.

Example:

```text
Task Scope

Feature:
Authentication -> Login

Allowed primary files:
- auth/router.py
- auth/service.py
- auth/schema.py
- auth/model.py
- tests/auth/

Related files:
- middleware/auth.py
- config/auth.py
```

If the agent wants to modify unrelated files, the orchestrator should detect the scope expansion.

Example:

```text
Agent wants to modify:
billing/payment.py

Reason:
No direct relationship found with current task.

Action:
Require explicit scope expansion or additional evidence.
```

This prevents agent wandering.

---

# 29. Planning Before Implementation

The agent must not immediately edit files for complex changes.

Required workflow:

```text
UNDERSTAND
    |
    v
LOCATE
    |
    v
ANALYZE
    |
    v
IMPACT ANALYSIS
    |
    v
RISK ANALYSIS
    |
    v
PLAN
    |
    v
PLAN REVIEW
    |
    v
IMPLEMENT
```

---

# 30. Plan Review

For complex changes, use a separate review stage.

```text
Planner
   |
   v
Implementation Plan
   |
   v
Plan Reviewer
   |
   +-- Missing dependency
   +-- Missing test
   +-- Architecture violation
   +-- Edge case
   +-- Security concern
   |
   v
Approved Plan
```

The same Nemotron model can be used with a different role/system instruction.

---

# 31. Edge Case Analysis

Before implementation, the agent should consider:

```text
- Empty input
- Invalid input
- Null values
- Missing records
- Duplicate records
- Concurrent requests
- Timeouts
- Retries
- Authentication failures
- Authorization failures
- Database failures
- External API failures
- Race conditions
- Backward compatibility
- Existing data
- Migration requirements
- Performance
- Security
```

Not every category applies to every task; the agent should select relevant cases.

---

# 32. Implementation Workflow

After plan approval:

```text
1. Create checkpoint
2. Re-read target files
3. Verify assumptions
4. Modify only scoped files
5. Preserve project style
6. Add/update tests
7. Format code
8. Run static checks
9. Run targeted tests
10. Run regression tests
11. Run build
12. Review diff
13. Update graph
14. Update memory
```

---

# 33. Multi-Gate Verification

Use multiple validation gates.

## Gate 1: Structural

```text
- Files exist
- Imports resolve
- Modules are correct
- New files are in correct locations
```

## Gate 2: Dependency

```text
- Callers remain valid
- API contracts remain valid
- Dependencies are correct
```

## Gate 3: Static

```text
- Formatter
- Linter
- Type checker
- Static analyzer
```

## Gate 4: Unit Tests

```text
- Changed behavior
- Edge cases
- Regression tests
```

## Gate 5: Integration Tests

```text
- API
- Database
- Redis
- External services
```

## Gate 6: Build

```text
- Backend build
- Frontend build
- Container build
```

## Gate 7: Diff Review

```text
git diff
```

## Gate 8: Regression Analysis

```text
- Affected features
- Affected tests
- Affected APIs
```

Only after the relevant gates pass should the task be marked completed.

---

# 34. Automatic Debugging

When a test fails:

```text
Test Failure
     |
     v
Collect Error
     |
     v
Analyze Stack Trace
     |
     v
Locate Source
     |
     v
Traverse Dependency Graph
     |
     v
Retrieve Relevant Context
     |
     v
Root Cause Analysis
     |
     v
Generate Patch
     |
     v
Apply Patch
     |
     v
Run Failed Test
     |
     +---- PASS ----> Regression Tests
     |
     +---- FAIL ----> Re-analyze
```

Set a hard retry limit.

Recommended initial value:

```text
max_auto_fix_attempts = 3
```

If the limit is reached, stop and report the evidence instead of making endless modifications.

---

# 35. Root Cause Analysis

The agent should distinguish:

```text
Symptom
    |
    v
Immediate failure
    |
    v
Underlying cause
    |
    v
Systemic cause
```

Example:

```text
Symptom:
HTTP 500

Immediate:
Redis timeout

Underlying:
Connection pool unavailable

Systemic:
Pool initialized per request
```

The final fix should address the actual cause where practical rather than merely hiding the symptom.

---

# 36. Test Intelligence

The agent should understand existing tests.

For a changed feature:

```text
Changed Feature
      |
      v
Find Existing Tests
      |
      v
Analyze Coverage
      |
      v
Identify Missing Cases
      |
      v
Generate Tests
      |
      v
Run Tests
```

Example:

```text
Payment Retry

Existing:
- test_payment_success
- test_payment_failure

Missing:
- test_payment_retry
- test_retry_limit
- test_retry_backoff
```

---

# 37. Regression Testing

After targeted tests pass, determine whether broader tests are required.

Example:

```text
Authentication change

Targeted:
tests/auth/*

Potential regression:
tests/admin/*
tests/session/*
tests/api/*
```

The graph should help identify related test areas.

---

# 38. Git Integration

Git should be a first-class tool.

Before changes:

```text
git status
git diff
git branch
```

Create a checkpoint.

After changes:

```text
git diff
git status
```

Never silently overwrite unrelated developer changes.

Rollback should be possible for agent-generated modifications.

---

# 39. Code Fingerprints

Each file and symbol should have fingerprints such as:

```text
file_hash
ast_hash
symbol_hash
embedding
last_indexed_commit
```

When a file changes:

```text
Changed File
    |
    v
Fingerprint Difference
    |
    v
Re-index File
    |
    v
Update Symbols
    |
    v
Update Graph Edges
    |
    v
Update Feature
    |
    v
Update Embedding
```

This enables incremental indexing.

---

# 40. Incremental Repository Intelligence

Do not re-index the entire repository after every change.

Instead:

```text
File changed
    |
    v
Determine changed symbols
    |
    v
Determine changed relationships
    |
    v
Determine affected feature
    |
    v
Update only affected graph
```

This reduces:

- CPU usage
- indexing time
- embedding cost
- database work
- unnecessary model calls

---

# 41. File Watcher

A file watcher can keep repository intelligence synchronized.

```text
File System
    |
    v
Watcher
    |
    v
Changed File
    |
    +-- AST re-index
    +-- Symbol update
    +-- Dependency update
    +-- Embedding update
    +-- Feature update
```

For Git-based workflows, commit-level incremental indexing can also be used.

---

# 42. Repository History

Git history can enrich repository intelligence.

The system can associate:

```text
Feature
  |
  +-- Recent commits
  +-- Previous changes
  +-- Previous bugs
  +-- Changed files
  +-- Architectural decisions
```

This is especially useful when debugging code that has changed frequently.

---

# 43. Tool System

The model should have tools rather than unrestricted shell access.

Recommended tools:

```text
read_file
search_code
search_symbol
find_definition
find_references
list_directory

create_file
modify_file
delete_file

git_status
git_diff
git_log
git_checkpoint
git_rollback

run_tests
run_linter
run_formatter
run_typecheck
run_build

inspect_logs
inspect_database
inspect_runtime
```

Tool execution should be controlled by the orchestrator.

---

# 44. Deterministic Tools vs LLM Reasoning

Do not use the LLM for tasks that deterministic tools can perform better.

## Deterministic

```text
AST parsing
Git operations
File hashing
Dependency extraction
Testing
Formatting
Linting
Type checking
Building
File discovery
```

## LLM

```text
Understanding
Planning
Reasoning
Code generation
Architecture analysis
Root-cause analysis
Review
```

This separation improves reliability.

---

# 45. Permission Model

Use permission levels.

```text
Level 0:
Read-only

Level 1:
Create/edit files

Level 2:
Run tests/build

Level 3:
Git commit

Level 4:
Deployment
```

Production deployment should not be automatically permitted by default.

---

# 46. Sandbox Execution

Agent-generated commands should execute inside an isolated environment when possible.

Recommended:

```text
Docker sandbox
```

The sandbox can restrict:

- Filesystem access
- Network access
- Credentials
- Environment variables
- Process access
- Production systems

---

# 47. Security

The agent must protect:

```text
API keys
Passwords
Database credentials
Cloud credentials
Private tokens
SSH keys
Session tokens
```

Secrets should not be placed into model prompts unless strictly required and safely handled.

The system should also detect:

```text
Hardcoded secrets
Unsafe shell commands
SQL injection risks
Path traversal
Authentication bypass
Authorization errors
Insecure deserialization
Sensitive logging
```

---

# 48. Repository Brain Data Model

A conceptual database can contain:

```text
repositories
projects
modules
files
symbols
features
edges
tests
api_endpoints
database_entities
dependencies
documents
memories
decisions
bugs
tasks
plans
changes
test_runs
checkpoints
```

---

# 49. Recommended Initial Storage

Start simple.

```text
PostgreSQL
    |
    +-- Normal relational tables
    +-- pgvector for embeddings
    +-- Graph relationship tables
```

Example:

```text
nodes
edges
files
symbols
features
memories
```

A dedicated graph database such as Neo4j can be introduced later if graph scale and traversal requirements justify it.

Do not introduce unnecessary infrastructure at the beginning.

---

# 50. Semantic Search

Use embeddings for:

```text
- Code meaning
- Documentation
- Feature descriptions
- Architecture explanations
- Bug history
- Lessons
```

Do not rely on semantic search alone for exact code navigation.

Combine:

```text
Lexical Search
+
Symbol Search
+
AST
+
Graph Search
+
Semantic Search
```

---

# 51. Hybrid Retrieval

Recommended retrieval pipeline:

```text
User Task
    |
    +-- Keyword Search
    |
    +-- Symbol Search
    |
    +-- Semantic Search
    |
    +-- Feature Search
    |
    +-- Graph Traversal
    |
    v
Candidate Context
    |
    v
Context Ranking
    |
    v
Final Context
    |
    v
Nemotron
```

---

# 52. Context Ranking

Recommended priority:

```text
1. Directly related feature files
2. Directly related symbols
3. Functions called by target
4. Functions calling target
5. Related tests
6. Configuration
7. Related documentation
8. Previous bugs
9. Architectural decisions
10. Unrelated repository content
```

The ranking should be task-dependent.

---

# 53. Repository Summaries

Generate hierarchical summaries.

## Repository

```text
What is this project?
What are its major systems?
```

## Module

```text
What does this module do?
```

## Feature

```text
How does this feature work?
```

## File

```text
What is this file responsible for?
```

## Symbol

```text
What does this function/class do?
```

These summaries should be regenerated when their underlying code changes materially.

---

# 54. Feature Graph Example

```text
                         Authentication
                               |
          +--------------------+---------------------+
          |                    |                     |
        Login              Registration         Password Reset
          |
     +----+---------+
     |              |
   Router         Service
                    |
             +------+------+
             |             |
          User Repo      JWT
             |
           Database
             |
           Tests
```

A request about login should primarily traverse the `Login` subgraph rather than the entire repository.

---

# 55. Example User Workflow

Developer:

```text
"Change login timeout from 15 minutes to 30 minutes."
```

Agent:

```text
Feature:
Authentication -> Login

Relevant files:
- auth/config.py
- auth/service.py
- auth/token.py
- tests/auth/test_token.py

Potential impact:
- Access-token expiration
- Session behavior
- Authentication tests

Risks:
- Existing clients expecting previous expiration
- Refresh-token interaction

Plan:
1. Verify current timeout source.
2. Determine whether timeout is configurable.
3. Update configuration.
4. Update affected tests.
5. Run authentication tests.
6. Run related regression tests.
7. Review final diff.
```

Then implementation occurs only after the plan is validated.

---

# 56. Example Automatic Debugging Workflow

```text
pytest
   |
   v
FAILED test_login_expiration
   |
   v
Stack trace analysis
   |
   v
Locate token creation
   |
   v
Graph traversal
   |
   v
Retrieve auth context
   |
   v
Root cause:
expiration value overridden by environment configuration
   |
   v
Fix configuration handling
   |
   v
Run failed test
   |
   v
PASS
   |
   v
Run authentication regression suite
   |
   v
PASS
```

---

# 57. Change Verification Report

Every completed change should produce a machine-readable and human-readable result.

Example:

```text
Task:
Change login timeout

Feature:
Authentication / Login

Files changed:
5

Files created:
0

Tests added:
2

Tests executed:
31

Tests passed:
31

Tests failed:
0

Static analysis:
PASS

Type checking:
PASS

Build:
PASS

Regression:
PASS

Scope violations:
0

Risk:
Reviewed

Repository graph:
Updated

Memory:
Updated
```

---

# 58. Agent State Machine

```text
                    +----------+
                    |   TASK   |
                    +----+-----+
                         |
                         v
                    +----------+
                    | ANALYZE  |
                    +----+-----+
                         |
                         v
                    +----------+
                    | LOCATE   |
                    +----+-----+
                         |
                         v
                    +----------+
                    |  IMPACT  |
                    +----+-----+
                         |
                         v
                    +----------+
                    |   PLAN   |
                    +----+-----+
                         |
                         v
                    +----------+
                    |  REVIEW  |
                    +----+-----+
                         |
                         v
                    +----------+
                    | IMPLEMENT|
                    +----+-----+
                         |
                         v
                    +----------+
                    |  TEST    |
                    +----+-----+
                         |
                 +-------+-------+
                 |               |
               PASS             FAIL
                 |               |
                 v               v
             VERIFY            DEBUG
                 |               |
                 |               v
                 |            PATCH
                 |               |
                 |               v
                 |             TEST
                 |               |
                 +-------+-------+
                         |
                         v
                    +----------+
                    | COMPLETE |
                    +----------+
```

---

# 59. Autonomous Debugging Limits

Automatic fixes must be bounded.

Recommended:

```text
max_auto_fix_attempts = 3
max_scope_expansions = 1
max_unrelated_file_changes = 0
```

After repeated failures:

```text
STOP

Report:
- What failed
- What was attempted
- Evidence collected
- Suspected root cause
- Remaining uncertainty
```

Never let an agent endlessly modify the repository.

---

# 60. Important Design Rule: No Blind Refactoring

If the task is:

```text
Fix login timeout
```

the agent should not decide to:

```text
Rewrite authentication architecture
Refactor unrelated services
Rename dozens of files
Upgrade dependencies
```

unless the evidence shows that it is necessary and the scope is explicitly expanded.

Prefer:

```text
Smallest correct change.
```

---

# 61. Repository Learning Pipeline

The repository learning process should be:

```text
Repository
   |
   v
Parse
   |
   v
Extract
   |
   +-- Files
   +-- Symbols
   +-- Dependencies
   +-- APIs
   +-- Tests
   +-- Models
   |
   v
Build Graph
   |
   v
Generate Summaries
   |
   v
Detect Patterns
   |
   v
Create Candidate Rules
   |
   v
Verify
   |
   v
Store Repository Knowledge
```

---

# 62. Do Not Automatically Trust Legacy Code

Existing code is evidence, not necessarily a rule.

For example:

```text
Observed:
10 files use pattern X.
```

does not automatically mean:

```text
Rule:
Always use X.
```

Instead:

```text
Observed Pattern
      |
      v
Repeated Pattern
      |
      v
High Confidence
      |
      v
Candidate Rule
      |
      v
Verification / Approval
      |
      v
Project Rule
```

This prevents the agent from learning bad legacy patterns.

---

# 63. Model Roles

One model can be used for different roles through system instructions.

Recommended roles:

```text
Architect
Planner
Coder
Debugger
Tester
Reviewer
Security Reviewer
```

Example:

```text
Nemotron
   |
   +-- Architect prompt
   +-- Planner prompt
   +-- Coder prompt
   +-- Debugger prompt
   +-- Tester prompt
   +-- Reviewer prompt
```

Different roles should receive different context and tools.

---

# 64. Planner Context

Planner receives:

```text
Task
Feature graph
Architecture rules
Relevant source
Dependencies
Tests
Known bugs
Project constraints
```

Planner should not necessarily receive the entire repository.

---

# 65. Coder Context

Coder receives:

```text
Approved plan
Scoped files
Relevant source
Coding rules
Relevant symbols
Tests
Architecture decisions
```

---

# 66. Reviewer Context

Reviewer receives:

```text
Original task
Approved plan
Git diff
Affected feature
Tests
Architecture rules
```

The reviewer can determine whether the implementation matches the requested scope.

---

# 67. Debugger Context

Debugger receives:

```text
Error
Stack trace
Failed test
Relevant source
Dependency graph
Recent changes
Known bugs
Architecture
```

---

# 68. Tester Context

Tester receives:

```text
Changed feature
Changed symbols
Existing tests
Coverage
Impact analysis
```

This prevents every agent role from receiving the same huge context.

---

# 69. Token Optimization Strategy

Use all of the following:

```text
1. Feature-scoped retrieval
2. Graph traversal
3. Hierarchical summaries
4. Exact symbol retrieval
5. Semantic retrieval
6. Context ranking
7. Context deduplication
8. Incremental indexing
9. Cached summaries
10. Cached embeddings
11. Skill-specific context
12. Role-specific context
13. File fingerprints
14. Task scope locks
```

The objective is not simply:

```text
Use a larger context.
```

The objective is:

```text
Use the smallest context that contains enough evidence to make the correct decision.
```

---

# 70. Recommended Technology Stack

## Model

```text
Nemotron 3 Ultra
```

## Agent Runtime

```text
Python
```

## API

```text
FastAPI
```

## Repository Parsing

```text
Tree-sitter
Python AST
Language-specific parsers where useful
```

## Database

```text
PostgreSQL
```

## Vector Search

```text
pgvector
```

## Graph

Initial:

```text
PostgreSQL graph tables
```

Possible future:

```text
Neo4j
```

## Search

```text
ripgrep
symbol index
semantic search
graph traversal
```

## Git

```text
native git
or GitPython
```

## Execution

```text
Docker sandbox
```

## Testing

Project-dependent, for example:

```text
pytest
ruff
mypy
pyright
eslint
tsc
```

## File Watching

```text
watchdog
```

---

# 71. Suggested Repository Structure for the Agent Platform

```text
repo-agent/
|
+-- agent/
|   +-- orchestrator/
|   +-- planner/
|   +-- coder/
|   +-- debugger/
|   +-- tester/
|   +-- reviewer/
|
+-- intelligence/
|   +-- repository/
|   +-- feature/
|   +-- architecture/
|   +-- dependency/
|   +-- context/
|
+-- indexing/
|   +-- ast/
|   +-- symbols/
|   +-- imports/
|   +-- tests/
|   +-- documentation/
|
+-- retrieval/
|   +-- semantic/
|   +-- lexical/
|   +-- graph/
|   +-- ranking/
|
+-- memory/
|   +-- repository/
|   +-- decisions/
|   +-- bugs/
|   +-- tasks/
|   +-- lessons/
|
+-- tools/
|   +-- filesystem/
|   +-- git/
|   +-- testing/
|   +-- shell/
|   +-- build/
|
+-- execution/
|   +-- sandbox/
|   +-- validation/
|
+-- model/
|   +-- nemotron/
|
+-- skills/
|   +-- repository-intelligence/
|   +-- planning/
|   +-- implementation/
|   +-- debugging/
|   +-- testing/
|   +-- verification/
|   +-- git/
|
+-- api/
|
+-- storage/
|
+-- tests/
|
+-- README.md
```

---

# 72. Recommended Development Phases

## Phase 1 — Repository Intelligence

Build:

```text
- Repository scanner
- AST parser
- File index
- Symbol index
- Import graph
- Basic search
```

## Phase 2 — Feature Intelligence

Build:

```text
- Feature nodes
- Feature-to-file relationships
- Feature-to-symbol relationships
- Feature-to-test relationships
- Feature documentation
```

## Phase 3 — Nemotron Agent

Build:

```text
- Model integration
- Tool calling
- Planning
- Code generation
- File editing
```

## Phase 4 — Verification

Build:

```text
- Test execution
- Lint
- Type checking
- Build
- Diff review
- Rollback
```

## Phase 5 — Memory

Build:

```text
- Architecture decisions
- Bug memory
- Lessons
- Project-specific rules
```

## Phase 6 — Autonomous Debugging

Build:

```text
- Failure detection
- Root cause analysis
- Patch generation
- Test/retry loop
- Rollback
```

## Phase 7 — Advanced Optimization

Build:

```text
- Incremental indexing
- Graph-aware retrieval
- Context compression
- Hierarchical summaries
- Parallel analysis
- Advanced ranking
```

---

# 73. Final Target Architecture

```text
                           DEVELOPER
                               |
                               v
                    +-----------------------+
                    |   Agent Orchestrator  |
                    +-----------+-----------+
                                |
                +---------------+---------------+
                |               |               |
                v               v               v
        +-------------+  +-------------+  +-------------+
        | Feature     |  | Repository  |  | Memory      |
        | Graph       |  | Search      |  | System      |
        +------+------+  +------+------+  +------+------+
               |                |                |
               +----------------+----------------+
                                |
                                v
                    +-----------------------+
                    |   Context Manager     |
                    |                       |
                    | Ranking / Compression |
                    | Scope / Deduplication |
                    +-----------+-----------+
                                |
                                v
                    +-----------------------+
                    |    Nemotron 3 Ultra   |
                    |                       |
                    | Architect / Planner    |
                    | Coder / Debugger      |
                    | Tester / Reviewer     |
                    +-----------+-----------+
                                |
                                v
                    +-----------------------+
                    |   Tool Orchestrator   |
                    +-----------+-----------+
                                |
             +------------------+------------------+
             |                  |                  |
             v                  v                  v
         FILE SYSTEM           GIT              TESTS
             |                  |                  |
             +------------------+------------------+
                                |
                                v
                    +-----------------------+
                    | Validation Pipeline    |
                    +-----------+-----------+
                                |
                    +-----------+-----------+
                    |                       |
                   PASS                   FAIL
                    |                       |
                    v                       v
              Update Graph              Debug
              Update Memory                |
                    |                     Fix
                    |                      |
                    +----------<-----------+
```

---

# 74. Final Operating Principle

The system should behave like this:

```text
Understand first.
Search intelligently.
Follow the feature graph.
Retrieve only relevant context.
Respect project rules.
Analyze dependencies.
Calculate impact.
Plan before changing.
Review the plan.
Modify only the required scope.
Run tests.
Analyze failures.
Fix verified problems.
Run regression checks.
Review the final diff.
Update repository knowledge.
Remember verified lessons.
Never blindly trust memory.
Never modify unrelated features.
Never declare success without verification.
```

The end goal is not a model that "knows every file."

The goal is a **repository-aware autonomous engineering system** where Nemotron can dynamically navigate a persistent graph of the project and retrieve exactly the knowledge it needs for the current task.

This architecture allows the same model to work effectively on small repositories and progressively scale toward very large codebases without putting the entire repository into every prompt.
