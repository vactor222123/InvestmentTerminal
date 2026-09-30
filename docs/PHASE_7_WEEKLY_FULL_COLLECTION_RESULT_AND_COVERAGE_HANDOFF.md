# Phase 7 — completed weekly collection and stored-coverage handoff

Classification: `OPERATIONAL — READY FOR USER EXECUTION`.

Fresh clean GitHub `develop` matched caller baseline
`9fb52e3942df0e068ec081c089b2d28b9cce075f`. The returned redacted
slice-003 report has SHA-256
`94889176b51d0ed147fcf5d8845f72a76f338e8ae3e28769e2668e9a3e101303`.
For exclusive end `2026-09-29T00:00:00+00:00`, it records
`COMPLETE_WITH_FAILURES`: all 11,892 selected series have an outcome, zero
remain, 11,805 succeeded, and 87 failed (45 `NO_PRICE_DATA`, one
`RESPONSE_NUMERIC`, 41 `STORED_CANDLE_DRIFT`). The full-remaining invocation
attempted 11,791 series in 1,641.480055 seconds; its cumulative transfer
counts are 120,273 downloaded, 49,540 inserted, 70,733 duplicates, and one
omitted trailing candle. The user independently reported `SQLite integrity:
ok`.

The first handoff block stopped in PowerShell preflight with an ambiguous
`[int]` conversion of a property collection; the target coverage report was
absent and the scan had not started. This corrected block performs numeric
and checkpoint-count checks in Python before the CLI invocation.

This proves completion of the **attempted collection pass**, not that every
series is complete, fresh, or indicator-ready. In particular, the reported
10,206 `indicator_200_ready_count` proves only stored sample size among
successful/empty outcomes; it does not prove exchange-session coverage or
valid 200-day indicators. Do not retry the 87 failures or enable a scheduler
from this aggregate report. The next smallest safe step is one read-only
`WEEKLY_STORED_COVERAGE` schema-2 scan over the explicit ten-year window
`2016-09-29T00:00:00+00:00` to `2026-09-29T00:00:00+00:00`. This measures
stored rows, sample-size bins, seven-calendar-day endpoint proxies, and
large observed gaps against the complete weekly checkpoint. It makes no
Yahoo request, candle write, or checkpoint change. The window differs from
the earlier 2016-09-23 to 2026-09-23 report; do not compare raw totals as
if the windows were identical.

Run this ASCII-only PowerShell block on the Desktop repository **before
applying this ZIP**. Pause other candle jobs during the scan. Return only
the generated redacted report, its SHA-256, and the independent SQLite
integrity line.

```powershell
$ErrorActionPreference = "Stop"
$Repository = "C:\Users\tu\Desktop\InvestmentTerminal"
$ExpectedHead = "9fb52e3942df0e068ec081c089b2d28b9cce075f"
$Profile = "C:\runtime\data\weekly_run_profile.json"
$Checkpoint = "C:\runtime\data\weekly_run\weekly_candle_refresh_2026-09-29.json"
$Database = "C:\runtime\data\investment_terminal.db"
$PreviousReport = "C:\runtime\reports\weekly_candle_refresh_2026-09-29_003.json"
$PreviousSha256 = "94889176b51d0ed147fcf5d8845f72a76f338e8ae3e28769e2668e9a3e101303"
$Report = "C:\runtime\reports\weekly_stored_coverage_20160929_20260929_001.json"
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
if (Test-Path -LiteralPath $Report) { throw "Coverage report already exists" }
if ((Get-FileHash -LiteralPath $PreviousReport -Algorithm SHA256).Hash.ToLowerInvariant() -ne $PreviousSha256) {
    throw "Completed-run report checksum mismatch"
}
$PreflightCode = @'
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from investment_terminal.cli.weekly_run import _profile
from investment_terminal.operations.weekly_candle_refresh import WeeklyCandleRefreshPlan, _validated_outcomes

profile_path, checkpoint_path, database_path, previous_path = map(Path, sys.argv[1:5])
end = datetime.fromisoformat(sys.argv[5])
profile, paths = _profile(profile_path)
if (profile["manifest_checksum"] != "8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a"
        or paths["database"] != database_path.resolve()
        or paths["weekly_checkpoint_directory"] / checkpoint_path.name != checkpoint_path.resolve()):
    raise SystemExit("Private profile binding mismatch")
completed = json.loads(previous_path.read_text(encoding="utf-8"))
coverage = completed.get("coverage")
if (completed.get("status") != "COMPLETE_WITH_FAILURES"
        or completed.get("manifest_checksum") != profile["manifest_checksum"]
        or completed.get("selection_checksum") != "75d839c54ff43969832a4d1110deba538cd52793e9402db5cba2dc1decc6c5ae"
        or completed.get("end") != end.isoformat()
        or not isinstance(coverage, dict)
        or coverage.get("selected_count") != 11892
        or coverage.get("completed_count") != 11892
        or coverage.get("remaining_count") != 0
        or coverage.get("success_count") != 11805
        or coverage.get("empty_count") != 0
        or coverage.get("failure_count") != 87):
    raise SystemExit("Completed report binding mismatch")
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
statuses = Counter(value["status"] for value in outcomes.values())
categories = Counter(value["category"] for value in outcomes.values()
                     if value["status"] == "FAILED")
if (len(plan.items) != 11892
        or plan.excluded_count != 127
        or plan.selection_checksum != completed["selection_checksum"]
        or len(outcomes) != 11892
        or statuses != {"SUCCESS": 11805, "FAILED": 87}
        or categories != {"NO_PRICE_DATA": 45, "RESPONSE_NUMERIC": 1,
                          "STORED_CANDLE_DRIFT": 41}):
    raise SystemExit("Private checkpoint does not match completed report")
print("Completed report, private profile and checkpoint: PASSED")
'@
$PreflightCode | python - $Profile $Checkpoint $Database $PreviousReport $End
if ($LASTEXITCODE -ne 0) { throw "Preflight failed; do not run coverage scan" }
$PrivateProfile = Get-Content -LiteralPath $Profile -Raw -Encoding UTF8 | ConvertFrom-Json
$Manifest = [string]$PrivateProfile.manifest
$SourceDirectory = [string]$PrivateProfile.source_checkpoint_directory
if (-not (Test-Path -LiteralPath $Manifest -PathType Leaf) -or
    -not (Test-Path -LiteralPath $SourceDirectory -PathType Container)) {
    throw "Manifest or source checkpoint directory is missing"
}
$CheckpointHashBefore = (Get-FileHash -LiteralPath $Checkpoint -Algorithm SHA256).Hash

python -m investment_terminal.cli.weekly_stored_coverage `
    --manifest $Manifest --manifest-checksum $ManifestChecksum `
    --source-checkpoint-directory $SourceDirectory `
    --weekly-checkpoint $Checkpoint --database $Database `
    --history-start $Start --report-output $Report
$CommandExit = $LASTEXITCODE
if (-not (Test-Path -LiteralPath $Report -PathType Leaf)) {
    throw "No coverage report was produced; do not rerun"
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
if (report.get("schema_version") != 2
        or report.get("operation_identity") != "WEEKLY_STORED_COVERAGE"
        or report.get("status") != "COMPLETE"
        or report.get("manifest_checksum") != "8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a"
        or report.get("selection_checksum") != "75d839c54ff43969832a4d1110deba538cd52793e9402db5cba2dc1decc6c5ae"
        or report.get("history_start") != "2016-09-29T00:00:00+00:00"
        or report.get("end") != "2026-09-29T00:00:00+00:00"):
    raise SystemExit("Coverage report binding mismatch")
coverage = report.get("coverage")
if not isinstance(coverage, dict):
    raise SystemExit("Coverage aggregate is missing")
if (coverage.get("selected_series_count") != 11892
        or coverage.get("source_excluded_count") != 127
        or coverage.get("weekly_success_count") != 11805
        or coverage.get("weekly_empty_count") != 0
        or coverage.get("weekly_failure_count") != 87
        or sum(coverage.get(key, 0) for key in (
            "zero_count", "one_to_49_count", "50_to_199_count", "200_plus_count")) != 11892
        or coverage.get("sample_200_ready_count") != coverage.get("200_plus_count")
        or coverage.get("sample_50_ready_count") != coverage.get("50_to_199_count", 0) + coverage.get("200_plus_count", 0)):
    raise SystemExit("Coverage aggregate does not reconcile")
categories = {item["category"]: item["count"] for item in report.get("weekly_failure_categories", [])}
if categories != {"NO_PRICE_DATA": 45, "RESPONSE_NUMERIC": 1, "STORED_CANDLE_DRIFT": 41}:
    raise SystemExit("Coverage failure categories do not reconcile")
print("Read-only stored-coverage qualification: PASSED")
'@
$ValidationCode | python - $Report
if ($LASTEXITCODE -ne 0) { throw "Coverage validation failed; send the redacted report" }
if ($CommandExit -ne 0) { throw "Coverage scan failed; send the redacted report" }
```

Only the redacted report, its hash, and the `SQLite integrity: ok` line are
shareable here. If validation fails, do not rerun automatically. This
measurement is observational: late listings, holidays, and delistings can
affect endpoint/gap proxies, and it does not identify which candles to
repair or authorize a scheduler.
