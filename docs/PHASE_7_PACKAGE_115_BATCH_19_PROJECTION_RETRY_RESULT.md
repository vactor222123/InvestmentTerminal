# Phase 7 Package 115 - Batch 19 Projection Retry Result

Classification: `OPERATIONAL`. Fresh `develop` baseline:
`c1484e8f7e56d8de80e6808a8509f7bd26f6e5b4`.

Only the explicitly returned redacted report was reviewed. The private
manifest, checkpoint, database, cache, symbol, currency, and candle values were
not read or added to the repository.

The report is schema version 2 and is bound to manifest checksum
`8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a`,
batch 19 of 601, and request checksum
`bba88de6404ac7dae91b7a98aa32a6e0ac32f276bd1d332a7f8c0a449e4f4864`.

The controlled run attempted the one failed outcome and skipped the 19 prior
successes. It remained `PARTIAL` with one
`YahooCandleInvalidResponseError`. Current-run downloaded, inserted, duplicate,
and omitted counts are all zero. Cumulative state remains 19 successes and one
failure; all 20 requested outcomes reconcile.

The projected path was exercised but produced no
`TRAILING_NON_FINITE_NUMERIC` evidence. Therefore the current provider frame did
not satisfy every bounded omission guard, but this aggregate report cannot
identify which guard rejected it. It would be unsafe to weaken validation or
infer that the response still has the earlier two-row shape.

The report does not contain SQLite integrity evidence, so database integrity is
not claimed from this artifact. Its reviewed SHA-256 is
`2f68a2f6087a2359ef33d9927a16c56f05f350380580b849243cbf66da910001`.

The next operation is one repeat of the existing read-only failed-series raw
diagnostic for batch 19. It must use the same manifest/checkpoint and return
only its redacted report. No checkpoint mutation, ingestion retry, validation
change, batch 20, or broader drain is authorized before review.

Verification:

- focused diagnostic/projection/manifest/architecture tests: 68 passed;
- complete suite: 2,996 passed, 4 skipped, one existing Starlette warning;
- `git diff --check`: clean.
