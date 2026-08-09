# Investment Terminal вЂ” Product Roadmap

**Status:** Canonical Roadmap
**Updated after:** Sprint 19 вЂ” Knowledge Domain Foundation
**Current development branch:** `develop`

## 1. Product Evolution

```text
Foundation
в†’ Current-State Analysis
в†’ Portfolio and Decision Intelligence
в†’ Unified Review Package
в†’ Historical Intelligence Foundation
в†’ Historical Comparison and Replay
в†’ Outcome-Aware Historical Intelligence
в†’ Historical Outcome Methodology Hardening
в†’ Statistically Honest Outcome Research Foundation
в†’ Research Provenance and Population Quality Hardening
в†’ Explicit Historical Archive Continuity
в†’ Knowledge Domain Foundation
в†’ Evidence-Grounded AI Experience
```

## 2. Completed Milestones

### Sprint 11 вЂ” Foundation

Architecture and canonical product documentation foundation.

### Sprint 12 вЂ” Historical Intelligence Foundation

Immutable Review Package history, integrity verification, History SQLite, typed imports, and timeline foundation.

### Sprint 13 вЂ” Historical Comparison and Replay

Historical navigation, comparison, compatibility, replay, read-only CLIs, migrations/import state, and realistic E2E coverage.

### Sprint 14 вЂ” Outcome-Aware Historical Intelligence

Canonical outcome observations, exact local price evidence, raw price movement, descriptive aggregation, CLI, and E2E.

### Sprint 15 вЂ” Historical Outcome Methodology Hardening

Explicit methodology identities, deterministic session semantics, exact-only evidence, methodology-aware observations, and CLI/E2E.

### Sprint 16 вЂ” Statistically Honest Outcome Research Foundation

`DESCRIPTIVE_OUTCOME_RESEARCH@1`, exact cohorts, eligibility/coverage, sample sufficiency, descriptive statistics, uncertainty, and claim boundaries.

### Sprint 17 вЂ” Research Provenance and Population Quality Hardening

Population frame, selection accounting, boundary completeness, source import quality, canonical research provenance, compatibility migration, and E2E.

### Sprint 18 вЂ” Explicit Historical Archive Continuity

`FIXED_INTERVAL_ARCHIVE_CADENCE@1`, expected timestamp generation, exact archive-gap assessment, repository composition, internal continuity, optional archive-gap provenance, CLI, and E2E.

### Sprint 19 вЂ” Knowledge Domain Foundation

Delivered:

- immutable versioned `KnowledgeRecord`;
- traceable `KnowledgeEvidenceReference`;
- checksum-aware evidence provenance;
- persistence-agnostic repository contract;
- separate Knowledge SQLite schema v1;
- deterministic snapshot-evidence projection through a neutral Knowledge-side source contract;
- canonical record + provenance envelope;
- deterministic query service;
- descriptive temporal comparison;
- read-only Knowledge CLI;
- real SQLite в†’ query в†’ provenance в†’ comparison в†’ CLI E2E.

Canonical Knowledge flow:

```text
verified evidence
в†’ application/CLI composition
в†’ neutral Knowledge source
в†’ deterministic projection
в†’ KnowledgeRecord
в†’ Knowledge SQLite
в†’ KnowledgeQueryService
в†’ KnowledgeRecordEnvelope
в†’ temporal comparison / read-only CLI
```

Knowledge never imports or mutates History directly.

## 3. Canonical Evidence Hierarchy

```text
Archived Review Package JSON
    canonical historical source evidence

History SQLite
    rebuildable normalized historical projection

Historical outcome/research layers
    rebuildable descriptive historical intelligence

KnowledgeRecord
    versioned, rebuildable, traceable knowledge statement

KnowledgeProvenanceAssessment
    rebuildable lineage-quality view

Knowledge SQLite
    Knowledge-owned query persistence, separate from History
```

## 4. Stable Knowledge Guardrails

Knowledge v1 is descriptive and traceable. It does not establish:

```text
prediction
recommendation effectiveness
success probability
causal validity
market representativeness
AI authority
```

A provenance status of `COMPLETE` describes lineage to checksum-backed canonical snapshot evidence; it is not a confidence or truth score.

Temporal comparison reports factual field/evidence changes only and does not classify better/worse outcomes.

## 5. Persistence Status

```text
History schema target = 2
Knowledge schema target = 1
Knowledge provenance = derived/on demand
Knowledge comparison = derived/on demand
```

History and Knowledge databases remain separate ownership boundaries.

## 6. Deferred Scope

Still deferred:

- automatic History-to-Knowledge ingestion;
- comparison/replay/research projection into Knowledge;
- semantic deduplication and conflict resolution;
- relationship graph traversal;
- Knowledge migrations beyond schema v1;
- embeddings/vector retrieval;
- LLM-generated knowledge;
- evidence-grounded AI synthesis;
- predictive confidence or effectiveness scoring;
- causal inference;
- autonomous portfolio actions;
- broker execution.

## 7. Next Product Decision Point

Sprint 19 completes the deterministic Knowledge Domain foundation.

The next milestone can begin **Evidence-Grounded AI Experience** only if AI remains downstream of immutable evidence, historical intelligence, and traceable Knowledge provenance.

The AI layer must not bypass provenance, invent source authority, or reintroduce prohibited predictive/effectiveness claims without a new explicit methodology and governance contract.

## 8. Definition of Done

A milestone is complete only when:

- focused tests pass;
- full regression suite passes;
- architecture boundaries remain clean;
- documentation reflects implementation;
- deferred scope is explicit;
- repository is committed and pushed.
