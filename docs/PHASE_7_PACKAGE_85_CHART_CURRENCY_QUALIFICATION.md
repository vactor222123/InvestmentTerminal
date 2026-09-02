# Phase 7 Package 85 — Chart-Metadata Currency Qualification

Classification: `IMPLEMENTATION`. Fresh `develop` baseline:
`1e80d637af5622dd3facc485aded9823a2130ad2`.

This package adds a dedicated Yahoo `get_history_metadata()` adapter and one
fail-closed qualification for the first private terminal `INVALID_CURRENCY`
outcome. Only an explicit three-letter metadata currency succeeds. The result
is stored in a separate private checksum-bound artifact; the existing currency
checkpoint is not mutated. A separate report contains only aggregate coverage
and checksums, never symbol or currency values.

Missing, invalid, provider, validation, and private-write failures produce a
redacted non-zero report. No fallback, broader scan, batch generation, candle
ingestion, analysis, or trading is authorized.

Next: run this qualification once and return only its redacted report.
