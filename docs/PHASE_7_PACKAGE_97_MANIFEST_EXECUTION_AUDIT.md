# Phase 7 Package 97 — Manifest-Bound Execution Audit

Classification: `AUDIT`. Fresh `develop` baseline:
`6d199d15c9783954b38235a6a61c87faa49719d9`.

## Result

The existing `ResumableMarketBatchService` is a suitable execution primitive
for one request, but the current CLI cannot prove that its request came from the
qualified private manifest. Executing a manifest request directly is therefore
not yet authorized.

The service accepts one schema-version-1 request containing 1–20 unique symbols,
processes them sequentially, atomically checkpoints after every attempted item,
skips prior `SUCCESS` and `EMPTY` outcomes on exact resume, and isolates
per-symbol exceptions. SQLite writes are owned by each existing historical
import operation; the complete request is not one database transaction.

## Evidence gap

The current CLI accepts a standalone request file rather than the private
manifest. Its schema-version-2 report exposes aggregate transfers and failure
types but does not expose the request checksum, manifest checksum, batch index,
or manifest batch count. The schema-version-1 checkpoint binds only to the
request checksum. Consequently a returned redacted report cannot establish
which of the 601 qualified requests produced it.

The executor also retries a prior `FAILED` item on resume without an attempt cap
and reports provider exceptions only by Python type. It has no immediate typed
rate-limit halt. These limitations are acceptable only for one explicitly
bounded request and must remain visible; they do not support a complete-manifest
drain.

## Selected boundary

The next package should implement a separate manifest-bound executor and CLI
that executes exactly one caller-selected batch index. Before database creation
or provider access it must:

1. validate the private schema-version-1 manifest identity and caller-supplied
   canonical manifest checksum;
2. require ordered, contiguous, unique batch indices and select exactly one;
3. reconstruct the selected existing `MarketBatchRequest` and verify its stored
   request checksum;
4. bind the private checkpoint to that request through the unchanged resumable
   service;
5. emit a versioned redacted envelope containing manifest checksum, batch index,
   batch count, request checksum, aggregate execution result, and limitations;
6. write handled failures before exiting non-zero without symbols, currencies,
   paths, prices, provider text, or exception messages.

The first operational run after implementation should execute batch index 1
only, with its own private checkpoint and redacted report. A partial result must
stop expansion. Even a successful result authorizes only an exact-resume check
for that same batch; it does not authorize batch 2 or a 601-request drain.

## Excluded scope

This audit does not read the private manifest, create a database or checkpoint,
contact Yahoo, retrieve candles, change the existing request/report schemas,
schedule work, calculate indicators, or authorize mass ingestion.
