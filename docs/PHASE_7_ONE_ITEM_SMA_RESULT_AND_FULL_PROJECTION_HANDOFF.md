# Phase 7 — one-item SMA result and complete projection handoff

Classification: `OPERATIONAL — READY FOR USER EXECUTION`. A fresh clean
GitHub `develop` clone matched `776f80dc60e9b71e7d0a57a64392b754ebf56b0a`.
The explicitly returned redacted one-item report has SHA-256
`0b8772614f97199bfe68ddb88cf65d212c2c53f9b8b0a547caa74de14e755e64`.
It is schema 1 `COMPLETE`, bound to manifest
`8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a`
and selection
`75d839c54ff43969832a4d1110deba538cd52793e9402db5cba2dc1decc6c5ae`.
Exactly one of 11,892 selected series was processed; that series had both
SMA50 and SMA200 available and met the seven-calendar-day recency proxy.
The user separately reported `SQLite integrity: ok`. Neither fact proves
full-universe success, ten-year completeness, exchange-session continuity,
or corporate-action-adjusted prices.

The existing CLI can project the entire deterministic selection without a
provider request or a candle/checkpoint write. The private output contains
symbols, prices and values; only its redacted aggregate report may be sent
back. This package changes no application code or private runtime data.
The user should run the ASCII-only PowerShell block **before applying this
ZIP**. Pause other candle/database jobs. The command may take time because
it validates each selected stored series; do not interrupt or automatically
retry it. If a single series fails validation, the CLI emits a generic
redacted failure report and no private partial projection. That is a
diagnostic result, not permission to weaken validation.

```powershell
$ErrorActionPreference = "Stop"
$Repository = "C:\Users\tu\Desktop\InvestmentTerminal"
$ExpectedHead = "776f80dc60e9b71e7d0a57a64392b754ebf56b0a"
$Profile = "C:\runtime\data\weekly_run_profile.json"
$Checkpoint = "C:\runtime\data\weekly_run\weekly_candle_refresh_2026-09-29.json"
$Database = "C:\runtime\data\investment_terminal.db"
$PriorReport = "C:\runtime\reports\latest_raw_indicator_projection_20260929_001.json"
$PriorSha256 = "0b8772614f97199bfe68ddb88cf65d212c2c53f9b8b0a547caa74de14e755e64"
$PrivateOutput = "C:\runtime\data\latest_raw_indicator_projection_20260929_full.json"
$Report = "C:\runtime\reports\latest_raw_indicator_projection_20260929_full.json"
$End = "2026-09-29T00:00:00+00:00"
$ManifestChecksum = "8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a"
$SelectionChecksum = "75d839c54ff43969832a4d1110deba538cd52793e9402db5cba2dc1decc6c5ae"

Set-Location -LiteralPath $Repository
if ((git branch --show-current).Trim() -ne "develop") { throw "Branch mismatch" }
if ((git rev-parse HEAD).Trim() -ne $ExpectedHead) { throw "HEAD mismatch" }
if (@(git status --porcelain).Count -ne 0) { throw "Working tree is not clean" }
foreach ($RequiredPath in @($Profile, $Checkpoint, $Database, $PriorReport)) {
    if (-not (Test-Path -LiteralPath $RequiredPath -PathType Leaf)) {
        throw "Required private input is missing: $RequiredPath"
    }
}
if (Test-Path -LiteralPath $PrivateOutput) { throw "Private output already exists" }
if (Test-Path -LiteralPath $Report) { throw "Report already exists" }
if ((Get-FileHash -LiteralPath $PriorReport -Algorithm SHA256).Hash.ToLowerInvariant() -ne $PriorSha256) {
    throw "One-item report checksum mismatch"
}

$PreflightCode = @'
import json
import sys
from datetime import datetime
from pathlib import Path
from investment_terminal.cli.weekly_run import _profile
from investment_terminal.operations.weekly_candle_refresh import WeeklyCandleRefreshPlan, _validated_outcomes

profile_path, checkpoint_path, database_path, report_path = map(Path, sys.argv[1:5])
end = datetime.fromisoformat(sys.argv[5])
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

plan = WeeklyCandleRefreshPlan.from_manifest(
    manifest, profile["manifest_checksum"], source, end=end,
)
outcomes = _validated_outcomes(
    json.loads(checkpoint_path.read_text(encoding="utf-8")), plan,
)
prior = json.loads(report_path.read_text(encoding="utf-8"))
if (len(plan.items) != 11892 or plan.excluded_count != 127
        or plan.selection_checksum != "75d839c54ff43969832a4d1110deba538cd52793e9402db5cba2dc1decc6c5ae"
        or len(outcomes) != len(plan.items)
        or prior.get("schema_version") != 1
        or prior.get("operation_identity") != "LATEST_RAW_INDICATOR_PROJECTION_REPORT"
        or prior.get("status") != "COMPLETE"
        or prior.get("manifest_checksum") != plan.manifest_checksum
        or prior.get("selection_checksum") != plan.selection_checksum
        or prior.get("end") != end.isoformat()
        or prior.get("processed_count") != 1
        or prior.get("sma50_available_count") != 1
        or prior.get("sma200_available_count") != 1):
    raise SystemExit("Complete private evidence binding mismatch")
print("Private input and one-item evidence: PASSED")
'@
$PreflightCode | python - $Profile $Checkpoint $Database $PriorReport $End
if ($LASTEXITCODE -ne 0) { throw "Preflight failed; do not run projection" }
$PrivateProfile = Get-Content -LiteralPath $Profile -Raw -Encoding UTF8 | ConvertFrom-Json
$Manifest = [string]$PrivateProfile.manifest
$SourceDirectory = [string]$PrivateProfile.source_checkpoint_directory
$CheckpointHashBefore = (Get-FileHash -LiteralPath $Checkpoint -Algorithm SHA256).Hash

python -m investment_terminal.cli.latest_raw_indicator_projection `
    --manifest $Manifest --manifest-checksum $ManifestChecksum `
    --source-checkpoint-directory $SourceDirectory `
    --weekly-checkpoint $Checkpoint --database $Database `
    --end $End --max-items 11892 `
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
if ((Get-FileHash -LiteralPath $Checkpoint -Algorithm SHA256).Hash -ne $CheckpointHashBefore) {
    throw "Private checkpoint changed; send the redacted report"
}
if ($CommandExit -ne 0) { throw "Complete projection failed; send the redacted report" }
if (-not (Test-Path -LiteralPath $PrivateOutput -PathType Leaf)) {
    throw "Private result is missing; send the redacted report"
}

$ValidationCode = @'
import json
import math
import sys
from pathlib import Path

private = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
report = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
binding = {
    "schema_version": 1,
    "manifest_checksum": "8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a",
    "selection_checksum": "75d839c54ff43969832a4d1110deba538cd52793e9402db5cba2dc1decc6c5ae",
    "end": "2026-09-29T00:00:00+00:00",
    "price_basis": "STORED_CLOSE_NO_EXPLICIT_ADJUSTMENT",
    "selected_series_count": 11892,
    "processed_count": 11892,
    "max_items": 11892,
}
for payload, identity in (
        (private, "LATEST_RAW_INDICATOR_PROJECTION"),
        (report, "LATEST_RAW_INDICATOR_PROJECTION_REPORT")):
    if (any(type(payload.get(key)) is not type(value) or payload.get(key) != value
            for key, value in binding.items())
            or payload.get("operation_identity") != identity
            or payload.get("status") != "COMPLETE"):
        raise SystemExit("Projection binding mismatch")
if report.get("failure") is not None or "items" in report:
    raise SystemExit("Redacted report shape mismatch")
keys = ("NO_CANDLES", "UNDER_50", "50_TO_199", "BOTH_AVAILABLE")
bins = report.get("availability_counts")
if (not isinstance(bins, list) or len(bins) != 4
        or [entry.get("category") for entry in bins] != list(keys)
        or any(type(entry.get("count")) is not int or entry["count"] < 0
               for entry in bins)
        or sum(entry["count"] for entry in bins) != 11892):
    raise SystemExit("Availability bins do not reconcile")
counts = {entry["category"]: entry["count"] for entry in bins}
if (report.get("sma50_available_count") != counts["50_TO_199"] + counts["BOTH_AVAILABLE"]
        or report.get("sma200_available_count") != counts["BOTH_AVAILABLE"]
        or type(report.get("recent_7_calendar_day_proxy_count")) is not int):
    raise SystemExit("SMA or recency totals do not reconcile")
items = private.get("items")
if not isinstance(items, list) or len(items) != 11892:
    raise SystemExit("Private item count mismatch")
observed = {key: 0 for key in keys}
symbols = set()
recent = 0
for item in items:
    if not isinstance(item, dict):
        raise SystemExit("Invalid private item")
    symbol = item.get("symbol")
    count = item.get("sample_count_capped_at_200")
    if (not isinstance(symbol, str) or not symbol or symbol in symbols
            or type(count) is not int or not 0 <= count <= 200
            or type(item.get("recent_7_calendar_day_proxy")) is not bool):
        raise SystemExit("Invalid private item identity or sample")
    symbols.add(symbol)
    expected = "NO_CANDLES" if count == 0 else "UNDER_50" if count < 50 else "50_TO_199" if count < 200 else "BOTH_AVAILABLE"
    if item.get("availability") != expected:
        raise SystemExit("Private availability mismatch")
    for field, minimum in (("sma50_raw_close", 50), ("sma200_raw_close", 200)):
        value = item.get(field)
        if (count >= minimum) != (type(value) in (int, float) and math.isfinite(value) and value > 0):
            raise SystemExit("Private SMA availability mismatch")
    observed[expected] += 1
    recent += item["recent_7_calendar_day_proxy"]
if observed != counts or recent != report["recent_7_calendar_day_proxy_count"]:
    raise SystemExit("Private and redacted aggregate mismatch")
print("Complete private/report qualification: PASSED")
'@
$ValidationCode | python - $PrivateOutput $Report
if ($LASTEXITCODE -ne 0) { throw "Projection validation failed; send the redacted report" }
```

Return only the redacted full report, its SHA-256, and `SQLite integrity: ok`.
Never send the private value document, profile, manifest, source evidence,
weekly checkpoint, or database. On failure, send the redacted report if it
exists and the error line; do not rerun automatically. Review the measured
availability and recency counts before designing a ChatGPT-facing export,
adjustment policy, or weekly schedule.
