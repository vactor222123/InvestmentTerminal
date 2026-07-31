# Investment Terminal

# Decision Engine Specification

Version: 1.0.0

Status:
Approved

---

# Purpose

Decision Engine transforms raw market data into structured investment recommendations.

It combines technical analysis, trend analysis, fundamentals and market context into one final Investment Score.

The Decision Engine itself does not download data.

It only evaluates already validated information stored in the database.

---

# Philosophy

No recommendation should depend on a single indicator.

Every recommendation must be based on multiple independent signals.

Technical indicators confirm price behaviour.

Fundamental indicators confirm business quality.

Market conditions confirm probability.

---

# Decision Flow

```
Market Data
        │
        ▼
Validation
        │
        ▼
Technical Analysis
        │
        ▼
Fundamental Analysis
        │
        ▼
Market Analysis
        │
        ▼
Risk Analysis
        │
        ▼
Investment Score
        │
        ▼
Recommendation
```

---

# Score Components

## Technical Score

Weight

35%

Inputs

RSI

MACD

EMA Trend

SMA Trend

Volume

ATR

52 Week Position

Trend Strength

---

## Fundamental Score

Weight

30%

Inputs

Revenue Growth

EPS Growth

ROE

Debt

Cash Flow

P/E

PEG

Dividend

---

## News Score

Weight

20%

Inputs

Company News

Sector News

Macro News

Analyst Ratings

Insider Transactions

---

## Trend Score

Weight

15%

Inputs

Daily Trend

Weekly Trend

Monthly Trend

Six Month Trend

Relative Strength

---

# Investment Score

Range

0 - 100

Interpretation

95 - 100

Exceptional Opportunity

90 - 94

Strong Buy

80 - 89

Buy

70 - 79

Accumulation

60 - 69

Watch

50 - 59

Neutral

40 - 49

Reduce

Below 40

Sell

---

# Trading Candidate Rules

A trading candidate should satisfy most of the following:

- Strong technical setup
- Positive momentum
- Increasing volume
- Acceptable valuation
- Positive news flow
- Defined risk

---

# ETF Rules

ETF decisions prioritize:

Trend

Allocation

Diversification

Risk

Short-term news has lower influence.

---

# Portfolio Rules

Core ETFs

Never sold because of short-term volatility.

Growth stocks

Can be accumulated during corrections.

Trading positions

Can be closed after target profit or if technical conditions deteriorate.

---

# Risk Rules

High volatility reduces score.

Large drawdowns require confirmation.

Negative earnings reduce score.

Missing data reduces confidence.

---

# Confidence Score

Every recommendation includes confidence.

Range

0 - 100

Confidence depends on:

Data freshness

Number of available indicators

Agreement between signals

Missing information

---

# Output

Decision Engine returns:

Investment Score

Technical Score

Fundamental Score

News Score

Trend Score

Confidence Score

Recommendation

Reason Summary

---

# No Recommendation Rule

If confidence is too low:

Recommendation:

INSUFFICIENT DATA

No investment recommendation is generated.

---

# Future Expansion

Version 2

Sector Rotation

Economic Cycle

Correlation Analysis

Version 3

Machine Learning Ranking

Factor Models

Portfolio Optimization

Version 4

AI Assisted Decision Engine

---

# Principle

Investment recommendations must always be explainable.

Every score must be traceable back to the indicators that produced it.