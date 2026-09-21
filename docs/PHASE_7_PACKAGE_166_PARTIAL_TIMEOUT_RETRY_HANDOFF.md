# Phase 7 Package 166 — Partial Timeout Retry Handoff

## Classification

`OPERATIONAL — READY FOR USER EXECUTION`

## Verified Baseline

```text
develop @ 440dd4856437ee9eeac1321778130f4129fbe99d
```

## Package 167 Execution Rebaseline

Package 166 was applied before its operational block was run. Package 167
therefore rebinds only the command's repository guard to the new exact GitHub
baseline:

```text
develop @ f3ed7bac471f598fc368d4a1b309fc4982c16848
```

No runtime binding, checksum, selected operation, validation rule, report
contract, or scope permission changes.

## Scope

Package 165 implemented one evidence-bound attempt for the unique blocking
timeout in partial batch 576. The operation validates the immutable aggregate
inventory and current schema-4 checkpoint before composing SQLite or Yahoo,
then replaces only the selected timeout outcome.

The command below verifies the exact repository state, private manifest,
unique request-bound checkpoint, immutable causal-inventory bytes, all three
stored causal signatures, and the pre-run aggregate shape. After exactly one
retry it validates the redacted report, proves that the other 17 outcomes and
two missing members were preserved, and performs a read-only SQLite integrity
check. It does not resume the collection sweep or execute batch 577.

## Execution Order

Run this block **before applying Package 167**. It deliberately requires the
Package 166 GitHub baseline recorded in the rebaseline section above. The
PowerShell source and all emitted command messages are ASCII-only.

```powershell
$ErrorActionPreference = "Stop"

$Repository = "C:\Users\tu\Desktop\InvestmentTerminal"
$ExpectedHead = "f3ed7bac471f598fc368d4a1b309fc4982c16848"
$ExpectedBranch = "develop"
$ManifestPath = "C:\runtime\data\market_batch_manifest_10y.json"
$CheckpointSearchRoot = "C:\runtime\data"
$InventoryPath = "C:\runtime\reports\manifest_batch_0576_partial_causal_inventory_001.json"
$DatabasePath = "C:\runtime\data\investment_terminal.db"
$CacheDirectory = "C:\runtime\cache\yfinance"
$ReportDirectory = "C:\runtime\reports"
$ReportPath = Join-Path $ReportDirectory "manifest_batch_0576_timeout_retry_001.json"
$ManifestChecksum = "8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a"
$RequestChecksum = "0b025a4862ff8e26cb00cbfc11f242227478a78e8385a82d4671a7543edd6fcb"
$InventoryChecksum = "67fd4eca4ede8205c5e669a44d70cbd269601227c7a939b80b5776d29d35e069"
$BatchIndex = 576
$BatchCount = 601

function Test-ExactChain {
    param([object[]]$Actual, [string[]]$Expected)
    if ($Actual.Count -ne $Expected.Count) {
        return $false
    }
    for ($Index = 0; $Index -lt $Expected.Count; $Index++) {
        if ([string]$Actual[$Index] -ne $Expected[$Index]) {
            return $false
        }
    }
    return $true
}

function Test-DeferableOutcome {
    param([object]$Outcome)
    if ([string]$Outcome.status -ne "FAILED") {
        return $false
    }
    if ([string]$Outcome.failure_type -eq "YahooCandleInvalidResponseError") {
        return $true
    }
    if ([string]$Outcome.failure_type -ne "APIError" -or
        $null -eq $Outcome.causal_failure_evidence -or
        [string]$Outcome.causal_failure_evidence.category -ne "NO_PRICE_DATA") {
        return $false
    }
    $Chain = @($Outcome.causal_failure_evidence.exception_type_chain)
    if ($Chain.Count -eq 0 -or
        [string]$Chain[0] -ne "investment_terminal.utils.exceptions.APIError") {
        return $false
    }
    $HasMissingPrice = $false
    foreach ($TypeName in $Chain) {
        if ([string]$TypeName -eq "UNRECOGNIZED_EXCEPTION_TYPE" -or
            [string]$TypeName -eq "EXCEPTION_CHAIN_TRUNCATED") {
            return $false
        }
        if ([string]$TypeName -eq "yfinance.exceptions.YFPricesMissingError") {
            $HasMissingPrice = $true
        }
    }
    return $HasMissingPrice
}

function Get-OutcomeCoverage {
    param([object[]]$Outcomes)
    $Success = 0
    $Empty = 0
    $Retryable = 0
    $Final = 0
    $Deferable = 0
    foreach ($Outcome in $Outcomes) {
        switch ([string]$Outcome.status) {
            "SUCCESS" { $Success++ }
            "EMPTY" { $Empty++ }
            "FAILED" { $Retryable++ }
            "FINAL_FAILED" { $Final++ }
            default { throw "Checkpoint contains an unsupported status" }
        }
        if (Test-DeferableOutcome -Outcome $Outcome) {
            $Deferable++
        }
    }
    return [pscustomobject]@{
        success_count = $Success
        empty_count = $Empty
        retryable_failure_count = $Retryable
        final_failure_count = $Final
        deferable_failure_count = $Deferable
        blocking_failure_count = $Retryable - $Deferable
    }
}

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

foreach ($RequiredPath in @($ManifestPath, $InventoryPath, $DatabasePath)) {
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

$ActualInventoryChecksum = (
    Get-FileHash -LiteralPath $InventoryPath -Algorithm SHA256
).Hash.ToLowerInvariant()
if ($ActualInventoryChecksum -ne $InventoryChecksum) {
    throw "Causal inventory checksum mismatch"
}
try {
    $Manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 |
        ConvertFrom-Json
    $Inventory = Get-Content -LiteralPath $InventoryPath -Raw -Encoding UTF8 |
        ConvertFrom-Json
} catch {
    throw "Could not parse the manifest or causal inventory"
}

$SelectedBatches = @($Manifest.batches | Where-Object {
    [int]$_.batch_index -eq $BatchIndex
})
if ($SelectedBatches.Count -ne 1 -or @($Manifest.batches).Count -ne $BatchCount) {
    throw "Could not uniquely identify batch 576 in the manifest"
}
$SelectedBatch = $SelectedBatches[0]
$RequestedItems = @($SelectedBatch.request.items)
$RequestedStart = [string]$SelectedBatch.request.start
$RequestedEnd = [string]$SelectedBatch.request.end
if ([string]$SelectedBatch.request_checksum -ne $RequestChecksum -or
    $RequestedItems.Count -ne 20) {
    throw "Manifest batch-576 binding validation failed"
}

$InventoryCoverage = $Inventory.coverage
if ([int]$Inventory.schema_version -ne 1 -or
    [string]$Inventory.operation_identity -ne "MANIFEST_PARTIAL_CAUSAL_INVENTORY" -or
    [string]$Inventory.provider_identity -ne "YAHOO_FINANCE" -or
    [string]$Inventory.status -ne "SUCCESS" -or
    [string]$Inventory.manifest_checksum -ne $ManifestChecksum -or
    [int]$Inventory.batch_index -ne $BatchIndex -or
    [int]$Inventory.batch_count -ne $BatchCount -or
    [string]$Inventory.request_checksum -ne $RequestChecksum -or
    [string]$Inventory.requested_start -ne $RequestedStart -or
    [string]$Inventory.requested_end -ne $RequestedEnd -or
    [int]$InventoryCoverage.requested_count -ne 20 -or
    [int]$InventoryCoverage.checkpoint_outcome_count -ne 18 -or
    [int]$InventoryCoverage.missing_count -ne 2 -or
    [int]$InventoryCoverage.success_count -ne 15 -or
    [int]$InventoryCoverage.empty_count -ne 0 -or
    [int]$InventoryCoverage.retryable_failure_count -ne 3 -or
    [int]$InventoryCoverage.final_failure_count -ne 0 -or
    [int]$InventoryCoverage.deferable_failure_count -ne 2 -or
    [int]$InventoryCoverage.blocking_failure_count -ne 1 -or
    $null -ne $Inventory.failure) {
    throw "Causal inventory contract validation failed"
}

$ExpectedTimeoutChain = @(
    "investment_terminal.utils.exceptions.APIError",
    "curl_cffi.requests.exceptions.Timeout",
    "curl_cffi.curl.CurlError"
)
$ExpectedNoPriceChain = @(
    "investment_terminal.utils.exceptions.APIError",
    "yfinance.exceptions.YFPricesMissingError"
)
$ExpectedOhlcChain = @(
    "investment_terminal.clients.yahoo_finance_client.YahooCandleInvalidResponseError"
)
$TimeoutSignatureCount = 0
$NoPriceSignatureCount = 0
$OhlcSignatureCount = 0
foreach ($Signature in @($Inventory.causal_signatures)) {
    $Chain = @($Signature.exception_type_chain)
    if ([string]$Signature.category -eq "TIMEOUT" -and
        [string]$Signature.sweep_disposition -eq "BLOCKING" -and
        [int]$Signature.count -eq 1 -and
        (Test-ExactChain -Actual $Chain -Expected $ExpectedTimeoutChain)) {
        $TimeoutSignatureCount++
    } elseif ([string]$Signature.category -eq "NO_PRICE_DATA" -and
        [string]$Signature.sweep_disposition -eq "DEFERABLE" -and
        [int]$Signature.count -eq 1 -and
        (Test-ExactChain -Actual $Chain -Expected $ExpectedNoPriceChain)) {
        $NoPriceSignatureCount++
    } elseif ([string]$Signature.category -eq "RESPONSE_OHLC" -and
        [string]$Signature.sweep_disposition -eq "DEFERABLE" -and
        [int]$Signature.count -eq 1 -and
        (Test-ExactChain -Actual $Chain -Expected $ExpectedOhlcChain)) {
        $OhlcSignatureCount++
    } else {
        throw "Causal inventory contains an unexpected signature"
    }
}
if (@($Inventory.causal_signatures).Count -ne 3 -or
    $TimeoutSignatureCount -ne 1 -or
    $NoPriceSignatureCount -ne 1 -or
    $OhlcSignatureCount -ne 1) {
    throw "Causal inventory signature validation failed"
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
$Checkpoint = $CheckpointMatches[0].Payload
$OutcomeProperties = @($Checkpoint.outcomes.PSObject.Properties)
if ([int]$Checkpoint.schema_version -ne 4 -or
    [string]$Checkpoint.request_checksum -ne $RequestChecksum -or
    $OutcomeProperties.Count -ne 18) {
    throw "Batch-576 checkpoint contract validation failed"
}

$RequestedIdentities = @{}
foreach ($Item in $RequestedItems) {
    $RequestedIdentities[[string]$Item.symbol] = $true
}
$TimeoutCandidates = @()
$BeforeOtherOutcomes = @{}
foreach ($Property in $OutcomeProperties) {
    if (-not $RequestedIdentities.ContainsKey([string]$Property.Name)) {
        throw "Checkpoint contains an outcome outside batch 576"
    }
    $Outcome = $Property.Value
    $Chain = @($Outcome.causal_failure_evidence.exception_type_chain)
    $IsTimeout = (
        [string]$Outcome.status -eq "FAILED" -and
        [string]$Outcome.failure_type -eq "APIError" -and
        [string]$Outcome.causal_failure_evidence.category -eq "TIMEOUT" -and
        (Test-ExactChain -Actual $Chain -Expected $ExpectedTimeoutChain)
    )
    if ($IsTimeout) {
        $TimeoutCandidates += $Property
    } else {
        $BeforeOtherOutcomes[[string]$Property.Name] = (
            $Outcome | ConvertTo-Json -Depth 20 -Compress
        )
    }
}
if ($TimeoutCandidates.Count -ne 1) {
    throw "Checkpoint does not contain one unique inventory-bound timeout"
}
$TargetIdentity = [string]$TimeoutCandidates[0].Name
$BeforeCoverage = Get-OutcomeCoverage -Outcomes @(
    $OutcomeProperties | ForEach-Object { $_.Value }
)
if ([int]$BeforeCoverage.success_count -ne 15 -or
    [int]$BeforeCoverage.empty_count -ne 0 -or
    [int]$BeforeCoverage.retryable_failure_count -ne 3 -or
    [int]$BeforeCoverage.final_failure_count -ne 0 -or
    [int]$BeforeCoverage.deferable_failure_count -ne 2 -or
    [int]$BeforeCoverage.blocking_failure_count -ne 1) {
    throw "Batch-576 checkpoint aggregate validation failed"
}
$CheckpointBeforeHash = (
    Get-FileHash -LiteralPath $CheckpointPath -Algorithm SHA256
).Hash.ToLowerInvariant()

New-Item -ItemType Directory -Force -Path $CacheDirectory | Out-Null
New-Item -ItemType Directory -Force -Path $ReportDirectory | Out-Null

python -m investment_terminal.cli.manifest_partial_timeout_retry `
    --manifest $ManifestPath `
    --manifest-checksum $ManifestChecksum `
    --batch-index $BatchIndex `
    --checkpoint $CheckpointPath `
    --inventory $InventoryPath `
    --inventory-checksum $InventoryChecksum `
    --database $DatabasePath `
    --cache-directory $CacheDirectory `
    --report-output $ReportPath `
    --json
$CommandExitCode = $LASTEXITCODE

if (-not (Test-Path -LiteralPath $ReportPath -PathType Leaf)) {
    throw "Partial timeout retry did not produce a report"
}
try {
    $Report = Get-Content -LiteralPath $ReportPath -Raw -Encoding UTF8 |
        ConvertFrom-Json
} catch {
    throw "Could not parse the partial timeout retry report"
}

$AllowedStatuses = @("READY_FOR_SWEEP", "BLOCKED", "FAILED")
if ([int]$Report.schema_version -ne 1 -or
    [string]$Report.operation_identity -ne "MANIFEST_PARTIAL_TIMEOUT_RETRY" -or
    [string]$Report.provider_identity -ne "YAHOO_FINANCE" -or
    $AllowedStatuses -notcontains [string]$Report.status) {
    throw "Partial timeout retry report contract validation failed"
}

if ([string]$Report.status -eq "FAILED") {
    $CheckpointAfterHash = (
        Get-FileHash -LiteralPath $CheckpointPath -Algorithm SHA256
    ).Hash.ToLowerInvariant()
    if ($CommandExitCode -eq 0 -or
        $CheckpointAfterHash -ne $CheckpointBeforeHash -or
        $null -ne $Report.inventory_checksum -or
        $null -ne $Report.coverage -or
        $null -ne $Report.retry_result -or
        $null -eq $Report.failure) {
        throw "Failed partial timeout retry evidence is inconsistent"
    }
} else {
    if ([string]$Report.manifest_checksum -ne $ManifestChecksum -or
        [int]$Report.batch_index -ne $BatchIndex -or
        [int]$Report.batch_count -ne $BatchCount -or
        [string]$Report.request_checksum -ne $RequestChecksum -or
        [string]$Report.requested_start -ne $RequestedStart -or
        [string]$Report.requested_end -ne $RequestedEnd -or
        [string]$Report.inventory_checksum -ne $InventoryChecksum -or
        $null -ne $Report.failure) {
        throw "Partial timeout retry report binding validation failed"
    }

    $Coverage = $Report.coverage
    $ReportBefore = $Coverage.before
    if ([int]$Coverage.requested_count -ne 20 -or
        [int]$Coverage.checkpoint_outcome_count -ne 18 -or
        [int]$Coverage.missing_count -ne 2 -or
        [int]$Coverage.selected_count -ne 1 -or
        [int]$Coverage.attempted_count -ne 1 -or
        [int]$Coverage.unchanged_outcome_count -ne 17 -or
        [int]$ReportBefore.success_count -ne 15 -or
        [int]$ReportBefore.empty_count -ne 0 -or
        [int]$ReportBefore.retryable_failure_count -ne 3 -or
        [int]$ReportBefore.final_failure_count -ne 0 -or
        [int]$ReportBefore.deferable_failure_count -ne 2 -or
        [int]$ReportBefore.blocking_failure_count -ne 1) {
        throw "Partial timeout retry coverage validation failed"
    }

    try {
        $CheckpointAfter = Get-Content -LiteralPath $CheckpointPath -Raw -Encoding UTF8 |
            ConvertFrom-Json
    } catch {
        throw "Could not parse the updated batch-576 checkpoint"
    }
    $AfterProperties = @($CheckpointAfter.outcomes.PSObject.Properties)
    if ([int]$CheckpointAfter.schema_version -ne 4 -or
        [string]$CheckpointAfter.request_checksum -ne $RequestChecksum -or
        $AfterProperties.Count -ne 18) {
        throw "Updated batch-576 checkpoint contract validation failed"
    }
    foreach ($Property in $AfterProperties) {
        $Name = [string]$Property.Name
        if ($Name -eq $TargetIdentity) {
            continue
        }
        if (-not $BeforeOtherOutcomes.ContainsKey($Name) -or
            ($Property.Value | ConvertTo-Json -Depth 20 -Compress) -ne $BeforeOtherOutcomes[$Name]) {
            throw "A non-target checkpoint outcome changed"
        }
    }
    if ($BeforeOtherOutcomes.Count -ne 17) {
        throw "Non-target checkpoint preservation validation failed"
    }

    $TargetAfterProperties = @($CheckpointAfter.outcomes.PSObject.Properties | Where-Object {
        [string]$_.Name -eq $TargetIdentity
    })
    if ($TargetAfterProperties.Count -ne 1) {
        throw "Updated timeout outcome is missing"
    }
    $TargetAfter = $TargetAfterProperties[0].Value
    if ([string]$TargetAfter.status -ne [string]$Report.retry_result.status -or
        $TargetAfter.downloaded -ne $Report.retry_result.downloaded -or
        $TargetAfter.inserted -ne $Report.retry_result.inserted -or
        $TargetAfter.duplicates -ne $Report.retry_result.duplicates -or
        [int]$TargetAfter.omitted_trailing_count -ne [int]$Report.retry_result.omitted_trailing_count) {
        throw "Updated timeout outcome does not match the redacted report"
    }
    if ([string]$TargetAfter.status -eq "FAILED") {
        $TargetChain = @($TargetAfter.causal_failure_evidence.exception_type_chain)
        $ReportChain = @($Report.retry_result.exception_type_chain)
        if ([string]$TargetAfter.causal_failure_evidence.category -ne
                [string]$Report.retry_result.failure_category -or
            -not (Test-ExactChain -Actual $TargetChain -Expected $ReportChain)) {
            throw "Updated failure evidence does not match the redacted report"
        }
    }

    $AfterCoverage = Get-OutcomeCoverage -Outcomes @(
        $AfterProperties | ForEach-Object { $_.Value }
    )
    $ReportAfter = $Coverage.after
    foreach ($Field in @(
        "success_count",
        "empty_count",
        "retryable_failure_count",
        "final_failure_count",
        "deferable_failure_count",
        "blocking_failure_count"
    )) {
        if ([int]$AfterCoverage.$Field -ne [int]$ReportAfter.$Field) {
            throw "Updated checkpoint aggregate does not match the report"
        }
    }

    if ([string]$Report.status -eq "READY_FOR_SWEEP") {
        if ($CommandExitCode -ne 0 -or
            [int]$ReportAfter.blocking_failure_count -ne 0 -or
            @("CLEARED", "DEFERABLE") -notcontains
                [string]$Report.retry_result.sweep_disposition) {
            throw "Ready partial timeout retry evidence is inconsistent"
        }
    } elseif ([string]$Report.status -eq "BLOCKED") {
        if ($CommandExitCode -eq 0 -or
            [int]$ReportAfter.blocking_failure_count -ne 1 -or
            [string]$Report.retry_result.sweep_disposition -ne "BLOCKING") {
            throw "Blocked partial timeout retry evidence is inconsistent"
        }
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
Write-Host "Partial timeout retry status: $($Report.status)"
if ($null -ne $Report.retry_result) {
    Write-Host "Retry disposition: $($Report.retry_result.sweep_disposition)"
    Write-Host "Blocking failures after retry: $($Report.coverage.after.blocking_failure_count)"
}
Write-Host "SQLite integrity: $Integrity"
Write-Host "Report: $ReportPath"
Write-Host "Report SHA-256: $ReportHash"
Write-Host "SEND: $ReportPath"
Write-Host "SEND: SQLite integrity: $Integrity"
Write-Host "DO NOT SEND: $ManifestPath"
Write-Host "DO NOT SEND: $CheckpointPath"
Write-Host "DO NOT SEND: $DatabasePath"
Write-Host "DO NOT SEND: $CacheDirectory"
Write-Host "Do not resume the collection sweep until this report is reviewed"
```

## Expected Evidence

`READY_FOR_SWEEP` means the unique blocking timeout either cleared or became a
recognized deferable failure. It does not itself authorize the sweep. `BLOCKED`
means the retry still has systemic evidence and must not be repeated blindly.
`FAILED` means validation, I/O, or checkpoint publication failed; the command
requires the checkpoint bytes to remain unchanged in that case. All three
statuses are redacted evidence to return for review together with the printed
`SQLite integrity: ok` line.

The two pre-existing deferable failures and all 15 pre-existing successes must
remain byte-equivalent as JSON values. The batch stays a proper partial
checkpoint with exactly two missing members; this command never processes them.

## Scope Exclusions

- no collection-sweep resume or execution of batches 577–601;
- no retry of the existing no-price or OHLC failures;
- no automatic retry loop, sleep, timeout deferral, or final exclusion;
- no disclosure of private identities, manifest, checkpoint, SQLite, or cache;
- no analysis, ranking, recommendation, or trading authority.

## Repository Verification

```text
PowerShell block ASCII validation: passed (483 lines)
focused timeout-retry, causal-inventory, sweep, resumable-batch, manifest, and
architecture tests: 81 passed in 4.06s
full test suite: 3146 passed, 4 skipped, 1 warning in 31.91s
git diff --check: clean
```

The warning is the existing Starlette `httpx` deprecation warning and is not a
Package 166 regression. No private runtime input was read and the operational
command was not executed while preparing this documentation-only package.

## Next Gate

Return only
`C:\runtime\reports\manifest_batch_0576_timeout_retry_001.json` and the printed
`SQLite integrity: ok` line. Review the redacted retry disposition before
designing or authorizing any remaining collection sweep.
