# Phase 7 — bound split symbol resolution

## Audit and scope

IMPLEMENTATION, fresh develop baseline
`0fa9e6d72adc8fd1fba2943896cfb415f0bd2b16`.
The explicitly returned provider diagnostic observed TIMEZONE_MISSING during
HISTORY_OR_METADATA, one application invocation, no snapshot, exit 1.
Diagnostic file SHA-256:
`df4510f3ac6636746903e01c6c1877c9c60e9e3d24c67c845625c34100332363`.
Original collection report SHA-256:
`52fc890cf9c6264dcea9e742f2573354e1ee2026ec8b4f0caae868feadde46f5`.
This is not evidence of delisting, no splits, or the original failure's cause.
An internal portfolio symbol may differ from a provider listing; this is a
hypothesis to test, not an observed private identity. No private runtime data,
provider network calls or database writes were used in this implementation.

## Bounded flow

1. Pin the diagnostic; validate its missing-timezone/price category and original
   report/selection/CSV bindings; reconstruct exactly the failed request.
2. Search the existing ISIN once using the existing Yahoo search service (maximum
   25 returned rows). Retain candidates privately.
3. Require a unique exact match to the original CSV exchange_ticker, compatible
   quote type and provided currency. Never pick the first or invent a suffix.
4. Only then invoke the existing action collector once for the matched symbol
   and original request window. Check exact metadata currency/type again:
   search normalization alone must not conflate GBP and GBp.
5. Persist separate private resolution/snapshot and redacted aggregate. Verify
   readbacks and all input hashes again. Preserve all old outputs and source data.

One invocation is not a guarantee of one HTTP request inside yfinance.
Missing ISIN/ticker, no match, ambiguous match and metadata disagreements are
explicit blockers. Provider failure is FAILED. Successful collection is only
RESOLVED_CANDIDATE, with UNVERIFIED_BROKER_MAPPING and adjustment_performed=false.
Search cannot independently certify broker listing identity. Missing candidates
do not prove absence. A null snapshot hash does not rule out a partial artifact.
Source changes or late output failures return nonzero; preserve outputs and do
not automatically retry, even if a report was already written.

## Operational handoff

After package application and confirmation of the applied SHA, invoke
`python -B -m investment_terminal.cli.portfolio_split_resolve` with:

- --diagnostic-report: returned portfolio_split_provider_diagnostic report;
- --diagnostic-report-sha256: exact diagnostic hash above;
- --collection-report: original portfolio_split_collection report;
- --snapshot-directory: existing private collection snapshot directory;
- --cache-directory: dedicated separate Yahoo cache directory;
- --report-output: a new redacted report filename.

The original CSV and selection are discovered by their existing bindings.
No manual market data entry is requested. Send only the redacted report and
exit code; DO NOT SEND CSV, private selection/candidates, snapshots, cache or DB.
Do not resume the batch or promote a resolved candidate automatically.
Production split closure still needs broker identity, known price basis and
operational adjustment qualification; existing Yahoo prices must not be adjusted
twice. No existing JSON contract or dependency direction changed.

## Verification

Focused: 217 passed, including 28 new resolution tests. Full: 3713 passed,
4 skipped, one existing Starlette deprecation warning. git diff --check: clean.
Tests cover missing/ambiguous identity, malformed and oversized responses,
typed provider failures, currency units, checksum/source drift, locks, overwrite
protection, persistence/readback/tampering failure and invocation limits.
All inputs are synthetic. Test artifacts are excluded from delivery.
