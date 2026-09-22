# Phase 7 Package 172 — Post-Sweep Failure Remediation Audit

## Classification

`AUDIT`

## Verified Baseline

```text
develop @ 2867c6702e778f6789d9c6a4946efd59d0feb931
```

## Reviewed Evidence

Only the explicitly returned redacted schema-version-1 completed-sweep failure
inventory was reviewed. Its SHA-256 is:

```text
1ae8fb0a6b7a915bb0567b6a5b48d1b328adfe6725f282acf203b181fd5c42f6
```

The report is `SUCCESS`, binds manifest checksum
`8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a`
and completed-sweep checksum
`b8e7504cd1a6ff8b5755ed60ffde9ff20bd70a32111ea845e624105ab65be0dc`,
and reconciles all 12,019 outcomes across 601 batches. Coverage contains
11,892 successes, zero empty outcomes, 124 retryable failures, three final
failures, zero missing outcomes, and zero blocking failures.

Retryable evidence is partitioned exactly as follows:

- 113 stored `NO_PRICE_DATA` outcomes with chain
  `APIError -> YFPricesMissingError`;
- eight local `RESPONSE_OHLC` outcomes;
- two local `RESPONSE_NUMERIC` outcomes;
- one legacy outcome with null causal evidence.

The three existing final exclusions remain one reproduced `NO_PRICE_DATA`, one
stored `NO_PRICE_DATA`, and one normal-and-repaired strict numeric rejection.

The separately requested `SQLite integrity: ok` line was not returned with the
inventory. Database integrity therefore remains unverified for this package.
No private manifest, checkpoint, database, cache, identity, currency, price, or
candle was read or modified.

## Audit Findings

Collection is complete. Re-running the sweep would perform no useful provider
work because every batch is sweep-covered and every remaining retryable outcome
is currently deferable. The next problem is evidence-preserving remediation,
not further collection.

The existing `ManifestStoredNoPriceIsolationService` cannot process this state.
It deliberately requires a proper partial checkpoint, exactly one retryable or
already-final failure, and one checksum-bound per-series causal diagnostic. A
completed request checkpoint fails its partial-checkpoint guard, and a request
with multiple failures fails its one-failure guard.

The existing numeric/OHLC terminal policy is also intentionally one-series. It
requires matching normal and explicitly repaired strict-rejection reports for
the same manifest request and category. The aggregate inventory proves counts
only; it does not prove per-series row position, current response parity, or
repair rejection. Those ten outcomes cannot be terminalized from aggregate
evidence.

The one legacy null-causal outcome has no recoverable category or type chain.
It cannot be treated as no-price, local-defect, or terminal evidence. A general
manifest retry would also retry unrelated deferable outcomes from the same
request and is therefore not a safe remediation boundary.

The inventory is intentionally redacted and read-only. It can bind a future
private operation to exact aggregate evidence, but it cannot itself identify or
mutate an outcome. Any multi-checkpoint operation must retain per-checkpoint
atomic writes, explicit progress, and exact resume; it must not claim one
cross-file transaction.

## Selected Next Boundary

Implement a separate offline, inventory-bound, resumable completed-sweep
no-price transition. It must be reusable and contain no private symbol special
cases.

1. Verify the immutable inventory bytes and caller-supplied SHA-256, exact
   manifest binding, completed coverage, zero blocking evidence, and exact
   current private checkpoint set before the first write.
2. Accept only retryable schema-4 outcomes whose stored causal category is
   `NO_PRICE_DATA`, whose chain begins with the allowlisted InvestmentTerminal
   `APIError`, contains a recognized yfinance missing-price type, and contains
   no redaction or truncation marker. The measured eligible total is exactly
   113.
3. Add a distinct versioned policy identity for completed-sweep stored
   no-price evidence. Do not overload the existing one-series diagnostic policy.
   Final evidence must bind the immutable inventory checksum.
4. Process an explicit bounded number of manifest checkpoints in canonical
   order. Within one checkpoint, transition all and only eligible no-price
   outcomes in one atomic replacement. Preserve success, empty, numeric/OHLC,
   legacy-null, and existing final outcomes byte-for-value.
5. Support exact resume after any completed checkpoint write. Starting evidence
   may contain an original eligible retryable outcome or an exactly matching
   already-transitioned final outcome. Conflicting policy/evidence fails closed.
6. Emit a separate redacted versioned report with starting/current/ending
   eligible, transitioned, already-final, and remaining counts plus explicit
   completion, budget, and failure status. It must expose no identity, value,
   path, provider text, or exception message.
7. Keep Yahoo, cache, SQLite, candle ingestion, local-defect diagnostics,
   scheduling, analysis, and trading outside this boundary. A checkpoint-write
   failure must remain visible; report-write failure after committed progress
   must be recoverable by exact resume.

Focused implementation tests must cover multiple eligible outcomes in one
checkpoint, mixed failure categories, legacy null evidence, unsupported or
redacted chains, inventory/checkpoint drift, bounded progress, atomic write
failure, idempotent resume, completed zero-write resume, report privacy, and
architecture guards.

## Remediation Order After That Boundary

After the 113 no-price transitions complete, run a new read-only inventory.
Only then select an automated per-series diagnostic workflow for the eight OHLC
and two numeric defects. The legacy null-causal outcome requires a separate
single-outcome production revalidation or qualification and must never be
inferred. No numeric/OHLC retry or terminal transition is authorized now.

## Scope Exclusions

- no private runtime inspection or mutation;
- no provider request, retry, candle ingestion, or SQLite access;
- no terminalization from aggregate evidence in this audit;
- no weakening of existing one-series no-price or strict-rejection policies;
- no claim that a retryable no-price result means an instrument can never
  obtain future prices in another window or manifest;
- no analysis, recommendation, scheduling, or trading authority.

## Repository Verification

```text
focused inventory, no-price, causal-evidence, terminal-isolation, sweep, and
architecture tests: 77 passed in 4.16s
full test suite: 3154 passed, 4 skipped, 1 warning in 28.46s
git diff --check: clean
```

The warning is the existing Starlette `httpx` deprecation warning and is not a
Package 172 regression.

## Next Package

Implement the selected inventory-bound resumable no-price transition with its
new policy, versioned redacted report, atomic checkpoint ownership, focused
failure-path tests, and unchanged existing policy meanings. Runtime execution
remains a later exact-baseline operational package.
