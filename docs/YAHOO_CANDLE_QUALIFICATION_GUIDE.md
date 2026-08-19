# Yahoo Historical Candle Qualification Guide

Run one explicit bounded request:

```powershell
python -m investment_terminal.cli.yahoo_candle_qualification `
  --symbol MSFT `
  --resolution D `
  --currency USD `
  --start 2026-08-01T00:00:00+00:00 `
  --end 2026-08-19T00:00:00+00:00 `
  --cache-directory C:\runtime\cache\yfinance `
  --output C:\runtime\reports\yahoo_msft_qualification.json `
  --json
```

Both timestamps must be timezone-aware and `start` must precede `end`.
Supported resolutions are `D`, `W`, and `M`. The output file is atomically
replaced. The cache directory is required for live execution so yfinance does
not select an implicit user-profile cache that may be unwritable or outside the
runtime filesystem boundary.

Exit behavior:

- `SUCCESS`: positive validated candle coverage, exit zero;
- `EMPTY`: provider returned no candles, exit zero with explicit zero coverage;
- `FAILED`: report is written first, then exit code 1.

Keep live reports outside public source control. A report may identify requested
instruments and local output paths. Never interpret one successful request as
general reliability, licensing approval, 20-year coverage, or authorization to
start broad ingestion.
