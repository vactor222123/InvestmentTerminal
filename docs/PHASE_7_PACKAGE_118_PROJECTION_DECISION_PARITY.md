# Phase 7 Package 118 - Projection Decision Parity

Classification: `IMPLEMENTATION`. Fresh `develop` baseline:
`0195690547a0c9566de91bf33ecc55dccbc3a560`.

The Yahoo adapter now owns immutable
`YahooTrailingIncompleteAssessment` evidence for policy
`DAILY_SINGLE_TRAILING_NON_FINITE_NUMERIC_V1`. Its closed status and rejection
vocabularies distinguish resolution, frame shape, timestamp normalization,
uniqueness/order, invalid-row multiplicity/position, predecessor, numeric/sign,
and partial finite-OHLC guards without values or identities.

The production projected path consults this assessment before permitting an
omission and then strictly projects the validated prefix. Strict legacy import,
generic refresh, weekly/monthly behavior, and every existing rejection remain
unchanged.

The manifest failed-series diagnostic evaluates its already-fetched in-memory
frame through the same provider-owned assessment, so it makes no second Yahoo
request. Its report advances to schema version 2 and adds only policy identity,
`ELIGIBLE`/`REJECTED`, stable rejection reason, and typed omission evidence.
The generic raw analyzer and eligibility diagnostic remain schema version 1.

The service remains read-only and has no database, repository, importer, or
checkpoint writer. This package performs no runtime request and authorizes no
ingestion or later batch.

Next, run exactly one manifest failed-series diagnostic for batch 19 and review
its schema-2 projection assessment. Do not retry ingestion or execute batch 20
before that result.

Verification:

- focused Yahoo/assessment/raw/manifest/architecture tests: 82 passed;
- complete suite: 3,012 passed, 4 skipped, one existing Starlette warning;
- `git diff --check`: clean.
