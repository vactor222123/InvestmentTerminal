# Phase 7 Package 13 — IBM Operational Preflight

Baseline: `develop @ 69affb8ba7f3a31cadecaf8fea183e75b26341fd`.

The staged `XNYS@1` document was re-verified successfully with session checksum
`83d70a90bb334fac740a209a20bcfbfcb685de805130655cfef31134ab48e2fb`.
The operational SQLite remains read-only in this execution profile and still
contains zero IBM daily candles.

A separate non-persisting Yahoo qualification request was then attempted for
IBM, USD daily candles, and the exact half-open 2021-08-19 through 2026-08-19
window. It failed closed before ingestion:

```text
status: FAILED
failure type: APIError
transport detail: curl error 7
endpoint: fc.yahoo.com:443
cause: outbound connection unavailable
```

The failure report was written atomically in the workspace output directory.
No IBM candles were downloaded or persisted, and the operational database was
not modified. The next run must first obtain outbound Yahoo HTTPS access and
repeat this exact qualification. Runtime write access is required only after a
successful qualification, for evidence placement and bounded ingestion.

## Verification

- focused qualification/evidence/ingestion/architecture suite: 43 passed;
- complete local suite: 2,726 passed, 4 skipped;
- one existing Starlette deprecation warning;
- `git diff --check`: clean.
