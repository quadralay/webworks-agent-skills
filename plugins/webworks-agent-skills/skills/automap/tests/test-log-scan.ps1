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

# Localized installs: Publish Core translates the markers it writes (de
# [WARNUNG]/[FEHLER], fr [AVERTISSEMENT]/[ERREUR], ja the kanji pair), so an
# English-only scan would report a false 0/0 here. The German log also pins
# the token boundary: '[WARN]' must not also match inside '[WARNUNG]', or the
# warning count would read 2. Logs are UTF-8 with a BOM, as the product writes
# generate.log.
Test-Fixture 'localized-targets' `
    (Join-Path $fixtures 'localized-targets') `
    (Join-Path $fixtures 'localized-targets\expected-default.txt')

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

# Localized composition log: same marker set as generate.log, but this log is
# written without a BOM (FileInfo.CreateText()), so it also covers reading
# non-ASCII markers out of a BOM-less UTF-8 file.
Test-CompositionFixture 'composition-localized' `
    (Join-Path $fixtures 'composition-localized\composition.wacj') `
    (Join-Path $fixtures 'composition-localized\expected-default.txt')

# -IncludeClean reports a clean log as an [INFO] line, so the output names
# every log the build wrote (#164).
$actual = (@(Get-GenerateLogSummaries -BaseDir (Join-Path $fixtures 'multi-target') -IncludeClean) |
    ForEach-Object { $_.Text }) -join "`n"
Assert-Summary 'multi-target-include-clean' (Join-Path $fixtures 'multi-target\expected-include-clean.txt') $actual

# -Since skips logs last written before the build started: another target's
# generate.log from an earlier build must not be counted (#164). The fixture
# is copied to a temp folder so its timestamps can be set.
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("automap-logscan-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tempRoot | Out-Null
try {
    $staleCopy = Join-Path $tempRoot 'multi-target'
    Copy-Item -LiteralPath (Join-Path $fixtures 'multi-target') -Destination $staleCopy -Recurse
    $buildStart = (Get-Date).AddMinutes(-1)
    foreach ($name in 'PDF', 'Reverb2') {
        (Get-Item -LiteralPath (Join-Path $staleCopy "Logs\$name\generate.log")).LastWriteTime = (Get-Date).AddDays(-2)
    }
    (Get-Item -LiteralPath (Join-Path $staleCopy 'Logs\Clean\generate.log')).LastWriteTime = Get-Date
    $actual = (@(Get-GenerateLogSummaries -BaseDir $staleCopy -Since $buildStart -IncludeClean) |
        ForEach-Object { $_.Text }) -join "`n"
    if ($actual -ceq '[INFO] 0 warning(s), 0 error(s) in Logs/Clean/generate.log') { $script:Pass++; Write-Output 'PASS: stale-logs-skipped' }
    else { $script:Fail++; Write-Output "FAIL: stale-logs-skipped`n--- actual ---`n$actual" }

    # Same check for the composition log beside a .wacj.
    $compCopy = Join-Path $tempRoot 'composition-warning'
    Copy-Item -LiteralPath (Join-Path $fixtures 'composition-warning') -Destination $compCopy -Recurse
    (Get-Item -LiteralPath (Join-Path $compCopy 'Product Docs-log.txt')).LastWriteTime = (Get-Date).AddDays(-2)
    $stale = Get-CompositionLogSummary -Path (Join-Path $compCopy 'composition.wacj') -Since $buildStart
    if ($null -eq $stale) { $script:Pass++; Write-Output 'PASS: stale-composition-log-skipped' }
    else { $script:Fail++; Write-Output "FAIL: stale-composition-log-skipped`n--- actual ---`n$($stale.Text)" }

    # The CLI reports the staging folder it used; a job in a named workspace
    # stages there, not in the default folder (#164).
    $reported = @(Get-ReportedStagingRoots -Lines @(
            'Some progress line',
            "Staging folder of the 'Release 2026.1' workspace: D:\Builds\2026.1\Staging",
            'Staging folder (--stagingdir): C:\automap\staging',
            'Staging folder: C:\Users\me\Documents\WebWorks ePublisher AutoMap\Staging',
            "Staging folder of the 'Release 2026.1' workspace: D:\Builds\2026.1\Staging"))
    $expectedRoots = 'D:\Builds\2026.1\Staging|C:\automap\staging|C:\Users\me\Documents\WebWorks ePublisher AutoMap\Staging'
    if (($reported -join '|') -ceq $expectedRoots) { $script:Pass++; Write-Output 'PASS: reported-staging-roots' }
    else { $script:Fail++; Write-Output "FAIL: reported-staging-roots`n--- actual ---`n$($reported -join '|')" }

    # Get-LogScanBases prefers the reported folder over the default.
    $workspaceStaging = Join-Path $tempRoot 'WorkspaceStaging'
    New-Item -ItemType Directory -Path (Join-Path $workspaceStaging 'Trial Job\Logs') -Force | Out-Null
    $jobFile = Join-Path $tempRoot 'trial.waj'
    Set-Content -LiteralPath $jobFile -Value '<?xml version="1.0" encoding="utf-8"?><Job name="Trial Job" version="1.0"></Job>' -Encoding UTF8
    $bases = @(Get-LogScanBases -ProjectFiles @($jobFile) -PassthroughArgs @($jobFile) -ReportedStagingRoots @($workspaceStaging))
    $expectedBase = Join-Path $workspaceStaging 'Trial Job'
    if (($bases.Count -eq 1) -and ($bases[0].Dir -eq $expectedBase) -and $bases[0].Announce) { $script:Pass++; Write-Output 'PASS: scan-base-uses-reported-staging' }
    else { $script:Fail++; Write-Output "FAIL: scan-base-uses-reported-staging`n--- actual ---`n$(($bases | ForEach-Object { $_.Dir }) -join ', ')" }
}
finally {
    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Output ''
Write-Output "Results: $($script:Pass) passed, $($script:Fail) failed"

if ($script:Fail -eq 0) { exit 0 } else { exit 1 }
