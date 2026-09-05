# Phase 7 Package 95 — Deterministic Market-Batch Manifest

Classification: `IMPLEMENTATION`. Fresh `develop` baseline:
`e872ed5a5d5ad1a3bd097085a6b7b0261ce067e8`.

Package 95 implements the offline boundary selected by Package 94. The service
verifies the eligibility-success projection checksum, requires its matching
complete schema-version-2 currency checkpoint, rejects any symbol-set mismatch,
and includes only terminal `SUCCESS` outcomes with explicit three-letter
currencies.

Items are sorted by normalized symbol, converted through the existing
schema-version-1 `MarketBatchRequest`, and partitioned into consecutive requests
of at most 20 items. The private schema-version-1 manifest records every
canonical request and request checksum. A SHA-256 of the complete manifest is
published only in the separate redacted schema-version-1 report.

The CLI atomically writes the private manifest and aggregate report. Failure
reports contain only exception type and a fixed reason; symbols, currencies,
paths, prices, provider text, and exception messages remain excluded.

The package has no Yahoo client, database, repository, scheduler, analysis, or
trading dependency. Its implementation does not authorize ingestion. The next
step is one user-executed offline construction against the established private
projection and checkpoint, followed by review of only the redacted report.
