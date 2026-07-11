# AutoMap Installation Detection

## Overview

This document describes how WebWorks ePublisher AutoMap installations are detected on Windows. The skill's implementation is `scripts/Find-AutomapInstallation.ps1` (Windows PowerShell 5.1+); `Invoke-Automap.ps1` calls it automatically when no override is given.

```bash
powershell -ExecutionPolicy Bypass -File "<skill-dir>/scripts/Find-AutomapInstallation.ps1" -ShowBuild -Verbose
```

| Option | Description |
|--------|-------------|
| `-Version <ver>` | Detect a specific installed version (e.g. `2024.1`) instead of the latest |
| `-ShowBuild` | Also print `Build: <n>` (registry-detected installs only) |
| `-Verbose` | Detection diagnostics on the verbose stream |

Exit codes: `0` found (path printed to stdout), `1` not found.

## Resolution Order (Wrapper)

`Invoke-Automap.ps1` resolves the executable in this order:

1. `-ExePath <path>` wrapper option
2. `AUTOMAP_EXE_PATH` environment variable
3. `Find-AutomapInstallation.ps1` (registry, then filesystem — below)

If an explicitly-set override points to a missing file, the wrapper fails with exit 3 rather than silently falling through — an override is a statement of intent.

## Registry-Based Detection (Preferred)

### Registry Locations

**64-bit Installation:**
```
HKEY_LOCAL_MACHINE\SOFTWARE\WebWorks\ePublisher AutoMap\[VERSION]
```

**32-bit Installation:**
```
HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\WebWorks\ePublisher AutoMap\[VERSION]
```

### Registry Values

Each version subkey (e.g. `2026.1`) carries:

- **`ExePath`** (REG_SZ) — full path to the AutoMap **Administrator** executable:
  ```
  C:\Program Files\WebWorks\ePublisher\2026.1\ePublisher AutoMap\WebWorks.Automap.Administrator.exe
  ```
- **`Version`** (REG_SZ) — full version string, e.g. `26.1.4712`; the build number is the last fragment.

### Algorithm

1. Enumerate version subkeys in **both** hives (`Get-ChildItem`/`Get-ItemProperty` — native and fast, no `reg.exe` spawning).
2. Filter to `-Version` if requested.
3. Sort candidates by version **descending**; on a version tie, prefer the 64-bit hive.
4. Normalize each candidate's `ExePath` to the CLI executable (below) and return the first whose CLI executable exists on disk.

Detection completes in well under a second, so no caching layer is needed — the historical ~8s overhead was the cost of spawning `reg.exe` from bash and text-parsing its output.

## Executable Path Normalization

The AutoMap installation includes two executables:

| Filename | Purpose | Returned by Detection |
|----------|---------|----------------------|
| `WebWorks.Automap.Administrator.exe` | UI for interactive job management | No (intermediate) |
| `WebWorks.Automap.exe` | CLI for automation and scripting | **Yes** |

Both detection methods locate the Administrator executable location, then normalize: replace `.Administrator.exe` with `.exe` and validate the CLI executable exists.

### Naming Convention Quirk

Note the capitalization difference:
- **Product name:** AutoMap (capital M)
- **Directory name:** ePublisher AutoMap (capital M)
- **Executable names:** Automap (lowercase m)

```
C:\Program Files\WebWorks\ePublisher\2026.1\ePublisher AutoMap\WebWorks.Automap.exe
                                                ^^^^^^^                 ^^^^^^^
                                               capital M              lowercase m
```

## Filesystem Fallback

Used only when the registry yields no usable candidate (corrupted registry, permissions issues):

1. `C:\Program Files\WebWorks\ePublisher\[version]\ePublisher AutoMap\WebWorks.Automap.exe`
2. `C:\Program Files (x86)\WebWorks\ePublisher\[version]\ePublisher AutoMap\WebWorks.Automap.exe`

Version directories matching `<digits>.<digits>` are sorted descending; the first existing CLI executable wins. Filesystem detection cannot provide a build number.

## Error Handling

**Registry key not found**
- Cause: AutoMap not installed or installation corrupted
- Handled: falls back to standard filesystem paths

**ExePath exists but file not found**
- Cause: AutoMap was uninstalled but registry not cleaned
- Handled: candidate skipped; next version / filesystem tried

**Multiple versions installed**
- Cause: side-by-side installations
- Handled: highest version wins (64-bit preferred on tie); use `-Version` to pin

**Nothing found**
- `[ERROR] AutoMap installation not found` on stderr, exit 1
- Resolution: install ePublisher AutoMap, or set `AUTOMAP_EXE_PATH` / pass `-ExePath` explicitly

## Testing Scenarios

- [ ] Fresh installation (64-bit)
- [ ] Fresh installation (32-bit on 64-bit Windows)
- [ ] Multiple versions installed (across both hives)
- [ ] AutoMap uninstalled but registry entry remains
- [ ] No AutoMap installed
- [ ] `-Version` pinning to a non-latest install
- [ ] `AUTOMAP_EXE_PATH` pointing at a development build

## Version History

- **2.0** (2026-07-11): PowerShell implementation (`Find-AutomapInstallation.ps1`); merged-hive candidate ordering; caching removed as unnecessary
- **1.0** (2025-01-27): Initial documentation of registry-based detection method
