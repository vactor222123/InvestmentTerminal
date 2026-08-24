# Phase 7 Package 10 — Controlled Second XNAS Instrument

Baseline: `develop @ 9ff76a69c4cf0cdc2468ee35fac273eb15dadebe`.

The focused audit selected Apple Inc. Common Stock (`AAPL`) as the second
instrument. Nasdaq's official AAPL page identifies it as Nasdaq Listed, so the
existing bounded `XNAS@2` evidence applies to the same 2021-08-19 through
2026-08-18 window. No inferred exchange mapping, new calendar, contract change,
or mass-ingestion mechanism was introduced.

The operational SQLite contained zero AAPL daily candles before the run. One
bounded Yahoo request then produced the following measured result:

```text
instrument: AAPL
exchange/calendar: NASDAQ / XNAS@2
currency/resolution: USD / D
stored candles: 1,254
range: 2021-08-19T04:00:00Z — 2026-08-18T04:00:00Z
first ingestion: 1,254 inserted, 0 duplicates
exact repeat: 0 inserted, 1,254 duplicates
expected sessions: 1,254
missing sessions: 0
unexpected candles: 0
completeness ratio: 1.0
SQLite integrity: ok
session checksum: acfc95f44103cff38e6e2fcbdbf06f7be6b84073d4a64aa0818268079af7ab30
```

This verifies only AAPL in the explicit window. It does not establish general
Yahoo reliability, multi-exchange support, mass-ingestion readiness,
approximately twenty-year coverage, analytical meaning, or trading authority.

Verification:

```text
focused: 34 passed
full: 2,724 passed, 4 skipped
git diff --check: clean
```
