# Phase 7 Package 68 - Typed Invalid-Response Diagnostics

## Classification

IMPLEMENTATION.

## Result

Yahoo post-response validation now raises APIError-compatible typed errors.
Stable categories distinguish response shape, timestamp, numeric fields, OHLC
consistency, and eligibility candle-set validation without parsing or exposing
provider messages.

Eligibility checkpoint/report schema version 3 atomically migrates a valid
schema-2 checkpoint before provider work. Only terminal `INVALID_RESPONSE`
outcomes below the three-attempt cap become `RETRY_PENDING` with
`UNKNOWN_LEGACY_INVALID_RESPONSE`; successes, empty results, projection
failures, no-price failures, other terminal evidence, identities, metrics, and
attempt counts remain unchanged. Migrated outcomes have exactly one final
attempt available. Retry ordering, the 100-request bound, and immediate
rate-limit halt remain unchanged.

## Privacy and scope

Reports expose aggregate stable categories only. Symbols, prices, paths,
provider text, exception messages, and member metrics remain private. This
package does not query Yahoo, edit a runtime checkpoint, start slice 002, rank
members, or generate historical ingestion.

## Next step

Run one controlled schema-3 diagnostic invocation with the existing private
universe/checkpoint, unchanged window, and `--max-items 10`. Return only the
redacted report. Do not drain the remaining retries or start slice 002 before
that measurement is reviewed.
