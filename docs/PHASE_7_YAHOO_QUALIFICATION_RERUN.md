# Phase 7 — Yahoo Qualification Rerun and Cache Remediation

## Verified baseline

`develop @ a9fe38c4beddf3dbf194f698fec78e6a236bdec4`

## Status

```text
RUNTIME CACHE GAP RESOLVED
LIVE QUALIFICATION FAILED — NETWORK CONNECTIVITY BLOCKED
```

## Repeated request

The same bounded request was repeated from a fresh clone:

```text
provider   = YAHOO_FINANCE
symbol     = MSFT
resolution = D
currency   = USD
window     = [2026-08-01T00:00:00Z, 2026-08-19T00:00:00Z)
```

## Focused diagnosis

The first rerun failed before network access. Direct yfinance diagnosis exposed:

```text
peewee.OperationalError: unable to open database file
```

yfinance was selecting an implicit timezone/cookie cache location that was not
writable in the execution environment.

The bounded remediation adds optional explicit cache configuration to
`YahooFinanceClient`. Live qualification CLI execution now requires
`--cache-directory`; the directory is created by the caller-facing client and
passed to yfinance's cache-location boundary. Existing callers that do not use
live qualification remain backward compatible.

## Post-remediation live result

With a writable cache inside the workspace, the request progressed to transport
and returned:

```text
status   = FAILED
duration = 0.117104 seconds
coverage = unknown
cause    = curl (7): failed to connect to fc.yahoo.com:443
```

The canonical qualification report intentionally preserves the normalized
public `APIError`; the lower-level transport cause was captured only during the
focused local diagnosis. Both local reports and the yfinance cache remain
outside source control.

## Conclusion

The repository-side runtime cache defect is resolved and covered by tests. The
remaining failure is the current execution environment's inability to connect
to Yahoo over HTTPS. It is not evidence of a candle parsing, qualification,
atomic export, or provider-wide defect.

Bulk ingestion remains blocked. The next action is to run the documented
command in an environment that permits outbound HTTPS to Yahoo and review a
`SUCCESS` result before selecting the next package.
