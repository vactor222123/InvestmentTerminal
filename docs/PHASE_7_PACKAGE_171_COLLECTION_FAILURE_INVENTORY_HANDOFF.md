# Phase 7 Package 171 — Collection Failure Inventory Handoff

## Classification

`OPERATIONAL — READY FOR USER EXECUTION`

## Verified Baseline

```text
develop @ f278da4dd5497d609e96b9b5d70a15960a8d2d44
```

## Scope

The completed schema-version-2 sweep report has SHA-256
`b8e7504cd1a6ff8b5755ed60ffde9ff20bd70a32111ea845e624105ab65be0dc`.
It records 601 sweep-covered batches, 495 fully complete batches, zero
unswept batches, and 124 deferable failures. Package 170 added a read-only
aggregate inventory for this exact post-sweep state.

The command below validates repository, manifest, checkpoint-directory, and
immutable sweep-report bindings before running that inventory once. It then
validates the redacted output and checks SQLite integrity read-only. It makes
no provider request and cannot mutate the manifest, checkpoints, or database.

## Execution Order

Run this block **before applying Package 171**, because it deliberately
requires the baseline above. The PowerShell source and emitted messages are
ASCII-only. Do not rerun it if the report path already exists.

```powershell
$ErrorActionPreference = "Stop"

$Repository = "C:\Users\tu\Desktop\InvestmentTerminal"
$ExpectedHead = "f278da4dd5497d609e96b9b5d70a15960a8d2d44"
$ExpectedBranch = "develop"
$ManifestPath = "C:\runtime\data\market_batch_manifest_10y.json"
$CheckpointSearchRoot = "C:\runtime\data"
$SweepReportPath = "C:\runtime\reports\manifest_collection_sweep_resume_0576_0601_schema2.json"
$DatabasePath = "C:\runtime\data\investment_terminal.db"
$ReportDirectory = "C:\runtime\reports"
$ReportPath = Join-Path $ReportDirectory "manifest_collection_failure_inventory_001.json"
$ManifestChecksum = "8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a"
$SweepReportChecksum = "b8e7504cd1a6ff8b5755ed60ffde9ff20bd70a32111ea845e624105ab65be0dc"
$Batch576RequestChecksum = "0b025a4862ff8e26cb00cbfc11f242227478a78e8385a82d4671a7543edd6fcb"
$BatchCount = 601
$RequestedCount = 12019
$DeferredFailureCount = 124

Set-Location -LiteralPath $Repository

$ActualHead = (git rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $ActualHead -ne $ExpectedHead) {
    throw "HEAD mismatch. Expected $ExpectedHead, got $ActualHead"
}

$ActualBranch = (git branch --show-current).Trim()
if ($LASTEXITCODE -ne 0 -or $ActualBranch -ne $ExpectedBranch) {
    throw "Branch mismatch. Expected $ExpectedBranch, got $ActualBranch"
}

$WorktreeState = @(git status --porcelain)
if ($LASTEXITCODE -ne 0 -or $WorktreeState.Count -ne 0) {
    throw "Working tree is not clean"
}

foreach ($RequiredPath in @($ManifestPath, $SweepReportPath, $DatabasePath)) {
    if (-not (Test-Path -LiteralPath $RequiredPath -PathType Leaf)) {
        throw "Required input is missing: $RequiredPath"
    }
}
if (-not (Test-Path -LiteralPath $CheckpointSearchRoot -PathType Container)) {
    throw "Required checkpoint search root is missing: $CheckpointSearchRoot"
}
if (Test-Path -LiteralPath $ReportPath) {
    throw "Refusing to overwrite existing report: $ReportPath"
}

$ActualSweepChecksum = (
    Get-FileHash -LiteralPath $SweepReportPath -Algorithm SHA256
).Hash.ToLowerInvariant()
if ($ActualSweepChecksum -ne $SweepReportChecksum) {
    throw "Sweep report checksum mismatch"
}

try {
    $Manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 |
        ConvertFrom-Json
    $SweepReport = Get-Content -LiteralPath $SweepReportPath -Raw -Encoding UTF8 |
        ConvertFrom-Json
} catch {
    throw "Could not parse manifest or sweep report"
}

$Batches = @($Manifest.batches)
$Batch576 = @($Batches | Where-Object { [int]$_.batch_index -eq 576 })
$ManifestRequestedCount = (
    $Batches | ForEach-Object { @($_.request.items).Count } |
        Measure-Object -Sum
).Sum
if ($Batches.Count -ne $BatchCount -or
    $Batch576.Count -ne 1 -or
    [string]$Batch576[0].request_checksum -ne $Batch576RequestChecksum -or
    [int]$ManifestRequestedCount -ne $RequestedCount) {
    throw "Manifest binding validation failed"
}

$Ending = $SweepReport.ending_coverage
if ([int]$SweepReport.schema_version -ne 2 -or
    [string]$SweepReport.operation_identity -ne "MANIFEST_COLLECTION_SWEEP" -or
    [string]$SweepReport.provider_identity -ne "YAHOO_FINANCE" -or
    [string]$SweepReport.status -ne "COMPLETE" -or
    [string]$SweepReport.manifest_checksum -ne $ManifestChecksum -or
    [int]$Ending.batch_count -ne $BatchCount -or
    [int]$Ending.sweep_covered_batch_count -ne $BatchCount -or
    [int]$Ending.fully_complete_batch_count -ne 495 -or
    [int]$Ending.remaining_unswept_batch_count -ne 0 -or
    [int]$Ending.deferred_failure_count -ne $DeferredFailureCount -or
    $null -ne $SweepReport.stop_batch_index -or
    @($SweepReport.failure_types).Count -ne 0) {
    throw "Completed sweep report contract validation failed"
}

$CheckpointMatches = @()
$CheckpointCandidates = @(
    Get-ChildItem -LiteralPath $CheckpointSearchRoot -Recurse -File -Filter "batch_0576.json"
)
foreach ($Candidate in $CheckpointCandidates) {
    try {
        $CandidateCheckpoint = Get-Content -LiteralPath $Candidate.FullName -Raw -Encoding UTF8 |
            ConvertFrom-Json
    } catch {
        continue
    }
    if ([string]$CandidateCheckpoint.request_checksum -eq $Batch576RequestChecksum) {
        $CheckpointMatches += [pscustomobject]@{
            Path = $Candidate.FullName
            Payload = $CandidateCheckpoint
        }
    }
}
if ($CheckpointMatches.Count -ne 1) {
    throw "Could not uniquely identify the request-bound checkpoint directory"
}
$CheckpointPath = [string]$CheckpointMatches[0].Path
$CheckpointDirectory = [System.IO.Path]::GetDirectoryName($CheckpointPath)
if ([string]::IsNullOrWhiteSpace($CheckpointDirectory)) {
    throw "Could not resolve the checkpoint directory"
}

New-Item -ItemType Directory -Force -Path $ReportDirectory | Out-Null

python -m investment_terminal.cli.manifest_collection_failure_inventory `
    --manifest $ManifestPath `
    --manifest-checksum $ManifestChecksum `
    --checkpoint-directory $CheckpointDirectory `
    --sweep-report $SweepReportPath `
    --sweep-report-checksum $SweepReportChecksum `
    --report-output $ReportPath `
    --json
$CommandExitCode = $LASTEXITCODE

if (-not (Test-Path -LiteralPath $ReportPath -PathType Leaf)) {
    throw "Failure inventory did not produce a report"
}
try {
    $Report = Get-Content -LiteralPath $ReportPath -Raw -Encoding UTF8 |
        ConvertFrom-Json
} catch {
    throw "Could not parse the failure inventory report"
}

if ([int]$Report.schema_version -ne 1 -or
    [string]$Report.operation_identity -ne "MANIFEST_COLLECTION_FAILURE_INVENTORY" -or
    [string]$Report.provider_identity -ne "YAHOO_FINANCE" -or
    @("SUCCESS", "FAILED") -notcontains [string]$Report.status) {
    throw "Failure inventory report contract validation failed"
}

if ([string]$Report.status -eq "SUCCESS") {
    $Coverage = $Report.coverage
    $RetryableSignatures = @($Report.retryable_causal_signatures)
    $FinalSignatures = @($Report.final_failure_signatures)
    $RetryableSignatureTotal = (
        $RetryableSignatures | Measure-Object -Property count -Sum
    ).Sum
    $FinalSignatureTotal = (
        $FinalSignatures | Measure-Object -Property count -Sum
    ).Sum
    foreach ($Signature in $RetryableSignatures) {
        if ([string]$Signature.sweep_disposition -ne "DEFERABLE") {
            throw "Inventory contains a non-deferable retryable signature"
        }
    }
    $OutcomeTotal = (
        [int]$Coverage.success_count +
        [int]$Coverage.empty_count +
        [int]$Coverage.retryable_failure_count +
        [int]$Coverage.final_failure_count
    )
    if ($CommandExitCode -ne 0 -or
        [string]$Report.manifest_checksum -ne $ManifestChecksum -or
        [string]$Report.sweep_report_checksum -ne $SweepReportChecksum -or
        [int]$Coverage.batch_count -ne $BatchCount -or
        [int]$Coverage.sweep_covered_batch_count -ne $BatchCount -or
        [int]$Coverage.fully_complete_batch_count -ne 495 -or
        [int]$Coverage.requested_count -ne $RequestedCount -or
        [int]$Coverage.checkpoint_outcome_count -ne $RequestedCount -or
        [int]$Coverage.missing_count -ne 0 -or
        [int]$Coverage.retryable_failure_count -ne $DeferredFailureCount -or
        [int]$Coverage.deferable_failure_count -ne $DeferredFailureCount -or
        [int]$Coverage.blocking_failure_count -ne 0 -or
        [int]$RetryableSignatureTotal -ne $DeferredFailureCount -or
        [int]$FinalSignatureTotal -ne [int]$Coverage.final_failure_count -or
        $OutcomeTotal -ne $RequestedCount -or
        $null -ne $Report.failure) {
        throw "Successful failure inventory evidence is inconsistent"
    }
} else {
    if ($CommandExitCode -eq 0 -or
        ($null -ne $Report.manifest_checksum -and
            [string]$Report.manifest_checksum -ne $ManifestChecksum) -or
        $null -ne $Report.sweep_report_checksum -or
        $null -ne $Report.coverage -or
        @($Report.retryable_causal_signatures).Count -ne 0 -or
        @($Report.final_failure_signatures).Count -ne 0 -or
        [string]$Report.failure.reason -ne "Manifest collection failure inventory failed") {
        throw "Failed failure inventory evidence is inconsistent"
    }
}

$IntegrityScript = @'
import sqlite3
import sys

database = sys.argv[1].replace("\\", "/")
connection = sqlite3.connect("file:" + database + "?mode=ro", uri=True)
try:
    print(connection.execute("PRAGMA integrity_check").fetchone()[0])
finally:
    connection.close()
'@
$Integrity = ($IntegrityScript | python - $DatabasePath).Trim()
if ($LASTEXITCODE -ne 0 -or $Integrity -ne "ok") {
    throw "SQLite integrity check failed"
}

$ReportHash = (
    Get-FileHash -LiteralPath $ReportPath -Algorithm SHA256
).Hash.ToLowerInvariant()

Write-Host "Failure inventory status: $($Report.status)"
if ([string]$Report.status -eq "SUCCESS") {
    Write-Host "Requested outcomes: $($Report.coverage.requested_count)"
    Write-Host "Retryable failures: $($Report.coverage.retryable_failure_count)"
    Write-Host "Final failures: $($Report.coverage.final_failure_count)"
    Write-Host "Retryable signature count: $(@($Report.retryable_causal_signatures).Count)"
    Write-Host "Final signature count: $(@($Report.final_failure_signatures).Count)"
}
Write-Host "SQLite integrity: $Integrity"
Write-Host "Report: $ReportPath"
Write-Host "Report SHA-256: $ReportHash"
Write-Host "SEND: $ReportPath"
Write-Host "SEND: SQLite integrity: $Integrity"
Write-Host "DO NOT SEND: $ManifestPath"
Write-Host "DO NOT SEND: $CheckpointDirectory"
Write-Host "DO NOT SEND: $DatabasePath"
```

## Expected Evidence

`SUCCESS` must account for all 12,019 manifest outcomes, all 601 batches, zero
missing outcomes, exactly 124 deferable retryable failures, zero blocking
failures, and internally reconciled retryable/final signatures. `FAILED` is
also valid safe evidence and must be returned without modifying any runtime
input. The command must print `SQLite integrity: ok`.

## Repository Verification

```text
PowerShell block ASCII validation: passed (236 lines)
focused inventory, sweep, partial-inventory, resumable-batch, manifest, and
architecture tests: 75 passed in 3.08s
full test suite: 3154 passed, 4 skipped, 1 warning in 26.79s
git diff --check: clean
```

The warning is the existing Starlette `httpx` deprecation warning and is not a
Package 171 regression. This documentation-only package did not inspect or
mutate private runtime data.

## Next Gate

Return only
`C:\runtime\reports\manifest_collection_failure_inventory_001.json` and the
printed `SQLite integrity: ok` line. Do not send the manifest, checkpoint
directory, or database. Review the aggregate evidence before authorizing any
failure remediation or moving to indicator generation.
