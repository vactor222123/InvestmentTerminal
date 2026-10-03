# Phase 7 — one profile-backed MCD research qualification

Classification: `OPERATIONAL — READY FOR USER EXECUTION`. A fresh clean
GitHub `develop` clone matched
`70c8d51dd7963d08a725594e601f782a46dc1c28`. This package changes
documentation only. It did not read or modify `C:\runtime`, call a provider,
or inspect the user's SQLite database.

The generic `instrument_research_run` command is already present at this
baseline. MCD is only the user's selected **qualification input**, not a
hardcoded Terminal rule. The command below reads the previously reported
complete private 2026-09-29 projection and matching weekly checkpoint. The
projection's exact-byte SHA-256 was previously reported as
`a8ffe1f944d529b64d688fb75ba4e9ad2278edc0d59bbe8ba1850c1017fabf0a`;
manifest and selection checksums were reported as
`8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a`
and `75d839c54ff43969832a4d1110deba538cd52793e9402db5cba2dc1decc6c5ae`.
These are evidence bindings, not assertions that MCD is in the selection or
has a complete/adjusted ten-year price history. If it is absent or its current
stored closes differ from the projection, the export fails closed.

Pause other jobs that could modify this SQLite database or weekly evidence.
Run this entire ASCII-only PowerShell block in a fresh terminal **before
applying this documentation ZIP**. Do not rerun blindly after a failure; the
two output names must be unused.

```powershell
$ErrorActionPreference = "Stop"
$Repository = "C:\Users\tu\Desktop\InvestmentTerminal"
$ExpectedHead = "70c8d51dd7963d08a725594e601f782a46dc1c28"
$Profile = "C:\runtime\data\weekly_run_profile.json"
$Projection = "C:\runtime\data\latest_raw_indicator_projection_20260929_full.json"
$Checkpoint = "C:\runtime\data\weekly_run\weekly_candle_refresh_2026-09-29.json"
$Database = "C:\runtime\data\investment_terminal.db"
$PrivateOutput = "C:\runtime\data\instrument_research_run_mcd_20260929_001.json"
$Report = "C:\runtime\reports\instrument_research_run_mcd_20260929_001.json"
$ProjectionSha256 = "a8ffe1f944d529b64d688fb75ba4e9ad2278edc0d59bbe8ba1850c1017fabf0a"
$ManifestChecksum = "8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a"
$SelectionChecksum = "75d839c54ff43969832a4d1110deba538cd52793e9402db5cba2dc1decc6c5ae"
$Symbol = "MCD"
$HistoryStart = "2016-09-29T00:00:00+00:00"
$End = "2026-09-29T00:00:00+00:00"

Set-Location -LiteralPath $Repository
if ((git branch --show-current).Trim() -ne "develop") { throw "Branch mismatch" }
if ((git rev-parse HEAD).Trim() -ne $ExpectedHead) { throw "HEAD mismatch" }
if (@(git status --porcelain).Count -ne 0) { throw "Working tree is not clean" }
foreach ($RequiredPath in @($Profile, $Projection, $Checkpoint, $Database)) {
    if (-not (Test-Path -LiteralPath $RequiredPath -PathType Leaf)) {
        throw "Required private input is missing: $RequiredPath"
    }
}
if (Test-Path -LiteralPath $PrivateOutput) { throw "Private output already exists" }
if (Test-Path -LiteralPath $Report) { throw "Report already exists" }
if ((Get-FileHash -LiteralPath $Projection -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ProjectionSha256) {
    throw "Private projection checksum mismatch"
}
$CheckpointShaBefore = (Get-FileHash -LiteralPath $Checkpoint -Algorithm SHA256).Hash.ToLowerInvariant()

python -m investment_terminal.cli.instrument_research_run `
    --profile $Profile --projection $Projection `
    --projection-sha256 $ProjectionSha256 --symbol $Symbol `
    --history-start $HistoryStart --end $End `
    --private-output $PrivateOutput --report-output $Report
$CommandExit = $LASTEXITCODE
if (-not (Test-Path -LiteralPath $Report -PathType Leaf)) {
    throw "No redacted report was produced; do not rerun"
}
$Result = Get-Content -LiteralPath $Report -Raw -Encoding UTF8 | ConvertFrom-Json
$ExpectedFields = @(
    "schema_version", "operation_identity", "status", "manifest_checksum",
    "selection_checksum", "source_projection_sha256", "history_start", "end",
    "price_basis", "candle_count", "history_candles_sha256",
    "sample_count_capped_at_200", "availability",
    "recent_7_calendar_day_proxy", "failure", "limitations"
)
if (@(Compare-Object $ExpectedFields @($Result.PSObject.Properties.Name)).Count -ne 0) {
    throw "Unexpected report fields; do not send"
}
if ($Result.schema_version -ne 1 -or $Result.operation_identity -ne "INSTRUMENT_RESEARCH_EXPORT_REPORT" -or
    $Result.price_basis -ne "STORED_CLOSE_NO_EXPLICIT_ADJUSTMENT") {
    throw "Unexpected report contract; do not send"
}
if ($Result.status -eq "COMPLETE") {
    if ($CommandExit -ne 0 -or -not (Test-Path -LiteralPath $PrivateOutput -PathType Leaf) -or
        $Result.manifest_checksum -ne $ManifestChecksum -or
        $Result.selection_checksum -ne $SelectionChecksum -or
        $Result.source_projection_sha256 -ne $ProjectionSha256 -or
        $Result.history_start -ne $HistoryStart -or $Result.end -ne $End -or
        [int]$Result.candle_count -le 0 -or [int]$Result.candle_count -gt 4000 -or
        $Result.sample_count_capped_at_200 -ne 200 -or
        $Result.availability -ne "BOTH_AVAILABLE" -or
        $Result.recent_7_calendar_day_proxy -ne $true -or
        $Result.history_candles_sha256 -notmatch '^[0-9a-f]{64}$' -or
        $Result.failure -ne $null) {
        throw "Completed export binding mismatch; do not send"
    }
    $ExpectedLimitations = @(
        "report excludes instrument identity, currency, timestamps, prices and values",
        "stored Close has no explicit Terminal-side corporate-action adjustment",
        "observed rows and recency do not prove exchange-session completeness"
    )
} elseif ($Result.status -eq "FAILED") {
    if ($CommandExit -eq 0 -or $Result.failure -ne "PRECONDITION_OR_RUNTIME_FAILURE" -or
        (Test-Path -LiteralPath $PrivateOutput)) {
        throw "Unexpected failure report; do not send"
    }
    $ExpectedLimitations = @("failed report excludes private identities and error text")
} else {
    throw "Unexpected report status; do not send"
}
if (@(Compare-Object $ExpectedLimitations @($Result.limitations)).Count -ne 0) {
    throw "Unexpected report limitations; do not send"
}

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
if ($LASTEXITCODE -ne 0) { throw "SQLite integrity failed; do not rerun" }
if ((Get-FileHash -LiteralPath $Checkpoint -Algorithm SHA256).Hash.ToLowerInvariant() -ne $CheckpointShaBefore) {
    throw "Weekly checkpoint changed; do not rerun"
}
if ((Get-FileHash -LiteralPath $Projection -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ProjectionSha256) {
    throw "Private projection changed; do not rerun"
}
Write-Host "SEND: $Report"
Write-Host "Report SHA-256: $((Get-FileHash -LiteralPath $Report -Algorithm SHA256).Hash.ToLowerInvariant())"
Write-Host "DO NOT SEND: $Profile, $Projection, $Checkpoint, $Database, $PrivateOutput"
if ($Result.status -ne "COMPLETE") { throw "Research export failed; send only the redacted report" }
```

Send only the validated redacted report, its SHA-256, and the
`SQLite integrity: ok` line. Do not send the profile, projection, checkpoint,
SQLite database, or private MCD export. A `COMPLETE` report is factual stored-
close evidence only: no adjusted-return, exchange-session completeness,
portfolio recommendation, automatic ChatGPT upload, or weekly scheduler is
established. Review this one result before any further runtime action.
