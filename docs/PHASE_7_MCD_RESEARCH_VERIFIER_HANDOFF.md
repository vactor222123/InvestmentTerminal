# Phase 7 — local verification of the existing MCD research pair

Classification: `OPERATIONAL — READY FOR USER EXECUTION`. A fresh, clean
GitHub `develop` clone matched
`1769859eb3dca2407c1c82ada23a40499768548f` before this documentation
package. No private runtime file, SQLite database, or provider was accessed.

The generic read-only verifier is already implemented. This handoff checks
only the existing MCD-named private export against its previously reviewed
redacted report, whose exact-byte SHA-256 is
`f67727f3f09ef6b7b82a0f80102323b56ecdd67786e6177f600bd409cc0ea3ed`.
The private path is taken from the original MCD export handoff; its existence
and contents are checked only on the user's machine. No new export is created.

Run the complete ASCII-only block in Windows PowerShell 5.1 from the user's
existing repository **before applying this documentation ZIP**. Stop on any
failure; do not substitute a different report, guess a private path, or rerun
the export. The block makes no SQLite or provider request and writes no file.

```powershell
$ErrorActionPreference = "Stop"
$Repository = "C:\Users\tu\Desktop\InvestmentTerminal"
$ExpectedHead = "1769859eb3dca2407c1c82ada23a40499768548f"
$PrivateExport = "C:\runtime\data\instrument_research_run_mcd_20260929_001.json"
$Report = "C:\runtime\reports\instrument_research_run_mcd_20260929_001.json"
$ReportSha256 = "f67727f3f09ef6b7b82a0f80102323b56ecdd67786e6177f600bd409cc0ea3ed"

Set-Location -LiteralPath $Repository
$ActualBranch = (git branch --show-current).Trim()
if ($LASTEXITCODE -ne 0 -or $ActualBranch -ne "develop") { throw "Branch mismatch" }
$ActualHead = (git rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $ActualHead -ne $ExpectedHead) { throw "HEAD mismatch" }
$GitStatus = @(git status --porcelain)
if ($LASTEXITCODE -ne 0 -or $GitStatus.Count -ne 0) { throw "Working tree is not clean" }
foreach ($RequiredPath in @($PrivateExport, $Report)) {
    if (-not (Test-Path -LiteralPath $RequiredPath -PathType Leaf)) {
        throw "Required research evidence is missing; do not rerun export"
    }
}
$ReportHashBefore = (Get-FileHash -LiteralPath $Report -Algorithm SHA256).Hash.ToLowerInvariant()
if ($ReportHashBefore -ne $ReportSha256) { throw "Redacted report checksum mismatch" }
$PrivateHashBefore = (Get-FileHash -LiteralPath $PrivateExport -Algorithm SHA256).Hash.ToLowerInvariant()

$VerifierOutput = @(& python -m investment_terminal.cli.instrument_research_verify `
    --private-export $PrivateExport --report $Report `
    --report-sha256 $ReportSha256 --symbol MCD 2>&1)
$VerifierExit = $LASTEXITCODE
if ($VerifierExit -ne 0) { throw "Research verification failed; do not share private data" }
$ActualLines = @($VerifierOutput | ForEach-Object { $_.ToString() })
$ExpectedLines = @(
    "VERIFIED: private export and redacted report match the selected symbol",
    "REPORT_SHA256: $ReportSha256",
    "PRIVATE_SHA256: $PrivateHashBefore",
    "DO NOT SEND: private export without explicit per-artifact approval"
)
if ($ActualLines.Count -ne $ExpectedLines.Count) { throw "Unexpected verifier output" }
for ($Index = 0; $Index -lt $ExpectedLines.Count; $Index++) {
    if ($ActualLines[$Index] -cne $ExpectedLines[$Index]) {
        throw "Unexpected verifier output"
    }
}
if ((Get-FileHash -LiteralPath $Report -Algorithm SHA256).Hash.ToLowerInvariant() -ne $ReportHashBefore) {
    throw "Redacted report changed during verification"
}
if ((Get-FileHash -LiteralPath $PrivateExport -Algorithm SHA256).Hash.ToLowerInvariant() -ne $PrivateHashBefore) {
    throw "Private export changed during verification"
}
$ActualLines | ForEach-Object { Write-Host $_ }
Write-Host "SEND: $Report and the four verifier lines above"
Write-Host "DO NOT SEND: $PrivateExport"
```

Return only the four displayed verifier lines, including the two SHA-256
values, and the existing redacted report path (or the report again if asked).
Do not send the private export. `VERIFIED` establishes internal pair parity
for the explicit selected symbol, not provider authenticity, corporate-action
adjusted returns, exchange-session completeness, today's market freshness,
or an investment conclusion. Whether to share the **exact private artifact**
with ChatGPT remains a separate explicit user decision after reviewing this
result; no automatic upload or wider export is authorized.
