# Phase 7 — composed research result audit

Classification: `AUDIT`. Fresh clean `develop` matched the caller's exact
baseline `ae87d4436ff18aa1a892779cefd4340e0976dd92` before changes.
Only returned redacted reports were read. No private snapshot, research export,
profile, checkpoint or database was opened; no provider request or runtime write
was performed. Application code, architecture and JSON contracts are unchanged.

## Reviewed evidence

The operator ran `instrument_research_collect` with selected symbol MCD, run ID
`mcd_20260929_composed_001`, explicit snapshot reuse and a seven-day action-age
policy. The user returned both redacted reports and these console lines:

```text
SQLite integrity: ok
COMPLETE: corporate-action research run
```

Exact-byte SHA-256 values independently calculated from the returned files:

- `research_mcd_20260929_composed_001.json`:
  `abd57b14cfc8bc80eef90e0bc6975d447f1da23ee675abc53d170035d605b7d3`.
- `research_mcd_20260929_composed_001_actions.json`:
  `33c6ae8de0942cb866e65a8d704252a003886e0879147a09ec3260d3f0db45f7`.

Research schema 2 reports `COMPLETE`, null failure, 2,512 stored candles in
`[2016-09-29T00:00:00+00:00, 2026-09-29T00:00:00+00:00)`, a sample capped at
200 and `BOTH_AVAILABLE` SMA50/SMA200 availability. The seven-calendar-day recency
proxy is true relative to that exclusive end, not to the audit date. Stored price
basis remains `STORED_CLOSE_NO_EXPLICIT_ADJUSTMENT`.

Collection schema 1 reports `STORED`, `snapshot_persisted=true`,
`reused_snapshot=true`, 2,512 observed source rows and null failure category.
Both reports agree on 40 dividend observations, zero observed split/capital-gain
events, absent capital-gains field, and the following evidence bindings:

- Exact snapshot SHA-256:
  `903ba45bd3d691ca40c114afde5f0e65501fbe79edf246b5236f643a74cec637`.
- Normalized content SHA-256:
  `035457b2b8a258e85f87923cc075d7bc866b4434e491d7dda712e640436b1ced`.

Research context is `AVAILABLE` at `2026-10-06T14:58:08.993646+00:00` under the
seven-day policy. Its full embedded-document checksum is
`17fcfd29246eb0fb134722d258f361415582a9c89bb8d2397bed8e06d3e00db4`.
These pins match the earlier separate-step qualification recorded in
`PHASE_7_CORPORATE_ACTION_RESEARCH_RUN.md`. The research projection pin remains
`a8ffe1f944d529b64d688fb75ba4e9ad2278edc0d59bbe8ba1850c1017fabf0a`;
the exported candle-array hash remains
`c1dfbca37452360f3cc1d53675c455069b40b0d26afa7cd5cd8d4fe1faa80230`.
Matching reported hashes are consistency evidence, not an independent read of
the private source files or proof of a provider's truthfulness.

## Code-path audit and conclusion

The composed CLI preflights export readiness, requires matching fresh pinned
reuse evidence, verifies persisted private/report parity, checks SQLite through
a read-only connection, and rechecks bound files before printing overall
completion. Existing failure tests ensure a late verification/integrity failure
cannot emit that completion line. A collection `STORED` or research `COMPLETE`
alone would not certify the later stages; the separately returned final console
lines matter. The audit has not independently rerun SQLite or the private pair
verifier. The redacted report omits symbol, so MCD identity is established by the
user-executed selected-symbol verifier, not inferred from the report filename.

The result qualifies the generic composed **offline reuse** path. Earlier live
collection evidence is separate; this run is not a new live download or evidence
that all instruments have action snapshots. Generic synthetic tests exercise
other symbols and failures; no MCD-specific rule is added.

Close the bounded dividend/split acquisition, separate snapshot persistence,
research-context integration and single-command verification slice. Keep Phase 7
open. Explicit limitations remain:

- normalized yfinance observations, with raw-source/action completeness unknown;
- zero observed events do not prove absence; absent fields are not evidence of zero;
- cash-action currency and historical per-share adjustment basis unverified;
- no candle adjustment, dividend-inclusive total return or broker cash posting;
- no proof of exchange-session completeness or present-day candle freshness;
- no automatic private upload, broad action refresh or unattended scheduling.

EODHD remains paused. No further MCD repetition is required to close this slice.

## Verification

Returned report byte hashes and shared snapshot/content/count/presence fields
passed a separate read-only consistency check. This does not inspect private
artifacts. Existing focused tests exercise offline no-fallback reuse, stale and
corrupt inputs, locks, write failures, retained snapshots, tampering and late
SQLite failure. No new tests are added because only documentation changes.

Executed with Python 3.13.7:

```text
python -m pytest tests/test_instrument_research_collect.py tests/test_research_corporate_actions.py tests/test_instrument_research_export.py tests/test_instrument_research_verification.py tests/test_instrument_research_run.py tests/test_yahoo_corporate_actions.py tests/test_architecture_dependencies.py tests/test_dependency_reproducibility_contract.py --basetemp=.pytest-composed-audit-focused -q
244 passed in 28.28s

python -m pytest --basetemp=.pytest-composed-audit-full -q
3520 passed, 4 skipped, 1 warning in 69.74s

git diff --check
clean
```

The warning is the existing Starlette/httpx deprecation. No dependency change,
live provider qualification or CI execution is claimed by these local results.
Architecture.md and DataModel.md need no update because their boundaries and
schema definitions are unchanged. Test temporary directories and runtime reports
are excluded from the commit and ZIP.

## Next action

Apply and commit this documentation package, then return the applied SHA. Preserve
the existing successful outputs; no runtime command is required for this audit.
The next development package should audit the smallest generic composition of
existing `weekly_run`, stored-quality measurement and latest raw-indicator
projection. The aim is one manageable operator workflow for the dataset rather
than another symbol-specific investigation. Preserve explicit end/budget, bound
checkpoints, isolated failures, rate-limit halts, non-overwriting reports and
separate quality evidence. Audit incomplete/failed runs and stale projection
handling before implementation; this selection does not authorize live refresh,
automatic retries, scheduling or a new data contract.

SEND: applied Git SHA only; no additional runtime evidence requested now.

DO NOT SEND: private snapshots, research exports, profile, projection,
checkpoints, portfolio, cache or SQLite database.
