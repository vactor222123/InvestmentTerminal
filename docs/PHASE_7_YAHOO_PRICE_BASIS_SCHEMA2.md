# Phase 7 — normalized-frame provenance report, schema 2

Classification: `IMPLEMENTATION`. A fresh clean GitHub `develop` clone
matched `5c3ca361c1ff57b39193fdc56813865e11b8dbf7` before edits.

The existing one-instrument `yahoo_price_basis_qualification` CLI now accepts
an explicit `--schema-version 2`. Its default remains schema 1 and produces
the same bytes as an explicit `--schema-version 1`; no existing report or
candle/storage contract is rewritten. Both versions make at most one history
request through the same client. No provider request, runtime database, or
private file was used while implementing this package.

Schema 2 is a separate redacted JSON contract. It keeps the request window,
flags, status, aggregate row count, and fixed failure category, but places
candidate field counts under `normalized_frame_fields`. It adds:

- `observed_layer: YFINANCE_HISTORY_FRAME`;
- `qualification_scope: NORMALIZED_FRAME_SHAPE_ONLY`;
- `adapter: {name: YFINANCE, version: <installed release>}`;
- `raw_source_evidence` with `UNKNOWN` for raw adjusted-close indicator,
  dividend, split, and capital-gains event presence and action completeness.

The adapter version is validated before any provider request in schema-2
mode. Invalid version text, malformed provider data, and provider exceptions
fail closed. Existing output non-overwrite and redaction rules remain. The
report contains no symbol, candle values, event dates, raw provider text,
exception message, or private path. Schema 2 does not inspect the raw Yahoo
response and does not turn normalized-frame shape into action completeness
or adjusted-return proof.

Focused fake-provider tests cover schema-1 byte parity, schema-2 success,
provider failure, privacy, one-call behavior, and invalid-version preflight.
The next gate is one explicitly selected live schema-2 qualification and
redacted report review. Do not change stored `Close`, derive returns, run
bulk requests, or schedule refreshes from this report alone.
