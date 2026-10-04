# Phase 7 — profile-backed research result audit

Classification: `AUDIT`. A fresh clean GitHub `develop` clone matched
`4d22fd509c0ea9b5c3204afb307acf56e592c72c`. The only runtime file read
was the user's explicitly returned redacted report
`C:\runtime\reports\instrument_research_run_mcd_20260929_001.json`.
It parses as JSON and its exact-byte SHA-256 is
`f67727f3f09ef6b7b82a0f80102323b56ecdd67786e6177f600bd409cc0ea3ed`.
The user separately reported `SQLite integrity: ok`; this audit did not rerun
the check. No private export, projection, profile, checkpoint, or SQLite
database was read or modified.

## Measured result

The schema-version-1 `INSTRUMENT_RESEARCH_EXPORT_REPORT` has `COMPLETE`
status and `failure=null`. It binds manifest
`8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a`,
selection `75d839c54ff43969832a4d1110deba538cd52793e9402db5cba2dc1decc6c5ae`,
source projection bytes
`a8ffe1f944d529b64d688fb75ba4e9ad2278edc0d59bbe8ba1850c1017fabf0a`,
and the 2016-09-29 through 2026-09-29 exclusive UTC window. It reports
2,512 stored daily-labeled rows with exported candle-array checksum
`c1dfbca37452360f3cc1d53675c455069b40b0d26afa7cd5cd8d4fe1faa80230`.
The latest capped sample contains 200 closes, so both raw-close SMA50 and
SMA200 are available. The seven-calendar-day recency proxy is true relative
to the **2026-09-29 exclusive end**, not a live freshness guarantee today.

The report's shape and limitations match the established redacted contract:
it contains no symbol, currency, candle timestamp/value/volume, SMA value,
path, or exception text. The MCD identity is supplied by the handoff command
and filename, **not independently attested by this report**. Its 2,512-row
count happens to match the earlier unidentified export, but its candle-array
checksum differs; neither fact proves instrument identity or a causal reason
for the difference.

## Boundary and next package

`STORED_CLOSE_NO_EXPLICIT_ADJUSTMENT` does not establish corporate-action-
adjusted returns. A row count and recent-candle proxy do not establish
exchange-session completeness, history start coverage, or absence of gaps.
The CLI checks selected latest-200 parity against the private projection;
older exported rows are bound to this export's candle-array checksum only.
The returned redacted report cannot itself verify the private artifact's
symbol, its exact bytes, or private/report candle-array parity.

The smallest reusable next implementation is a **local, read-only research
handoff verifier** for any caller-selected symbol. It should accept the
existing private schema-1 export and redacted report, verify the expected
symbol and matching evidence bindings, recompute the deterministic candle-
array checksum, and fail closed on missing, altered, or mismatched evidence.
It must neither change existing JSON schemas nor automatically upload the
private artifact, call a provider, rewrite SQLite, calculate investment
conclusions, or schedule work. Only after such local verification and an
explicit per-artifact sharing decision should ChatGPT consume private candle
values. No further runtime action is authorized by this aggregate result.
