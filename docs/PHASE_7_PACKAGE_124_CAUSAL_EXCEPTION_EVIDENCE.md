# Phase 7 Package 124 - Causal Exception Evidence

Classification: `IMPLEMENTATION`. Fresh `develop` baseline:
`8c21c4114fabdd3d7e0c25227be444b3c2f64ca6`.

## Result

The Yahoo provider boundary now projects one immutable failure-evidence value
containing the existing stable category and a privacy-safe causal exception
type chain. The established classifier delegates to this projection, so all
existing consumers preserve their category behavior.

The report chain is outermost first, cycle-safe, and capped at eight entries.
It exposes only ASCII module/class identifiers from the reviewed namespaces
`builtins`, `yfinance`, `curl_cffi`, `pandas`, `numpy`, `peewee`, `sqlite3`,
`requests`, `urllib3`, and `investment_terminal`. Unapproved or malformed type
identities become `UNRECOGNIZED_EXCEPTION_TYPE`. A causal chain beyond the
evidence bound ends with `EXCEPTION_CHAIN_TRUNCATED`, while classification still
examines the complete chain.

The projection never reads or serializes exception messages, representations,
arguments, tracebacks, source lines, local variables, paths, symbols,
currencies, or provider payloads.

## Repaired-series report migration

All newly generated repaired-series reports use schema version 2. `QUALIFIED`
and `REJECTED` preserve `failure=null`. `FAILED` adds the non-empty
`failure.exception_type_chain` beside the unchanged stable category and fixed
reason. Historical schema-version-1 reports remain valid and immutable.

This package made no Yahoo request and changed no repair, candle projection,
checkpoint, SQLite, importer, retry, or drain behavior. It grants no authority
to persist repaired candles, retry batch 19, execute batch 20, or resume the
manifest drain.

## Verification scope

Focused tests cover category parity, allowlisted built-in and dependency class
identities, unapproved and malformed identities, causal order, cycles,
truncation beyond the evidence bound, strict JSON privacy, and unchanged
qualified/rejected failure semantics. Architecture dependency guards and the
complete regression suite remain required before delivery.

Verification completed with `90 passed` focused tests and `3031 passed,
4 skipped, 1 warning` in the complete suite. The warning is the existing
Starlette `httpx` deprecation warning. `git diff --check` is clean.
