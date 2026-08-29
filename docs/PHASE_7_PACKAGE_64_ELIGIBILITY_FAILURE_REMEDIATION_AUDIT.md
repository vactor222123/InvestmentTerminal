# Phase 7 Package 64 - Eligibility Failure Remediation Audit

## Classification

AUDIT.

## Measured trigger

The first controlled Package 63 slice is structurally valid but operationally
requires remediation:

```text
member_count = 12424
attempted_count = 100
success_count = 10
empty_count = 0
failure_count = 90
pending_count = 12324
failure_types = [APIError]
duration_seconds = 36.368634
status = IN_PROGRESS
```

The report arithmetic is consistent and its privacy boundary held. It does not
establish why 90 requests failed. Slice 002 must not run against the current
contract.

## Failure-flow audit

The repository locks `yfinance==1.6.0`. That dependency defines distinct
provider exceptions including `YFRateLimitError`, `YFPricesMissingError`,
`YFTzMissingError`, `YFTickerMissingError`, and `YFInvalidPeriodError`.

`YahooFinanceClient.get_candles()` currently catches every provider exception
and raises the same public `APIError`. Python exception chaining preserves the
original cause only in memory. `UniverseEligibilityScanService` catches that
outer error and persists only `type(exc).__name__`, so every provider failure
becomes `APIError` in both the private checkpoint and redacted report. The
existing checkpoint cannot retrospectively distinguish throttling, unavailable
prices, invalid requests, transport failures, or unexpected provider defects.

Package 63 also skips every member key already present in the checkpoint.
`FAILED` is therefore terminal exactly like `SUCCESS`, `EMPTY`, and
`PROJECTION_FAILED`. Repeating the same request performs zero provider work for
all 100 outcomes and cannot remeasure the 90 generic failures.

## Selected remediation

Implement a versioned schema-2 checkpoint/report boundary while preserving the
same universe checksum, request checksum, and fixed 90-day window.

### Privacy-safe categories

Classify the in-memory causal chain without persisting exception messages:

- `RATE_LIMITED` for `YFRateLimitError`;
- `NO_PRICE_DATA` for ticker/timezone/price-missing provider evidence;
- `INVALID_REQUEST` for `YFInvalidPeriodError`;
- `TIMEOUT` for timeout causes;
- `TRANSPORT_FAILURE` for recognized transport causes;
- `INVALID_RESPONSE` for post-response type, column, candle, or identity defects;
- `PROVIDER_FAILURE` for another recognized yfinance exception;
- `UNEXPECTED` for an unclassified exception;
- `UNKNOWN_LEGACY_API_ERROR` only when migrating a schema-1 `APIError` outcome
  whose original cause is irretrievably absent.

Do not classify by provider message text. Redacted output may contain only the
stable categories and aggregate counts.

### Schema-1 migration

Migration must be atomic and must occur before any provider request:

- preserve `SUCCESS`, `EMPTY`, and `PROJECTION_FAILED` outcomes exactly;
- convert schema-1 `FAILED/APIError` outcomes to private `RETRY_PENDING` with
  `attempt_count = 1` and `UNKNOWN_LEGACY_API_ERROR`;
- preserve other schema-1 failures as explicit final failures unless a verified
  category rule says they are retryable;
- never delete the checkpoint or reset successful evidence;
- reject identity, checksum, window, or outcome corruption.

### Retry and halt semantics

- retry `UNKNOWN_LEGACY_API_ERROR`, `RATE_LIMITED`, `TIMEOUT`, and
  `TRANSPORT_FAILURE` in later bounded invocations;
- cap a member at three provider attempts across checkpoints;
- make `NO_PRICE_DATA`, `INVALID_REQUEST`, `INVALID_RESPONSE`,
  `PROVIDER_FAILURE`, and `UNEXPECTED` final visible outcomes;
- on the first `RATE_LIMITED` outcome, checkpoint it as retryable and stop the
  current invocation immediately; do not consume the remainder of the slice;
- do not sleep, loop, or automatically schedule another invocation;
- retry-pending members precede never-attempted members in deterministic source
  order so the existing 90 failures are measured before slice 002 expands.

Schema-2 progress distinguishes `terminal_count`, `retry_pending_count`, and
`never_attempted_count`. A rate-limit stop uses explicit `PAUSED` status and
`RATE_LIMITED` halt category. It is not reported as complete or successful.

## Required implementation tests

- causal category mapping for every recognized yfinance and local validation
  family without message matching;
- atomic schema-1 migration before the first provider call;
- preservation of 10 successful outcomes and retry conversion of 90 generic
  failures in a representative checkpoint fixture;
- retry-pending-first deterministic ordering and invocation bound;
- immediate checkpoint-and-halt on rate limit;
- exact resume bypass for success/empty/projection/final failures;
- maximum-attempt transition from retry-pending to final failure;
- checksum/window/schema/corruption rejection;
- schema-2 report aggregation, privacy markers, and post-checkpoint report
  failure;
- unchanged absence of ranking, candle persistence, and ten-year batch output.

## Excluded scope

- reading, committing, or sharing the private runtime checkpoint;
- provider-message persistence or parsing;
- deleting or manually editing failed outcomes;
- automatic sleep, backoff scheduling, concurrency, or proxy rotation;
- slice 002, ranking, selection, ten-year ingestion, indicators, or valuation.

## Selected next package

Implement schema-2 causal categories, atomic schema-1 checkpoint migration,
bounded retry semantics, and rate-limit halt behavior. Then run one controlled
remediation slice with at most 10 provider attempts and return only its redacted
schema-2 report.
