# Phase 7 Package 12 — XNYS Evidence Generation Checkpoint

Baseline: `develop @ 8fde6a0fab31a0ae1ee891741dea158219b786a8`.

The bounded `XNYS@1` generator was executed with retrieval time
`2026-08-24T00:00:00Z`. The resulting document passed the existing provenance,
timezone, and canonical session-checksum verifier:

```text
calendar identity: XNYS@1
session count: 1,254
range: 2021-08-19 — 2026-08-18
session checksum: 83d70a90bb334fac740a209a20bcfbfcb685de805130655cfef31134ab48e2fb
```

The current execution permission profile allowed read-only inspection of the
operational SQLite and confirmed `IBM_TOTAL=0`, but denied writes outside the
workspace and did not permit an approval escalation. The generated JSON was
therefore verified in the workspace output directory rather than copied into
`C:\runtime\reports`. No IBM request was sent and the operational database was
not modified.

This is an exact operational blocker, not missing calendar data or a failed
provider qualification. The next run must first place the verified evidence at
`C:\runtime\reports\xnys_sessions_2021-08-19_2026-08-18.json` under an explicit
write permission, re-run its checksum verifier, and only then execute one
bounded IBM ingestion.

Verification:

```text
focused: 35 passed
full: 2,726 passed, 4 skipped
git diff --check: clean
```
