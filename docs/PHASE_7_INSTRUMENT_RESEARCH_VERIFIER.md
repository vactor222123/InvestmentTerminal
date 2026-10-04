# Phase 7 — local selected-instrument research verifier

Classification: `IMPLEMENTATION`. A fresh clean GitHub `develop` clone matched
`ed5baf3cffacf93a16309ff15c604d6aa59bfbc5` before changes. No private
runtime input, operational SQLite database, or provider was accessed.

`python -m investment_terminal.cli.instrument_research_verify` accepts one
existing private schema-1 `INSTRUMENT_RESEARCH_EXPORT`, its existing redacted
schema-1 `INSTRUMENT_RESEARCH_EXPORT_REPORT`, the caller's expected canonical
symbol, and a previously recorded exact-byte report SHA-256. It reads both
files without writing anything. The report hash is checked before JSON
parsing; strict parsing rejects duplicate keys and non-finite literals.

The verifier requires exact schema shapes and identities, `COMPLETE` status,
the existing price basis and limitation texts, matching manifest/selection/
projection/window/count/candle checksums, matching selected symbol and
currency in the private indicator item, and an ordered, bounded UTC candle
array with valid finite OHLCV. It recomputes the same canonical candle-array
SHA-256 as the exporter. It also requires the export window to contain the
full latest indicator sample and recomputes latest timestamp/close, raw-close
SMA50/SMA200 availability and values, and the seven-calendar-day proxy from
that sample. A narrower legitimate export that omits part of the latest
sample fails closed rather than receiving an incomplete verification claim.

On success the command prints only a generic verification line and the
exact-byte report/private-export SHA-256 values. It prints no symbol, price,
SMA, timestamp, path, or private JSON. On failure it prints one generic
message without exception text or private identity. Neither result creates
a new JSON contract or grants permission to share the private artifact.

The verifier does not re-read the source manifest, projection, checkpoint,
or SQLite snapshot; it proves internal parity of the **existing pair**
against the caller-pinned redacted report bytes, not provider authenticity,
exchange-session completeness, corporate-action adjustment, current market
freshness, or investment suitability. It cannot retroactively prove that
older SQLite rows were unchanged before the export. No upload, provider
request, database write, recommendation, or scheduler is added.

Next prepare one exact-baseline, user-executed qualification for the existing
private MCD-named export and its previously reviewed redacted report. The
report's recorded SHA-256 is
`f67727f3f09ef6b7b82a0f80102323b56ecdd67786e6177f600bd409cc0ea3ed`.
Run verification locally first, then decide separately whether the user
explicitly approves sharing those exact private export bytes with ChatGPT.
