
# Investment Terminal

> **A deterministic investment intelligence platform that collects, validates,
structures and preserves financial evidence to support long-term investment
decisions.**

---

## Vision

Investment Terminal is not a trading bot and does not attempt to predict the
future.

Its purpose is to reduce uncertainty by combining high-quality data,
deterministic analysis, historical evidence and AI-assisted interpretation.

---

## Core Principles

- Deterministic calculations
- Explainable recommendations
- Portfolio-aware analysis
- Historical intelligence
- Immutable evidence
- Human remains the final decision maker

---

## Current Capabilities

### Portfolio

- Portfolio holdings
- Allocation policy
- Market value
- Policy gap analysis
- Contribution planning

### Analysis

- Technical indicators
- Fundamental analysis
- ETF analysis
- Recommendation engine

### Review Package

Produces a structured `investment_review_package.json` containing:

- portfolio state
- recommendations
- deployment decision
- ETF analysis
- market metadata
- diagnostics

This package is the canonical interface between the Python engine and AI.

---

## Architecture

The platform is organized into domains.

```
Market
 ├── Technical
 ├── Fundamental
 ├── Recommendation
 ├── Portfolio
 ├── Review
 ├── History (planned)
 ├── Knowledge (planned)
 └── Decision (planned)
```

---

## Repository

```
docs/
investment_terminal/
tests/
data/
```

Important documentation:

- PROJECT_VISION.md
- CONSTITUTION.md
- ARCHITECTURE.md
- DATA_MODEL.md
- INVESTMENT_PHILOSOPHY.md
- DESIGN_PRINCIPLES.md
- DEVELOPMENT_GUIDELINES.md
- QUALITY_ATTRIBUTES.md
- ROADMAP.md

---

## Development

Typical workflow:

```bash
python -m pytest
```

Generate a review package:

```bash
python -m investment_terminal.cli.investment_review_package
```

---

## Engineering Standards

Every change should include:

- tests
- documentation updates
- deterministic behaviour
- backward compatibility review

Large architectural changes should be introduced through RFCs and documented
using ADRs.

---

## Long-Term Roadmap

Milestone 1
- Analysis Engine ✅

Milestone 2
- Portfolio Intelligence ✅

Milestone 3
- Review Package ✅

Milestone 4
- Documentation Foundation 🚧

Milestone 5
- Historical Intelligence

Milestone 6
- Knowledge Engine

Milestone 7
- AI Decision Intelligence

Milestone 8
- Personal Investment Operating System

---

## Philosophy

Investment Terminal becomes more valuable after every completed review because
it accumulates structured historical evidence rather than attempting to predict
markets.

---

## License

Project-specific. See repository license when published.
