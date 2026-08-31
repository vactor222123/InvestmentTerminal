# Phase 7 Package 74 - Complete Eligibility Drain Audit

## Classification

AUDIT.

## Operational evidence

The returned schema-version-4 numeric-drain report is bound to the unchanged
request and universe checksums. It attempted 85 items and made 85 provider
requests. Successes increased from 11 to 95, retry-pending numeric outcomes
fell from 85 to zero, and no rate-limit halt or operational failure occurred.
The first 100 members are now terminal: 95 successes, three `NO_PRICE_DATA`,
and two `RESPONSE_OHLC`. Exactly 12,324 members remain never attempted.

The evidence establishes that the numeric remediation is complete. It does not
establish complete-universe eligibility or authorize ranking or ten-year
ingestion.

## Current limitation

`UniverseEligibilityScanService.run()` explicitly accepts only 1 through 100
items. The CLI invokes that service once and publishes one slice report. Passing
12,324 to `--max-items` fails validation. Repeating the CLI manually about 124
times would preserve correctness but would make progress, stopping conditions,
and operator error control unnecessarily manual.

Simply raising the existing 100-item cap is rejected. It would erase the
reviewed slice boundary without adding a run-level budget, durable aggregate
progress, or explicit stop semantics.

## Selected implementation

Add one operations-owned complete-drain coordinator and a separate CLI while
leaving the existing slice service and schema-version-4 checkpoint unchanged.
The coordinator must:

- invoke the existing service in deterministic slices of at most 100;
- accept an explicit positive run-level item budget large enough for the known
  universe but bounded to prevent an unbounded process;
- carry forward the latest atomically written private checkpoint after every
  outcome and preserve exact resume across process failure;
- stop on `COMPLETE`, `PAUSED/RATE_LIMITED`, budget exhaustion, a zero-progress
  invariant violation, or an exception;
- never sleep through or automatically retry a rate limit;
- publish one distinct versioned redacted aggregate report with run-level slice,
  attempted-item, provider-request, starting/ending coverage, halt, and failure
  evidence;
- keep member identities, values, paths, provider text, and exception messages
  private;
- make exact resume perform zero provider work when the checkpoint is complete.

The CLI must atomically write the aggregate report on success, pause, budget
exhaustion, and handled failure, then return non-zero only for failed execution.
Focused tests must cover completion across multiple slices, partial final slice,
rate-limit halt, budget exhaustion, zero progress, malformed checkpoint,
post-checkpoint report-write failure, privacy, and exact resume.

## Explicit exclusions

This audit does not run Yahoo, alter the private checkpoint, implement
concurrency, add scheduled/background execution, bypass provider controls,
rank members, generate a ten-year request, or start ingestion.

## Verification

- focused eligibility, CLI, and architecture checks: 39 passed;
- complete suite: 2,884 passed, four skipped, one existing Starlette warning;
- `git diff --check`: clean.

## Next step

Implement the bounded complete eligibility drain coordinator and CLI. After its
tests and package review, one user-executed run may process all remaining
members within an explicit total-item budget and halt safely on rate limiting.
