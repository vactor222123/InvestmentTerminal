# Phase 7 Package 157 — Batch-109 Causal-Evidence Handoff

## Classification

`OPERATIONAL — READY FOR USER EXECUTION`

## Verified Baseline

```text
develop @ 2bed0d12ed20d470920cdb42024859acc006f7d9
```

## Scope

Package 156 added a read-only diagnostic for the causal evidence already stored
in a schema-version-4 partial checkpoint. This handoff binds that diagnostic to
batch 109 of the private ten-year manifest and validates its redacted output.

The command verifies the exact repository HEAD, branch, clean worktree,
manifest binding, and unique request-bound checkpoint. It requires schema 4 and
one `FAILED/APIError` outcome, invokes only the stored-evidence diagnostic, and
prints only the redacted report path and SHA-256. It does not contact Yahoo,
open SQLite or cache files, mutate the checkpoint, ingest candles, resume batch
109, or execute batch 110.

## Execution Order

Run this block **before** applying Package 157, because the block deliberately
requires the Package 156 baseline. The PowerShell source is ASCII-only.

```powershell
$ErrorActionPreference = "Stop"

$Repository = "C:\Users\tu\Desktop\InvestmentTerminal"
$ExpectedHead = "2bed0d12ed20d470920cdb42024859acc006f7d9"
$ExpectedBranch = "develop"
$ManifestPath = "C:\runtime\data\market_batch_manifest_10y.json"
$CheckpointSearchRoot = "C:\runtime\data"
$ReportDirectory = "C:\runtime\reports"
$ReportPath = Join-Path $ReportDirectory "manifest_batch_0109_causal_evidence_diagnostic_001.json"
$ManifestChecksum = "8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a"
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
if (Test-Path -LiteralPath $ReportPath) {
    throw "Refusing to overwrite existing report: $ReportPath"
}

try {
    $Manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
} catch {
    throw "Could not parse the private manifest"
}

$SelectedBatches = @($Manifest.batches | Where-Object {
    [int]$_.batch_index -eq $BatchIndex
})
if ($SelectedBatches.Count -ne 1) {
    throw "Could not uniquely identify batch $BatchIndex in the manifest"
}

$RequestChecksum = [string]$SelectedBatches[0].request_checksum
if ($RequestChecksum -cnotmatch '^[0-9a-f]{64}$') {
    throw "Batch request checksum is invalid"
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
if ([int]$Checkpoint.schema_version -ne 4) {
    throw "Batch-109 checkpoint must use schema version 4"
}
if ([string]$Checkpoint.request_checksum -ne $RequestChecksum) {
    throw "Batch-109 checkpoint request checksum mismatch"
}
if ($CheckpointOutcomes.Count -ne 1) {
    throw "Batch-109 checkpoint must contain exactly one outcome"
}
if ([string]$CheckpointOutcomes[0].status -ne "FAILED" -or
    [string]$CheckpointOutcomes[0].failure_type -ne "APIError") {
    throw "Batch-109 checkpoint must contain one FAILED APIError outcome"
}

New-Item -ItemType Directory -Force -Path $ReportDirectory | Out-Null

python -m investment_terminal.cli.manifest_partial_causal_evidence `
    --manifest $ManifestPath `
    --manifest-checksum $ManifestChecksum `
    --batch-index $BatchIndex `
    --checkpoint $CheckpointPath `
    --report-output $ReportPath `
    --json
$CommandExitCode = $LASTEXITCODE

if ($CommandExitCode -ne 0) {
    throw "Causal-evidence diagnostic failed with exit code $CommandExitCode"
}
if (-not (Test-Path -LiteralPath $ReportPath -PathType Leaf)) {
    throw "Causal-evidence diagnostic did not write its report"
}

try {
    $Report = Get-Content -LiteralPath $ReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
} catch {
    throw "Could not parse the causal-evidence diagnostic report"
}

$AllowedStatuses = @("EVIDENCE_AVAILABLE", "LEGACY_EVIDENCE_UNAVAILABLE")
if ([int]$Report.schema_version -ne 1 -or
    [string]$Report.operation_identity -ne "MANIFEST_PARTIAL_CAUSAL_EVIDENCE_DIAGNOSTIC" -or
    [string]$Report.provider_identity -ne "YAHOO_FINANCE" -or
    $AllowedStatuses -notcontains [string]$Report.status -or
    [string]$Report.manifest_checksum -ne $ManifestChecksum -or
    [int]$Report.batch_index -ne 109 -or
    [int]$Report.batch_count -ne 601 -or
    [string]$Report.request_checksum -ne $RequestChecksum -or
    $null -ne $Report.failure) {
    throw "Causal-evidence diagnostic report contract validation failed"
}

$FailureTypes = @($Report.selection.checkpoint_failure_types)
if ([int]$Report.selection.requested_count -ne 20 -or
    [int]$Report.selection.checkpoint_outcome_count -ne 1 -or
    [int]$Report.selection.missing_count -ne 19 -or
    [int]$Report.selection.failed_candidate_count -ne 1 -or
    [int]$Report.selection.selected_count -ne 1 -or
    $FailureTypes.Count -ne 1 -or
    [string]$FailureTypes[0] -ne "APIError") {
    throw "Causal-evidence diagnostic selection validation failed"
}

if ([string]$Report.status -eq "EVIDENCE_AVAILABLE") {
    if ($null -eq $Report.causal_failure_evidence) {
        throw "Stored causal evidence is missing"
    }
    $ExceptionTypeChain = @($Report.causal_failure_evidence.exception_type_chain)
    if ([string]::IsNullOrWhiteSpace([string]$Report.causal_failure_evidence.category) -or
        $ExceptionTypeChain.Count -lt 1 -or
        $ExceptionTypeChain.Count -gt 8) {
        throw "Stored causal evidence is invalid"
    }
    foreach ($ExceptionType in $ExceptionTypeChain) {
        if ([string]::IsNullOrWhiteSpace([string]$ExceptionType)) {
            throw "Stored causal exception type is invalid"
        }
    }
} elseif ($null -ne $Report.causal_failure_evidence) {
    throw "Legacy unavailable status must not contain inferred causal evidence"
}

$ReportHash = (Get-FileHash -LiteralPath $ReportPath -Algorithm SHA256).Hash.ToLowerInvariant()

Write-Host "Privacy-safe batch-109 causal-evidence diagnostic completed"
Write-Host "Status: $($Report.status)"
Write-Host "Report: $ReportPath"
Write-Host "SHA-256: $ReportHash"
Write-Host "SEND: $ReportPath"
Write-Host "DO NOT SEND: manifest or checkpoint files"
```

## Expected Evidence

The valid result is either `EVIDENCE_AVAILABLE`, with one stored stable category
and a bounded allowlisted exception-type chain, or
`LEGACY_EVIDENCE_UNAVAILABLE`, with null evidence and no inferred cause. The
expected selection is 20 requested members, one checkpoint outcome, 19 missing
members, and one selected `APIError`. A `FAILED` report or any mismatch is a
blocker and does not authorize a provider retry.

## Repository Verification

```text
focused causal-evidence, partial-failure, checkpoint, sweep, and architecture tests: 56 passed in 3.13s
full test suite: 3102 passed, 4 skipped, 1 warning in 29.45s
git diff --check: clean
```

The warning is the existing Starlette `httpx` deprecation warning and is not a
Package 157 regression.

## Next Gate

Return only
`C:\runtime\reports\manifest_batch_0109_causal_evidence_diagnostic_001.json`.
Review that redacted evidence before choosing any batch-109 retry or isolation
path. Batch 110 and the remaining collection sweep stay blocked.
