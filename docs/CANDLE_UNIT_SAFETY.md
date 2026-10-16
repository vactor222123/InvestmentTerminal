# Candle unit safety: bounded rejection, no conversion

Classification: IMPLEMENTATION. Fresh clean develop baseline:
`95b5265b95fa7ced963d5723814fb196325db5ad`.
The user authorized selecting the appropriate compatibility strategy.

## Decision and audit

The old chart adapter uppercased the source label, qualification persisted only
that string, terminal-success resume skipped metadata, and manifests embedded
the resulting currency in checksum-bound requests. A new field cannot recover
an old source spelling. A checkpoint schema bump alone would falsely certify
old evidence or force a broad requalification without an observed need.

Select the smaller safe rejection boundary already permitted by the A03 audit.
Do not introduce a conversion/provenance schema in this package. Preserve old
JSON schemas, request serialization, checksums and source files. Tighten accepted
inputs deliberately; compatibility means preserving evidence, not continuing
unsafe execution. No migration, source call, runtime inspection or rescaling ran.

## Implemented boundaries

`market.candle_currency` owns two pure functions and typed ValueError subclasses:

- `normalize_candle_currency`: strip outer whitespace; require three ASCII
  letters; reject mixed case before uppercasing. Ordinary all-lowercase codes
  remain compatible. `GBp`, `ZAc`, `USc`, mixed-case ordinary spellings and Unicode
  lookalikes cannot silently become different labels. No arithmetic occurs.
- `require_yahoo_candle_currency`: apply that validation and reject normalized
  `GBP` on the current string-only Yahoo path. This includes genuinely major-unit
  GBP: the conservative restriction is intentional, not a claim it is corrupt.

Chart metadata, Yahoo strict/projected candle entry points, qualification results
(including injected clients), market-batch requests and manifest construction use
the Yahoo gate. Both checkpoint schemas 1 and 2 validate SUCCESS currency before
migration writes or terminal bypass. Complete drain shares this checkpoint loader.
Existing manifests pass through request validation, so a stored GBP request stops
before weekly source-checkpoint reads. Direct typed batch/weekly execution also
checks every input before provider/repository calls, checkpoint writes or skip.
There is no automatic exclusion, retry, checkpoint reopening or hash rewriting.

Repository save/save_many use the generic label validator before any write.
One bad label in a batch leaves all prior rows unchanged and inserts nothing.
Explicit canonical GBP remains representable by the provider-neutral repository;
this is not Yahoo source certification. Existing reads and direct SQL retain
their previous scope; they do not retroactively validate historical price units.

## Compatibility and limits

Ordinary USD/EUR request serialization and hashes, completed checkpoint no-op,
OHLCV values, repository atomicity and all existing report schemas are retained.
New validation failures use the existing ValueError/INVALID_RESPONSE handling;
this package adds no report failure-category vocabulary. Existing operational
retry bounds remain unchanged. Incompatible old successful evidence fails before
provider access instead of being silently reclassified or rewritten.

This fixes the reproduced GBp-to-GBP relabeling and adds a generic mixed-case
guard. It is NOT a complete ISO currency registry, a complete provider-unit alias
catalog, response/request currency matching, historical unit-change detection,
price-basis proof, or certification of old candles. Unknown all-uppercase aliases
and labels already normalized by unrelated adapters are not universally resolved.
Corporate-action snapshots keep their case-preserved quote labels and are not
changed; portfolio settlement currency and amounts are also unchanged.

If a supported workflow stops on the GBP compatibility gate, preserve all inputs.
Do not change GBP to another currency, divide prices, delete/recreate checkpoints,
or rerun all history. Restoring that unit family requires a separately versioned,
source-observed unit contract and an explicit historical compatibility decision.
An unaffected universe needs no wholesale re-download or metadata migration.

## Verification and next boundary

Synthetic tests cover raw metadata, malformed/case-sensitive labels, provider
bypass, strict empty frames, atomic repository failure, both legacy checkpoint
versions, complete drain, old manifest gating, direct typed execution, unchanged
source objects, ordinary exact resume, checksum parity and unchanged OHLCV.
The two A03 expected-failure probes are now ordinary regression tests. Their
passing status does not close historical-unit qualification or all audit findings.

Focused: 329 passed, 6.91 s, including architecture/dependency guards. Full:
3928 passed, 4 skipped, 43.91 s, one existing Starlette deprecation warning.
No xfails remain from the A02/A03 probes. There are 51 new synthetic cases.
`git diff --check` is clean. No network or private runtime qualification ran.

Next development priority is A06: audit and implement the smallest consistent
market-runtime backup/restore boundary, reusing existing backup facilities before
any historical repair. Unit-bearing source support remains explicitly deferred;
do not enable collection or a scheduler merely because these local tests pass.
