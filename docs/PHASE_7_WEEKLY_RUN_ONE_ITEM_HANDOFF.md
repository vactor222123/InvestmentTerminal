# Phase 7 — profile bootstrap and one-item weekly-run handoff

Classification: `OPERATIONAL — READY FOR USER EXECUTION`.

Fresh clean GitHub `develop` matched the caller baseline
`f817a22c6ce2b5f82e8609c3d947426d276012a2`. This documentation-only
package does not inspect or modify private runtime inputs. Run the ASCII-only
PowerShell block below on the Desktop repository **before applying this ZIP**.
Pause any other candle job. It creates one private runtime profile from the
verified manifest/source evidence, then asks Yahoo for at most one selected
daily series through the existing weekly service. It does not schedule,
retry, backfill, or run the remaining universe.

```powershell
$ErrorActionPreference = "Stop"
$Repository = "C:\Users\tu\Desktop\InvestmentTerminal"
$ExpectedHead = "f817a22c6ce2b5f82e8609c3d947426d276012a2"
$DataRoot = "C:\runtime\data"
$Manifest = "C:\runtime\data\market_batch_manifest_10y.json"
$ManifestChecksum = "8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a"
$Batch576Checksum = "0b025a4862ff8e26cb00cbfc11f242227478a78e8385a82d4671a7543edd6fcb"
$Database = "C:\runtime\data\investment_terminal.db"
$Cache = "C:\runtime\cache\yfinance"
$Profile = "C:\runtime\data\weekly_run_profile.json"
$Checkpoint = "C:\runtime\data\weekly_run\weekly_candle_refresh_2026-09-29.json"
$Report = "C:\runtime\reports\weekly_candle_refresh_2026-09-29_001.json"
$End = "2026-09-29T00:00:00+00:00"

Set-Location -LiteralPath $Repository
if ((git branch --show-current).Trim() -ne "develop") { throw "Branch mismatch" }
if ((git rev-parse HEAD).Trim() -ne $ExpectedHead) { throw "HEAD mismatch" }
if (@(git status --porcelain).Count -ne 0) { throw "Working tree is not clean" }
foreach ($RequiredPath in @($Manifest, $Database)) {
    if (-not (Test-Path -LiteralPath $RequiredPath -PathType Leaf)) {
        throw "Required private input is missing: $RequiredPath"
    }
}
if (Test-Path -LiteralPath $Profile) { throw "Private profile already exists" }
if (Test-Path -LiteralPath $Checkpoint) { throw "New-end checkpoint already exists" }
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
    $SourcePath = Join-Path $SourceDirectory ("batch_{0:D4}.json" -f $Index)
    if (-not (Test-Path -LiteralPath $SourcePath -PathType Leaf)) {
        throw "Source checkpoints are incomplete"
    }
}

$BootstrapCode = @'
import json
import sys
from datetime import datetime
from pathlib import Path
from investment_terminal.operations.weekly_candle_refresh import WeeklyCandleRefreshPlan
from investment_terminal.utils.atomic_write import write_json_atomic

manifest_path = Path(sys.argv[1])
checksum = sys.argv[2]
source_dir = Path(sys.argv[3])
database_path = Path(sys.argv[4])
cache_dir = Path(sys.argv[5])
profile_path = Path(sys.argv[6])
end = datetime.fromisoformat(sys.argv[7])
if profile_path.exists():
    raise SystemExit("Private profile already exists")
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

def source(index):
    path = source_dir / f"batch_{index:04d}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

plan = WeeklyCandleRefreshPlan.from_manifest(manifest, checksum, source, end=end)
if (len(plan.items) != 11892 or
        plan.selection_checksum != "75d839c54ff43969832a4d1110deba538cd52793e9402db5cba2dc1decc6c5ae"):
    raise SystemExit("Selected series do not match prior verified evidence")
profile = {
    "schema_version": 1,
    "operation_identity": "WEEKLY_RUN_PROFILE",
    "manifest": str(manifest_path),
    "manifest_checksum": checksum,
    "source_checkpoint_directory": str(source_dir),
    "database": str(database_path),
    "cache_directory": str(cache_dir),
    "weekly_checkpoint_directory": r"C:\runtime\data\weekly_run",
    "report_directory": r"C:\runtime\reports",
}
write_json_atomic(profile_path, profile)
print("Private weekly profile created from verified source evidence")
'@
$BootstrapCode | python - $Manifest $ManifestChecksum $SourceDirectory $Database $Cache $Profile $End
if ($LASTEXITCODE -ne 0) { throw "Profile bootstrap failed; do not run the weekly slice" }

New-Item -ItemType Directory -Force -Path $Cache, "C:\runtime\reports" | Out-Null
python -m investment_terminal.cli.weekly_run `
    --profile $Profile --end $End --max-items 1 --slice-id 001
$CommandExit = $LASTEXITCODE
if (-not (Test-Path -LiteralPath $Report -PathType Leaf)) {
    throw "No weekly report was produced; do not rerun"
}
Write-Host "SEND: $Report"
Write-Host "DO NOT SEND: $Profile"
Write-Host "DO NOT SEND: $Manifest"
Write-Host "DO NOT SEND: $SourceDirectory"
Write-Host "DO NOT SEND: $Checkpoint"
Write-Host "DO NOT SEND: $Database"
Write-Host "DO NOT SEND: $Cache"

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
if ($CommandExit -ne 0) { throw "Weekly slice did not complete normally; send the redacted report" }

$ValidationCode = @'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
coverage = report.get("coverage")
if (report.get("schema_version") != 1 or
        report.get("operation_identity") != "WEEKLY_CANDLE_REFRESH" or
        report.get("status") != "BUDGET_EXHAUSTED" or
        report.get("manifest_checksum") != "8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a" or
        report.get("selection_checksum") != "75d839c54ff43969832a4d1110deba538cd52793e9402db5cba2dc1decc6c5ae" or
        report.get("end") != "2026-09-29T00:00:00+00:00" or
        report.get("budget") != {"max_items": 1} or
        not isinstance(coverage, dict) or
        coverage.get("selected_count") != 11892 or
        coverage.get("completed_count") != 1 or
        coverage.get("remaining_count") != 11891 or
        coverage.get("current_run_attempted_count") != 1 or
        coverage.get("failure_count") != 0 or
        coverage.get("success_count", 0) + coverage.get("empty_count", 0) != 1):
    raise SystemExit("Weekly one-item report requires review")
print("One-item weekly qualification: PASSED")
'@
$ValidationCode | python - $Report
if ($LASTEXITCODE -ne 0) { throw "Report validation failed; do not rerun" }
Write-Host "Report SHA-256: $((Get-FileHash -LiteralPath $Report -Algorithm SHA256).Hash.ToLowerInvariant())"
```

Return only the redacted report, the `SQLite integrity: ok` line, and the
report SHA-256. If any step fails after profile creation, do not rerun the
block automatically: the profile, checkpoint, and possibly some candles may
already exist. Send the redacted report if one exists and request a focused
resume instruction. Do not send private inputs or the profile. One successful
item does not qualify the remaining 11,891 or establish session completeness.
