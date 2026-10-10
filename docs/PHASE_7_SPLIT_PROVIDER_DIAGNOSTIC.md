# Phase 7 — one bound portfolio action provider diagnostic

Classification: `IMPLEMENTATION`. Fresh clean `develop` baseline:
`311b1e3b64350e40ea115472b8bb08ff56dc8476`.

## Returned evidence and focused audit

The user's preflight found 12 instruments against budget 10. Repeating the
read-only check with budget 12 returned READY, one valid CSV and zero blocked
items. Collection then returned exit 1 and the explicitly shared report
`portfolio_split_collection_20261007_163405_454b8eb5.json`: STOPPED, FAILED 1,
PENDING 11, BLOCKED 0 and zero successful split/no-split observations.
Its only category is PROVIDER_REQUEST; adjustment_performed is false.

Exact returned report SHA-256:
`52fc890cf9c6264dcea9e742f2573354e1ee2026ec8b4f0caae868feadde46f5`.

The existing action CLI intentionally catches provider exceptions and persists
only the generic category. Therefore the earlier cause cannot be recovered from
this report. It does not establish rate limiting, timeout, invalid ticker,
delisting or no corporate actions. Only the returned redacted report was read;
no private selection, transaction CSV, snapshot, cache or database was accessed.

Audited local installed yfinance exception definitions, curl_cffi request
exception inheritance, the action adapter/collector and existing portfolio
composition. The new classifier uses those actual exception types, not message
keywords, private exception attributes or guessed class names. Existing report
category semantics remain unchanged; richer diagnosis has a separate contract.

## Bounded implementation

`portfolio_split_diagnose` requires `--collection-report`,
`--collection-report-sha256`, `--snapshot-directory`, `--cache-directory` and
a new `--report-output`. All paths must be absolute and non-symlink; private,
cache and report boundaries are checked before provider work.

The original report must be schema 1 STOPPED with exactly one eligible
PROVIDER_REQUEST failure. Its existing path-derived token locates the private
selection; the report pins that selection, which in turn pins the original CSV.
Four-MB reads, strict duplicate-key JSON parsing, hashes, ledger validation,
reconstructed request identities/windows, and aggregate status/category parity
are checked. The selected failed item must still be a pending-eligible candidate
in the reconstructed original plan. No first-match ticker or file search is used.
Moving/renaming the original report breaks its path-derived selection binding;
preserve its original location. Changed source bytes fail before provider work.

A cooperative portfolio-directory lock and new diagnostic-report lock protect
composition. The existing collector performs exactly one application invocation
through the probe; it may issue multiple HTTP history/metadata requests through
yfinance. No application retry loop is added, and the remaining instruments are
not invoked. Existing snapshots are not reused for this fresh observation;
unique diagnostic snapshot/stage paths must not already exist.

The probe classifies the exception actually exposed by the adapter:

- RATE_LIMIT: typed yfinance rate limit or typed HTTP error with integer 429;
- TIMEOUT: typed curl/Python timeout;
- PRICE_DATA_MISSING / TIMEZONE_MISSING: typed yfinance missing-data errors,
  not proof of delisting or an absent split;
- TLS_ERROR, CONNECTION_ERROR, HTTP_ACCESS_DENIED (401/403), HTTP_SERVER_ERROR
  (5xx), HTTP_ERROR, TRANSPORT_ERROR: typed transport/status evidence;
- UNKNOWN_PROVIDER_ERROR: everything else, without inspecting exception text.

CLIENT_SETUP versus HISTORY_OR_METADATA records where the exposed exception
occurred. The adapter's combined call cannot distinguish history from metadata
failure, or recover suppressed nested failures. A provider result rejected by
existing validation/storage is COLLECTION_VALIDATION_OR_STORAGE, not a guessed
transport error. Client setup can fail before an HTTP call even though the probe
invocation count is one. No internal transport retries are claimed or controlled.

Successful validated responses are retained as separate private snapshots and
bound to the diagnostic report. The original batch index is not updated and the
normal batch does not automatically promote/reuse a diagnostic-named snapshot.
Review the result and retained evidence before deciding subsequent reuse/resume.
This preserves the observation without silently changing batch authority.

## Contract and failure handling

The redacted schema-1 PORTFOLIO_SPLIT_PROVIDER_DIAGNOSTIC report records status,
original report/selection/CSV hashes, invocation count, fixed category/phase,
private stage-report/snapshot hashes and explicit limits. No symbols, prices,
holdings, paths or raw exception messages are copied into it. Existing collection
and selection contracts are unchanged. COLLECTED means the request and snapshot
validation/storage succeeded, not verified broker mapping or split adjustment.

Exact input pins are rechecked before and after collection and after report
write. Snapshot/stage hashes and atomic report readback are checked before final
RESULT. Existing output names are refused. A failed or interrupted run preserves
all partial evidence; a null snapshot hash is not a file-absence claim. A late
failure may leave a complete-looking report: require final RESULT and exit code.
Provider/response failure returns 1 with a report when that report can be written;
preflight or persistence failure can return 1 without a diagnostic report.

SEND: only the new diagnostic report and exit code.
DO NOT SEND: CSV, private selection, snapshots, stage report, cache or database.
Locks are cooperative, not protection against unrelated external editors.

## Verification and operational next step

Tests use synthetic original CSV/report/index pairs and fake providers. They
cover typed timeout/rate-limit/HTTP/missing-data classification, no message
guessing, checksum/selection mismatch, changed CSV, multiple failures, output
and lock collisions, exactly one failed-item replay, preserved original bytes,
private output retention, late write/readback/source/snapshot failures and
redaction. No live request or private runtime read was performed in this package.

Measured: 32 new tests passed in development; focused 202 passed with one cache
access warning; full pytest 3,685 passed, 4 skipped with two warnings (existing
Starlette deprecation and inaccessible pytest cache). There were no test failures.
`git diff --check` is clean. Local pytest roots and caches are excluded from the
commit and ZIP; no permission workaround or unrelated file deletion was used.

After applying the package, return the new SHA. Run one diagnostic using the
original report path/hash above and the existing private snapshot/cache roots,
with a new report name. Do not rerun the batch. A new outcome is a new observation
and cannot prove the old failure cause; choose a remedy only from returned facts.
