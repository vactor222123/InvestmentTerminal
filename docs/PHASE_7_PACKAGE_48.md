# Phase 7 Package 48 - Local-Only Candidate-Absence Diagnostic Audit

## Package Type

`AUDIT`

## Verified Source Baseline

```text
develop @ 069a8fd43a60fc77d63a4c26961ba93677baab23
```

The package began from a fresh clone whose branch, exact `HEAD`, and clean
worktree were verified before inspection.

## Triggering Evidence

The controlled Package 47 run remained fail-closed with redacted report
category `CANDIDATE_TICKER_ABSENT`. Candidate-ticker filtering had already
allowed alternative listings to proceed, but the shareable schema-version-3
report intentionally did not identify the private instrument, requested
ticker, or provider tickers. Automatic ticker substitution is therefore not
justified.

## Factual Repository Seam

At candidate absence the bootstrap service already possesses the deterministic
request and batch position, private instrument key and candidate ticker,
normalized provider tickers, archived response SHA-256, run identifier, and
retrieval time. The CLI already owns explicit output paths and an atomic JSON
writer. No new provider request or durable mutation is needed to expose those
existing failure facts locally.

## Selected Contract

The smallest safe implementation is a separate local-only diagnostic:

- add an explicit required CLI path `--private-diagnostic-output`;
- carry an optional typed diagnostic on `OpenFigiBootstrapFailure` only for
  `CANDIDATE_TICKER_ABSENT`;
- write it atomically only when that category occurs;
- use a unique operator-selected path under `C:\runtime\data` per run;
- leave the shareable OpenFIGI report at schema version 3 unchanged;
- exclude identifying values and the diagnostic path from stdout, redacted
  reports, commits, ZIP artifacts, and AI handoffs.

The private diagnostic schema version 1 contains exactly:

```text
schema_version
run_id
retrieved_at
failure_category
request_ordinal
batch_number
instrument_key
candidate_ticker
provider_tickers
response_sha256
```

Ordinals are one-based. `provider_tickers` is sorted, duplicate-free, and
normalized. Raw response content, FIGIs, exchange codes, paths, quote values,
and unrelated instruments are excluded.

## Failure and Side-Effect Rules

- Candidate absence still terminates the bootstrap.
- The immutable raw-response archive remains the authoritative provider
  evidence and is not replaced by this diagnostic.
- The diagnostic is written before the redacted failure report.
- Diagnostic-write failure remains non-zero, leaks no private values or paths,
  and uses the existing redacted `INPUT_OR_RUNTIME_FAILURE` category.
- Metadata stays unmodified on candidate-absence and diagnostic-write failures.
- The CLI does not delete an earlier artifact; a unique path is an operational
  precondition.
- No provider ticker is adopted and no private quote file is edited.

## Required Implementation Tests

- exact typed diagnostic construction for candidate absence;
- one-based ordinals and deterministic ticker sorting/deduplication;
- exclusion of FIGIs, raw bodies, exchange codes, and paths;
- atomic private diagnostic output;
- unchanged schema-version-3 redacted report;
- private-value/path absence from stdout and the redacted report;
- diagnostic-write failure is non-zero with no metadata mutation;
- existing archive, alternate-listing, categorized-failure, and architecture
  guards remain green.

## Explicitly Deferred

Another private run, automatic ticker correction, AI inspection of private raw
responses, quote qualification, valuation, integrated review execution,
multi-instrument expansion, and Phase 8 UI work remain excluded.

## Audit Result

`IMPLEMENTATION-READY`

Package 49 can implement this bounded diagnostic without changing the provider
contract, metadata acceptance rules, or shareable report schema.

## Verification

- focused OpenFIGI and architecture suite: 32 passed;
- complete local suite: 2,811 passed, 4 skipped;
- one existing Starlette deprecation warning;
- `git diff --check`: clean.
