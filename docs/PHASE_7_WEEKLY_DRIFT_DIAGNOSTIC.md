# Phase 7 — One-Series Weekly Candle Drift Diagnostic

Classification: `IMPLEMENTATION`. The fresh `develop` clone matched caller
baseline `8a3fc092def8dca952ee8119932672131a0024e7` and was clean.

The returned redacted weekly report measured 120 attempted series, 96 successes,
and 24 isolated failures: three `NO_PRICE_DATA`, twelve `RESPONSE_NUMERIC`, and
nine `STORED_CANDLE_DRIFT`. It reported 89 omitted trailing rows. The user then
confirmed `SQLite integrity: ok`. These counts do not establish why any one
overlap changed or whether the first 120 represent the remaining universe.

The weekly checkpoint records only a stable failure category, not candle values.
This package adds a separate read-only diagnostic that validates the manifest,
complete source checkpoint set, and private weekly checkpoint before selecting
the first stored-drift outcome in manifest order. It reads the existing SQLite
overlap under `PRAGMA query_only = ON`, makes at most one Yahoo projection
request using the original seven-day overlap and exclusive end, and compares
only the stored and current versions of matching candles. It never saves
candles, changes the weekly checkpoint, retries a weekly outcome, or resumes
the broad refresh. The Yahoo cache and redacted report are the only potential
filesystem writes.

The schema-version-1 `WEEKLY_CANDLE_DRIFT_DIAGNOSTIC` report binds manifest,
weekly selection, and end. `REPRODUCED` means at least one current overlap row
differs; `NOT_REPRODUCED` means compared overlap rows now match;
`INCONCLUSIVE` means there is no current overlap to compare;
`PROVIDER_FAILURE` records one stable provider failure category; `FAILED`
indicates preflight or runtime failure. It reports overlap, changed-row,
new-row, omission, and changed-field counts, without symbols, currency,
timestamps, prices, volume values, paths, provider text, or exception messages.
One current response cannot prove the cause of an earlier difference.

Next, run exactly one controlled private diagnostic and return only its
redacted report. Do not run all remaining weekly series or change the stored
candles based on this implementation alone. The `RESPONSE_NUMERIC` cohort is a
separate follow-up question after the drift result is reviewed.
