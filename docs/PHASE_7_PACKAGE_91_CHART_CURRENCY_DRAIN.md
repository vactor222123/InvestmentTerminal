# Phase 7 Package 91 — Bounded Chart-Currency Drain

Classification: `IMPLEMENTATION`. Fresh `develop` baseline:
`eaeee75ad527bea80bc992bef26ea5b60acc1ff7`.

`SymbolCurrencyDrainService` coordinates the unchanged schema-version-2
currency qualification service in deterministic slices of at most 100. A
caller-supplied total-item budget is required and capped at 20,000. Every
successfully written private checkpoint is carried into the next slice.

The coordinator stops on completion, immediate rate-limit halt, budget
exhaustion, or zero progress. A completed exact resume performs no provider
work. Its separate schema-version-1 report contains aggregate starting/ending
coverage, slice/attempt/provider-request totals, checksums, budget, timing, and
halt/failure evidence without symbols, currencies, paths, provider text, or
exception messages.

The CLI atomically writes the existing private checkpoint through the slice
service and separately writes the aggregate report for success, halt, budget
exhaustion, or handled failure. No concurrency, sleeping, scheduling, batch
generation, candle retrieval, ingestion, analysis, or trading is introduced.

Next: run the CLI once against the existing private projection/checkpoint with
`--max-total-items 12000`, then return only its redacted aggregate report.
