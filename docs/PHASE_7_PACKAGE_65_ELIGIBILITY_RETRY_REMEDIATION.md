# Phase 7 Package 65 - Eligibility Retry Remediation

## Classification

IMPLEMENTATION.

## Result

Yahoo candle failures now receive stable privacy-safe categories by inspecting
exception types in the in-memory causal chain. No provider message is parsed,
persisted, or projected. Existing `YahooFinanceClient.get_candles()` behavior
remains APIError-compatible.

The eligibility checkpoint and redacted report advance to schema version 2.
When a valid schema-1 checkpoint is supplied, the service atomically writes its
migration before the first provider call:

- `SUCCESS`, `EMPTY`, and `PROJECTION_FAILED` evidence is preserved;
- generic `FAILED/APIError` becomes `RETRY_PENDING` with category
  `UNKNOWN_LEGACY_API_ERROR` and attempt count 1;
- known legacy timeout becomes retry-pending;
- another legacy failure becomes explicit final `UNEXPECTED` evidence;
- request, universe, identity, time-window, and metric validation remains
  fail-closed.

Retry-pending members are processed before never-attempted members. Transient
rate-limit, timeout, and transport failures remain retryable until the third
provider attempt; then they become final. No-price, invalid-request,
invalid-response, other recognized provider, and unexpected failures are final
immediately. A rate-limit result is checkpointed and halts the invocation with
redacted `PAUSED` status before another member is requested.

## Report boundary

Schema version 2 separates terminal, retry-pending, and never-attempted counts.
It exposes aggregate failure-category counts and an optional halt category.
Symbols, names, prices, paths, provider bodies, exception messages, and private
metric values remain excluded.

## Excluded scope

- automatic sleep, scheduled retry, concurrency, or proxy behavior;
- deletion or manual editing of the existing checkpoint;
- slice 002, ranking, selection, ten-year ingestion, indicators, or valuation.

## Next step

Run one controlled remediation invocation with the existing private universe
and checkpoint, the unchanged window end, and `--max-items 10`. Return only the
redacted schema-version-2 report. Keep the migrated checkpoint, universe, cache,
and member-level evidence private.
