# Phase 7 Package 162 — Optimized Collection Sweep Handoff

## Classification

`OPERATIONAL — READY FOR USER EXECUTION`

## Verified Baseline

```text
develop @ 6a9de4fa0f5dee2e28eea78a99568495d4055ff0
```

## Scope

Package 161 expanded the collection sweep without weakening its failure
boundary. Exact local candle-validation failures and schema-4 `APIError`
outcomes with verified Yahoo `NO_PRICE_DATA` causal evidence may be deferred;
generic or legacy API errors, rate limiting, timeout, transport, persistence,
checkpoint, and unknown failures still halt before later work.

The reviewed Package 160 result leaves batches 1–108 sweep-covered. Batch 109
contains one evidence-bound final `NO_PRICE_DATA` exclusion and 19 missing
members. A budget of 493 therefore covers the exact remaining range from batch
109 through batch 601.

The command below validates the exact repository state, private manifest,
unique request-bound batch-109 checkpoint, stored terminal evidence, schema-2
redacted report, and read-only SQLite integrity. It never prints or copies the
private manifest, checkpoint, database, cache, symbols, currencies, prices, or
candles.

## Execution Order

Run this block **before applying Package 162**, because it deliberately
requires the Package 161 GitHub baseline above. The PowerShell source and all
emitted command messages are ASCII-only.

```powershell
$ErrorActionPreference = "Stop"

$Repository = "C:\Users\tu\Desktop\InvestmentTerminal"
$ExpectedHead = "6a9de4fa0f5dee2e28eea78a99568495d4055ff0"
$ExpectedBranch = "develop"
$ManifestPath = "C:\runtime\data\market_batch_manifest_10y.json"
$CheckpointSearchRoot = "C:\runtime\data"
$DatabasePath = "C:\runtime\data\investment_terminal.db"
$CacheDirectory = "C:\runtime\cache\yfinance"
$ReportDirectory = "C:\runtime\reports"
$ReportPath = Join-Path $ReportDirectory "manifest_collection_sweep_resume_0109_0601_schema2.json"
$ManifestChecksum = "8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a"
$RequestChecksum = "a3b00484a202f114f2051f0568f1ed61c0d79535415266ebba120c15134c0a34"
$DiagnosticChecksum = "509769c10ef7a4617104b80c5ed3ca626cd763e98c97e76353d52586507b64ef"
$BatchIndex = 109
$BatchCount = 601
$MaxBatches = 493

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

foreach ($RequiredPath in @($ManifestPath, $DatabasePath)) {
    if (-not (Test-Path -LiteralPath $RequiredPath -PathType Leaf)) {
        throw "Required private input is missing: $RequiredPath"
    }
}
if (-not (Test-Path -LiteralPath $CheckpointSearchRoot -PathType Container)) {
    throw "Required checkpoint search root is missing: $CheckpointSearchRoot"
}
if (Test-Path -LiteralPath $ReportPath) {
    throw "Refusing to overwrite existing report: $ReportPath"
}

try {
    $Manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 |
        ConvertFrom-Json
} catch {
    throw "Could not parse the private manifest"
}

$SelectedBatches = @($Manifest.batches | Where-Object {
    [int]$_.batch_index -eq $BatchIndex
})
if ($SelectedBatches.Count -ne 1) {
    throw "Could not uniquely identify batch $BatchIndex in the manifest"
}
$SelectedBatch = $SelectedBatches[0]
$RequestedItems = @($SelectedBatch.request.items)
if ([string]$SelectedBatch.request_checksum -ne $RequestChecksum -or
    $RequestedItems.Count -ne 20 -or
    @($Manifest.batches).Count -ne $BatchCount) {
    throw "Manifest batch-109 binding validation failed"
}

$CheckpointMatches = @()
$CheckpointCandidates = @(
    Get-ChildItem -LiteralPath $CheckpointSearchRoot -Recurse -File -Filter "batch_0109.json"
)
foreach ($Candidate in $CheckpointCandidates) {
    try {
        $CandidateCheckpoint = Get-Content -LiteralPath $Candidate.FullName -Raw -Encoding UTF8 |
            ConvertFrom-Json
    } catch {
        continue
    }
    if ([string]$CandidateCheckpoint.request_checksum -eq $RequestChecksum) {
        $CheckpointMatches += [pscustomobject]@{
            Path = $Candidate.FullName
            Payload = $CandidateCheckpoint
        }
    }
}
if ($CheckpointMatches.Count -ne 1) {
    throw "Could not uniquely identify the request-bound batch-109 checkpoint"
}

$CheckpointPath = [string]$CheckpointMatches[0].Path
$CheckpointDirectory = Split-Path -LiteralPath $CheckpointPath -Parent
$Checkpoint = $CheckpointMatches[0].Payload
$CheckpointOutcomes = @(
    $Checkpoint.outcomes.PSObject.Properties | ForEach-Object { $_.Value }
)
if ([int]$Checkpoint.schema_version -ne 4 -or
    [string]$Checkpoint.request_checksum -ne $RequestChecksum -or
    $CheckpointOutcomes.Count -ne 1) {
    throw "Batch-109 checkpoint contract validation failed"
}

$FinalOutcome = $CheckpointOutcomes[0]
$IsolationProperties = @($FinalOutcome.isolation_evidence.PSObject.Properties)
if ([string]$FinalOutcome.status -ne "FINAL_FAILED" -or
    [string]$FinalOutcome.failure_type -ne "APIError" -or
    [string]$FinalOutcome.failure_category -ne "NO_PRICE_DATA" -or
    [string]$FinalOutcome.isolation_policy_identity -ne "STORED_YAHOO_NO_PRICE_DATA_V1" -or
    $IsolationProperties.Count -ne 1 -or
    [string]$FinalOutcome.isolation_evidence.causal_evidence_diagnostic_checksum -ne $DiagnosticChecksum) {
    throw "Batch-109 stored no-price evidence validation failed"
}

New-Item -ItemType Directory -Force -Path $CacheDirectory | Out-Null
New-Item -ItemType Directory -Force -Path $ReportDirectory | Out-Null

python -m investment_terminal.cli.manifest_collection_sweep `
    --manifest $ManifestPath `
    --manifest-checksum $ManifestChecksum `
    --checkpoint-directory $CheckpointDirectory `
    --database $DatabasePath `
    --cache-directory $CacheDirectory `
    --report-output $ReportPath `
    --max-batches $MaxBatches `
    --json
$CommandExitCode = $LASTEXITCODE

if (-not (Test-Path -LiteralPath $ReportPath -PathType Leaf)) {
    throw "Collection sweep did not produce a report"
}
try {
    $Report = Get-Content -LiteralPath $ReportPath -Raw -Encoding UTF8 |
        ConvertFrom-Json
} catch {
    throw "Could not parse the collection sweep report"
}

$AllowedStatuses = @("COMPLETE", "HALTED", "FAILED")
if ([int]$Report.schema_version -ne 2 -or
    [string]$Report.operation_identity -ne "MANIFEST_COLLECTION_SWEEP" -or
    [string]$Report.provider_identity -ne "YAHOO_FINANCE" -or
    $AllowedStatuses -notcontains [string]$Report.status) {
    throw "Collection sweep report contract validation failed"
}

if ([string]$Report.status -eq "FAILED") {
    if ($CommandExitCode -eq 0 -or
        @($Report.failure_types).Count -eq 0 -or
        ($null -ne $Report.manifest_checksum -and
            [string]$Report.manifest_checksum -ne $ManifestChecksum) -or
        ($null -ne $Report.budget -and
            [int]$Report.budget.max_batches -ne $MaxBatches) -or
        $null -ne $Report.starting_coverage -or
        $null -ne $Report.current_run -or
        $null -ne $Report.ending_coverage) {
        throw "Failed collection sweep evidence is inconsistent"
    }
} else {
    if ([string]$Report.manifest_checksum -ne $ManifestChecksum -or
        [int]$Report.budget.max_batches -ne $MaxBatches) {
        throw "Collection sweep report binding validation failed"
    }
    $Starting = $Report.starting_coverage
    $StartingDeferredTypes = @($Starting.deferred_failure_types)
    if ([int]$Starting.batch_count -ne $BatchCount -or
        [int]$Starting.sweep_covered_batch_count -ne 108 -or
        [int]$Starting.fully_complete_batch_count -ne 107 -or
        [int]$Starting.remaining_unswept_batch_count -ne 493 -or
        [int]$Starting.deferred_failure_count -ne 1 -or
        $StartingDeferredTypes.Count -ne 1 -or
        [string]$StartingDeferredTypes[0] -ne "YahooCandleInvalidResponseError") {
        throw "Collection sweep starting coverage mismatch"
    }

    $EndingDeferredTypes = @($Report.ending_coverage.deferred_failure_types)
    foreach ($FailureType in $EndingDeferredTypes) {
        if (@("APIError", "YahooCandleInvalidResponseError") -notcontains [string]$FailureType) {
            throw "Collection sweep reported an unsupported deferred failure type"
        }
    }
}

if ([string]$Report.status -eq "COMPLETE") {
    if ([int]$Report.ending_coverage.sweep_covered_batch_count -ne $BatchCount -or
        [int]$Report.ending_coverage.remaining_unswept_batch_count -ne 0 -or
        $null -ne $Report.stop_batch_index -or
        @($Report.failure_types).Count -ne 0 -or
        $CommandExitCode -ne 0) {
        throw "Complete collection sweep evidence is inconsistent"
    }
} elseif ([string]$Report.status -eq "HALTED") {
    if ($null -eq $Report.stop_batch_index -or
        @($Report.failure_types).Count -eq 0 -or
        $CommandExitCode -eq 0) {
        throw "Halted collection sweep evidence is inconsistent"
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

Write-Host "Collection sweep status: $($Report.status)"
Write-Host "Starting covered batches: $($Report.starting_coverage.sweep_covered_batch_count)"
Write-Host "Ending covered batches: $($Report.ending_coverage.sweep_covered_batch_count)"
Write-Host "Deferred failure count: $($Report.ending_coverage.deferred_failure_count)"
Write-Host "SQLite integrity: $Integrity"
Write-Host "Report: $ReportPath"
Write-Host "Report SHA-256: $ReportHash"
Write-Host "SEND: $ReportPath"
Write-Host "SEND: SQLite integrity: $Integrity"
Write-Host "DO NOT SEND: $ManifestPath"
Write-Host "DO NOT SEND: $CheckpointDirectory"
Write-Host "DO NOT SEND: $DatabasePath"
Write-Host "DO NOT SEND: $CacheDirectory"
```

## Expected Evidence

`COMPLETE` is the successful collection outcome: all 601 batches are
sweep-covered, zero remain unswept, and deferred failures stay explicit for the
later aggregate inventory. `HALTED` or `FAILED` is also valid safe evidence and
must be returned without bypassing the recorded stopping category. The command
must print `SQLite integrity: ok`.

The run may take a long time. It is resumable from every atomically written
private checkpoint. Do not delete checkpoints or use SQLite row counts as a
replacement progress index.

## Repository Verification

```text
PowerShell block ASCII validation: passed (231 lines)
focused sweep, stored-evidence, causal-evidence, and architecture tests: 55 passed in 3.91s
full test suite: 3127 passed, 4 skipped, 1 warning in 32.30s
git diff --check: clean
```

The warning is the existing Starlette `httpx` deprecation warning. The local
PowerShell AST process could not start because this Windows host reports missing
CET support; no runtime command was executed in this documentation-only
package. The block reuses the established handoff syntax and passed the
ASCII-only check.

## Next Gate

Return only
`C:\runtime\reports\manifest_collection_sweep_resume_0109_0601_schema2.json`
and the printed `SQLite integrity: ok` line. If collection is complete, build
one redacted aggregate deferred/final-failure inventory. If it halts, inspect
only the recorded systemic stop before resuming.
