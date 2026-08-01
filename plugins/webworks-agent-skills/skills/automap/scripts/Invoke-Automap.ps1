<#
Invoke-Automap.ps1
Wrapper for the WebWorks ePublisher AutoMap CLI (WebWorks.Automap.exe).

The wrapper exists for exactly four jobs:
  1. Resolve the AutoMap executable (-ExePath, AUTOMAP_EXE_PATH env var, or
     auto-detection via Find-AutomapInstallation.ps1).
  2. Suppress AutoMap's streaming stdout (stderr passes through), reporting
     a one-line result instead.
  3. Apply development-safe default flags (-n, --skip-reports) and require
     an explicit target, unless opted out. Composition jobs (.wacj) always
     run with native semantics: no flag applies to a compose and targets
     belong to member builds, so nothing is injected and no target is
     required (use --dryrun to rehearse a compose safely).
  4. Scan generate.log files (and, for a .wacj, the composition's
     <job name>-log.txt beside the file) after a successful run and report
     warning/error counts.

Every AutoMap flag is PASS-THROUGH. The wrapper never translates, renames,
or owns AutoMap options; anything that is not a wrapper option below is
forwarded to WebWorks.Automap.exe verbatim.

Usage:
  powershell -ExecutionPolicy Bypass -File Invoke-Automap.ps1 `
      [wrapper options] [--] <automap options> <project-file>

Wrapper options (must come before the first AutoMap option or the --
separator; everything after -- is always forwarded verbatim):
  -NoDefaults      Verbatim native CLI behavior: no injected flags, no
                   explicit-target requirement.
  -AllTargets      Waive only the explicit-target requirement (for .waj,
                   builds the job file's build="True" set; for projects,
                   builds every target).
  -ExePath <path>  AutoMap executable to run (overrides AUTOMAP_EXE_PATH
                   and auto-detection).
  -Help            Show usage.

Default flags injected unless -NoDefaults:
  -n               unless -n/--nodeploy already present, or deploy intent
                   is signaled (-d/--deployfolder, -l/--cleandeploy,
                   --deploysettings, --deployscope, --destination,
                   --dryrun).
  --skip-reports   unless already present (requires ePublisher 2025.1+;
                   use -NoDefaults with older versions).
And an explicit -t/--target is required unless -NoDefaults or -AllTargets.

Exit codes:
  0 - Build succeeded
  1 - Build failed
  2 - Invalid arguments / no target specified
  3 - AutoMap not found
  4 - Project file not found

Requires Windows PowerShell 5.1 or later.
#>

Set-StrictMode -Version 2.0

$script:ProjectExtensionPattern = '\.(wep|wrp|waj|wacj|wxsp)$'
$script:DefaultStagingRoot = Join-Path $env:USERPROFILE 'Documents\WebWorks ePublisher AutoMap\Staging'

# Severity markers the product stamps on log lines. Publish Core localizes
# them (Core/Resources/Messages.resx plus its .de/.fr/.ja satellites, keys
# Warn/Error), and the satellites ship with every install, so matching the
# English tokens alone reports a false 0/0 on a localized machine. Both scan
# sites share these sets. Each token carries its closing bracket, so '[WARN]'
# cannot also match inside '[WARNUNG]'.
#
# The Japanese tokens are built from character codes rather than written as
# literals: this file has no BOM, and Windows PowerShell 5.1 parses a BOM-less
# script in the host's ANSI codepage, which would mangle literal kanji.
$script:WarnMarkers = @(
    '[WARN]',                                                # en
    '[WARNUNG]',                                             # de
    '[AVERTISSEMENT]',                                       # fr
    ('[' + [char]0x8B66 + [char]0x544A + ']')                # ja
)
$script:ErrorMarkers = @(
    '[ERROR]',                                               # en
    '[FEHLER]',                                              # de
    '[ERREUR]',                                              # fr
    ('[' + [char]0x30A8 + [char]0x30E9 + [char]0x30FC + ']') # ja
)
$script:WarnMarkerPattern = (($script:WarnMarkers | ForEach-Object { [regex]::Escape($_) }) -join '|')
$script:ErrorMarkerPattern = (($script:ErrorMarkers | ForEach-Object { [regex]::Escape($_) }) -join '|')

function Write-StderrLine {
    param([string]$Message)
    [Console]::Error.WriteLine($Message)
}

function Show-Usage {
    Write-Output @'
Usage: Invoke-Automap.ps1 [wrapper options] [--] <automap options> <project-file>

Wrapper options (before the first AutoMap option or the -- separator):
  -NoDefaults      Verbatim native CLI behavior: no injected flags, no
                   explicit-target requirement.
  -AllTargets      Waive only the explicit-target requirement.
  -ExePath <path>  AutoMap executable to run (overrides AUTOMAP_EXE_PATH).
  -Help            Show this help.

Everything else is forwarded to WebWorks.Automap.exe verbatim. Run
"WebWorks.Automap.exe --help" for the native option list (-c, -n, -t,
--target, -d, -s, -l, --skip-reports, ...).

Defaults injected unless -NoDefaults: -n (unless deploy flags present),
--skip-reports (2025.1+). An explicit -t/--target is required unless
-NoDefaults or -AllTargets. A composition job (.wacj) always runs with
native semantics -- nothing is injected and no target is required; pass
--dryrun to rehearse a compose without touching the mirror.

Examples:
  # Dev build, safe defaults applied
  Invoke-Automap.ps1 -- -t "WebWorks Reverb 2.0" project.wep

  # Job file: build its enabled target set, still no deploy/reports
  Invoke-Automap.ps1 -AllTargets -- job.waj

  # Composition job: rehearse the compose dry, then run it for real
  Invoke-Automap.ps1 -- --dryrun composition.wacj
  Invoke-Automap.ps1 -- composition.wacj

  # Production: exact native semantics (deploys, generates reports)
  Invoke-Automap.ps1 -NoDefaults -- -c -t "WebWorks Reverb 2.0" project.wep

Environment:
  AUTOMAP_EXE_PATH  AutoMap executable to run (e.g. a development build).
'@
}

# Extracts target names from a project (.wep/.wrp/.wxsp) or job (.waj) file.
# Job-file targets carry an "(enabled)" suffix when marked build="True".
function Get-ProjectTargets {
    param([string]$Path)

    $content = Get-Content -LiteralPath $Path -Raw -ErrorAction SilentlyContinue
    if (-not $content) { return @() }

    $targets = @()
    if ($Path -match '\.waj$') {
        foreach ($match in [regex]::Matches($content, '<Target\b[^>]*>')) {
            $tag = $match.Value
            $nameMatch = [regex]::Match($tag, 'name\s*=\s*"([^"]*)"')
            if (-not $nameMatch.Success) { continue }
            $name = $nameMatch.Groups[1].Value
            if ($tag -match 'build\s*=\s*"True"') {
                $targets += "$name (enabled)"
            }
            else {
                $targets += $name
            }
        }
    }
    else {
        foreach ($match in [regex]::Matches($content, 'TargetName\s*=\s*"([^"]*)"')) {
            $targets += $match.Groups[1].Value
        }
    }
    return $targets
}

# Resolves the AutoMap CLI executable: explicit override, then the
# AUTOMAP_EXE_PATH environment variable, then auto-detection.
# Returns the path, or $null after writing an error.
function Get-AutomapExePath {
    param([string]$Override)

    foreach ($source in @(
            @{ Value = $Override; Label = '-ExePath' },
            @{ Value = $env:AUTOMAP_EXE_PATH; Label = 'AUTOMAP_EXE_PATH' }
        )) {
        if (-not $source.Value) { continue }
        if (Test-Path -LiteralPath $source.Value -PathType Leaf) {
            return $source.Value
        }
        Write-StderrLine "[ERROR] $($source.Label) is set but file not found: $($source.Value)"
        return $null
    }

    $finder = Join-Path $PSScriptRoot 'Find-AutomapInstallation.ps1'
    $detected = & $finder
    if ($LASTEXITCODE -eq 0 -and $detected) {
        return [string]$detected
    }
    Write-StderrLine '[ERROR] AutoMap installation not found. Install ePublisher AutoMap or set AUTOMAP_EXE_PATH.'
    return $null
}

# Counts marked lines in one log file and returns @{ Warn = <n>; Error = <n> },
# or $null when the file cannot be read. The read encoding is pinned to UTF-8
# because that is what the product writes -- generate.log with a BOM, the
# composition log without -- so the non-ASCII tokens do not depend on the
# host's active codepage.
function Get-LogMarkerCount {
    param([string]$Path)

    try {
        return [pscustomobject]@{
            Warn  = @(Select-String -LiteralPath $Path -Pattern $script:WarnMarkerPattern -Encoding UTF8).Count
            Error = @(Select-String -LiteralPath $Path -Pattern $script:ErrorMarkerPattern -Encoding UTF8).Count
        }
    }
    catch {
        return $null
    }
}

# Scans Logs/<Target>/generate.log under a base directory and returns one
# summary object per target that has warnings or errors:
#   @{ Text = '[WARNING] 3 warning(s), 0 error(s) in Logs/T/generate.log'; IsError = $false }
# Purely observational -- callers must not let scan results alter exit codes.
function Get-GenerateLogSummaries {
    param([string]$BaseDir)

    $summaries = @()
    $logsRoot = Join-Path $BaseDir 'Logs'
    if (-not (Test-Path -LiteralPath $logsRoot -PathType Container)) { return $summaries }

    foreach ($logFile in Get-ChildItem -Path (Join-Path $logsRoot '*\generate.log') -ErrorAction SilentlyContinue | Sort-Object FullName) {
        $counts = Get-LogMarkerCount -Path $logFile.FullName
        if (-not $counts) { continue }
        $warnCount = $counts.Warn
        $errorCount = $counts.Error
        if (($warnCount -eq 0) -and ($errorCount -eq 0)) { continue }

        # Display path relative to the base directory, forward slashes.
        $relative = $logFile.FullName.Substring($BaseDir.TrimEnd('\', '/').Length).TrimStart('\', '/') -replace '\\', '/'
        $isError = ($errorCount -gt 0)
        $label = '[WARNING]'
        if ($isError) { $label = '[ERROR]' }
        $summaries += [pscustomobject]@{
            Text    = "$label $warnCount warning(s), $errorCount error(s) in $relative"
            IsError = $isError
        }
    }
    return $summaries
}

# A composition job writes a job-style log beside the .wacj file, named
# <job name>-log.txt (job name attribute, falling back to the file's base
# name). Returns a summary object like Get-GenerateLogSummaries, or $null
# when the log is absent or clean. Purely observational.
function Get-CompositionLogSummary {
    param([string]$Path)

    $fullPath = (Resolve-Path -LiteralPath $Path).Path
    $dir = Split-Path -Parent $fullPath

    $jobName = $null
    $content = Get-Content -LiteralPath $fullPath -Raw -ErrorAction SilentlyContinue
    if ($content) {
        $nameMatch = [regex]::Match($content, '<CompositionJob\b[^>]*\bname\s*=\s*"([^"]*)"')
        if ($nameMatch.Success) { $jobName = $nameMatch.Groups[1].Value }
    }
    if (-not $jobName) { $jobName = [System.IO.Path]::GetFileNameWithoutExtension($fullPath) }

    $logFile = Join-Path $dir "$jobName-log.txt"
    if (-not (Test-Path -LiteralPath $logFile -PathType Leaf)) { return $null }

    $counts = Get-LogMarkerCount -Path $logFile
    if (-not $counts) { return $null }
    $warnCount = $counts.Warn
    $errorCount = $counts.Error
    if (($warnCount -eq 0) -and ($errorCount -eq 0)) { return $null }

    $isError = ($errorCount -gt 0)
    $label = '[WARNING]'
    if ($isError) { $label = '[ERROR]' }
    return [pscustomobject]@{
        Text    = "$label $warnCount warning(s), $errorCount error(s) in $jobName-log.txt"
        IsError = $isError
    }
}

# Determines the directories whose Logs/ should be scanned after a build.
# Project files log beside the project; job files (.waj) log under the
# staging folder at <staging>/<JobName>/Logs.
function Get-LogScanBases {
    param(
        [string[]]$ProjectFiles,
        [string[]]$PassthroughArgs
    )

    # Staging directory from pass-through args: -s <dir>, --stagingdir <dir>,
    # or --stagingdir=<dir>. Read-only inspection; the args are still
    # forwarded untouched.
    $stagingRoot = $null
    for ($i = 0; $i -lt $PassthroughArgs.Count; $i++) {
        $token = $PassthroughArgs[$i]
        if (($token -ceq '-s') -or ($token -ceq '--stagingdir')) {
            if ($i + 1 -lt $PassthroughArgs.Count) { $stagingRoot = $PassthroughArgs[$i + 1] }
        }
        elseif ($token -clike '--stagingdir=*') {
            $stagingRoot = $token.Substring('--stagingdir='.Length).Trim('"')
        }
    }

    $bases = @()
    foreach ($file in $ProjectFiles) {
        $fullPath = (Resolve-Path -LiteralPath $file).Path

        if ($file -match '\.waj$') {
            $root = $stagingRoot
            if (-not $root) { $root = $script:DefaultStagingRoot }

            $content = Get-Content -LiteralPath $fullPath -Raw -ErrorAction SilentlyContinue
            $jobName = $null
            if ($content) {
                $jobMatch = [regex]::Match($content, '<Job\b[^>]*\bname\s*=\s*"([^"]*)"')
                if ($jobMatch.Success) { $jobName = $jobMatch.Groups[1].Value }
            }
            if ($jobName) {
                $jobDir = Join-Path $root $jobName
                if (Test-Path -LiteralPath $jobDir -PathType Container) {
                    $bases += [pscustomobject]@{ Dir = $jobDir; Announce = $true }
                    continue
                }
            }
        }

        $bases += [pscustomobject]@{ Dir = (Split-Path -Parent $fullPath); Announce = $false }
    }
    return $bases
}

function Invoke-Main {
    param([string[]]$Arguments = @())

    $argv = @($Arguments)

    # --- Wrapper option parsing -------------------------------------------
    # Wrapper options are only recognized before the first AutoMap token.
    # A bare -- always ends wrapper parsing; everything after it is
    # forwarded verbatim.
    $noDefaults = $false
    $allTargets = $false
    $exePathOverride = $null
    $passthrough = @()

    $i = 0
    while ($i -lt $argv.Count) {
        $token = [string]$argv[$i]
        if ($token -eq '--') {
            if ($i + 1 -lt $argv.Count) { $passthrough = @($argv[($i + 1)..($argv.Count - 1)]) }
            $i = $argv.Count
        }
        elseif ($token -ieq '-NoDefaults') {
            $noDefaults = $true
            $i++
        }
        elseif ($token -ieq '-AllTargets') {
            $allTargets = $true
            $i++
        }
        elseif ($token -ieq '-ExePath') {
            if ($i + 1 -ge $argv.Count) {
                Write-StderrLine '[ERROR] -ExePath requires a value'
                exit 2
            }
            $exePathOverride = [string]$argv[$i + 1]
            $i += 2
        }
        elseif (($token -ieq '-Help') -or ($token -eq '-h') -or ($token -eq '--help') -or ($token -eq '-?')) {
            Show-Usage
            exit 0
        }
        else {
            $passthrough = @($argv[$i..($argv.Count - 1)])
            $i = $argv.Count
        }
    }

    if ($passthrough.Count -eq 0) {
        Write-StderrLine '[ERROR] Project file required'
        Show-Usage
        exit 2
    }

    # --- Project file validation ------------------------------------------
    # Read-only inspection: project/job files are recognized by extension so
    # the wrapper can validate existence, enforce the target requirement,
    # and locate logs. The tokens themselves are forwarded untouched.
    $projectFiles = @($passthrough | Where-Object {
            ($_ -notlike '-*') -and ($_ -match $script:ProjectExtensionPattern)
        })

    if ($projectFiles.Count -eq 0) {
        Write-StderrLine '[ERROR] No project or job file (.wep, .wrp, .waj, .wacj, .wxsp) found in arguments'
        Show-Usage
        exit 2
    }

    foreach ($file in $projectFiles) {
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
            Write-StderrLine "[ERROR] Project file not found: $file"
            exit 4
        }
    }

    # --- Composition jobs run verbatim -------------------------------------
    # A .wacj composes already-deployed output: -n would fight the run's
    # purpose, --skip-reports has nothing to skip, and output targets belong
    # to the member builds, not the composition. So a composition implies
    # -NoDefaults; --dryrun is the native way to rehearse a compose safely.
    $compositionFiles = @($projectFiles | Where-Object { $_ -match '\.wacj$' })
    if (($compositionFiles.Count -gt 0) -and (-not $noDefaults)) {
        $noDefaults = $true
        Write-Output '[INFO] Composition job (.wacj): native CLI semantics (no injected flags, no target requirement); pass --dryrun to rehearse the compose.'
    }

    # --- Explicit-target requirement --------------------------------------
    $hasTargetFlag = $false
    foreach ($token in $passthrough) {
        if (($token -ceq '-t') -or ($token -ceq '--target') -or ($token -clike '--target=*')) {
            $hasTargetFlag = $true
        }
    }

    if ((-not $noDefaults) -and (-not $allTargets) -and (-not $hasTargetFlag)) {
        Write-StderrLine '[ERROR] No target specified. Pass -t "<name>" (or --target="Name1,Name2") to choose target(s).'
        foreach ($file in $projectFiles) {
            Write-StderrLine "[ERROR] Available targets in ${file}:"
            foreach ($target in Get-ProjectTargets -Path $file) {
                Write-StderrLine "[ERROR]   - $target"
            }
        }
        Write-StderrLine '[ERROR] To build without naming targets, pass the wrapper option -AllTargets (or -NoDefaults for verbatim CLI behavior).'
        exit 2
    }

    # --- Default flag injection -------------------------------------------
    $finalArgs = @($passthrough)
    if (-not $noDefaults) {
        $injected = @()

        $hasSkipReports = ($passthrough -ccontains '--skip-reports')
        if (-not $hasSkipReports) { $injected += '--skip-reports' }

        $hasNoDeploy = ($passthrough -ccontains '-n') -or ($passthrough -ccontains '--nodeploy')
        $deployIntent = $false
        foreach ($token in $passthrough) {
            if (($token -ceq '-d') -or ($token -ceq '-l') -or
                ($token -ceq '--deployfolder') -or ($token -clike '--deployfolder=*') -or
                ($token -ceq '--cleandeploy') -or
                ($token -ceq '--deploysettings') -or ($token -clike '--deploysettings=*') -or
                ($token -ceq '--deployscope') -or ($token -clike '--deployscope=*') -or
                ($token -ceq '--destination') -or ($token -clike '--destination=*') -or
                ($token -ceq '--dryrun')) {
                $deployIntent = $true
            }
        }
        if ((-not $hasNoDeploy) -and (-not $deployIntent)) { $injected = @('-n') + $injected }

        if ($injected.Count -gt 0) {
            $finalArgs = @($injected) + $finalArgs
            Write-Output "[INFO] Applied default flags: $($injected -join ' ') (pass -NoDefaults for verbatim CLI behavior)"
        }
    }

    # --- Executable resolution --------------------------------------------
    $exePath = Get-AutomapExePath -Override $exePathOverride
    if (-not $exePath) { exit 3 }

    # --- Execution ---------------------------------------------------------
    # AutoMap's streaming stdout (banner, per-pipeline progress) is
    # suppressed to keep output minimal; stderr passes through untouched.
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    $buildExitCode = 1
    try {
        & $exePath @finalArgs > $null
        $buildExitCode = $LASTEXITCODE
    }
    catch {
        Write-StderrLine "[ERROR] Failed to run AutoMap: $($_.Exception.Message)"
        exit 1
    }
    $stopwatch.Stop()
    $duration = [int][math]::Round($stopwatch.Elapsed.TotalSeconds)

    if ($buildExitCode -ne 0) {
        Write-StderrLine "[ERROR] Build failed with exit code $buildExitCode after ${duration}s"
        exit 1
    }

    Write-Output "[SUCCESS] Build completed in ${duration}s"

    # --- Post-build log scan (observational; never alters the exit code) ---
    try {
        foreach ($file in $compositionFiles) {
            $summary = Get-CompositionLogSummary -Path $file
            if ($summary) {
                if ($summary.IsError) { Write-StderrLine $summary.Text }
                else { Write-Output $summary.Text }
            }
        }
        $buildFiles = @($projectFiles | Where-Object { $_ -notmatch '\.wacj$' })
        foreach ($base in Get-LogScanBases -ProjectFiles $buildFiles -PassthroughArgs $passthrough) {
            $summaries = @(Get-GenerateLogSummaries -BaseDir $base.Dir)
            if (($summaries.Count -gt 0) -and $base.Announce) {
                Write-Output "[INFO] Logs under staging folder: $($base.Dir)"
            }
            foreach ($summary in $summaries) {
                if ($summary.IsError) { Write-StderrLine $summary.Text }
                else { Write-Output $summary.Text }
            }
        }
    }
    catch {
        Write-StderrLine "[WARNING] Log scan failed: $($_.Exception.Message)"
    }

    exit 0
}

# Dot-source this file to import its functions (e.g. from the test harness)
# without running a build.
if ($MyInvocation.InvocationName -ne '.') {
    Invoke-Main $args
}
