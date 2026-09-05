# Phase 7 Package 102 — Bounded Manifest Drain

Classification: `IMPLEMENTATION`. Fresh `develop` baseline:
`ea66dd6cebb90b22b70a5349747d8bd38af3cde4`.

Package 102 implements the bounded coordinator selected by Package 101. An
immutable drain plan validates the manifest and every embedded request checksum
once, enforces a caller-owned budget from 1 through 25 batches, and carries no
runtime path or provider dependency.

Before the first provider call, the service reads all deterministic private
`batch_####.json` checkpoints, validates each existing request binding, and
rejects progress after the first unfinished batch. Completion requires exact
request-symbol coverage with every outcome terminal `SUCCESS` or `EMPTY`.
SQLite contents are never used as a completion index.

The coordinator executes first-unfinished requests sequentially through the
existing manifest-bound service. It stops on manifest completion, budget
exhaustion, or the first `PARTIAL`/`FAILED` result. Each item remains atomically
checkpointed by the existing request service. The CLI shares one explicit
database and cache composition across the bounded run while preserving separate
per-request checkpoint files.

The schema-version-1 redacted report contains manifest checksum, explicit
budget, starting and ending batch coverage, current attempted batch/item and
transfer totals, stop index, and failure types. It excludes private symbols,
currencies, paths, prices, provider text, and exception messages.

The package does not add scheduling, typed intra-request rate-limit halt,
indicator calculation, analysis, trading, or complete-manifest authority. The
next operation is one controlled `max_batches=5` run. Because batch 1 is already
complete, only batches 2–6 may be attempted. Review the redacted report before
any larger budget.
