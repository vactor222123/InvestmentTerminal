# Investment Terminal

> Professional Investment Analysis System

Version: 1.0.0

Author:
- Viktor
- OpenAI

---

# Overview

Investment Terminal is a professional portfolio analysis and market research application designed for long-term investing and position trading.

The system automatically downloads market data, calculates technical indicators, analyzes portfolio allocation and generates professional investment reports.

The main goal is to make investment decisions using verified and up-to-date market data instead of assumptions.

---

# Main Features

## Market Data

- Finnhub API integration
- Historical price data
- Real-time quotes
- Automatic updates

---

## Technical Analysis

(Current Version)

- RSI (14)
- SMA20
- SMA50
- SMA100
- SMA200
- EMA20
- EMA50
- EMA200
- MACD
- Signal Line
- MACD Histogram
- ATR
- Average Volume
- 52 Week High
- 52 Week Low

Future Versions

- Bollinger Bands
- ADX
- VWAP
- Stochastic RSI
- Ichimoku Cloud

---

## Portfolio Analysis

- Current Allocation
- Target Allocation
- Profit / Loss
- Portfolio Performance
- ETF Allocation
- Stock Allocation

---

## Market Analysis

Future Versions

- Fear & Greed Index
- VIX
- US10Y Yield
- Gold
- Oil
- Bitcoin
- Dollar Index

---

## Fundamental Analysis

Future Versions

- P/E
- PEG
- EPS
- ROE
- Revenue Growth
- Debt
- Free Cash Flow
- Dividend Yield
- Market Cap

---

## Reports

The application generates:

- Investment_Database.xlsx

Future versions:

- Monthly Report
- Portfolio Report
- Market Report
- Risk Report

---

# Project Structure

InvestmentTerminal/

```
config/
data/
logs/
output/
src/
tests/

README.md
requirements.txt
Run.bat
```

---

# Data Sources

Primary

- Finnhub API

Backup

- Yahoo Finance

Future

- Financial Modeling Prep
- Alpha Vantage

---

# Project Philosophy

Investment Terminal follows one simple principle:

**Data Quality First**

The application should never generate investment recommendations using outdated or incomplete market data.

Every value should be traceable to its source.

---

# Development Rules

The project follows:

- PEP8
- SOLID Principles
- Type Hints
- Docstrings
- Modular Architecture
- Exception Handling
- Logging
- Unit Testing

---

# Version Roadmap

## Version 1.0

- Project Foundation
- Finnhub API
- Excel Export
- Technical Indicators

---

## Version 1.1

- News
- Earnings Calendar
- Analyst Ratings
- Insider Transactions

---

## Version 2.0

- Investment Score
- Opportunity Score
- Buy Score
- Sell Score
- Portfolio Score

---

## Version 3.0

Investment Dashboard

- Charts
- Portfolio Analytics
- AI Assistant
- One-click Market Update

---

# Data Quality

Before generating any report the application verifies:

- API connection
- Missing values
- Historical data completeness
- Indicator calculation
- Timestamp freshness

If validation fails, the report will not be generated.

---

# Logging

Every execution creates log files.

Example

logs/

```
2026-08-01.log
```

---

# License

Personal Use

Copyright © Viktor & OpenAI

---

# Disclaimer

This software is intended to assist investment research.

It does not provide financial advice.

All investment decisions remain the responsibility of the investor.

---

# Mission

Build one of the most reliable private investment analysis systems using transparent data, automation and disciplined decision making.