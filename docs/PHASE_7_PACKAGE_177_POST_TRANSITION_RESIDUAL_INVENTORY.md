# Phase 7 Package 177 — Post-Transition Residual Inventory

## Classification

`IMPLEMENTATION`

## Verified Baseline

```text
develop @ ec9807343a3c4e0092f91ddf89c9b026357a0bdb
```

## Result

Package 177 implements the separate read-only boundary selected by Package
176. `ManifestPostTransitionResidualInventoryService` verifies the complete
manifest checkpoint set against both immutable source documents before it
reports current aggregate coverage, residual retryable causal signatures, and
final-failure signatures.

The service does not weaken or reuse the original sweep-bound inventory
contract. It verifies the source inventory bytes and completed transition
report bytes against caller-supplied SHA-256 values, validates their manifest,
inventory, provider, policy, status, budget, and coverage bindings, and then
reconciles every current checkpoint outcome with the immutable pre-transition
inventory.

## Contract

The new schema-version-1 report identity is:

```text
MANIFEST_POST_TRANSITION_RESIDUAL_INVENTORY
```

Successful reports bind:

- the manifest checksum;
- the immutable source-inventory checksum;
- the completed transition-report checksum;
- `COMPLETED_SWEEP_STORED_YAHOO_NO_PRICE_DATA_V1`;
- aggregate checkpoint coverage;
- deterministic residual retryable signatures containing only category,
  allowlisted exception-type chain, `DEFERABLE`, and count;
- deterministic final signatures containing only category, policy, and count.

The report excludes private symbols, currencies, prices, paths, provider text,
exception messages, request payloads, candle values, and per-series evidence.
CLI failures produce a schema-valid redacted `FAILED` report.

## Ownership and Side Effects

- operations owns strict source validation and deterministic aggregation;
- CLI owns local file reads, atomic JSON output, and redacted failure mapping;
- the manifest, checkpoints, inventory, and transition report are read-only;
- Yahoo, candle persistence, SQLite, retries, and checkpoint writes are absent.

## Verification

Focused tests cover successful reconciliation, both source checksum failures,
invalid transition bindings and arithmetic, incomplete or drifted checkpoints,
resurrected no-price state, residual-signature drift, negative duration,
privacy exclusions, redacted CLI failure output, and checkpoint immutability.
The full suite and repository diff check are required before delivery.

## Operational State

No private runtime command is executed by this implementation package. The
measured post-transition counts remain evidence from Package 176 until the new
CLI is run against the exact private manifest, all checkpoints, the immutable
source inventory, and the completed transition report.

## Next Package

Prepare one exact-baseline, ASCII-only PowerShell handoff for a single read-only
execution of the new CLI. It must verify all private source paths and SHA-256
bindings before invocation and return only the redacted report. Yahoo, SQLite,
retries, terminalization, and checkpoint mutation remain excluded.
