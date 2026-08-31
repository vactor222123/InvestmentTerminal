# Phase 7 Package 71 - Numeric-Failure Recovery Audit

## Classification

AUDIT.

## Evidence reviewed

The Package 70 redacted operational report is valid schema version 1 and is
bound to the existing eligibility request and universe checksums. It selected
one of 86 terminal `RESPONSE_NUMERIC` outcomes and repeated only that raw
90-day Yahoo request. The new frame contained 48 rows, all 48 passed the exact
numeric and OHLC checks, and zero invalid rows or reasons were observed.

This does not reconstruct the original invalid value and does not prove that
all 86 outcomes will recover. It does prove that a terminal
`RESPONSE_NUMERIC` result is not necessarily a stable statement that the
instrument lacks usable price data.

## Implementation audit

The schema-3 scan currently places `RESPONSE_NUMERIC` in `_FINAL_CATEGORIES`,
not `_RETRYABLE_CATEGORIES`. Every such result is therefore `FINAL_FAILED`
immediately. Existing measured outcomes happen to have `attempt_count = 3`
because they passed through the earlier schema migrations. Schema-3 validation
also caps all provider attempts at three, and exact resume never revisits a
terminal outcome.

The read-only diagnostic cannot reconcile the checkpoint. It uses a separate
raw-frame adapter, intentionally performs no production candle conversion, and
cannot overwrite, migrate, or append eligibility evidence. Running slice 002
would therefore preserve one demonstrated stale result and 85 other
potentially stale terminal classifications while moving on to new members.

## Selected remediation

The smallest safe implementation is eligibility checkpoint/report schema
version 4 with one bounded numeric revalidation allowance:

- atomically migrate only schema-3 `FINAL_FAILED/RESPONSE_NUMERIC` outcomes
  below the new four-attempt cap to `RETRY_PENDING` before provider work;
- retain their identity, metrics-null state, measured time, category, and
  existing attempt count;
- treat a new `RESPONSE_NUMERIC` outcome as retryable only while its attempt
  count is below four;
- keep all other terminal evidence, including `RESPONSE_OHLC` and
  `NO_PRICE_DATA`, unchanged;
- preserve retry-first ordering, the 100-request invocation bound, immediate
  rate-limit halt, atomic per-outcome checkpointing, and redacted aggregate
  reporting;
- prove that a successful fourth production-client attempt replaces the stale
  failure with validated success evidence, while a repeated numeric failure is
  final at attempt four;
- reject malformed schema-4 counts and preserve exact resume after the bounded
  revalidation.

Package 72 implementation must include focused migration, success, repeated
failure, no-op preservation, privacy, CLI failure, and architecture tests. It
must not query Yahoo, edit runtime evidence, run slice 002, rank members, or
generate a ten-year batch.

## Next step

Implement the schema-version-4 numeric revalidation contract. After that
implementation is applied, run exactly one revalidation attempt and review its
redacted report before draining any remaining numeric outcomes or starting
slice 002.
