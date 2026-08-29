# Phase 7 Package 67 - Eligibility Invalid-Response Audit

## Classification

AUDIT.

## Measured trigger

The bounded retry drain completed all 80 remaining legacy retries. Cumulative
coverage is 10 successes, two `NO_PRICE_DATA` failures, and 88
`INVALID_RESPONSE` failures. No retry-pending outcome or rate-limit halt remains;
12,324 universe members have not been attempted.

## Code-path finding

The current category does not identify one provider defect. A direct
`APIError` without a causal exception is mapped to `INVALID_RESPONSE`.
`YahooFinanceClient` raises that same direct type for all of these distinct
post-response conditions:

- non-DataFrame response;
- missing OHLCV columns;
- invalid timestamp type;
- non-numeric, non-finite, zero, or negative price fields;
- invalid volume;
- inconsistent candle high or low.

The eligibility service also maps its own `TypeError` and `ValueError` checks to
the same category. Those checks cover a non-list candle collection, identity or
window mismatch, invalid values, and non-unique or unordered timestamps.

The schema-version-2 checkpoint persists only `INVALID_RESPONSE`, with no typed
sub-category. All 88 outcomes are `FINAL_FAILED`, so exact resume performs no
provider requests for them. Neither the redacted report nor the private
checkpoint can now distinguish which validation boundary failed. Provider text
must not be used to reconstruct the missing fact.

## Audit conclusion

The 88 failures do not establish a Yahoo outage, a symbol-projection defect, or
invalid securities. The current contract erased the evidence needed to choose
among those explanations. Starting slice 002 would repeat an unmeasured failure
mode over new members.

## Selected remediation

Implement one versioned schema-3 diagnostic boundary:

- replace direct client validation errors with APIError-compatible typed errors
  carrying stable code-owned categories, never provider text;
- distinguish client response-shape, timestamp, numeric-price/volume, OHLC, and
  service candle-set validation families;
- atomically migrate schema-2 `FINAL_FAILED/INVALID_RESPONSE` outcomes to
  `RETRY_PENDING` as `UNKNOWN_LEGACY_INVALID_RESPONSE`, preserving their attempt
  count and all successful/no-price evidence;
- allow only the remaining third attempt for those migrated outcomes;
- keep the first rate-limit halt and 100-request invocation cap;
- expose only aggregate stable categories in the redacted report.

After implementation, run 10 diagnostic retries before draining the remaining
78. Slice 002, ranking, and ten-year ingestion remain blocked until the typed
measurement is reviewed.

## Required tests

- every direct Yahoo client validation exit maps to its stable category;
- APIError compatibility and absence of message parsing are preserved;
- schema-2 migration preserves 10 successes and two no-price failures while
  converting 88 legacy invalid responses to third-attempt retry-pending;
- migration is written before provider work;
- exact retry ordering, attempt cap, rate-limit halt, report privacy, and
  corrupted-checkpoint rejection remain covered.
