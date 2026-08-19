# Phase 7 Package 9 — Controlled Five-Year MSFT History

Baseline: `develop @ b04990d1e2f35f1b38e404cc9728e582da74647d`.

Official Nasdaq annual trading-calendar documents cover 2021 through 2026.
Version 2 evidence also cites Nasdaq Equity Trader Alert 2025-1 because the
annual 2025 calendar predates the exceptional January 9, 2025 closure for
President Jimmy Carter's national day of mourning.

The existing one-year `XNAS@1` generator remains unchanged. The new explicit
`five-year` option emits only 2021-08-19 through 2026-08-18 as `XNAS@2`, carries
the primary calendar URI plus every annual source URI and the exceptional-close
alert, and rejects malformed multi-source provenance before coverage evaluation.
It is bounded evidence, not a general calendar provider.

Operational result:

```text
MSFT daily candles: 1,254
range: 2021-08-19T04:00:00Z — 2026-08-18T04:00:00Z
first ingestion: 1,003 inserted, 251 duplicates
exact repeat: 0 inserted, 1,254 duplicates
XNAS@2 expected sessions: 1,254
missing sessions: 0
unexpected candles: 0
completeness ratio: 1.0
SQLite integrity: ok
session checksum: acfc95f44103cff38e6e2fcbdbf06f7be6b84073d4a64aa0818268079af7ab30
```

This establishes only the measured MSFT/XNAS window. It does not claim general
Yahoo reliability, twenty-year coverage, multi-instrument readiness,
analytical meaning, or trading authority.

Verification:

```text
focused: 54 passed
full: 2,724 passed, 4 skipped
git diff --check: clean
```
