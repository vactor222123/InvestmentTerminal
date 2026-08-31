# InvestmentTerminal — Roadmap After Audit

## Purpose

This document defines the development order after the complete product alignment audit.

Source documents:

- docs/PROJECT_VISION.md
- docs/PROJECT_FULL_AUDIT.md

The roadmap follows the existing architecture:

Data
→ Deterministic Analysis
→ Review Package
→ History
→ Knowledge
→ AI Interpretation

---

# Phase 1 — Multi-Asset Evidence Foundation

Goal:

Expand from stock-focused analysis into a broader investment data platform.

Scope:

- ETF data contracts
- fund/security identity model
- exchange metadata
- currency support
- trading calendars
- source provenance
- data quality contracts

Outcome:

A reliable foundation for stocks, ETFs and additional asset classes.

---

# Phase 2 — Portfolio Lifecycle Intelligence

Goal:

Transform portfolio snapshots into a complete investment history.

Scope:

- transaction ledger
- purchases/sales
- dividends
- fees
- realised/unrealised performance
- portfolio valuation history
- tax-lot readiness

Outcome:

Full portfolio evolution analysis.

---

# Phase 3 — Portfolio Decision Intelligence

Goal:

Improve investment decisions.

Scope:

- portfolio risk analysis
- drawdown analysis
- volatility
- correlation
- rebalancing evidence
- strategy-specific rules:
  - CORE_LONG_TERM
  - STOCK_LONG_TERM
  - POSITION_TRADE
  - CASH_RESERVE

Outcome:

Evidence-based portfolio improvement recommendations.

---

# Phase 4 — Context and Market Intelligence

Goal:

Add information that cannot be represented only by financial metrics.

Scope:

- news ingestion
- macroeconomic data
- geopolitical context
- events
- sentiment/context evidence

Requirements:

- provenance
- freshness
- explicit uncertainty

Outcome:

Richer AI-assisted investment reviews.

---

# Phase 5 — Market Discovery

Goal:

Analyze the broader investment universe.

Scope:

- maintained asset universe
- thousands of companies
- ETF discovery
- sector analysis
- screening pipeline

Outcome:

Find opportunities beyond manually configured assets.

---

# Phase 6 — Integrated Investment Review Workflow

Goal:

Create the complete operating workflow.

Future workflow:

refresh data
→ validate evidence
→ analyze portfolio
→ analyze market
→ generate Review Package
→ archive history
→ compare changes
→ produce investment review

Audited implementation order:

1. immutable workflow run and stage-result contract — COMPLETE;
2. typed deterministic evidence assembly across portfolio, context, and market
   discovery boundaries — COMPLETE;
3. Review Package generation and atomic export — COMPLETE;
4. explicit immutable archive and rebuildable History projection stages —
   COMPLETE;
5. deterministic previous-snapshot selection and comparison — COMPLETE;
6. one user-facing review command with a hermetic end-to-end contract —
   COMPLETE.

Closure readiness is `NOT CLOSED` at baseline `0212fb2`. The success path is
complete, but the command must durably report failed and dependent skipped
stages, including successful archive registration followed by projection
failure. See `docs/PHASE_6_CLOSURE_AUDIT.md`.

The bounded failure-reporting remediation is complete: failed reports preserve
completed artifacts, the first failed stage, dependent skips, and archive
success before projection failure. The next action is the repeated closure
audit.

Phase 6 is closed at verified baseline `2590773`. The closure record is
`docs/PHASE_6_CLOSURE.md`.

Boundary audit:

```text
docs/PHASE_6_WORKFLOW_BOUNDARY_AUDIT.md
```

The workflow coordinates existing public services. It does not own analytical
algorithms, silently promote History into Knowledge, invoke AI implicitly, or
grant trade-execution authority.

---

# Phase 7 — Operational Data and First Real Use

Goal:

Turn the implemented architectural and analytical platform into a populated,
repeatable, operationally verified product using real data.

Scope:

- audit, configure, and connect real market-data providers;
- establish stable bulk and incremental ingestion;
- measure approximately 20-year candle coverage for supported stocks and ETFs;
- establish maintained universes for major companies, approximately the largest
  1000 companies where data and licensing permit, developing/growth companies,
  popular ETFs, and instruments not manually named in advance;
- schedule regular updates and expose refresh status, duration, failures, and
  freshness;
- load and verify the user's real portfolio and transaction history;
- connect real news and external-context sources with provenance, freshness,
  uncertainty, and quality;
- validate screening, discovery, trend, candle-pattern, and recommendation
  evidence on populated datasets;
- prepare a safe portable database or evidence package for explicit ChatGPT
  analysis;
- verify monitoring, backup, restore, recovery, and data-quality reporting;
- run several complete real investment-review workflows and record runtime,
  provider, coverage, quality, and usability gaps before UI design.

Phase 7 must distinguish:

- architecture capability;
- configured provider capability;
- actual populated data coverage;
- measured operational performance;
- analytical evidence;
- AI or human interpretation.

Neither approximately 1000-company universe coverage nor approximately 20-year
candle coverage may be claimed until measured against populated data.

Package 1:

```text
Operational data baseline and coverage report
```

Package 1 is the smallest coherent prerequisite: define one deterministic,
machine-readable operational inventory that reports configured provider
capability, populated candle ranges/counts, maintained-universe membership,
portfolio/context presence, refresh observations, and explicit unknown or
unmeasured states. It must be read-only, use existing repositories and runtime
configuration, and must not add a speculative provider, scheduler, UI, broker,
or analytical authority.

Package 1 is COMPLETE. Its contract, implementation boundary, and verification
record are documented in `docs/PHASE_7_PACKAGE_1.md`.

The first local Package 1 run found no real populated operational inputs and is
recorded in `docs/PHASE_7_OPERATIONAL_BASELINE_1.md`. It selects Package 2 —
Yahoo Historical Candle Operational Qualification — to verify one bounded real
provider request before any bulk ingestion work.

Package 2 implementation is COMPLETE. Its first explicit live request returned
a durably reported `FAILED` result, so operational Yahoo qualification and bulk
ingestion remain incomplete. See `docs/PHASE_7_PACKAGE_2.md`.

The fresh-clone rerun resolved yfinance cache ownership and isolated the
remaining failure to blocked outbound Yahoo HTTPS connectivity. See
`docs/PHASE_7_YAHOO_QUALIFICATION_RERUN.md`.

The repeated local qualification then succeeded for MSFT with 12 daily
candles. Package 3 adds one bounded persistence composition root over the
existing Yahoo client, historical service, and SQLite candle repository.
Broader ingestion remains deferred until its persisted result is reviewed.

Package 3 then succeeded and its exact repeat proved idempotent persistence.
Package 4 adds indexed stored-boundary measurement to report schema version 2;
one controlled one-year MSFT expansion is next, not multi-instrument ingestion.

That expansion stored 251 daily candles across a 364-day observed span.
Package 5 adds History-owned comparison against explicit versioned session
evidence. Calendar sourcing remains the next prerequisite; weekday inference
is prohibited.

Packages 6–8 add the explicit coverage command, integrity validation, and
bounded `XNAS@1` evidence. Package 9 adds separately versioned, official-source
backed `XNAS@2` evidence for the controlled five-year MSFT window. The measured
result is 1,254 expected and observed sessions with no missing or unexpected
candles. Mass ingestion remains out of scope.

Package 10 selects AAPL only after official Nasdaq-listed identity
confirmation, reuses the exact bounded `XNAS@2` evidence, and measures 1,254
observed candles against 1,254 expected sessions with no gaps or unexpected
candles. The exact repeat inserts zero rows. The next boundary is a separate
XNYS instrument/evidence audit; no XNAS calendar may be silently reused.

Package 11 selects `XNYS:IBM` for the later operational run and adds bounded
`XNYS@1` evidence backed only by official ICE/NYSE schedules and the January 9,
2025 exceptional-close memorandum. It emits 1,254 deterministic sessions but
does not ingest IBM. Generating/verifying the JSON and measuring one IBM request
are the next separate operational action.

Package 12 executes and verifies the exact `XNYS@1` document, but the current
permission profile prevents writing it to `C:\runtime\reports` or modifying the
operational SQLite. `IBM_TOTAL=0` was confirmed read-only. IBM ingestion remains
blocked until explicit runtime write access is available; no other instrument
may bypass this step.

Package 13 records a successful user-executed bounded IBM Yahoo qualification:
1,254 daily candles cover the exact requested five-year window and `failure` is
null. Staged `XNYS@1` still passes checksum verification, while read-only
inspection confirms `IBM_TOTAL=0` and SQLite integrity `ok`. The current
execution profile still cannot place the calendar or modify runtime SQLite, so
no ingestion was attempted and no other instrument may bypass this step.

Package 14 completes the controlled IBM/XNYS operational step. The initial
ingestion stores 1,254 daily candles; its exact repeat inserts zero rows and
reports 1,254 duplicates. All 1,254 stored candles match all 1,254 explicit
`XNYS@1` sessions with no missing or unexpected evidence, completeness 1.0,
and SQLite integrity `ok`. A focused measured-state audit is required before
another instrument or broader ingestion is selected.

Package 15 re-runs the read-only operational baseline against the populated
market store. MSFT, AAPL, and IBM each contain 1,254 bounded daily candles, for
3,762 total, while per-series freshness, refresh observability, and measured
performance remain `UNMEASURED`. Existing freshness and refresh services have
no dedicated bounded operational CLI/report. The selected next package is a
single-instrument refresh-observability composition root; scheduling,
multi-instrument refresh, and mass ingestion remain deferred.

Package 16 adds the dedicated single-instrument refresh-observability CLI and
atomic versioned report over the existing Yahoo, repository, freshness, and
refresh boundaries. `SUCCESS`, `NOT_READY`, and `FAILED` outcomes preserve
before/after freshness, exact import evidence, duration, and visible failures.
One explicit live MSFT run is next; no other instrument, scheduler, or mass
refresh is authorized before its result is reviewed.

Package 17 records the first live MSFT refresh report. Trading-session
freshness transitions from `STALE` to `FRESH`; the bounded overlap downloads
10 candles, inserts four, and identifies six duplicates in 1.149708 seconds.
MSFT then contains 1,258 daily candles through 2026-08-24 and SQLite integrity
is `ok`. An exact same-checked-at repeat is required to measure the
already-fresh provider bypass before any broader refresh.

Package 18 confirms that exact same-checked-at repeat: both freshness states
are `FRESH`, refresh is not attempted, import is null, all transfer counters
are zero, and SQLite remains unchanged and healthy. The canonical operational
baseline still cannot consume an explicit refresh report, so its refresh and
performance fields remain `UNMEASURED`. A focused backward-compatibility audit
of that projection is next; another instrument and broader refresh remain
deferred.

Package 19 audits every operational-baseline consumer and selects an optional,
conditional `REFRESH_REPORT` store as the smallest backward-compatible seam.
When no refresh path is supplied, the existing schema-version-1 JSON and its
eight-store inventory must remain unchanged. Explicit valid evidence may make
refresh observability/performance `READY`; malformed, unsupported, or
inconsistent evidence must remain visible and fail closed. This package runs no
refresh and authorizes no broader ingestion.

Package 20 implements that conditional projection without changing baseline
schema version 1 or the omitted-input eight-store shape. Valid `SUCCESS`,
`NOT_READY`, and `FAILED` reports become bounded operational evidence;
malformed, unsupported, inconsistent, naive-time, or invalid-duration reports
remain visible `ERROR` stores and cannot produce measured readiness. A read-only
run against the existing live MSFT report projects nine stores and reports both
refresh observability and measured performance as `READY`. No refresh,
scheduling, multi-instrument aggregation, analysis, or trading is added.

Package 21 repeats the Phase 7 closure-readiness audit against the actual
runtime inventory and the implemented operational boundaries. Phase 7 is not
ready to close: only the market-candle store and one explicit refresh report
are `READY`; current portfolio, transactions, valuations, maintained universe,
external context, backups, and workflow evidence are absent, and broad Phase 7
coverage targets remain unmeasured. The database remains healthy with 3,766
daily candles across MSFT, AAPL, and IBM. The smallest safe next package is a
focused audit of the existing current-portfolio JSON/CSV input, validation,
persistence, privacy, and baseline-projection seams before any private data is
requested or written. Another instrument, scheduler, and mass refresh remain
deferred.

Package 22 audits the complete current-portfolio input surface. The typed JSON
loader, CSV importer, atomic holdings writer, snapshot CLI, repository privacy
guards, and redacted operational-baseline projection already provide the
smallest coherent path; no duplicate qualification code is justified. The
runtime portfolio is absent, the default path is repository-relative, and a
holdings import requires an existing portfolio whose policy and cash balance
remain user-owned. CSV `--preview` exposes full holdings and is not a shareable
operational artifact. Package 23 is therefore a user-executed controlled
runtime qualification: prepare one private portfolio JSON under `C:\runtime`,
validate it locally, and return only the redacted baseline report. Transactions,
valuations, workflow execution, another instrument, scheduling, and mass
refresh remain deferred.

Package 23 records the successful user-executed current-portfolio runtime
qualification. The schema-version-1 redacted baseline reports
`CURRENT_PORTFOLIO=READY`, three holdings, and EUR without exposing holding
identities, quantities, costs, cash, contribution, or policy. Market candles
and the bounded MSFT refresh evidence remain `READY`; transaction and valuation
stores remain absent. The next smallest package is a focused audit of the
existing portfolio-transaction CSV, import, SQLite, CLI, privacy, and baseline
seams before any private transaction data is requested or written. Valuation
generation, workflow execution, another instrument, scheduling, and mass
refresh remain deferred.

Package 24 audits the transaction input and persistence surface. The canonical
CSV parser, immutable ledger models, idempotent import accounting, schema-
versioned SQLite repository, and redacted operational-baseline projection
exist, but no transaction CLI, tracked example CSV, or versioned redacted
qualification/import report exists. The current import service commits one
repository add at a time, so an unexpected later failure does not provide an
all-or-nothing durable batch guarantee. The smallest safe next package is a
parse-only transaction CSV qualification CLI and synthetic example with an
atomic redacted report. No private input or database mutation is authorized
until that result and the later atomic batch-import boundary are reviewed.

Package 25 adds that parse-only qualification boundary. The CLI reuses the
canonical parser, atomically writes a redacted schema-version-1 report, and
includes a synthetic example plus a privacy-protected working filename. It
exposes only aggregate count, type counts, and occurrence range and never
initializes SQLite. One private user-executed qualification is next; durable
import remains prohibited pending a later atomic batch boundary.

The controlled private qualification then completed successfully for 62 events
without database mutation. Package 26 audits the durable import seam and
reproduces partial persistence when an unexpected failure occurs after an
earlier per-row commit. Schema version 1 is sufficient, but the repository
contract has no atomic batch operation. The smallest safe next package is a
persistence-agnostic batch append implemented atomically by both in-memory and
SQLite repositories, with row-aligned duplicate accounting and durable rollback
tests. A user-facing import CLI and operational database mutation remain
deferred.

Package 27 adds the repository-level atomic batch append selected by that
audit. Row-aligned outcomes preserve every imported and duplicate input,
including repeats inside one batch. The in-memory adapter stages before
publication, while SQLite owns one transaction for the whole batch; a simulated
later trigger failure rolls back earlier candidates and preserves pre-existing
rows after reopen. The import-result JSON and schema version 1 remain unchanged.
A focused audit of the bounded durable import CLI/report and private-runtime
handoff is next; no operational database has been initialized or modified.

Package 28 audits the bounded durable import composition. Existing parser,
atomic batch repository, SQLite store, and read-only baseline projection are
sufficient; no schema or baseline extension is needed. The missing boundary is
one versioned redacted CLI report with explicit metadata, privacy-safe failure
normalization, exact-repeat evidence, rollback tests, and visible ownership of
the unavoidable SQLite-commit/report-write gap. A post-commit report failure is
reconciled by repairing the output and rerunning the same immutable identities,
not by claiming rollback. Package 29 implements this boundary before any
private runtime import.

Package 29 implements the bounded durable import command and immutable redacted
report without changing SQLite schema 1 or the operational baseline. Parsing
precedes database initialization; batch persistence is atomic; metadata and
persistence failures are privacy-safe; exact repeat is explicitly idempotent.
The SQLite-commit/report-write boundary has a distinct visible error and an
exact-repeat reconciliation path. One controlled user-executed private import
is next; valuation and workflow execution remain deferred until its report is
reviewed.

Package 30 records the controlled user-executed private import. The redacted
report is `SUCCESS`: all 62 qualified rows were inserted, duplicates are zero,
stored total is 62, and occurrence coverage remains 2026-05-05T16:38:00Z
through 2026-08-21T16:28:00Z. Failure is null and the returned report contains
no private identities or values. One exact repeat is required before valuation
or workflow work; it must preserve stored total and coverage while reporting
all 62 submitted rows as duplicates.

Package 31 records the exact repeat. The redacted report is `SUCCESS`: all 62
submitted immutable transaction identities were duplicates, zero rows were
inserted, stored total remained 62, and occurrence coverage remained
2026-05-05T16:38:00Z through 2026-08-21T16:28:00Z. Failure is null and no
private identities or values were returned. The next smallest safe package is a
focused audit of the existing transaction-derived valuation path and its quote,
currency, cutoff, persistence, atomicity, privacy, and redacted-report
boundaries before any private valuation or integrated workflow execution.

Package 32 audits the transaction-derived valuation path. Position
reconstruction, realised and quote-backed unrealised performance, immutable
valuation snapshots, and append-only SQLite persistence already exist with
identity, currency, temporal, ownership, rollback, duplicate, and strict-JSON
guards. No service or CLI composes those boundaries from the operational
transaction store, and no redacted valuation report exists. The calculators do
not independently exclude transactions later than `valued_at`, while the JSON
quote input defines no freshness threshold. The next package is therefore one
bounded service and CLI/report implementation with an explicit fail-closed
transaction cutoff, complete matching offline quotes, atomic snapshot append,
post-commit report-failure distinction, and privacy-safe aggregate evidence.
Live quote fetching, FX conversion, freshness policy, private execution, and
integrated workflow execution remain deferred.

Boundary audit:

```text
docs/PHASE_7_OPERATIONAL_DATA_BOUNDARY_AUDIT.md
```

---

# Phase 8 — User Product Layer

Goal:

Create user-facing application capabilities after real operational gaps have
been measured.

Scope:

- Windows/Desktop UI;
- portfolio dashboard;
- portfolio and transaction editing through the UI;
- provider and refresh configuration;
- explicit manual workflow launch;
- Review Package viewer;
- warnings, freshness, quality, uncertainty, and missing-evidence views;
- History navigation and snapshot comparison;
- reports;
- read-only broker integrations;
- possible Trade Republic integration.

Phase 8 must not move analytical calculations into the UI, hide missing or
low-quality evidence, invoke AI without explicit user action, automatically
promote History into Knowledge, give brokers write access, or execute trades.
Package 33 implements the bounded transaction-derived valuation service and CLI.
It enforces an explicit transaction cutoff, complete matching offline quotes,
currency/time validation, immutable SQLite append, privacy-safe failure, and a
distinct post-commit report-write error. Private quote qualification is next;
no private valuation or workflow execution has occurred.
Package 34 finds no read-only offline quote qualification boundary. The JSON
loader and valuation calculation guards are reusable, but the only composition
CLI can append a private snapshot. A bounded parse/reconstruct-only qualifier
with a privacy-safe aggregate report is required before private quote review.
Package 35 adds read-only exact quote-coverage qualification with privacy-safe
reporting and no valuation persistence. Controlled private qualification is next.
Package 36 measured 62 transactions, 10 reconstructed open positions, and 10
required private quotes, but matching could not start because immutable ledger
instrument identities lack exchange tickers. Valuation remained untouched. A
bounded provenance-aware metadata enrichment audit is next; historical payload
rewrites and guessed venue mappings are excluded.
Package 37 confirms that immutable transaction payloads must not be rewritten
and that neither the private quote file nor the unprovenanced current-portfolio
file can serve as metadata authority. The smallest safe next package is a
provider-neutral, provenance-aware metadata evidence document and detached
read-only position projection, composed first into quote qualification only.
Package 38 implements that strict private metadata document and detached
projection. Qualification may now opt into exact `READY` metadata coverage with
a caller-owned age limit while preserving its redacted schema-version-1 report
and leaving immutable transaction evidence untouched. One controlled private
metadata-backed qualification is next; valuation remains excluded.
Package 39 stops that manual operational handoff before runtime execution. The
existing private metadata document is sufficient as a reusable local registry,
but its initial mappings require independent evidence. Official OpenFIGI v3 can
map ISIN jobs without an API key, although multi-listing results must not be
resolved by first-row selection and provider exchange codes must not be treated
as MICs. A bounded exact-ticker-confirming bootstrap with private raw-response
preservation and redacted reporting is next.
Package 40 implements the bounded OpenFIGI v3 client, deterministic batching,
exact private response archives, strict ticker confirmation, atomic metadata,
and a privacy-safe aggregate report. Synthetic success and failure paths are
green. One controlled private bootstrap is next; quote qualification and
valuation remain excluded until that evidence is reviewed.
Package 41 records that controlled bootstrap as blocked after the first of two
planned responses was archived. The schema-version-1 report proves fail-closed
behavior but does not safely distinguish provider rejection, malformed data,
missing FIGI, or ticker ambiguity. A versioned privacy-safe failure category is
the smallest next package; private response inspection, rerun, qualification,
and valuation remain excluded.
Package 42 advances the redacted OpenFIGI report to schema version 2 with one
bounded privacy-safe failure category. Provider request, archive, response,
provider error/warning, ticker, FIGI, metadata-write, and unexpected failures
remain distinguishable without exposing response text or private identities.
One categorized controlled private rerun is next; qualification and valuation
remain excluded until its result is reviewed.
Package 43 records that rerun as blocked in the first batch with
`TICKER_MISMATCH_OR_AMBIGUOUS`. The safe report cannot distinguish a missing
candidate ticker from a confirmed candidate accompanied by alternative listing
tickers, so changing acceptance would require guessing. Splitting those two
privacy-safe categories is next; raw-response inspection, rerun, qualification,
and valuation remain excluded.
Package 44 advances the redacted report to schema version 3 and splits the
combined ticker outcome into candidate absent and candidate present with
alternative listings. Both remain fail-closed and expose no ticker values or
response details. One controlled schema-3 rerun is next; raw-response
inspection, qualification, and valuation remain excluded.
Package 45 records the schema-3 run as blocked in the first batch with
`CANDIDATE_TICKER_WITH_ALTERNATIVES`. This proves the candidate is present and
that alternate listing rows cause the strict set-equality rejection. The
smallest remediation is deterministic filtering to all candidate-ticker FIGIs,
while candidate absence and missing candidate FIGIs remain fail-closed.
Qualification and valuation remain excluded.
Package 46 accepts mappings containing alternative listings only when the
candidate ticker is present, then deterministically retains all and only
candidate-ticker FIGIs. Candidate absence and missing candidate FIGIs remain
fail-closed. One controlled filtered bootstrap is next; private response
inspection, qualification, and valuation remain excluded.
Package 47 records the filtered run as blocked in the first batch with
`CANDIDATE_TICKER_ABSENT`. Alternative listings no longer terminate the run,
but another candidate ticker has no matching provider row. Automatic provider
ticker adoption is not justified, and the redacted report cannot identify the
private entry. A focused audit of a separate local-only remediation diagnostic
is next; rerun, qualification, and valuation remain excluded.
Package 48 selects a separate schema-version-1 local-only candidate-absence
diagnostic behind an explicit CLI path. It contains only failure facts already
available at the service boundary. The shareable report remains schema version
3, ticker acceptance stays fail-closed, and automatic correction remains
excluded. Bounded implementation is next; rerun, qualification, and valuation
remain excluded.
Package 49 implements the typed candidate-absence diagnostic and its explicit
atomic CLI output while leaving the shareable report at schema version 3.
Diagnostic persistence failure remains redacted and non-zero, and metadata is
unchanged. One controlled private rerun is next; only the redacted report may
be returned, while the diagnostic and raw archive remain local-only.
Package 50 records the controlled rerun as blocked with the same
`CANDIDATE_TICKER_ABSENT` category after one archived response. The unchanged
category proves the new local diagnostic did not encounter its fail-closed
write path, while the identifying artifact remained private. Local operator
review against independent identity/venue evidence and a justified private
quote correction are next; another rerun, qualification, and valuation remain
excluded.
Package 51 records a privacy-safe local review: one quote matches the private
instrument and retains the submitted candidate ticker, while 17 returned
provider tickers exclude that candidate. No automatic correction occurred.
Independent identity and intended-venue verification is next; correction,
rerun, qualification, and valuation remain excluded.
Package 52 replaces the manual-verification handoff with an automated resolver
path. The existing runtime can query Yahoo Search and already owns private
OpenFIGI listing evidence, but Yahoo's documented search contract does not
guarantee ISIN queries. A bounded Yahoo ISIN-search qualification with private
candidates and a redacted aggregate report is next. Cross-provider selection,
quote correction, rerun, valuation, and broader automation remain excluded.
Package 53 implements the bounded Yahoo ISIN-search adapter, typed normalized
candidates, atomic private output, and schema-version-1 aggregate redacted
report. No manual identifier input or quote mutation occurs. One controlled
private search measurement is next; cross-provider resolution and downstream
operations remain excluded until its result is known.
Package 54 records that successful two-candidate measurement and implements a
fail-closed exact match between the existing quote ticker and Yahoo candidates
returned for the same diagnostic ISIN. Only one exact match creates private
evidence; no runtime business data is mutated.
Package 55 records the product-direction correction. Existing ingestion,
storage, indicators, transactions, and valuation remain the foundation, while
the critical path moves to resumable ten-year multi-instrument acquisition and
a factual ChatGPT-ready export. Single-ticker failures become isolated
secondary outcomes and cannot block unrelated instruments.
Package 56 finds that `ensure_many` is fail-fast, three-year freshness
orchestration rather than a restart boundary. The selected implementation
composes per-symbol imports with a private request-correlated atomic checkpoint,
isolated sequential outcomes, and a redacted report for 1-20 instruments.
Package 57 implements those request/checkpoint/report contracts, sequential
failure isolation, exact resume correlation, and the operational CLI.
Package 58 records the successful 10-instrument ten-year run and exact resume,
then versions the report to separate current-run work from cumulative evidence.
Package 59 verifies schema-2 resume and selects official State Street SPY daily
fund holdings as an automatically acquired broad-US universe. It preserves fund
holdings semantics, raw provenance, and a separate Yahoo symbol projection;
undocumented S&P scraping and ingestion remain excluded.
Package 60 supersedes that unimplemented SPY path because exact S&P membership
is not required. The selected broad universe uses official Nasdaq-listed and
other-exchange-listed directories, exact dual archives, official-field filters,
and explicit Yahoo projection failures before downstream eligibility work.
Package 61 implements that dual-source client, immutable archives, typed
normalization/projection, private universe, and redacted qualification report.

The live qualification then measures 12,424 unique accepted members. Package 62
audits the required eligibility step and rejects Nasdaq market-level files and
Nasdaq-venue per-symbol share as a neutral consolidated-liquidity shortcut. The
next implementation is a complete-universe, resumable Yahoo 90-day OHLCV scan
in bounded 100-member slices. It records private availability/data-quality and
median `close * volume` evidence while exposing only redacted aggregate
progress. Ranking and ten-year batch generation remain blocked until all
members have terminal outcomes for one versioned scan.

Package 63 implements that boundary. The operations service validates and
checksums the complete private universe, derives the exact 90-day window from a
caller-supplied aware end time, processes no more than 100 pending members, and
atomically checkpoints every terminal result. The CLI writes a schema-version-1
redacted progress report. One controlled private slice is next; complete scan
coverage remains required before selection or ten-year batch generation.

The first slice returns 10 successes and 90 generic `APIError` failures.
Package 64 confirms that typed yfinance causes are lost when only the client's
outer `APIError` is checkpointed, and that schema-1 cannot retry any stored
failure. The selected schema-2 remediation atomically preserves completed
evidence, converts legacy generic failures to capped retry-pending outcomes,
publishes stable aggregate causal categories, and stops immediately when rate
limiting is observed. Slice 002 remains blocked until implementation and a
controlled 10-attempt remediation measurement.

Package 65 implements the schema-2 migration and retry contract. Stable causal
categories are derived from exception types, legacy successes remain terminal,
generic API failures become retry-pending, retries precede new members, and the
first rate-limit result is checkpointed before `PAUSED` return. A single
10-attempt private remediation invocation is next; only its redacted report may
be reviewed.

Package 66 records that private remediation through its redacted report. The
migration preserved 100 existing outcomes; 10 retries produced eight
`INVALID_RESPONSE` and two `NO_PRICE_DATA` final outcomes, with no halt category.
The next bounded invocation is limited to the 80 remaining migrated legacy
failures. Slice 002, ranking, and ten-year ingestion remain blocked until those
retry-pending outcomes are resolved or explicitly paused.

That retry drain completes with 88 aggregate `INVALID_RESPONSE` and two
`NO_PRICE_DATA` failures. Package 67 audits the implementation and finds that
the dominant category combines multiple direct Yahoo client validation exits
with eligibility-service validation failures, persists no subtype, and is
terminal. The next implementation adds schema-3 typed diagnostics and one
final bounded retry of those 88 outcomes before any new member is attempted.

Package 68 implements that schema-3 boundary with typed local validation
categories, APIError compatibility, atomic schema-2 migration, preserved attempt
counts, retry-first ordering, and unchanged rate-limit halt behavior.

Package 69 records the completed typed retry measurement. The 100 terminal
first-slice outcomes comprise 10 successes, 86 numeric-response failures, two
OHLC failures, and two no-price failures; no retry or rate-limit evidence
remains. The operator explicitly pauses further scanning. Package 70 adds a
read-only diagnostic that automatically selects the first numeric failure,
refetches only its unchanged 90-day raw series, and emits dates and stable
defect categories without identities or values. That controlled run returns 48
valid rows and no current defect. Package 71 confirms that schema 3 cannot
reconcile this recovered response because numeric failures are terminal and the
three-attempt cap is closed. The next implementation is schema 4 with one
bounded fourth production-client attempt for numeric failures only. Slice 002
remains blocked.
