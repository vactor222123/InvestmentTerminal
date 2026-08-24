# Phase 7 Package 19 — Refresh-Report Projection Audit

Baseline: `develop @ 1c0d247123d9a5d1aec11f4b2ba92e96dd181073`.

The focused audit covers the schema-version-1 operational baseline, its CLI,
all current consumers/tests, and the schema-version-1 single-instrument refresh
report. The baseline currently derives both `refresh_observability` and
`measured_performance` only from an optional integrated workflow report. It has
no input or store identity for standalone refresh evidence.

Changing the default store inventory would alter every existing baseline even
when no refresh report is supplied. The smallest backward-compatible seam is:

1. add optional `refresh_report` to `OperationalDataBaselineInputs` and
   `--refresh-report` to the CLI;
2. preserve the exact current eight-store default when the option is omitted;
3. only when a path is explicitly supplied, add one `REFRESH_REPORT` store;
4. validate schema version, provider, status, normalized request identity,
   aware start/completion/checked-at timestamps, non-negative finite duration,
   and status/result/failure consistency;
5. project only aggregate operational evidence: identity, duration, status,
   refresh-attempted flag, readiness, and transfer counters;
6. set refresh observability and measured performance to `READY` only for a
   valid `REFRESH_REPORT` (or the already supported valid workflow report);
7. expose absent/malformed/unsupported explicitly without treating it as
   measured success.

The implementation package must retain baseline schema version 1, default JSON
shape, deterministic store ordering, secret/content redaction, and read-only
inspection. Focused tests must cover omitted input, valid `SUCCESS`, valid
`NOT_READY`, valid `FAILED`, malformed JSON, unsupported schema, inconsistent
status/result/failure combinations, naive timestamps, and invalid duration.

No refresh execution, scheduler, multi-instrument aggregation, analysis, or
trading belongs in this projection package. After implementation, the existing
MSFT live refresh report should be supplied explicitly to one read-only
baseline run.

Verification:

```text
focused: 40 passed
full: 2,731 passed, 4 skipped
existing warnings: 1 Starlette deprecation warning
git diff --check: clean
```
