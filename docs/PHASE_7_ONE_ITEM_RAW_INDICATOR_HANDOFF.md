# Phase 7 — one-item stored-close SMA qualification

Classification: `OPERATIONAL — READY FOR USER EXECUTION`. Fresh clean
GitHub `develop` matched caller baseline
`5ce869688cbd61e1a9ae0621bdac6d6b760058c4`. This package changes no
application code or private runtime data. The one-item projection is a
read-only SQLite operation; it writes only a new private value document and
a separate redacted report. The previous complete cohort report has SHA-256
`1f9cf22bcd152dee0c6bcc0d4a558fe1a2d71560596e9ba56bf104e6aeeef937`.

Run the ASCII-only PowerShell block below in the Desktop repository **before
applying this ZIP**. Pause other candle jobs. It verifies the exact Git
baseline, private profile/manifest/source/weekly-checkpoint binding, prior
report checksum, one-item output contracts, unchanged checkpoint, and
independent SQLite integrity. It makes no Yahoo request and does not change
the candle database or weekly checkpoint. Never send the private result:
it contains a symbol, currency, latest price, and SMA values.

```powershell
$ErrorActionPreference = "Stop"
$Repository = "C:\Users\tu\Desktop\InvestmentTerminal"
$ExpectedHead = "5ce869688cbd61e1a9ae0621bdac6d6b760058c4"
$Profile = "C:\runtime\data\weekly_run_profile.json"
$Checkpoint = "C:\runtime\data\weekly_run\weekly_candle_refresh_2026-09-29.json"
$Database = "C:\runtime\data\investment_terminal.db"
$CohortReport = "C:\runtime\reports\weekly_stored_cohorts_20160929_20260929_001.json"
$CohortSha256 = "1f9cf22bcd152dee0c6bcc0d4a558fe1a2d71560596e9ba56bf104e6aeeef937"
$PrivateOutput = "C:\runtime\data\latest_raw_indicator_projection_20260929_001.json"
$Report = "C:\runtime\reports\latest_raw_indicator_projection_20260929_001.json"
$End = "2026-09-29T00:00:00+00:00"
$ManifestChecksum = "8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a"
$SelectionChecksum = "75d839c54ff43969832a4d1110deba538cd52793e9402db5cba2dc1decc6c5ae"

Set-Location -LiteralPath $Repository
if ((git branch --show-current).Trim() -ne "develop") { throw "Branch mismatch" }
if ((git rev-parse HEAD).Trim() -ne $ExpectedHead) { throw "HEAD mismatch" }
if (@(git status --porcelain).Count -ne 0) { throw "Working tree is not clean" }
foreach ($RequiredPath in @($Profile, $Checkpoint, $Database, $CohortReport)) {
    if (-not (Test-Path -LiteralPath $RequiredPath -PathType Leaf)) {
        throw "Required private input is missing: $RequiredPath"
    }
}
if (Test-Path -LiteralPath $PrivateOutput) { throw "Private output already exists" }
if (Test-Path -LiteralPath $Report) { throw "Report already exists" }
if ((Get-FileHash -LiteralPath $CohortReport -Algorithm SHA256).Hash.ToLowerInvariant() -ne $CohortSha256) {
    throw "Cohort report checksum mismatch"
}

$PreflightCode = @'
import json
import sys
from datetime import datetime
from pathlib import Path
from investment_terminal.cli.weekly_run import _profile
from investment_terminal.operations.weekly_candle_refresh import WeeklyCandleRefreshPlan, _validated_outcomes

profile_path, checkpoint_path, database_path, cohort_path = map(Path, sys.argv[1:5])
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
cohort = json.loads(cohort_path.read_text(encoding="utf-8"))
if (len(plan.items) != 11892 or plan.excluded_count != 127
        or plan.selection_checksum != "75d839c54ff43969832a4d1110deba538cd52793e9402db5cba2dc1decc6c5ae"
        or len(outcomes) != len(plan.items)
        or cohort.get("schema_version") != 1
        or cohort.get("operation_identity") != "WEEKLY_STORED_COHORTS"
        or cohort.get("status") != "COMPLETE"
        or cohort.get("manifest_checksum") != plan.manifest_checksum
        or cohort.get("selection_checksum") != plan.selection_checksum
        or cohort.get("end") != end.isoformat()
        or cohort.get("selected_series_count") != len(plan.items)):
    raise SystemExit("Complete private evidence binding mismatch")
print("Private inputs and complete checkpoint: PASSED")
'@
$PreflightCode | python - $Profile $Checkpoint $Database $CohortReport $End
if ($LASTEXITCODE -ne 0) { throw "Preflight failed; do not run projection" }
$PrivateProfile = Get-Content -LiteralPath $Profile -Raw -Encoding UTF8 | ConvertFrom-Json
$Manifest = [string]$PrivateProfile.manifest
$SourceDirectory = [string]$PrivateProfile.source_checkpoint_directory
$CheckpointHashBefore = (Get-FileHash -LiteralPath $Checkpoint -Algorithm SHA256).Hash

python -m investment_terminal.cli.latest_raw_indicator_projection `
    --manifest $Manifest --manifest-checksum $ManifestChecksum `
    --source-checkpoint-directory $SourceDirectory `
    --weekly-checkpoint $Checkpoint --database $Database `
    --end $End --max-items 1 `
    --private-output $PrivateOutput --report-output $Report
$CommandExit = $LASTEXITCODE
if (-not (Test-Path -LiteralPath $Report -PathType Leaf)) {
    throw "No report was produced; do not rerun"
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
if ($CommandExit -ne 0) { throw "One-item projection failed; send the redacted report" }
if (-not (Test-Path -LiteralPath $PrivateOutput -PathType Leaf)) {
    throw "Private result is missing; send the redacted report"
}

$ValidationCode = @'
import json
import math
import sys
from datetime import datetime
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
    "processed_count": 1,
    "max_items": 1,
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
bins = report.get("availability_counts")
keys = ("NO_CANDLES", "UNDER_50", "50_TO_199", "BOTH_AVAILABLE")
if (not isinstance(bins, list) or len(bins) != 4
        or [item.get("category") for item in bins] != list(keys)
        or any(type(item.get("count")) is not int or item["count"] < 0
               for item in bins)
        or sum(item["count"] for item in bins) != 1):
    raise SystemExit("Availability bins do not reconcile")
counts = {item["category"]: item["count"] for item in bins}
if (report.get("sma50_available_count") != counts["50_TO_199"] + counts["BOTH_AVAILABLE"]
        or report.get("sma200_available_count") != counts["BOTH_AVAILABLE"]
        or type(report.get("recent_7_calendar_day_proxy_count")) is not int
        or report["recent_7_calendar_day_proxy_count"] not in (0, 1)):
    raise SystemExit("SMA or recency counts do not reconcile")
items = private.get("items")
if not isinstance(items, list) or len(items) != 1 or not isinstance(items[0], dict):
    raise SystemExit("Private projection item count mismatch")
item = items[0]
count = item.get("sample_count_capped_at_200")
if (type(count) is not int or not 0 <= count <= 200
        or item.get("availability") not in keys
        or counts[item["availability"]] != 1
        or type(item.get("recent_7_calendar_day_proxy")) is not bool
        or int(item["recent_7_calendar_day_proxy"]) != report["recent_7_calendar_day_proxy_count"]):
    raise SystemExit("Private sample evidence mismatch")
expected = "NO_CANDLES" if count == 0 else "UNDER_50" if count < 50 else "50_TO_199" if count < 200 else "BOTH_AVAILABLE"
if item["availability"] != expected:
    raise SystemExit("Private availability mismatch")
for field, minimum in (("sma50_raw_close", 50), ("sma200_raw_close", 200)):
    value = item.get(field)
    if (count >= minimum) != (type(value) in (int, float) and math.isfinite(value) and value > 0):
        raise SystemExit("Private SMA availability mismatch")
if count == 0:
    if item.get("latest_timestamp") is not None or item.get("latest_raw_close") is not None:
        raise SystemExit("Empty private sample mismatch")
else:
    stamp = datetime.fromisoformat(item["latest_timestamp"])
    value = item.get("latest_raw_close")
    if (stamp.utcoffset() is None or stamp >= datetime.fromisoformat(binding["end"])
            or type(value) not in (int, float) or not math.isfinite(value) or value <= 0):
        raise SystemExit("Latest private observation mismatch")
print("One-item private/report qualification: PASSED")
'@
$ValidationCode | python - $PrivateOutput $Report
if ($LASTEXITCODE -ne 0) { throw "Projection validation failed; send the redacted report" }
```

Return only the redacted report, its SHA-256, and the `SQLite integrity: ok`
line. Do not send the private value document, profile, manifest, checkpoints,
or database. If any step fails, do not rerun automatically; send the redacted
report if it exists and the error line. One-item success does not authorize
full-universe projection, adjusted-price claims, or unattended scheduling.
