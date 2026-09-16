# Phase 7 Package 155 — No-Price Transition Result and Collection Resume

## Classification

`OPERATIONAL — RESULT REVIEWED / COLLECTION RESUME READY`

## Verified Baseline

```text
develop @ 9ff65c72ab90f5f1f6d0ef0dcf37578c8d5a909b
```

## Reviewed Evidence

Only the explicitly returned redacted schema-version-1
`MANIFEST_PARTIAL_NO_PRICE_ISOLATION` report was reviewed. The private
manifest, checkpoint, database, cache, symbols, currencies, prices, and candles
were not reviewed.

Report SHA-256:

```text
6eb813eb379ab8f41712b5837a857fcaa633c28503559e4cc12ce44d911d510a
```

The report binds the established manifest and request:

```text
manifest_checksum = 8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a
batch_index = 106
batch_count = 601
request_checksum = e75eb6f083b162d8f1998a37bef9814265415adf15335008f6b4a64b97949ab9
qualification_checksum = 6a88fef1629287a395faecb04ba6d1ba72587d582573a99b4d211684aad9ce05
```

## Transition Result

The transition succeeded in 0.00028 seconds. It changed the one stored
`FAILED/APIError` outcome to one evidence-bound
`FINAL_FAILED/NO_PRICE_DATA` outcome under policy
`REPRODUCED_YAHOO_NO_PRICE_DATA_V1`.

Coverage is exact for the partial checkpoint:

```text
requested_count = 20
checkpoint_outcome_count = 7
success_count = 6
empty_count = 0
retryable_failure_count = 0
final_failure_count = 1
transitioned_count = 1
already_final_count = 0
missing_count = 13
```

The original lost cause was not rewritten. The current reproduced evidence is
preserved as the terminal policy input, and the 13 unattempted members remain
pending.

## Collection-Resume Decision

The existing collection sweep can now resume safely. Checkpoint schema 4 is
accepted by the shared parser; `FINAL_FAILED` is terminal and provider-bypassed;
the partial batch remains uncovered until the 13 missing members receive
outcomes. A budget of 496 batches exactly covers batch 106 through batch 601.

This follows the operator-selected strategy: collect all remaining obtainable
candles first and analyze deferred failures after the sweep. Exact local
`YahooCandleInvalidResponseError` defects may be deferred. Any API, transport,
rate-limit, persistence, checkpoint, or unknown failure is checkpointed and
halts before later work.

## User-Executed PowerShell

Run this ASCII-only block before applying the Package 155 documentation commit.
It expects the caller-supplied baseline above.

```powershell
$ErrorActionPreference = "Stop"

$Repository = "C:\Users\tu\Desktop\InvestmentTerminal"
$ExpectedHead = "9ff65c72ab90f5f1f6d0ef0dcf37578c8d5a909b"
$ExpectedBranch = "develop"
$ManifestPath = "C:\runtime\data\market_batch_manifest_10y.json"
$CheckpointSearchRoot = "C:\runtime\data"
$DatabasePath = "C:\runtime\data\investment_terminal.db"
$CacheDirectory = "C:\runtime\cache\yfinance"
$ReportDirectory = "C:\runtime\reports"
$ReportPath = Join-Path $ReportDirectory "manifest_collection_sweep_resume_0106_0601_10y.json"
$ManifestChecksum = "8590c3e29490ef6f738696a401e35537986bf18e8704bd5318ebbf055f47238a"
$RequestChecksum = "e75eb6f083b162d8f1998a37bef9814265415adf15335008f6b4a64b97949ab9"
$MaxBatches = 496

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

foreach ($RequiredPath in @($ManifestPath, $DatabasePath)) {
    if (-not (Test-Path -LiteralPath $RequiredPath -PathType Leaf)) {
        throw "Required private input is missing: $RequiredPath"
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
$CheckpointDirectory = $CheckpointCandidates[0].Directory.FullName

$Batch106 = Get-Content -LiteralPath $CheckpointCandidates[0].FullName -Raw -Encoding UTF8 |
    ConvertFrom-Json
$Batch106Outcomes = @(
    $Batch106.outcomes.PSObject.Properties | ForEach-Object { $_.Value }
)
$Batch106Final = @(
    $Batch106Outcomes | Where-Object {
        $_.status -eq "FINAL_FAILED" -and
        $_.failure_type -eq "APIError" -and
        $_.failure_category -eq "NO_PRICE_DATA" -and
        $_.isolation_policy_identity -eq "REPRODUCED_YAHOO_NO_PRICE_DATA_V1"
    }
)
if (
    [int]$Batch106.schema_version -ne 4 -or
    $Batch106.request_checksum -ne $RequestChecksum -or
    $Batch106Outcomes.Count -ne 7 -or
    $Batch106Final.Count -ne 1
) {
    throw "Batch-106 transition checkpoint validation failed"
}

if (Test-Path -LiteralPath $ReportPath) {
    throw "Report output already exists: $ReportPath"
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

$Report = Get-Content -LiteralPath $ReportPath -Raw -Encoding UTF8 |
    ConvertFrom-Json
$AllowedStatuses = @("COMPLETE", "BUDGET_EXHAUSTED", "HALTED", "FAILED")
if (
    [int]$Report.schema_version -ne 1 -or
    $Report.operation_identity -ne "MANIFEST_COLLECTION_SWEEP" -or
    $Report.provider_identity -ne "YAHOO_FINANCE" -or
    $Report.manifest_checksum -ne $ManifestChecksum -or
    [int]$Report.budget.max_batches -ne $MaxBatches -or
    $AllowedStatuses -notcontains $Report.status
) {
    throw "Collection sweep report validation failed"
}

if ($Report.status -eq "FAILED") {
    if ($CommandExitCode -eq 0 -or @($Report.failure_types).Count -eq 0) {
        throw "Failed collection sweep evidence is inconsistent"
    }
}
else {
    $Starting = $Report.starting_coverage
    if (
        [int]$Starting.batch_count -ne 601 -or
        [int]$Starting.sweep_covered_batch_count -ne 105 -or
        [int]$Starting.fully_complete_batch_count -ne 104 -or
        [int]$Starting.remaining_unswept_batch_count -ne 496 -or
        [int]$Starting.deferred_failure_count -ne 1
    ) {
        throw "Collection sweep starting coverage mismatch"
    }
}

if ($Report.status -eq "COMPLETE") {
    if (
        [int]$Report.ending_coverage.sweep_covered_batch_count -ne 601 -or
        [int]$Report.ending_coverage.remaining_unswept_batch_count -ne 0 -or
        $null -ne $Report.stop_batch_index -or
        @($Report.failure_types).Count -ne 0 -or
        $CommandExitCode -ne 0
    ) {
        throw "Complete collection sweep evidence is inconsistent"
    }
}
elseif ($Report.status -eq "HALTED") {
    if (
        $null -eq $Report.stop_batch_index -or
        @($Report.failure_types).Count -eq 0 -or
        $CommandExitCode -eq 0
    ) {
        throw "Halted collection sweep evidence is inconsistent"
    }
}
elseif ($Report.status -eq "BUDGET_EXHAUSTED" -and $CommandExitCode -ne 0) {
    throw "Budget-exhausted collection sweep returned a nonzero exit code"
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

$ReportChecksum = (
    Get-FileHash -LiteralPath $ReportPath -Algorithm SHA256
).Hash.ToLowerInvariant()

Write-Host "Collection sweep status: $($Report.status)"
Write-Host "SQLite integrity: $Integrity"
Write-Host "Report: $ReportPath"
Write-Host "Report SHA-256: $ReportChecksum"
Write-Host "SEND: $ReportPath"
Write-Host "SEND: SQLite integrity: $Integrity"
Write-Host "DO NOT SEND: $ManifestPath"
Write-Host "DO NOT SEND: $CheckpointDirectory"
Write-Host "DO NOT SEND: $DatabasePath"
Write-Host "DO NOT SEND: $CacheDirectory"
```

The run may take a long time. A `HALTED` report is a valid safe outcome and
must be returned rather than bypassed. `COMPLETE` means every manifest member
has an attempted outcome; it may still retain deferred local candle defects for
later analysis.

## Repository Verification

```text
focused tests: 44 passed in 1.13s
full test suite: 3094 passed, 4 skipped, 1 warning in 25.74s
git diff --check: clean
```

The warning is the existing Starlette `httpx` deprecation warning and is not a
Package 155 regression.

## Next Gate

Return the redacted sweep report and the printed SQLite integrity result. If
the sweep is complete, audit the aggregate deferred/final failures only after
all obtainable candles have been collected. If it halts, inspect the one
recorded systemic stopping category without discarding completed progress.
