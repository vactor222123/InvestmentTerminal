# Investment Terminal — Next Steps

**Current repository baseline:** `develop @ 68690fc`
**Sprint 32:** CLOSED
**Post-Sprint-32 audit:** COMPLETE
**Approved next Sprint:** Sprint 33 — Integrated Current-State Market Intelligence

## Platform Contract

```text
Local development / host regression:
Windows + PowerShell + Python 3.13

Production container execution verification:
GitHub Actions ubuntu-latest + Docker
```

## Sprint 33 plan

```text
33.1 Canonical Live Analysis Contract
33.2 Direct Stock Analysis → Review Package Composition
33.3 Current-State Analysis Orchestrator / CLI
33.4 Freshness & Failure Surface Reconciliation
33.5 Review Package → History Handoff
33.6 Real Current-State Workflow E2E
33.7 Documentation / CLI Usability Reconciliation
33.8 Sprint 33 Closure
```

### 33.1 Canonical Live Analysis Contract

Audit and formalize the existing `portfolio_ranking` pipeline as the single
current-state equity-analysis authority. Do not duplicate ranking/scoring logic.

### 33.2 Direct Stock Analysis → Review Package Composition

Remove the requirement for a manual intermediate stock-analysis JSON file.
Preserve explicit file import as backward-compatible/offline mode if justified.

### 33.3 Current-State Analysis Orchestrator / CLI

One canonical command:

```text
refresh
→ analyze universe
→ rank/recommend
→ build Review Package
```

### 33.4 Freshness & Failure Surface Reconciliation

Make stale data, provider failures, and incomplete fundamental coverage explicit.

### 33.5 Review Package → History Handoff

Connect output to the established immutable History path while preserving
explicit operator intent.

### 33.6 Real Current-State Workflow E2E

CI remains hermetic; optional local live verification may run on Windows.

### 33.7 Documentation / CLI Usability Reconciliation

Update stale capability/phase documentation.

### 33.8 Sprint 33 Closure

Require local Windows regression and GitHub CI green.
