# Current-State Analysis Orchestrator

Sprint 33 Task 3 introduces the canonical composition entry point for the
current-state analysis workflow.

## Boundary

The orchestrator composes existing authorities:

```
existing portfolio analysis pipeline
        |
        v
CurrentStateEquityAnalysisResult
        |
        v
Review Package composition
```

## Ownership

The orchestrator does not own:

- market refresh;
- ranking;
- scoring;
- recommendations;
- theses;
- allocation;
- providers.

Those remain in the existing analysis pipeline.

## Non-goals

Task 33.3 does not add:

- news;
- macro data;
- ETF analysis;
- watchlist analysis;
- AI generation;
- History persistence.
