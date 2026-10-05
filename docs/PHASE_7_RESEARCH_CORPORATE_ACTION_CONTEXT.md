# Phase 7 — corporate-action context in generic research exports

Classification: `IMPLEMENTATION`. Fresh clean GitHub `develop` matched
`0b440ccb1571ba501137afd246b78d9124c7abe8` exactly. Mandatory documents
were checked against the fully read preceding package and are unchanged.
EODHD remains paused. No provider, private runtime input, or operational
database was accessed during this package.

## Focused audit and change

The preceding package implemented normalized dividend/split collection and
validated snapshots, but neither research export consumed those observations.
The existing export and local verifier have exact schema-1 key sets; silently
adding an action field would break that contract. The selected bounded change
is explicit schema 2 in both existing export commands, plus matching verifier
support, using one shared pure context projector. No new downloader, command
family, SQLite schema, indicator or portfolio calculation is introduced.

## Command contract

Existing `instrument_research_export` and `instrument_research_run` retain
schema 1 as their default. Explicit schema 1 produces identical bytes to the
omitted option. Existing failed-report shape and CLI behavior are preserved.
Action options with schema 1 are rejected rather than silently ignored.

For schema 2 add:

```text
--schema-version 2
--actions-as-of <explicit UTC ISO-8601 time>
--actions-maximum-age-days <integer 1..365>
```

Optionally supply both:

```text
--actions-snapshot <absolute private snapshot path>
--actions-sha256 <pinned exact-file SHA-256>
```

The first three options are mandatory for schema 2; no wall-clock or implicit
freshness threshold is chosen. The existing selected symbol, history window,
projection checksum and profile/manifest/checkpoint/SQLite arguments still apply.
The action file must be distinct from inputs/outputs, and profile composition
rejects action snapshots under the report directory. The action file is bounded,
strictly reconstructed and checked against the caller's SHA-256 before opening
SQLite. Its exact symbol, case-sensitive quote currency, start and exclusive end
must match the selected research export. No inferred alias or window trimming.

An explicitly supplied absent, corrupt, mismatched or future-dated snapshot is
a failure, not `MISSING`. Omitting the snapshot/checksum pair deliberately
produces `MISSING`. Collection remains the separate `yahoo_corporate_actions`
command; export never downloads a replacement automatically.

## Availability and scope

`ResearchActionPolicy` and `project_action_context` own the deterministic rule:

- `MISSING`: no snapshot was supplied; event counts and checksums are null.
- `AVAILABLE`: a valid matching snapshot was fetched at or before `as_of`, with
  age no greater than the explicit maximum.
- `STALE`: a valid matching snapshot exceeds that age; its observations remain
  included with that label.

The explicit evaluation time must be at or after the research exclusive end.
A snapshot fetched after that evaluation time is rejected. This is availability
of a provider-normalized artifact as assessed at a chosen time, not historical
point-in-time market knowledge, present-day freshness, complete corporate-action
coverage or verified adjusted returns. A stale/missing context may accompany a
`COMPLETE` raw-price export: completion describes successful export, not universal
analytical readiness. Zero observed actions are distinct from missing evidence.

Cash event currency remains null and its historical per-share adjustment basis
unverified. `GBp` is not treated as `GBP`. Attaching a split does not apply it to
candles. Existing `STORED_CLOSE_NO_EXPLICIT_ADJUSTMENT`, OHLCV and SMA values are
unchanged. No dividend is posted to the portfolio and no return is calculated.

## New schema and evidence bindings

Schema 2 preserves the schema-1 fields and adds `corporate_actions`. Private
context embeds the complete validated schema-1 normalized snapshot, with its
source version, window, UTC/local dates, fetch time, units and limitations.
Redacted context contains no embedded snapshot, identity, currency, event dates,
event values or paths; it includes:

- fixed normalized-layer and factual-context labels;
- explicit evaluation time, maximum age and availability;
- exact source-file SHA-256, validated at acquisition into this export;
- canonical complete-snapshot SHA-256, including fetch time;
- normalized-content SHA-256, excluding fetch time as in the source contract;
- aggregate event counts and capital-gains field presence;
- unknown completeness and unchanged limitations.

The separate full-document hash prevents unnoticed changes to the embedded
fetch time as well as events. A content checksum alone would not bind that time.
The objects are detached: altering the returned private dictionary cannot change
the original schema-1 pair or redacted context.

## Verification and failure behavior

The existing `instrument_research_verify` command accepts both versions without
new flags. Its schema-2 path reconstructs the embedded model, recomputes the full
context with the same projector and checks exact private/report parity, including
strict types, units, counts, availability and hashes. It then applies all existing
schema-1 candle/indicator/identity rules. An embedded snapshot with a recomputed
content hash still cannot pass an unchanged caller-pinned report if its content
or fetch time changed.

The verifier reads only the pair and the caller-pinned report SHA-256. It does
not reopen the original action file, authenticate provider data, prove licensing
or certify action completeness. Exact source-file checksum is the acquisition
binding recorded by the exporter; canonical embedded-document parity is what
the offline verifier can recompute. These are different claims.

Schema-2 export calls that same verifier before writing its artifacts. As a
result, a narrow history window omitting part of the latest indicator sample
fails rather than producing an export that the verifier would reject. Schema-1
producer behavior is unchanged. On handled failure, only newly created export
files are cleaned and a schema-2 generic failed report with null action context
is attempted, using the existing export lifecycle. Source actions, projection,
checkpoint and database remain untouched.

## Verification evidence

Focused selection covers research schema 1/2, profile forwarding, local pair
verification, the source snapshot model, architecture and dependency guards:

```text
python -m pytest tests/test_research_corporate_actions.py tests/test_instrument_research_export.py tests/test_instrument_research_verification.py tests/test_instrument_research_run.py tests/test_yahoo_corporate_actions.py tests/test_architecture_dependencies.py tests/test_dependency_reproducibility_contract.py --basetemp=.pytest-research-actions-focused -q
197 passed
```

Tests include exact schema-1 byte parity, available/stale/missing/observed-zero
cases, inclusive freshness cutoff, typed policy bounds, source checksums before
database access, corrupt/duplicate-key data, identity/window/currency mismatches,
future times, event/count/units/fetch-time tampering, source/output aliases,
post-write failure cleanup, source immutability and synthetic read-only E2E.
Full suite: `3473 passed, 4 skipped`, with one existing Starlette deprecation
warning. `git diff --check`: clean.

## Next operational step

Apply the complete changed files and commit them. Then qualify one selected
symbol through the schema-2 profile command using confirmed local paths and
matching snapshot/window, and run the existing local verifier against the new
report checksum. This package does not guess the user's private snapshot path
or automatically acquire data. A full operator block should be bound to the
applied GitHub SHA and the confirmed private input paths.

SEND: only the redacted schema-2 research report and generic verification result.

DO NOT SEND: private action snapshot, research export, profile, projection,
checkpoints, portfolio or SQLite database without a separate sharing decision.

Broad action refresh and total-return accounting remain separate features.
