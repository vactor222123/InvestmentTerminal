# Phase 7 Package 7 — Session Calendar Evidence Integrity

Baseline: `develop @ aad6cc8a157346ce4cbdccfa633dad91f7b800b3`.

Coverage execution now requires `evidence.source_uri`, a timezone-aware
`retrieved_at`, and SHA-256 over canonicalized session records. A mismatch
fails before database evaluation. The verified provenance is projected into
the coverage report. Existing methodology calendar files remain compatible;
the stricter requirement applies to operational coverage claims.

Next: create the XNAS JSON from preserved official Nasdaq evidence, calculate
its session checksum, and run the coverage command.
