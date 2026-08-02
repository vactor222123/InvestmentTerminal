# Investment Terminal — Data Model

## Status

**Product:** Investment Terminal  
**Document type:** Canonical data-model specification  
**Document status:** Foundational  
**Milestone:** 2 — Historical and Decision Intelligence  

This document defines the canonical data concepts of Investment Terminal, their responsibilities, relationships, validation rules, serialization requirements, and long-term evolution.

It describes both:

- models already implemented in the current codebase;
- target models required by the approved architecture.

Implemented and planned concepts are identified explicitly.

`ARCHITECTURE.md` defines how domains interact. `CONSTITUTION.md` defines non-negotiable rules. This document defines what the product means when it uses terms such as portfolio, holding, recommendation, policy gap, review package, historical snapshot, confidence, and knowledge.

---

# 1. Data-Model Philosophy

Investment Terminal uses explicit domain models because financial data must remain:

- understandable;
- validated;
- reproducible;
- serializable;
- traceable;
- historically comparable;
- stable across product evolution.

Models do not exist merely because Python requires classes.

Each canonical model must answer a product or investment question.

Examples:

| Model | Question |
|---|---|
| `PortfolioHolding` | What instrument does the user own? |
| `CurrentPortfolio` | What does the user own now, including cash and policy? |
| `PortfolioSnapshot` | How is the portfolio structured? |
| `PortfolioPolicyGapResult` | Where does the portfolio differ from strategic targets? |
| `ContributionPlan` | How can available capital reduce strategic gaps? |
| `DeploymentDecision` | How much machine evidence supports deploying capital now? |
| Recommendation result | What is the deterministic machine view of an asset? |
| Review package | What complete evidence should be presented to history and AI? |
| Historical snapshot | What exactly did the system know at a specific moment? |
| Confidence result | How strong, complete, fresh, and consistent is the evidence? |
| Knowledge entry | What historically supported pattern has been derived from evidence? |

---

# 2. Canonical-Model Rules

## 2.1 One Canonical Meaning

The same business concept must not have multiple incompatible definitions.

For example:

- there is one canonical meaning of a portfolio holding;
- there is one canonical machine recommendation;
- there is one canonical policy-gap result;
- there will be one product-wide confidence model;
- there will be one immutable snapshot identity.

Different serialized views are allowed, but they must represent the same canonical concept.

## 2.2 Models and Serialized Representations

A Python model and its JSON representation are not separate business concepts.

```text
Canonical model
        ↓
to_dict or adapter
        ↓
JSON representation
        ↓
Review package or history
```

Adapters may reshape data for a consumer, but must not silently change its meaning.

## 2.3 Explicit State

Important states must use explicit values rather than inference from missing fields.

Examples include:

- `READY`;
- `PARTIAL`;
- `STALE`;
- `MISSING`;
- `INVALID`;
- `CONNECTED`;
- `NOT_CONNECTED`;
- `COST_BASIS_ONLY`;
- `MARKET_VALUE_CONNECTED`.

## 2.4 Immutable Value Objects

Financial results and historical evidence should use immutable value objects where practical.

Current models commonly use:

```python
@dataclass(frozen=True, slots=True)
```

This prevents accidental mutation after validation.

## 2.5 Validation at Construction

A canonical model should reject invalid state at creation.

Examples:

- negative quantity;
- invalid ISIN shape;
- portfolio policy weights that do not sum to `1.0`;
- duplicate portfolio instruments;
- strategy and sleeve combinations that conflict;
- recommendation counts that do not match universe size;
- breakdown values that do not sum to portfolio total.

## 2.6 Stable Financial Rounding

Money values use explicit commercial half-up rounding where financial totals are calculated.

Binary floating-point rounding must not be relied upon implicitly for cost-basis totals.

## 2.7 Time

All generated timestamps must use ISO 8601.

Target requirement:

```text
2026-08-02T18:30:00+00:00
```

Historical and external-source timestamps must include timezone information.

## 2.8 Currency

Monetary values must carry or inherit an explicit currency.

The current portfolio base currency is normally `EUR`.

Future multi-currency models must separate:

- instrument currency;
- quote currency;
- portfolio base currency;
- foreign-exchange conversion source;
- conversion timestamp.

---

# 3. Model Relationship Overview

```text
PortfolioPolicy
        │
        ├─────────────┐
        ▼             ▼
PortfolioHolding   cash_balance
        │             │
        └──────┬──────┘
               ▼
        CurrentPortfolio
               │
       ┌───────┴────────┐
       ▼                ▼
PortfolioSnapshot   PortfolioMarketValueResult
       │                │
       └────────┬───────┘
                ▼
     PortfolioPolicyGapResult
                │
                ▼
        ContributionPlan
                │
                ├──────────────┐
                ▼              ▼
    Recommendation Result   Market Evidence
                │              │
                └──────┬───────┘
                       ▼
              DeploymentDecision
                       │
                       ▼
            Investment Review Package
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
Historical Snapshot         Structured History
          │                         │
          └────────────┬────────────┘
                       ▼
             Historical Intelligence
                       │
                       ▼
                 Knowledge Entry
```

Not every arrow means direct class dependency.

Some relationships occur at the application-service or review-package level.

---

# 4. Portfolio Domain

## 4.1 `PortfolioHolding`

**Implementation status:** Implemented  
**Canonical location:** `investment_terminal/portfolio/current_portfolio_models.py`

### Purpose

Represents one non-cash instrument currently owned by the user.

Cash is deliberately not represented as a holding. It belongs to `CurrentPortfolio.cash_balance`.

### Current Fields

| Field | Type | Meaning |
|---|---|---|
| `symbol` | `str` | Internal human-readable portfolio symbol |
| `name` | `str` | Instrument display name |
| `asset_type` | `str` | Asset classification |
| `sleeve` | `str` | Strategic portfolio sleeve |
| `quantity` | `float` | Number of units owned |
| `average_cost` | `float` | Average acquisition cost per unit |
| `currency` | `str` | Cost-basis currency |
| `isin` | `str | None` | International security identifier |
| `exchange_ticker` | `str | None` | Market or exchange ticker |
| `strategy` | `str | None` | Holding strategy, resolved during validation |

### Supported Asset Types

```text
ETF
STOCK
BOND
GOLD
CASH
OTHER
```

`CASH` exists in the supported enumeration for broader domain consistency, but a `PortfolioHolding` rejects it.

### Supported Sleeves

```text
CORE
TACTICAL
RESERVE
```

### Supported Holding Strategies

```text
CORE_LONG_TERM
STOCK_LONG_TERM
POSITION_TRADE
```

Cash is represented separately as `CASH_RESERVE` in portfolio breakdowns.

### Derived Fields

#### `invested_cost`

```text
quantity × average_cost
```

Rounded to two decimals using commercial half-up rounding.

#### `instrument_key`

Stable matching priority:

```text
ISIN
    else exchange_ticker
    else symbol
```

This identifier is used for:

- duplicate detection;
- quote mapping;
- future historical identity resolution.

### Validation Rules

- `symbol` and `name` must be non-empty.
- `quantity` must be finite and greater than zero.
- `average_cost` must be finite and non-negative.
- `currency` is normalized to uppercase.
- ETF, bond, and gold holdings require an ISIN.
- Individual stocks cannot use the `CORE` sleeve.
- `CORE_LONG_TERM` requires `CORE`.
- `STOCK_LONG_TERM` and `POSITION_TRADE` require a stock in `TACTICAL`.
- Missing strategy is resolved backward-compatibly:
  - `CORE` → `CORE_LONG_TERM`;
  - tactical stock → `STOCK_LONG_TERM`.

### Serialization

The current `to_dict()` includes:

```json
{
  "symbol": "WORLD",
  "name": "iShares Core MSCI World USD (Acc)",
  "asset_type": "ETF",
  "sleeve": "CORE",
  "quantity": 126.51,
  "average_cost": 122.15,
  "currency": "EUR",
  "isin": "IE00B4L5Y983",
  "exchange_ticker": "EUNL",
  "strategy": "CORE_LONG_TERM",
  "instrument_key": "IE00B4L5Y983",
  "invested_cost": 15452.21
}
```

### Future Extensions

Potential future fields should be introduced through an explicit schema change:

- broker account;
- broker instrument identifier;
- acquisition date;
- tax lots;
- fees;
- accumulated distributions;
- target weight;
- position thesis;
- intended time horizon;
- maximum position size;
- position-trade entry and exit rules.

Tax lots must not be added by overloading `average_cost`; they require a separate model.

---

## 4.2 `PortfolioPolicy`

**Implementation status:** Implemented  
**Canonical location:** `investment_terminal/portfolio/current_portfolio_models.py`

### Purpose

Defines strategic target allocation for the whole portfolio, including cash.

### Current Fields

| Field | Type | Meaning |
|---|---|---|
| `core_target_weight` | `float` | Target core share of total portfolio |
| `tactical_target_weight` | `float` | Target tactical share |
| `cash_target_weight` | `float` | Target cash share |
| `monthly_contribution` | `float` | Default contribution-planning amount |
| `base_currency` | `str` | Portfolio reporting currency |

### Strategic Interpretation

Preferred long-term intent:

```text
80% CORE
10% TACTICAL
10% CASH
```

Supported compatibility ranges currently allow:

```text
CORE:     75%–85%
TACTICAL:  5%–15%
CASH:      5%–15%
```

### Invariants

```text
core_target_weight
+ tactical_target_weight
+ cash_target_weight
= 1.0
```

Tolerance is explicitly defined.

### Derived Field

`invested_target_weight`:

```text
core_target_weight + tactical_target_weight
```

### Important Semantic Rule

All weights are shares of total portfolio value, including cash.

They are not percentages of invested capital only.

---

## 4.3 `CurrentPortfolio`

**Implementation status:** Implemented  
**Canonical location:** `investment_terminal/portfolio/current_portfolio_models.py`

### Purpose

Represents the current user-owned portfolio input:

- portfolio identity;
- strategic policy;
- validated holdings;
- cash balance.

### Current Fields

| Field | Type |
|---|---|
| `name` | `str` |
| `policy` | `PortfolioPolicy` |
| `holdings` | `tuple[PortfolioHolding, ...]` |
| `cash_balance` | `float` |

### Invariants

- `holdings` must be a tuple.
- Every entry must be a `PortfolioHolding`.
- `instrument_key` values must be unique.
- `cash_balance` must be finite and non-negative.

### Derived Cost-Basis Values

- `invested_cost`;
- `total_cost_basis`;
- `core_cost`;
- `tactical_cost`.

### Input Sources

Current input paths include:

- JSON through `CurrentPortfolioLoader`;
- CSV through `PortfolioHoldingCsvImporter`, followed by generated portfolio configuration.

Future broker synchronization must adapt broker data into this canonical model rather than create a parallel portfolio representation.

---

## 4.4 Portfolio Input CSV

**Implementation status:** Implemented

### Current Required Columns

```text
symbol
name
asset_type
sleeve
quantity
average_cost
currency
isin
exchange_ticker
```

### Optional Columns

```text
strategy
```

### Parsing Rules

- UTF-8 or UTF-8 with BOM;
- comma-delimited;
- blank optional values become `None`;
- comma decimal input may be normalized where supported;
- invalid rows identify their CSV line number;
- legacy CSV without `strategy` remains supported.

CSV is an input format, not the canonical portfolio model.

---

# 5. Portfolio Snapshot Domain

## 5.1 `PortfolioBreakdownItem`

**Implementation status:** Implemented  
**Canonical location:** `investment_terminal/portfolio/portfolio_snapshot_models.py`

### Purpose

Represents one category inside a portfolio breakdown.

### Fields

| Field | Meaning |
|---|---|
| `key` | Category identifier |
| `amount` | Monetary amount |
| `weight` | Share of total portfolio |
| `percent` | Derived percentage |

### Invariants

- key is non-empty and normalized;
- amount is finite and non-negative;
- weight is between `0` and `1`.

---

## 5.2 `PortfolioSnapshot`

**Implementation status:** Implemented  
**Canonical location:** `investment_terminal/portfolio/portfolio_snapshot_models.py`

### Purpose

Represents a calculated structural view of the current portfolio.

The current implementation is cost-basis-based.

Market-value-based strategic analysis is a target evolution and should not silently replace cost basis without explicit source status.

### Core Fields

| Field | Meaning |
|---|---|
| `portfolio_name` | Portfolio identity |
| `base_currency` | Reporting currency |
| `total_value` | Total snapshot value |
| `invested_value` | Non-cash value |
| `cash_value` | Cash balance |
| `monthly_contribution` | Default contribution |
| `asset_breakdown` | Breakdown by asset type |
| `sleeve_breakdown` | Breakdown by portfolio sleeve |
| `strategy_breakdown` | Breakdown by holding strategy |

### Strategy Breakdown Keys

```text
CORE_LONG_TERM
STOCK_LONG_TERM
POSITION_TRADE
CASH_RESERVE
```

### Invariants

For each complete breakdown:

```text
sum(amounts) = total_value
sum(weights) = 1.0
```

For a zero-value portfolio:

```text
sum(weights) = 0.0
```

### Derived Values

- `cash_weight`;
- `invested_weight`.

### Accessors

The model supports explicit lookup by:

- asset;
- sleeve;
- strategy.

---

# 6. Portfolio Pricing Domain

## 6.1 `PortfolioPriceQuote`

**Implementation status:** Implemented

### Purpose

Represents one price observation used to value a portfolio instrument.

### Expected Semantic Fields

The implemented provider flow uses concepts equivalent to:

- `instrument_key`;
- `exchange_ticker`;
- `price`;
- `currency`;
- `quoted_at`;
- `source`.

### Target Requirements

A quote must identify:

- instrument;
- price;
- quote currency;
- exact time;
- source;
- whether the value represents a completed candle or live/intraday price;
- market venue where relevant.

---

## 6.2 Price Provider Contract

**Implementation status:** Implemented

### Purpose

Separates portfolio valuation from concrete price sources.

The portfolio market-value service asks a provider for a quote rather than downloading data directly.

Current implementations include JSON-based quote provision.

Target implementations include:

- SQLite latest-completed-candle provider;
- exchange-aware symbol resolution;
- future broker quote provider.

### Architectural Rule

`PortfolioMarketValueService` must not know whether a quote came from:

- JSON;
- SQLite;
- Yahoo;
- a broker;
- another validated source.

---

## 6.3 `PortfolioMarketValueResult`

**Implementation status:** Implemented

### Purpose

Represents current priced portfolio state.

### Core Semantic Values

- invested cost basis;
- invested market value;
- cash value;
- total market value;
- unrealized profit or loss;
- unrealized return percentage;
- valued positions;
- generation time.

### Target Extension

Future versions should include:

- complete/partial pricing status;
- missing quotes;
- quote ages;
- currency-conversion details;
- market-value strategy breakdown;
- concentration measures;
- daily portfolio change.

---

# 7. Strategic Policy-Gap Domain

## 7.1 `PortfolioPolicyGapItem`

**Implementation status:** Implemented  
**Canonical location:** `investment_terminal/portfolio/portfolio_policy_gap_models.py`

### Purpose

Compares one current strategic allocation with its target.

### Fields

| Field | Meaning |
|---|---|
| `key` | Strategic bucket |
| `current_amount` | Current monetary amount |
| `current_weight` | Current portfolio share |
| `target_amount` | Target monetary amount |
| `target_weight` | Target portfolio share |
| `gap_amount` | `target_amount - current_amount` |
| `gap_weight` | `target_weight - current_weight` |
| `status` | Derived allocation state |

### Statuses

```text
UNDERWEIGHT
ON_TARGET
OVERWEIGHT
```

### Gap Semantics

Positive gap:

```text
target exceeds current
```

Negative gap:

```text
current exceeds target
```

---

## 7.2 `PortfolioPolicyGapResult`

**Implementation status:** Implemented

### Current Strategic Keys

```text
CORE_LONG_TERM
TACTICAL_TOTAL
CASH_RESERVE
```

`TACTICAL_TOTAL` combines:

```text
STOCK_LONG_TERM + POSITION_TRADE
```

This is intentional at the top-level strategic-policy layer.

A future tactical sub-policy may divide that bucket further.

### Current Calculation Basis

Policy gaps currently derive from `PortfolioSnapshot`, which is cost-basis-based.

### Target Requirement

The review package must state whether a policy gap is based on:

- cost basis;
- complete current market value;
- partial market value with fallback.

The basis must never be ambiguous.

---

# 8. Contribution Planning Domain

## 8.1 `ContributionPlanItem`

**Implementation status:** Implemented  
**Canonical location:** `investment_terminal/portfolio/contribution_plan_models.py`

### Purpose

Represents one proposed strategic destination for available capital.

### Fields

- strategic key;
- amount;
- share of available capital;
- explanation.

### Current Scope

The planner chooses strategic buckets.

It does not yet select a specific ETF or stock.

---

## 8.2 `ContributionPlan`

**Implementation status:** Implemented

### Fields

| Field | Meaning |
|---|---|
| `available_capital` | Capital supplied to planner |
| `deployable_capital` | Capital allocated to positive gaps |
| `retained_cash` | Unallocated remainder |
| `items` | Strategic allocations |
| `status` | Plan state |

### Statuses

```text
ALLOCATE
HOLD_CASH
NO_CAPITAL
```

### Invariant

```text
deployable_capital + retained_cash = available_capital
```

### Current Planning Rule

Available capital is distributed proportionally across positive strategic gaps.

Deployment is capped at the total positive gap.

Excess remains cash.

### Important Limitation

A contribution plan is not a timing recommendation.

It answers:

> Where would capital improve strategic alignment?

It does not by itself answer:

> Should the capital be invested today?

That question belongs to deployment and final interpretation.

---

# 9. Market Analysis and Recommendation Domain

## 9.1 Market Universe

**Implementation status:** Implemented concept

### Purpose

Defines the candidate instruments to be analysed together.

Current universes include named text-file definitions such as:

```text
mega_cap_tech
us_large_cap_30
```

### Target Canonical Model

A future explicit `MarketUniverse` model should include:

- universe identity;
- version;
- instrument identifiers;
- asset type;
- inclusion rationale;
- source;
- effective date.

Text files may remain an input representation.

---

## 9.2 Technical Analysis Result

**Implementation status:** Implemented across current analysis modules

### Purpose

Represents deterministic technical evidence for one instrument.

Typical evidence includes:

- moving averages;
- RSI;
- MACD;
- volatility;
- trend state;
- momentum state;
- technical score;
- warnings;
- source-candle time.

### Data-Model Requirement

Raw indicator values, classifications, and final technical score must remain distinguishable.

---

## 9.3 Fundamental Analysis Result

**Implementation status:** Implemented

### Purpose

Represents validated company fundamentals and derived fundamental evidence.

Current architecture supports sector-aware normalization.

### Semantic Categories

- growth;
- profitability;
- financial health;
- valuation;
- coverage;
- risk factors;
- sector-specific interpretation.

### Requirement

Raw metrics must not be overwritten by normalized scores.

Both should be preservable.

---

## 9.4 Ranking Candidate

**Implementation status:** Implemented

### Purpose

Represents one analysed instrument in a ranked universe.

### Expected Content

- symbol;
- rank;
- component scores;
- overall score;
- technical evidence;
- fundamental evidence;
- risk factors;
- coverage;
- ranking reasons.

### Invariant

Rank order must remain deterministic for the same evidence and tie-breaking rules.

---

## 9.5 Machine Recommendation

**Implementation status:** Implemented concept

### Current Labels

The current recommendation domain uses labels including:

```text
BUY
ACCUMULATE
HOLD
WATCH
AVOID
SELL
```

Not every run necessarily emits every label.

### Required Semantic Content

A canonical recommendation should eventually include:

- instrument identity;
- recommendation label;
- generated time;
- overall score;
- reason codes;
- positive factors;
- negative factors;
- risk factors;
- coverage;
- confidence;
- previous recommendation where available;
- recommendation-rule version.

### Important Rule

Recommendation is machine evidence.

It is not equivalent to final personal action.

---

# 10. Deployment Decision Domain

## 10.1 `DeploymentDecision`

**Implementation status:** Implemented as a machine-evidence model  
**Canonical location:** `investment_terminal/review/deployment_decision_models.py`

### Purpose

Summarizes whether current internal machine evidence supports capital deployment.

### Modes

```text
INVEST_NOW
PARTIAL_DEPLOYMENT
WAIT
```

The current service intentionally caps machine-only deployment because external context is not yet integrated.

### Fields

- mode;
- deployment fraction;
- confidence label;
- positive recommendation count;
- neutral recommendation count;
- negative recommendation count;
- universe size;
- reasons;
- cautions;
- external-context-required flag.

### Derived Value

```text
positive_breadth = positive_count / universe_size
```

### Important Limitation

Current deployment confidence is a coarse internal label.

It is not yet the approved product-wide confidence framework.

When the unified Confidence domain is introduced, this field must be migrated or explicitly renamed to prevent semantic conflict.

---

# 11. Review Package Domain

## 11.1 Investment Review Package

**Implementation status:** Implemented as a structured JSON product artifact

### Purpose

The review package is the primary interface between:

- deterministic Python evidence;
- immutable history;
- AI-assisted interpretation.

### Canonical Filename

```text
investment_review_package.json
```

### Current Major Sections

The package currently includes or reserves sections such as:

- metadata;
- data freshness;
- market summary;
- stock analysis;
- machine recommendations;
- opportunities;
- portfolio;
- ETF analysis;
- watchlist;
- external context.

Some sections may currently be `NOT_CONNECTED`.

### Portfolio Section

Current portfolio review data includes:

- cost-basis snapshot;
- market value when quotes are available;
- quote source;
- policy gap;
- contribution plan;
- status and fallback message.

### Target Metadata Contract

The package should evolve to include:

```json
{
  "metadata": {
    "schema_version": "2.0",
    "package_id": "uuid",
    "generated_at": "ISO-8601",
    "generator": "investment-terminal",
    "product_version": "version",
    "timezone": "UTC",
    "checksum": "sha256"
  }
}
```

### Target Section Contract

Every major section should support:

- `status`;
- `source`;
- `generated_at`;
- `data_as_of`;
- `coverage`;
- `issues`;
- `payload`.

Existing package structure should migrate backward-compatibly where possible.

### Required Distinction

The package must distinguish:

1. facts;
2. calculations;
3. machine signals;
4. missing external context;
5. final interpretation, which occurs outside deterministic package generation.

---

# 12. Issue and Data-Quality Models

## 12.1 Structured Issue

**Implementation status:** Partially implemented in audit and readiness outputs  
**Target status:** Canonical cross-domain model required

### Purpose

Represents one problem, warning, or informational limitation.

### Target Fields

```json
{
  "code": "QUOTE_NOT_FOUND",
  "severity": "WARNING",
  "domain": "PORTFOLIO",
  "symbol": "EMIMI",
  "message": "No validated current quote was available.",
  "effect": "Market value and allocation are incomplete.",
  "recoverable": true,
  "fallback": "COST_BASIS"
}
```

### Severity Values

Target canonical values:

```text
INFO
WARNING
ERROR
CRITICAL
```

A shared issue model should replace incompatible ad hoc warning dictionaries over time.

---

## 12.2 Coverage Result

**Implementation status:** Implemented in multiple domains  
**Target status:** Canonical shared semantics required

### Purpose

Explains how much required evidence is available.

### Target Fields

- required field count;
- available field count;
- missing field names;
- coverage fraction;
- coverage classification;
- affected decision components.

Coverage and confidence are related but not identical.

Coverage measures presence.

Confidence also measures quality, freshness, consistency, and agreement.

---

# 13. Confidence Domain

## 13.1 `ConfidenceComponent`

**Implementation status:** Planned

### Purpose

Represents one evidence-quality dimension.

### Target Fields

| Field | Meaning |
|---|---|
| `key` | Component identity |
| `score` | Normalized evidence-quality score |
| `weight` | Contribution to aggregate result |
| `status` | Component state |
| `reasons` | Positive evidence |
| `penalties` | Reductions |
| `missing_evidence` | Known gaps |
| `source_refs` | Evidence references |

Potential keys:

```text
DATA_QUALITY
DATA_FRESHNESS
FUNDAMENTAL_COVERAGE
TECHNICAL_AGREEMENT
TREND_STABILITY
PORTFOLIO_FIT
MARKET_REGIME
NEWS_COVERAGE
MACRO_COVERAGE
GEOPOLITICAL_CONTEXT
HISTORICAL_CONSISTENCY
DECISION_STABILITY
```

---

## 13.2 `ConfidenceResult`

**Implementation status:** Planned

### Purpose

Represents overall evidence quality for one decision or review.

### Target Fields

- subject identity;
- overall score;
- qualitative band;
- components;
- calculation version;
- generated time;
- reasons;
- limitations;
- missing evidence.

### Non-Negotiable Semantic Rule

```text
confidence ≠ probability of profit
```

Confidence must never be serialized under field names such as:

```text
success_probability
win_probability
expected_profit_probability
```

unless a separate statistically validated model is explicitly introduced.

---

# 14. Decision Trace Domain

## 14.1 `DecisionTrace`

**Implementation status:** Planned

### Purpose

Preserves why a machine output existed.

### Target Fields

```json
{
  "decision_id": "uuid",
  "decision_type": "MACHINE_RECOMMENDATION",
  "subject_key": "GOOGL",
  "generated_at": "ISO-8601",
  "label": "ACCUMULATE",
  "previous_label": "WATCH",
  "positive_reason_codes": [],
  "negative_reason_codes": [],
  "risk_codes": [],
  "thresholds": [],
  "evidence_refs": [],
  "confidence": {},
  "rule_version": "version"
}
```

### Requirements

- reason codes must be stable identifiers;
- human-readable messages may evolve independently;
- thresholds used at decision time must remain recoverable;
- traces must be archived with the package.

---

# 15. Historical Intelligence Domain

## 15.1 `HistoricalSnapshot`

**Implementation status:** Planned for the next product milestone

### Purpose

Represents one immutable archived review package and its identity metadata.

### Target Fields

| Field | Meaning |
|---|---|
| `snapshot_id` | Stable UUID |
| `package_id` | Review package identity |
| `schema_version` | Package schema |
| `product_version` | Generator version |
| `generated_at` | Original generation time |
| `archived_at` | Archive-write time |
| `relative_path` | Archive location |
| `checksum` | SHA-256 of exact bytes |
| `supersedes` | Optional corrected snapshot reference |
| `status` | Archive state |

### Archive Path Convention

Target convention:

```text
data/history/YYYY/MM/YYYY-MM-DDTHH-MM-SSZ_<package-id>.json
```

The timestamp alone must not be the sole identity.

### Invariants

- archived bytes are immutable;
- duplicate exact package may be detected by checksum;
- an existing snapshot is never silently replaced;
- corrections create a new snapshot.

---

## 15.2 `HistoryManifestEntry`

**Implementation status:** Planned

### Purpose

Provides lightweight navigation without opening every archived package.

### Target Fields

- snapshot identity;
- generation time;
- schema version;
- file path;
- checksum;
- portfolio name;
- portfolio value if available;
- top recommendation if available;
- deployment mode if available;
- package status.

The manifest is an index.

The immutable package remains the authoritative archived evidence.

---

## 15.3 Structured History Records

**Implementation status:** Planned

Planned normalized history entities include:

- snapshot;
- portfolio snapshot;
- holding state;
- recommendation state;
- ranking state;
- policy-gap state;
- contribution-plan state;
- deployment state;
- confidence state;
- issue state;
- decision trace;
- instrument quote reference.

Each record must reference its source snapshot.

Structured history should be rebuildable from immutable packages where feasible.

---

## 15.4 `SnapshotDiff`

**Implementation status:** Planned

### Purpose

Represents change between two compatible snapshots.

### Target Change Categories

- recommendation transition;
- rank change;
- score change;
- confidence change;
- portfolio holding change;
- cash change;
- portfolio weight change;
- policy-gap change;
- contribution-plan change;
- deployment-mode change;
- issue added or resolved;
- data-coverage change.

### Compatibility Requirement

Snapshots must be schema-compatible or migrated before comparison.

---

# 16. Knowledge Domain

## 16.1 `KnowledgeEntry`

**Implementation status:** Future

### Purpose

Represents a historically derived, traceable product insight.

### Example

```json
{
  "knowledge_id": "uuid",
  "knowledge_type": "FACTOR_OUTCOME_ASSOCIATION",
  "subject_scope": "US_LARGE_CAP",
  "statement": "Positive signals with strong trend stability had better 90-day outcomes in the observed sample.",
  "sample_size": 84,
  "observation_window": "90D",
  "evidence_snapshot_ids": [],
  "method_version": "1.0",
  "limitations": [],
  "generated_at": "ISO-8601"
}
```

### Invariants

A knowledge entry must include:

- evidence references;
- sample size;
- observation horizon;
- calculation method;
- limitations;
- generation time.

Knowledge must not overwrite facts.

Knowledge must not imply causation from correlation without support.

---

# 17. Future Journal Models

## 17.1 Opportunity Journal Entry

**Status:** Future

Tracks an opportunity identified by the system, including whether it was acted upon.

Potential fields:

- instrument;
- detected time;
- recommendation;
- reasons;
- confidence;
- user action;
- future evaluation horizons;
- observed outcomes.

## 17.2 Decision Journal Entry

**Status:** Future

Tracks a user decision separately from the machine recommendation.

Potential fields:

- machine recommendation;
- user action;
- action timestamp;
- user rationale;
- amount;
- linked portfolio transaction;
- later outcome;
- review notes.

The machine recommendation and the user decision must remain separate concepts.

## 17.3 Trade Journal Entry

**Status:** Future

Represents an executed position-trading lifecycle.

It should not be inferred only from holding snapshots when explicit transaction data becomes available.

---

# 18. Serialization Rules

## 18.1 JSON Safety

Canonical exports must use JSON-safe values.

Not allowed directly:

- `NaN`;
- positive or negative infinity;
- non-string dictionary keys;
- naive datetime objects;
- arbitrary Python objects.

## 18.2 Null Semantics

`null` means the value is not available or not applicable.

It must not be used interchangeably with:

- zero;
- empty string;
- false;
- missing field.

## 18.3 Lists and Ordering

Use lists when order is meaningful or stable export order is useful.

Examples:

- ranked recommendations;
- historical changes;
- issue lists.

Use keyed objects when stable identity lookup is more important.

## 18.4 Money

Money fields should use values rounded to documented precision.

Future high-precision tax-lot or FX models may require decimal-string serialization.

## 18.5 Percentages

The canonical calculation field should normally be a fraction:

```json
"weight": 0.10
```

Human-readable exports may additionally include:

```json
"percent": 10.0
```

The meaning must remain explicit.

---

# 19. Schema Versioning

## 19.1 Version Location

Every top-level long-lived product artifact must contain `schema_version`.

This applies to:

- review packages;
- historical snapshots;
- history manifests;
- history exports;
- future knowledge exports.

## 19.2 Version Policy

Recommended format:

```text
MAJOR.MINOR
```

- `MAJOR`: breaking semantic or structural change;
- `MINOR`: backward-compatible addition.

## 19.3 Migration

Breaking schema changes require:

- migration logic or documented migration tool;
- compatibility tests;
- updated `DATA_MODEL.md`;
- updated examples;
- an ADR for significant changes.

## 19.4 Model Version vs Schema Version

These are different:

- schema version describes serialized structure;
- rule or model version describes calculation behavior;
- product version describes the application release.

A historical package may need all three.

---

# 20. Single Sources of Truth

| Concept | Source of truth |
|---|---|
| Current owned instruments | `CurrentPortfolio` |
| Strategic targets | `PortfolioPolicy` |
| Instrument identity in portfolio | `PortfolioHolding.instrument_key` |
| Completed current market candles | operational SQLite market-data store |
| Current priced portfolio | `PortfolioMarketValueResult` |
| Structural portfolio view | `PortfolioSnapshot` |
| Strategic difference | `PortfolioPolicyGapResult` |
| Strategic contribution allocation | `ContributionPlan` |
| Machine recommendation | canonical recommendation result |
| Python-to-AI interface | investment review package |
| Exact past system state | immutable historical snapshot |
| Queryable historical facts | history SQLite linked to snapshots |
| Derived historical insight | versioned knowledge entry |

No later derived representation may silently replace its upstream source.

---

# 21. Model Lifecycle

Canonical lifecycle:

```text
External or user input
        ↓
Parse
        ↓
Validate
        ↓
Normalize
        ↓
Create canonical model
        ↓
Calculate derived model
        ↓
Serialize through stable contract
        ↓
Include in review package
        ↓
Archive exact snapshot
        ↓
Normalize into history
        ↓
Compare and evaluate
        ↓
Derive knowledge
```

At each transition, source identity and status should remain traceable.

---

# 22. Backward Compatibility

Current compatibility requirements include:

- portfolio holdings without `strategy` remain loadable;
- existing `85/10/5` portfolio policies remain valid while preferred policy is `80/10/10`;
- legacy CSV headers without the optional strategy column remain loadable;
- review generation can continue with cost-basis fallback when price quotes are unavailable, but the fallback must be visible.

Compatibility logic must be tested and eventually retired through explicit migrations, not accidental breakage.

---

# 23. Data Privacy

Portfolio and future transaction data are personal financial information.

Data models and exports should follow these rules:

- examples must not contain unnecessary private data;
- secrets and credentials must never appear in models or exported review packages;
- broker identifiers should be minimized;
- user-facing exports should include only data required for analysis;
- local private portfolio files should remain separable from public repository fixtures;
- future AI exports should permit redaction of account-specific details.

---

# 24. Documentation Maintenance

`DATA_MODEL.md` must be updated when:

- a canonical model is added;
- a model changes semantic meaning;
- a serialized schema changes;
- a new long-lived status or enum is added;
- a source of truth changes;
- historical storage changes;
- confidence semantics change;
- a backward-compatibility rule is introduced or removed.

Pure internal refactoring that preserves public semantics does not require a data-model version change.

---

# 25. Data-Model Review Checklist

Before accepting a new model, verify:

- What investment or product question does it answer?
- Is a canonical model already available?
- Is the model immutable where appropriate?
- Are invalid states rejected?
- Are units, currencies, and timestamps explicit?
- Is source identity preserved?
- Can it be serialized without information loss?
- Can it be stored historically?
- Can future versions migrate it?
- Does it duplicate another domain?
- Are null and zero semantically distinct?
- Does it expose facts separately from interpretation?
- Are tests included?
- Is this document updated?

---

# 26. Guiding Data Statements

> Canonical models represent product meaning; files represent transport or storage.

> Missing evidence is data and must remain visible.

> Cost basis and market value are different concepts and must never be confused.

> Recommendation and user action are different concepts.

> Confidence and probability are different concepts.

> History stores facts; knowledge stores traceable derived patterns.

> Every historical record must remain linked to the exact evidence snapshot from which it came.

> Stable data contracts make long-term intelligence possible.
