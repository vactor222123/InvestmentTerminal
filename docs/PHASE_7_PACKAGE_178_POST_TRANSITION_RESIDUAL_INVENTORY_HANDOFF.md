# Phase 7 Package 178 — Post-Transition Residual Inventory Handoff

## Classification

`OPERATIONAL — READY FOR USER EXECUTION`

## Verified Baseline

```text
develop @ fc40dad7c6290a79b7704da962e24e4236349ee2
```

## Scope

Package 177 added the separate read-only
`MANIFEST_POST_TRANSITION_RESIDUAL_INVENTORY` service and CLI. This package
provides one exact-baseline, ASCII-only PowerShell handoff for the private
completed-sweep evidence.

The command verifies the immutable source-inventory and transition-report byte
checksums, canonical manifest binding, complete 601-checkpoint directory, and
expected source aggregates. It hashes every checkpoint before and after the
CLI and fails if any input changes. The command performs no Yahoo request,
SQLite access, retry, terminalization, candle ingestion, or checkpoint write.

## Frozen Evidence

- manifest checksum:
  `8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a`;
- immutable source-inventory SHA-256:
  `1ae8fb0a6b7a915bb0567b6a5b48d1b328adfe6725f282acf203b181fd5c42f6`;
- completed transition-report SHA-256:
  `6e7418e282006a55f3d5a909b02433adbb80066d638e17167cd02b649cc17d57`;
- transition policy:
  `COMPLETED_SWEEP_STORED_YAHOO_NO_PRICE_DATA_V1`;
- expected current state: 12,019 outcomes, 11,892 successes, 11 retryable
  failures, and 116 final failures;
- expected residual cohort: eight `RESPONSE_OHLC`, two `RESPONSE_NUMERIC`, and
  one legacy null-causal outcome;
- expected final cohort: 113 transition-policy finals and three other finals.

The manifest checksum is canonical parsed-JSON evidence, not a raw file hash.
The CLI owns canonical manifest validation. The two source-report checksums are
defined over their exact file bytes and are verified with `Get-FileHash`.

## Run Once in Windows PowerShell

Run this block after Package 178 is checked out. It refuses a wrong baseline,
dirty worktree, changed source document, ambiguous checkpoint directory,
incomplete checkpoint set, existing output report, or inconsistent result.

```powershell
$ErrorActionPreference = "Stop"

$Repository = "C:\Users\tu\Desktop\InvestmentTerminal"
$ExpectedHead = "fc40dad7c6290a79b7704da962e24e4236349ee2"
$ExpectedBranch = "develop"
$ManifestPath = "C:\runtime\data\market_batch_manifest_10y.json"
$CheckpointSearchRoot = "C:\runtime\data"
$InventoryPath = "C:\runtime\reports\manifest_collection_failure_inventory_001.json"
$TransitionReportPath = "C:\runtime\reports\manifest_completed_sweep_no_price_transition_001.json"
$ReportDirectory = "C:\runtime\reports"
$ReportPath = Join-Path $ReportDirectory "manifest_post_transition_residual_inventory_001.json"

$ManifestChecksum = "8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a"
$InventoryChecksum = "1ae8fb0a6b7a915bb0567b6a5b48d1b328adfe6725f282acf203b181fd5c42f6"
$TransitionReportChecksum = "6e7418e282006a55f3d5a909b02433adbb80066d638e17167cd02b649cc17d57"
$Batch576RequestChecksum = "0b025a4862ff8e26cb00cbfc11f242227478a78e8385a82d4671a7543edd6fcb"
$ExpectedPolicy = "COMPLETED_SWEEP_STORED_YAHOO_NO_PRICE_DATA_V1"
$ExpectedBatchCount = 601
$ExpectedRequestedCount = 12019
$ExpectedSuccessCount = 11892
$ExpectedRetryableCount = 11
$ExpectedFinalCount = 116
$ExpectedTransitionFinalCount = 113
$ExpectedOtherFinalCount = 3

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

foreach ($RequiredPath in @($ManifestPath, $InventoryPath, $TransitionReportPath)) {
    if (-not (Test-Path -LiteralPath $RequiredPath -PathType Leaf)) {
        throw "Required input is missing: $RequiredPath"
    }
}
if (-not (Test-Path -LiteralPath $CheckpointSearchRoot -PathType Container)) {
    throw "Checkpoint search root is missing: $CheckpointSearchRoot"
}
if (Test-Path -LiteralPath $ReportPath) {
    throw "Refusing to overwrite existing report: $ReportPath"
}
if (-not (Test-Path -LiteralPath $ReportDirectory -PathType Container)) {
    New-Item -ItemType Directory -Path $ReportDirectory -Force | Out-Null
}

$ActualInventoryChecksum = (
    Get-FileHash -LiteralPath $InventoryPath -Algorithm SHA256
).Hash.ToLowerInvariant()
if ($ActualInventoryChecksum -ne $InventoryChecksum) {
    throw "Inventory checksum mismatch"
}

$ActualTransitionChecksum = (
    Get-FileHash -LiteralPath $TransitionReportPath -Algorithm SHA256
).Hash.ToLowerInvariant()
if ($ActualTransitionChecksum -ne $TransitionReportChecksum) {
    throw "Transition report checksum mismatch"
}

try {
    $Manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 |
        ConvertFrom-Json
    $Inventory = Get-Content -LiteralPath $InventoryPath -Raw -Encoding UTF8 |
        ConvertFrom-Json
    $Transition = Get-Content -LiteralPath $TransitionReportPath -Raw -Encoding UTF8 |
        ConvertFrom-Json
} catch {
    throw "Could not parse a required JSON input"
}

$Batches = @($Manifest.batches)
$ManifestRequestedCount = (
    $Batches | ForEach-Object { @($_.request.items).Count } |
        Measure-Object -Sum
).Sum
if ($Batches.Count -ne $ExpectedBatchCount -or
    [int]$ManifestRequestedCount -ne $ExpectedRequestedCount -or
    [string]$Batches[575].request_checksum -ne $Batch576RequestChecksum) {
    throw "Manifest binding validation failed"
}

$InventoryCoverage = $Inventory.coverage
if ([int]$Inventory.schema_version -ne 1 -or
    [string]$Inventory.operation_identity -ne "MANIFEST_COLLECTION_FAILURE_INVENTORY" -or
    [string]$Inventory.provider_identity -ne "YAHOO_FINANCE" -or
    [string]$Inventory.status -ne "SUCCESS" -or
    [string]$Inventory.manifest_checksum -ne $ManifestChecksum -or
    [int]$InventoryCoverage.batch_count -ne $ExpectedBatchCount -or
    [int]$InventoryCoverage.requested_count -ne $ExpectedRequestedCount -or
    [int]$InventoryCoverage.checkpoint_outcome_count -ne $ExpectedRequestedCount -or
    [int]$InventoryCoverage.missing_count -ne 0 -or
    [int]$InventoryCoverage.success_count -ne $ExpectedSuccessCount -or
    [int]$InventoryCoverage.empty_count -ne 0 -or
    [int]$InventoryCoverage.retryable_failure_count -ne 124 -or
    [int]$InventoryCoverage.final_failure_count -ne 3 -or
    [int]$InventoryCoverage.blocking_failure_count -ne 0 -or
    $null -ne $Inventory.failure) {
    throw "Source inventory contract validation failed"
}

$TransitionEnding = $Transition.ending_coverage
if ([int]$Transition.schema_version -ne 1 -or
    [string]$Transition.operation_identity -ne "MANIFEST_COMPLETED_SWEEP_NO_PRICE_TRANSITION" -or
    [string]$Transition.provider_identity -ne "YAHOO_FINANCE" -or
    [string]$Transition.status -ne "COMPLETE" -or
    [string]$Transition.manifest_checksum -ne $ManifestChecksum -or
    [string]$Transition.inventory_checksum -ne $InventoryChecksum -or
    [string]$Transition.isolation_policy_identity -ne $ExpectedPolicy -or
    [int]$TransitionEnding.eligible_count -ne $ExpectedTransitionFinalCount -or
    [int]$TransitionEnding.final_count -ne $ExpectedTransitionFinalCount -or
    [int]$TransitionEnding.remaining_count -ne 0 -or
    $null -ne $Transition.failure) {
    throw "Transition report contract validation failed"
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
        $CheckpointMatches += [System.IO.Path]::GetDirectoryName($Candidate.FullName)
    }
}
$CheckpointMatches = @($CheckpointMatches | Sort-Object -Unique)
if ($CheckpointMatches.Count -ne 1) {
    throw "Could not uniquely identify the request-bound checkpoint directory"
}
$CheckpointDirectory = [string]$CheckpointMatches[0]

$CheckpointPaths = @()
$BeforeHashes = @{}
for ($BatchIndex = 1; $BatchIndex -le $ExpectedBatchCount; $BatchIndex++) {
    $CheckpointPath = Join-Path $CheckpointDirectory ("batch_{0:D4}.json" -f $BatchIndex)
    if (-not (Test-Path -LiteralPath $CheckpointPath -PathType Leaf)) {
        throw "The completed checkpoint set is incomplete"
    }
    $CheckpointPaths += $CheckpointPath
    $BeforeHashes[[string]$BatchIndex] = (
        Get-FileHash -LiteralPath $CheckpointPath -Algorithm SHA256
    ).Hash.ToLowerInvariant()
}

python -m investment_terminal.cli.manifest_post_transition_residual_inventory `
    --manifest $ManifestPath `
    --manifest-checksum $ManifestChecksum `
    --checkpoint-directory $CheckpointDirectory `
    --inventory $InventoryPath `
    --inventory-checksum $InventoryChecksum `
    --transition-report $TransitionReportPath `
    --transition-report-checksum $TransitionReportChecksum `
    --report-output $ReportPath `
    --json
$CommandExitCode = $LASTEXITCODE

if (-not (Test-Path -LiteralPath $ReportPath -PathType Leaf)) {
    throw "Residual inventory did not produce a report"
}
try {
    $Report = Get-Content -LiteralPath $ReportPath -Raw -Encoding UTF8 |
        ConvertFrom-Json
} catch {
    throw "Could not parse the residual inventory report"
}

for ($BatchIndex = 1; $BatchIndex -le $ExpectedBatchCount; $BatchIndex++) {
    $AfterHash = (
        Get-FileHash -LiteralPath $CheckpointPaths[$BatchIndex - 1] -Algorithm SHA256
    ).Hash.ToLowerInvariant()
    if ($AfterHash -ne $BeforeHashes[[string]$BatchIndex]) {
        throw "A checkpoint changed during read-only inventory"
    }
}

if ($CommandExitCode -ne 0) {
    if ([string]$Report.status -eq "FAILED") {
        Write-Host "SEND: $ReportPath"
    }
    throw "Post-transition residual inventory failed with exit code $CommandExitCode"
}

$Coverage = $Report.coverage
if ([int]$Report.schema_version -ne 1 -or
    [string]$Report.operation_identity -ne "MANIFEST_POST_TRANSITION_RESIDUAL_INVENTORY" -or
    [string]$Report.provider_identity -ne "YAHOO_FINANCE" -or
    [string]$Report.status -ne "SUCCESS" -or
    [string]$Report.manifest_checksum -ne $ManifestChecksum -or
    [string]$Report.source_inventory_checksum -ne $InventoryChecksum -or
    [string]$Report.transition_report_checksum -ne $TransitionReportChecksum -or
    [string]$Report.isolation_policy_identity -ne $ExpectedPolicy -or
    [int]$Coverage.batch_count -ne $ExpectedBatchCount -or
    [int]$Coverage.requested_count -ne $ExpectedRequestedCount -or
    [int]$Coverage.checkpoint_outcome_count -ne $ExpectedRequestedCount -or
    [int]$Coverage.missing_count -ne 0 -or
    [int]$Coverage.success_count -ne $ExpectedSuccessCount -or
    [int]$Coverage.empty_count -ne 0 -or
    [int]$Coverage.retryable_failure_count -ne $ExpectedRetryableCount -or
    [int]$Coverage.final_failure_count -ne $ExpectedFinalCount -or
    [int]$Coverage.transition_policy_final_count -ne $ExpectedTransitionFinalCount -or
    [int]$Coverage.other_final_failure_count -ne $ExpectedOtherFinalCount -or
    $null -ne $Report.failure) {
    throw "Residual inventory coverage validation failed"
}

$ResidualSignatures = @($Report.residual_causal_signatures)
$ResidualTotal = ($ResidualSignatures | Measure-Object -Property count -Sum).Sum
$OhlcCount = (
    $ResidualSignatures |
        Where-Object { [string]$_.category -eq "RESPONSE_OHLC" } |
        Measure-Object -Property count -Sum
).Sum
$NumericCount = (
    $ResidualSignatures |
        Where-Object { [string]$_.category -eq "RESPONSE_NUMERIC" } |
        Measure-Object -Property count -Sum
).Sum
$LegacySignatures = @(
    $ResidualSignatures |
        Where-Object { $null -eq $_.category }
)
$LegacyCount = ($LegacySignatures | Measure-Object -Property count -Sum).Sum
foreach ($Signature in $ResidualSignatures) {
    if ([string]$Signature.source_disposition -ne "DEFERABLE" -or
        [int]$Signature.count -le 0 -or
        @($null, "RESPONSE_OHLC", "RESPONSE_NUMERIC") -notcontains $Signature.category) {
        throw "Residual signature validation failed"
    }
}
foreach ($Signature in $LegacySignatures) {
    if (@($Signature.exception_type_chain).Count -ne 0) {
        throw "Legacy null-causal signature contains an unexpected type chain"
    }
}
if ([int]$ResidualTotal -ne $ExpectedRetryableCount -or
    [int]$OhlcCount -ne 8 -or
    [int]$NumericCount -ne 2 -or
    [int]$LegacyCount -ne 1) {
    throw "Residual signature totals are inconsistent"
}

$FinalSignatures = @($Report.final_failure_signatures)
$FinalSignatureTotal = ($FinalSignatures | Measure-Object -Property count -Sum).Sum
$TransitionFinalSignatureCount = (
    $FinalSignatures |
        Where-Object {
            [string]$_.isolation_policy_identity -eq $ExpectedPolicy -and
            [string]$_.category -eq "NO_PRICE_DATA"
        } |
        Measure-Object -Property count -Sum
).Sum
if ([int]$FinalSignatureTotal -ne $ExpectedFinalCount -or
    [int]$TransitionFinalSignatureCount -ne $ExpectedTransitionFinalCount) {
    throw "Final signature totals are inconsistent"
}

$ReportHash = (
    Get-FileHash -LiteralPath $ReportPath -Algorithm SHA256
).Hash.ToLowerInvariant()

Write-Host "Residual inventory status: $($Report.status)"
Write-Host "Requested outcomes: $($Coverage.requested_count)"
Write-Host "Retryable failures: $($Coverage.retryable_failure_count)"
Write-Host "Final failures: $($Coverage.final_failure_count)"
Write-Host "Transition-policy finals: $($Coverage.transition_policy_final_count)"
Write-Host "Other finals: $($Coverage.other_final_failure_count)"
Write-Host "Report: $ReportPath"
Write-Host "Report SHA-256: $ReportHash"
Write-Host "SEND: $ReportPath"
Write-Host "DO NOT SEND: $ManifestPath"
Write-Host "DO NOT SEND: $CheckpointDirectory"
Write-Host "DO NOT SEND: $InventoryPath"
Write-Host "DO NOT SEND: $TransitionReportPath"
```

## Expected Evidence

A successful report must bind both immutable source checksums and account for
all 12,019 outcomes: 11,892 successes, zero empty or missing outcomes, 11
retryable failures, 116 final failures, 113 transition-policy finals, and three
other finals. Residual signatures must reconcile to eight OHLC, two numeric,
and one null-causal outcome. All 601 checkpoint hashes must remain unchanged.

If the CLI emits a redacted `FAILED` report, return that report and do not
rerun automatically. The failure is evidence for the next review gate.

## Repository Verification

```text
PowerShell block ASCII validation: passed (290 lines)
focused residual-inventory, transition, collection-inventory,
resumable-batch, CLI, and architecture tests: 63 passed in 2.83s
full test suite: 3178 passed, 4 skipped, 1 warning in 28.14s
git diff --check: clean
```

The warning is the existing Starlette `httpx` deprecation warning and is not a
Package 178 regression. This documentation-only package did not inspect or
mutate private runtime data.

## Next Gate

Return only:

```text
C:\runtime\reports\manifest_post_transition_residual_inventory_001.json
```

Do not send the manifest, checkpoint files, source inventory, or transition
report. Review the redacted aggregate evidence before selecting separate
numeric/OHLC diagnostics or a distinct legacy-null remediation path.
