# Phase 7 Package 169 — Remaining Collection Sweep Handoff

## Classification

`OPERATIONAL — READY FOR USER EXECUTION`

## Verified Baseline

```text
develop @ d5d9281f4558f15f6598beb8b8e966b983615fa4
```

## Scope

The returned schema-version-2 collection-sweep report has SHA-256
`356feed607a4d8a235757818718c443caf3b42f85b5d8bd82d2727b4ff9bfee2`.
It proves sweep coverage through batch 575: 575 batches are covered, 474 are
fully complete, 118 deferred failures remain explicit, and 26 batches remain.

Package 168 records that the evidence-bound retry cleared the only blocking
batch-576 timeout. The current batch has 16 successes, two deferable failures,
two missing members, and zero blocking failures. The exact remaining range is
therefore batches 576–601 inclusive, so the command below uses a budget of 26.

This handoff validates the exact repository state, manifest and request
bindings, immutable retry-report bytes, current private batch-576 aggregate,
schema-2 sweep report, and read-only SQLite integrity. It does not print or
copy the private manifest, checkpoint, database, cache, symbols, currencies,
prices, or candles.

## Execution Order

Run this block **before applying Package 169**, because it deliberately
requires the baseline above. The PowerShell source and emitted messages are
ASCII-only. Do not rerun it if the report path already exists.

```powershell
$ErrorActionPreference = "Stop"

$Repository = "C:\Users\tu\Desktop\InvestmentTerminal"
$ExpectedHead = "d5d9281f4558f15f6598beb8b8e966b983615fa4"
$ExpectedBranch = "develop"
$ManifestPath = "C:\runtime\data\market_batch_manifest_10y.json"
$CheckpointSearchRoot = "C:\runtime\data"
$DatabasePath = "C:\runtime\data\investment_terminal.db"
$CacheDirectory = "C:\runtime\cache\yfinance"
$RetryReportPath = "C:\runtime\reports\manifest_batch_0576_timeout_retry_001.json"
$ReportDirectory = "C:\runtime\reports"
$ReportPath = Join-Path $ReportDirectory "manifest_collection_sweep_resume_0576_0601_schema2.json"
$ManifestChecksum = "8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a"
$RequestChecksum = "0b025a4862ff8e26cb00cbfc11f242227478a78e8385a82d4671a7543edd6fcb"
$InventoryChecksum = "67fd4eca4ede8205c5e669a44d70cbd269601227c7a939b80b5776d29d35e069"
$RetryReportChecksum = "59b8d58ac76903edbb03f55ee6ec8f79220ad0f38ecedb156412170c2d1385aa"
$BatchIndex = 576
$BatchCount = 601
$MaxBatches = 26

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

foreach ($RequiredPath in @($ManifestPath, $DatabasePath, $RetryReportPath)) {
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

$ActualRetryReportChecksum = (
    Get-FileHash -LiteralPath $RetryReportPath -Algorithm SHA256
).Hash.ToLowerInvariant()
if ($ActualRetryReportChecksum -ne $RetryReportChecksum) {
    throw "Timeout retry report checksum mismatch"
}
try {
    $RetryReport = Get-Content -LiteralPath $RetryReportPath -Raw -Encoding UTF8 |
        ConvertFrom-Json
} catch {
    throw "Could not parse the timeout retry report"
}
$RetryBefore = $RetryReport.coverage.before
$RetryAfter = $RetryReport.coverage.after
if ([int]$RetryReport.schema_version -ne 1 -or
    [string]$RetryReport.operation_identity -ne "MANIFEST_PARTIAL_TIMEOUT_RETRY" -or
    [string]$RetryReport.provider_identity -ne "YAHOO_FINANCE" -or
    [string]$RetryReport.status -ne "READY_FOR_SWEEP" -or
    [string]$RetryReport.manifest_checksum -ne $ManifestChecksum -or
    [int]$RetryReport.batch_index -ne $BatchIndex -or
    [int]$RetryReport.batch_count -ne $BatchCount -or
    [string]$RetryReport.request_checksum -ne $RequestChecksum -or
    [string]$RetryReport.inventory_checksum -ne $InventoryChecksum -or
    [int]$RetryBefore.success_count -ne 15 -or
    [int]$RetryBefore.retryable_failure_count -ne 3 -or
    [int]$RetryBefore.deferable_failure_count -ne 2 -or
    [int]$RetryBefore.blocking_failure_count -ne 1 -or
    [int]$RetryAfter.success_count -ne 16 -or
    [int]$RetryAfter.empty_count -ne 0 -or
    [int]$RetryAfter.retryable_failure_count -ne 2 -or
    [int]$RetryAfter.final_failure_count -ne 0 -or
    [int]$RetryAfter.deferable_failure_count -ne 2 -or
    [int]$RetryAfter.blocking_failure_count -ne 0 -or
    [int]$RetryReport.coverage.checkpoint_outcome_count -ne 18 -or
    [int]$RetryReport.coverage.missing_count -ne 2 -or
    [string]$RetryReport.retry_result.status -ne "SUCCESS" -or
    [int]$RetryReport.retry_result.downloaded -ne 1573 -or
    [int]$RetryReport.retry_result.inserted -ne 1573 -or
    [int]$RetryReport.retry_result.duplicates -ne 0 -or
    [int]$RetryReport.retry_result.omitted_trailing_count -ne 0 -or
    [string]$RetryReport.retry_result.sweep_disposition -ne "CLEARED") {
    throw "Timeout retry report binding validation failed"
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
    throw "Manifest batch-576 binding validation failed"
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
    if ([string]$CandidateCheckpoint.request_checksum -eq $RequestChecksum) {
        $CheckpointMatches += [pscustomobject]@{
            Path = $Candidate.FullName
            Payload = $CandidateCheckpoint
        }
    }
}
if ($CheckpointMatches.Count -ne 1) {
    throw "Could not uniquely identify the request-bound batch-576 checkpoint"
}

$CheckpointPath = [string]$CheckpointMatches[0].Path
$CheckpointDirectory = [System.IO.Path]::GetDirectoryName($CheckpointPath)
$Checkpoint = $CheckpointMatches[0].Payload
$CheckpointOutcomes = @(
    $Checkpoint.outcomes.PSObject.Properties | ForEach-Object { $_.Value }
)
if ([int]$Checkpoint.schema_version -ne 4 -or
    [string]$Checkpoint.request_checksum -ne $RequestChecksum -or
    $CheckpointOutcomes.Count -ne 18 -or
    [string]::IsNullOrWhiteSpace($CheckpointDirectory)) {
    throw "Batch-576 checkpoint contract validation failed"
}

$SuccessOutcomes = @($CheckpointOutcomes | Where-Object { [string]$_.status -eq "SUCCESS" })
$EmptyOutcomes = @($CheckpointOutcomes | Where-Object { [string]$_.status -eq "EMPTY" })
$FailedOutcomes = @($CheckpointOutcomes | Where-Object { [string]$_.status -eq "FAILED" })
$FinalOutcomes = @($CheckpointOutcomes | Where-Object { [string]$_.status -eq "FINAL_FAILED" })
$KnownOutcomeCount = $SuccessOutcomes.Count + $EmptyOutcomes.Count + $FailedOutcomes.Count + $FinalOutcomes.Count
if ($SuccessOutcomes.Count -ne 16 -or
    $EmptyOutcomes.Count -ne 0 -or
    $FailedOutcomes.Count -ne 2 -or
    $FinalOutcomes.Count -ne 0 -or
    $KnownOutcomeCount -ne 18 -or
    ($RequestedItems.Count - $CheckpointOutcomes.Count) -ne 2) {
    throw "Batch-576 checkpoint aggregate mismatch"
}

$VerifiedNoPriceCount = 0
$VerifiedOhlcCount = 0
foreach ($Outcome in $FailedOutcomes) {
    $Category = [string]$Outcome.causal_failure_evidence.category
    $Chain = @($Outcome.causal_failure_evidence.exception_type_chain)
    if ([string]$Outcome.failure_type -eq "APIError" -and
        $Category -eq "NO_PRICE_DATA" -and
        $Chain.Count -ge 2 -and
        [string]$Chain[0] -eq "investment_terminal.utils.exceptions.APIError" -and
        $Chain -contains "yfinance.exceptions.YFPricesMissingError") {
        $VerifiedNoPriceCount += 1
    } elseif ([string]$Outcome.failure_type -eq "YahooCandleInvalidResponseError" -and
        $Category -eq "RESPONSE_OHLC" -and
        $Chain.Count -eq 1 -and
        [string]$Chain[0] -eq "investment_terminal.clients.yahoo_finance_client.YahooCandleInvalidResponseError") {
        $VerifiedOhlcCount += 1
    }
}
if ($VerifiedNoPriceCount -ne 1 -or $VerifiedOhlcCount -ne 1) {
    throw "Batch-576 deferable failure evidence mismatch"
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
        [int]$Starting.sweep_covered_batch_count -ne 575 -or
        [int]$Starting.fully_complete_batch_count -ne 474 -or
        [int]$Starting.remaining_unswept_batch_count -ne 26 -or
        [int]$Starting.deferred_failure_count -ne 118 -or
        $StartingDeferredTypes.Count -ne 2 -or
        $StartingDeferredTypes -notcontains "APIError" -or
        $StartingDeferredTypes -notcontains "YahooCandleInvalidResponseError") {
        throw "Collection sweep starting coverage mismatch"
    }
    foreach ($FailureType in @($Report.ending_coverage.deferred_failure_types)) {
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
    if ([int]$Report.stop_batch_index -lt $BatchIndex -or
        [int]$Report.stop_batch_index -gt $BatchCount -or
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
if ($null -ne $Report.starting_coverage) {
    Write-Host "Starting covered batches: $($Report.starting_coverage.sweep_covered_batch_count)"
    Write-Host "Ending covered batches: $($Report.ending_coverage.sweep_covered_batch_count)"
    Write-Host "Remaining unswept batches: $($Report.ending_coverage.remaining_unswept_batch_count)"
    Write-Host "Deferred failure count: $($Report.ending_coverage.deferred_failure_count)"
}
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

`COMPLETE` is the desired collection outcome: all 601 batches are
sweep-covered and zero remain unswept. Existing and newly encountered
deferable failures remain explicit for the later aggregate inventory.
`HALTED` or `FAILED` is valid safe evidence and must be returned without an
automatic retry or bypass of the recorded stopping category. The command must
also print `SQLite integrity: ok`.

The run is resumable from atomically written private checkpoints. Do not delete
checkpoints, modify the report, or use SQLite row counts as a replacement
progress index.

## Repository Verification

```text
PowerShell block ASCII validation: passed (305 lines)
focused sweep, timeout-retry, causal-inventory, resumable-batch, manifest, and
architecture tests: 76 passed in 2.86s
full test suite: 3146 passed, 4 skipped, 1 warning in 26.45s
git diff --check: clean
```

The warning is the existing Starlette `httpx` deprecation warning and is not a
Package 169 regression. This documentation-only package did not run the private
sweep.

## Next Gate

Return only
`C:\runtime\reports\manifest_collection_sweep_resume_0576_0601_schema2.json`
and the printed `SQLite integrity: ok` line. If collection is complete, build
one redacted aggregate inventory of all deferred and final failures. If it
halts, inspect only the recorded systemic stop before authorizing any retry.
