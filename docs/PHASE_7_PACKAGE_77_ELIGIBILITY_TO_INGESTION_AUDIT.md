# Phase 7 Package 77 - Eligibility-to-Ingestion Audit

## Classification

AUDIT.

## Measured input

The reviewed complete-drain report is valid schema version 1 and is bound to
the established request and universe checksums. All 12,424 members are terminal:
12,020 `SUCCESS`, 404 `FINAL_FAILED`, and zero empty, projection-failed,
retry-pending, or never-attempted outcomes. The final run used 73 slices and
7,005 provider requests without a halt or failure.

The 99 requests above the 6,906 initially pending members are bounded retries,
not evidence that terminal members were rescanned.

## Repository audit

The private schema-version-4 eligibility checkpoint contains the only direct
member-to-Yahoo-symbol association plus measured 90-day liquidity fields.
The redacted report intentionally cannot generate ingestion identities.

`MarketBatchRequest` accepts only 1 through 20 unique symbol/currency items.
`ResumableMarketBatchService` is one request/checkpoint boundary and explicitly
does not authorize mass ingestion. No current operation validates a complete
eligibility checkpoint and projects only its `SUCCESS` members into a durable
private ingestion universe. There is also no reviewed contract for partitioning
12,020 identities into hundreds of ten-year requests.

## Selected next package

Implement a read-only eligibility-success projection before any historical
ingestion. It must:

- require the matching private universe and complete schema-4 checkpoint;
- fail closed unless all universe members are terminal and no retry is pending;
- include only `SUCCESS` outcomes and exclude all 404 final failures;
- retain deterministic source identity and Yahoo symbol privately;
- bind output to the eligibility request/universe checksums;
- publish the private versioned projection atomically;
- publish a separate redacted report with only total/success/excluded counts,
  checksums, timing, normalized failure, and limitations;
- grant no ranking, currency inference, ten-year request generation, ingestion,
  scheduling, or trading authority.

Currency and ten-year partition policy remain later explicit boundaries. The
eligibility request used the existing USD candle contract, but this audit does
not infer a reusable ingestion currency merely from listing membership.

## Explicit exclusions

This package does not read the private checkpoint, generate the projection,
query Yahoo, create batch requests, rank instruments, or persist candles.

## Verification

- focused eligibility, drain, batch, and architecture checks: 49 passed;
- complete suite: 2,891 passed, four skipped, one existing Starlette warning;
- `git diff --check`: clean.

## Next step

Implement the private complete-success projection and its redacted
qualification report with focused completeness, checksum, exclusion, privacy,
atomic-write, malformed-input, and architecture tests.
