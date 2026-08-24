# Phase 7 Package 14 — Controlled Five-Year IBM/XNYS History

Baseline: `develop @ e9a652abe3af7c2adc6cade6a9a713be8623bf83`.

The runtime `XNYS@1` evidence passed the existing provenance and canonical
session-checksum verifier. One bounded IBM Yahoo ingestion then populated the
operational SQLite for the exact half-open 2021-08-19 through 2026-08-19
window:

```text
downloaded: 1,254
inserted: 1,254
duplicates: 0
stored total: 1,254
earliest candle: 2021-08-19T04:00:00Z
latest candle: 2026-08-18T04:00:00Z
```

The exact repeat downloaded the same 1,254 candles, inserted zero rows,
reported 1,254 duplicates, and preserved the stored total. This establishes
idempotency for this explicit request.

History-owned coverage evaluation against `XNYS@1` measured:

```text
expected sessions: 1,254
observed sessions: 1,254
missing sessions: 0
unexpected candles: 0
completeness ratio: 1.0
is complete: true
session checksum: 83d70a90bb334fac740a209a20bcfbfcb685de805130655cfef31134ab48e2fb
SQLite integrity: ok
```

Operational artifact SHA-256 values:

```text
yahoo_ibm_ingestion_5y.json:
a5793b84cbeb31a292faa07f2ec0d71cd31edb88b0ea89cb6e1903064e55395e
yahoo_ibm_ingestion_5y_repeat.json:
f086529d3fa7a73719702dac5afb068bb75582c1852b5ccbc8df521e08d04a0b
ibm_xnys_coverage_5y.json:
9da753efcc9b83cc553dfa6b0f42b8b224ec7854b7de5a7d1491cd537ac92e21
xnys_sessions_2021-08-19_2026-08-18.json:
5dfaae78397ac4a3e1f51512f206f3731dc8e294fdd917abe96525f31ed60514
```

This result establishes only bounded IBM/XNYS coverage. It does not authorize
mass ingestion, claim approximately 20-year coverage, or select another
instrument. The next package must audit the measured Phase 7 state and select
one smallest evidence-backed operational gap.

Verification:

```text
focused: 31 passed
full: 2,726 passed, 4 skipped
existing warnings: 1 Starlette deprecation warning
git diff --check: clean
```
