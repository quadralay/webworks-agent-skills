<#
test-wacj-tools.ps1
Test driver for composition job (.wacj) support in the AutoMap Python tools:
parse-job.py, validate-job.py, list-job-targets.py and create-job.py.

Runs each tool against the fixtures under fixtures/composition-federation
(a valid federated composition) and fixtures/composition-invalid (hand-edit
defects that must be rejected), asserts exit codes and key output, and
round-trips the composition through --config / create-job.py. Also spot-checks
the .waj path so composition support cannot regress it.

Usage: powershell -ExecutionPolicy Bypass -File test-wacj-tools.ps1
Exit code: 0 if all assertions pass, 1 otherwise.
#>

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$scripts = Join-Path $scriptDir '..\scripts'
$federation = Join-Path $scriptDir 'fixtures\composition-federation'
$invalid = Join-Path $scriptDir 'fixtures\composition-invalid'

$python = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $python) {
    Write-Output 'SKIP: python is not on PATH; cannot run the .wacj tool tests.'
    exit 1
}

$script:Pass = 0
$script:Fail = 0

function Invoke-Tool {
    param(
        [string]$Tool,
        [string[]]$Arguments,
        [string]$WorkingDirectory
    )

    $toolPath = Join-Path $scripts $Tool
    $previousLocation = Get-Location
    if ($WorkingDirectory) { Set-Location -LiteralPath $WorkingDirectory }

    # Under $ErrorActionPreference = 'Stop', PowerShell 5.1 turns redirected
    # native stderr lines into terminating NativeCommandErrors; relax while
    # the tool runs (the tools write diagnostics to stderr by design).
    $previousEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = & $python.Source $toolPath @Arguments 2>&1 |
            ForEach-Object { $_.ToString() }
        $exit = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousEap
        Set-Location -LiteralPath $previousLocation
    }

    return [pscustomobject]@{ Output = ($output -join "`n"); ExitCode = $exit }
}

function Assert-Equal {
    param([string]$Name, $Expected, $Actual)

    if ($Expected -eq $Actual) {
        $script:Pass++
        Write-Output "PASS: $Name"
    }
    else {
        $script:Fail++
        Write-Output "FAIL: $Name"
        Write-Output "  expected: $Expected"
        Write-Output "  actual:   $Actual"
    }
}

function Assert-Contains {
    param([string]$Name, [string]$Needle, [string]$Haystack)

    if ($Haystack -and $Haystack.Contains($Needle)) {
        $script:Pass++
        Write-Output "PASS: $Name"
    }
    else {
        $script:Fail++
        Write-Output "FAIL: $Name"
        Write-Output "  missing: $Needle"
        Write-Output "--- output ---"
        Write-Output $Haystack
        Write-Output "--------------"
    }
}

# --- parse-job.py -----------------------------------------------------------

$composition = Join-Path $federation 'composition.wacj'

$result = Invoke-Tool -Tool 'parse-job.py' -Arguments @($composition)
Assert-Equal 'parse-job .wacj exit code' 0 $result.ExitCode
Assert-Contains 'parse-job names the composition' 'Composition Job:' $result.Output
Assert-Contains 'parse-job reports Custom mode' 'custom (compose exactly the declared placements)' $result.Output
Assert-Contains 'parse-job reports the member count' 'Members (3 total, 1 built' $result.Output
Assert-Contains 'parse-job reports the inline definition' 'Inline definition: ProductionMirror' $result.Output

$result = Invoke-Tool -Tool 'parse-job.py' -Arguments @('--json', $composition)
Assert-Equal 'parse-job --json exit code' 0 $result.ExitCode
$json = $result.Output | ConvertFrom-Json
Assert-Equal 'parse-job --json kind' 'composition' $json.kind
Assert-Equal 'parse-job --json member count' 3 $json.members.Count
Assert-Equal 'parse-job --json composition-wide target' 'WebWorks Reverb 2.0' $json.outputTarget
Assert-Equal 'parse-job --json per-member target override' 'Online Docs' $json.members[2].effectiveTarget
Assert-Equal 'parse-job --json target source' 'member override' $json.members[2].targetSource
Assert-Equal 'parse-job --json build flag' $true $json.members[1].build
Assert-Equal 'parse-job --json destination name' 'ProductionMirror' $json.destination.name
Assert-Equal 'parse-job --json inline action' 'file' $json.destination.deploySettings[0].action
Assert-Equal 'parse-job --json TOC container' 'container' $json.mergeSettings.spec[0].kind
Assert-Equal 'parse-job --json nested group' 'Parcel A' $json.mergeSettings.spec[0].children[0].name

# The legacy <DeployTarget> spelling loads as the destination.
$result = Invoke-Tool -Tool 'parse-job.py' -Arguments @('--json', (Join-Path $invalid 'broken.wacj'))
$json = $result.Output | ConvertFrom-Json
Assert-Equal 'parse-job reads the legacy DeployTarget spelling' 'LegacyMirror' $json.destination.name
Assert-Equal 'parse-job flags the legacy spelling' $true $json.destination.legacySpelling
Assert-Equal 'parse-job normalizes an unknown role' 'infer' $json.members[1].role
Assert-Equal 'parse-job keeps the declared role' 'member' $json.members[1].roleDeclared
Assert-Equal 'parse-job rejects a non-boolean build' $false $json.members[1].build

# --- validate-job.py --------------------------------------------------------

$result = Invoke-Tool -Tool 'validate-job.py' -Arguments @('-v', $composition)
Assert-Equal 'validate-job .wacj exit code' 0 $result.ExitCode
Assert-Contains 'validate-job passes the fixture' 'Validation: PASSED' $result.Output

$result = Invoke-Tool -Tool 'validate-job.py' -Arguments @('-v', '--check-members', $composition)
Assert-Equal 'validate-job --check-members exit code' 0 $result.ExitCode
Assert-Contains 'validate-job finds every member' 'All 3 members found' $result.Output
Assert-Contains 'validate-job cross-checks .waj members' '.waj members cross-checked' $result.Output

$result = Invoke-Tool -Tool 'validate-job.py' -Arguments @((Join-Path $invalid 'broken.wacj'))
Assert-Equal 'validate-job rejects the broken fixture' 3 $result.ExitCode
Assert-Contains 'validate-job reports the missing path' "missing its 'path' attribute" $result.Output
Assert-Contains 'validate-job warns on the unknown role' 'unrecognized role' $result.Output
Assert-Contains 'validate-job warns on the non-boolean build' 'non-boolean build' $result.Output
Assert-Contains 'validate-job warns on the unused MergeSettings title' 'not used by composition' $result.Output
Assert-Contains 'validate-job warns on an ignored element' '<Parcel> under <MergeSettings> is ignored' $result.Output
Assert-Contains 'validate-job warns on duplicate groups' 'declared more than once' $result.Output
Assert-Contains 'validate-job warns on the legacy spelling' 'pre-release spelling' $result.Output
Assert-Contains 'validate-job rejects an inline WebDAV definition' "WebDAV ('http') action" $result.Output

# No <MergeSettings> at all is Automatic mode, not an omission.
$result = Invoke-Tool -Tool 'parse-job.py' -Arguments @('--json', (Join-Path $invalid 'no-destination.wacj'))
$json = $result.Output | ConvertFrom-Json
Assert-Equal 'parse-job reports Automatic mode' 'automatic' $json.mode
Assert-Equal 'parse-job reports no MergeSettings' $false $json.mergeSettings.present

$result = Invoke-Tool -Tool 'validate-job.py' -Arguments @((Join-Path $invalid 'no-destination.wacj'))
Assert-Equal 'validate-job rejects a composition with no destination' 3 $result.ExitCode
Assert-Contains 'validate-job names the missing destination' 'Missing <Destination' $result.Output
Assert-Contains 'validate-job warns when no member is the shell' 'No member declares role="shell"' $result.Output

# --- list-job-targets.py ----------------------------------------------------

$result = Invoke-Tool -Tool 'list-job-targets.py' -Arguments @('--json', $composition)
Assert-Equal 'list-job-targets .wacj exit code' 0 $result.ExitCode
$json = $result.Output | ConvertFrom-Json
Assert-Equal 'list-job-targets lists every member' 3 $json.Count

$result = Invoke-Tool -Tool 'list-job-targets.py' -Arguments @('--simple', '--enabled', $composition)
Assert-Equal 'list-job-targets --enabled exit code' 0 $result.ExitCode
Assert-Equal 'list-job-targets --enabled lists built members only' `
    '[BUILD] parcel-a.waj -> WebWorks Reverb 2.0 (composition target)' $result.Output.Trim()

# --- create-job.py + round trip ---------------------------------------------

$temp = Join-Path ([System.IO.Path]::GetTempPath()) ("wacj-tests-" + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temp | Out-Null

try {
    $result = Invoke-Tool -Tool 'create-job.py' -Arguments @('--template', '--composition')
    Assert-Equal 'create-job --template --composition exit code' 0 $result.ExitCode
    Set-Content -LiteralPath (Join-Path $temp 'template.json') -Value $result.Output -Encoding UTF8

    $result = Invoke-Tool -Tool 'create-job.py' `
        -Arguments @('--config', 'template.json', '--output', 'from-template.wacj', '-y') `
        -WorkingDirectory $temp
    Assert-Equal 'create-job generates from the template' 0 $result.ExitCode

    $result = Invoke-Tool -Tool 'validate-job.py' -Arguments @((Join-Path $temp 'from-template.wacj'))
    Assert-Equal 'the generated .wacj validates' 0 $result.ExitCode

    # discover="true" is Custom mode with "Also include newly published
    # parcels not listed above" checked.
    $template = (Invoke-Tool -Tool 'create-job.py' -Arguments @('--template', '--composition')).Output | ConvertFrom-Json
    $template.mergeSettings.discover = $true
    Set-Content -LiteralPath (Join-Path $temp 'include-new.json') `
        -Value ($template | ConvertTo-Json -Depth 10) -Encoding UTF8

    $result = Invoke-Tool -Tool 'create-job.py' `
        -Arguments @('--config', 'include-new.json', '--output', 'include-new.wacj', '-y') `
        -WorkingDirectory $temp
    Assert-Equal 'create-job generates the include-new variant' 0 $result.ExitCode
    Assert-Contains 'create-job emits discover="true"' 'discover="true"' `
        (Get-Content -LiteralPath (Join-Path $temp 'include-new.wacj') -Raw)

    $json = (Invoke-Tool -Tool 'parse-job.py' -Arguments @('--json', (Join-Path $temp 'include-new.wacj'))).Output | ConvertFrom-Json
    Assert-Equal 'parse-job reports the include-new mode' 'custom+include-new' $json.mode

    # Round trip: parse --config -> create-job -> parse --json must be identical
    # apart from the resolved member paths, which follow the file's location.
    $result = Invoke-Tool -Tool 'parse-job.py' -Arguments @('--config', $composition)
    Assert-Equal 'parse-job --config exit code' 0 $result.ExitCode
    Set-Content -LiteralPath (Join-Path $temp 'roundtrip.json') -Value $result.Output -Encoding UTF8

    $result = Invoke-Tool -Tool 'create-job.py' `
        -Arguments @('--config', 'roundtrip.json', '--output', 'roundtrip.wacj', '-y') `
        -WorkingDirectory $temp
    Assert-Equal 'create-job regenerates the composition' 0 $result.ExitCode

    $original = (Invoke-Tool -Tool 'parse-job.py' -Arguments @('--json', $composition)).Output | ConvertFrom-Json
    $rebuilt = (Invoke-Tool -Tool 'parse-job.py' -Arguments @('--json', (Join-Path $temp 'roundtrip.wacj'))).Output | ConvertFrom-Json

    Assert-Equal 'round trip keeps the name' $original.name $rebuilt.name
    Assert-Equal 'round trip keeps the composition-wide target' $original.outputTarget $rebuilt.outputTarget
    Assert-Equal 'round trip keeps the mode' $original.mode $rebuilt.mode
    Assert-Equal 'round trip keeps every member' $original.members.Count $rebuilt.members.Count
    Assert-Equal 'round trip keeps the member override' `
        $original.members[2].target $rebuilt.members[2].target
    Assert-Equal 'round trip keeps the build flag' `
        $original.members[1].build $rebuilt.members[1].build
    Assert-Equal 'round trip keeps the destination' `
        $original.destination.name $rebuilt.destination.name
    Assert-Equal 'round trip keeps the inline definition' `
        $original.destination.deploySettings[0].configuration.Value `
        $rebuilt.destination.deploySettings[0].configuration.Value
    Assert-Equal 'round trip migrates to the current spelling' $false $rebuilt.destination.legacySpelling

    # A composition config rejects the same defects the file grammar does.
    $badConfig = @'
{
  "kind": "composition",
  "name": "bad",
  "members": [ { "path": "", "role": "middle" } ],
  "destination": { "name": "" }
}
'@
    Set-Content -LiteralPath (Join-Path $temp 'bad.json') -Value $badConfig -Encoding UTF8
    $result = Invoke-Tool -Tool 'create-job.py' `
        -Arguments @('--config', 'bad.json', '--output', 'bad.wacj', '-y') `
        -WorkingDirectory $temp
    Assert-Equal 'create-job rejects an invalid composition config' 3 $result.ExitCode
    Assert-Contains 'create-job names the empty member path' 'Member 1 path cannot be empty' $result.Output
    Assert-Contains 'create-job names the invalid role' "role 'middle' is invalid" $result.Output
    Assert-Contains 'create-job names the empty destination' 'Destination name cannot be empty' $result.Output
}
finally {
    Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
}

# --- .waj regression spot-checks -------------------------------------------

$sampleJob = Join-Path $scriptDir 'sample.waj'

$result = Invoke-Tool -Tool 'parse-job.py' -Arguments @('--json', $sampleJob)
Assert-Equal 'parse-job .waj exit code' 0 $result.ExitCode
$json = $result.Output | ConvertFrom-Json
Assert-Equal 'parse-job .waj kind' 'job' $json.kind
Assert-Equal 'parse-job .waj target count' 2 $json.targets.Count

$result = Invoke-Tool -Tool 'validate-job.py' -Arguments @('-v', $sampleJob)
Assert-Equal 'validate-job .waj exit code' 0 $result.ExitCode

$result = Invoke-Tool -Tool 'validate-job.py' `
    -Arguments @('-v', (Join-Path $scriptDir 'sample-designer-stationery.waj'))
Assert-Equal 'validate-job project-as-stationery .waj exit code' 0 $result.ExitCode

$result = Invoke-Tool -Tool 'list-job-targets.py' -Arguments @('--simple', '--enabled', $sampleJob)
Assert-Equal 'list-job-targets .waj exit code' 0 $result.ExitCode
Assert-Equal 'list-job-targets .waj enabled target' '[BUILD] WebWorks Reverb 2.0' $result.Output.Trim()

# A composition job in a .waj file (and the reverse) is named, not mis-parsed.
$result = Invoke-Tool -Tool 'parse-job.py' -Arguments @((Join-Path $federation 'parcel-b.wep'))
Assert-Equal 'parse-job rejects a non-job extension' 1 $result.ExitCode

Write-Output ''
Write-Output "Results: $($script:Pass) passed, $($script:Fail) failed"

if ($script:Fail -eq 0) { exit 0 } else { exit 1 }
