# Phase 7 Package 98 — Manifest-Bound Market Batch

Classification: `IMPLEMENTATION`. Fresh `develop` baseline:
`df1245454d7267eb75f017013b5d08810646c6fc`.

Package 98 implements the one-batch boundary selected by Package 97. A pure
selection contract validates the private schema-version-1 manifest identity,
caller-supplied canonical manifest checksum, upstream evidence checksums,
ordered contiguous batch indices, selected index, embedded request schema, and
embedded request checksum before persistence or provider composition.

The execution service accepts only a validated immutable selection and delegates
the selected request to the existing resumable batch service. Existing private
schema-version-1 checkpoint semantics, per-item persistence, exact resume,
failure isolation, and schema-version-2 execution accounting remain unchanged.

The new CLI executes exactly one caller-selected batch and writes a separate
schema-version-1 redacted envelope. It includes manifest checksum, batch index,
batch count, request checksum, timing, aggregate transfer coverage, and failure
types. It excludes symbols, currencies, paths, prices, provider text, and
exception messages. Handled validation, database, checkpoint, provider, and
reportable execution failures exit non-zero after report construction.

The implementation adds no loop across manifest batches, scheduler, retry cap,
typed rate-limit coordinator, indicator calculation, analysis, or trading
authority. The next step is one controlled execution of batch index 1 using its
own private checkpoint and the established market database. Only the redacted
report may be returned. A successful run authorizes only an exact resume of the
same batch, not batch 2.
