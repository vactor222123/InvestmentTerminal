# InvestmentTerminal — Project Continuation

**Document role:** Durable project handoff and execution checkpoint  
**Update rule:** MUST be updated after every completed Task  
**Current repository:** `vactor222123/InvestmentTerminal`  
**Current branch:** `develop`  
**Current baseline:** `b81fe98`  
**Current phase:** Post-Sprint-31 audited hardening / production maturity  
**Current next action:** Sprint 32 Task 2 — SQLite Operational Inventory

---

## 1. Purpose

This document exists so InvestmentTerminal work can continue in a new ChatGPT
conversation without relying on the previous conversation history.

It records:

- the current verified repository baseline;
- why the project is in its current phase;
- completed hardening work;
- the latest architecture/product audit;
- the approved next-sprint direction;
- the exact next Task;
- deferred work;
- working protocol;
- known failure patterns;
- the mandatory handoff/update procedure.

This file is a living checkpoint, not a historical changelog.

After every completed Task, update this file in the same Task/closure commit or
in the immediately following checkpoint commit.

---

## 2. Resume Protocol for a New Conversation

Start a new ChatGPT conversation with:

```text
Continue InvestmentTerminal.
Read PROJECT_CONTINUATION.md from the develop branch first.
Treat it as the current handoff checkpoint.
Then verify the recorded baseline against GitHub and continue from
"Current Next Action" using the Working Protocol in that file.
```

The assistant must then:

```text
1. Read PROJECT_CONTINUATION.md from develop.
2. Verify current develop HEAD.
3. If HEAD differs from the recorded baseline, inspect the commits after the
   recorded baseline before changing anything.
4. Read the current versions of every file that the next Task may modify.
5. Perform a focused impact audit.
6. Continue only from the verified repository state.
```

Never reconstruct project state from memory when this document and GitHub are
available.

---

## 3. Current Project Phase

The project has moved beyond initial architecture construction.

Current development mode:

```text
core architecture built
→ capital / post-sprint audit
→ identify concrete gaps
→ audited hardening sprint
→ production maturity
→ later return to feature/intelligence expansion
```

Current Sprints are therefore primarily **audit-driven hardening work**.

They are not arbitrary cleanup. Each Sprint should close a coherent class of
risk discovered by audit before adding more product surface.

Expected long-term path:

```text
audited hardening
→ production maturity
→ security / multi-instance maturity where justified
→ renewed intelligence/product feature expansion
```

---

## 4. Stable Authority Hierarchy

The system must preserve:

```text
market / external data
→ deterministic analysis
→ Review Package
→ immutable History
→ explicit verified History-to-Knowledge ingestion
→ versioned Knowledge
→ grounded generation
→ strict grounding validation
→ ADMISSIBLE generated evidence
→ durable grounded-generation persistence
```

Generated evidence is downstream evidence.

It MUST NOT automatically become History or Knowledge.

Provider usage/cost accounting remains a parallel operational boundary.

Historical source-of-truth rule:

```text
Archived Review Package JSON
    canonical historical evidence

manifest.jsonl
    append-only navigation index

history.db
    rebuildable structured projection
```

---

## 5. Completed Hardening Baseline

### Sprint 31 — Evidence Integrity & Delivery Hardening

Status:

```text
CLOSED
closure baseline: develop @ 2026e7b
closure CI: GREEN
```

Completed:

```text
31.1 Deep immutable grounded evidence
31.2 Strict JSON persistence boundary
31.3 Architecture dependency guards
31.4 Documentation authority reconciliation
31.5 Dependency reproducibility baseline
31.6 GitHub Actions CI quality gate
```

Sprint 31 established:

- deep nested immutability of persisted grounded generation/trace JSON;
- detached external serialization;
- strict JSON-compatible persistence values;
- rejection of non-finite numbers and non-string JSON object keys;
- expanded executable architecture dependency guards;
- canonical root documentation authority;
- Python 3.13.x dependency-resolution family;
- `requirements.in` and `requirements-dev.in`;
- pinned pip/pip-tools compiler toolchain;
- committed hash-locked runtime/dev dependencies;
- cross-platform dependency ownership;
- GitHub Actions clean Linux CI;
- `--require-hashes` dependency installation;
- focused dependency and architecture contract tests;
- full pytest CI regression;
- `git diff --check`;
- hermetic tests that do not rely on developer-local personal portfolio data.

Verified local regression immediately before Sprint 31 closure:

```text
2190 passed
3 skipped
1 warning
0 failed
```

The closure commit also passed clean GitHub Actions.

---

## 6. Important Sprint 31 Failure Lessons

These are mandatory engineering lessons, not optional notes.

### 6.1 Do not over-pin the Python patch release without need

Initial dependency work required Python `3.13.14` while the established local
environment used `3.13.7`.

Correct contract:

```text
Python 3.13.x
```

Use an exact patch only if a real technical compatibility requirement exists.

### 6.2 A lock generated on one OS can expose hidden platform extras

`fastapi[standard]` caused the Windows-generated lock to request Linux-only
`uvloop` during strict Linux installation.

Correct ownership became:

```text
fastapi    → framework runtime
uvicorn    → explicit ASGI server runtime
httpx      → explicit development/test TestClient transport
```

Do not hide important direct dependencies behind convenience extras when they
damage cross-platform reproducibility.

### 6.3 Tests must be hermetic

Six tests passed locally only because a developer-local
`data/portfolios/current_portfolio.json` existed.

Correct solution:

```text
tracked current_portfolio.example.json
+ explicit --portfolio path
```

Never make clean CI depend on personal/local untracked data.

### 6.4 Strict CI should be fixed, not weakened

When `--require-hashes` exposed a real dependency problem, the solution was to
fix dependency ownership.

Do not remove strictness merely to make CI green.

### 6.5 Contract changes require consumer/fixture/persistence audit

Deep immutability changes exposed equality/mutation assumptions in tests.

Before changing established data contracts, inspect:

```text
models
→ serializers
→ persistence
→ repositories
→ application services
→ fixtures/tests
→ CLI/API consumers
```

---

## 7. Post-Sprint-31 Audit

Audit baseline:

```text
develop @ 2026e7b
```

Conclusion:

The main remaining bottleneck is no longer evidence correctness,
architecture dependency direction, or reproducible CI.

The next critical gap is **production deployment and operational resilience**.

Observed production characteristics:

- `create_app()` initializes operational SQLite stores directly;
- runtime config carries separate Knowledge, provider usage/cost, and grounded
  generation database paths;
- there is no explicit persistent data-root contract;
- there is no backup-root contract;
- there is no repository-owned backup/restore workflow;
- there is no explicit WAL-safe operational backup primitive;
- there is no validated restore/activation workflow;
- there is no explicit FastAPI lifespan/resource shutdown contract;
- there is no container/volume deployment contract;
- there is no repository-owned TLS/reverse-proxy topology contract;
- there is no container CI smoke test.

Therefore the approved next Sprint is:

```text
Sprint 32 — Production Deployment & Operational Resilience
```

---

## 8. Sprint 32 Approved Plan

### 32.1 Runtime Filesystem Contract — CLOSED

Closure:

```text
commit: b81fe98
CI: GREEN
```

Established an optional strict runtime data-root boundary without silently relocating existing databases. Production validates configured database confinement before operational SQLite initialization, rejects path escape, and prepares writable operational parents while leaving missing Knowledge data to readiness semantics.

Goals:

```text
persistent data root
DB path ownership/confinement
read/write validation
runtime filesystem invariants
```

Do NOT begin with Docker.

First establish what state is persistent and where it is allowed to live.

### 32.2 SQLite Operational Inventory

Explicitly enumerate operational SQLite stores, ownership, criticality,
rebuildability, and backup requirements.

### 32.3 Consistent SQLite Backup Primitive

Required properties:

```text
SQLite backup API
WAL-safe behavior
temporary destination
validation
atomic publication
failure cleanup
```

Do not implement backup as a naive live `.db` file copy.

### 32.4 Backup Service

Cover the operational stores according to their authority/rebuildability
contract and produce deterministic backup metadata.

### 32.5 Restore Validation

Restore must fail closed.

Never overwrite/activate a live database before validating the candidate backup
and expected schema/identity.

### 32.6 Backup / Restore CLI

Provide explicit operator workflows while preserving domain boundaries.

CLI must orchestrate; it must not own SQLite internals.

### 32.7 FastAPI Lifespan Contract

Move startup/shutdown resource lifecycle into explicit lifespan ownership where
appropriate.

Verify initialization and cleanup behavior.

### 32.8 Runtime Deployment Layout

Define:

```text
read-only application/code
writable persistent data
backup destination
configuration boundary
secret boundary
```

### 32.9 Container Baseline

Only after filesystem/persistence contracts are explicit:

```text
Dockerfile
locked dependency install
non-root execution
healthcheck
persistent volume contract
```

### 32.10 Deployment Security Contract

Define responsibility for:

```text
reverse proxy
TLS termination
secret injection
trusted network assumptions
```

Do not add application-level TLS merely for appearance if the deployment
boundary should own TLS.

### 32.11 CI Container Smoke Test

Build and start the production image with fixture configuration, then verify
health/readiness.

### 32.12 Real Operational Resilience E2E

Required scenario:

```text
write durable data
→ backup
→ damage/replace working database
→ validate restore candidate
→ restore
→ restart
→ exact readback
```

### 32.13 Sprint 32 Closure

Reconcile:

```text
docs
project inventory
CI
full regression
PROJECT_CONTINUATION.md
```

---

## 9. Current Next Action

```text
Sprint 32 Task 2 — SQLite Operational Inventory
```

Before writing Task 32.2:

```text
1. Verify develop HEAD against b81fe98 or inspect every later commit.
2. Search every SQLite store/repository in the repository.
3. Identify which databases are production-operational versus historical
   projection or other rebuildable state.
4. For each store, determine authority, owner, rebuildability, criticality,
   write behavior, WAL/journal behavior, and backup/restore requirement.
5. Read schema initialization/migration code and relevant persistence tests.
6. Read production composition and runtime filesystem contract.
7. Do not implement backup code in 32.2.
8. Produce one explicit operational inventory/contract that 32.3 can consume.
```

Task 32.2 is a classification/ownership Task. It must prevent the later backup
primitive from treating all SQLite files as if they had the same authority or
recovery semantics.

---

## 10. Deferred Areas

Do not silently pull these into Sprint 32 unless a Task audit proves they are
required for the operational-resilience contract:

- distributed/shared rate limiting;
- richer authorization/scopes;
- multi-worker shared admission state;
- retry jitter;
- proactive provider throttling;
- streaming responses;
- additional provider adapters;
- provider pricing synchronization;
- automatic/scheduled History-to-Knowledge ingestion;
- semantic/vector retrieval;
- entailment/contradiction detection;
- generated-evidence promotion governance;
- autonomous portfolio actions;
- broker execution.

A likely later direction after operational maturity is:

```text
Production Security & Multi-Instance Controls
```

followed eventually by renewed intelligence/product expansion.

---

## 11. Working Protocol

This protocol applies to every Task.

### Before changes

```text
1. Verify current develop HEAD.
2. Read current GitHub versions of every file that may change.
3. Search the target subsystem and its direct consumers.
4. Audit relevant tests and fixtures.
5. Identify architecture/authority constraints.
6. Do not assume old chat snippets still match the repository.
```

### Package design

- Make one coherent Task at a time.
- Prefer the smallest complete change that closes the audited gap.
- Do not mix unrelated refactors.
- Preserve established authority direction.
- Do not weaken fail-closed behavior to satisfy tests.
- Do not invent infrastructure before defining its contract.
- When delivering files manually, provide complete changed files rather than
  ambiguous partial patches.

### Validation

At minimum:

```text
focused tests
→ full python -m pytest -q
→ git diff --check
```

For delivery/runtime changes also use the relevant clean CI or operational E2E.

### Commit flow

```text
implement
→ focused tests
→ full tests
→ inspect diff
→ commit
→ push develop
→ provide SHA
→ verify actual GitHub commit
→ verify actual GitHub Actions result
→ only then mark Task CLOSED
```

A local green suite alone does not close a CI-affecting Task.

---

## 12. Mandatory PROJECT_CONTINUATION.md Update Rule

**This file MUST be updated after every completed Task.**

A Task is not fully closed until its handoff state is recorded here.

After each Task, update at least:

```text
Current baseline
Current phase
Current next action
Completed Task list
What changed
Important architectural decisions
New tests / CI guarantees
New failure lessons
Deferred consequences
Sprint plan status
```

If the Task changes the future plan, update the remaining Task list too.

### Required Task checkpoint format

Append/update a concise entry:

```text
Task: <sprint.task + title>
Status: CLOSED
Commit: <full or short SHA>
CI: <GREEN / not applicable>
Changed:
- ...

Decisions:
- ...

Tests/guarantees:
- ...

Lessons:
- ...

Next:
<sprint.task + title>
```

Do not let this file become a chronological dump of every implementation detail.
Keep only the information necessary to resume correctly and understand why the
current path was chosen.

At Sprint closure, perform a full reconciliation of this document rather than
only appending the final Task.

---

## 13. Documentation Authority and Handoff Relationship

Canonical repository documents remain:

```text
Architecture.md
DataModel.md
Roadmap.md
NEXT_STEPS.md
README.md
CHANGELOG.md
```

`PROJECT_CONTINUATION.md` is the canonical **execution/handoff checkpoint**.

It does not replace Architecture or DataModel.

Its job is to answer:

```text
Where are we?
Why are we here?
What was verified?
What failed before and what did we learn?
What exactly comes next?
How must the next Task be executed?
```

`docs/AI_CONTEXT.md` is supporting AI context and should point to this handoff
document.

---

## 14. Checkpoint Synchronization

```text
Checkpoint: durable continuation mechanism established
Status: CLOSED
Commit: 30a28ac
CI: GREEN
Changed:
- added PROJECT_CONTINUATION.md;
- linked continuation workflow from README/NEXT_STEPS/AI context;
- made handoff updates mandatory after every completed Task.

Decisions:
- PROJECT_CONTINUATION.md is the canonical execution/handoff checkpoint;
- architecture/data-model authority remains in the canonical architecture docs;
- every Task Definition of Done now includes checkpoint reconciliation.

Tests/guarantees:
- clean GitHub Actions run succeeded on the checkpoint commit.

Lessons:
- handoff state must refer to an already verified commit, not a future commit
  identity that does not yet exist.

Next:
Sprint 32 Task 1 — Runtime Filesystem Contract
```

---

## 15. Sprint 32 Task Checkpoints

### Task 32.1 — Runtime Filesystem Contract

```text
Status: CLOSED
Commit: b81fe98
CI: GREEN

Changed:
- added optional INVESTMENT_TERMINAL_RUNTIME_DATA_ROOT;
- added explicit runtime filesystem ownership/confinement validation;
- production validates the filesystem contract before SQLite store initialization;
- added focused filesystem/configuration tests and runtime filesystem documentation.

Decisions:
- the runtime data root is opt-in for backward compatibility;
- configuring a root does not relocate existing database paths;
- when configured, all three production runtime database paths must resolve
  inside the root;
- path/symlink escape fails closed;
- writable operational parents may be prepared by the contract;
- the filesystem contract does not create a missing Knowledge database.

Tests/guarantees:
- focused runtime filesystem/config/production tests passed before commit;
- full regression passed before commit;
- GitHub Actions run #7 completed successfully.

Lessons:
- filesystem ownership must be established before container/volume work;
- strict production confinement can be introduced without a hidden data migration.

Next:
Sprint 32 Task 2 — SQLite Operational Inventory
```

---

## 16. Current Checkpoint Summary

```text
Repository: vactor222123/InvestmentTerminal
Branch: develop
Baseline: b81fe98
Sprint 31: CLOSED / CI GREEN
Development mode: audit-driven hardening / production maturity
Approved Sprint: Sprint 32 — Production Deployment & Operational Resilience
Current next action: 32.2 SQLite Operational Inventory
```

Checkpoint synchronization:

```text
PROJECT_CONTINUATION.md introduced: develop @ 30a28ac
CI: GREEN
```

Task 32.1 is closed on verified CI. Continue with Task 32.2 only from the
verified `b81fe98` baseline, or audit every later commit before proceeding.
