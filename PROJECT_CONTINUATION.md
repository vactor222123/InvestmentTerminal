# InvestmentTerminal — Project Continuation

**Document role:** Durable project handoff and execution checkpoint  
**Update rule:** MUST be updated after every completed Task  
**Current repository:** `vactor222123/InvestmentTerminal`  
**Current branch:** `develop`  
**Current baseline:** `b4c26a7`  
**Current phase:** Post-Sprint-31 audited hardening / production maturity  
**Current next action:** Sprint 32 Task 12 — Real Operational Resilience E2E

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

### 32.5 Restore Validation — CLOSED

Closure:

```text
commit: cb8bd40
CI: GREEN
```

Established fail-closed validation of complete runtime SQLite backup sets before
any live database mutation.

Validation contract:

```text
backup-set metadata identity/schema
→ directory ↔ backup_set_id consistency
→ exact three runtime boundaries
→ inventory classification match
→ exact backup filenames / no path traversal
→ size metadata match
→ read-only immutable SQLite validation
→ PRAGMA quick_check
→ required tables
→ boundary-specific schema metadata/version
→ ValidatedRuntimeSQLiteRestoreCandidate
```

Candidate SQLite files are opened read-only with `mode=ro&immutable=1`; domain
store `initialize()` methods are never called during validation.

The validator tolerates SQLite-managed WAL/SHM sidecars that may already exist
from backup/test SQLite activity, while arbitrary extra artifacts still fail
closed.

Restore activation remains outside Task 32.5.

### 32.6 Backup / Restore CLI — CLOSED

Closure:

```text
commit: 8a22b7b
CI: GREEN
```

Established a thin operator CLI with:

```text
backup
validate
restore
```

The CLI owns argument parsing, explicit operator intent, service orchestration,
and human/JSON output only.

Restore activation is implemented beneath the CLI in a dedicated persistence
service:

```text
validate backup set
→ create WAL-safe rollback snapshots of existing live DBs
→ stage validated candidate DBs
→ checkpoint live WAL
→ switch target journal_mode to DELETE
→ close SQLite connection
→ remove stale WAL/SHM sidecars
→ replace live DBs
→ compensating rollback on partial activation failure
```

Actual restore requires explicit `--confirm-offline`.

A prerequisite connection-lifecycle defect was also corrected in
`KnowledgeSQLiteStore`: short-lived helper operations now explicitly close
SQLite connections using `closing(self.connect())`, matching the already
established provider-ledger and grounded-generation store pattern.

### 32.7 FastAPI Lifespan Contract — CLOSED

Closure:

```text
commit: 3b069e6
CI: GREEN
```

Production application construction is now side-effect free with respect to
operational persistence.

`production.create_app()` performs configuration and object composition only.
The explicit FastAPI/ASGI lifespan owns startup side effects:

```text
runtime filesystem prepare
→ provider usage/cost SQLite initialize
→ grounded-generation SQLite initialize
→ accept requests
```

Startup failure propagates out of lifespan and prevents successful application
startup.

Knowledge remains an external prerequisite and is not created or migrated by
the server lifespan.

The current production graph owns no long-lived SQLite connections or provider
HTTP client handles, so shutdown does not invent fake cleanup. The explicit
shutdown boundary remains the required ownership point for future long-lived
resources.

Production tests that depend on startup state now enter lifespan explicitly via
`with TestClient(app)`.

### 32.8 Runtime Deployment Layout — CLOSED

Closure:

```text
commit: 543e737
CI: GREEN
```

Established a canonical deployment topology with five independent roots:

```text
/application   read-only application/code
/runtime       persistent writable live runtime state
/backups       persistent independent backup storage
/config        read-only non-secret deployment configuration
/secrets       read-only deployment-managed secret boundary
```

Canonical runtime SQLite paths are:

```text
/runtime/knowledge.db
/runtime/operational/provider_usage_cost.db
/runtime/operational/grounded_generations.db
```

The deployment-layout contract is descriptive only. It validates absolute,
independent roots and projects canonical non-secret runtime path environment,
but does not create directories, move databases, read secrets, start the
server, or run backup/restore.

Backward compatibility remains unchanged:

```text
INVESTMENT_TERMINAL_RUNTIME_DATA_ROOT remains optional
explicit legacy database paths remain valid
no database is silently relocated
```

The backup root is explicitly independent from the live runtime-data root.

### 32.9 Container Baseline — CLOSED

Closure:

```text
commit: f0a4b64
CI: GREEN
```

Established a minimal production container baseline consuming the 32.8
deployment layout:

```text
python:3.13-slim
→ runtime requirements.lock installed with --require-hashes
→ non-root investment-terminal user
→ /application made read-only
→ /runtime and /backups declared as persistent volume boundaries
→ /config and /secrets created as deployment mount points
→ /health liveness healthcheck
→ canonical one-worker server CLI
```

The build context excludes local `.env`, SQLite/WAL/SHM files, runtime data,
backup data, test/dev payload, and development lock files.

The image does not bake Knowledge or real secrets.

Local Docker build was not executed because Docker CLI was unavailable in the
developer environment. This is recorded as an unverified local build step, not
as a passing image build. Real image build/start verification remains Task
32.11.

### 32.10 Deployment Security Contract — CLOSED

Closure:

```text
commit: 1c6fe62
CI: GREEN
```

Established explicit deployment-security ownership:

```text
public client
→ HTTPS
→ reverse proxy / platform ingress
→ private HTTP
→ Investment Terminal container
```

TLS, certificate policy, and HSTS remain owned by the TLS termination boundary.

Application API-key authentication remains mandatory defense in depth behind the
proxy boundary.

The production server CLI now explicitly launches Uvicorn with:

```text
proxy_headers=False
```

so arbitrary `X-Forwarded-*` metadata is not implicitly trusted.

Canonical exposure policy:

```text
/health       liveness; no app auth; deployment-private where practical
/ready        readiness/operator endpoint; deployment-private
/openapi.json operator/developer schema; deployment-private
/v1/*         API-key authentication required
```

Secret authority remains single-source:

```text
deployment secret manager / environment injection
→ process environment
→ existing runtime config
```

No automatic `/secrets/...` loader or application-level TLS stack was added.

### 32.11 CI Container Smoke Test — CLOSED

Closure:

```text
commit: b4c26a7
CI: GREEN
```

GitHub Actions now contains a dedicated production-container smoke job that
executes the real image lifecycle:

```text
docker build
→ isolated runtime fixture
→ docker run
→ /health liveness
→ /ready readiness
→ non-root runtime identity check
→ operational SQLite initialization check
→ cleanup
```

Verified GitHub Actions run:

```text
run: #27
Python 3.13 / tests: SUCCESS
Production container / smoke: SUCCESS
```

This closes the previously unverified image build/start item from Task 32.9.

Platform boundary is explicit:

```text
local development/regression authority:
Windows + PowerShell + Python 3.13

production container execution verification:
GitHub Actions ubuntu-latest + Docker
```

The Linux container smoke test complements but does not replace Windows
compatibility. Core application, persistence, backup, restore, and resilience
logic must remain Windows-compatible.

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
Sprint 32 Task 12 — Real Operational Resilience E2E
```

Before writing Task 32.12:

```text
1. Verify develop HEAD against b4c26a7 or inspect every later commit.
2. Read the current runtime backup service, restore validator, restore activation
   service, three runtime SQLite stores/repositories, operator CLI, filesystem
   contract, and all restore/Windows regression tests before changing anything.
3. Build one real end-to-end scenario across all three runtime-managed SQLite
   boundaries:
   Knowledge, provider usage/cost, and grounded generation.
4. Write distinctive durable data into each source database using real domain
   stores/repositories where available; do not rely on placeholder bytes.
5. Create a real runtime backup set through RuntimeSQLiteBackupService.
6. Validate the published backup set through the real restore validator.
7. Mutate/damage/replace the live runtime state so restoration is necessary and
   the test can prove it is not reading untouched source data.
8. Perform restore activation through the real offline restore service.
9. Reopen/restart the runtime stores after restore and assert exact durable
   readback of the pre-backup state across all three boundaries.
10. Assert post-backup mutations are absent after restoration where applicable.
11. Preserve WAL-safe behavior and explicit connection closure before file
    replacement.
12. Treat Windows as the primary local regression environment:
    no POSIX-only unlink/rename assumptions, no Bash-only test logic, and no
    reliance on Linux file-handle semantics.
13. Keep the E2E hermetic under pytest tmp_path and avoid developer-local data.
14. Linux container CI may provide supplementary verification, but it must not
    substitute for Windows-compatible persistence semantics.
15. Do not broaden 32.12 into backup scheduling, registry publishing, proxy/TLS,
    or new product features.
```

Task 32.12 owns proof that the repository-managed backup/restore stack can
actually recover real durable runtime state end-to-end, with Windows-compatible
filesystem and SQLite semantics.

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

### Task 32.5 — Restore Validation

```text
Status: CLOSED
Commit: cb8bd40
CI: GREEN

Changed:
- added fail-closed runtime backup-set restore-candidate validation;
- added exact runtime boundary/membership and metadata validation;
- added read-only immutable SQLite integrity checks;
- added boundary-specific schema/version compatibility checks;
- added Windows SQLite sidecar handling without relaxing arbitrary-artifact
  rejection;
- added focused restore-validation regression coverage.

Decisions:
- validation never receives or mutates live destination paths;
- domain store initialize() methods are not called during candidate validation;
- a valid SQLite file is insufficient unless it matches the expected boundary
  schema identity/version;
- History remains outside the runtime restore set;
- current metadata does not support cryptographic tamper claims.

Tests/guarantees:
- initial Windows runs exposed SQLite-managed WAL/SHM sidecars in backup sets;
- validator was corrected to distinguish SQLite-managed sidecars from arbitrary
  extra artifacts;
- lifecycle test baseline was moved immediately before validation so it tests
  validator mutation rather than prior backup-service housekeeping;
- full local regression passed after fixes;
- GitHub Actions run #15 completed successfully.

Lessons:
- SQLite read-only access must not be assumed to imply zero filesystem
  side-effects in surrounding lifecycle stages;
- tests for one lifecycle stage must snapshot state immediately before that
  stage, otherwise previous-stage SQLite housekeeping can create false
  positives;
- fail-closed validation should reject unsupported artifacts without confusing
  SQLite-managed sidecars for user-controlled payloads.

Next:
Sprint 32 Task 6 — Backup / Restore CLI
```

---

### Task 32.6 — Backup / Restore CLI

```text
Status: CLOSED
Commit: 8a22b7b
CI: GREEN

Changed:
- added thin runtime backup/validate/restore CLI;
- added dedicated offline restore-activation service beneath the CLI;
- added WAL-safe rollback snapshots and compensating rollback;
- added explicit --confirm-offline operator acknowledgement;
- added Windows-safe WAL checkpoint/journal-mode transition before replacement;
- fixed KnowledgeSQLiteStore short-lived connection lifecycle;
- added CLI, restore-activation, busy-database, and connection-lifecycle tests.

Decisions:
- CLI does not own SQLite, schema, WAL, atomic replacement, or rollback logic;
- restore activation always validates the backup candidate first;
- restore is offline-only and fails closed if a live target remains busy;
- History remains outside runtime backup/restore operator workflows;
- cross-file restore is not described as an atomic transaction; recovery uses
  compensating rollback.

Tests/guarantees:
- initial Windows restore tests exposed locked WAL sidecars;
- deeper audit found KnowledgeSQLiteStore used sqlite3.Connection as a context
  manager without explicit close();
- Knowledge store now uses closing(self.connect()) consistently with the other
  runtime SQLite stores;
- full local regression passed after fixes;
- GitHub Actions run #17 completed successfully.

Lessons:
- sqlite3.Connection context-manager semantics govern commit/rollback but must
  not be relied upon as connection-lifecycle ownership;
- short-lived SQLite helper methods must explicitly close connections;
- Windows WAL locks often reveal lifecycle bugs rather than merely filesystem
  deletion problems;
- tests must stop defending obsolete symptoms after the underlying lifecycle
  defect is corrected.

Next:
Sprint 32 Task 7 — FastAPI Lifespan Contract
```

---

### Task 32.7 — FastAPI Lifespan Contract

```text
Status: CLOSED
Commit: 3b069e6
CI: GREEN

Changed:
- moved production filesystem preparation from create_app() into ASGI lifespan;
- moved operational SQLite initialization into lifespan startup;
- added optional lifespan injection to the generic FastAPI adapter;
- updated production E2E/TestClient usage to enter lifespan explicitly;
- added focused startup side-effect, startup failure, readiness, and repeated
  app-construction tests.

Decisions:
- create_app() is configuration/composition only;
- operational persistence side effects belong to startup lifecycle;
- Knowledge remains an external prerequisite;
- startup failures fail closed before the app becomes available;
- current shutdown has no fake resource cleanup because no long-lived owned
  handles exist;
- future long-lived resources must be closed in the explicit lifespan shutdown
  boundary.

Tests/guarantees:
- initial full regression exposed three stale composition expectations;
- fake FastAPI factories were updated to accept lifespan;
- persistence composition tests now assert DB creation after lifespan entry,
  not during create_app();
- full local regression passed after fixes;
- GitHub Actions run #19 completed successfully.

Lessons:
- application construction and runtime startup are distinct lifecycle stages;
- tests that depend on startup state must explicitly enter ASGI lifespan;
- when moving side effects into lifecycle ownership, all composition consumers
  and test doubles must be audited for the new callable boundary;
- tests should validate lifecycle timing, not preserve old construction-time
  side effects.

Next:
Sprint 32 Task 8 — Runtime Deployment Layout
```

---

### Task 32.8 — Runtime Deployment Layout

```text
Status: CLOSED
Commit: 543e737
CI: GREEN

Changed:
- added GroundedAIServerDeploymentLayout as a descriptive deployment contract;
- defined independent /application, /runtime, /backups, /config, /secrets roots;
- defined canonical live SQLite paths beneath /runtime;
- projected only non-secret runtime path environment;
- documented persistent, read-only, and ephemeral deployment boundaries;
- updated .env.example to show the canonical production layout.

Decisions:
- /runtime and /backups are independent persistent roots;
- application/code is not a writable runtime-state location;
- config and secrets remain deployment-owned/read-only boundaries;
- secrets continue to enter through the established environment-variable
  contract; no implicit secret-file loader was introduced;
- existing explicit-path deployments remain backward compatible and no database
  is silently moved.

Tests/guarantees:
- deployment roots must be absolute and independent;
- backup_root nesting under runtime_data_root is rejected;
- runtime_data_root nesting under application_root is rejected;
- the contract does not create deployment directories as a side effect;
- full local regression passed;
- GitHub Actions run #21 completed successfully.

Lessons:
- live state and its backup must not share the same failure domain by default;
- deployment topology should be explicit before container image design;
- read-only code/config/secret boundaries must not become accidental runtime
  persistence;
- introducing a deployment layout must not create a second configuration or
  secret authority.

Next:
Sprint 32 Task 9 — Container Baseline
```

---

### Task 32.9 — Container Baseline

```text
Status: CLOSED
Commit: f0a4b64
CI: GREEN

Changed:
- added production Dockerfile;
- added .dockerignore excluding secrets, local runtime data, SQLite sidecars,
  tests, docs, scripts, and development locks;
- installed runtime requirements.lock with --require-hashes;
- added non-root runtime user;
- made /application read-only and disabled Python bytecode writes;
- declared /runtime and /backups as persistent volume boundaries;
- added /health liveness healthcheck using Python stdlib;
- preserved canonical one-worker server command;
- added container-baseline contract tests and documentation.

Decisions:
- container consumes the 32.8 filesystem layout instead of inventing new paths;
- /health is liveness; /ready remains readiness and is not used for restart
  semantics;
- Knowledge and real secrets are not baked into the image;
- current env-variable secret contract remains authoritative;
- no Docker Compose/Kubernetes/TLS/reverse-proxy semantics were pulled into
  Task 32.9.

Tests/guarantees:
- focused container contract suite passed locally;
- full Python regression passed locally;
- git diff --check passed locally;
- GitHub Actions run #23 completed successfully;
- local docker build was NOT executed because Docker CLI was unavailable.

Lessons:
- static Dockerfile contract tests do not prove the image actually builds;
- liveness and readiness must remain separate;
- build context must explicitly exclude developer secrets and live SQLite state;
- container work should consume prior filesystem/security contracts rather than
  becoming a new authority.

Unverified:
- real docker build/start on the developer machine.

Verification owner:
- Task 32.11 CI Container Smoke Test.

Next:
Sprint 32 Task 10 — Deployment Security Contract
```

---

### Task 32.10 — Deployment Security Contract

```text
Status: CLOSED
Commit: 1c6fe62
CI: GREEN

Changed:
- added canonical deployment-security ownership model;
- documented TLS/reverse-proxy/private-HTTP topology;
- explicitly disabled Uvicorn proxy-header trust;
- documented endpoint exposure policy for /health, /ready, /openapi.json, /v1/*;
- preserved application API-key authentication as defense in depth;
- preserved environment-variable secret injection as the sole application
  secret authority;
- added deployment-security contract tests and server CLI regression coverage.

Decisions:
- TLS certificates, HTTPS policy, and HSTS belong to proxy/platform ingress;
- application-level TLS is not added merely for appearance;
- application container is not a supported direct-public deployment boundary;
- arbitrary X-Forwarded-* metadata is not trusted;
- /ready and /openapi.json are deployment-private operator surfaces;
- no automatic secret-file loader is introduced.

Tests/guarantees:
- focused deployment-security/server tests passed locally;
- full Python regression passed locally;
- git diff --check passed locally;
- GitHub Actions run #25 completed successfully.

Lessons:
- deployment security must distinguish infrastructure ownership from application
  enforcement;
- defaults around proxy headers are security-sensitive and should be explicit;
- defense-in-depth application authentication should remain even behind trusted
  ingress;
- secret injection must have one authoritative path rather than competing env
  and file mechanisms.

Next:
Sprint 32 Task 11 — CI Container Smoke Test
```

---

### Task 32.11 — CI Container Smoke Test

```text
Status: CLOSED
Commit: b4c26a7
CI: GREEN
GitHub Actions run: #27

Changed:
- added a dedicated Production container / smoke CI job;
- built the real production Dockerfile on the GitHub runner;
- started the image with an isolated mounted /runtime fixture;
- injected only synthetic runtime credentials;
- verified /health and /ready separately;
- verified the running container UID is non-root;
- verified lifespan-created operational SQLite stores exist on mounted runtime;
- captured logs on failure and guaranteed container cleanup;
- preserved the existing Python regression job.

Verified runtime steps:
- Build production image: SUCCESS
- Start production container: SUCCESS
- Wait for liveness: SUCCESS
- Verify readiness: SUCCESS
- Verify non-root runtime identity: SUCCESS
- Verify operational stores were initialized: SUCCESS
- Cleanup: SUCCESS

Platform contract:
- developer/local regression environment is Windows + PowerShell + Python 3.13;
- container execution verification uses GitHub Actions ubuntu-latest + Docker;
- Linux CI supplements but does not replace Windows compatibility;
- persistence/backup/restore work must preserve Windows file-handle, SQLite WAL,
  replace/unlink, and fsync semantics.

Lessons:
- static Dockerfile contract tests are not equivalent to a real image build;
- CI contracts must be audited before adding workflow literals or secret-like
  names;
- liveness and readiness remain separate;
- container CI and host-platform regression prove different properties;
- Windows-specific persistence behavior remains a first-class compatibility
  requirement even when production container verification runs on Linux.

Next:
Sprint 32 Task 12 — Real Operational Resilience E2E
```

---

## 16. Current Checkpoint Summary

```text
Repository: vactor222123/InvestmentTerminal
Branch: develop
Baseline: b4c26a7
Sprint 31: CLOSED / CI GREEN
Development mode: audit-driven hardening / production maturity
Approved Sprint: Sprint 32 — Production Deployment & Operational Resilience
Current next action: 32.12 Real Operational Resilience E2E
```

Checkpoint synchronization:

```text
PROJECT_CONTINUATION.md introduced: develop @ 30a28ac
CI: GREEN
```

Tasks 32.1–32.11 are closed on verified CI. Continue with Task 32.12 only from
the verified `b4c26a7` implementation baseline, or audit every later commit
before proceeding.
