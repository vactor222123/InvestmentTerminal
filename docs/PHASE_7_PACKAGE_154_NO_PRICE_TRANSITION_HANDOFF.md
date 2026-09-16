# Phase 7 Package 154 — No-Price Transition Handoff

## Classification

`OPERATIONAL — READY FOR USER EXECUTION`

## Verified Baseline

```text
develop @ bc340ebb693cdfe2937b410f88f55730c8e26e94
```

## Scope

This package prepares exactly one offline checkpoint transition for manifest
batch 106. It does not contact Yahoo, open SQLite, ingest a missing item,
resume the collection sweep, or permit batch 107.

The command binds the established evidence:

```text
manifest_checksum = 8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a
batch_index = 106
request_checksum = e75eb6f083b162d8f1998a37bef9814265415adf15335008f6b4a64b97949ab9
qualification_checksum = 6a88fef1629287a395faecb04ba6d1ba72587d582573a99b4d211684aad9ce05
```

The CLI verifies strict report bytes and all bindings before atomically
changing only the existing `FAILED/APIError` outcome to
`FINAL_FAILED/NO_PRICE_DATA`. The 13 missing request members remain absent from
the checkpoint and therefore pending collection.

## User-Executed PowerShell

The block is ASCII-only for Windows PowerShell 5.1 compatibility.

```powershell
$ErrorActionPreference = "Stop"

$Repository = "C:\Users\tu\Desktop\InvestmentTerminal"
$ExpectedHead = "bc340ebb693cdfe2937b410f88f55730c8e26e94"
$ExpectedBranch = "develop"
$ManifestPath = "C:\runtime\data\market_batch_manifest_10y.json"
$QualificationPath = "C:\runtime\reports\manifest_batch_0106_partial_failure_qualification_001.json"
$CheckpointSearchRoot = "C:\runtime\data"
$ReportDirectory = "C:\runtime\reports"
$ReportPath = Join-Path $ReportDirectory "manifest_batch_0106_no_price_isolation_001.json"
$ManifestChecksum = "8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a"
$RequestChecksum = "e75eb6f083b162d8f1998a37bef9814265415adf15335008f6b4a64b97949ab9"
$QualificationChecksum = "6a88fef1629287a395faecb04ba6d1ba72587d582573a99b4d211684aad9ce05"

Set-Location -LiteralPath $Repository

$ActualHead = (git rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $ActualHead -ne $ExpectedHead) {
    throw "HEAD mismatch. Expected $ExpectedHead, got $ActualHead"
}

$ActualBranch = (git branch --show-current).Trim()
if ($LASTEXITCODE -ne 0 -or $ActualBranch -ne $ExpectedBranch) {
    throw "Branch mismatch. Expected $ExpectedBranch, got $ActualBranch"
}

$WorkingTree = @(git status --porcelain)
if ($LASTEXITCODE -ne 0 -or $WorkingTree.Count -ne 0) {
    throw "Working tree is not clean"
}

foreach ($RequiredPath in @($ManifestPath, $QualificationPath)) {
    if (-not (Test-Path -LiteralPath $RequiredPath -PathType Leaf)) {
        throw "Required input is missing: $RequiredPath"
    }
}

if (-not (Test-Path -LiteralPath $CheckpointSearchRoot -PathType Container)) {
    throw "Checkpoint search root is missing: $CheckpointSearchRoot"
}

$CheckpointCandidates = @(
    Get-ChildItem -LiteralPath $CheckpointSearchRoot -Filter "batch_0106.json" -File -Recurse |
        Where-Object {
            try {
                $Candidate = Get-Content -LiteralPath $_.FullName -Raw -Encoding UTF8 |
                    ConvertFrom-Json
                $Candidate.request_checksum -eq $RequestChecksum
            }
            catch {
                $false
            }
        }
)

if ($CheckpointCandidates.Count -ne 1) {
    throw "Could not uniquely identify the bound batch-106 checkpoint"
}
$CheckpointPath = $CheckpointCandidates[0].FullName

if (Test-Path -LiteralPath $ReportPath) {
    throw "Report output already exists: $ReportPath"
}
New-Item -ItemType Directory -Force -Path $ReportDirectory | Out-Null

$ActualQualificationChecksum = (
    Get-FileHash -LiteralPath $QualificationPath -Algorithm SHA256
).Hash.ToLowerInvariant()
if ($ActualQualificationChecksum -ne $QualificationChecksum) {
    throw "Qualification checksum mismatch"
}

python -m investment_terminal.cli.manifest_partial_no_price_isolation `
    --manifest $ManifestPath `
    --manifest-checksum $ManifestChecksum `
    --batch-index 106 `
    --checkpoint $CheckpointPath `
    --qualification $QualificationPath `
    --qualification-checksum $QualificationChecksum `
    --report-output $ReportPath `
    --json

$CommandExitCode = $LASTEXITCODE
if ($CommandExitCode -ne 0) {
    throw "No-price transition failed with exit code $CommandExitCode"
}

$Report = Get-Content -LiteralPath $ReportPath -Raw -Encoding UTF8 |
    ConvertFrom-Json
if (
    [int]$Report.schema_version -ne 1 -or
    $Report.operation_identity -ne "MANIFEST_PARTIAL_NO_PRICE_ISOLATION" -or
    $Report.status -ne "SUCCESS" -or
    $Report.manifest_checksum -ne $ManifestChecksum -or
    [int]$Report.batch_index -ne 106 -or
    [int]$Report.batch_count -ne 601 -or
    $Report.request_checksum -ne $RequestChecksum -or
    $Report.isolation_policy_identity -ne "REPRODUCED_YAHOO_NO_PRICE_DATA_V1" -or
    $Report.failure_category -ne "NO_PRICE_DATA" -or
    $null -ne $Report.failure
) {
    throw "Transition report binding validation failed"
}

$Coverage = $Report.coverage
if (
    [int]$Coverage.requested_count -ne 20 -or
    [int]$Coverage.checkpoint_outcome_count -ne 7 -or
    [int]$Coverage.missing_count -ne 13 -or
    [int]$Coverage.retryable_failure_count -ne 0 -or
    [int]$Coverage.final_failure_count -ne 1 -or
    ([int]$Coverage.transitioned_count + [int]$Coverage.already_final_count) -ne 1
) {
    throw "Transition report coverage validation failed"
}

$Checkpoint = Get-Content -LiteralPath $CheckpointPath -Raw -Encoding UTF8 |
    ConvertFrom-Json
$CheckpointOutcomes = @(
    $Checkpoint.outcomes.PSObject.Properties | ForEach-Object { $_.Value }
)
$NoPriceFinal = @(
    $CheckpointOutcomes | Where-Object {
        $_.status -eq "FINAL_FAILED" -and
        $_.failure_type -eq "APIError" -and
        $_.failure_category -eq "NO_PRICE_DATA" -and
        $_.isolation_policy_identity -eq "REPRODUCED_YAHOO_NO_PRICE_DATA_V1" -and
        $_.isolation_evidence.partial_failure_qualification_checksum -eq $QualificationChecksum
    }
)
if (
    [int]$Checkpoint.schema_version -ne 4 -or
    $Checkpoint.request_checksum -ne $RequestChecksum -or
    $CheckpointOutcomes.Count -ne 7 -or
    $NoPriceFinal.Count -ne 1
) {
    throw "Private checkpoint validation failed"
}

$ReportChecksum = (
    Get-FileHash -LiteralPath $ReportPath -Algorithm SHA256
).Hash.ToLowerInvariant()

Write-Host "No-price transition: SUCCESS"
Write-Host "Missing request items preserved: 13"
Write-Host "Report: $ReportPath"
Write-Host "Report SHA-256: $ReportChecksum"
Write-Host "SEND: $ReportPath"
Write-Host "DO NOT SEND: $ManifestPath"
Write-Host "DO NOT SEND: $CheckpointPath"
```

## Expected Result

The redacted report must contain one final `NO_PRICE_DATA` exclusion, zero
retryable failures, seven checkpoint outcomes, and 13 missing members. Either
`transitioned_count=1` or, only after recovery from a previous post-commit
report failure, `already_final_count=1` is valid.

## Repository Verification

- focused transition, CLI atomicity, checkpoint, and collection-sweep tests:
  41 passed;
- complete suite: 3,094 passed, 4 skipped;
- one existing Starlette deprecation warning;
- `git diff --check`: clean.

## Next Gate

Review only the returned redacted report. If it is valid, authorize a separate
collection-resume package that processes the 13 still-missing batch-106 members
and then continues later batches. Do not combine that provider/database work
with this offline transition.
