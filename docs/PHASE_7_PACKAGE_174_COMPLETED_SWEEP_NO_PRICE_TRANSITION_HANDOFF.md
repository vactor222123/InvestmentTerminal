# Phase 7 Package 174: completed-sweep `NO_PRICE_DATA` transition handoff

## Purpose

Package 173 added the bounded, resumable transition that converts only the 113
immutable-inventory outcomes proven to be stored Yahoo `NO_PRICE_DATA` into the
existing final-isolation contract. Package 174 does not change that contract.
It provides the single operational handoff needed to run the transition against
the private completed-sweep checkpoint set and to validate the privacy-safe
result locally.

This handoff deliberately does not touch SQLite. The operation changes only the
manifest checkpoint files selected by the immutable inventory. Success means
that all 113 eligible outcomes are final, the 11 intentionally preserved
retryable outcomes remain outside this transition, and a privacy-safe report is
available for review.

## Frozen evidence

- repository baseline: `281b057c46dc8bf24f5c29fb9188b346377d594b`
- branch: `develop`
- completed manifest checksum:
  `8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a`
- immutable failure-inventory checksum:
  `1ae8fb0a6b7a915bb0567b6a5b48d1b328adfe6725f282acf203b181fd5c42f6`
- immutable failure inventory: 124 retryable, 3 final, 0 blocking
- eligible stored Yahoo `NO_PRICE_DATA`: 113
- preserved retryable outcomes: 11
- expected final outcomes after the transition: 116
- transition policy:
  `COMPLETED_SWEEP_STORED_YAHOO_NO_PRICE_DATA_V1`

The checkpoint budget is 601, equal to the complete manifest batch count. The
service still changes only checkpoint files that contain eligible outcomes.
This removes an arbitrary small-run limit without broadening eligibility.

## Run once in Windows PowerShell

The block is ASCII-only and compatible with Windows PowerShell 5.1. Run it from
a new PowerShell window after the package commit is checked out. It refuses a
wrong branch, wrong HEAD, dirty worktree, changed immutable inputs, ambiguous
checkpoint directory, incomplete checkpoint set, or an existing output report.

```powershell
$ErrorActionPreference = "Stop"

$Repository = "C:\Users\tu\Desktop\InvestmentTerminal"
$ExpectedBranch = "develop"
$ExpectedHead = "281b057c46dc8bf24f5c29fb9188b346377d594b"
$ManifestPath = "C:\runtime\data\market_batch_manifest_10y.json"
$CheckpointSearchRoot = "C:\runtime\data"
$InventoryPath = "C:\runtime\reports\manifest_collection_failure_inventory_001.json"
$ReportDirectory = "C:\runtime\reports"
$ReportPath = Join-Path $ReportDirectory "manifest_completed_sweep_no_price_transition_001.json"

$ExpectedManifestChecksum = "8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a"
$ExpectedInventoryChecksum = "1ae8fb0a6b7a915bb0567b6a5b48d1b328adfe6725f282acf203b181fd5c42f6"
$ExpectedBatch576RequestChecksum = "0b025a4862ff8e26cb00cbfc11f242227478a78e8385a82d4671a7543edd6fcb"
$ExpectedPolicy = "COMPLETED_SWEEP_STORED_YAHOO_NO_PRICE_DATA_V1"
$ExpectedBatchCount = 601
$ExpectedRequestedCount = 12019
$ExpectedSuccessCount = 11892
$ExpectedRetryableCount = 124
$ExpectedFinalCount = 3
$ExpectedEligibleCount = 113
$ExpectedPreservedRetryableCount = 11
$MaxCheckpoints = 601

Set-Location -LiteralPath $Repository

$ActualBranch = (git branch --show-current).Trim()
if ($LASTEXITCODE -ne 0 -or $ActualBranch -ne $ExpectedBranch) {
    throw "Branch mismatch. Expected $ExpectedBranch, got $ActualBranch"
}

$ActualHead = (git rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $ActualHead -ne $ExpectedHead) {
    throw "HEAD mismatch. Expected $ExpectedHead, got $ActualHead"
}

$WorkingTree = @(git status --porcelain)
if ($LASTEXITCODE -ne 0) {
    throw "Could not inspect the working tree"
}
if ($WorkingTree.Count -ne 0) {
    throw "Working tree is not clean"
}

foreach ($RequiredPath in @($ManifestPath, $InventoryPath)) {
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

$ActualManifestChecksum = (Get-FileHash -LiteralPath $ManifestPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($ActualManifestChecksum -ne $ExpectedManifestChecksum) {
    throw "Manifest checksum mismatch"
}

$ActualInventoryChecksum = (Get-FileHash -LiteralPath $InventoryPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($ActualInventoryChecksum -ne $ExpectedInventoryChecksum) {
    throw "Inventory checksum mismatch"
}

try {
    $Manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $Inventory = Get-Content -LiteralPath $InventoryPath -Raw -Encoding UTF8 | ConvertFrom-Json
}
catch {
    throw "Could not parse the manifest or inventory JSON"
}

$ManifestBatches = @($Manifest.batches)
if ($ManifestBatches.Count -ne $ExpectedBatchCount) {
    throw "Manifest batch count mismatch"
}
if ([string]$ManifestBatches[575].request_checksum -ne $ExpectedBatch576RequestChecksum) {
    throw "Manifest batch 0576 request checksum mismatch"
}

if ([int]$Inventory.schema_version -ne 1) {
    throw "Inventory schema version mismatch"
}
if ([string]$Inventory.operation_identity -ne "MANIFEST_COLLECTION_FAILURE_INVENTORY") {
    throw "Inventory operation identity mismatch"
}
if ([string]$Inventory.provider_identity -ne "YAHOO_FINANCE") {
    throw "Inventory provider identity mismatch"
}
if ([string]$Inventory.status -ne "SUCCESS") {
    throw "Inventory status mismatch"
}
if ([string]$Inventory.manifest_checksum -ne $ExpectedManifestChecksum) {
    throw "Inventory manifest checksum mismatch"
}
if ($null -ne $Inventory.failure) {
    throw "Inventory contains a failure"
}

$Coverage = $Inventory.coverage
if (
    [int]$Coverage.batch_count -ne $ExpectedBatchCount -or
    [int]$Coverage.sweep_covered_batch_count -ne $ExpectedBatchCount -or
    [int]$Coverage.requested_count -ne $ExpectedRequestedCount -or
    [int]$Coverage.checkpoint_outcome_count -ne $ExpectedRequestedCount -or
    [int]$Coverage.missing_count -ne 0 -or
    [int]$Coverage.success_count -ne $ExpectedSuccessCount -or
    [int]$Coverage.empty_count -ne 0 -or
    [int]$Coverage.retryable_failure_count -ne $ExpectedRetryableCount -or
    [int]$Coverage.final_failure_count -ne $ExpectedFinalCount -or
    [int]$Coverage.deferable_failure_count -ne $ExpectedRetryableCount -or
    [int]$Coverage.blocking_failure_count -ne 0
) {
    throw "Inventory coverage does not match the frozen completed sweep"
}

$MissingPriceTypes = @(
    "yfinance.exceptions.YFPricesMissingError",
    "yfinance.exceptions.YFTickerMissingError",
    "yfinance.exceptions.YFTzMissingError"
)
$RedactionTypes = @(
    "UNRECOGNIZED_EXCEPTION_TYPE",
    "EXCEPTION_CHAIN_TRUNCATED"
)
$EligibleInventoryCount = 0
$RetryableSignatureCount = 0
foreach ($Signature in @($Inventory.retryable_causal_signatures)) {
    $SignatureCount = [int]$Signature.count
    $RetryableSignatureCount += $SignatureCount
    $Chain = @($Signature.exception_type_chain)
    $RecognizedMissingType = $false
    $HasRedaction = $false
    foreach ($ExceptionType in $Chain) {
        if ($MissingPriceTypes -contains [string]$ExceptionType) {
            $RecognizedMissingType = $true
        }
        if ($RedactionTypes -contains [string]$ExceptionType) {
            $HasRedaction = $true
        }
    }
    if (
        [string]$Signature.category -eq "NO_PRICE_DATA" -and
        $Chain.Count -gt 0 -and
        [string]$Chain[0] -eq "investment_terminal.utils.exceptions.APIError" -and
        $RecognizedMissingType -and
        -not $HasRedaction
    ) {
        $EligibleInventoryCount += $SignatureCount
    }
}
if ($RetryableSignatureCount -ne $ExpectedRetryableCount) {
    throw "Retryable inventory signature total mismatch"
}
if ($EligibleInventoryCount -ne $ExpectedEligibleCount) {
    throw "Eligible inventory count mismatch"
}
if (($RetryableSignatureCount - $EligibleInventoryCount) -ne $ExpectedPreservedRetryableCount) {
    throw "Preserved retryable count mismatch"
}

$FinalSignatureCount = 0
foreach ($Signature in @($Inventory.final_failure_signatures)) {
    $FinalSignatureCount += [int]$Signature.count
}
if ($FinalSignatureCount -ne $ExpectedFinalCount) {
    throw "Final inventory signature total mismatch"
}

$CheckpointCandidates = @(
    Get-ChildItem -LiteralPath $CheckpointSearchRoot -Filter "batch_0576.json" -File -Recurse -ErrorAction Stop
)
$MatchingCheckpointDirectories = @()
foreach ($Candidate in $CheckpointCandidates) {
    try {
        $CandidateCheckpoint = Get-Content -LiteralPath $Candidate.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
    }
    catch {
        continue
    }
    if ([string]$CandidateCheckpoint.request_checksum -eq $ExpectedBatch576RequestChecksum) {
        $MatchingCheckpointDirectories += [System.IO.Path]::GetDirectoryName($Candidate.FullName)
    }
}
$MatchingCheckpointDirectories = @($MatchingCheckpointDirectories | Sort-Object -Unique)
if ($MatchingCheckpointDirectories.Count -ne 1) {
    throw "Could not uniquely identify the completed-sweep checkpoint directory"
}
$CheckpointDirectory = [string]$MatchingCheckpointDirectories[0]

$CheckpointPaths = @()
$BeforeHashes = @{}
for ($BatchIndex = 1; $BatchIndex -le $ExpectedBatchCount; $BatchIndex++) {
    $CheckpointPath = Join-Path $CheckpointDirectory ("batch_{0:D4}.json" -f $BatchIndex)
    if (-not (Test-Path -LiteralPath $CheckpointPath -PathType Leaf)) {
        throw "The completed-sweep checkpoint set is incomplete"
    }
    $CheckpointPaths += $CheckpointPath
    $BeforeHashes[[string]$BatchIndex] = (Get-FileHash -LiteralPath $CheckpointPath -Algorithm SHA256).Hash.ToLowerInvariant()
}

python -m investment_terminal.cli.manifest_completed_sweep_no_price_transition `
    --manifest $ManifestPath `
    --manifest-checksum $ExpectedManifestChecksum `
    --checkpoint-directory $CheckpointDirectory `
    --inventory $InventoryPath `
    --inventory-checksum $ExpectedInventoryChecksum `
    --report-output $ReportPath `
    --max-checkpoints $MaxCheckpoints `
    --json
$CommandExitCode = $LASTEXITCODE

if (-not (Test-Path -LiteralPath $ReportPath -PathType Leaf)) {
    throw "The transition command did not write its report"
}
try {
    $Report = Get-Content -LiteralPath $ReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
}
catch {
    throw "Could not parse the transition report"
}

$ChangedCheckpointCount = 0
for ($BatchIndex = 1; $BatchIndex -le $ExpectedBatchCount; $BatchIndex++) {
    $CheckpointPath = $CheckpointPaths[$BatchIndex - 1]
    $AfterHash = (Get-FileHash -LiteralPath $CheckpointPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($AfterHash -ne $BeforeHashes[[string]$BatchIndex]) {
        $ChangedCheckpointCount += 1
    }
}

if ($CommandExitCode -ne 0) {
    Write-Host "SEND: $ReportPath"
    throw "Completed-sweep NO_PRICE_DATA transition failed with exit code $CommandExitCode"
}
if ([int]$Report.schema_version -ne 1) {
    throw "Transition report schema version mismatch"
}
if ([string]$Report.operation_identity -ne "MANIFEST_COMPLETED_SWEEP_NO_PRICE_TRANSITION") {
    throw "Transition report operation identity mismatch"
}
if ([string]$Report.provider_identity -ne "YAHOO_FINANCE") {
    throw "Transition report provider identity mismatch"
}
if ([string]$Report.status -ne "COMPLETE") {
    throw "Transition report did not reach COMPLETE"
}
if ([string]$Report.manifest_checksum -ne $ExpectedManifestChecksum) {
    throw "Transition report manifest checksum mismatch"
}
if ([string]$Report.inventory_checksum -ne $ExpectedInventoryChecksum) {
    throw "Transition report inventory checksum mismatch"
}
if ([string]$Report.isolation_policy_identity -ne $ExpectedPolicy) {
    throw "Transition report policy mismatch"
}
if ([int]$Report.budget.max_checkpoints -ne $MaxCheckpoints) {
    throw "Transition report budget mismatch"
}
if ($null -ne $Report.failure) {
    throw "Transition report contains a failure"
}

$Starting = $Report.starting_coverage
$Current = $Report.current_run
$Ending = $Report.ending_coverage
$StartingAlreadyFinal = [int]$Starting.already_final_count
$StartingRemaining = [int]$Starting.remaining_count
$CurrentTransitioned = [int]$Current.transitioned_count
$ProcessedCheckpointCount = [int]$Current.processed_checkpoint_count

if (
    [int]$Starting.eligible_count -ne $ExpectedEligibleCount -or
    [int]$Starting.transitioned_count -ne 0 -or
    $StartingAlreadyFinal -lt 0 -or
    $StartingAlreadyFinal -gt $ExpectedEligibleCount -or
    $StartingRemaining -ne ($ExpectedEligibleCount - $StartingAlreadyFinal)
) {
    throw "Starting transition coverage mismatch"
}
if (
    [int]$Current.eligible_count -ne $ExpectedEligibleCount -or
    [int]$Current.already_final_count -ne $StartingAlreadyFinal -or
    $CurrentTransitioned -ne $StartingRemaining -or
    [int]$Current.remaining_count -ne 0
) {
    throw "Current-run transition coverage mismatch"
}
if (
    [int]$Ending.eligible_count -ne $ExpectedEligibleCount -or
    [int]$Ending.already_final_count -ne $StartingAlreadyFinal -or
    [int]$Ending.transitioned_count -ne $CurrentTransitioned -or
    [int]$Ending.final_count -ne $ExpectedEligibleCount -or
    [int]$Ending.remaining_count -ne 0
) {
    throw "Ending transition coverage mismatch"
}
if ($ProcessedCheckpointCount -lt 0 -or $ProcessedCheckpointCount -gt $MaxCheckpoints) {
    throw "Processed checkpoint count is outside the allowed range"
}
if ($ChangedCheckpointCount -ne $ProcessedCheckpointCount) {
    throw "Changed checkpoint count does not match the transition report"
}

$ReportHash = (Get-FileHash -LiteralPath $ReportPath -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Host "Completed-sweep NO_PRICE_DATA transition: COMPLETE"
Write-Host "Eligible outcomes: $ExpectedEligibleCount"
Write-Host "Transitioned in this run: $CurrentTransitioned"
Write-Host "Already final before this run: $StartingAlreadyFinal"
Write-Host "Preserved retryable outcomes: $ExpectedPreservedRetryableCount"
Write-Host "Changed checkpoint files: $ChangedCheckpointCount"
Write-Host "Report SHA-256: $ReportHash"
Write-Host "SEND: $ReportPath"
Write-Host "DO NOT SEND: $CheckpointDirectory"
Write-Host "DO NOT SEND: $ManifestPath"
```

## Expected successful result

The console must end with:

- `Completed-sweep NO_PRICE_DATA transition: COMPLETE`
- `Eligible outcomes: 113`
- `Preserved retryable outcomes: 11`
- a non-negative changed-checkpoint count equal to
  `current_run.processed_checkpoint_count`
- `SEND: C:\runtime\reports\manifest_completed_sweep_no_price_transition_001.json`

For the normal first run, `Transitioned in this run` is 113 and
`Already final before this run` is 0. The validation also accepts an exact
resume after a prior report-write failure: already-final outcomes are counted,
only the remainder is changed, and ending coverage must still be 113 of 113.

Return only the generated transition report. Do not send the manifest or any
checkpoint file; they contain private instrument identities.

## Next decision gate

After the report is reviewed, regenerate the privacy-safe completed-sweep
failure inventory from the stabilized checkpoint state or add the smallest
read-only verification package required by the existing contracts. Do not
restart broad collection and do not classify the preserved response-shape or
legacy outcomes as `NO_PRICE_DATA`.
