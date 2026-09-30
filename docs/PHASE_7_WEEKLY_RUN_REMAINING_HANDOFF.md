# Phase 7 — one full remaining weekly collection run

Classification: `OPERATIONAL — READY FOR USER EXECUTION`.

Fresh clean GitHub `develop` matched the caller's last exact baseline
`7c2ca38d44cfe24c0e0a612c7aa2e85e6867b930`; remote `develop` still
matches it. This handoff supersedes the unapplied 1000-item draft. The
returned redacted slice-002 report has SHA-256
`1ac08d20bb2bbe7003f8882acfa631de6f0b4027d2a6f5bf66e32c1141f94b2b`.
It records 101 completed of 11,892 selected series: 91 successes and 10
isolated failures (three `NO_PRICE_DATA`, seven `STORED_CANDLE_DRIFT`). The
user independently reported `SQLite integrity: ok`.

The existing ordinary `weekly_run` resumes the same-end private checkpoint,
skips all 101 prior outcomes, and attempts at most the 11,791 unattempted
series. It checkpoints each outcome. A rate limit halts the run; a persistence
or precondition failure also stops it. None of these cases authorizes an
automatic rerun. If all remaining series are attempted, the expected final
status is `COMPLETE_WITH_FAILURES`, and the CLI returns exit code 1 because
the 10 known failures remain. That status can mean collection coverage is
complete, but not that every series has acceptable candles or that a weekly
scheduler is ready.

Run this ASCII-only PowerShell block on the Desktop repository **before
applying this ZIP**, with no other candle job active. It verifies the
previous redacted report, private profile and checkpoint before contacting
Yahoo; uses a new non-overwriting slice-003 report; validates the resulting
report; and runs an independent read-only SQLite integrity check. The private
files and database must not be sent back.

```powershell
$ErrorActionPreference = "Stop"
$Repository = "C:\Users\tu\Desktop\InvestmentTerminal"
$ExpectedHead = "7c2ca38d44cfe24c0e0a612c7aa2e85e6867b930"
$Profile = "C:\runtime\data\weekly_run_profile.json"
$Checkpoint = "C:\runtime\data\weekly_run\weekly_candle_refresh_2026-09-29.json"
$Database = "C:\runtime\data\investment_terminal.db"
$PreviousReport = "C:\runtime\reports\weekly_candle_refresh_2026-09-29_002.json"
$PreviousSha256 = "1ac08d20bb2bbe7003f8882acfa631de6f0b4027d2a6f5bf66e32c1141f94b2b"
$Report = "C:\runtime\reports\weekly_candle_refresh_2026-09-29_003.json"
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
if (Test-Path -LiteralPath $Report) { throw "Slice 003 report already exists" }
if ((Get-FileHash -LiteralPath $PreviousReport -Algorithm SHA256).Hash.ToLowerInvariant() -ne $PreviousSha256) {
    throw "Previous report checksum mismatch"
}

$PreflightCode = @'
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from investment_terminal.cli.weekly_run import _profile
from investment_terminal.operations.weekly_candle_refresh import WeeklyCandleRefreshPlan, _validated_outcomes

profile_path, checkpoint_path, database_path, report_path, previous_path = map(Path, sys.argv[1:6])
end = datetime.fromisoformat(sys.argv[6])
profile, paths = _profile(profile_path)
if (profile["manifest_checksum"] != "8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a"
        or paths["database"] != database_path.resolve()
        or paths["weekly_checkpoint_directory"] / checkpoint_path.name != checkpoint_path.resolve()
        or paths["report_directory"] / report_path.name != report_path.resolve()):
    raise SystemExit("Private profile binding mismatch")
previous = json.loads(previous_path.read_text(encoding="utf-8"))
coverage = previous.get("coverage")
if (previous.get("status") != "BUDGET_EXHAUSTED"
        or previous.get("manifest_checksum") != profile["manifest_checksum"]
        or previous.get("selection_checksum") != "75d839c54ff43969832a4d1110deba538cd52793e9402db5cba2dc1decc6c5ae"
        or previous.get("end") != end.isoformat()
        or previous.get("budget") != {"max_items": 100}
        or not isinstance(coverage, dict)
        or coverage.get("completed_count") != 101
        or coverage.get("remaining_count") != 11791
        or coverage.get("success_count") != 91
        or coverage.get("failure_count") != 10):
    raise SystemExit("Previous report binding mismatch")
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
statuses = Counter(value["status"] for value in outcomes.values())
categories = Counter(value["category"] for value in outcomes.values() if value["status"] == "FAILED")
if (len(plan.items) != 11892
        or plan.excluded_count != 127
        or plan.selection_checksum != previous["selection_checksum"]
        or len(outcomes) != 101
        or statuses != {"SUCCESS": 91, "FAILED": 10}
        or categories != {"NO_PRICE_DATA": 3, "STORED_CANDLE_DRIFT": 7}):
    raise SystemExit("Private checkpoint does not match the returned report")
print("Previous report, profile and checkpoint: PASSED")
'@
$PreflightCode | python - $Profile $Checkpoint $Database $Report $PreviousReport $End
if ($LASTEXITCODE -ne 0) { throw "Preflight failed; do not run collection" }

python -m investment_terminal.cli.weekly_run `
    --profile $Profile --end $End --max-items 11791 --slice-id 003
$CommandExit = $LASTEXITCODE
if (-not (Test-Path -LiteralPath $Report -PathType Leaf)) {
    throw "No slice 003 report was produced; do not rerun"
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
from collections import Counter
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
checkpoint = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
if (report.get("schema_version") != 1
        or report.get("operation_identity") != "WEEKLY_CANDLE_REFRESH"
        or report.get("provider_identity") != "YAHOO_FINANCE"
        or report.get("manifest_checksum") != "8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a"
        or report.get("selection_checksum") != "75d839c54ff43969832a4d1110deba538cd52793e9402db5cba2dc1decc6c5ae"
        or report.get("end") != "2026-09-29T00:00:00+00:00"
        or report.get("budget") != {"max_items": 11791}
        or report.get("status") not in {"COMPLETE_WITH_FAILURES", "HALTED", "FAILED"}):
    raise SystemExit("Slice 003 report binding mismatch")
coverage = report.get("coverage")
if report["status"] != "FAILED":
    if not isinstance(coverage, dict):
        raise SystemExit("Slice 003 coverage is missing")
    attempted = coverage.get("current_run_attempted_count")
    completed = coverage.get("completed_count")
    remaining = coverage.get("remaining_count")
    if (type(attempted) is not int or not 1 <= attempted <= 11791
            or completed != 101 + attempted
            or remaining != 11892 - completed
            or sum(coverage.get(key, 0) for key in ("success_count", "empty_count", "failure_count")) != completed
            or coverage.get("failure_count", 0) < 10):
        raise SystemExit("Slice 003 coverage requires review")
    if report["status"] == "COMPLETE_WITH_FAILURES" and (attempted != 11791 or remaining != 0):
        raise SystemExit("Full collection accounting mismatch")
    if (checkpoint.get("schema_version") != 1
            or checkpoint.get("operation_identity") != "WEEKLY_CANDLE_REFRESH"
            or checkpoint.get("manifest_checksum") != report["manifest_checksum"]
            or checkpoint.get("selection_checksum") != report["selection_checksum"]
            or checkpoint.get("end") != report["end"]
            or not isinstance(checkpoint.get("outcomes"), dict)
            or len(checkpoint["outcomes"]) != completed):
        raise SystemExit("Post-run checkpoint binding mismatch")
    outcomes = checkpoint["outcomes"].values()
    statuses = Counter(value["status"] for value in outcomes)
    if any(statuses.get(status, 0) != coverage.get(key) for status, key in (
            ("SUCCESS", "success_count"), ("EMPTY", "empty_count"), ("FAILED", "failure_count"))):
        raise SystemExit("Post-run checkpoint status mismatch")
    categories = Counter(value["category"] for value in checkpoint["outcomes"].values()
                         if value["status"] == "FAILED")
    if categories != {item["category"]: item["count"] for item in report["failure_categories"]}:
        raise SystemExit("Post-run checkpoint failure-category mismatch")
print("Slice 003 report binding: PASSED")
print("Slice 003 status:", report["status"])
'@
$ValidationCode | python - $Report $Checkpoint
if ($LASTEXITCODE -ne 0) { throw "Report validation failed; do not rerun" }
if ($CommandExit -ne 1) { throw "Unexpected CLI exit code; send the redacted report" }
if ((Get-Content -LiteralPath $Report -Raw -Encoding UTF8 | ConvertFrom-Json).status -ne "COMPLETE_WITH_FAILURES") {
    throw "Collection halted or failed; send the redacted report"
}
Write-Host "Collection command finished; review the redacted report before any retry or scheduler"
```

Return only the redacted slice-003 report, its SHA-256, and the independent
`SQLite integrity: ok` line. A `COMPLETE_WITH_FAILURES` report with zero
remaining means the collection pass reached every selected series; it does
not clear the failed cohort. A `HALTED` report means the provider halted the
run, even if the final attempted series caused the halt.
If the process is interrupted without a report, preserve the private
checkpoint and database and request a focused resume instruction. Do not
rerun this block or run multiple copies in parallel. Do not send private
profile, checkpoint, source manifest, cache, or database.
