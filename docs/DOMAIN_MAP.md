# Investment Terminal — Domain Map

**Status:** Canonical Architecture Map  
**Updated after:** Sprint 13 — Historical Comparison and Replay

## 1. High-Level Map

```text
Market Data
→ Technical / Fundamental Analysis
→ Ranking / Recommendation
→ Portfolio / Decision
→ Review
→ History
→ Historical Intelligence
→ Future Knowledge
→ AI Interpretation
→ Human Decision
```

Supporting boundaries:

```text
Configuration · Infrastructure · CLI · Serialization · Persistence · Logging
```

## 2. Domain Maturity

| Domain | Status |
|---|---|
| Market Data | Established |
| Technical Analysis | Established |
| Fundamental Analysis | Established |
| Ranking | Established |
| Recommendation | Established |
| Portfolio | Established |
| Decision | Developing |
| Review | Established |
| History | Established foundation |
| Historical Intelligence | Implemented foundation |
| Knowledge | Planned |
| AI Interpretation | External integration layer |

## 3. Review Domain

Owns the versioned Review Package and assembly of independently produced domain outputs.

Does not own analytical calculations or historical storage.

## 4. History Domain

Purpose: preserve completed Review Packages as immutable, verifiable, indexed, and queryable historical evidence.

Owns:

- snapshot identity;
- immutable exact-byte archive;
- checksum and path safety;
- manifest;
- SQLite schema and migrations;
- import-state persistence;
- structured historical import;
- timeline generation;
- History persistence repositories.

Produces:

- archived JSON;
- manifest metadata;
- normalized SQLite history;
- import state;
- typed timeline records.

Does not own:

- current market-data acquisition;
- technical/fundamental calculations;
- recommendation generation;
- cross-snapshot comparison policy;
- AI interpretation.

## 5. Historical Intelligence Domain

**Status: Implemented foundation in Sprint 13.**

Purpose: analyze relationships across verified snapshots and expose safe historical replay.

Owns:

- snapshot compatibility policy;
- portfolio-summary comparison;
- holdings comparison;
- recommendation comparison;
- deployment comparison;
- aggregate snapshot comparison;
- replay request/result semantics;
- replay orchestration.

Consumes:

- typed History repositories;
- immutable archive evidence through verified loader;
- snapshot/import-state metadata.

Produces:

- compatibility results;
- `SnapshotComparison`;
- exact replay result;
- normalized replay result.

Must not own:

- archive mutation;
- market API access;
- current recommendation generation;
- current-code historical recalculation without an explicit future contract;
- fuzzy identity matching.

## 6. Knowledge Domain

**Status: Planned.**

Will derive reusable traceable knowledge from historical evidence and Historical Intelligence outputs.

Knowledge never rewrites History.

## 7. Infrastructure Boundary

Owns technical mechanisms:

- filesystem;
- SQLite connections;
- JSON serialization;
- CLI parsing;
- logging;
- configuration.

Infrastructure does not own business meaning.

## 8. CLI Boundary

Current History CLIs:

```text
archive_review_package.py
import_history.py
query_history.py
compare_history.py
replay_history.py
```

CLI only parses, constructs dependencies, invokes domain/application boundaries, formats, and exits.

CLI must not own SQL or domain rules.

## 9. Ownership Matrix

| Data / Capability | Owner |
|---|---|
| Review Package | Review |
| Historical snapshot | History |
| Archived JSON | History |
| Manifest | History |
| SQLite historical rows | History |
| Import state | History |
| Timeline event | History |
| Snapshot compatibility | Historical Intelligence |
| Snapshot comparison | Historical Intelligence |
| Replay semantics/result | Historical Intelligence |
| Knowledge entry | Future Knowledge |

## 10. Source-of-Truth Map

| Information | Source of Truth |
|---|---|
| Current portfolio | Portfolio Domain |
| Current Review Package | Review artifact |
| Historical Review Package | Immutable archived JSON |
| Snapshot metadata navigation | Manifest / synchronized repository |
| Queryable historical projection | SQLite History |
| Historical comparison | Historical Intelligence result |
| Exact replay | Verified archived package |
| Normalized replay | Typed SQLite projection |
| Future knowledge | Versioned Knowledge output |

## 11. Forbidden Dependencies

```text
History → Market API
History → analysis calculations
Historical Intelligence → archive mutation
Historical Intelligence → raw SQL
Replay → external data
CLI → domain-rule implementation
AI → canonical historical rewrite
Knowledge → History mutation
```
