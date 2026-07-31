# Investment Terminal

# Software Architecture

Version: 1.0.0

Status:
Architecture Approved

---

# Vision

Investment Terminal is a professional investment analysis platform designed to support long-term investing and position trading using verified market data, technical analysis, fundamental analysis and automated decision support.

The system is designed to be modular, scalable and production-ready.

---

# Core Principles

1. Data Quality First
2. Automation Before Manual Work
3. Single Source of Truth
4. Modular Architecture
5. Test Before Release
6. No Investment Decisions Based On Incomplete Data

---

# High Level Architecture

```
                    Finnhub API
                         │
                    Yahoo Finance
                         │
                         ▼
                Data Collection Layer
                         │
                         ▼
                 SQLite Database
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
 Technical        Fundamental        News Engine
 Indicators         Analysis
        │                │                │
        └────────────────┼────────────────┘
                         ▼
                 Decision Engine
                         │
          ┌──────────────┴──────────────┐
          ▼                             ▼
    Excel Reports               ChatGPT Analysis
```

---

# Project Structure

```
InvestmentTerminal/

investment_terminal/

    config/
    api/
    database/
    indicators/
    market/
    portfolio/
    watchlist/
    reports/
    utils/

data/

output/

logs/

tests/

README.md
Architecture.md
requirements.txt
Run.bat
```

---

# System Layers

## Layer 1

Configuration

Responsible for:

- Environment variables
- Global constants
- Project settings

---

## Layer 2

API Layer

Responsible for:

- Finnhub
- Yahoo Finance
- Future APIs

Responsibilities

- Download data
- Retry failed requests
- Validate responses
- Cache requests

---

## Layer 3

Database Layer

SQLite

Tables

- watchlist
- portfolio
- market_data
- indicators
- fundamentals
- news
- journal
- recommendations

Database is the single source of truth.

Excel is never used as a database.

---

## Layer 4

Technical Analysis

Indicators

- RSI
- SMA20
- SMA50
- SMA100
- SMA200
- EMA20
- EMA50
- EMA200
- MACD
- Signal
- Histogram
- ATR
- Average Volume

Future

- ADX
- Bollinger Bands
- Ichimoku
- VWAP

---

## Layer 5

Fundamental Analysis

Metrics

- Market Cap

- Revenue

- EPS

- P/E

- PEG

- ROE

- Debt

- Free Cash Flow

- Dividend Yield

---

## Layer 6

Market Analysis

Future modules

- News Analysis

- Insider Trading

- Earnings Calendar

- Fear & Greed

- VIX

- US10Y

- Dollar Index

---

## Layer 7

Decision Engine

This is the heart of the system.

Every asset receives:

Technical Score

Fundamental Score

Trend Score

News Score

Risk Score

Final Score

Investment Score

Range

0 - 100

Example

95

Strong Buy

82

Buy

70

Watch

55

Neutral

40

Reduce

25

Sell

---

# WatchList

Each asset contains

Ticker

Company

Sector

Industry

Category

Priority

Holding

Target Allocation

Current Allocation

Investment Score

Status

---

# Categories

Core ETF

Satellite ETF

Core Stock

Growth Stock

Dividend Stock

Trading Candidate

Watch Only

---

# Portfolio

Tracks

Current Holdings

Cash

Profit

Allocation

Performance

Rebalancing

---

# Reports

Generated automatically

Investment_Database.xlsx

Future

Monthly Report

Portfolio Report

Risk Report

Trading Journal

---

# Logging

Every operation is logged.

No silent failures are allowed.

---

# Error Handling

If one module fails

↓

System continues where possible

↓

Critical failures stop report generation

---

# Testing

Every module requires

Unit Tests

Integration Tests

Manual Verification

---

# Version Roadmap

Version 1

Foundation

SQLite

Finnhub

Excel

Technical Indicators

Version 2

Decision Engine

Investment Score

Portfolio Score

Version 3

AI Assistant

Automatic Reports

Risk Analysis

Version 4

Web Dashboard

Interactive Charts

Notifications

---

# Development Workflow

Design

↓

Implementation

↓

Testing

↓

Review

↓

Release

No feature is released without successful testing.

---

# Mission

Build a reliable investment platform that combines automation, transparent data and disciplined decision making to support high-quality investment research.