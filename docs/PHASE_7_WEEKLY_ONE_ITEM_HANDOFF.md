# Phase 7 — Weekly Candle One-Item Qualification Handoff

Classification: `OPERATIONAL — READY FOR USER EXECUTION`.

Fresh `develop` clone verified at
`75fe7919174246ca3a6e1259c739cb54e3d96a5a` with a clean worktree.
This handoff runs the existing weekly CLI for exactly one previously successful
daily series. It does not run the full universe, retry residual collection
defects, set up a scheduler, or claim analytical completeness.

Known repository-recorded private paths are the manifest at
`C:\runtime\data\market_batch_manifest_10y.json`, SQLite at
`C:\runtime\data\investment_terminal.db`, and Yahoo cache at
`C:\runtime\cache\yfinance`. The manifest checksum is
`8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a`.
The checkpoint directory is discovered by the exact batch-576 request checksum
and required to contain all 601 files; its location is not guessed.

Run once in Windows PowerShell after the package files are applied. The local
`develop` HEAD must contain the verified baseline and retain its weekly CLI and
service blobs unchanged. Do not rerun automatically if the command or report
fails. All PowerShell text is ASCII-only.

```powershell
$ErrorActionPreference = "Stop"
$Repository = "C:\Users\tu\Desktop\InvestmentTerminal"
$Baseline = "75fe7919174246ca3a6e1259c739cb54e3d96a5a"
$Manifest = "C:\runtime\data\market_batch_manifest_10y.json"
$Database = "C:\runtime\data\investment_terminal.db"
$DataRoot = "C:\runtime\data"
$Cache = "C:\runtime\cache\yfinance"
$WeeklyCheckpoint = "C:\runtime\data\weekly_candle_refresh_2026-09-23.json"
$Report = "C:\runtime\reports\weekly_candle_qualification_001.json"
$ManifestChecksum = "8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a"
$Batch576Checksum = "0b025a4862ff8e26cb00cbfc11f242227478a78e8385a82d4671a7543edd6fcb"

Set-Location -LiteralPath $Repository
if ((git branch --show-current).Trim() -ne "develop") { throw "Branch mismatch" }
if (@(git status --porcelain).Count -ne 0) { throw "Working tree is not clean" }
git merge-base --is-ancestor $Baseline HEAD
if ($LASTEXITCODE -ne 0) { throw "Verified baseline is not an ancestor" }
foreach ($File in @("investment_terminal/cli/weekly_candle_refresh.py", "investment_terminal/operations/weekly_candle_refresh.py")) {
    $ExpectedBlob = (git rev-parse "${Baseline}:$File").Trim()
    $ActualBlob = (git rev-parse "HEAD:$File").Trim()
    if ($ExpectedBlob -ne $ActualBlob) { throw "Weekly implementation changed after baseline" }
}
foreach ($Path in @($Manifest, $Database)) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Required input is missing: $Path" }
}
if (Test-Path -LiteralPath $WeeklyCheckpoint) { throw "Weekly checkpoint already exists" }
if (Test-Path -LiteralPath $Report) { throw "Report already exists" }

$Matches = @()
foreach ($Candidate in @(Get-ChildItem -LiteralPath $DataRoot -Recurse -File -Filter "batch_0576.json")) {
    try {
        $Value = Get-Content -LiteralPath $Candidate.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch { continue }
    if ([string]$Value.request_checksum -eq $Batch576Checksum) {
        $Matches += [System.IO.Path]::GetDirectoryName($Candidate.FullName)
    }
}
$Matches = @($Matches | Sort-Object -Unique)
if ($Matches.Count -ne 1) { throw "Could not uniquely identify source checkpoints" }
$SourceDirectory = [string]$Matches[0]
for ($Index = 1; $Index -le 601; $Index++) {
    $Path = Join-Path $SourceDirectory ("batch_{0:D4}.json" -f $Index)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Source checkpoints are incomplete" }
}

New-Item -ItemType Directory -Force -Path $Cache, "C:\runtime\reports" | Out-Null
python -m investment_terminal.cli.weekly_candle_refresh `
    --manifest $Manifest --manifest-checksum $ManifestChecksum `
    --source-checkpoint-directory $SourceDirectory `
    --weekly-checkpoint $WeeklyCheckpoint --database $Database `
    --cache-directory $Cache --report-output $Report `
    --end "2026-09-23T00:00:00+00:00" --max-items 1 --json
$ExitCode = $LASTEXITCODE
if (-not (Test-Path -LiteralPath $Report -PathType Leaf)) { throw "No report produced" }
$Result = Get-Content -LiteralPath $Report -Raw -Encoding UTF8 | ConvertFrom-Json
Write-Host "SEND: $Report"
Write-Host "DO NOT SEND: $Manifest"
Write-Host "DO NOT SEND: $SourceDirectory"
Write-Host "DO NOT SEND: $WeeklyCheckpoint"
Write-Host "DO NOT SEND: $Database"
if ($ExitCode -ne 0 -or [string]$Result.status -ne "BUDGET_EXHAUSTED" -or
    [int]$Result.coverage.current_run_attempted_count -ne 1 -or
    [int]$Result.coverage.failure_count -ne 0 -or
    ([int]$Result.coverage.success_count + [int]$Result.coverage.empty_count) -ne 1) {
    throw "One-item qualification needs report review; do not rerun"
}
Write-Host "Report SHA-256: $((Get-FileHash -LiteralPath $Report -Algorithm SHA256).Hash.ToLowerInvariant())"
```

Return only `C:\runtime\reports\weekly_candle_qualification_001.json`.
The report is aggregate and redacted; the manifest, source checkpoints,
weekly checkpoint, database, and cache remain private. Review the report before
any repeat, integrity check, broader refresh, or scheduler setup.
