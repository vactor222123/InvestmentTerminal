# Phase 7 — one private instrument research-export handoff

Classification: `OPERATIONAL — READY FOR USER EXECUTION`. A fresh clean
GitHub `develop` clone matched
`a1bc935877266c94861e0ed00b7dcb7350cf6feb`. This package changes
documentation only. It does not inspect or mutate `C:\runtime`, call Yahoo,
update SQLite, or assert that an export has already succeeded.

The reviewed full raw-indicator aggregate report is schema 1 `COMPLETE`
for all 11,892 selected series and has SHA-256
`1cc1b7b09ff1ddf84699a9e137af44e07044f373680af6a01eafbbe6c976d184`.
It reports 10,239 with both SMA50 and SMA200 and 11,787 meeting the
seven-calendar-day recency proxy. Their intersection and identities are not
in that redacted report. The command below chooses the first qualifying
symbol **locally from the existing private full projection**, without
printing or transmitting that identity. It exports only that symbol's
stored daily candles for the explicit 2016-09-29 to 2026-09-29 exclusive
window. This is a stored-row window, not a claim of ten-year continuous
trading sessions or adjusted-price performance.

Run this entire ASCII-only PowerShell block in a fresh terminal **before
applying this package's ZIP**. Pause other candle/database jobs. Do not
automatically rerun after a failure; send the redacted report and error line
if one was produced. The two output names must be unused.

```powershell
$ErrorActionPreference = "Stop"
$Repository = "C:\Users\tu\Desktop\InvestmentTerminal"
$ExpectedHead = "a1bc935877266c94861e0ed00b7dcb7350cf6feb"
$Profile = "C:\runtime\data\weekly_run_profile.json"
$Checkpoint = "C:\runtime\data\weekly_run\weekly_candle_refresh_2026-09-29.json"
$Database = "C:\runtime\data\investment_terminal.db"
$Projection = "C:\runtime\data\latest_raw_indicator_projection_20260929_full.json"
$PriorReport = "C:\runtime\reports\latest_raw_indicator_projection_20260929_full.json"
$PriorReportSha256 = "1cc1b7b09ff1ddf84699a9e137af44e07044f373680af6a01eafbbe6c976d184"
$PrivateOutput = "C:\runtime\data\instrument_research_export_20260929_001.json"
$Report = "C:\runtime\reports\instrument_research_export_20260929_001.json"
$ManifestChecksum = "8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a"
$SelectionChecksum = "75d839c54ff43969832a4d1110deba538cd52793e9402db5cba2dc1decc6c5ae"
$HistoryStart = "2016-09-29T00:00:00+00:00"
$End = "2026-09-29T00:00:00+00:00"

Set-Location -LiteralPath $Repository
if ((git branch --show-current).Trim() -ne "develop") { throw "Branch mismatch" }
if ((git rev-parse HEAD).Trim() -ne $ExpectedHead) { throw "HEAD mismatch" }
if (@(git status --porcelain).Count -ne 0) { throw "Working tree is not clean" }
foreach ($RequiredPath in @($Profile, $Checkpoint, $Database, $Projection, $PriorReport)) {
    if (-not (Test-Path -LiteralPath $RequiredPath -PathType Leaf)) {
        throw "Required private input is missing: $RequiredPath"
    }
}
if (Test-Path -LiteralPath $PrivateOutput) { throw "Private output already exists" }
if (Test-Path -LiteralPath $Report) { throw "Report already exists" }
if ((Get-FileHash -LiteralPath $PriorReport -Algorithm SHA256).Hash.ToLowerInvariant() -ne $PriorReportSha256) {
    throw "Full projection report checksum mismatch"
}
$ProjectionSha256 = (Get-FileHash -LiteralPath $Projection -Algorithm SHA256).Hash.ToLowerInvariant()
$CheckpointHashBefore = (Get-FileHash -LiteralPath $Checkpoint -Algorithm SHA256).Hash.ToLowerInvariant()

$PreflightCode = @'
import json
import sys
from datetime import datetime
from pathlib import Path
from investment_terminal.cli.weekly_run import _profile
from investment_terminal.operations.weekly_candle_refresh import WeeklyCandleRefreshPlan, _validated_outcomes

profile_path, checkpoint_path, database_path, projection_path, report_path = map(Path, sys.argv[1:6])
end = datetime.fromisoformat(sys.argv[6])
projection_sha256 = sys.argv[7]
profile, paths = _profile(profile_path)
if (profile["manifest_checksum"] != "8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a"
        or paths["database"] != database_path.resolve()
        or paths["weekly_checkpoint_directory"] / checkpoint_path.name != checkpoint_path.resolve()):
    raise SystemExit("Private profile binding mismatch")
manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
source_dir = paths["source_checkpoint_directory"]
def source(index):
    path = source_dir / f"batch_{index:04d}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
plan = WeeklyCandleRefreshPlan.from_manifest(manifest, profile["manifest_checksum"], source, end=end)
outcomes = _validated_outcomes(json.loads(checkpoint_path.read_text(encoding="utf-8")), plan)
projection = json.loads(projection_path.read_text(encoding="utf-8"))
prior = json.loads(report_path.read_text(encoding="utf-8"))
if (len(plan.items) != 11892 or len(outcomes) != len(plan.items)
        or plan.selection_checksum != "75d839c54ff43969832a4d1110deba538cd52793e9402db5cba2dc1decc6c5ae"
        or prior.get("schema_version") != 1
        or prior.get("operation_identity") != "LATEST_RAW_INDICATOR_PROJECTION_REPORT"
        or prior.get("status") != "COMPLETE"
        or prior.get("manifest_checksum") != plan.manifest_checksum
        or prior.get("selection_checksum") != plan.selection_checksum
        or prior.get("end") != end.isoformat()
        or prior.get("processed_count") != len(plan.items)
        or projection.get("operation_identity") != "LATEST_RAW_INDICATOR_PROJECTION"
        or projection.get("status") != "COMPLETE"
        or projection.get("manifest_checksum") != plan.manifest_checksum
        or projection.get("selection_checksum") != plan.selection_checksum
        or projection.get("end") != end.isoformat()
        or projection.get("processed_count") != len(plan.items)
        or len(projection.get("items", [])) != len(plan.items)
        or len(projection_sha256) != 64):
    raise SystemExit("Complete private evidence binding mismatch")
candidates = [item["symbol"] for item in projection["items"]
              if item.get("availability") == "BOTH_AVAILABLE"
              and item.get("recent_7_calendar_day_proxy") is True]
if not candidates or candidates[0] not in {symbol for symbol, _ in plan.items}:
    raise SystemExit("No qualifying selected instrument")
print(candidates[0])
'@
$Symbol = $PreflightCode | python - $Profile $Checkpoint $Database $Projection $PriorReport $End $ProjectionSha256
if ($LASTEXITCODE -ne 0 -or @($Symbol).Count -ne 1 -or -not $Symbol) {
    throw "Private preflight failed; do not run export"
}
$PrivateProfile = Get-Content -LiteralPath $Profile -Raw -Encoding UTF8 | ConvertFrom-Json
$Manifest = [string]$PrivateProfile.manifest
$SourceDirectory = [string]$PrivateProfile.source_checkpoint_directory

python -m investment_terminal.cli.instrument_research_export `
    --manifest $Manifest --manifest-checksum $ManifestChecksum `
    --source-checkpoint-directory $SourceDirectory `
    --weekly-checkpoint $Checkpoint --projection $Projection `
    --projection-sha256 $ProjectionSha256 --database $Database `
    --symbol $Symbol --history-start $HistoryStart --end $End `
    --private-output $PrivateOutput --report-output $Report
$CommandExit = $LASTEXITCODE
if (-not (Test-Path -LiteralPath $Report -PathType Leaf)) {
    throw "No redacted report was produced; do not rerun"
}
Write-Host "SEND: $Report"
Write-Host "Report SHA-256: $((Get-FileHash -LiteralPath $Report -Algorithm SHA256).Hash.ToLowerInvariant())"
Write-Host "DO NOT SEND: $Profile"
Write-Host "DO NOT SEND: $Manifest"
Write-Host "DO NOT SEND: $SourceDirectory"
Write-Host "DO NOT SEND: $Checkpoint"
Write-Host "DO NOT SEND: $Database"
Write-Host "DO NOT SEND: $Projection"
Write-Host "DO NOT SEND: $PrivateOutput"

$IntegrityCode = @'
import sqlite3
import sys
from pathlib import Path
database = Path(sys.argv[1])
connection = sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)
try:
    connection.execute("PRAGMA query_only = ON")
    result = connection.execute("PRAGMA integrity_check").fetchone()[0]
finally:
    connection.close()
if result != "ok":
    raise SystemExit("SQLite integrity check failed")
print("SQLite integrity: ok")
'@
$IntegrityCode | python - $Database
if ($LASTEXITCODE -ne 0) { throw "SQLite integrity failed; send the redacted report" }
if ((Get-FileHash -LiteralPath $Checkpoint -Algorithm SHA256).Hash.ToLowerInvariant() -ne $CheckpointHashBefore) {
    throw "Private checkpoint changed; send the redacted report"
}
if ((Get-FileHash -LiteralPath $Projection -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ProjectionSha256) {
    throw "Private source projection changed; send the redacted report"
}
if ($CommandExit -ne 0) { throw "Instrument export failed; send the redacted report" }
if (-not (Test-Path -LiteralPath $PrivateOutput -PathType Leaf)) {
    throw "Private result is missing; send the redacted report"
}

$ValidationCode = @'
import hashlib
import json
import sys
from pathlib import Path
private = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
report = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
symbol = sys.argv[3]
projection_sha256 = sys.argv[4]
report_keys = {
    "schema_version", "manifest_checksum", "selection_checksum",
    "source_projection_sha256", "history_start", "end", "price_basis",
    "candle_count", "history_candles_sha256", "operation_identity", "status",
    "sample_count_capped_at_200", "availability",
    "recent_7_calendar_day_proxy", "failure", "limitations",
}
common = {
    "schema_version": 1,
    "manifest_checksum": "8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a",
    "selection_checksum": "75d839c54ff43969832a4d1110deba538cd52793e9402db5cba2dc1decc6c5ae",
    "source_projection_sha256": projection_sha256,
    "history_start": "2016-09-29T00:00:00+00:00",
    "end": "2026-09-29T00:00:00+00:00",
    "price_basis": "STORED_CLOSE_NO_EXPLICIT_ADJUSTMENT",
    "status": "COMPLETE",
}
if (set(report) != report_keys or report.get("operation_identity") != "INSTRUMENT_RESEARCH_EXPORT_REPORT"
        or private.get("operation_identity") != "INSTRUMENT_RESEARCH_EXPORT"
        or any(payload.get(key) != value for payload in (private, report) for key, value in common.items())
        or private.get("symbol") != symbol or report.get("failure") is not None
        or report.get("availability") != "BOTH_AVAILABLE"
        or report.get("recent_7_calendar_day_proxy") is not True):
    raise SystemExit("Export binding or redaction mismatch")
candles = private.get("candles")
indicator = private.get("indicator")
if (not isinstance(candles, list) or not isinstance(indicator, dict)
        or not 0 < len(candles) <= 4000
        or private.get("candle_count") != len(candles)
        or report.get("candle_count") != len(candles)
        or report.get("sample_count_capped_at_200") != indicator.get("sample_count_capped_at_200")
        or report.get("availability") != indicator.get("availability")):
    raise SystemExit("Private/result count mismatch")
digest = hashlib.sha256(json.dumps(candles, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")).hexdigest()
if private.get("history_candles_sha256") != digest or report.get("history_candles_sha256") != digest:
    raise SystemExit("Exported candle checksum mismatch")
print("Private/report qualification: PASSED")
'@
$ValidationCode | python - $PrivateOutput $Report $Symbol $ProjectionSha256
if ($LASTEXITCODE -ne 0) { throw "Export validation failed; send the redacted report" }
```

Return only the redacted report, its printed SHA-256, and the
`SQLite integrity: ok` line. Do not send the private instrument export,
private projection, profile, manifest, checkpoints, or SQLite database.
Review this one result before deciding on any wider export or explicit
ChatGPT-sharing boundary. Do not claim adjusted performance or enable
unattended weekly scheduling from this qualification.
