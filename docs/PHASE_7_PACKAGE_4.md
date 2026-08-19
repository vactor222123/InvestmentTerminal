# Phase 7 Package 4 — Stored Candle Coverage Measurement

## Verified baseline and evidence

`develop @ b23f37267e7b84a678a4d08d049e6f36bd7caaf1`

The first bounded MSFT ingestion inserted 12 daily candles. An exact repeat
downloaded 12, inserted zero, reported 12 duplicates, and retained 12 stored
rows. SQLite integrity and stored boundaries were independently read-only
verified.

## Change

`CandleRepository.get_earliest` complements the existing indexed latest query.
Ingestion report schema version 2 now records stored candle count, earliest and
latest timestamps, and elapsed observed span after persistence. Failure leaves
coverage unknown. No complete history is loaded to calculate these bounds.

## Limits and next action

Elapsed span does not measure expected-session completeness or gaps. This
package adds no bulk orchestration, scheduling, retry, analysis, or trading.
Next, run one MSFT daily request beginning 2025-08-19 against the same database
and inspect the measured report before selecting broader scope.
