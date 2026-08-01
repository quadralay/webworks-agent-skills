<#
test-log-scan.ps1
Test driver for Get-GenerateLogSummaries and Get-CompositionLogSummary in
Invoke-Automap.ps1.

Dot-sources the wrapper (its main-flow guard prevents a build from running),
invokes the log scan against each fixture directory, and compares the summary
lines against the per-fixture expected-default.txt reference files.

Usage: powershell -ExecutionPolicy Bypass -File test-log-scan.ps1
Exit code: 0 if all assertions pass, 1 otherwise.
#>

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$fixtures = Join-Path $scriptDir 'fixtures'

# Import the wrapper's functions without running a build.
. (Join-Path $scriptDir '..\scripts\Invoke-Automap.ps1')

$script:Pass = 0
$script:Fail = 0

function Assert-Summary {
    param(
        [string]$Name,
        [string]$ExpectedFile,
        [string]$Actual
    )

    $expected = ''
    if (Test-Path -LiteralPath $ExpectedFile) {
        $raw = Get-Content -LiteralPath $ExpectedFile -Raw
        if ($raw) { $expected = $raw }
    }
    $expected = ($expected -replace "`r`n", "`n").TrimEnd("`n")

    $actual = $Actual

    if ($expected -ceq $actual) {
        $script:Pass++
        Write-Output "PASS: $Name"
    }
    else {
        $script:Fail++
        Write-Output "FAIL: $Name"
        Write-Output '--- expected ---'
        Write-Output $expected
        Write-Output '--- actual ---'
        Write-Output $actual
        Write-Output '----------------'
    }
}

function Test-Fixture {
    param(
        [string]$Name,
        [string]$FixtureDir,
        [string]$ExpectedFile
    )

    $actual = (@(Get-GenerateLogSummaries -BaseDir $FixtureDir) | ForEach-Object { $_.Text }) -join "`n"
    Assert-Summary -Name $Name -ExpectedFile $ExpectedFile -Actual $actual
}

function Test-CompositionFixture {
    param(
        [string]$Name,
        [string]$CompositionFile,
        [string]$ExpectedFile
    )

    $actual = (@(Get-CompositionLogSummary -Path $CompositionFile) |
        Where-Object { $_ } | ForEach-Object { $_.Text }) -join "`n"
    Assert-Summary -Name $Name -ExpectedFile $ExpectedFile -Actual $actual
}

# Single-target, warnings only: summary format.
Test-Fixture 'single-warning-target' `
    (Join-Path $fixtures 'single-warning-target') `
    (Join-Path $fixtures 'single-warning-target\expected-default.txt')

# Multi-target aggregation: error-only target reports [ERROR], clean target
# emits nothing, alphabetical target order.
Test-Fixture 'multi-target' `
    (Join-Path $fixtures 'multi-target') `
    (Join-Path $fixtures 'multi-target\expected-default.txt')

# Target directory name with an embedded space.
Test-Fixture 'space-target' `
    (Join-Path $fixtures 'space-target') `
    (Join-Path $fixtures 'space-target\expected-default.txt')

# Single target with both [WARN] and [ERROR] in one log: summary is [ERROR].
Test-Fixture 'mixed-target' `
    (Join-Path $fixtures 'mixed-target') `
    (Join-Path $fixtures 'mixed-target\expected-default.txt')

# Missing Logs/ directory emits nothing.
Test-Fixture 'no-logs-dir' `
    (Join-Path $fixtures 'no-logs-dir') `
    (Join-Path $fixtures 'no-logs-dir\expected-default.txt')

# Logs/ directory exists but contains no generate.log file: emits nothing.
Test-Fixture 'empty-logs-dir' `
    (Join-Path $fixtures 'empty-logs-dir') `
    (Join-Path $fixtures 'empty-logs-dir\expected-default.txt')

# Composition log, warnings only: the product writes [WARN]/[ERROR] (Publish
# Core's Messages.Warn/.Error), so warnings must be counted, not dropped.
Test-CompositionFixture 'composition-warning' `
    (Join-Path $fixtures 'composition-warning\composition.wacj') `
    (Join-Path $fixtures 'composition-warning\expected-default.txt')

# Composition log with both markers: summary is [ERROR], both counted. The log
# is located by the <CompositionJob name="..."> attribute, not the file name.
Test-CompositionFixture 'composition-mixed' `
    (Join-Path $fixtures 'composition-mixed\composition.wacj') `
    (Join-Path $fixtures 'composition-mixed\expected-default.txt')

Write-Output ''
Write-Output "Results: $($script:Pass) passed, $($script:Fail) failed"

if ($script:Fail -eq 0) { exit 0 } else { exit 1 }
