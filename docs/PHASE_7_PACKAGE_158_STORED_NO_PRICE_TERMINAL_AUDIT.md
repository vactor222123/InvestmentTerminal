# Phase 7 Package 158 — Stored No-Price Terminal Audit

## Classification

`AUDIT`

## Verified Baseline

```text
develop @ d146eafb5e7c3628672eabba6b2de9762b481d2d
```

## Reviewed Evidence

Only the explicitly returned redacted schema-version-1
`MANIFEST_PARTIAL_CAUSAL_EVIDENCE_DIAGNOSTIC` report was reviewed. The private
manifest, checkpoint, cache, database, symbols, currencies, prices, provider
payloads, and candles were not read or modified. No provider request was made.

Report SHA-256:

```text
509769c10ef7a4617104b80c5ed3ca626cd763e98c97e76353d52586507b64ef
```

The report is strictly bound to manifest checksum
`8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a`,
batch 109 of 601, request checksum
`a3b00484a202f114f2051f0568f1ed61c0d79535415266ebba120c15134c0a34`,
and the half-open ten-year window from 2016-09-05 to 2026-09-05 UTC. It records:

```text
status = EVIDENCE_AVAILABLE
requested_count = 20
checkpoint_outcome_count = 1
missing_count = 19
failed_candidate_count = 1
selected_count = 1
checkpoint_failure_types = APIError
category = NO_PRICE_DATA
exception chain = APIError -> YFPricesMissingError
failure = null
```

This is the causal evidence captured by the schema-version-4 checkpoint at the
original failure boundary. It is not a later reproduction and does not require
another Yahoo request.

## Audit Findings

The existing `REPRODUCED_YAHOO_NO_PRICE_DATA_V1` transition cannot consume this
report safely. Its semantics and validator require a distinct
`MANIFEST_PARTIAL_FAILURE_QUALIFICATION` report produced by a later provider
request, null coverage, a fixed qualification failure reason, and
`partial_failure_qualification_checksum` evidence. Relabeling the stored
diagnostic as that qualification would falsify provenance.

The existing strict numeric/OHLC policy is also inapplicable. It requires
matching normal and repaired strict-projection rejection and intentionally does
not accept provider-level missing-price evidence.

Checkpoint schema 4 already owns the required causal evidence and a
policy-discriminated `FINAL_FAILED` envelope. Collection sweep, ordered drain,
manifest execution, and checkpoint diagnostic consumers already delegate final
outcome validation to `ResumableMarketBatchService._outcomes` and aggregate
policy-independent final category evidence. They do not need public report or
SQLite changes for a new stored-evidence policy.

## Selected Contract

Implement one separate offline transition with policy identity
`STORED_YAHOO_NO_PRICE_DATA_V1`.

1. The service accepts strict UTF-8 bytes of one checksum-bound
   `MANIFEST_PARTIAL_CAUSAL_EVIDENCE_DIAGNOSTIC` report and verifies the supplied
   SHA-256 before any checkpoint change.
2. Manifest, batch, request, window, proper-partial selection counts, stored
   `APIError`, report status `EVIDENCE_AVAILABLE`, category `NO_PRICE_DATA`, and
   the allowlisted causal type chain must match exactly.
3. The report's causal object must equal the retryable checkpoint outcome's
   stored `causal_failure_evidence`. A merely valid but different report cannot
   authorize transition.
4. The chain must start with
   `investment_terminal.utils.exceptions.APIError` and contain a recognized
   yfinance missing-price type. Legacy null evidence, another category, an
   unrecognized or redacted missing-price type, and a truncated chain fail
   closed.
5. Only the selected retryable outcome changes to schema-4 `FINAL_FAILED` with
   outer `failure_type=APIError`, category `NO_PRICE_DATA`, the new policy, and
   `causal_evidence_diagnostic_checksum`. The other outcome fields and all 19
   missing request members remain untouched.
6. The new operation has its own schema-version-1 redacted identity
   `MANIFEST_STORED_NO_PRICE_ISOLATION`. It reports exact binding, policy,
   category, evidence checksum, and aggregate coverage without private values.
7. Exact matching repeat is idempotent. Conflicting final evidence, complete or
   empty checkpoints, duplicate keys, non-finite JSON, unsupported schemas,
   mismatched bindings/counts/checksum/evidence, or any other status/category
   fails before write.
8. The CLI writes the private checkpoint atomically before the detached report.
   Checkpoint-write failure cannot claim success; report-write failure after
   checkpoint commit is recoverable by exact idempotent repeat.

The checkpoint remains schema version 4 because the outcome envelope is
unchanged and the policy identity versions the new evidence interpretation.
Existing `REPRODUCED_YAHOO_NO_PRICE_DATA_V1` and
`NORMAL_AND_REPAIRED_STRICT_REJECTION_V1` meanings remain immutable.

## Rejected Shortcuts

- Do not rerun Yahoo to reproduce evidence already captured at failure time.
- Do not pass this diagnostic to the reproduced-evidence CLI.
- Do not broaden the existing reproduced policy or change its evidence key.
- Do not terminalize generic `APIError`, empty data, timeout, rate limiting,
  legacy null evidence, or an arbitrary no-price message.
- Do not serialize exception messages, provider text, paths, or identities.
- Do not combine implementation, runtime checkpoint mutation, sweep resume, or
  batch 110 execution with this audit.

## Verification

```text
focused checkpoint, causal-evidence, isolation, sweep/drain, and architecture tests: 94 passed in 3.34s
full test suite: 3102 passed, 4 skipped, 1 warning in 29.77s
git diff --check: clean
```

The warning is the existing Starlette `httpx` deprecation warning and is not a
Package 158 regression.

## Next Package

Implement the selected stored-evidence transition, validator extension, CLI,
privacy checks, exact-match/idempotency/conflict tests, and atomic-write failure
paths. Do not contact Yahoo, open SQLite, mutate private runtime evidence,
resume batch 109, or execute batch 110. A later operational package must perform
the transition and return its redacted report before collection resumes.
