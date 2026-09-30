# Phase 7 — stored-coverage result and observed-history cohorts

Classification: `OPERATIONAL — READY FOR USER EXECUTION`.

Fresh clean GitHub `develop` matched caller baseline
`b46a96982993322c04d64dba5979599b432d052d`. The returned redacted
schema-2 coverage report has SHA-256
`e7cea0ba6b5440092237e1ebfdee6560b69be65cc9dad5596872358ae4c8279e`.
It is bound to the 11,892 selected series and the explicit half-open
2016-09-29 to 2026-09-29 UTC window. The user separately reported SQLite
integrity `ok`.

Measured within that window: 17,274,367 stored daily rows, zero series
without a row, 10,239 series with at least 200 stored rows, 11,787 with a
last-candle proxy within seven calendar days of the end, 4,461 with a
first-candle proxy within seven days of the start, 4,449 with both proxies,
41 with an observed interior gap over seven days, and 25 with one over 30
days. The 87 weekly failures remain 45 `NO_PRICE_DATA`, one
`RESPONSE_NUMERIC`, and 41 `STORED_CANDLE_DRIFT`. None of these aggregates
proves exchange-session completeness, listing age, corporate-action
adjustment quality, or indicator validity. In particular, 7,431 without a
start proxy must not be labeled missing history without age/context evidence.

The next smallest safe measurement is one existing read-only
`WEEKLY_STORED_COHORTS` run for the **same** window and complete private
checkpoint. It partitions observed first-candle age, start/end proxies,
largest gaps, and their intersections with weekly outcomes. It makes no
Yahoo request and does not modify candles or the checkpoint. Run the
ASCII-only PowerShell block below on the Desktop repository **before
applying this ZIP**. Pause other candle jobs during the scan.

```powershell
$ErrorActionPreference = "Stop"
$Repository = "C:\Users\tu\Desktop\InvestmentTerminal"
$ExpectedHead = "b46a96982993322c04d64dba5979599b432d052d"
$Profile = "C:\runtime\data\weekly_run_profile.json"
$Checkpoint = "C:\runtime\data\weekly_run\weekly_candle_refresh_2026-09-29.json"
$Database = "C:\runtime\data\investment_terminal.db"
$PreviousReport = "C:\runtime\reports\weekly_stored_coverage_20160929_20260929_001.json"
$PreviousSha256 = "e7cea0ba6b5440092237e1ebfdee6560b69be65cc9dad5596872358ae4c8279e"
$Report = "C:\runtime\reports\weekly_stored_cohorts_20160929_20260929_001.json"
$Start = "2016-09-29T00:00:00+00:00"
$End = "2026-09-29T00:00:00+00:00"
$ManifestChecksum = "8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a"
$SelectionChecksum = "75d839c54ff43969832a4d1110deba538cd52793e9402db5cba2dc1decc6c5ae"

Set-Location -LiteralPath $Repository
if ((git branch --show-current).Trim() -ne "develop") { throw "Branch mismatch" }
if ((git rev-parse HEAD).Trim() -ne $ExpectedHead) { throw "HEAD mismatch" }
if (@(git status --porcelain).Count -ne 0) { throw "Working tree is not clean" }
foreach ($RequiredPath in @($Profile, $Checkpoint, $Database, $PreviousReport)) {
    if (-not (Test-Path -LiteralPath $RequiredPath -PathType Leaf)) {
        throw "Required private input is missing: $RequiredPath"
    }
}
if (Test-Path -LiteralPath $Report) { throw "Cohort report already exists" }
if ((Get-FileHash -LiteralPath $PreviousReport -Algorithm SHA256).Hash.ToLowerInvariant() -ne $PreviousSha256) {
    throw "Stored-coverage report checksum mismatch"
}

$PreflightCode = @'
import json
import sys
from datetime import datetime
from pathlib import Path
from investment_terminal.cli.weekly_run import _profile
from investment_terminal.operations.weekly_candle_refresh import WeeklyCandleRefreshPlan, _validated_outcomes

profile_path, checkpoint_path, database_path, previous_path = map(Path, sys.argv[1:5])
start = datetime.fromisoformat(sys.argv[5])
end = datetime.fromisoformat(sys.argv[6])
profile, paths = _profile(profile_path)
if (profile["manifest_checksum"] != "8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a"
        or paths["database"] != database_path.resolve()
        or paths["weekly_checkpoint_directory"] / checkpoint_path.name != checkpoint_path.resolve()):
    raise SystemExit("Private profile binding mismatch")
previous = json.loads(previous_path.read_text(encoding="utf-8"))
coverage = previous.get("coverage")
if (previous.get("schema_version") != 2
        or previous.get("operation_identity") != "WEEKLY_STORED_COVERAGE"
        or previous.get("status") != "COMPLETE"
        or previous.get("manifest_checksum") != profile["manifest_checksum"]
        or previous.get("selection_checksum") != "75d839c54ff43969832a4d1110deba538cd52793e9402db5cba2dc1decc6c5ae"
        or previous.get("history_start") != start.isoformat()
        or previous.get("end") != end.isoformat()
        or not isinstance(coverage, dict)
        or coverage.get("selected_series_count") != 11892
        or coverage.get("history_window_zero_count") != 0
        or coverage.get("first_candle_within_7_calendar_days_of_start_count") != 4461
        or coverage.get("last_candle_within_7_calendar_days_of_end_count") != 11787
        or coverage.get("both_endpoint_proxy_count") != 4449
        or coverage.get("series_with_gap_over_7_calendar_days_count") != 41
        or coverage.get("series_with_gap_over_30_calendar_days_count") != 25):
    raise SystemExit("Stored-coverage report binding mismatch")
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
if (len(plan.items) != 11892 or plan.excluded_count != 127
        or plan.selection_checksum != previous["selection_checksum"]
        or len(outcomes) != 11892):
    raise SystemExit("Complete private checkpoint binding mismatch")
print("Coverage report, profile and checkpoint: PASSED")
'@
$PreflightCode | python - $Profile $Checkpoint $Database $PreviousReport $Start $End
if ($LASTEXITCODE -ne 0) { throw "Preflight failed; do not run cohort scan" }
$PrivateProfile = Get-Content -LiteralPath $Profile -Raw -Encoding UTF8 | ConvertFrom-Json
$Manifest = [string]$PrivateProfile.manifest
$SourceDirectory = [string]$PrivateProfile.source_checkpoint_directory
$CheckpointHashBefore = (Get-FileHash -LiteralPath $Checkpoint -Algorithm SHA256).Hash

python -m investment_terminal.cli.weekly_stored_cohorts `
    --manifest $Manifest --manifest-checksum $ManifestChecksum `
    --source-checkpoint-directory $SourceDirectory `
    --weekly-checkpoint $Checkpoint --database $Database `
    --history-start $Start --report-output $Report
$CommandExit = $LASTEXITCODE
if (-not (Test-Path -LiteralPath $Report -PathType Leaf)) {
    throw "No cohort report was produced; do not rerun"
}
Write-Host "SEND: $Report"
Write-Host "Report SHA-256: $((Get-FileHash -LiteralPath $Report -Algorithm SHA256).Hash.ToLowerInvariant())"
Write-Host "DO NOT SEND: $Profile"
Write-Host "DO NOT SEND: $Manifest"
Write-Host "DO NOT SEND: $SourceDirectory"
Write-Host "DO NOT SEND: $Checkpoint"
Write-Host "DO NOT SEND: $Database"

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
if ($LASTEXITCODE -ne 0) { throw "SQLite integrity check failed; send the redacted report" }
if ((Get-FileHash -LiteralPath $Checkpoint -Algorithm SHA256).Hash -ne $CheckpointHashBefore) {
    throw "Private checkpoint changed during read-only scan; send the redacted report"
}

$ValidationCode = @'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if (report.get("schema_version") != 1
        or report.get("operation_identity") != "WEEKLY_STORED_COHORTS"
        or report.get("status") != "COMPLETE"
        or report.get("manifest_checksum") != "8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a"
        or report.get("selection_checksum") != "75d839c54ff43969832a4d1110deba538cd52793e9402db5cba2dc1decc6c5ae"
        or report.get("history_start") != "2016-09-29T00:00:00+00:00"
        or report.get("end") != "2026-09-29T00:00:00+00:00"
        or report.get("selected_series_count") != 11892):
    raise SystemExit("Cohort report binding mismatch")

def bins(name, keys):
    items = report.get(name)
    if not isinstance(items, list) or len(items) != len(keys):
        raise SystemExit("Cohort bin shape mismatch: " + name)
    result = {}
    for item in items:
        if not isinstance(item, dict) or set(item) != {"bucket", "count"}:
            raise SystemExit("Cohort bin item mismatch: " + name)
        key, count = item["bucket"], item["count"]
        if key in result or key not in keys or type(count) is not int or count < 0:
            raise SystemExit("Cohort bin value mismatch: " + name)
        result[key] = count
    if set(result) != set(keys) or sum(result.values()) != 11892:
        raise SystemExit("Cohort bin total mismatch: " + name)
    return result

ages = bins("first_observation_age_bins", {
    "WITHIN_7_DAYS", "OVER_7_TO_30_DAYS", "OVER_30_TO_365_DAYS",
    "AFTER_365_DAYS", "NO_ROWS",
})
endpoints = bins("endpoint_proxy_bins", {"BOTH", "START_ONLY", "END_ONLY", "NEITHER"})
gaps = bins("largest_observed_gap_bins", {
    "NO_GAP_OVER_7_DAYS", "GAP_OVER_7_TO_30_DAYS", "GAP_OVER_30_DAYS",
})
if (ages["WITHIN_7_DAYS"] != 4461 or ages["NO_ROWS"] != 0
        or endpoints != {"BOTH": 4449, "START_ONLY": 12,
                         "END_ONLY": 7338, "NEITHER": 93}
        or gaps != {"NO_GAP_OVER_7_DAYS": 11851,
                    "GAP_OVER_7_TO_30_DAYS": 16, "GAP_OVER_30_DAYS": 25}):
    raise SystemExit("Cohort aggregates differ from the stored-coverage report")
expected = {"SUCCESS": 11805, "NO_PRICE_DATA": 45,
            "RESPONSE_NUMERIC": 1, "STORED_CANDLE_DRIFT": 41}
items = report.get("weekly_outcome_intersections")
if not isinstance(items, list) or len(items) != len(expected):
    raise SystemExit("Weekly intersection shape mismatch")
seen = {}
for item in items:
    if not isinstance(item, dict) or set(item) != {
            "category", "count", "missing_start_proxy_count",
            "missing_end_proxy_count", "gap_over_7_days_count"}:
        raise SystemExit("Weekly intersection item mismatch")
    category = item["category"]
    count = item["count"]
    if category in seen or category not in expected or type(count) is not int or count != expected[category]:
        raise SystemExit("Weekly intersection category/count mismatch")
    for key in ("missing_start_proxy_count", "missing_end_proxy_count",
                "gap_over_7_days_count"):
        if type(item[key]) is not int or not 0 <= item[key] <= count:
            raise SystemExit("Weekly intersection value mismatch")
    seen[category] = item
if set(seen) != set(expected):
    raise SystemExit("Weekly intersection coverage mismatch")
if (sum(item["missing_start_proxy_count"] for item in items) != 7431
        or sum(item["missing_end_proxy_count"] for item in items) != 105
        or sum(item["gap_over_7_days_count"] for item in items) != 41):
    raise SystemExit("Weekly intersections do not reconcile")
print("Read-only cohort qualification: PASSED")
'@
$ValidationCode | python - $Report
if ($LASTEXITCODE -ne 0) { throw "Cohort validation failed; send the redacted report" }
if ($CommandExit -ne 0) { throw "Cohort scan failed; send the redacted report" }
```

Return only the redacted cohort report, its SHA-256, and `SQLite integrity:
ok`. Do not send the private manifest, source/weekly checkpoints, profile,
or database. If any validation fails, do not rerun automatically. Observed
first-candle age is not listing age; calendar-day gaps do not prove missing
exchange sessions or indicator-readiness defects.
