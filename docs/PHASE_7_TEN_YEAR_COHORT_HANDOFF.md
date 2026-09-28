# Phase 7 — observed-history cohort operational handoff

Classification: `OPERATIONAL — READY FOR USER EXECUTION`.

Fresh clean `develop` matched the exact caller-supplied GitHub baseline
`bc90efe5976138a6d4690c004713f86064ab0f77`. This package changes no
application code and does not inspect or mutate private runtime inputs. It
prepares one read-only, aggregate `WEEKLY_STORED_COHORTS` report for the same
half-open ten-year window as the completed span audit. Run the ASCII-only
PowerShell block below on the Desktop repository **before applying this
documentation ZIP**. Stop any candle-ingestion job during the scan. It makes
no Yahoo request and does not alter the database or checkpoints.

```powershell
$ErrorActionPreference = "Stop"
$Repository = "C:\Users\tu\Desktop\InvestmentTerminal"
$ExpectedHead = "bc90efe5976138a6d4690c004713f86064ab0f77"
$DataRoot = "C:\runtime\data"
$Manifest = "C:\runtime\data\market_batch_manifest_10y.json"
$Database = "C:\runtime\data\investment_terminal.db"
$WeeklyCheckpoint = "C:\runtime\data\weekly_candle_refresh_2026-09-23.json"
$Report = "C:\runtime\reports\weekly_stored_cohorts_20160923_20260923_001.json"
$ManifestChecksum = "8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a"
$Batch576Checksum = "0b025a4862ff8e26cb00cbfc11f242227478a78e8385a82d4671a7543edd6fcb"

Set-Location -LiteralPath $Repository
if ((git branch --show-current).Trim() -ne "develop") { throw "Branch mismatch" }
if ((git rev-parse HEAD).Trim() -ne $ExpectedHead) { throw "HEAD mismatch" }
if (@(git status --porcelain).Count -ne 0) { throw "Working tree is not clean" }
foreach ($RequiredPath in @($Manifest, $Database, $WeeklyCheckpoint)) {
    if (-not (Test-Path -LiteralPath $RequiredPath -PathType Leaf)) {
        throw "Required private input is missing: $RequiredPath"
    }
}
if (Test-Path -LiteralPath $Report) { throw "Report already exists" }

$SourceMatches = @()
foreach ($Candidate in @(Get-ChildItem -LiteralPath $DataRoot -Recurse -File -Filter "batch_0576.json")) {
    try {
        $Value = Get-Content -LiteralPath $Candidate.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch { continue }
    if ([string]$Value.request_checksum -eq $Batch576Checksum) {
        $SourceMatches += [System.IO.Path]::GetDirectoryName($Candidate.FullName)
    }
}
$SourceMatches = @($SourceMatches | Sort-Object -Unique)
if ($SourceMatches.Count -ne 1) { throw "Could not uniquely identify source checkpoints" }
$SourceDirectory = [string]$SourceMatches[0]
for ($Index = 1; $Index -le 601; $Index++) {
    $CheckpointPath = Join-Path $SourceDirectory ("batch_{0:D4}.json" -f $Index)
    if (-not (Test-Path -LiteralPath $CheckpointPath -PathType Leaf)) {
        throw "Source checkpoints are incomplete"
    }
}

New-Item -ItemType Directory -Force -Path "C:\runtime\reports" | Out-Null
Write-Host "Starting read-only cohort scan; this may take several minutes."
python -m investment_terminal.cli.weekly_stored_cohorts `
    --manifest $Manifest --manifest-checksum $ManifestChecksum `
    --source-checkpoint-directory $SourceDirectory `
    --weekly-checkpoint $WeeklyCheckpoint --database $Database `
    --history-start "2016-09-23T00:00:00+00:00" `
    --report-output $Report
$CommandExit = $LASTEXITCODE
if (-not (Test-Path -LiteralPath $Report -PathType Leaf)) {
    throw "No cohort report was produced"
}
Write-Host "SEND: $Report"
Write-Host "DO NOT SEND: $Manifest"
Write-Host "DO NOT SEND: $SourceDirectory"
Write-Host "DO NOT SEND: $WeeklyCheckpoint"
Write-Host "DO NOT SEND: $Database"
if ($CommandExit -ne 0) {
    throw "Cohort scan failed; send the redacted report and do not rerun"
}

$ValidationCode = @'
import json
import sqlite3
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
database = Path(sys.argv[2])
expected_manifest = sys.argv[3]
if (report.get("schema_version") != 1 or
        report.get("operation_identity") != "WEEKLY_STORED_COHORTS" or
        report.get("status") != "COMPLETE" or
        report.get("manifest_checksum") != expected_manifest or
        report.get("selection_checksum") != "75d839c54ff43969832a4d1110deba538cd52793e9402db5cba2dc1decc6c5ae" or
        report.get("history_start") != "2016-09-23T00:00:00+00:00" or
        report.get("end") != "2026-09-23T00:00:00+00:00" or
        report.get("selected_series_count") != 11892):
    raise SystemExit("Cohort report status or binding mismatch")

def bins(name, expected_keys):
    items = report.get(name)
    if not isinstance(items, list) or len(items) != len(expected_keys):
        raise SystemExit("Cohort bin shape mismatch: " + name)
    result = {}
    for item in items:
        if not isinstance(item, dict) or set(item) != {"bucket", "count"}:
            raise SystemExit("Cohort bin item mismatch: " + name)
        key, count = item["bucket"], item["count"]
        if key in result or key not in expected_keys or type(count) is not int or count < 0:
            raise SystemExit("Cohort bin value mismatch: " + name)
        result[key] = count
    if set(result) != set(expected_keys) or sum(result.values()) != 11892:
        raise SystemExit("Cohort bin total mismatch: " + name)
    return result

ages = bins("first_observation_age_bins", {
    "WITHIN_7_DAYS", "OVER_7_TO_30_DAYS", "OVER_30_TO_365_DAYS",
    "AFTER_365_DAYS", "NO_ROWS",
})
endpoints = bins("endpoint_proxy_bins", {
    "BOTH", "START_ONLY", "END_ONLY", "NEITHER",
})
gaps = bins("largest_observed_gap_bins", {
    "NO_GAP_OVER_7_DAYS", "GAP_OVER_7_TO_30_DAYS", "GAP_OVER_30_DAYS",
})
if (ages["WITHIN_7_DAYS"] != 4457 or ages["NO_ROWS"] != 0 or
        endpoints != {"BOTH": 4410, "START_ONLY": 47,
                      "END_ONLY": 7237, "NEITHER": 198} or
        gaps != {"NO_GAP_OVER_7_DAYS": 11856,
                 "GAP_OVER_7_TO_30_DAYS": 12, "GAP_OVER_30_DAYS": 24}):
    raise SystemExit("Cohort aggregates differ from the prior span report")

items = report.get("weekly_outcome_intersections")
expected = {"SUCCESS": 11678, "NO_PRICE_DATA": 42,
            "RESPONSE_NUMERIC": 140, "STORED_CANDLE_DRIFT": 32}
if not isinstance(items, list) or len(items) != len(expected):
    raise SystemExit("Weekly intersection shape mismatch")
seen = {}
for item in items:
    if not isinstance(item, dict) or set(item) != {
            "category", "count", "missing_start_proxy_count",
            "missing_end_proxy_count", "gap_over_7_days_count"}:
        raise SystemExit("Weekly intersection item mismatch")
    category = item["category"]
    if category in seen or category not in expected:
        raise SystemExit("Weekly intersection category mismatch")
    count = item["count"]
    if type(count) is not int or count != expected[category]:
        raise SystemExit("Weekly intersection count mismatch")
    for key in ("missing_start_proxy_count", "missing_end_proxy_count",
                "gap_over_7_days_count"):
        if type(item[key]) is not int or not 0 <= item[key] <= count:
            raise SystemExit("Weekly intersection value mismatch")
    seen[category] = item
if set(seen) != set(expected):
    raise SystemExit("Weekly intersection coverage mismatch")
if (sum(item["missing_start_proxy_count"] for item in items) != 7435 or
        sum(item["missing_end_proxy_count"] for item in items) != 245 or
        sum(item["gap_over_7_days_count"] for item in items) != 36):
    raise SystemExit("Weekly intersections do not reconcile")

connection = sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)
try:
    connection.execute("PRAGMA query_only = ON")
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
finally:
    connection.close()
if integrity != "ok":
    raise SystemExit("SQLite integrity check failed")
print("SQLite integrity: ok")
'@
$ValidationCode | python - $Report $Database $ManifestChecksum
if ($LASTEXITCODE -ne 0) { throw "Cohort report or SQLite validation failed; do not rerun" }
Write-Host "Report SHA-256: $((Get-FileHash -LiteralPath $Report -Algorithm SHA256).Hash.ToLowerInvariant())"
```

Return only the redacted report and `SQLite integrity: ok` line. The source
manifest, 601 checkpoints, weekly checkpoint, and SQLite database remain
private. If validation differs from the earlier span report, send the redacted
result without repeating or repairing anything. The bins describe candle
timestamps, not download dates, listing ages, or exchange-session completeness.
