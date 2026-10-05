# Phase 7 — live schema-2 price-basis qualification result

Classification: `OPERATIONAL`. A fresh clean GitHub `develop` clone matched
`a03fe14d6891d89c9d75287d714e31c1fb6b59b7`. The first clone attempt
could not reach GitHub under the initial network profile; after network
permission was granted, the fresh clone succeeded and the exact baseline,
branch, and clean worktree were verified before any package work.

Exactly one live `yahoo_price_basis_qualification --schema-version 2`
history request was executed for the previously selected public MCD symbol,
with UTC window `[2025-10-01, 2026-10-01)`. Its redacted schema-2 report
parsed as JSON and recorded:

| Measure | Result |
|---|---:|
| Status / observed layer | `QUALIFIED` / `YFINANCE_HISTORY_FRAME` |
| Qualification scope | `NORMALIZED_FRAME_SHAPE_ONLY` |
| Adapter | `YFINANCE 1.6.0` |
| Daily rows | 251 |
| `Adj Close` present / valid / nonzero | true / 251 / 251 |
| `Dividends` present / valid / nonzero | true / 251 / 4 |
| `Stock Splits` present / valid / nonzero | true / 251 / 0 |
| All five raw-source evidence fields | `UNKNOWN` |
| Failure category | null |

The report's exact-byte SHA-256 is
`f354f02db935e0d0729bf969acdcd9693a0bf26b0b3a78cfb38c0ace5eb58651`.
It remains untracked at `.operational-price-basis-schema2/report.json` in the
isolated package checkout; the yfinance cache is also untracked. Neither is
included in Git or the package ZIP. No private `C:\runtime` data, portfolio,
SQLite database, existing candle, or research export was accessed or changed.

The observed aggregate counts agree with the preceding schema-1 MCD report,
but these are two separate requests and do not prove identical source bytes.
Schema-2 `QUALIFIED` validates only the normalized frame. It does not prove
raw Yahoo adjusted-close presence, complete dividends/splits/capital gains,
adjustment methodology, total return, or exchange-session completeness.

Next: audit a bounded, supportable raw-source/provenance evidence boundary
and provider terms before implementing adjusted-price/action persistence.
Do not bulk-qualify, overwrite stored `Close`, infer returns, or start a
weekly scheduler from this result.
