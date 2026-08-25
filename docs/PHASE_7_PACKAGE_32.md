# Phase 7 Package 32 - Transaction-Derived Valuation Operational Audit

Package type: `AUDIT`.

Source baseline: `develop @ d4df2f56ac64aa6bd49b399f4dc197246e792b06`.

## Scope

This package audits the existing transaction-derived valuation path after the
private transaction import and exact-repeat evidence. It reads repository code,
contracts, and tests only. It does not read private transaction or quote data,
create a valuation database, generate a valuation, execute the integrated
workflow, or authorize analysis or trading.

## Existing boundaries

The repository already provides the domain and persistence building blocks:

- `SQLitePortfolioTransactionRepository.snapshot()` reconstructs the typed,
  deterministically ordered ledger from the versioned transaction store;
- `PositionReconstructor` derives open BUY/SELL positions with average-cost
  accounting and rejects oversells, identity changes, and currency changes;
- `RealizedPerformanceCalculator` derives sale-level and currency-separated
  realised results without mutating the ledger;
- `UnrealizedPerformanceCalculator` requires one explicit quote per open
  position and preserves quote time and source provenance;
- quote identity, exchange ticker, and cost currency must match, and a quote
  later than `valued_at` fails closed;
- `PortfolioValuationSnapshot` combines realised and unrealised evidence only
  when ledger and portfolio ownership match;
- `SQLitePortfolioValuationHistoryRepository` appends the full immutable
  snapshot in one SQLite transaction, rejects duplicate snapshot identities,
  validates store ownership metadata, and round-trips strict JSON;
- `JsonPortfolioPriceProvider` is an available explicit offline quote input.

The valuation snapshot and its SQLite payload contain private instrument,
quantity, cost, price, proceeds, and gain/loss evidence. They belong under
`C:\runtime\data` and are not shareable operational reports.

## Measured gap

There is no application service or CLI that composes the transaction store,
bounded valuation time, explicit quotes, performance calculators, immutable
snapshot, and valuation repository. There is also no schema-versioned redacted
operational report for success or failure.

The calculators consume the ledger supplied to them. They do not independently
exclude transactions later than `valued_at`. A composition boundary that loads
the complete operational ledger must therefore fail closed when any transaction
is later than the requested valuation time, or construct an explicitly tested
cutoff ledger. Silently valuing future transactions is not acceptable.

The existing JSON quote provider validates quote structure and uniqueness but
does not define a freshness threshold. The implementation must not invent one.
It must preserve explicit quote timestamps, require every open position to have
a matching quote, reject future quotes and currency mismatches, and state that
quote age remains caller-owned evidence.

The legacy `QuoteRepository` is not a compatible substitute: it stores a
different symbol-scoped quote model and does not implement
`PortfolioPriceProvider` with canonical instrument identity and exchange ticker.

## Smallest safe implementation package

Add one bounded transaction-derived valuation service and CLI/report contract
that composes only the established domain and SQLite boundaries. It must:

1. require explicit transaction database, private quote JSON, valuation
   database, ledger/portfolio metadata, snapshot identity, and timezone-aware
   `valued_at`;
2. fail closed before valuation persistence on transaction ownership mismatch,
   any transaction later than `valued_at`, missing or mismatched quotes,
   unsupported currency conversion, invalid quote time, calculation failure, or
   valuation-store metadata mismatch;
3. build realised and unrealised projections from the same bounded ledger and
   append exactly one immutable valuation snapshot transactionally;
4. write a separate atomic schema-version-1 report with status, timing,
   transaction/open-position/quote/currency aggregate counts, stored snapshot
   total, valuation-time coverage, normalized failure, and explicit
   limitations;
5. exclude all paths, identities, instruments, quantities, prices, monetary
   values, proceeds, returns, references, and raw snapshot data from that
   report;
6. distinguish a committed snapshot followed by report-write failure so an
   operator cannot mistake durable success for rollback;
7. add focused success, cutoff, quote, currency, ownership, duplicate,
   rollback, report-write, strict-JSON, and privacy tests.

Live quote fetching, FX conversion, quote-freshness policy, valuation of current
portfolio cash, scheduling, integrated workflow execution, analysis, and
trading remain out of scope.

## Next step

Implement the bounded transaction-derived valuation CLI and redacted report
described above with synthetic tests only. Do not request or execute a private
valuation until that implementation package is reviewed and pushed.

## Verification

```text
focused valuation/transaction/quote/persistence/privacy/architecture: 94 passed
full: 2,767 passed, 4 skipped
existing warnings: 1 Starlette deprecation warning
git diff --check: clean
```
