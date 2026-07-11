# AutoMap CLI Reference

Complete reference for WebWorks ePublisher AutoMap command-line interface options and execution patterns.

The execution interface is the wrapper script `Invoke-Automap.ps1`. **Every AutoMap flag is pass-through**: the wrapper never translates or renames native options, so this document is a reference for the *native* CLI surface plus the wrapper's own (PowerShell-style) options.

## Table of Contents

- [Basic Command Pattern](#basic-command-pattern)
- [Wrapper Options](#wrapper-options)
- [Safe Defaults](#safe-defaults)
- [Environment Variables](#environment-variables)
- [Native Command Options](#native-command-options)
- [Example Commands](#example-commands)
- [Execution Guidelines](#execution-guidelines)
- [Output Monitoring](#output-monitoring)
- [Common Errors](#common-errors)
- [Best Practices](#best-practices)

## Basic Command Pattern

```bash
powershell -ExecutionPolicy Bypass -File "<skill-dir>/scripts/Invoke-Automap.ps1" [wrapper options] -- <automap options> <project-file>
```

**Components:**
- `[wrapper options]`: PowerShell-style options for the wrapper itself (`-NoDefaults`, `-AllTargets`, `-ExePath <path>`, `-Help`)
- `--`: separator — everything after it is forwarded to `WebWorks.Automap.exe` verbatim. (Technically optional: the first token that is not a wrapper option also ends wrapper parsing. Always include it anyway; it makes the boundary explicit.)
- `<automap options>`: native AutoMap CLI flags (see [Native Command Options](#native-command-options))
- `<project-file>`: path to `.wep`, `.wrp`, `.waj`, or `.wxsp` project/job file

## Wrapper Options

| Option | Description |
|--------|-------------|
| `-NoDefaults` | Verbatim native CLI behavior: no injected flags, no explicit-target requirement. Use for production/CI builds and for AutoMap versions older than 2025.1. |
| `-AllTargets` | Waive only the explicit-target requirement. For `.waj` files, builds the job's `build="True"` set; for project files, builds every target. Safe defaults still apply. |
| `-ExePath <path>` | AutoMap executable to run. Overrides `AUTOMAP_EXE_PATH` and auto-detection. |
| `-Help` | Show usage. |

These four options are the wrapper's entire vocabulary. Everything else belongs after `--` and must be a native AutoMap flag.

## Safe Defaults

Unless `-NoDefaults` is given, the wrapper injects these **native** flags and reports them on an `[INFO]` line:

| Injected flag | Skipped when | Purpose |
|---------------|--------------|---------|
| `-n` (nodeploy) | `-n`/`--nodeploy` already present, or deploy intent signaled: `-d`/`--deployfolder`, `-l`/`--cleandeploy`, `--deploysettings`, `--deployscope` | Prevents accidental deployment during development |
| `--skip-reports` | already present | Faster builds *(2025.1+; use `-NoDefaults` with older versions)* |

**Explicit-target requirement:** unless `-NoDefaults` or `-AllTargets` is given, the arguments must include `-t` or `--target`. Otherwise the wrapper exits 2 and lists the file's available targets (for `.waj`, annotating which are `build="True"` enabled). This prevents a job file's full enabled set — or a project's every target — from building by accident.

**Not a default:** `-c` (clean build). Incremental is the default; pass `-c` explicitly when build state is suspect.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `AUTOMAP_EXE_PATH` | Path to AutoMap CLI executable. Bypasses installation detection when set. The `-ExePath` wrapper option takes precedence over it. |

### Development Builds

Point to a debug build for testing:

```bash
# bash syntax
export AUTOMAP_EXE_PATH="C:/Repo/.../Automap/bin/Debug/WebWorks.Automap.exe"
```

```powershell
# PowerShell syntax
$env:AUTOMAP_EXE_PATH = 'C:\Repo\...\Automap\bin\Debug\WebWorks.Automap.exe'
```

Or per-invocation, without touching the environment:

```bash
powershell -ExecutionPolicy Bypass -File "<skill-dir>/scripts/Invoke-Automap.ps1" -ExePath "C:/dev/WebWorks.Automap.exe" -- -t "Target" project.wep
```

Auto-detection (registry, then filesystem) completes in well under a second, so there is no need to cache the detected path for batch builds.

## Native Command Options

All options below belong after the `--` separator and are forwarded to `WebWorks.Automap.exe` unchanged, in any form the CLI itself accepts (`-t "Name"`, `--target=A,B`, `--stagingdir <dir>`, `--stagingdir=<dir>`, ...).

### Core Build Options

**`-c, --clean`**
- **Purpose**: Clean build (remove cached files before generation)
- **Use When**: Ensuring fresh build after major changes, or when incremental state is suspect
- **Impact**: Longer build time but guaranteed clean state
- **Example**: `-c -t "Target" project.wep`

**`-n, --nodeploy`** *(injected by default — see [Safe Defaults](#safe-defaults))*
- **Purpose**: Do not copy output to deployment location
- **Use When**: Testing builds or using custom deployment
- **Impact**: Output remains in the project's Output folder only. For a Stationery-based job file (`.waj`), that folder is inside the Staging Folder — `<stagingDir>/<JobName>/Output/<target>/`, **not** next to the `.waj`. See [Staging Folder (Job Files)](#staging-folder-job-files).

**`-l, --cleandeploy`**
- **Purpose**: Clean deployment location before copying output
- **Use When**: Ensuring deployment folder has only latest files
- **Impact**: Removes old files from previous builds. Signals deploy intent — the wrapper will not inject `-n`.

### Target Selection

**`-t <TargetName>`** or **`--target=<TargetName1>,<TargetName2>`**
- **Purpose**: Build specific target(s) only
- **Use When**: Working on specific output format(s) rather than all targets
- **Impact**: Faster builds, generates only specified target(s)
- **Syntax**:
  - Single target: `-t "WebWorks Reverb 2.0"`
  - Multiple targets: `--target="WebWorks Reverb 2.0,PDF - XSL-FO"`
- **Note**: Target names must exactly match `TargetName` in project file (case-sensitive). With job files, `-t` overrides the `build="True"` set.

### Deployment Control

**`-d, --deployfolder "[Path]"`**
- **Purpose**: Override default deployment destination
- **Use When**: Deploying to custom location (web server, network share)
- **Impact**: Output copied to specified path instead of project default. Signals deploy intent — the wrapper will not inject `-n`.
- **Note**: Must have write permissions to deployment path

**`--deployscope <everything|groups|shell>`** *(2026.1+)*
- **Purpose**: Override the deploy scope declared on the target
- **Use When**: Layer-scoped deployments (e.g., publishing only group parcels, or only the shell)

**`--deploysettings <file>`** *(2026.1+)*
- **Purpose**: XML file of inline deploy-target definitions (deploy.prefs entry schema, file/s3 actions only) overlaying deploy.prefs by name
- **Use When**: CI environments where deploy.prefs is not configured on the machine

### Staging Folder (Job Files)

When AutoMap builds a Stationery-based job file (`.waj`), it stages a temporary Express project (`.wrp`) under the **Staging Folder** and builds there. The output lands at `<stagingDir>/<JobName>/Output/<target>/` — **not** next to the `.waj`. This is the most common reason "I can't find my output." (Project files — `.wep`/`.wrp` — build into their own Output folder.)

- **Default Staging Folder**: `%USERPROFILE%\Documents\WebWorks ePublisher AutoMap\Staging` (an AutoMap preference).
- **Job/target naming**: `<JobName>` is the `<Job name="...">` attribute; `<target>` is the target's `name`.

**`-s <dir>`, `--stagingdir <dir>`**
- **Purpose**: Override the staging directory for this build
- **Use When**: Directing job-file output to a known location, or isolating builds
- **Impact**: Staged project and output go under `<dir>/<JobName>/...`. The wrapper's post-build log scan follows this value.
- **Note**: See the job file guide's [Output Location](./job-file-guide.md#output-location-staging-folder).

### Project Maintenance

**`-u, --update`**
- **Purpose**: Update conditions, styles, variables, references and more before building

**`-j, --justupdate`**
- **Purpose**: Just update and save the project file (no generation)

### Performance Options

**`--skip-reports`** *(2025.1+; injected by default — see [Safe Defaults](#safe-defaults))*
- **Purpose**: Skip report generation pipelines during build
- **Use When**: CI/CD builds, agentic workflows, or iterative development where reports not needed
- **Impact**: Faster builds, reduced file system output
- **Trade-off**: No build reports generated (errors and warnings still recorded in `generate.log`)

### Notification

**`-f, --nonotify`**
- **Purpose**: Do not send the job-result notification (job files with notification preferences)

### Information

**`--version, -v`** *(2025.1, build 4652+)*
- **Purpose**: Display the product version and exit
- **Output format**: `Major.Minor.Build` (e.g., `2025.1.4652`)
- **Use When**: Determining the build number for golden output naming, verifying which build is installed, scripting build-specific workflows
- **Example**: `"path/to/WebWorks.Automap.exe" --version`
- **Note**: Available in all ePublisher products (AutoMap, Designer, Express). Not available in builds prior to 4652.

## Output Behavior

The wrapper suppresses AutoMap's streaming stdout (banner, per-pipeline progress) but **lets stderr pass through**, so genuine build errors surface inline. After a successful build (exit 0) it scans each `Logs/<target>/generate.log` and prints a per-target `N warning(s), M error(s)` summary (see [Post-Build Log Scan](../SKILL.md#post-build-log-scan)). This is optimized for AI-assisted workflows where progress output costs tokens without informing decisions.

**Default output:**
```
[INFO] Applied default flags: -n --skip-reports (pass -NoDefaults for verbatim CLI behavior)
[SUCCESS] Build completed in 45s
[WARNING] 3 warning(s), 0 error(s) in Logs/Reverb2/generate.log
```

There is no verbose/streaming wrapper mode. To investigate a reported count or failure, **read `generate.log`** (below). To watch live progress interactively — a human need — run `WebWorks.Automap.exe` directly.

## Example Commands

### Basic Builds

**Build single target (defaults applied):**
```bash
powershell -ExecutionPolicy Bypass -File "<skill-dir>/scripts/Invoke-Automap.ps1" -- -t "WebWorks Reverb 2.0" project.wep
```

**Build multiple targets:**
```bash
powershell -ExecutionPolicy Bypass -File "<skill-dir>/scripts/Invoke-Automap.ps1" -- --target="WebWorks Reverb 2.0,PDF - XSL-FO" project.wep
```

**Build a job file's enabled target set:**
```bash
powershell -ExecutionPolicy Bypass -File "<skill-dir>/scripts/Invoke-Automap.ps1" -AllTargets -- job.waj
```

### Deployment Builds

**Deploy to the target's configured location (verbatim native semantics):**
```bash
powershell -ExecutionPolicy Bypass -File "<skill-dir>/scripts/Invoke-Automap.ps1" -NoDefaults -- -c -t "WebWorks Reverb 2.0" project.wep
```

**Deploy to a specific folder (deploy intent suppresses the `-n` default):**
```bash
powershell -ExecutionPolicy Bypass -File "<skill-dir>/scripts/Invoke-Automap.ps1" -- -t "WebWorks Reverb 2.0" -d "C:\TestOutput" project.wep
```

## Execution Guidelines

### Path Requirements

1. **Use absolute or relative paths** for project files
2. **Quote paths containing spaces** - Most Windows paths have spaces
3. **Use the full path to the wrapper script** - it lives in the skill directory, not the project directory

### Timeout Configuration

Set appropriate timeout based on project size when using the Bash tool:

| Project Size | Recommended Timeout |
|-------------|---------------------|
| Small (< 50 pages) | 2 minutes (default) |
| Medium (50-200 pages) | 5 minutes (300000ms) |
| Large (200-500 pages) | 10 minutes (600000ms) |
| Very Large (> 500 pages) | 15 minutes (900000ms) |

### Exit Code Handling

The wrapper provides consistent exit codes:

| Exit Code | Meaning |
|-----------|---------|
| 0 | Build succeeded |
| 1 | Build failed |
| 2 | Invalid arguments / no target specified |
| 3 | AutoMap not installed |
| 4 | Project file not found |

**Check build status:**
```bash
if powershell -ExecutionPolicy Bypass -File "<skill-dir>/scripts/Invoke-Automap.ps1" -- -t "Target" project.wep; then
    echo "Build succeeded"
else
    echo "Build failed with exit code: $?"
fi
```

## Output Monitoring

**Errors do not require any flag.** The wrapper lets AutoMap's stderr pass through; after a successful build it scans each `generate.log` and prints per-target `[WARN]`/`[ERROR]` counts; a non-zero exit is reported directly.

### Reading `generate.log`

When the scan reports a non-zero warning/error count, or a build exits non-zero, read the per-line detail straight from the log:

```bash
grep -nE '\[ERROR\]|\[WARN\]' "<project-or-staging>/Logs/<target>/generate.log"
```

- **Project files** (`.wep`/`.wrp`): the log is at `<project-dir>/Logs/<target>/generate.log`.
- **Job files** (`.waj`): the log is under the staging folder — `<stagingDir>/<JobName>/Logs/<target>/generate.log` (see [Staging Folder (Job Files)](#staging-folder-job-files)).

The patterns below are the tokens used in `generate.log` and AutoMap's console output.

### Error Patterns

- `"[ERROR]"` - Log-recorded errors (counted by the post-build scan)
- `"Error:"` - Critical errors
- `"Failed to"` - Operation failures
- `"Unable to"` - Capability errors
- `"Exception"` - Runtime exceptions

### Warning Patterns

- `"[WARN]"` - Log-recorded warnings (counted by the post-build scan)
- `"Warning:"` - Non-critical issues
- `"Could not find"` - Missing optional resources
- `"Deprecated"` - Outdated configurations
- `"Skipping"` - Excluded content

## Common Errors

### Error 1: Project File Not Found

**Symptom:**
```
[ERROR] Project file not found: C:\projects\my-proj\my-proj.wep
```

**Solutions:**
1. Verify file exists and check for typos in filename
2. Check file permissions
3. Use absolute path

### Error 2: Source Documents Missing

**Symptom:**
```
Error: Source document not found: 'Source\getting-started.md'
```

**Solutions:**
1. Verify source file exists
2. Check path in project file `<Document Path="..."/>`
3. Update project file if source moved

### Error 3: No Target Specified (exit 2)

**Symptom:**
```
[ERROR] No target specified. Pass -t "<name>" (or --target="Name1,Name2") to choose target(s).
[ERROR] Available targets in project.wep:
[ERROR]   - WebWorks Reverb 2.0
```

**Solutions:**
1. Pass `-t "<name>"` with a name from the listed targets
2. To build the file's full declared set intentionally, pass the wrapper option `-AllTargets`
3. For verbatim native CLI behavior, pass `-NoDefaults`

### Error 4: Unknown Option

**Symptom:** AutoMap reports an unknown/invalid option.

**Causes:**
- A retired wrapper-only flag was used (`--deploy`, `--no-clean`, `--with-reports`, `--all-targets`, `--verbose` do not exist natively)
- The installed AutoMap predates the flag (`--skip-reports` requires 2025.1+ — including when injected by the wrapper's defaults)

**Solutions:**
1. Use only native flags after `--` (this document's [Native Command Options](#native-command-options))
2. With pre-2025.1 versions, pass `-NoDefaults`

### Error 5: Target Not Found

**Symptom:**
```
Error: Target 'Invalid Target Name' not found in project
```

**Solutions:**
1. List available targets: use the epublisher skill's `parse-targets.py`, or trigger the wrapper's target listing by omitting `-t`
2. Use exact target name from project file (case-sensitive; check for extra spaces)

### Error 6: Permission / Disk Errors

**Symptom:** `Access denied writing to 'C:\Output'`, `Out of disk space`

**Solutions:**
1. Check folder permissions and available disk space
2. Close files in output folder (files in use by another process)
3. Choose a different deployment location

## Best Practices

### 1. Development Builds: Rely on the Defaults

```bash
powershell -ExecutionPolicy Bypass -File "<skill-dir>/scripts/Invoke-Automap.ps1" -- -t "WebWorks Reverb 2.0" project.wep
```

No deployment, no reports, explicit target — nothing to remember, nothing to undo.

### 2. Production Builds: `-NoDefaults`

```bash
powershell -ExecutionPolicy Bypass -File "<skill-dir>/scripts/Invoke-Automap.ps1" -NoDefaults -- -c -t "WebWorks Reverb 2.0" project.wep
```

Exact native CLI semantics: deploys per the target's configuration, generates reports.

### 3. Build Specific Targets When Testing

Save time by building only the target(s) you're working on with `-t`.

### 4. Read `generate.log` to Debug Build Issues

```bash
grep -nE '\[ERROR\]|\[WARN\]' "<project-or-staging>/Logs/WebWorks Reverb 2.0/generate.log"
```

### 5. Capture Build Output

```bash
powershell -ExecutionPolicy Bypass -File "<skill-dir>/scripts/Invoke-Automap.ps1" -- -t "Target" project.wep 2>&1 | tee build.log
```

### 6. Clean Builds When State Is Suspect

Incremental is the default. Pass `-c` explicitly after format changes, upgrades, or unexplained output staleness.

## Script Reference

The wrapper is the primary execution interface:

| Script | Purpose |
|--------|---------|
| **Invoke-Automap.ps1** | Execute builds (primary interface) |
| **Find-AutomapInstallation.ps1** | Verify installation, debug detection |
| **parse-targets.py** *(epublisher skill)* | List valid target names for `-t` parameter |

Use `Find-AutomapInstallation.ps1` only for:
- Verifying AutoMap is installed (`-ShowBuild` adds the build number)
- Debugging installation detection issues (`-Verbose`)

## Related Documentation

- [installation-detection.md](./installation-detection.md) - Finding AutoMap executable
- [../SKILL.md](../SKILL.md) - Main skill documentation

## Adding New CLI Options

New native AutoMap options need **documentation only** — the wrapper forwards unknown flags verbatim, so no script change is required:

1. **cli-reference.md** - Add to [Native Command Options](#native-command-options) with examples
2. **SKILL.md** - Add to the frequently-used table only if it earns the space

The only script-relevant cases are flags that interact with the wrapper's defaults (deploy-intent detection, `-n`/`--skip-reports` duplication checks) — update `Invoke-Automap.ps1` and its tests when AutoMap grows a new deployment-related flag.

---

**Version**: 3.5.0
**Last Updated**: 2026-07-11
**Target**: ePublisher 2024.1+ AutoMap CLI (--skip-reports requires 2025.1+, --version requires 2025.1 build 4652+)
