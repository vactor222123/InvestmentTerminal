# Phase 7 — bounded portfolio split candidate collection

## Current diagnostic follow-up

Fresh baseline `c3864d552a166fbdb024a12fe1853cee4eb3f587`; classification
`IMPLEMENTATION`. The user returned `Portfolio action collection failed at
PREFLIGHT`, no aggregate report and exit 1. The collector is invoked only after
the stage changes to `COLLECTION`, so no provider work occurred in that attempt.
The old catch-all hid the cause. It is not evidence that the CSV, date, paths or
instrument count were specifically at fault. No runtime files were accessed by
the agent to guess which condition failed.

The optional `--preflight-only` flag now stops before locks, directory creation,
collector calls or writes. It shares the normal path's guards, reads/parses the
CSV, builds the bounded plan, verifies source bytes and prints one console-only
schema-1 `PORTFOLIO_SPLIT_PREFLIGHT` diagnostic prefixed `PREFLIGHT_RESULT: `.
Invoke using `python -B` to suppress Python interpreter bytecode writes as well.
All usual options remain required; `--report-output` is checked but never written
in this mode. Existing report/private-index files and locks remain protected.

`READY` and `READY_WITH_BLOCKERS` return 0 with safe instrument/CSV/plan counts.
`FAILED` returns 1 with a fixed category and applicable numeric counts. Normal
collection also emits this diagnosis for a known preflight failure. The result
contains no source hashes, paths, identities, trade IDs, quantities or prices.
No new persisted schema or migration is introduced. Normal successful collection
output stays unchanged; later-stage failures keep the existing behavior.

Categories distinguish:

- `CSV_NOT_FOUND` / `CSV_AMBIGUOUS`: seen, valid and invalid CSV counts;
- `CSV_FILE_LIMIT` / `CSV_SIZE_LIMIT`: the existing bounds, without truncation;
- `CSV_SYMLINK`, `CSV_READ_ERROR`, `CSV_CHANGED`: unsafe/unreadable/changing input;
- `DUPLICATE_TRANSACTION_IDS`: duplicate count, never private IDs;
- `LEDGER_INVALID`, `NO_TRADE_INSTRUMENTS`, `INSTRUMENT_BUDGET`: validation or
  required instrument count versus the unchanged requested maximum;
- `PATH_NOT_ABSOLUTE_OR_SYMLINK`, `INPUT_DIRECTORY_MISSING`,
  `REPORT_EXISTS`, `PRIVATE_SELECTION_EXISTS`, `OUTPUT_DIRECTORY_INVALID`,
  `OUTPUT_LOCK_EXISTS`, `SNAPSHOT_INPUT_OVERLAP`, `REPORT_PRIVATE_OVERLAP`,
  `CACHE_SNAPSHOT_OVERLAP`: specific path/ownership guards;
- `INVALID_INSTRUMENT_LIMIT`, `INVALID_AGE_LIMIT`, `INVALID_CLOCK`,
  `INVALID_END_DATE`, `FUTURE_END_DATE`: invalid explicit policy or time;
- `PREFLIGHT_UNEXPECTED`: sanitized fallback, not a guessed specific cause.

The diagnostic stops at the first failed guard. `INPUT_DIRECTORY_MISSING` means
the supplied path did not identify a directory. Argument parsing remains argparse
and is outside the structured diagnostic. Read-only checks cannot prove future
write permissions, prevent later races, validate existing snapshot contents,
establish provider-symbol mapping or certify CSV completeness. The underlying
CSV discovery scope is unchanged. Preflight is not a positive split qualification.

Next operational step: after applying and returning the SHA, run only preflight
with the same runtime roots/end policy and budget 10. Send its console line and
exit code. Do not raise limits, delete evidence, edit private values or resume
network collection until the actual category is measured. No private report file
needs to be sent or created for this step.

Verification: 49 new diagnostic cases; combined development run 80 passed;
focused CSV/ledger/collection/architecture/dependency selection 123 passed;
full pytest 3,653 passed, 4 skipped, one existing Starlette warning.
`git diff --check` clean. Tests assert both normal and dry-run categories,
exact budget/duplicate/CSV counts, no provider/writer invocation, no new runtime
paths and unchanged bytes, existing lock/output preservation, injected read
errors/source changes and private-exception redaction. Temporary pytest roots
are excluded from the commit and ZIP. No live diagnosis was performed here.

## Original collection implementation

Classification: `IMPLEMENTATION`. Fresh clean `develop` baseline:
`3507c2c6eb98b453675983bf61cbc3f394db9f66`.

## Audit and decision

The user returned local discovery counts: zero split-positive snapshots, one
canonical transaction CSV, zero exact identity candidates, two oversized files
skipped, qualification not performed and no source changes. The old snippet
silently skipped parse errors; these counts cannot establish absence of events.
The earlier positive AAPL qualification was workspace-only and its private
snapshot was correctly excluded from delivery. MCD's zero-split snapshot is not
a positive arithmetic test. Repeating discovery alone cannot obtain missing data.

The existing action collector already owns provider requests, strict snapshot
validation, immutable persistence and offline reuse. The smallest next change
is a bounded composition of that collector with the original CSV parser. The
portfolio `symbol` field is provider-independent, so it is used only as a request
candidate. No listing suffix, currency conversion, ISIN mapping or substitute
symbol is invented. A matching response is still not broker identity proof.

## Implemented command

```powershell
python -m investment_terminal.cli.portfolio_split_collect --help
```

Required options: `--transactions-directory`, `--snapshot-directory`,
`--report-output`, `--cache-directory`, `--end` (exclusive UTC date).
Optional: `--max-instruments` (default 10, range 1..50),
`--maximum-age-days` (default 7, range 1..365).

Input discovery recursively examines at most 100 CSV files, each at most four
MB; oversize/unreadable/unsafe inputs fail rather than masquerading as missing.
Unparseable CSVs are counted; exactly one canonical parse is required. Multiple
valid files fail rather than selecting by filename or modification time. Duplicate
transaction IDs fail ledger validation. Empty/no-trade input cannot proceed.
No private source file is read by the agent during development.

The plan groups BUY/SELL by instrument key in stable order and includes closed
positions. Each window starts two UTC days before the earliest original trade
(to include adjacent exchange-local sessions) and ends at the explicit cutoff.
Future end, more than 3,660 days, trades on/after end, changed identity,
unsupported type/symbol and duplicate candidate symbols across identities are
blocked. Only STOCK/ETF candidates are requested. Exceeding the instrument budget
fails preflight, never silently truncates the portfolio. Source completeness is
not inferred from a parsable CSV.

Snapshots use deterministic identity/window-derived names in the dedicated
private directory. The existing collector is called once per pending candidate;
its own history/metadata calls may entail multiple HTTP requests. No application
retry loop is added. First collector failure stops subsequent requests, retaining
`FAILED` and `PENDING` counts. Unchanged successful requests are reused offline
on a later run with a new report filename. Corrupt snapshots are not overwritten
or refetched. Stale/future acquisition time is `SNAPSHOT_AGE`, not a reason to
silently refresh. An explicit new snapshot directory is required for a new
full-window acquisition; previous evidence remains untouched.

The composition checks stage snapshot hashes, symbol/window identity, quote
currency and type before classifying observed splits. Metadata mismatch is
`BLOCKED`, not zero splits. Freshness is evaluated after each stage. A split
observation in the window is a candidate only: it need not fall within an actual
holding period, prove ISIN/listing equivalence or validate original trade basis.
No split projection is automatically executed.

## Privacy and failure behavior

New private schema 1 `PORTFOLIO_SPLIT_CANDIDATES` holds ordered identities,
windows, snapshot paths/hashes and outcomes, bound to exact source CSV bytes.
New redacted schema 1 `PORTFOLIO_SPLIT_COLLECTION_REPORT` holds only counts,
fixed categories, CSV/private-index hashes and policy. Both explicitly declare
`UNVERIFIED_PROVIDER_MAPPING` and `adjustment_performed=false`; completeness is
`UNKNOWN`. `COLLECTED` does not mean prices or holdings have been adjusted.

Paths must be absolute/non-symlink, report/private trees separate and cache not
overlap snapshots. Outputs are new-only. Cooperative directory/report locks
prevent concurrent runs of this composition; the collector retains per-snapshot
locks. Locks cannot prevent unrelated external editors. Source checks before and
after stages, atomic writes/readbacks, private hash and final snapshot hashes
detect changes before final result output. No database is opened and no CSV is
rewritten. Only candidate symbols/windows go to the provider, not broker trades.

`STOPPED` returns exit 1 with a redacted report when a collector returns failure.
Preflight, corrupt stage evidence or persistence failures return 1 with a fixed
stage message; a report is not guaranteed. Partial artifacts are deliberately
retained. A late failure may leave a complete-looking report: require the final
`RESULT` and exit code, not report existence alone. Do not delete outputs or retry
blindly. Use a new report path for reviewed recovery; snapshot reuse avoids
repeating successful network work. Stage collection reports remain private here.

`SEND`: only the aggregate report. `DO NOT SEND`: CSV, private selection,
snapshots, cache, stage outputs or database. Provider exception text and private
values are not copied into the aggregate. Invalid CSV count is not a guarantee
that the discovery tree contained no other relevant file formats.

## Verification and next gate

Tests use synthetic CSVs and fake providers; no live request or private runtime
access was made. Focused checks cover automatic selection, deterministic plan,
budgets, metadata mismatch versus zero events, provider stop with pending items,
offline repeat, stale/corrupt reuse, duplicate IDs, path/lock guards, source
preservation, redaction, write/readback failures and stage checksum mismatch.
Measured results: focused 183 passed (31 new cases); full pytest 3,604 passed,
4 skipped, one existing Starlette deprecation warning; `git diff --check` clean.
Test roots `.pytest-collection-focused` and `.pytest-collection-full` are excluded
from commit/ZIP. The initial 27-case development run also passed.

After applying the package, return the applied SHA for one short bounded
PowerShell invocation using the standard runtime directories. Review its counts
and categories before selecting a positive-split projection or resolving provider
identity. No manual prices/actions, synthetic broker trades or whole-market
scan are required. Production price adjustment remains blocked on known price
basis/cutoff and compatible quote/share integration, unchanged from the prior
split-projection package.
