# Phase 7 Package 11 — Bounded XNYS Session Evidence

Baseline: `develop @ 1f2f46f80b5d52d3b7a0ac7d2f2db7a1701e0ca3`.

The focused audit selects IBM (`XNYS:IBM`) as the future controlled NYSE
instrument but performs no ingestion in this package. Official ICE/NYSE holiday
announcements cover 2021 through 2026, and an NYSE Regulation memorandum
separately records the exceptional January 9, 2025 national-day-of-mourning
closure.

The new generator emits only 2021-08-19 through 2026-08-18 as `XNYS@1`. It
preserves the NYSE hours page, three official ICE calendar announcements, the
exceptional-close memorandum, regular Eastern Time hours, early closes, and a
canonical checksum. It is not a general calendar provider.

Deterministic generator result:

```text
calendar identity: XNYS@1
session count: 1,254
range: 2021-08-19 — 2026-08-18
session checksum: 83d70a90bb334fac740a209a20bcfbfcb685de805130655cfef31134ab48e2fb
```

This package does not claim IBM candle coverage, Yahoo support for IBM,
cross-exchange equivalence, mass-ingestion readiness, analytical meaning, or
trading authority. The evidence must be generated and verified before the
separate bounded IBM ingestion step.

Verification:

```text
focused: 56 passed
full: 2,726 passed, 4 skipped
git diff --check: clean
```
