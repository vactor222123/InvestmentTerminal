# Phase 7 Package 6 — Explicit Calendar Coverage Command

Baseline: `develop @ baca2c58125e842142b332b4884859298a68714f`.

The new `investment_terminal.cli.candle_coverage_quality` command connects an
explicit local session-calendar JSON document, the existing candle repository,
and Package 5 coverage evaluation. It atomically writes the measured report.

Nasdaq's official calendar and trading-hours pages are the selected authority
for XNAS evidence. No third-party calendar library is treated as authoritative,
and no weekday or holiday inference is added. The next action is to preserve an
explicit XNAS session document with source/version provenance and run the CLI.
