# Phase 7 Package 45 - Schema-3 Private OpenFIGI Bootstrap

Package type: `OPERATIONAL`.

Source baseline: `develop @ f18b39b72824abcef126c540c67e97ac8457ce7e`.

## Result

The controlled schema-version-3 OpenFIGI bootstrap completed with `FAILED`
status and category `CANDIDATE_TICKER_WITH_ALTERNATIVES`. The redacted report
records 10 requested instruments, two planned batches, one archived response,
no published matched count, and a duration of 1.159853 seconds.

The returned report SHA-256 is
`76b8f54053db8e0bb5499b606270ef8bdba9e004911a2b5c1a2b9dd94c1773a9`.
The private transaction database, quote input, metadata output, and exact raw
response archive were not reviewed or added to the repository. Quote
qualification and valuation were not run.

## Audit conclusion

The evidence proves that the first failing mapping contains the private
candidate ticker together with alternative OpenFIGI listing tickers. The
current all-ticker-set equality check is therefore stricter than needed to
confirm the candidate. The existing code already derives provenance only from
rows whose ticker equals that candidate.

The smallest safe remediation is to accept a mapping when the candidate ticker
is present, deterministically retain every candidate-ticker FIGI, and ignore
alternative listing rows for metadata construction. Candidate absence,
provider failures, malformed data, and missing candidate FIGIs must continue to
fail closed. No first-row selection or provider exchange-code-to-MIC projection
is permitted.

## Next step

Implement candidate-ticker row filtering with focused alternative-listing,
candidate-absent, missing-FIGI, privacy, archive, and metadata tests. Do not
rerun bootstrap, qualify quotes, or value the portfolio before that package is
reviewed and pushed.

## Verification

```text
focused OpenFIGI/privacy/architecture checks: 32 passed
full: 2811 passed, 4 skipped, 1 existing Starlette deprecation warning
git diff --check: clean
```
