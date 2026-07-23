<#
test-wrapper-args.ps1
Integration tests for Invoke-Automap.ps1 argument handling: wrapper option
parsing, pass-through fidelity, default flag injection, the explicit-target
requirement, and exit codes.

Runs the wrapper as a child Windows PowerShell 5.1 process (the supported
baseline) against a stub executable that records the arguments it receives,
so no ePublisher installation is needed.

Usage: powershell -ExecutionPolicy Bypass -File test-wrapper-args.ps1
Exit code: 0 if all assertions pass, 1 otherwise.
#>

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$wrapper = Join-Path $scriptDir '..\scripts\Invoke-Automap.ps1'

# --- Sandbox: stub AutoMap + sample project files -------------------------

$work = Join-Path $env:TEMP ("automap-wrapper-test-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $work | Out-Null

$stub = Join-Path $work 'stub-automap.cmd'
Set-Content -LiteralPath $stub -Encoding Ascii -Value @'
@echo off
if not defined STUB_EXIT set STUB_EXIT=0
echo %* > "%STUB_OUT%"
exit /b %STUB_EXIT%
'@

$project = Join-Path $work 'sample.wep'
Set-Content -LiteralPath $project -Encoding Ascii -Value @'
<Project><Formats><Format TargetName="Target A"/><Format TargetName="Target B"/></Formats></Project>
'@

$job = Join-Path $work 'sample.waj'
Set-Content -LiteralPath $job -Encoding Ascii -Value @'
<Job name="Sample Job"><Targets><Target name="Target A" build="True"/><Target name="Target B" build="False"/></Targets></Job>
'@

$composition = Join-Path $work 'sample.wacj'
Set-Content -LiteralPath $composition -Encoding Ascii -Value @'
<CompositionJob name="Sample Composition" version="1.0"><Jobs><Job path="sample.waj" role="shell"/></Jobs><Destination name="Mirror"/></CompositionJob>
'@

$argsFile = Join-Path $work 'stub-args.txt'
$env:STUB_OUT = $argsFile
$env:STUB_EXIT = '0'

$script:Pass = 0
$script:Fail = 0

function Invoke-Wrapper {
    # Runs the wrapper in a child powershell.exe, returning combined output
    # and exit code.
    param([string[]]$WrapperArgs)

    Remove-Item -LiteralPath $env:STUB_OUT -ErrorAction SilentlyContinue
    # Under $ErrorActionPreference = 'Stop', PowerShell 5.1 turns redirected
    # native stderr lines into terminating NativeCommandErrors; relax while
    # the child runs.
    $previousEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = & powershell -NoProfile -ExecutionPolicy Bypass -File $wrapper @WrapperArgs 2>&1 |
            ForEach-Object { $_.ToString() }
    }
    finally {
        $ErrorActionPreference = $previousEap
    }
    $stubArgs = ''
    if (Test-Path -LiteralPath $env:STUB_OUT) {
        $stubArgs = (Get-Content -LiteralPath $env:STUB_OUT -Raw).Trim()
    }
    return [pscustomobject]@{
        ExitCode = $LASTEXITCODE
        Output   = ($output -join "`n")
        StubArgs = $stubArgs
    }
}

function Assert {
    param([string]$Name, [bool]$Condition, [string]$Detail = '')

    if ($Condition) {
        $script:Pass++
        Write-Output "PASS: $Name"
    }
    else {
        $script:Fail++
        Write-Output "FAIL: $Name"
        if ($Detail) { Write-Output "      $Detail" }
    }
}

# --- Cases -----------------------------------------------------------------

# 1. Defaults injected before user args; build succeeds.
$r = Invoke-Wrapper @('-ExePath', $stub, '--', '-t', 'Target A', $project)
Assert 'defaults: exit 0' ($r.ExitCode -eq 0) $r.Output
Assert 'defaults: -n injected' ($r.StubArgs -match '(^| )-n( |$)') $r.StubArgs
Assert 'defaults: --skip-reports injected' ($r.StubArgs -match '--skip-reports') $r.StubArgs
Assert 'defaults: injected flags precede user args' ($r.StubArgs -match '^-n --skip-reports ') $r.StubArgs
Assert 'defaults: quoted target survives' ($r.StubArgs -match '"Target A"') $r.StubArgs
Assert 'defaults: info line reported' ($r.Output -match '\[INFO\] Applied default flags: -n --skip-reports') $r.Output
Assert 'defaults: success line reported' ($r.Output -match '\[SUCCESS\] Build completed in \d+s') $r.Output

# 2. Already-present flags are not duplicated.
$r = Invoke-Wrapper @('-ExePath', $stub, '--', '-n', '--skip-reports', '-t', 'Target A', $project)
Assert 'no duplicates: single -n' (@([regex]::Matches($r.StubArgs, '(^| )-n( |$)')).Count -eq 1) $r.StubArgs
Assert 'no duplicates: single --skip-reports' (@([regex]::Matches($r.StubArgs, '--skip-reports')).Count -eq 1) $r.StubArgs

# 3. Deploy intent suppresses -n but not --skip-reports.
$r = Invoke-Wrapper @('-ExePath', $stub, '--', '-t', 'Target A', '-d', (Join-Path $work 'deploy'), $project)
Assert 'deploy intent: no -n injected' (-not ($r.StubArgs -match '(^| )-n( |$)')) $r.StubArgs
Assert 'deploy intent: --skip-reports still injected' ($r.StubArgs -match '--skip-reports') $r.StubArgs

# 4. -NoDefaults: verbatim pass-through, no injection, no target requirement.
$r = Invoke-Wrapper @('-ExePath', $stub, '-NoDefaults', '--', $project)
Assert '-NoDefaults: exit 0' ($r.ExitCode -eq 0) $r.Output
Assert '-NoDefaults: nothing injected' ($r.StubArgs -eq ('"' + $project + '"') -or $r.StubArgs -eq $project) $r.StubArgs

# 5. Explicit-target requirement: no -t and no waiver fails with target list.
$r = Invoke-Wrapper @('-ExePath', $stub, '--', $project)
Assert 'target guard: exit 2' ($r.ExitCode -eq 2) $r.Output
Assert 'target guard: lists targets' (($r.Output -match 'Target A') -and ($r.Output -match 'Target B')) $r.Output
Assert 'target guard: AutoMap not invoked' ($r.StubArgs -eq '') $r.StubArgs

# 6. Job files list enabled markers in the guard message.
$r = Invoke-Wrapper @('-ExePath', $stub, '--', $job)
Assert 'job guard: exit 2' ($r.ExitCode -eq 2) $r.Output
Assert 'job guard: enabled marker' ($r.Output -match 'Target A \(enabled\)') $r.Output

# 7. -AllTargets waives only the target requirement; defaults still apply.
$r = Invoke-Wrapper @('-ExePath', $stub, '-AllTargets', '--', $job)
Assert '-AllTargets: exit 0' ($r.ExitCode -eq 0) $r.Output
Assert '-AllTargets: defaults still injected' ($r.StubArgs -match '^-n --skip-reports ') $r.StubArgs

# 8. Wrapper options are not recognized after the -- separator.
$r = Invoke-Wrapper @('-ExePath', $stub, '-AllTargets', '--', '-NoDefaults', $project)
Assert 'post-separator: -NoDefaults forwarded verbatim' ($r.StubArgs -match '-NoDefaults') $r.StubArgs

# 9. Missing project file: exit 4.
$r = Invoke-Wrapper @('-ExePath', $stub, '--', '-t', 'X', (Join-Path $work 'missing.wep'))
Assert 'missing file: exit 4' ($r.ExitCode -eq 4) $r.Output

# 10. No project file argument at all: exit 2.
$r = Invoke-Wrapper @('-ExePath', $stub, '--', '-t', 'X')
Assert 'no project file: exit 2' ($r.ExitCode -eq 2) $r.Output

# 11. Build failure: stub exit code surfaces as wrapper exit 1.
$env:STUB_EXIT = '7'
$r = Invoke-Wrapper @('-ExePath', $stub, '--', '-t', 'Target A', $project)
$env:STUB_EXIT = '0'
Assert 'build failure: exit 1' ($r.ExitCode -eq 1) $r.Output
Assert 'build failure: reported with code' ($r.Output -match '\[ERROR\] Build failed with exit code 7') $r.Output

# 12. -ExePath without a value: exit 2.
$r = Invoke-Wrapper @('-ExePath')
Assert 'dangling -ExePath: exit 2' ($r.ExitCode -eq 2) $r.Output

# 13. Composition job (.wacj): recognized, native semantics, no target guard.
$r = Invoke-Wrapper @('-ExePath', $stub, '--', '--dryrun', $composition)
Assert 'wacj: exit 0' ($r.ExitCode -eq 0) $r.Output
Assert 'wacj: nothing injected' (-not ($r.StubArgs -match '(^| )-n( |$)') -and -not ($r.StubArgs -match '--skip-reports')) $r.StubArgs
Assert 'wacj: --dryrun forwarded verbatim' ($r.StubArgs -match '--dryrun') $r.StubArgs
Assert 'wacj: native-semantics info line' ($r.Output -match '\[INFO\] Composition job \(\.wacj\)') $r.Output

# 14. Composition job with explicit -NoDefaults: no redundant info line.
$r = Invoke-Wrapper @('-ExePath', $stub, '-NoDefaults', '--', $composition)
Assert 'wacj -NoDefaults: exit 0' ($r.ExitCode -eq 0) $r.Output
Assert 'wacj -NoDefaults: no info line' (-not ($r.Output -match '\[INFO\] Composition job')) $r.Output

# 15. Composition log scan: <job name>-log.txt beside the .wacj is summarized.
$compositionLog = Join-Path $work 'Sample Composition-log.txt'
Set-Content -LiteralPath $compositionLog -Encoding Ascii -Value @'
Composition job 'Sample Composition' started.
[Warning] parcel 'Extra' has no descriptor; omitted.
[Error] Destination 'Mirror' is not defined in deploy.prefs, the --deploysettings overlay, or inline in the composition job.
'@
$r = Invoke-Wrapper @('-ExePath', $stub, '--', $composition)
Assert 'wacj log scan: counts reported' ($r.Output -match '\[ERROR\] 1 warning\(s\), 1 error\(s\) in Sample Composition-log\.txt') $r.Output
Assert 'wacj log scan: exit code unaffected' ($r.ExitCode -eq 0) $r.Output
Remove-Item -LiteralPath $compositionLog -ErrorAction SilentlyContinue

# --- Results ---------------------------------------------------------------

Remove-Item -Recurse -Force -LiteralPath $work -ErrorAction SilentlyContinue
Remove-Item Env:\STUB_OUT -ErrorAction SilentlyContinue
Remove-Item Env:\STUB_EXIT -ErrorAction SilentlyContinue

Write-Output ''
Write-Output "Results: $($script:Pass) passed, $($script:Fail) failed"

if ($script:Fail -eq 0) { exit 0 } else { exit 1 }
