# ADR-0002 — History Is Immutable

**Status:** Accepted  
**Date:** 2026-08-02  
**Decision owner:** Investment Terminal Architecture  
**Scope:** History Domain, Review Domain, Knowledge Domain

---

# Context

Investment Terminal is designed to accumulate knowledge over many years.

Historical reviews are not cache files—they are evidence describing what the
system knew at a specific point in time.

Future capabilities such as:

- Historical Intelligence
- Snapshot Diff
- Recommendation Timeline
- Decision Trace
- Confidence Calibration
- Knowledge Engine

all depend on preserving history exactly as it originally existed.

If historical records can be edited, overwritten or silently corrected, the
product loses its ability to reproduce past analyses and evaluate how its
recommendations evolved.

---

# Problem

How should historical review data be stored so that it remains trustworthy,
reproducible and suitable for long-term analysis?

---

# Decision

Historical snapshots are **immutable**.

Once a snapshot has been archived it must never be modified in place.

Corrections are represented by creating a new snapshot rather than editing an
existing one.

The lifecycle is:

```text
Review Package
        ↓
Historical Snapshot
        ↓
Immutable Archive
```

---

# Decision Details

## Snapshot Identity

Every snapshot should eventually contain:

- unique identifier;
- generation timestamp;
- schema version;
- generator version;
- checksum;
- metadata.

## Corrections

If incorrect data is discovered:

```
Snapshot #105
        ↓
Correction identified
        ↓
Snapshot #106
(reason: corrected market data)
```

Snapshot #105 remains preserved.

## Archive Rules

The archive is append-only.

Allowed:

- create snapshot;
- index snapshot;
- verify checksum;
- import into structured history.

Forbidden:

- overwrite snapshot;
- delete snapshot without explicit administrative process;
- rewrite recommendations;
- silently replace evidence.

---

# Rationale

Immutable history provides:

- reproducibility;
- auditability;
- trustworthy timelines;
- historical comparison;
- AI replay;
- future knowledge extraction.

The system must always be able to answer:

> What evidence existed when this recommendation was produced?

---

# Alternatives Considered

## Mutable History

Rejected.

Editing historical records destroys reproducibility.

## Overwrite Existing JSON

Rejected.

Important evidence about previous states disappears.

## SQLite Only

Rejected.

SQLite is a structured representation, not the canonical archive.

---

# Positive Consequences

- historical evidence remains trustworthy;
- recommendation evolution becomes measurable;
- confidence can be calibrated over time;
- snapshot diff becomes reliable;
- knowledge derives from authentic history.

---

# Negative Consequences

- storage requirements increase;
- archive management becomes necessary;
- migrations require care;
- duplicate snapshots may exist after corrections.

These costs are accepted because preserving evidence has higher value than
saving storage.

---

# Compliance Rules

A change complies with this ADR if it:

- creates new snapshots instead of modifying existing ones;
- preserves timestamps;
- preserves historical identifiers;
- documents correction reasons.

A change violates this ADR if it:

- edits archived snapshots;
- silently replaces history;
- rewrites historical recommendations;
- changes archived evidence in place.

---

# Implementation Status

| Area | Status |
|---|---|
| Review Package | Implemented |
| Immutable archive | Implemented |
| Snapshot manifest | Implemented |
| Archive-root path safety | Implemented |
| Checksum verification | Implemented |
| Read-once verified byte path | Implemented |
| Structured historical import | Implemented |
| Atomic detail import | Implemented |
| Snapshot diff | Planned |
| Historical replay | Planned |

---

# Related Documents

- PROJECT_VISION.md
- ARCHITECTURE.md
- DATA_MODEL.md
- DOMAIN_MAP.md
- ADR-0001 Review Package Is the Only AI Interface

---

# Future Evolution

Future enhancements may include:

- snapshot signing;
- archive compaction metadata;
- retention policies;
- distributed archive support.

None of these features may compromise the immutability of archived snapshots.

---

# Guiding Statement

> History is evidence.

Evidence must be preserved exactly as it existed when the investment review was
created.
