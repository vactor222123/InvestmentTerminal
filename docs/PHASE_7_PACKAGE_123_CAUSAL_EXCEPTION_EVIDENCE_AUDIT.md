# Phase 7 Package 123 - Causal Exception Evidence Audit

Classification: `AUDIT`. Fresh `develop` baseline:
`d0cd9afd237f40157a4c42d88ba73506d844dbab`.

## Findings

The Yahoo candle classifier already traverses the exception `__cause__` or
`__context__` chain with cycle protection and recognizes stable yfinance,
curl-cffi, local validation, timeout, and request categories. When an `APIError`
wraps an unrecognized causal type, however, the classifier deliberately returns
only `UNEXPECTED`.

The repaired-series CLI then writes only that category and a fixed reason. It
does not preserve the exception object, causal class, arguments, message, or
traceback. Consequently the Package 122 report cannot be enriched offline and
does not distinguish a yfinance repair defect, pandas transformation failure,
cache failure, or another unrecognized runtime exception. Selecting one of
those causes without new evidence would be invention.

## Selected contract

The smallest safe implementation is a shared Yahoo failure-evidence projection
used by the existing classifier and the repaired-series CLI. It must return the
existing stable category plus a bounded normalized causal exception-type chain.
The existing category behavior remains unchanged.

The chain contract is:

- outermost exception first, then `__cause__` or `__context__`;
- cycle-safe and limited to eight entries;
- each entry is a module-qualified class identifier only;
- module and class segments must match the ASCII Python-identifier grammar;
- only fixed reviewed namespaces may be exposed: `builtins`, `yfinance`,
  `curl_cffi`, `pandas`, `numpy`, `peewee`, `sqlite3`, `requests`, `urllib3`,
  and `investment_terminal`;
- an unsafe or unapproved type becomes `UNRECOGNIZED_EXCEPTION_TYPE`;
- a longer chain ends with the fixed `EXCEPTION_CHAIN_TRUNCATED` marker.

No `str(exception)`, `repr(exception)`, `args`, traceback, source line, local
variable, path, symbol, currency, provider response, or payload field may be
read or serialized. The projection belongs to the provider boundary rather
than a generic utility because its allowlist and failure categories are Yahoo
operational policy.

## Versioning and scope

The repaired-series report must advance to schema version 2 for every status.
Only `FAILED` owns a non-empty `failure.exception_type_chain`; qualified and
rejected reports retain `failure=null`. Historical schema-version-1 reports
remain valid and immutable. The qualification identity and all existing
manifest/request/repair/coverage semantics remain unchanged.

The implementation package must add focused tests for recognized built-in and
dependency types, an unapproved dynamic exception, cycles, truncation, category
parity, failure-report strict JSON/privacy, and unchanged qualified/rejected
behavior. It must make no provider request and grant no retry or persistence
authority.

After implementation, one controlled schema-version-2 rerun may be authorized
to identify the causal class. Until that report is reviewed, do not change
repair logic, retry ingestion, execute batch 20, or resume the drain.

## Verification

- focused regression and architecture tests: `84 passed`;
- complete test suite: `3025 passed, 4 skipped, 1 warning`;
- the warning is the existing Starlette `httpx` deprecation warning;
- `git diff --check`: clean.
