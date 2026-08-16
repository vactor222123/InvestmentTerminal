# InvestmentTerminal — Project Continuation

**Document role:** Durable project handoff and execution checkpoint  
**Update rule:** MUST be updated after every completed Task  
**Current repository:** `vactor222123/InvestmentTerminal`  
**Current branch:** `develop`  
**Current baseline:** `5e846ce`  
**Current phase:** Post-Sprint-31 audited hardening / production maturity  
**Current next action:** Sprint 32 Task 5 — Restore Validation

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

### 32.2 SQLite Operational Inventory — CLOSED

Closure:

```text
commit: ab53d8e
CI: GREEN
```

Established a neutral cross-domain SQLite persistence inventory with four
classified boundaries:

```text
History SQLite
→ rebuildable projection
→ upstream archived Review Packages remain authority

Knowledge SQLite
→ rebuildable derived state
→ backup for availability

Provider usage/cost SQLite
→ durable operational record
→ backup required

Grounded-generation SQLite
→ durable generated evidence
→ backup required
```

The inventory intentionally does not implement backup or restore I/O.

Explicitly enumerate operational SQLite stores, ownership, criticality,
rebuildability, and backup requirements.

### 32.3 Consistent SQLite Backup Primitive — CLOSED

Closure:

```text
commit: 2299a6f
CI: GREEN
```

Established a cross-domain file-backed SQLite backup primitive with:

```text
inventory identity validation
→ SQLite Connection.backup()
→ WAL-safe committed-state snapshot
→ temporary destination in target directory
→ PRAGMA quick_check
→ backup-file fsync
→ atomic os.replace publication
→ directory sync where supported
→ partial-output cleanup on failure
```

Windows-specific durability contract:

```text
close all SQLite handles before os.replace
reopen completed temp backup as r+b before os.fsync
```

The `r+b` access mode is required because Windows' CRT-backed `os.fsync`
requires a descriptor with write access; it does not modify backup content.

Existing destinations are protected by default and require explicit
`overwrite=True` for replacement.

Do not implement backup as a naive live `.db` file copy.

### 32.4 Backup Service — CLOSED

Closure:

```text
commit: 5e846ce
CI: GREEN
```

Established an all-or-nothing runtime SQLite backup-set service for exactly the
three runtime-managed persistence boundaries:

```text
KNOWLEDGE_SQLITE@1
PROVIDER_USAGE_COST_SQLITE@1
GROUNDED_GENERATION_SQLITE@1
```

History SQLite remains excluded from the grounded-AI runtime backup set.

Backup-set contract:

```text
explicit backup_root
→ deterministic UTC backup-set identity
→ staging directory
→ three Task-32.3 SQLite snapshots
→ deterministic metadata.json
→ atomic set-directory publication
→ backup-root sync
```

Any database-backup or metadata failure before publication removes staging and
leaves no final backup set. Existing final set directories are never
overwritten.

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
Sprint 32 Task 5 — Restore Validation
```

Before writing Task 32.5:

```text
1. Verify develop HEAD against 5e846ce or inspect every later commit.
2. Read runtime_backup_service.py, sqlite_backup.py, and sqlite_inventory.py.
3. Read the schema/version initialization contract of each runtime-managed DB.
4. Define a fail-closed backup-set metadata parser/validator.
5. Require exactly the expected three runtime boundary identities; reject
   missing, duplicate, unknown, or History entries.
6. Validate backup files before any live-path mutation.
7. Validate SQLite storage integrity plus expected schema/version/identity for
   each boundary.
8. Detect metadata/file mismatch and tampering where the existing metadata
   contract can support it; do not invent unverifiable guarantees.
9. Keep restore activation/replacement out of 32.5.
10. Add focused tests for missing/extra files, malformed metadata, wrong
    boundary mapping, corrupt SQLite, incompatible schema/version, and a valid
    complete candidate.
```

Task 32.5 owns candidate validation only. It must produce a validated restore
candidate or fail closed without mutating live databases. Operator activation
and CLI orchestration remain later Tasks.

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

### Task 32.2 — SQLite Operational Inventory

```text
Status: CLOSED
Commit: ab53d8e
CI: GREEN

Changed:
- added neutral `investment_terminal.persistence` package;
- added executable SQLite persistence inventory;
- classified History, Knowledge, provider usage/cost, and grounded-generation
  SQLite boundaries;
- added focused inventory contract tests and operational documentation.

Decisions:
- common SQLite/WAL mechanics do not imply common authority;
- History SQLite is rebuildable projection, not historical authority;
- Knowledge SQLite is rebuildable derived state and may be backed up for
  availability;
- provider ledger and grounded generations are durable records/evidence and
  require backup if their durability guarantee is to hold;
- History SQLite is outside grounded-AI production runtime management.

Tests/guarantees:
- focused inventory tests passed before commit;
- full regression passed before commit;
- GitHub Actions run #9 completed successfully.

Lessons:
- backup policy must be driven by persistence authority classification, not by
  file extension or storage engine alone.

Next:
Sprint 32 Task 3 — Consistent SQLite Backup Primitive
```

---

### Task 32.3 — Consistent SQLite Backup Primitive

```text
Status: CLOSED
Commit: 2299a6f
CI: GREEN

Changed:
- added generic cross-domain SQLite backup primitive;
- used SQLite Connection.backup() instead of raw live-file copying;
- added WAL-consistency and storage-integrity validation;
- added atomic publication, overwrite policy, and failure cleanup;
- added Windows-compatible file fsync behavior;
- added focused backup/WAL/Windows regression tests and documentation.

Decisions:
- backup requests must identify a known SQLite persistence boundary;
- only file-backed SQLite sources/destinations are supported;
- source and destination must differ;
- existing destination replacement requires explicit overwrite=True;
- PRAGMA quick_check is storage-level validation only;
- schema/identity restore validation remains Task 32.5;
- all SQLite handles close before atomic replacement.

Tests/guarantees:
- initial Windows run exposed read-only descriptor fsync incompatibility;
- fixed _sync_file() to reopen completed backup as r+b;
- full local regression after fix: 2218 passed, 4 skipped, 1 warning;
- GitHub Actions run #11 completed successfully.

Lessons:
- Windows filesystem durability requires auditing descriptor access mode as well
  as file-handle closure;
- os.fsync on Windows must not be assumed to accept a read-only descriptor;
- cross-platform persistence code needs explicit Windows regression coverage.

Next:
Sprint 32 Task 4 — Backup Service
```

---

### Task 32.4 — Backup Service

```text
Status: CLOSED
Commit: 5e846ce
CI: GREEN

Changed:
- added runtime SQLite backup-set orchestration;
- scoped the service to Knowledge, provider usage/cost, and grounded generation;
- added explicit backup_root ownership;
- added deterministic UTC backup-set naming and metadata;
- added staging plus atomic set-directory publication;
- added all-or-nothing pre-publication failure cleanup.

Decisions:
- History SQLite is not part of the grounded-AI runtime backup set;
- backup destination is explicit and independent of runtime_data_root;
- a backup set is valid only when all three runtime snapshots and metadata are
  complete;
- existing final backup-set directories are never overwritten;
- restore validation/activation remains outside Task 32.4.

Tests/guarantees:
- focused backup-service tests passed before commit;
- full regression passed before commit;
- GitHub Actions run #13 completed successfully.

Lessons:
- backup atomicity must exist at the set level as well as at the individual
  SQLite-file level;
- live-data placement and backup-destination placement are separate deployment
  concerns and should not be coupled implicitly.

Next:
Sprint 32 Task 5 — Restore Validation
```

---

## 16. Current Checkpoint Summary

```text
Repository: vactor222123/InvestmentTerminal
Branch: develop
Baseline: 5e846ce
Sprint 31: CLOSED / CI GREEN
Development mode: audit-driven hardening / production maturity
Approved Sprint: Sprint 32 — Production Deployment & Operational Resilience
Current next action: 32.5 Restore Validation
```

Checkpoint synchronization:

```text
PROJECT_CONTINUATION.md introduced: develop @ 30a28ac
CI: GREEN
```

Tasks 32.1–32.4 are closed on verified CI. Continue with Task 32.5 only from
the verified `5e846ce` implementation baseline, or audit every later commit
before proceeding.
