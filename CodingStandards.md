# Investment Terminal

# Coding Standards

Version: 1.0.0

Status:
Approved

---

# Purpose

This document defines the coding standards for the Investment Terminal project.

The goal is to keep the codebase clean, consistent, testable and maintainable.

---

# General Principles

- Readability over cleverness.
- Simplicity over complexity.
- Explicit is better than implicit.
- Small modules with one responsibility.
- Every function should have a clear purpose.

---

# Python Version

Python 3.13+

---

# Formatting

- Follow PEP 8.
- Use 4 spaces for indentation.
- UTF-8 encoding.
- Maximum line length: 100 characters.

---

# Type Hints

All public functions must use type hints.

Example:

```python
def calculate_score(price: float, volume: int) -> float:
    ...
```

---

# Docstrings

Every public class and function must include a docstring.

Example:

```python
def load_watchlist() -> list:
    """
    Load all assets from watchlist.json.
    """
```

---

# Logging

Never use print() for application logging.

Use the project logger.

Allowed:

- INFO
- WARNING
- ERROR
- CRITICAL

---

# Error Handling

Never silently ignore exceptions.

Catch only expected exceptions.

Unexpected exceptions must be logged.

---

# Imports

Order:

1. Standard Library
2. Third-party Libraries
3. Project Modules

Example:

```python
import os
from pathlib import Path

import pandas as pd

from investment_terminal.config.settings import Settings
```

---

# Project Structure

One class per file where practical.

One responsibility per module.

Avoid circular imports.

---

# Configuration

Never hardcode:

- API keys
- File paths
- URLs
- Thresholds
- Indicator weights

Configuration belongs in:

- .env
- JSON
- settings.py

---

# Business Logic

Business rules must not be hardcoded.

Examples:

- Decision weights
- Portfolio allocation
- Buy/Sell thresholds

These belong in configuration files.

---

# Database

SQLite is the single source of truth.

Excel is only for reporting.

---

# JSON Files

Configuration files should be human-readable.

Use consistent formatting with 4-space indentation.

---

# Testing

Every new module should be tested before integration.

Unit tests first.

Integration tests second.

---

# Git

Commit messages should be descriptive.

Example:

Add Finnhub client

Implement RSI calculation

Fix portfolio allocation bug

---

# Performance

Avoid unnecessary API calls.

Cache reusable data when appropriate.

Optimize only after correctness.

---

# Security

Never commit:

- .env
- API keys
- Personal credentials

---

# Documentation

Every important module should be documented.

Major architectural changes require updates to:

- README.md
- Architecture.md

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

Integration

↓

Release

---

# Quality Goal

Every module should be:

- Understandable
- Testable
- Reusable
- Reliable
- Maintainable

---

# Final Principle

The code should be easy to understand six months later, even if written today.