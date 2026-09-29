# Phase 7 — weekly stale-success/gap operational handoff

Classification: `OPERATIONAL — READY FOR USER EXECUTION`.

Fresh clean `develop` matched the exact caller-supplied baseline
`1deeefa785a85b845650a6ca94d68a58e67edcc8`. This documentation-only
package does not access private runtime data. Run the following ASCII-only
PowerShell block on the Desktop repository **before applying this ZIP**.
Pause any candle-ingestion job during the read-only SQLite scan. The command
does not contact Yahoo or change the database or checkpoints.

```powershell
$ErrorActionPreference = "Stop"
$Repository = "C:\Users\tu\Desktop\InvestmentTerminal"
$ExpectedHead = "1deeefa785a85b845650a6ca94d68a58e67edcc8"
$DataRoot = "C:\runtime\data"
$Manifest = "C:\runtime\data\market_batch_manifest_10y.json"
$Database = "C:\runtime\data\investment_terminal.db"
$WeeklyCheckpoint = "C:\runtime\data\weekly_candle_refresh_2026-09-23.json"
$Report = "C:\runtime\reports\weekly_stale_gap_diagnostic_20160923_20260923_001.json"
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
Write-Host "Starting read-only stale-gap scan; this may take several minutes."
python -m investment_terminal.cli.weekly_stale_gap_diagnostic `
    --manifest $Manifest --manifest-checksum $ManifestChecksum `
    --source-checkpoint-directory $SourceDirectory `
    --weekly-checkpoint $WeeklyCheckpoint --database $Database `
    --history-start "2016-09-23T00:00:00+00:00" `
    --report-output $Report
$CommandExit = $LASTEXITCODE
if (-not (Test-Path -LiteralPath $Report -PathType Leaf)) {
    throw "No stale-gap report was produced"
}
Write-Host "SEND: $Report"
Write-Host "DO NOT SEND: $Manifest"
Write-Host "DO NOT SEND: $SourceDirectory"
Write-Host "DO NOT SEND: $WeeklyCheckpoint"
Write-Host "DO NOT SEND: $Database"
if ($CommandExit -ne 0) {
    throw "Stale-gap scan failed; send the redacted report and do not rerun"
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
        report.get("operation_identity") != "WEEKLY_STALE_GAP_DIAGNOSTIC" or
        report.get("status") != "COMPLETE" or
        report.get("manifest_checksum") != expected_manifest or
        report.get("selection_checksum") != "75d839c54ff43969832a4d1110deba538cd52793e9402db5cba2dc1decc6c5ae" or
        report.get("history_start") != "2016-09-23T00:00:00+00:00" or
        report.get("end") != "2026-09-23T00:00:00+00:00" or
        report.get("selected_series_count") != 11892 or
        report.get("failure") is not None):
    raise SystemExit("Stale-gap report status or binding mismatch")

def count(name, expected):
    value = report.get(name)
    if type(value) is not int or value != expected:
        raise SystemExit("Stale-gap count mismatch: " + name)
    return value

stale = count("stale_success_count", 31)
gap = count("long_gap_success_count", 36)
intersection = report.get("intersection_count")
union = report.get("union_count")
if (type(intersection) is not int or not 0 <= intersection <= 31 or
        type(union) is not int or union != stale + gap - intersection):
    raise SystemExit("Stale-gap intersection or union mismatch")

def bins(name, keys, total):
    items = report.get(name)
    if not isinstance(items, list) or len(items) != len(keys):
        raise SystemExit("Stale-gap bin shape mismatch: " + name)
    result = {}
    for item in items:
        if not isinstance(item, dict) or set(item) != {"bucket", "count"}:
            raise SystemExit("Stale-gap bin item mismatch: " + name)
        key, value = item["bucket"], item["count"]
        if key in result or key not in keys or type(value) is not int or value < 0:
            raise SystemExit("Stale-gap bin value mismatch: " + name)
        result[key] = value
    if set(result) != set(keys) or sum(result.values()) != total:
        raise SystemExit("Stale-gap bin total mismatch: " + name)
    return result

bins("staleness_bins", {
    "OVER_7_TO_14_DAYS", "OVER_14_TO_30_DAYS", "OVER_30_TO_90_DAYS",
    "OVER_90_DAYS", "NO_WINDOW_ROWS",
}, stale)
gaps = bins("largest_gap_bins", {
    "OVER_7_TO_30_DAYS", "OVER_30_TO_90_DAYS", "OVER_90_DAYS",
}, gap)
if gaps["OVER_7_TO_30_DAYS"] != 12:
    raise SystemExit("Stale-gap bins differ from prior cohort evidence")

fields = {"group", "series_count", "downloaded_total", "inserted_total",
          "duplicate_total", "omitted_trailing_total"}
groups = report.get("disjoint_groups")
if not isinstance(groups, list) or len(groups) != 3:
    raise SystemExit("Stale-gap group shape mismatch")
seen = {}
for item in groups:
    if not isinstance(item, dict) or set(item) != fields:
        raise SystemExit("Stale-gap group item mismatch")
    key = item["group"]
    if key in seen or key not in {"STALE_ONLY", "GAP_ONLY", "BOTH"}:
        raise SystemExit("Stale-gap group key mismatch")
    for field in fields - {"group"}:
        if type(item[field]) is not int or item[field] < 0:
            raise SystemExit("Stale-gap group value mismatch")
    if (item["inserted_total"] + item["duplicate_total"] != item["downloaded_total"] or
            item["omitted_trailing_total"] > item["series_count"]):
        raise SystemExit("Stale-gap transfer accounting mismatch")
    seen[key] = item
if set(seen) != {"STALE_ONLY", "GAP_ONLY", "BOTH"}:
    raise SystemExit("Stale-gap group coverage mismatch")
if (seen["STALE_ONLY"]["series_count"] + seen["BOTH"]["series_count"] != stale or
        seen["GAP_ONLY"]["series_count"] + seen["BOTH"]["series_count"] != gap or
        seen["BOTH"]["series_count"] != intersection or
        sum(item["series_count"] for item in groups) != union):
    raise SystemExit("Stale-gap group totals do not reconcile")

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
if ($LASTEXITCODE -ne 0) { throw "Stale-gap report or SQLite validation failed; do not rerun" }
Write-Host "Report SHA-256: $((Get-FileHash -LiteralPath $Report -Algorithm SHA256).Hash.ToLowerInvariant())"
```

Return only the redacted report and `SQLite integrity: ok` line. If any
validation fails, send the redacted report without rerunning or repairing.
These are calendar-day observations, not proof of missing trading sessions;
do not retry, backfill, change weekly `SUCCESS`, or schedule refreshes from
this result alone.
