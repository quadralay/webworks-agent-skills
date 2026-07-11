<#
test-log-scan.ps1
Test driver for Get-GenerateLogSummaries in Invoke-Automap.ps1.

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

function Test-Fixture {
    param(
        [string]$Name,
        [string]$FixtureDir,
        [string]$ExpectedFile
    )

    $expected = ''
    if (Test-Path -LiteralPath $ExpectedFile) {
        $raw = Get-Content -LiteralPath $ExpectedFile -Raw
        if ($raw) { $expected = $raw }
    }
    $expected = ($expected -replace "`r`n", "`n").TrimEnd("`n")

    $actual = (@(Get-GenerateLogSummaries -BaseDir $FixtureDir) | ForEach-Object { $_.Text }) -join "`n"

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

Write-Output ''
Write-Output "Results: $($script:Pass) passed, $($script:Fail) failed"

if ($script:Fail -eq 0) { exit 0 } else { exit 1 }
