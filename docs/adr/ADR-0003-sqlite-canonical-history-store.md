
# ADR-0003 — SQLite Is the Canonical Structured History Store

**Status:** Accepted  
**Date:** 2026-08-02  
**Decision owner:** Investment Terminal Architecture  
**Scope:** History Domain, Infrastructure Domain

---

# Context

Investment Terminal is designed to preserve every completed investment review.

The canonical archived artifact is the immutable
`investment_review_package.json`.

As historical reviews accumulate, the product must support:

- timeline queries;
- portfolio evolution;
- recommendation history;
- confidence trends;
- historical comparisons;
- knowledge extraction.

JSON files are excellent archival artifacts but are inefficient for structured
queries across thousands of reviews.

---

# Problem

How should historical information be stored so that it remains searchable,
efficient and independent from the immutable archive?

---

# Decision

SQLite is the canonical structured storage for historical data.

The immutable Review Package remains the canonical archival artifact.

The workflow is:

```text
investment_review_package.json
            ↓
     Immutable Archive
            ↓
     History Import
            ↓
          SQLite
            ↓
Timeline / Search / Analytics / Knowledge
```

SQLite is **not** the source of truth.

The archived Review Package remains authoritative.

SQLite is a normalized representation optimized for retrieval and analysis.

---

# Decision Details

## Responsibilities of SQLite

SQLite stores normalized historical information such as:

- snapshots;
- portfolio summaries;
- holdings;
- recommendations;
- deployment decisions;
- confidence metrics;
- timeline events;
- future knowledge links.

## Responsibilities of the Archive

The archive preserves:

- original Review Package;
- original timestamps;
- original evidence;
- original schema version;
- original package structure.

Whenever complete historical reconstruction is required, the archive is used.

---

# Domain Boundary

Only the History Domain owns SQLite.

Other business domains must not access SQLite directly.

Instead they communicate through History services or repositories.

Storage technology is an implementation detail.

---

# Rationale

SQLite was selected because it is:

- embedded;
- reliable;
- portable;
- zero-configuration;
- deterministic;
- widely supported.

It provides excellent performance for local analytical workloads without
introducing operational complexity.

---

# Alternatives Considered

## JSON Only

Rejected.

Searching and aggregating large historical datasets becomes inefficient.

## PostgreSQL

Rejected.

Operational complexity outweighs the current product requirements.

## DuckDB

Interesting for analytical workloads but not required at the current stage of
the project.

May be reconsidered in the future.

---

# Positive Consequences

- fast historical search;
- efficient timelines;
- structured analytics;
- foundation for Knowledge Engine;
- separation between archive and query layer.

---

# Negative Consequences

- schema migrations become necessary;
- import pipeline must be maintained;
- two historical representations must remain synchronized.

These costs are accepted because they significantly improve analytical
capabilities while preserving immutable evidence.

---

# Compliance Rules

A change complies with this ADR when:

- Review Packages remain the canonical archive;
- SQLite is populated from archived reviews;
- History Domain owns persistence;
- storage implementation remains hidden behind domain interfaces.

A change violates this ADR when:

- SQLite becomes the source of truth;
- business domains depend directly on database tables;
- historical archive is reconstructed solely from SQLite.

---

# Implementation Status

| Area | Status |
|---|---|
| Review Package archive | Planned |
| SQLite schema | Planned |
| Import pipeline | Planned |
| Timeline queries | Planned |
| Knowledge integration | Future |

---

# Related Documents

- PROJECT_VISION.md
- ARCHITECTURE.md
- DATA_MODEL.md
- DOMAIN_MAP.md
- ADR-0001 Review Package Is the Only AI Interface
- ADR-0002 History Is Immutable

---

# Future Evolution

Future enhancements may include:

- migration tooling;
- integrity verification;
- indexing improvements;
- optional cloud-backed implementations.

These changes must preserve the architectural rule that storage is an
implementation detail and the immutable Review Package remains the canonical
historical artifact.

---

# Guiding Statement

> Preserve history in immutable artifacts.  
> Query history through structured storage.  
> Never confuse storage optimization with the source of truth.
