# Phase 7 — weekly stale-success/gap result audit

Classification: `AUDIT`. A direct fresh GitHub clone of clean `develop`
matched the caller baseline `7e6655f1bdac67bab6f16d61c966452544a1e73a`.

The user-returned redacted report has SHA-256
`07258188a79dcece8adc141fe8c435c049f44ffe3183a09fb5f193875690aa52`.
It is `WEEKLY_STALE_GAP_DIAGNOSTIC` schema 1, `COMPLETE`, with no failure.
Its manifest/selection checksums and half-open
`[2016-09-23T00:00:00Z, 2026-09-23T00:00:00Z)` window match the prior
handoff. The user separately reported `SQLite integrity: ok`. No private
manifest, checkpoint, database, identity, or price was inspected for this
package, and no runtime command was executed.

## Reconciled result

- Of 11,892 selected series, 31 weekly `SUCCESS` series lack the seven-day
  end proxy and 36 have an observed consecutive-candle gap over seven
  calendar days. Nineteen are in both groups, so the union is **48**
  (`31 + 36 - 19`). The 214 weekly failures measured earlier are separate;
  262 series therefore have either a failed weekly outcome or one of these
  two observed quality flags. The remaining 11,630 have neither flag under
  these specific checks; that is not a trading-session completeness claim.
- Disjoint groups reconcile to 12 stale-only, 17 gap-only, and 19 both.
  Staleness durations are 9 over 7–14 days, 21 over 14–30 days, and one
  over 30–90 days. Gap durations are 12 over 7–30 days and 24 over
  30–90 days. No series enters either over-90-day bin or the no-window-row
  bin.
- Those 48 weekly `SUCCESS` outcomes aggregate 325 downloaded candles,
  115 inserted, 210 duplicates, and zero omitted trailing candles. Each
  disjoint group reconciles downloaded to inserted plus duplicates. New
  inserts did not by themselves establish a fresh end candle or close an
  older interior gap.

`WeeklyCandleRefreshService` currently records `SUCCESS` for a nonempty,
validated provider response; it does not require a post-refresh endpoint
or interior-continuity result. The separate diagnostic correctly preserves
that transfer contract. Its seven-calendar-day proxy is not an official
exchange calendar, and the aggregate report cannot establish whether the
24 gaps over 30 days represent missing sessions, instrument lifecycle,
provider history, or another cause. It also cannot identify a particular
series for a targeted repair. Do not reinterpret all 48 as defective candles,
rewrite stored OHLCV, or silently change the private checkpoint status.

## Next boundary

Do not initiate a new broad scan or chase the 48 series one by one from
aggregate evidence. The smallest next package is a focused **AUDIT of the
repeatable weekly-run boundary**: inspect the existing CLI, manifest/source
checkpoint discovery, date-bound private checkpoint ownership, report
semantics, and quality checks for a new exclusive end. Select a single
short, explicit operator command and a separate nonblocking quality summary
that retains failures and stale/gap warnings without calling them provider
successes or verified missing sessions. Only after that audit should an
implementation or operational qualification be chosen. No scheduler,
automatic retry, status migration, mass backfill, or user-interface action
is authorized by this result.
