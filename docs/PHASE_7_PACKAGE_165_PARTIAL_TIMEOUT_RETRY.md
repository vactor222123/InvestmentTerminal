# Phase 7 Package 165 — Evidence-Bound Partial Timeout Retry

## Classification

`IMPLEMENTATION`

## Verified Baseline

```text
develop @ db28c798c38db3430754199ee51ea965cabc5d6f
```

## Scope

Package 164 proved that batch 576 contains one blocking stored `TIMEOUT`, two
unrelated deferable failures, 15 successes, and two missing members. Repeating
the collection sweep cannot retry the stored timeout, while the general batch
retry would also repeat both deferable outcomes.

Package 165 implements a separate one-attempt boundary. It is reusable for any
proper partial manifest checkpoint whose immutable causal inventory proves
exactly one blocking timeout.

## Implementation

`ManifestPartialTimeoutRetryService`:

- verifies strict inventory bytes and caller-supplied SHA-256;
- requires exact manifest, batch, request, window, coverage, and causal-
  signature parity with the current private schema-4 checkpoint;
- accepts only one non-redacted `TIMEOUT` signature rooted at
  InvestmentTerminal `APIError` and containing a recognized timeout type;
- selects the matching private item internally and invokes the existing
  projected historical importer exactly once;
- replaces only that outcome and preserves successes, deferable failures,
  final exclusions, and missing members;
- retains new schema-4 causal evidence when the retry fails;
- reports `READY_FOR_SWEEP` when the outcome clears or becomes deferable, and
  `BLOCKED` for repeated timeout, rate limit, transport, persistence, or other
  systemic evidence.

The CLI validates evidence before database or provider composition, writes the
private checkpoint atomically before the detached redacted report, and exits
non-zero for `BLOCKED` or a validation/checkpoint-write failure.

## Report Contract

Schema-version-1 `MANIFEST_PARTIAL_TIMEOUT_RETRY` binds the manifest checksum,
batch index/count, request checksum, requested window, and exact inventory
checksum. Coverage exposes only aggregate before/after status and sweep-
disposition counts. `retry_result` contains transfer/omission totals plus an
allowlisted causal category/type chain when the attempt fails. It excludes
symbols, currencies, prices, paths, provider text, messages, rows, and candles.

## Failure-Path Coverage

Focused tests cover success, repeated timeout, rate limiting, a new deferable
no-price result, ambiguous timeout evidence, inventory checksum/binding
mismatch, negative duration, validation before database/provider access,
checkpoint-write failure, privacy, existing inventory behavior, sweep behavior,
resumable checkpoint behavior, and architecture dependencies.

## Scope Exclusions

- no private runtime or Yahoo execution in this package;
- no automatic retry loop, sleep, timeout deferral, or terminal exclusion;
- no processing of missing or unrelated failed members;
- no collection resume or later-batch authority;
- no change to generic refresh/import behavior, analysis, or trading.

## Verification

```text
focused timeout-retry, inventory, sweep, resumable-batch, manifest, CLI,
architecture, and documentation tests: 83 passed in 3.26s
full test suite: 3146 passed, 4 skipped, 1 warning in 28.72s
git diff --check: clean
```

The warning is the existing Starlette `httpx` deprecation warning and is not a
Package 165 regression. An earlier 18-test development run had one failing new
privacy assertion because it matched the safe word `private` in a limitation;
the assertion was narrowed to the actual exception type, then all focused and
full checks passed.

## Next Package

Prepare one exact-baseline ASCII-only PowerShell handoff for batch 576. It must
locate the unique request-bound checkpoint, verify the immutable inventory
checksum, run only the timeout retry, validate the redacted report and private
checkpoint aggregate shape without printing identities, and report read-only
SQLite integrity. Do not resume the collection sweep in the same command.
