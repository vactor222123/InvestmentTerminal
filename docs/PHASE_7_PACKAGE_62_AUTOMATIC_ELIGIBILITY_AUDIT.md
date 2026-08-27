# Phase 7 Package 62 - Automatic Eligibility Audit

## Classification

AUDIT.

## Measured starting point

The controlled Package 61 qualification succeeded with 13,184 source rows and
12,424 unique accepted members: 5,653 ETFs and 6,771 non-ETFs. There were no
normalized-key collisions. The source universe is therefore large enough for
the research objective, but it is not yet an ingestion universe. Automatically
requesting ten years for every member would be an unmeasured mass operation.

## Source audit

Nasdaq's yearly Daily Market Files contain market-level daily statistics, not a
per-security eligibility table. Nasdaq also publishes daily/monthly volume
statistics by symbol, but those statistics describe activity executed or
reported through Nasdaq-operated venues and carry separate usage terms. They
must not be represented as consolidated all-venue liquidity or silently used as
the product's neutral ranking authority.

The existing Yahoo chart boundary already returns the daily OHLCV facts needed
to measure provider availability and recent traded value for the same symbols
that will later enter historical ingestion. Reusing it avoids a second symbol
mapping and measures the actual downstream provider path.

## Selected automatic boundary

Implement a resumable eligibility scan over the complete private Package 61
universe. The operator supplies the universe evidence and runtime destinations,
not instrument identities. Each invocation processes a deterministic bounded
slice of at most 100 pending members and atomically checkpoints outcomes.

For every member, preserve private evidence for:

- source identity and Yahoo projection;
- provider outcome category;
- provider instrument type where returned;
- requested and observed time bounds;
- valid daily-candle count;
- positive-volume day count;
- median daily traded value calculated as `close * volume`;
- measured-at timestamp and evidence/checkpoint schema version.

Use a fixed 90-calendar-day recent window whose exact UTC bounds are recorded
in the request evidence. Provider failures and unsupported projections remain
isolated outcomes. No failed member may stop unrelated members.

## Completion and selection rule

Progress reports may expose only aggregate counts and failure categories. They
must never expose member identities or prices.

No ranked ingestion universe may be emitted until every accepted Package 61
member has one terminal eligibility outcome for the same request and window.
After completion, a separate package may define transparent minimum data
quality and ranking rules, version them, and select a bounded mass universe.
This prevents an alphabetical first-slice bias and avoids inventing an
unvalidated liquidity threshold.

Exact resume must do zero provider work for terminal outcomes. A changed input
universe, window, or eligibility schema requires a distinct request identity.

## Required implementation tests

- deterministic pending-member selection and 100-member upper bound;
- exact-resume provider bypass;
- isolated timeout, malformed payload, empty history, and projection failure;
- rejection of mismatched universe checksum, request window, and schema;
- atomic checkpoint/report writes and explicit post-checkpoint report failure;
- no ranking or ingestion output before complete-universe terminal coverage;
- redacted report contract with no symbols, names, prices, paths, or exception
  text.

## Excluded scope

- ten-year candle ingestion;
- selection of a final universe size or liquidity cutoff;
- market-cap, fundamentals, sectors, index membership, or name-based typing;
- concurrency, scheduler, indicators, valuation, or ChatGPT conclusions;
- manual instrument lists or manual quote entry.

## Selected next package

Implement the bounded resumable 90-day Yahoo eligibility scan and its private
checkpoint plus redacted progress report. Then run one controlled first slice.
Do not generate a ten-year batch until the complete universe scan has been
measured and a later versioned selection rule has been audited.
