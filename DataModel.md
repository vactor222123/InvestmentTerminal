# Investment Terminal

# Data Model

Version: 1.0.0

Status:
Approved

---

# Purpose

This document defines the complete database structure for Investment Terminal.

SQLite is the single source of truth.

No business data is stored in Excel.

---

# Database

investment_terminal.db

---

# Table

watchlist

Purpose

Master list of all assets monitored by the system.

Columns

id

ticker

name

asset_type

category

sector

industry

currency

exchange

country

priority

enabled

created_at

updated_at

---

# Table

portfolio

Purpose

Current portfolio holdings.

Columns

id

ticker

quantity

average_price

current_price

market_value

profit_loss

profit_loss_percent

target_allocation

current_allocation

opened_date

updated_at

---

# Table

market_data

Purpose

Latest market prices.

Columns

id

ticker

timestamp

open

high

low

close

volume

market_cap

currency

source

---

# Table

technical_indicators

Purpose

Calculated technical indicators.

Columns

id

ticker

timestamp

rsi

sma20

sma50

sma100

sma200

ema20

ema50

ema200

macd

macd_signal

macd_histogram

atr

average_volume

trend

---

# Table

fundamentals

Purpose

Fundamental company data.

Columns

id

ticker

timestamp

revenue

eps

pe

peg

roe

debt

cash_flow

dividend_yield

profit_margin

shares_outstanding

---

# Table

news

Purpose

News related to assets.

Columns

id

ticker

published_at

headline

source

url

sentiment

importance

processed

---

# Table

recommendations

Purpose

Decision Engine output.

Columns

id

ticker

timestamp

technical_score

fundamental_score

trend_score

news_score

risk_score

confidence_score

investment_score

recommendation

reason

---

# Table

journal

Purpose

Trading journal.

Columns

id

date

ticker

action

quantity

price

reason

result

notes

---

# Relationships

watchlist
        │
        ├────────────┐
        ▼            ▼
market_data     portfolio
        │            │
        ▼            ▼
technical    fundamentals
        │            │
        └──────┬─────┘
               ▼
      recommendations
               │
               ▼
           journal

---

# Data Flow

Finnhub API

↓

market_data

↓

technical_indicators

↓

fundamentals

↓

news

↓

recommendations

↓

reports

---

# Data Retention

Market Data

Daily updates

Indicators

Recalculated every update

Fundamentals

Updated after earnings

News

Stored permanently

Recommendations

Stored permanently

Journal

Never deleted

---

# Design Principles

Single Source of Truth

Normalized data

No duplicated calculations

Every recommendation reproducible

Historical data preserved

---

# Future Tables

earnings

dividends

economic_calendar

sector_performance

macro_data

broker_transactions

alerts