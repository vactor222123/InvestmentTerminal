# Changelog

## Sprint 31 — Evidence Integrity & Delivery Hardening

- Made persisted grounded generation/trace JSON deeply immutable.
- Added detached mutable serialization for external JSON consumers.
- Enforced strict JSON values and rejected non-finite numbers/non-string keys.
- Hardened SQLite JSON persistence and parsing.
- Expanded executable dependency guards for History, Knowledge, AI,
  Application, API, Server, Review, and CLI boundaries.
- Reconciled root canonical documentation with supporting `docs/` context.
- Added explicit grounded-generation DB configuration to `.env.example`.
- Established Python 3.13.x dependency-resolution contract.
- Split runtime and development direct dependency manifests.
- Added pinned dependency compiler toolchain.
- Added committed hash-locked runtime/development dependencies.
- Removed hidden platform-specific `fastapi[standard]` dependency ownership;
  declared FastAPI, Uvicorn, and HTTPX explicitly by responsibility.
- Added first GitHub Actions CI workflow.
- Added locked Linux dependency installation in CI.
- Added dependency contract, architecture contract, full pytest, and whitespace
  CI gates.
- Made portfolio/review CLI tests hermetic by using tracked example fixtures.
- Verified the full suite in a clean Linux GitHub Actions environment.

## Sprint 30 — Grounded Generation Persistence & History

- Added immutable persisted grounded-generation model.
- Added repository contract and in-memory reference semantics.
- Added deterministic projection from ADMISSIBLE grounded generation + trace.
- Added dedicated SQLite schema/store/repository.
- Added application-level recording with injected clock.
- Added runtime-configured grounded-generation database composition.
- Added schema-aware readiness for grounded-generation persistence.
- Added bounded recent and half-open time-window repository queries.
- Added read-only grounded-generation inspection CLI.
- Added authenticated read-only HTTP generation-history endpoints.
- Added real durable Knowledge → generation → persistence → reopen → HTTP E2E.
- Preserved the authority rule that generated evidence is not automatically
  History or Knowledge.

## Sprint 29 — Provider Operational Accounting Hardening

- Added runtime-configured provider usage/cost ledger path.
- Added schema-aware readiness and fail-closed corrupt store handling.
- Added bounded operational queries and exact Decimal summary aggregation.
- Hardened SQLite connection lifecycle.
- Added real operational accounting E2E.

## Sprint 28 — Persistent Provider Usage & Cost Ledger

- Added immutable provider usage/cost ledger persistence and operational CLI.

## v0.1.0-alpha1

- Project architecture approved.
- Sprint 1 initialized.
- Ready for core infrastructure implementation.
