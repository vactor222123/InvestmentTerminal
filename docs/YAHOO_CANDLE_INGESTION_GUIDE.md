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
