# Phase 7 — MCD research-pair verification result

Classification: `AUDIT`. A fresh clean GitHub `develop` clone matched
`dd7fb5f02d84478bbc9dab06ed6f7e675064a17d` before this package.
The only runtime artifact inspected here was the user's explicitly returned
redacted report at
`C:\runtime\reports\instrument_research_run_mcd_20260929_001.json`.
Its exact-byte SHA-256 was independently checked as
`f67727f3f09ef6b7b82a0f80102323b56ecdd67786e6177f600bd409cc0ea3ed`,
matching the previously pinned checksum. No private export, SQLite database,
provider, or runtime output was read or changed by this audit.

The user returned the local verifier's `VERIFIED` line, the matching
`REPORT_SHA256`, and a `PRIVATE_SHA256`. The private hash is deliberately not
copied into this repository: it was user-reported and its source bytes were
not independently available here. The handoff block checks the exact four
expected verifier lines, report and private hashes before/after execution,
and the baseline/worktree state; the returned excerpt does not itself prove
that the block was run unmodified. Conditional on that local execution, the
generic verifier confirmed the selected `MCD` identity, existing schema-1
private/report bindings, canonical exported-candle checksum, and available
latest-sample raw-close indicator parity. This is local pair integrity, not
independent provider or historical-market verification.

The redacted report independently records `COMPLETE`, `failure=null`, 2,512
stored daily-labeled candle rows in the 2016-09-29 through 2026-09-29
exclusive UTC window, 200 latest close samples, both SMA50/SMA200 available,
and a seven-calendar-day recency proxy relative to that historical end. It
contains no price, SMA value, per-candle timestamp, or instrument identity.
`STORED_CLOSE_NO_EXPLICIT_ADJUSTMENT` does not establish corporate-action-
adjusted returns; the row count and recency proxy do not establish exchange-
session completeness or current freshness.

The next gate is an explicit, separate user decision about sharing the exact
private MCD export with ChatGPT for factual research analysis. The earlier
general request to analyze McDonald's and the present verifier output do not
authorize automatic access to the artifact. If consent is withheld, continue
with a bounded local analytical projection and a separately reviewed redacted
result instead. Do not upload the private file, infer returns or trading
recommendations from this report, broaden to bulk export, or enable a weekly
scheduler on the strength of this pair check.
