# Phase 7 Package 49 - Bounded Local-Only Candidate-Absence Diagnostic

## Package Type

`IMPLEMENTATION`

## Verified Source Baseline

```text
develop @ 4fa45387964ac38ec1d973ab0642d6696d3f0cd8
```

The package began from a fresh `develop` clone with exact `HEAD` and a clean
worktree.

## Implemented Boundary

`OpenFigiCandidateAbsenceDiagnostic` is a typed Portfolio-owned private
contract. On `CANDIDATE_TICKER_ABSENT`, the bootstrap failure carries one
schema-version-1 document containing the run/time, one-based request and batch
ordinals, private instrument key, candidate ticker, sorted unique provider
tickers, and archived response SHA-256.

The CLI now requires `--private-diagnostic-output`. It atomically writes the
private document only for candidate absence and before writing the redacted
failure report. Success and other failure categories create no diagnostic.

The shareable report remains schema version 3 with its exact existing shape.
Private identities, tickers, diagnostic path, FIGIs, raw response data, and
provider exchange codes remain absent from it and from stdout.

## Failure Semantics

- Candidate absence remains non-zero and does not write metadata.
- A private diagnostic write failure remains non-zero, writes the redacted
  report with existing `INPUT_OR_RUNTIME_FAILURE`, and does not expose the
  private exception message or path.
- Exact raw response bytes remain preserved in the private exclusive archive.
- No provider ticker is adopted automatically.
- No transaction, quote, valuation, or Review state is modified.

## Focused Coverage

Tests cover exact diagnostic serialization, second-batch/global ordinals,
ticker normalization/sorting/deduplication, exclusion of FIGI/exchange details,
atomic CLI output, report/stdout redaction, no artifact on unrelated outcomes,
and diagnostic-write failure without metadata mutation.

## Explicitly Deferred

- controlled private OpenFIGI rerun;
- operator review and correction of the identified private quote entry;
- offline quote qualification and valuation;
- automatic correction or listing selection;
- multi-instrument expansion and Phase 8 UI.

## Result

`IMPLEMENTED`

## Verification

- focused OpenFIGI/privacy/architecture suite: 36 passed;
- complete local suite: 2,815 passed, 4 skipped;
- one existing Starlette deprecation warning;
- `git diff --check`: clean.
