# Investment Terminal
# Scoring Framework Specification

Version: 1.0.0
Status: Approved for implementation

## 1. Purpose

This document defines how Investment Terminal converts validated data into transparent, reproducible scores for Core ETFs, Satellite ETFs, long-term stocks, and position trades.

All scores use a 0–100 scale. Portfolio context is evaluated separately from asset quality.

## 2. Core Outputs

For every asset, return:

- Technical Score
- Trend Score
- Fundamental Score
- Valuation Score
- News Score
- Risk Score
- Portfolio Fit Score
- Confidence Score
- Raw Investment Score
- Asset Rating
- Portfolio Action
- Positive Reasons
- Negative Reasons
- Missing Data
- Risk Overrides
- Engine Version
- Data Timestamp

## 3. General Rules

1. No single indicator determines the final result.
2. Missing data lowers confidence.
3. Stale or inconsistent critical data blocks actionable recommendations.
4. Every contribution must be traceable.
5. Asset Rating and Portfolio Action are separate.
6. Portfolio constraints may change the action without changing the asset score.
7. Weights and thresholds belong in configuration.

## 4. Asset Profiles and Weights

### Core ETF

| Component | Weight |
|---|---:|
| Trend | 30% |
| Technical | 20% |
| Portfolio Fit | 25% |
| Risk | 15% |
| Valuation / Yield Context | 10% |

### Satellite ETF

| Component | Weight |
|---|---:|
| Trend | 30% |
| Technical | 25% |
| Risk | 20% |
| Portfolio Fit | 15% |
| News / Theme Context | 10% |

### Long-Term Stock

| Component | Weight |
|---|---:|
| Fundamental | 30% |
| Valuation | 20% |
| Trend | 20% |
| Technical | 15% |
| Risk | 10% |
| News | 5% |

### Position Trade

| Component | Weight |
|---|---:|
| Technical | 35% |
| Trend | 25% |
| Risk / Reward | 20% |
| News Catalyst | 10% |
| Fundamental Safety | 10% |

## 5. Technical Score

Inputs:

- RSI 14
- MACD line, signal, histogram
- SMA20, SMA50, SMA100, SMA200
- EMA20, EMA50, EMA200
- ATR and ATR percent
- Current and average volume
- 52-week position
- Support and resistance
- Breakout / pullback state

Suggested subweights:

| Signal Group | Weight |
|---|---:|
| Moving-average structure | 25% |
| Momentum | 25% |
| Volume confirmation | 15% |
| Price structure | 20% |
| Volatility quality | 15% |

Rules:

- RSI oversold is not automatically bullish.
- RSI overbought is not automatically bearish.
- MACD requires trend and price confirmation.
- Breakouts require volume confirmation.
- Excessive ATR reduces score unless reward-to-risk remains attractive.
- No individual input may contribute more than 25%.

## 6. Trend Score

Required horizons:

- 1 day
- 5 days
- 1 month
- 3 months
- 6 months
- 1 year

Long-term weights:

| Horizon | Weight |
|---|---:|
| 1 day | 5% |
| 5 days | 5% |
| 1 month | 15% |
| 3 months | 20% |
| 6 months | 25% |
| 1 year | 30% |

Position-trade weights:

| Horizon | Weight |
|---|---:|
| 1 day | 15% |
| 5 days | 20% |
| 1 month | 25% |
| 3 months | 20% |
| 6 months | 15% |
| 1 year | 5% |

Classifications:

- 85–100: Strong Uptrend
- 70–84: Uptrend
- 45–69: Neutral / Sideways
- 25–44: Downtrend
- 0–24: Strong Downtrend

## 7. Fundamental Score

Suggested composition:

| Metric Group | Weight |
|---|---:|
| Revenue and EPS growth | 25% |
| Free cash flow quality | 20% |
| Profitability and margins | 20% |
| Balance-sheet quality | 20% |
| Capital efficiency | 15% |

Rules:

- Negative free cash flow reduces score and appears in explanations.
- Falling margins reduce score.
- Excessive debt reduces score.
- One quarter must not dominate multi-year quality.
- Share dilution reduces score.
- Missing fundamentals lower confidence.

## 8. Valuation Score

Inputs:

- P/E
- Forward P/E
- PEG
- EV/EBITDA
- Price-to-sales
- Price-to-book where relevant
- Free-cash-flow yield
- Dividend yield where relevant
- Historical valuation range
- Sector-peer comparison

Suggested composition:

| Comparison | Weight |
|---|---:|
| Own historical range | 40% |
| Sector peers | 30% |
| Growth-adjusted valuation | 20% |
| Cash-flow / yield support | 10% |

## 9. News Score

Event scale:

| Event | Base Effect |
|---|---:|
| Strong Positive | +20 |
| Positive | +10 |
| Neutral | 0 |
| Negative | -10 |
| Strong Negative | -20 |

Start from 50 and clamp to 0–100.

Rules:

- News impact decays over time.
- Duplicate stories are deduplicated.
- Source quality affects confidence.
- Forums may provide context but never primary scoring.
- Material negative events may trigger a risk override.

## 10. Risk Score

Higher means better risk quality.

| Risk Group | Weight |
|---|---:|
| Volatility and drawdown | 25% |
| Liquidity | 15% |
| Balance-sheet / earnings stability | 20% |
| Event risk | 15% |
| Concentration and correlation | 15% |
| Currency and data-quality risk | 10% |

Hard overrides:

- Invalid or stale critical price data
- Ticker mismatch
- Suspicious price anomaly
- Severe liquidity problem
- Missing minimum data set
- Material unquantifiable event

Override action:

- INSUFFICIENT_DATA
- AVOID

## 11. Portfolio Fit Score

Inputs:

- Current and target allocation
- Sector, geographic and currency concentration
- Correlation with holdings
- Available cash
- Maximum position size
- Long-term versus trading budget

Rules:

- Strong assets may receive WAIT if overweight.
- Underweight Core ETFs may receive higher purchase priority.
- Trading exposure must remain inside the defined 5–10% budget.
- Portfolio Fit changes action, not raw asset score.

## 12. Confidence Score

| Factor | Weight |
|---|---:|
| Data completeness | 30% |
| Data freshness | 25% |
| Source reliability | 20% |
| Signal agreement | 15% |
| Anomaly checks | 10% |

Interpretation:

- 0–49: Insufficient Data
- 50–64: Informational only
- 65–79: Moderate confidence
- 80–100: High confidence

No actionable buy or sell below 65 confidence.

## 13. Raw Investment Score

Raw Investment Score = sum(Component Score × Profile Weight)

The raw score remains independent from current portfolio allocation.

## 14. Asset Rating

| Score | Rating |
|---:|---|
| 90–100 | Exceptional |
| 80–89 | Attractive |
| 70–79 | Positive |
| 60–69 | Neutral |
| 50–59 | Weak |
| 0–49 | Unattractive |

## 15. Portfolio Actions

- ACCUMULATE
- BUY
- HOLD
- WATCH
- WAIT
- REDUCE
- EXIT_TRADE
- AVOID
- INSUFFICIENT_DATA

Decision priority:

1. Data-quality gate
2. Hard risk overrides
3. Confidence threshold
4. Asset profile
5. Raw score
6. Existing holding status
7. Portfolio Fit
8. Trading entry and invalidation requirements

A numeric score alone must never trigger a trade.

## 16. Position-Trade Requirements

Every actionable trade requires:

- Entry zone
- Invalidation level
- Target zone
- Reward-to-risk
- Maximum position size
- Holding horizon
- Exit conditions

Default minimum reward-to-risk: 1.8

## 17. Explainability

Every result includes:

- Positive reasons
- Negative reasons
- Missing data
- Risk overrides
- Timestamp
- Sources
- Engine version

## 18. Configuration

Planned files:

- data/scoring.json
- data/settings.json

scoring.json must contain:

- Profile weights
- Component subweights
- Score thresholds
- Confidence thresholds
- Risk overrides
- News decay parameters
- Minimum reward-to-risk
- Configuration version

All profile weights must sum to 1.0. Invalid configuration must be rejected.

## 19. Testing

Required tests:

1. Component scorer tests
2. Threshold boundary tests
3. Missing-data tests
4. Stale-data tests
5. Price-anomaly tests
6. Asset-profile tests
7. Portfolio-overweight tests
8. Position-trade invalidation tests
9. Explainability tests
10. Reproducibility tests
11. Configuration validation tests

Live APIs are forbidden in unit tests.

## 20. Implementation Order

1. Scoring configuration schema and validator
2. Data quality validator
3. Asset profile classifier
4. Technical scorer
5. Trend scorer
6. Fundamental scorer
7. Valuation scorer
8. News scorer
9. Risk scorer
10. Portfolio Fit scorer
11. Confidence calculator
12. Decision orchestrator
13. Explanation builder
14. Recommendation repository
15. Report integration

## 21. Non-Goals for Version 1

- Automatic order execution
- Autonomous trading
- Machine-learning price forecasts
- Options strategies
- High-frequency trading
- Guaranteed predictions

## 22. Final Principle

Investment Decision Engine is a decision-support system, not an oracle.

Its purpose is to improve discipline, consistency, transparency and data quality while keeping the investor in control of every final decision.
