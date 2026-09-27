# Phase 7 — Explicit Weekly Rate-Limit Resume

Classification: `IMPLEMENTATION`. Fresh clean `develop` HEAD exactly matched
the caller's `5b7905df339c98a6c7d48f54e51e7f6a70ed112f` baseline.

The returned 2026-09-23 weekly drain report is `HALTED` after 58 attempts in
part 003. Cumulative coverage is 5,178 of 11,892 selected series, with 6,714
unattempted, 4,978 successes, 200 isolated failures, and one `RATE_LIMITED`.
The user reported read-only SQLite integrity `ok`. The three-part drain added
44,326 candles relative to the previous 1,120-series report. No private
checkpoint, database, or per-series identity was reviewed here.

The existing schema-version-1 weekly service checkpoints `RATE_LIMITED` as a
failed outcome and halts. Ordinary exact resume skips every existing outcome,
including that transient failure. Immediately repeating ordinary collection
would therefore leave this series failed without another attempt. The
provider's reset time is unknown; this package makes no live request.

An explicit `--retry-rate-limited` mode now selects checkpointed
`FAILED/RATE_LIMITED` outcomes first in manifest order, before never-attempted
series. It requires at least one such outcome, retains the existing per-run
item budget, and stops on the first new rate limit. On a successful retry, the
same atomic checkpoint writer replaces only that outcome; other outcomes are
preserved. Existing candle overlap and persistence checks remain unchanged.
If SQLite commits but the checkpoint write fails, repeating the same retry
reconciles through idempotent candle insertion.

Default CLI behavior, private checkpoint schema version 1, and public report
schema version 1 remain unchanged. The opt-in report uses schema version 2:
`budget.retry_rate_limited=true`, with
`coverage.current_run_retry_count` and `coverage.current_run_new_count` summing
to `current_run_attempted_count`. Because retries replace existing outcomes,
completed coverage need not grow by the attempted count. The report remains
aggregate-only; neither it nor the CLI prints symbols, candle values, paths,
provider text, or exception messages.

Next, after applying this package and allowing the provider restriction to
clear, run one `--retry-rate-limited --max-items 1` qualification against the
unchanged private checkpoint and exclusive end. Review only its redacted
schema-2 report and SQLite integrity before continuing the other 6,714
series. Volume-only drift and numeric/no-price failures remain separate.
