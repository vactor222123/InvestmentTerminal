# Phase 7 Package 5 — Explicit-Session Candle Coverage Quality

## Verified baseline and evidence

`develop @ 9819ef92091626810f2d10407e8cc074b94a51a5`

The controlled one-year MSFT request downloaded 251 daily candles, inserted
239 new rows, retained 12 duplicates, and produced 251 stored rows from
2025-08-19 through 2026-08-18. SQLite integrity and boundaries matched the
version 2 report.

## Audit conclusion

Elapsed span and row count cannot establish completeness. The repository
already owns a versioned explicit market-session calendar contract that
deliberately prohibits weekday, exchange-name, or candle-derived inference.

## Implemented boundary

The History-owned `CandleCoverageQualityService` compares daily candle dates
in the calendar timezone with explicitly supplied sessions. It reports expected
and observed counts, missing session keys, unexpected candle timestamps,
completeness ratio, and a fail-closed completeness flag. Empty calendar
evidence never becomes 100% coverage.

No calendar provider, guessed holiday list, network request, persistence,
batching, analysis, or trading authority was added.

## Next action

Select a licensable authoritative XNAS/XNYS session source, preserve its
identity/version/provenance in the existing calendar contract, then evaluate
the stored MSFT period before broadening the ingestion scope.
