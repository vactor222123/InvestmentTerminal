# Phase 7 — explicit split-only projections

## Scope and audited baseline

Classification: `IMPLEMENTATION`, authorized by the user's request to audit and
implement price/share split handling. Fresh clean `develop` was verified at
`860ad718030414bfcca4ca5b45c2a056bedf5f0d` before changes. Mandatory architecture,
domain and delivery context was read; unchanged context was byte-compared to
the previously read baseline. This package supersedes the weekly-composition
next step, not the existing price/action provenance limitations.

The repository already collects immutable normalized corporate-action snapshots
and adds factual action context to research exports. `corporate_actions.py`
defines split units as new shares per old share, exchange-local event dates,
half-open UTC windows, hashes and `UNKNOWN` completeness. The existing
`position_reconstruction.py` and `realized_performance.py` replay BUY/SELL without
split events. `transaction_derived_valuation.py` consumes those legacy results.
Neither the candle table nor original trade schema records an adjustment basis.

The Yahoo client uses `auto_adjust=False`; that is not proof that older stored
closes are as-traded. The upstream [yfinance price-repair documentation](https://github.com/ranaroussi/yfinance/wiki/Price-repair)
describes missing historical split adjustments and repair calibration risks.
Consequently, blindly dividing existing stored prices could double-adjust them.
No unsupported interpretation of that flag, manual market value or price-jump
heuristic is used to fill missing provenance.

## Implemented behavior

- `market/split_adjustment.py`: immutable bounded daily OHLC and a pinned split
  plan; pure forward/reverse/multiple split projections, no volume or persistence.
- `portfolio/split_projection.py`: original-trade replay for one exact instrument,
  with split-adjusted quantity, preserved cost and gross average-cost realized
  gain/loss. Other instruments and primary evidence remain untouched.
- `cli/split_positions.py`: offline CSV/action snapshot composition with source
  pins, explicit freshness, private/redacted outputs and atomic readback checks.

For a split ratio `r`, pre-effective-session shares are multiplied by `r` and
known as-traded prices divided by `r`. For multiple later events use their
product. Price bars on the effective exchange-local date are post-split. Trade
execution on that date is rejected because a daily provider label does not prove
broker intraday ordering. Timezone conversion precedes date comparison.

All selected original trades must fall inside the action window, in chronological
ledger order, with stable instrument identity and settlement currency. Exact
provider symbol, quote currency and instrument type must match; no cross-listing
or ISIN-to-symbol mapping is guessed. The original transactions must include the
complete position history: this module cannot detect omitted earlier buys or
invent transfers/opening balances. `AS_TRADED` is an explicit caller attestation,
not a certification of broker completeness.

Trade quantities are replayed in common end-date units using exact rational
arithmetic. Original quantity times original unit price determines gross cash;
adjusted rounded prices never replace cash values. A sell releases proportional
average cost and must not exceed available shares. Full disposal yields no
position, not a synthetic zero-sized holding. A forward 2-for-1 split of 10
shares bought at 100 gives 20 shares at average cost 50, cost 1,000 unchanged.
Selling 15 at 60 leaves 5 shares/cost 250 and gross realized gain 150.

Fractional entitlements are retained. Cash-in-lieu, broker rounding, fees,
dividends, tax lots, FX conversion and total return are explicitly not inferred.
Unrepresentable numeric outputs, ambiguous duplicate split dates, stale/future
snapshots, unknown basis, out-of-window observations and identity mismatches fail.
No-split observations are a conditional identity projection, not completeness.

Price input has either `AS_TRADED` basis with no adjustment metadata or
`SPLIT_ADJUSTED` with cutoff and action-content hash. Repeating a projection with
the same evidence/cutoff is a no-op; rebasing adjusted output with different
evidence is rejected. A hash proves lineage, not the truth of declared basis.
The price API is not wired to legacy SQLite or exposed as a basis-override CLI.
Portfolio output is a different type from the input ledger, preventing accidental
replay of derived quantities as original transactions.

## CLI and output contract

Discover the executable interface with:

```powershell
python -m investment_terminal.cli.split_positions --help
```

Required arguments: `--transactions`, `--transactions-sha256`,
`--actions-snapshot`, `--actions-sha256`, `--instrument-key`,
`--trade-basis AS_TRADED`, `--actions-maximum-age-days` (1..365),
`--private-output`, `--report-output`. Supply verified absolute local paths and
new output names; this is not a command to guess missing runtime inputs.
The command uses the existing CSV parser, not an alternative broker importer.
It makes no network requests and does not open SQLite.

Private schema 1 `SPLIT_PORTFOLIO_PROJECTION` records exact source CSV and
canonical ledger hashes, identity, position/cost/gain values and explicit
limitations. The redacted schema 1 `SPLIT_PORTFOLIO_PROJECTION_REPORT` records
only counts, source/private/evidence hashes, evaluation policy and limitations.
It has status `PROJECTED_WITH_LIMITATIONS` and market-price status
`NOT_PERFORMED_UNVERIFIED_STORED_BASIS`. No symbol, quantity, cost, profit, path
or exception detail is in that report. Source snapshot/document hashes bind the
plan; action completeness remains `UNKNOWN`, never upgraded by successful math.

Paths must be absolute, non-symlink, distinct and non-ancestral; sources/private
values cannot be within the report directory. Existing destinations and lock
files are refused. Separate cooperative locks, source checks before/after work,
atomic writes and payload readback protect the handoff. Locks do not protect
against arbitrary non-cooperating external writers.

Failure returns 1 with a fixed stage, never private exception text. Partial
private/report outputs are preserved and must not be deleted or blindly retried.
A report written before a final source/hash failure is only stage evidence;
accept overall completion only with exit 0 and the final `COMPLETE` line. Recovery
requires inspecting the failed stage and choosing new destinations, not assuming
a two-file transaction. Only the report is marked `SEND`; source CSV, snapshot,
private projection and databases are `DO NOT SEND`.

## Verification

- New focused module: 53 tests passed. Coverage includes forward/reverse/multiple
  events, trades between events, fractional exact disposal, reopening, unaffected
  instruments, timezone/session boundaries, repeated adjustment, unknown price
  basis, overflow/underflow, zero cost, freshness boundaries and oversells.
- Combined focused selection: 233 passed, including corporate actions, legacy
  positions/realized valuation, CSV models/parser and architecture guards.
- Full pytest: 3,573 passed, 4 skipped; one existing Starlette deprecation warning.
- Test roots: `.pytest-splits-focused` and `.pytest-splits-full`, excluded from
  delivery. Development runs (43 then 53 cases) also passed.
- Persistence failures cover corrupt/checksum-changed input, alias paths, existing
  locks, private/report write/readback failures and changes after readback; there
  is no false completion, overwrite or private exception leak.
- `git diff --check`: clean. No live provider request, private runtime read/write,
  SQLite operation or actual broker holding adjustment was performed.

## Closure and next operational gate

The deterministic projection capability is implemented; the entire requested
production split stage is NOT yet closed. Existing JSON consumers retain their
old behavior. Do not present existing portfolio valuation or SMA as split-aware.

After applying this package, return the applied SHA. The next bounded operational
step is read-only discovery of existing snapshots and matching original trades,
then one offline positive-split qualification with redacted evidence. MCD's
qualified zero-split snapshot cannot demonstrate real split arithmetic. If no
matching complete trade history exists, report that blocker rather than fabricate
broker transactions or demand manual market prices.

Before price/valuation integration, a source adapter must establish and persist
price adjustment basis/cutoff and align it with derived quantities and quotes.
The missing legacy provenance cannot be manufactured retrospectively. Broker
split-day ordering and fractional settlement need separate evidence where they
occur. These gates prevent incorrect P/L and double adjustment across future
instruments; they are not ticker-specific exceptions.
