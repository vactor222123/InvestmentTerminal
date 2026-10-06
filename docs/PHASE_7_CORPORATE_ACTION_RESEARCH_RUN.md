# Phase 7 — one-command corporate-action research

Classification: `IMPLEMENTATION`. Fresh, clean `develop` matched caller baseline
`8232d583a46480dd7f21ed3982077a59aee77893`. No private runtime input,
operational SQLite database or provider was accessed during implementation.
The preceding user-returned redacted reports are the operational evidence below.

## Measured result and focused audit

The user executed the separate collection/export/verification/SQLite script
for MCD and returned both redacted reports plus `SQLite integrity: ok`.
The research report is schema 2, `COMPLETE`, with 2,512 stored rows over
`2016-09-29T00:00:00+00:00` inclusive to `2026-09-29T00:00:00+00:00`
exclusive, a 200-close sample and `BOTH_AVAILABLE` SMA availability. The
seven-day recency proxy is relative to that end, not to today's date.
Actions are `AVAILABLE` at `2026-10-05T18:39:16.480402+00:00` under a seven-day
policy. Collection reports `STORED`, 2,512 observed rows, 40 dividends, zero
observed splits/capital gains, absent capital-gains field and no failure.
Raw-source presence and completeness remain `UNKNOWN`.

Independently computed exact-byte report SHA-256 values:

- Research: `fa95e843325cdd76e5e0dc45f0dd3f602622e6bdd5b9164ea1a5b1928fb31272`.
- Collection: `713d00437309d34efe62fa59ea7706ec25da098e857f5ac8458f8365ef4a7ee5`.

Both reports carry matching snapshot checksum
`903ba45bd3d691ca40c114afde5f0e65501fbe79edf246b5236f643a74cec637`
and content checksum
`035457b2b8a258e85f87923cc075d7bc866b4434e491d7dda712e640436b1ced`.
This establishes redacted report consistency. Private snapshot/export bytes
were not reopened here; their identity/parity is the local command's boundary,
not something a redacted report alone proves. SQLite integrity is user-reported.
Zero observed splits is not independent proof that no split occurred.

The remaining usability gap was orchestration in a long operator script.
Collection, typed validation, export and verification already existed; the
smallest change is a CLI composition reusing those boundaries, not a second
downloader, new schema or MCD-specific rule.

## Command

```text
python -m investment_terminal.cli.instrument_research_collect --help
```

Required inputs: `--profile`, `--projection`, `--projection-sha256`, `--symbol`,
`--history-start`, `--end`, `--run-id`, `--actions-maximum-age-days`.
The profile retains its exact existing schema. The projection hash remains an
explicit evidence pin. Run IDs use 1..48 lowercase ASCII letters, digits,
underscores/hyphens, starting with a letter or digit; no path or symbol inference.
Dates are explicit UTC-midnight ISO values over a bounded half-open window.

The command derives outputs for run ID `example_001`:

- Beside the private projection: `research_example_001.json` (private export).
- Beside the private projection: `research_example_001_actions.json` (new actions).
- In the profile report directory: `research_example_001.json` (redacted export report).
- In the profile report directory: `research_example_001_actions.json` (redacted collection report).

Without reuse options it collects one explicit symbol/window through the existing
Yahoo action client, using the profile cache. It never downloads or inserts a
replacement candle series. Existing output names cause failure, not overwrite.

For offline reuse, supply both `--actions-snapshot` and `--actions-sha256` with
an existing matching snapshot and its pinned exact-file hash. No provider call
occurs; corrupted, mismatched, future or stale evidence fails instead of triggering
a silent refetch. The new report marks `reused_snapshot=true`. An actual refresh
requires a new run ID with no reuse arguments and produces a new full-window
snapshot, preserving the older one. No automatic latest-file search or tail merge.

The caller chooses maximum action age (1..365 days). Evaluation time is measured
in UTC after collection and recorded in the unchanged schema-2 context, rather
than requiring the operator to type a timestamp. This stricter combined command
requires `AVAILABLE`; the existing standalone export still supports `STALE` and
`MISSING` unchanged. Fresh actions do not make an old candle window current.

## Stage and persistence ownership

1. Validate profile, paths, unused outputs, window, policy and checksums. Hold the
   existing weekly-run lock plus cooperative locks on the new export/report.
   Reuse the extracted read-only `prepare_export` builder and legacy verifier to
   check selection, projection parity and export readiness before provider work.
2. Delegate action collection/offline reuse, reconstruct the snapshot and compare
   its entire redacted report to the existing report builder; require currency,
   symbol, window, freshness and source hash agreement.
3. Delegate schema-2 profile export, then independently verify the persisted pair
   against its exact report SHA-256 using the existing local verifier.
4. Run SQLite `PRAGMA integrity_check` through a `mode=ro`, `query_only` connection;
   require the entire result to equal one `ok` row. Check source/result hashes
   again before printing overall completion and report hashes.

Profile, projection, manifest, weekly checkpoint and all source `batch_*.json`
files are byte-fingerprinted before work and compared across stages. SQLite is
not file-hashed; the export reads its current transaction snapshot and verifies
latest-sample parity. Locks exclude cooperating commands, not unrelated external
writers; pause all other writers during execution. A stale lock is never removed
automatically. Only locks actually acquired by this invocation are cleaned up.

Any failed stage exits nonzero with its fixed stage name, never raw exception
text. Later stages do not run. Already collected snapshots and stage reports
are retained; export's existing cleanup rules apply to its own failed writes.
Use a new run ID and explicitly pinned snapshot to recover after fixing the
cause. An exact run repeat refuses existing destinations and makes no request.

There is no new aggregate JSON contract: `STORED` describes the collection stage
and `COMPLETE` in the export report describes export only. A later verifier or
SQLite failure cannot retroactively change these immutable stage facts; overall
success requires exit code zero and the final console `COMPLETE` line. If the
process is interrupted, inspect retained artifacts rather than deleting them or
assuming overall success. There is no automatic retry or transactional claim
across the snapshot, two reports and private export.

## Verification and next step

Focused tests cover generic-symbol online/offline success, source immutability,
invalid policy/window/path/checksum, stale/corrupt reuse without network fallback,
provider failure, lock ownership, snapshot retention, post-write export cleanup,
tampering, concurrent source changes, full SQLite result checking and repeat
refusal. Architecture/dependency guards and legacy schema-1/2 suites are included.

Focused selection: 244 passed. Full suite: 3520 passed, 4 skipped, one existing
Starlette deprecation warning. `git diff --check`: clean.

Next: apply the package and qualify the composed command once with the existing
MCD snapshot, a new run ID and the same 2016-09-29/2026-09-29 candle window.
Reuse avoids another Yahoo acquisition. Bind the operator command to the applied
GitHub SHA. Previously confirmed paths are the private `weekly_run_profile.json`,
`latest_raw_indicator_projection_20260929_full.json` and
`yahoo_corporate_actions_mcd_20160929_20260929_001.json` under `C:\runtime\data`.
The projection pin is
`a8ffe1f944d529b64d688fb75ba4e9ad2278edc0d59bbe8ba1850c1017fabf0a`.

SEND: only the two derived redacted reports, their hashes, final completion and
SQLite integrity lines. On failure send its fixed stage and available reports.

DO NOT SEND: private action snapshot, research export, profile, projection,
checkpoints, portfolio or SQLite database.

EODHD remains paused. Total return, action completeness, cash-currency
certification, candle adjustment, portfolio cash mutation, mass action refresh,
private upload, automatic retries and weekly scheduling are not introduced.
