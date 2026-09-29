# Phase 7 — first weekly-run continuation

Classification: `OPERATIONAL — READY FOR USER EXECUTION`.

Fresh clean GitHub `develop` matched caller baseline
`0362cf349eb0c9e8c26244f5b1dd663eff246c7f`. The returned schema-1
one-item report has SHA-256
`7f6ecf763cf05a7657d96b8c99acc30c8a68756494bffa41c70c720cba5f22eb`.
It is bound to manifest `8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a`,
selection `75d839c54ff43969832a4d1110deba538cd52793e9402db5cba2dc1decc6c5ae`,
and exclusive end `2026-09-29T00:00:00+00:00`. It records one success,
11 downloaded, five inserted, six duplicates, zero failures, and 11,891
remaining. The user independently reported `SQLite integrity: ok`.

This qualifies only the one-item execution path. The next bounded action is
one same-end `--max-items 100` slice, not a complete-universe run or a
scheduler. Run the ASCII-only PowerShell block below on the Desktop repository
**before applying this ZIP**, with no other candle job active. The block checks
the immutable previous report, the private profile and one-item checkpoint,
then uses the existing CLI to process at most 100 previously unattempted
series. It does not retry failed outcomes. The new report is separate and
cannot intentionally overwrite slice 001.

```powershell
$ErrorActionPreference = "Stop"
$Repository = "C:\Users\tu\Desktop\InvestmentTerminal"
$ExpectedHead = "0362cf349eb0c9e8c26244f5b1dd663eff246c7f"
$Profile = "C:\runtime\data\weekly_run_profile.json"
$Checkpoint = "C:\runtime\data\weekly_run\weekly_candle_refresh_2026-09-29.json"
$Database = "C:\runtime\data\investment_terminal.db"
$PreviousReport = "C:\runtime\reports\weekly_candle_refresh_2026-09-29_001.json"
$PreviousSha256 = "7f6ecf763cf05a7657d96b8c99acc30c8a68756494bffa41c70c720cba5f22eb"
$Report = "C:\runtime\reports\weekly_candle_refresh_2026-09-29_002.json"
$End = "2026-09-29T00:00:00+00:00"

Set-Location -LiteralPath $Repository
if ((git branch --show-current).Trim() -ne "develop") { throw "Branch mismatch" }
if ((git rev-parse HEAD).Trim() -ne $ExpectedHead) { throw "HEAD mismatch" }
if (@(git status --porcelain).Count -ne 0) { throw "Working tree is not clean" }
foreach ($RequiredPath in @($Profile, $Checkpoint, $Database, $PreviousReport)) {
    if (-not (Test-Path -LiteralPath $RequiredPath -PathType Leaf)) {
        throw "Required private input is missing: $RequiredPath"
    }
}
if (Test-Path -LiteralPath $Report) { throw "Slice 002 report already exists" }
if ((Get-FileHash -LiteralPath $PreviousReport -Algorithm SHA256).Hash.ToLowerInvariant() -ne $PreviousSha256) {
    throw "Previous report checksum mismatch"
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
        or paths["weekly_checkpoint_directory"] / checkpoint_path.name != checkpoint_path.resolve()
        or paths["report_directory"] / report_path.name != report_path.resolve()):
    raise SystemExit("Private profile binding mismatch")
manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
source_dir = paths["source_checkpoint_directory"]

def read_source(index):
    path = source_dir / f"batch_{index:04d}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

plan = WeeklyCandleRefreshPlan.from_manifest(
    manifest, profile["manifest_checksum"], read_source, end=end,
)
outcomes = _validated_outcomes(
    json.loads(checkpoint_path.read_text(encoding="utf-8")), plan,
)
if (len(plan.items) != 11892
        or plan.selection_checksum != "75d839c54ff43969832a4d1110deba538cd52793e9402db5cba2dc1decc6c5ae"
        or len(outcomes) != 1
        or outcomes.get(plan.items[0][0], {}).get("status") != "SUCCESS"):
    raise SystemExit("One-item checkpoint does not match prior report")
print("One-item checkpoint and profile binding: PASSED")
'@
$PreflightCode | python - $Profile $Checkpoint $Database $Report $End
if ($LASTEXITCODE -ne 0) { throw "Preflight failed; do not run slice 002" }

python -m investment_terminal.cli.weekly_run `
    --profile $Profile --end $End --max-items 100 --slice-id 002
$CommandExit = $LASTEXITCODE
if (-not (Test-Path -LiteralPath $Report -PathType Leaf)) {
    throw "No slice 002 report was produced; do not rerun"
}
Write-Host "SEND: $Report"
Write-Host "Report SHA-256: $((Get-FileHash -LiteralPath $Report -Algorithm SHA256).Hash.ToLowerInvariant())"
Write-Host "DO NOT SEND: $Profile"
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

$ValidationCode = @'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
coverage = report.get("coverage")
if (report.get("schema_version") != 1
        or report.get("operation_identity") != "WEEKLY_CANDLE_REFRESH"
        or report.get("provider_identity") != "YAHOO_FINANCE"
        or report.get("manifest_checksum") != "8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a"
        or report.get("selection_checksum") != "75d839c54ff43969832a4d1110deba538cd52793e9402db5cba2dc1decc6c5ae"
        or report.get("end") != "2026-09-29T00:00:00+00:00"
        or report.get("budget") != {"max_items": 100}
        or report.get("status") not in {"BUDGET_EXHAUSTED", "HALTED", "FAILED"}):
    raise SystemExit("Slice 002 report binding mismatch")
if report["status"] != "FAILED":
    if (not isinstance(coverage, dict)
            or coverage.get("selected_count") != 11892
            or coverage.get("source_excluded_count") != 127
            or not 1 <= coverage.get("current_run_attempted_count", 0) <= 100
            or coverage.get("completed_count") != 1 + coverage["current_run_attempted_count"]
            or coverage.get("remaining_count") != 11892 - coverage["completed_count"]
            or sum(coverage.get(key, 0) for key in ("success_count", "empty_count", "failure_count")) != coverage["completed_count"]):
        raise SystemExit("Slice 002 coverage requires review")
print("Slice 002 report binding: PASSED")
'@
$ValidationCode | python - $Report
if ($LASTEXITCODE -ne 0) { throw "Report validation failed; do not rerun" }
if ($CommandExit -ne 0) { throw "Slice 002 halted or failed; send the redacted report" }
```

Return only the redacted slice-002 report, its SHA-256, and the independent
`SQLite integrity: ok` line. If anything fails or the report contains isolated
series failures, do not rerun the block or advance to a broader run before
review. Do not send the private profile, checkpoints, source manifest, cache,
or database. One successful 100-item continuation still does not establish
freshness, trading-session completeness, or scheduler readiness.
