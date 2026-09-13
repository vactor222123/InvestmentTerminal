# Phase 7 Package 140 — Batch-41 Terminal Isolation Result

## Classification

`OPERATIONAL`

## Verified Baseline

```text
develop @ 53e6d633b0dd0d122f9cca64046c2d0c0666d03d
```

## Reviewed Evidence

The user returned only the redacted schema-version-1
`MANIFEST_TERMINAL_SERIES_ISOLATION` report. Private manifest, checkpoint,
database, candle values, and instrument identity were not reviewed.

Report SHA-256:

```text
d9f2a7a79aead42ddd7a75ff169c2792730ba493469f1b17807b52cea1c8775c
```

## Result

The controlled offline transition succeeded for manifest batch 41 of 601.
Manifest checksum, request checksum, batch index/count, and ten-year requested
window match the established batch-41 evidence.

Coverage after the transition is:

```text
requested_count = 20
success_count = 19
empty_count = 0
retryable_failure_count = 0
final_failure_count = 1
transitioned_count = 1
already_final_count = 0
```

The terminal category is `RESPONSE_NUMERIC` under policy
`NORMAL_AND_REPAIRED_STRICT_REJECTION_V1`. The report binds the transition to
the exact previously returned evidence:

```text
normal diagnostic SHA-256:
149b0732f613503e62ea495c0fd674d6010543408727d38677a91addb00901f5

repaired qualification SHA-256:
9b734e0a0581d8ff57f6f4895371d24a7dbedf7c33a72b8c05aeb334b5b208df
```

Both values were independently recalculated from the explicitly returned
redacted reports and match the isolation report. The operation did not retrieve
or persist candles and does not declare the instrument invalid outside this
fixed manifest request.

## Limits

The returned isolation JSON does not contain SQLite integrity evidence, so this
package makes no independent database-integrity claim. It also does not prove
the new resumable report's operational provider bypass; that behavior is
covered by tests but has not yet been measured against the private checkpoint.

## Verification

- focused isolation/resume/manifest/drain/diagnostic and architecture tests:
  81 passed;
- complete suite: 3,049 passed, 4 skipped, one existing Starlette warning;
- `git diff --check`: clean.

## Next Operational Gate

Run one exact manifest-bound batch-41 resume against the transitioned private
checkpoint. It must report `SUCCESS_WITH_EXCLUSIONS`, attempt zero items, skip
all 20, expose one final failure and zero retryable failures, and leave SQLite
integrity `ok`. Do not run batch 42 or the broader drain until that redacted
provider-bypass result is reviewed.
