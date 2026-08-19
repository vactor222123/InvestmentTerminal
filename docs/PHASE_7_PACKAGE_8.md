# Phase 7 Package 8 — Bounded XNAS Session Evidence

Baseline: `develop @ d71936b960d749bb0017d75e0c4a02cc45962df4`.

The generator emits exactly the audited MSFT window, 2025-08-19 through
2026-08-18, using Nasdaq-published regular hours, closures, and early closes.
It emits 251 explicit sessions with XNAS identity, source URI, retrieval time,
and a canonical session checksum. Its hard-coded bounds prevent unsupported
calendar claims. This is a bounded normalization of the cited Nasdaq schedule,
not a general calendar provider.
