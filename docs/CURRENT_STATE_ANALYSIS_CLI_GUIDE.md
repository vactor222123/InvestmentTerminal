# Current-State Analysis CLI Guide

Sprint 33 Task 7 reconciles documentation with the implemented workflow.

## Current architecture

```
market data
→ deterministic analysis
→ CurrentStateEquityAnalysisResult
→ Review Package
→ explicit History handoff
```

## Ownership

The existing portfolio analysis pipeline remains responsible for:

- market refresh;
- freshness validation;
- technical analysis;
- fundamental analysis;
- ranking;
- recommendations;
- theses;
- allocation.

The Review Package layer only consumes deterministic analysis output.

## Explicit boundaries

```
Review Package != History
History != Knowledge
Analysis != AI
```

## Deferred capabilities

Not part of Sprint 33:

- news ingestion;
- macro intelligence;
- ETF intelligence;
- automatic Knowledge ingestion;
- autonomous actions.
