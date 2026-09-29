# Phase 7 — profile-backed bounded weekly run

Classification: `IMPLEMENTATION`. Fresh clean GitHub `develop` matched
`5f82f1984cbef824b01a62edaca8aa4635db1b30` before changes.

`python -m investment_terminal.cli.weekly_run` is a short composition root
over the existing `weekly_candle_refresh` CLI and service. It does not alter
retrieval, persistence, provider failure policy, private weekly checkpoint
schema 1, or the existing redacted refresh report schemas 1/2. One invocation
still performs only an explicit bounded slice; no hidden loop, sleep,
scheduler, backfill, or automatic failure retry was added.

The private `WEEKLY_RUN_PROFILE` schema version 1 is a JSON object with exactly
`schema_version`, `operation_identity`, `manifest`, `manifest_checksum`,
`source_checkpoint_directory`, `database`, `cache_directory`,
`weekly_checkpoint_directory`, and `report_directory`. All paths must be
absolute. The first three input files/directories must exist, the manifest
checksum must match its canonical contents, and the complete source
checkpoint sequence is validated before provider access. Cache, source,
checkpoint, and report directories must not overlap. The profile contains
private paths and must remain under `C:\runtime\data`, not in Git or a ZIP.
This package does not fabricate the source directory or create the profile;
the next operational handoff must bootstrap it from existing verified private
evidence.

An operator invocation supplies `--profile`, explicit UTC-midnight exclusive
`--end`, `--max-items`, and a three-digit `--slice-id`. The derived private
checkpoint is `weekly_candle_refresh_YYYY-MM-DD.json` under the profile's
checkpoint directory. The derived redacted report is
`weekly_candle_refresh_YYYY-MM-DD_NNN.json` under its report directory.
Distinct slice IDs preserve prior reports; an existing report path is never
intentionally overwritten. A checkpoint copied from another end, malformed
profile or source evidence, future end, or report collision fails before a
provider request. An exclusive profile-local lock prevents concurrent weekly
slices, including different end dates; a
lock left by an interrupted process must be inspected and cleared manually,
never automatically retried through. The optional `--retry-rate-limited`
forwards the existing explicit retry mode and uses report schema 2; it never
retries other failures.

The command returns the existing refresh CLI exit code and prints the report
path with `SEND` plus a reminder that private inputs must not be shared.
`BUDGET_EXHAUSTED` may exit zero while containing isolated failures, and a
nonzero `HALTED` run may already have committed candle progress. Review the
durable report and private checkpoint before deciding whether to continue.
The command does not declare session completeness, endpoint freshness,
indicator validity, or scheduler readiness.

Next: one exact-baseline user-executed handoff to create the private profile
from the known manifest/database and checksum-identified complete source
checkpoint directory, then qualify one new-end `--max-items 1` slice. Return
only its redacted report and independent SQLite integrity; do not send the
profile, manifest, source/weekly checkpoints, database, or cache.
