# Phase 7 — Ten-Year Stored-Span Operational Handoff

Classification: `OPERATIONAL — READY FOR USER EXECUTION`.

Fresh clean `develop` matched the exact caller-supplied GitHub baseline
`650a85b09390da8914515b3725b391be85da8fc1`. This package changes no
application code and does not read or write private runtime inputs. It
prepares one offline, read-only schema-2 measurement of the explicit half-open
window `[2016-09-23T00:00:00Z, 2026-09-23T00:00:00Z)`.

Run the ASCII-only block below in Windows PowerShell while the Desktop
repository is still clean at the expected HEAD, **before applying this
documentation ZIP**. Stop any candle-ingestion job during the scan. The source
checkpoint directory is discovered by the recorded batch-576 request checksum,
not guessed; all 601 batch files must exist. A failed command or report is a
review gate, not permission to rerun automatically. This invokes no Yahoo
client and does not mutate the SQLite database or private checkpoints.

```powershell
$ErrorActionPreference = "Stop"
$Repository = "C:\Users\tu\Desktop\InvestmentTerminal"
$ExpectedHead = "650a85b09390da8914515b3725b391be85da8fc1"
$Manifest = "C:\runtime\data\market_batch_manifest_10y.json"
$Database = "C:\runtime\data\investment_terminal.db"
$DataRoot = "C:\runtime\data"
$WeeklyCheckpoint = "C:\runtime\data\weekly_candle_refresh_2026-09-23.json"
$Report = "C:\runtime\reports\weekly_stored_span_20160923_20260923_001.json"
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
Write-Host "Starting read-only ten-year span audit; this may take several minutes."
python -m investment_terminal.cli.weekly_stored_coverage `
    --manifest $Manifest --manifest-checksum $ManifestChecksum `
    --source-checkpoint-directory $SourceDirectory `
    --weekly-checkpoint $WeeklyCheckpoint --database $Database `
    --history-start "2016-09-23T00:00:00+00:00" `
    --report-output $Report
$CommandExit = $LASTEXITCODE
if (-not (Test-Path -LiteralPath $Report -PathType Leaf)) {
    throw "No span report was produced"
}
Write-Host "SEND: $Report"
Write-Host "DO NOT SEND: $Manifest"
Write-Host "DO NOT SEND: $SourceDirectory"
Write-Host "DO NOT SEND: $WeeklyCheckpoint"
Write-Host "DO NOT SEND: $Database"
if ($CommandExit -ne 0) {
    throw "Span audit failed; send the redacted report and do not rerun"
}

$ValidationCode = @'
import json
import sqlite3
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
database = Path(sys.argv[2])
expected_manifest = sys.argv[3]
if (report.get("schema_version") != 2 or
        report.get("operation_identity") != "WEEKLY_STORED_COVERAGE" or
        report.get("status") != "COMPLETE" or
        report.get("manifest_checksum") != expected_manifest or
        report.get("selection_checksum") != "75d839c54ff43969832a4d1110deba538cd52793e9402db5cba2dc1decc6c5ae" or
        report.get("history_start") != "2016-09-23T00:00:00+00:00" or
        report.get("end") != "2026-09-23T00:00:00+00:00"):
    raise SystemExit("Span report status or binding mismatch")
c = report.get("coverage")
if not isinstance(c, dict):
    raise SystemExit("Span report coverage is missing")
if (c.get("selected_series_count") != 11892 or
        c.get("source_excluded_count") != 127 or
        c.get("weekly_success_count") != 11678 or
        c.get("weekly_empty_count") != 0 or
        c.get("weekly_failure_count") != 214):
    raise SystemExit("Span report selected coverage mismatch")
bins = ("zero_count", "one_to_49_count", "50_to_199_count", "200_plus_count")
if sum(c.get(key, -1) for key in bins) != 11892:
    raise SystemExit("Span report row bins mismatch")
if (c.get("sample_50_ready_count") != c["50_to_199_count"] + c["200_plus_count"] or
        c.get("sample_200_ready_count") != c["200_plus_count"]):
    raise SystemExit("Span report sample readiness mismatch")
window_rows = c.get("history_window_row_count")
window_zero = c.get("history_window_zero_count")
first = c.get("first_candle_within_7_calendar_days_of_start_count")
last = c.get("last_candle_within_7_calendar_days_of_end_count")
both = c.get("both_endpoint_proxy_count")
if not (isinstance(window_rows, int) and 0 <= window_rows <= c["stored_row_count_before_end"] and
        isinstance(window_zero, int) and 0 <= window_zero <= 11892 and
        isinstance(first, int) and isinstance(last, int) and isinstance(both, int) and
        0 <= first <= 11892 - window_zero and
        0 <= last <= 11892 - window_zero and
        0 <= both <= min(first, last) and
        window_rows >= 11892 - window_zero):
    raise SystemExit("Span report window aggregates mismatch")
if not (0 <= c.get("series_with_gap_over_30_calendar_days_count", -1) <=
        c.get("series_with_gap_over_7_calendar_days_count", -1) <= 11892):
    raise SystemExit("Span report gap-series aggregates mismatch")
if not (0 <= c.get("gap_over_30_calendar_days_count", -1) <=
        c.get("gap_over_7_calendar_days_count", -1)):
    raise SystemExit("Span report gap-event aggregates mismatch")
categories = {item["category"]: item["count"] for item in report.get("weekly_failure_categories", [])}
if categories != {"NO_PRICE_DATA": 42, "RESPONSE_NUMERIC": 140, "STORED_CANDLE_DRIFT": 32}:
    raise SystemExit("Span report failure categories mismatch")
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
if ($LASTEXITCODE -ne 0) { throw "Span report or SQLite validation failed; do not rerun" }
Write-Host "Report SHA-256: $((Get-FileHash -LiteralPath $Report -Algorithm SHA256).Hash.ToLowerInvariant())"
```

Return only `C:\runtime\reports\weekly_stored_span_20160923_20260923_001.json`
and the `SQLite integrity: ok` line. The report is aggregate and redacted;
the manifest, source checkpoints, weekly checkpoint, and database remain
private. Endpoint and gap counts are calendar-day proxies, not exchange-
session-completeness or investment-analysis claims. Review this result before
any targeted remediation, new market request, or weekly scheduler.
