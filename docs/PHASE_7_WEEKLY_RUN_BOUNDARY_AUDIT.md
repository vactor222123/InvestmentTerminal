# Phase 7 — repeatable weekly-run boundary audit

Classification: `AUDIT`. A fresh clean GitHub `develop` clone matched the
caller-supplied baseline `2e3aceeb51a133db3f280d97097b5ce91209c5a5`.
No private runtime action, provider request, database write, or application
change occurred in this package.

## Existing capability and friction

`weekly_candle_refresh` already validates the manifest and complete source
checkpoints, selects source-success daily series, persists each validated
series transactionally, atomically checkpoints after each series, resumes
same-end work without refetching completed outcomes, and stops on a provider
rate limit. It has an explicit opt-in rate-limit retry. Its private checkpoint
is bound to the manifest, selection checksum, and exclusive UTC-midnight end.
Existing test coverage includes resume, provider failure, rate limiting,
drift isolation, and checkpoint-write failure.

The CLI nevertheless requires nine explicit operational inputs: manifest,
manifest checksum, source-checkpoint directory, weekly checkpoint, database,
cache directory, report path, end, and item budget. The historical PowerShell
handoffs discover the 601-file source directory with the batch-576 request
checksum; there is no reusable application-owned runtime profile or short
weekly operator entry point. A new end requires a new private checkpoint.
Each invocation needs a distinct report path because the CLI's atomic writer
can replace an existing report; it does not reserve report names. The CLI
checks that the database file exists, but then calls `Database.initialize()`;
this is not a read-only quality check.

Status and exit-code semantics must remain visible. `BUDGET_EXHAUSTED` exits
zero even when completed items include isolated failures. `HALTED`,
`COMPLETE_WITH_FAILURES`, and `FAILED` exit nonzero, but a `HALTED` or
`COMPLETE_WITH_FAILURES` report can still contain committed candle progress.
An operator wrapper must inspect the durable report and checkpoint rather
than equate process exit zero with market-data quality or delete a partial
run. Same-end ordinary resume skips all checkpointed outcomes, including
failures; only the explicit rate-limit mode reopens that category. A new-end
run may attempt those series again under a new checkpoint.

The separately measured 2026-09-23 cohort has 214 weekly failures and 48
weekly successes with a stale-end or long-calendar-gap warning. Existing
transfer `SUCCESS` does not certify endpoint freshness, exchange sessions,
or analysis readiness. The read-only stored-coverage and stale-gap CLIs
measure these properties only after a complete checkpoint; they do not
provide an automatic quality summary during an incomplete run.

## Selected next implementation seam

Build one small CLI composition root for a **bounded weekly slice**, not a
new downloader. It should take a private, versioned runtime profile plus an
explicit UTC-midnight `--end` and item budget; the profile owns stable
manifest/checksum, source-checkpoint-directory, database, and cache paths.
The operator-facing invocation should need only those changing values. The
profile must be bootstrapped from verified existing private evidence rather
than asking the user to enter symbols or prices. Before provider access, it
must fail closed on profile/schema/path/checksum errors, cross-end checkpoint
reuse, and an existing report destination. For each end, use a separate
private checkpoint; for each slice, require a unique durable redacted report.
Delegate selection, fetching, persistence, resume, and rate-limit policy to
the existing weekly service; preserve its checkpoint and report JSON
contracts. Do not hide a nonzero result or silently retry it. Test normal
and failure paths, including same-end resume, changed-end rejection, report
collision, and partial progress followed by rate limiting.

A later, separate read-only quality-summary boundary can compose the complete
weekly checkpoint and stored observations, keeping failed transfers and
stale/gap warnings distinct. It must not silently revise weekly `SUCCESS`,
declare official missing sessions from calendar gaps, or block unrelated
series from a future update. Scheduler, UI button, automated retry, broad
backfill, and investment interpretation remain outside this implementation.
