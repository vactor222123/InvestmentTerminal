# Phase 7 Package 160 — Stored No-Price Transition Handoff

## Classification

`OPERATIONAL — READY FOR USER EXECUTION`

## Verified Baseline

```text
develop @ 991b1c08b50c4a168c2fbca50c9e8feaab3202bf
```

## Scope

Package 159 implemented the distinct offline
`STORED_YAHOO_NO_PRICE_DATA_V1` transition. This handoff binds it to the
reviewed batch-109 diagnostic and validates both the private checkpoint change
and the separate redacted report.

The command verifies exact repository HEAD, branch, and clean state; the
private manifest and unique request-bound checkpoint; the immutable diagnostic
SHA-256 and contract; and exact equality between its causal object and the
checkpoint's stored schema-4 evidence. It then invokes only the offline
transition and validates the resulting one-outcome final checkpoint plus the
redacted report. It does not contact Yahoo, open SQLite, ingest candles, resume
batch 109, or execute batch 110.

## Execution Order

Run this block **before applying Package 160**, because it deliberately requires
the Package 159 GitHub baseline. The PowerShell source and emitted messages are
ASCII-only.

```powershell
$ErrorActionPreference = "Stop"

$Repository = "C:\Users\tu\Desktop\InvestmentTerminal"
$ExpectedHead = "991b1c08b50c4a168c2fbca50c9e8feaab3202bf"
$ExpectedBranch = "develop"
$ManifestPath = "C:\runtime\data\market_batch_manifest_10y.json"
$CheckpointSearchRoot = "C:\runtime\data"
$DiagnosticPath = "C:\runtime\reports\manifest_batch_0109_causal_evidence_diagnostic_001.json"
$ReportDirectory = "C:\runtime\reports"
$ReportPath = Join-Path $ReportDirectory "manifest_batch_0109_stored_no_price_isolation_001.json"
$ManifestChecksum = "8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a"
$DiagnosticChecksum = "509769c10ef7a4617104b80c5ed3ca626cd763e98c97e76353d52586507b64ef"
$BatchIndex = 109

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

if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
    throw "Required private manifest is missing: $ManifestPath"
}
if (-not (Test-Path -LiteralPath $CheckpointSearchRoot -PathType Container)) {
    throw "Required private checkpoint search root is missing: $CheckpointSearchRoot"
}
if (-not (Test-Path -LiteralPath $DiagnosticPath -PathType Leaf)) {
    throw "Required redacted diagnostic is missing: $DiagnosticPath"
}
if (Test-Path -LiteralPath $ReportPath) {
    throw "Refusing to overwrite existing report: $ReportPath"
}

$ActualDiagnosticChecksum = (Get-FileHash -LiteralPath $DiagnosticPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($ActualDiagnosticChecksum -ne $DiagnosticChecksum) {
    throw "Diagnostic checksum mismatch"
}

try {
    $Manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $Diagnostic = Get-Content -LiteralPath $DiagnosticPath -Raw -Encoding UTF8 | ConvertFrom-Json
} catch {
    throw "Could not parse the manifest or diagnostic"
}

$SelectedBatches = @($Manifest.batches | Where-Object {
    [int]$_.batch_index -eq $BatchIndex
})
if ($SelectedBatches.Count -ne 1) {
    throw "Could not uniquely identify batch $BatchIndex in the manifest"
}

$SelectedBatch = $SelectedBatches[0]
$RequestChecksum = [string]$SelectedBatch.request_checksum
if ($RequestChecksum -cnotmatch '^[0-9a-f]{64}$') {
    throw "Batch request checksum is invalid"
}
$RequestedStart = [string]$SelectedBatch.request.start
$RequestedEnd = [string]$SelectedBatch.request.end
$RequestedItems = @($SelectedBatch.request.items)
if ($RequestedItems.Count -ne 20) {
    throw "Batch 109 must contain exactly 20 requested items"
}

if ([int]$Diagnostic.schema_version -ne 1 -or
    [string]$Diagnostic.operation_identity -ne "MANIFEST_PARTIAL_CAUSAL_EVIDENCE_DIAGNOSTIC" -or
    [string]$Diagnostic.provider_identity -ne "YAHOO_FINANCE" -or
    [string]$Diagnostic.status -ne "EVIDENCE_AVAILABLE" -or
    [string]$Diagnostic.manifest_checksum -ne $ManifestChecksum -or
    [int]$Diagnostic.batch_index -ne $BatchIndex -or
    [int]$Diagnostic.batch_count -ne 601 -or
    [string]$Diagnostic.request_checksum -ne $RequestChecksum -or
    [string]$Diagnostic.requested_start -ne $RequestedStart -or
    [string]$Diagnostic.requested_end -ne $RequestedEnd -or
    $null -ne $Diagnostic.failure) {
    throw "Diagnostic contract validation failed"
}

$DiagnosticFailureTypes = @($Diagnostic.selection.checkpoint_failure_types)
if ([int]$Diagnostic.selection.requested_count -ne 20 -or
    [int]$Diagnostic.selection.checkpoint_outcome_count -ne 1 -or
    [int]$Diagnostic.selection.missing_count -ne 19 -or
    [int]$Diagnostic.selection.failed_candidate_count -ne 1 -or
    [int]$Diagnostic.selection.selected_count -ne 1 -or
    $DiagnosticFailureTypes.Count -ne 1 -or
    [string]$DiagnosticFailureTypes[0] -ne "APIError") {
    throw "Diagnostic selection validation failed"
}

$DiagnosticChain = @($Diagnostic.causal_failure_evidence.exception_type_chain)
if ([string]$Diagnostic.causal_failure_evidence.category -ne "NO_PRICE_DATA" -or
    $DiagnosticChain.Count -ne 2 -or
    [string]$DiagnosticChain[0] -ne "investment_terminal.utils.exceptions.APIError" -or
    [string]$DiagnosticChain[1] -ne "yfinance.exceptions.YFPricesMissingError") {
    throw "Diagnostic causal evidence validation failed"
}

$CheckpointMatches = @()
$CheckpointCandidates = @(Get-ChildItem -LiteralPath $CheckpointSearchRoot -Recurse -File -Filter "batch_0109.json")
foreach ($Candidate in $CheckpointCandidates) {
    try {
        $CandidateCheckpoint = Get-Content -LiteralPath $Candidate.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
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
$Checkpoint = $CheckpointMatches[0].Payload
$CheckpointOutcomes = @($Checkpoint.outcomes.psobject.Properties | ForEach-Object { $_.Value })
if ([int]$Checkpoint.schema_version -ne 4 -or
    [string]$Checkpoint.request_checksum -ne $RequestChecksum -or
    $CheckpointOutcomes.Count -ne 1) {
    throw "Batch-109 checkpoint contract validation failed"
}

$SourceOutcome = $CheckpointOutcomes[0]
$CheckpointChain = @($SourceOutcome.causal_failure_evidence.exception_type_chain)
if ([string]$SourceOutcome.status -ne "FAILED" -or
    [string]$SourceOutcome.failure_type -ne "APIError" -or
    [string]$SourceOutcome.causal_failure_evidence.category -ne "NO_PRICE_DATA" -or
    $CheckpointChain.Count -ne $DiagnosticChain.Count) {
    throw "Batch-109 checkpoint is not eligible for stored no-price isolation"
}
for ($Index = 0; $Index -lt $DiagnosticChain.Count; $Index++) {
    if ([string]$CheckpointChain[$Index] -ne [string]$DiagnosticChain[$Index]) {
        throw "Checkpoint causal evidence does not match the diagnostic"
    }
}

New-Item -ItemType Directory -Force -Path $ReportDirectory | Out-Null

python -m investment_terminal.cli.manifest_stored_no_price_isolation `
    --manifest $ManifestPath `
    --manifest-checksum $ManifestChecksum `
    --batch-index $BatchIndex `
    --checkpoint $CheckpointPath `
    --diagnostic $DiagnosticPath `
    --diagnostic-checksum $DiagnosticChecksum `
    --report-output $ReportPath
$CommandExitCode = $LASTEXITCODE

if ($CommandExitCode -ne 0) {
    throw "Stored no-price isolation failed with exit code $CommandExitCode"
}
if (-not (Test-Path -LiteralPath $ReportPath -PathType Leaf)) {
    throw "Stored no-price isolation did not write its report"
}

try {
    $UpdatedCheckpoint = Get-Content -LiteralPath $CheckpointPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $Report = Get-Content -LiteralPath $ReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
} catch {
    throw "Could not parse the updated checkpoint or isolation report"
}

$UpdatedOutcomes = @($UpdatedCheckpoint.outcomes.psobject.Properties | ForEach-Object { $_.Value })
if ([int]$UpdatedCheckpoint.schema_version -ne 4 -or
    [string]$UpdatedCheckpoint.request_checksum -ne $RequestChecksum -or
    $UpdatedOutcomes.Count -ne 1) {
    throw "Updated checkpoint contract validation failed"
}

$FinalOutcome = $UpdatedOutcomes[0]
$FinalEvidenceProperties = @($FinalOutcome.isolation_evidence.psobject.Properties)
$FinalOmissionTypes = @($FinalOutcome.omission_types)
if ([string]$FinalOutcome.status -ne "FINAL_FAILED" -or
    $null -ne $FinalOutcome.downloaded -or
    $null -ne $FinalOutcome.inserted -or
    $null -ne $FinalOutcome.duplicates -or
    [int]$FinalOutcome.omitted_trailing_count -ne 0 -or
    $FinalOmissionTypes.Count -ne 0 -or
    [string]$FinalOutcome.failure_type -ne "APIError" -or
    [string]$FinalOutcome.failure_category -ne "NO_PRICE_DATA" -or
    [string]$FinalOutcome.isolation_policy_identity -ne "STORED_YAHOO_NO_PRICE_DATA_V1" -or
    $FinalEvidenceProperties.Count -ne 1 -or
    [string]$FinalOutcome.isolation_evidence.causal_evidence_diagnostic_checksum -ne $DiagnosticChecksum -or
    $null -ne $FinalOutcome.psobject.Properties["causal_failure_evidence"]) {
    throw "Final checkpoint outcome validation failed"
}

if ([int]$Report.schema_version -ne 1 -or
    [string]$Report.operation_identity -ne "MANIFEST_STORED_NO_PRICE_ISOLATION" -or
    [string]$Report.status -ne "SUCCESS" -or
    [string]$Report.manifest_checksum -ne $ManifestChecksum -or
    [int]$Report.batch_index -ne $BatchIndex -or
    [int]$Report.batch_count -ne 601 -or
    [string]$Report.request_checksum -ne $RequestChecksum -or
    [string]$Report.requested_start -ne $RequestedStart -or
    [string]$Report.requested_end -ne $RequestedEnd -or
    [string]$Report.isolation_policy_identity -ne "STORED_YAHOO_NO_PRICE_DATA_V1" -or
    [string]$Report.failure_category -ne "NO_PRICE_DATA" -or
    [string]$Report.evidence.causal_evidence_diagnostic_checksum -ne $DiagnosticChecksum -or
    $null -ne $Report.failure) {
    throw "Stored no-price isolation report contract validation failed"
}

if ([int]$Report.coverage.requested_count -ne 20 -or
    [int]$Report.coverage.checkpoint_outcome_count -ne 1 -or
    [int]$Report.coverage.missing_count -ne 19 -or
    [int]$Report.coverage.success_count -ne 0 -or
    [int]$Report.coverage.empty_count -ne 0 -or
    [int]$Report.coverage.retryable_failure_count -ne 0 -or
    [int]$Report.coverage.final_failure_count -ne 1 -or
    [int]$Report.coverage.transitioned_count -ne 1 -or
    [int]$Report.coverage.already_final_count -ne 0) {
    throw "Stored no-price isolation report coverage validation failed"
}

$ReportHash = (Get-FileHash -LiteralPath $ReportPath -Algorithm SHA256).Hash.ToLowerInvariant()

Write-Host "Privacy-safe batch-109 stored no-price transition completed"
Write-Host "Status: $($Report.status)"
Write-Host "Transitioned count: $($Report.coverage.transitioned_count)"
Write-Host "Final failure count: $($Report.coverage.final_failure_count)"
Write-Host "Missing count: $($Report.coverage.missing_count)"
Write-Host "Report: $ReportPath"
Write-Host "SHA-256: $ReportHash"
Write-Host "SEND: $ReportPath"
Write-Host "DO NOT SEND: manifest, checkpoint, or other files under C:\runtime\data"
```

## Expected Evidence

The valid result is `SUCCESS` with one transitioned and one cumulative final
`NO_PRICE_DATA` outcome, zero retryable failures, and 19 still-missing request
members. The checkpoint remains schema 4 and the final evidence contains only
the immutable diagnostic checksum. Any mismatch or non-zero command exit is a
blocker and does not authorize collection resume.

## Repository Verification

```text
PowerShell 5.1 syntax and ASCII-only static validation: passed
focused checkpoint, causal-evidence, isolation, sweep/drain, and architecture tests: 111 passed in 3.90s
full test suite: 3120 passed, 4 skipped, 1 warning in 31.49s
git diff --check: clean
```

The warning is the existing Starlette `httpx` deprecation warning and is not a
Package 160 regression.

## Next Gate

Return only
`C:\runtime\reports\manifest_batch_0109_stored_no_price_isolation_001.json`.
Review that redacted report before resuming batch 109 or executing batch 110.
