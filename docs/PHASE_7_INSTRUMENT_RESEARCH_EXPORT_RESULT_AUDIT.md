# Phase 7 — one-instrument research-export result audit

Classification: `AUDIT`. A fresh clean GitHub `develop` clone matched
`f39a7566a0f67027fd29436f9cad3f79b4a71a6f`. The only runtime file
reviewed was the explicitly returned redacted report
`C:\runtime\reports\instrument_research_export_20260929_001.json`.
Its exact-byte SHA-256 is
`43cf520503abd2582d003a4575e5d51f7504ec75a571999a43654d9b7e9c7701`;
JSON parsing succeeded. The user separately reported `SQLite integrity: ok`.
The private export, source projection, manifest, checkpoints, and database
were not inspected or modified in this audit.

## Measured result

The schema-1 `INSTRUMENT_RESEARCH_EXPORT_REPORT` is `COMPLETE`, with
`failure=null`. It is bound to manifest
`8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a`,
selection
`75d839c54ff43969832a4d1110deba538cd52793e9402db5cba2dc1decc6c5ae`,
source projection bytes
`a8ffe1f944d529b64d688fb75ba4e9ad2278edc0d59bbe8ba1850c1017fabf0a`,
and the 2016-09-29 to 2026-09-29 exclusive UTC window. It reports 2,512
exported daily-labeled rows with candle-array checksum
`198e5cbf4e484679f6ef9c7a4acc7b6d332a8e6df7d799d9a5607201d6afd127`.
The latest sample contains 200 stored closes, so both raw-close SMA50 and
SMA200 are available; the seven-calendar-day recency proxy is true. The
redacted report exposes no symbol, currency, candle times/prices/volume,
or SMA values. These observations demonstrate one working read-only
manifest/checkpoint/projection-to-SQLite export path. They do not establish
the selected symbol's identity or any investment result.

## Boundary and next step

`price_basis=STORED_CLOSE_NO_EXPLICIT_ADJUSTMENT`: Terminal applies no
explicit corporate-action adjustment, and provider historical adjustment
semantics remain unverified. A 2,512-row count across a ten-year window is
not exchange-session completeness; the report omits first/last candle
timestamps and gaps. The source projection's latest-200 parity is checked
by the CLI, but older rows are bound only to this export's candle-array
checksum. The user did not return the local private/report validation line,
so this audit does not independently attest the private artifact's bytes.
The independent SQLite integrity result is user-reported, not rerun here.

The existing CLI already accepts an explicit selected symbol. The next
operational decision is **which instrument the user actually wants to
analyze** and whether the user authorizes sharing that instrument's private
research export with ChatGPT. The automatically selected first qualifying
instrument was only a pipeline qualification, not a user research choice.
If sharing is approved, first define a bounded, explicit, checksum-verified
handoff for that user-selected instrument and preserve price-basis,
coverage, and provenance limitations. Do not upload the existing private
artifact, infer adjusted returns or session completeness, create a bulk
export, or enable unattended weekly scheduling from this redacted report.
No application code or runtime data changes are made in this package.
