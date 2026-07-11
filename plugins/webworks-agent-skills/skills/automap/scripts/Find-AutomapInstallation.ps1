<#
.SYNOPSIS
Detects the WebWorks ePublisher AutoMap CLI installation on Windows.

.DESCRIPTION
Searches the Windows registry (64-bit and 32-bit hives), then falls back to
well-known filesystem locations. Both methods record the AutoMap
Administrator executable; the result is normalized to the CLI executable
(WebWorks.Automap.exe) for headless automation.

When multiple versions are installed, the highest version wins; on a version
tie the 64-bit installation is preferred.

Requires Windows PowerShell 5.1 or later. Invoke with:
  powershell -ExecutionPolicy Bypass -File Find-AutomapInstallation.ps1

.PARAMETER Version
Detect a specific installed version (e.g. 2024.1) instead of the latest.

.PARAMETER ShowBuild
Additionally print the build number (from the registry Version value) on a
second line: "Build: 4712". Filesystem-detected installations have no build
number and print nothing extra.

.OUTPUTS
On success, prints the full Windows path to WebWorks.Automap.exe.

.NOTES
Exit codes:
  0 - AutoMap CLI found
  1 - AutoMap not found (or invalid arguments)

Use -Verbose for detection diagnostics (written to the verbose stream).
#>
[CmdletBinding()]
param(
    [string]$Version,
    [switch]$ShowBuild
)

Set-StrictMode -Version 2.0

# Registry hives, in tie-break preference order (64-bit first).
$registryHives = @(
    'HKLM:\SOFTWARE\WebWorks\ePublisher AutoMap',
    'HKLM:\SOFTWARE\WOW6432Node\WebWorks\ePublisher AutoMap'
)

# Filesystem fallback roots, in tie-break preference order.
$fallbackRoots = @(
    'C:\Program Files\WebWorks\ePublisher',
    'C:\Program Files (x86)\WebWorks\ePublisher'
)

function ConvertTo-SortableVersion {
    param([string]$Name)
    # Version directory / registry key names look like "2026.1".
    try { return [version]$Name } catch { return [version]'0.0' }
}

function ConvertTo-CliPath {
    param([string]$ExePath)
    # Registry ExePath records the Administrator executable; the CLI
    # executable lives beside it without the ".Administrator" segment.
    if ($ExePath -match '\.Administrator\.exe$') {
        return $ExePath -replace '\.Administrator\.exe$', '.exe'
    }
    return $ExePath
}

$candidates = @()

# --- Registry detection ---
for ($hiveIndex = 0; $hiveIndex -lt $registryHives.Count; $hiveIndex++) {
    $hive = $registryHives[$hiveIndex]
    Write-Verbose "Querying registry path: $hive"

    if (-not (Test-Path -LiteralPath $hive)) {
        Write-Verbose "Registry path not present: $hive"
        continue
    }

    foreach ($key in Get-ChildItem -LiteralPath $hive) {
        $keyVersion = $key.PSChildName
        if ($Version -and ($keyVersion -ne $Version)) { continue }

        $props = Get-ItemProperty -LiteralPath $key.PSPath
        $exePath = $null
        $buildNumber = $null
        if ($props.PSObject.Properties['ExePath']) { $exePath = [string]$props.ExePath }
        if ($props.PSObject.Properties['Version']) {
            # Version value looks like "26.1.4712"; build is the last fragment.
            $fragments = ([string]$props.Version).Split('.')
            $buildNumber = $fragments[$fragments.Count - 1]
        }
        if (-not $exePath) {
            Write-Verbose "No ExePath value under $($key.PSPath); skipping"
            continue
        }

        Write-Verbose "Found $keyVersion -> $exePath"
        $candidates += [pscustomobject]@{
            SortKey      = ConvertTo-SortableVersion $keyVersion
            HivePriority = $hiveIndex
            CliPath      = ConvertTo-CliPath $exePath
            Build        = $buildNumber
        }
    }
}

# --- Filesystem fallback (only when the registry yields nothing usable) ---
if ($candidates.Count -eq 0) {
    Write-Verbose 'Registry detection found no candidates; trying filesystem...'

    for ($rootIndex = 0; $rootIndex -lt $fallbackRoots.Count; $rootIndex++) {
        $root = $fallbackRoots[$rootIndex]
        Write-Verbose "Checking: $root"

        if (-not (Test-Path -LiteralPath $root)) { continue }

        foreach ($dir in Get-ChildItem -LiteralPath $root -Directory) {
            if ($dir.Name -notmatch '^[0-9]+\.[0-9]+') { continue }
            if ($Version -and ($dir.Name -ne $Version)) { continue }

            $cliPath = Join-Path $dir.FullName 'ePublisher AutoMap\WebWorks.Automap.exe'
            Write-Verbose "Found $($dir.Name) -> $cliPath"
            $candidates += [pscustomobject]@{
                SortKey      = ConvertTo-SortableVersion $dir.Name
                HivePriority = $rootIndex
                CliPath      = $cliPath
                Build        = $null
            }
        }
    }
}

# Highest version first; 64-bit preferred on a version tie. Validate each
# candidate's CLI executable and return the first that exists.
$ordered = $candidates | Sort-Object -Property @{Expression = 'SortKey'; Descending = $true },
                                               @{Expression = 'HivePriority'; Descending = $false }
foreach ($candidate in $ordered) {
    if (Test-Path -LiteralPath $candidate.CliPath -PathType Leaf) {
        Write-Output $candidate.CliPath
        if ($ShowBuild -and $candidate.Build) {
            Write-Output "Build: $($candidate.Build)"
        }
        exit 0
    }
    Write-Verbose "CLI executable does not exist: $($candidate.CliPath)"
}

[Console]::Error.WriteLine('[ERROR] AutoMap installation not found')
exit 1
