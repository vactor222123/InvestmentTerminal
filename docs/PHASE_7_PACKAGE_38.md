# Phase 7 Package 38 - Provenance-Aware Instrument Metadata Enrichment

Package type: `IMPLEMENTATION`.

Source baseline: `develop @ 0f55a7c724ba0083148799f8b7df17f074e20342`.

## Result

Added a strict schema-version-1 private instrument-metadata document with one
canonical instrument key, explicit exchange ticker and optional exchange code,
plus existing market-metadata provenance per item. The loader rejects malformed
JSON, unsupported schemas, unknown or missing fields, duplicate keys, invalid
timestamps, and invalid provenance checksums.

The enrichment service requires exact open-position coverage and caller-owned
maximum age. It accepts only `READY` evidence, rejects future, stale, partial,
conflicting, or key-changing metadata, and returns a detached reconstruction.
Ledger transactions, SQLite payloads, quantities, costs, currencies, and
ownership metadata remain unchanged.

Offline quote qualification accepts the metadata document and maximum age as
an optional explicit pair. Omission preserves the existing schema-version-1
report and qualification behavior. The CLI remains read-only and creates no
valuation database or snapshot. Private metadata is gitignored.

Online lookup, ticker inference, provider selection, transaction migration,
maintained-universe ingestion, durable valuation, workflow execution, and
trading remain out of scope.

## Verification

```text
focused metadata/qualification/identity/reconstruction/privacy/architecture: 73 passed
full: 2793 passed, 4 skipped, 1 existing Starlette deprecation warning
git diff --check: clean
```

## Next step

After push, prepare one private schema-version-1 metadata document from verified
source records and run a controlled read-only offline quote qualification with
an explicit caller-selected maximum age. Return only the redacted qualification
report; do not send metadata, quotes, transaction SQLite, or execute valuation.
