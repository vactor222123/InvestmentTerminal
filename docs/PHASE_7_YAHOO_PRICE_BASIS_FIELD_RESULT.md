# Phase 7 — one-instrument Yahoo price-basis field result

Classification: `OPERATIONAL`. A fresh clean GitHub `develop` clone matched
`b168b2fed4f3f333719325dfbe55c77a8e087ce8` before the run. The user
explicitly resumed live checks. Exactly one `yahoo_price_basis_qualification`
command was executed for the previously selected public MCD symbol, with
UTC window `[2025-10-01, 2026-10-01)`, `auto_adjust=False`, `actions=True`,
and `repair=False`. No private `C:\runtime` file or SQLite database was read or
written. The runtime report and yfinance cache remain untracked and are not
included in Git or the package ZIP.

The schema-1 redacted report passed JSON parsing and recorded:

| Measure | Result |
|---|---:|
| Status | `QUALIFIED` |
| Daily rows | 251 |
| `Adj Close` present / valid / nonzero | true / 251 / 251 |
| `Dividends` present / valid / nonzero | true / 251 / 4 |
| `Stock Splits` present / valid / nonzero | true / 251 / 0 |
| Failure category | null |

The report's exact-byte SHA-256 is
`2e89df99fbe17ef381b3c554ce19f770fc134fe332eb2bee89e940795727db2d`.
The redacted report is at
`.operational-price-basis/report.json` in this isolated package checkout;
it contains no symbol, prices, event dates, provider text, or private paths.
The listed nonzero counts do not independently prove actual corporate
actions or correctness of Yahoo's adjustment methodology. One instrument
does not establish provider reliability across the universe, exchange-session
completeness, or adjusted return validity. Existing stored `Close`, candle
schema, and research JSON contracts are unchanged.

Next: audit the provider's adjusted-close and corporate-action semantics and
the required versioned provenance/storage contract before implementing any
adjusted-price persistence or return calculation. Do not extrapolate this
one-symbol result to bulk ingestion or enable weekly scheduling on its basis.
