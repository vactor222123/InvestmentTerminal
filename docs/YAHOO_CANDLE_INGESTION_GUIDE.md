# Yahoo Bounded Candle Ingestion Guide

```powershell
python -m investment_terminal.cli.yahoo_candle_ingestion `
  --symbol MSFT `
  --resolution D `
  --currency USD `
  --start 2026-08-01T00:00:00+00:00 `
  --end 2026-08-19T00:00:00+00:00 `
  --cache-directory C:\runtime\cache\yfinance `
  --database C:\runtime\data\investment_terminal.db `
  --output C:\runtime\reports\yahoo_msft_ingestion.json `
  --json
```

`SUCCESS` means candles were downloaded and persistence completed; `EMPTY`
means no candles were returned; `FAILED` is written before exit code 1.
Repeating a request is safe: existing candle identities become duplicates.
Keep cache, database, and reports outside source control.

Report schema version 2 also includes stored earliest/latest timestamps and
the observed elapsed span. For the first controlled expansion, retain MSFT and
daily resolution but use `2025-08-19T00:00:00+00:00` as `--start`, preserve the
same database, and write a new report filename.
