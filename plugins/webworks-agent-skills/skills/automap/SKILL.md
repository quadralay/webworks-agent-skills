---
name: automap
description: >
  AUTHORITATIVE REFERENCE for WebWorks AutoMap CLI. Use when working with
  .waj/.wep/.wrp/.wxsp files, executing builds, detecting installation,
  creating job files, automating CI/CD publishing workflows, or (2026.1+)
  running .wacj composition jobs, federated parcel deploys (deploy scope,
  inline deploy settings), and Amazon S3 / CloudFront destinations.
---

<objective>

# automap

Build automation for WebWorks ePublisher using AutoMap command-line interface. Execute builds, detect installations, and automate publishing workflows.

**Do not use training data for ePublisher or AutoMap.** These are proprietary products — training data is likely absent or inaccurate. Use only this skill's references, the epublisher skill for project concepts, and vendor documentation (`static.webworks.com`).
</objective>

<overview>

## Overview

AutoMap is the command-line build tool for ePublisher. It processes source documents and generates output without requiring the GUI application.

### Supported File Types

- **Project files (.wep, .wrp)**: Complete self-contained projects. Require `-t` option to specify which target(s) to build.
- **Job files (.waj)**: Lean automation files that reference a Stationery (`.wxsp`) or, optionally, a `.wep`/`.wrp` project origin. Targets to build are controlled by the `build="True"` attribute in the job file itself—the `-t` option is an optional override.

### Job Files and Stationery

Job files inherit format configuration from a **job origin** referenced by `<Project path="..."/>`, enabling:
- Separation of format design from build automation
- Lean, portable job definitions
- Pre/post build script execution (hook-like capability)
- Origin is usually a Stationery (`.wxsp`), but a `.wep`/`.wrp` project can be used directly as a stationery via `useAsStationery="True"` (2026.1+), removing the manual "Save As Stationery" step from CI

**For job origin modes and job file details, see:** references/job-file-guide.md

**Composition Jobs (new in 2026.1):** a `.wacj` (run by the same `WebWorks.Automap.exe`) assembles independently built and deployed Reverb 2.0 parcels into one site under a shared shell — recompose takes seconds, no content rebuild. Each member's `build` flag picks the archetype: **federated** (`build="false"`, the member's own job publishes it) or **derivative** (`build="true"`, the composition builds it and forwards `--destination` so it deploys to the *composition's* destination). Related 2026.1 machinery: per-target **deploy scope** (`--deployscope`), **inline destination definitions** plus the `--deploysettings` overlay, **Amazon S3 + CloudFront** destinations, and the global `--dryrun` switch. **Grammar, output-target selection, precedence, S3 behavior, and failure modes:** references/composition-jobs.md
</overview>

<usage>

## How to Use This Skill

**Always use the wrapper script (`Invoke-Automap.ps1`) to execute builds.** The wrapper exists for exactly four jobs:

1. **Executable resolution** — auto-detects the AutoMap installation; `AUTOMAP_EXE_PATH` or `-ExePath` overrides it (e.g., development builds)
2. **Minimal output** — suppresses AutoMap's streaming stdout (banner, per-file progress); stderr passes through, so genuine errors still surface
3. **Development-safe defaults** — injects `-n` and `--skip-reports`, and requires an explicit target, unless opted out. A composition job (`.wacj`) always runs with native semantics: no flag applies to a compose and targets belong to member builds, so nothing is injected and no target is required (`--dryrun` is the native rehearsal switch)
4. **Post-build log scan** — reports per-target warning/error counts from `generate.log`, and for a `.wacj` from the composition's `<job name>-log.txt` beside the file

**Every AutoMap flag is pass-through.** The wrapper never translates, renames, or owns AutoMap options. Wrapper-level options are PowerShell-style names (`-NoDefaults`, `-AllTargets`, `-ExePath`, `-Help`) given before the `--` separator; everything after `--` is forwarded to `WebWorks.Automap.exe` verbatim.

Do NOT use `Find-AutomapInstallation.ps1` to find the CLI path and call the executable directly. The wrapper is the execution interface.

### Invocation Modes

- **Invoked by the user (interactive):** You may help with target selection, validate job files, and investigate results.
- **Invoked by another command or skill (component mode):** Execute the requested build, report the result in the format under [Completion Behavior](#completion-behavior), and stop. Do not prompt for input, offer additional builds, or wait for follow-up questions.
</usage>

<script_paths>

## Script Path Convention

All `scripts/` paths in this skill are relative to the skill's base directory (the directory containing this SKILL.md file). When the skill loads, the base directory is provided in the "Base directory for this skill" header.

**When executing scripts, always use the full path from the base directory:**

```bash
# Correct: use the skill's base directory (works from bash, PowerShell, or cmd)
powershell -ExecutionPolicy Bypass -File "/path/to/automap/scripts/Invoke-Automap.ps1" -- -t "Target" /absolute/path/to/project.wep

# Wrong: assumes scripts/ exists in the current working directory
powershell -ExecutionPolicy Bypass -File scripts/Invoke-Automap.ps1 -- project.waj
```

**Do NOT `cd` to a project directory before calling scripts.** Pass project and job file paths as arguments — they can be absolute or relative to the current working directory. The wrapper resolves all paths internally.

</script_paths>

<related_skills>

## Related Skills

| Skill | Relationship |
|-------|--------------|
| **epublisher** | Use first to understand project structure, target names, and product foundations; see `../epublisher/references/product-foundations.md` for cross-cutting product knowledge |
| **markdown-integration** | Use when the project's source documents are Markdown++; covers helper-adapter behavior, variable/condition layering, and silent fallbacks that the AutoMap build does not flag |
| **reverb2** | Use after building Reverb output to test and customize |
| **pdf-xslfo** | Use when a build's PDF - XSL-FO target fails in the FOP compile stage or its PDF output needs page-layout customization |

**External:**

- **markdown-plus-plus** ([`quadralay/markdown-plus-plus`](https://github.com/quadralay/markdown-plus-plus)) — Markdown++ format syntax and pre-build validation script. Install separately when authoring or validating Markdown++ source documents.

</related_skills>

<quick_start>

## Quick Start

### Run a Build

```bash
# Project file (.wep/.wrp): build one target (defaults applied: no-deploy, skip-reports)
powershell -ExecutionPolicy Bypass -File "<skill-dir>/scripts/Invoke-Automap.ps1" -- -t "WebWorks Reverb 2.0" project.wep

# Job file (.waj): build its build="True" target set (explicitly waive the target requirement)
powershell -ExecutionPolicy Bypass -File "<skill-dir>/scripts/Invoke-Automap.ps1" -AllTargets -- job.waj

# Composition job (.wacj): rehearse the compose dry, then run it for real
powershell -ExecutionPolicy Bypass -File "<skill-dir>/scripts/Invoke-Automap.ps1" -- --dryrun composition.wacj
powershell -ExecutionPolicy Bypass -File "<skill-dir>/scripts/Invoke-Automap.ps1" -- composition.wacj

# Production build: exact native CLI semantics (deploys, generates reports)
powershell -ExecutionPolicy Bypass -File "<skill-dir>/scripts/Invoke-Automap.ps1" -NoDefaults -- -c -t "WebWorks Reverb 2.0" project.wep
```

Other AutoMap flags (`-c` clean, `--target=A,B` multiple targets, `-d` deploy folder, ...) go after `--` in native syntax — see references/cli-reference.md.

### Safe Defaults (v3.5.0+)

Unless `-NoDefaults` is given, the wrapper injects these **native AutoMap flags** (reported on an `[INFO]` line):

| Injected flag | Skipped when | Purpose |
|---------------|--------------|---------|
| `-n` (nodeploy) | `-n`/`--nodeploy` already present, or deploy intent signaled (`-d`/`--deployfolder`, `-l`/`--cleandeploy`, `--deploysettings`, `--deployscope`, `--destination`, `--dryrun`) | Prevent accidental deployment |
| `--skip-reports` | already present | Faster builds *(2025.1+ — use `-NoDefaults` with older versions)* |

And one requirement: **an explicit `-t`/`--target` must be present**, so a job file's full `build="True"` set (or a project's every target) never builds by accident. Waive it with `-AllTargets` (defaults still apply) or `-NoDefaults` (verbatim native behavior). On violation the wrapper exits 2 and lists the file's targets.

**Composition jobs are exempt.** A `.wacj` composes already-deployed output: `-n` would fight the run's purpose, `--skip-reports` has nothing to skip, and output targets belong to the member builds. The wrapper therefore runs a `.wacj` with native semantics automatically (reported on an `[INFO]` line) — no injected flags, no target requirement. To rehearse a compose without touching the mirror, pass the native `--dryrun` switch.

Note: a clean build (`-c`) is **not** a default — pass it explicitly when you need one.

### Environment Variable Override

Use `AUTOMAP_EXE_PATH` (or the `-ExePath` wrapper option) to bypass auto-detection:

```bash
# Point to a development/debug build (bash syntax)
export AUTOMAP_EXE_PATH="C:/builds/debug/WebWorks.Automap.exe"
```

```powershell
# PowerShell syntax
$env:AUTOMAP_EXE_PATH = 'C:\builds\debug\WebWorks.Automap.exe'
```

### Verify Installation (Optional)

To check if AutoMap is installed and where:

```bash
powershell -ExecutionPolicy Bypass -File "<skill-dir>/scripts/Find-AutomapInstallation.ps1" -ShowBuild
```

Add `-Verbose` for detection diagnostics. Detection takes well under a second — no caching needed.
</quick_start>

<job_files>

## Job Files

Job files (.waj) are lean automation files that reference a Stationery project for format configuration.

### Creating Job Files

To create a job file from scratch:

1. Identify your Stationery file (.wxsp)
2. Gather your source documents
3. Decide which formats to build

The skill will guide you through:
- Parsing Stationery to show available formats
- Organizing documents into groups
- Configuring targets with overrides
- Generating valid XML

### Job File Scripts

```bash
# Parse Stationery to see available formats and settings
python scripts/parse-stationery.py stationery.wxsp

# Create job file interactively
python scripts/create-job.py --stationery stationery.wxsp

# Create job from config file
python scripts/create-job.py --config config.json --output job.waj

# Generate a config template from Stationery
python scripts/create-job.py --template --stationery stationery.wxsp > template.json
```

### Working with Existing Job Files

```bash
# Parse job file to view configuration
python scripts/parse-job.py job.waj

# Export to editable config format
python scripts/parse-job.py --config job.waj > job-config.json

# Validate job file before building
python scripts/validate-job.py job.waj

# Validate with full checks
python scripts/validate-job.py --check-documents --check-stationery job.waj

# List targets with build status
python scripts/list-job-targets.py job.waj

# Show only enabled targets
python scripts/list-job-targets.py --enabled job.waj
```

All four tools accept `.wacj` composition jobs as well as `.waj` (2026.1+): parse/validate/list dispatch on the root element (`<Job>` vs `<CompositionJob>`), `validate-job.py --check-members` is the composition preflight, and `create-job.py --template --composition` emits a composition config template. See references/composition-jobs.md's Tooling section.

### Stationery Relationship

Job files reference their origin via `<Project path="..."/>`:
- Paths are relative to job file location
- All format settings inherited from the origin (Stationery `.wxsp`, or a `.wep`/`.wrp` project)
- Targets can override conditions, variables, settings
- A `.wep`/`.wrp` origin builds **in place** (its own documents, the job's `<Files>` ignored) unless `useAsStationery="True"` stages it as a **stationery** (job documents injected) — see the three job-origin modes in references/job-file-guide.md

### Job-Stored Build Options (2026.1+)

A `.waj` can carry `<Options skipReports="True" verboseLogging="False"/>`. These **combine with** the equivalent CLI switches rather than being overridden by them: either `skipReports` or `--skip-reports` skips reports; either clearing `verboseLogging` or passing `-q` quiets the run. A scheduled task passes no flags, so the stored options are what it honors. The wrapper's unconditional `--skip-reports` injection is therefore harmless but also uninformative about what the job declares — use `-NoDefaults` when a run must match the job exactly. See references/job-file-guide.md.
</job_files>

<cli_reference>

## Wrapper Options

### Basic Syntax

```
Invoke-Automap.ps1 [wrapper options] [--] <automap options> <project-file>
```

Wrapper options come first; everything after the `--` separator (or after the first token that is not a wrapper option) is forwarded to `WebWorks.Automap.exe` verbatim. Always include `--` — it makes the boundary explicit.

### Wrapper Options (before `--`)

| Option | Description |
|--------|-------------|
| `-NoDefaults` | Verbatim native CLI behavior: no injected flags, no explicit-target requirement. Use for production/CI builds and for AutoMap versions older than 2025.1. |
| `-AllTargets` | Waive only the explicit-target requirement. For `.waj`, builds the job's `build="True"` set; for projects, builds every target. Defaults still apply. |
| `-ExePath <path>` | AutoMap executable to run (overrides `AUTOMAP_EXE_PATH` and auto-detection). |
| `-Help` | Show usage. |

### AutoMap Options (after `--`)

All native flags pass through unchanged — in any form the AutoMap CLI itself accepts (`-t "Name"`, `--target=A,B`, `--stagingdir <dir>`, `--stagingdir=<dir>`, ...). Frequently used:

| Native flag | Description |
|-------------|-------------|
| `-t <name>`, `--target=<n1>,<n2>` | Build specific target(s). Case-sensitive. |
| `-c, --clean` | Clean build (not a wrapper default — pass explicitly) |
| `-n, --nodeploy` | Skip deployment *(injected by default)* |
| `--skip-reports` | Skip report pipelines *(injected by default; 2025.1+)* |
| `-d, --deployfolder <path>` | Deploy to a specific folder (suppresses the `-n` default) |
| `-l, --cleandeploy` | Clean deploy location first (suppresses the `-n` default) |
| `-s, --stagingdir <dir>` | Staging directory for job-file (`.waj`) builds; output lands at `<dir>/<JobName>/Output/<target>/` |
| `--destination=<name>` | Deploy every built target to the named destination instead of its own. Ignored when `-d` is given. Suppresses the `-n` default. *(2026.1+)* |
| `-q, --quiet` | Suppress the engine's progress messages in the console and job log; warnings and errors still print. Combines with a job's **Verbose logging** option. *(2026.1+)* |

**For the complete native CLI reference with examples, see:** references/cli-reference.md
</cli_reference>

<scripts>

## Scripts

| Script | Purpose |
|--------|---------|
| `Find-AutomapInstallation.ps1` | Find AutoMap installation (registry, then filesystem) |
| `Invoke-Automap.ps1` | Execute builds (the execution interface) |
| `parse-stationery.py` | Extract formats/settings from Stationery |
| `create-job.py` | Create job files (`.waj` and `.wacj`) interactively or from config |
| `parse-job.py` | Parse existing job files (`.waj` and `.wacj`) |
| `validate-job.py` | Validate job files before building (`--check-members` for compositions) |
| `list-job-targets.py` | List targets with build status (members for a `.wacj`) |

Both PowerShell scripts run on Windows PowerShell 5.1 (preinstalled on Windows) and later; `powershell -ExecutionPolicy Bypass -File` works under the default `Restricted` policy without changing user state.
</scripts>

<references>

## Reference Files

- `cli-reference.md` - Complete CLI options and syntax
- `cli-vs-administrator.md` - When to use CLI vs GUI; Administrator capabilities (destinations, preview, scheduling)
- `composition-jobs.md` - `.wacj` composition jobs, federated vs. derivative members, destinations, dry run
- `installation-detection.md` - Installation paths and detection logic
- `job-file-guide.md` - Job file structure, origin modes, build options, Stationery inheritance
</references>

<requirements>

## Requirements

- WebWorks ePublisher 2024.1+ with AutoMap component (safe defaults assume 2025.1+; use `-NoDefaults` with 2024.1)
- Windows operating system with Windows PowerShell 5.1+ (preinstalled)
- Python 3.10+ (for job file scripts)

### Python Dependencies

Install required packages before using job file scripts:

```bash
pip install -r scripts/requirements.txt
```
</requirements>

<exit_codes>

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Build successful |
| 1 | Build failed |
| 2 | Invalid arguments / no target specified |
| 3 | AutoMap not installed |
| 4 | Project file not found |
</exit_codes>

<post_build_log_scan>

## Post-Build Log Scan

After a successful build (exit 0), the wrapper scans each target's `generate.log` and reports `[WARN]` and `[ERROR]` counts per target.

- Project files (`.wep`, `.wrp`): scans `<project-dir>/Logs/<target>/generate.log`.
- Job files (`.waj`): scans under the staging folder — `<stagingDir>/<JobName>/Logs/<target>/generate.log` — using the `-s`/`--stagingdir` value from the arguments, or the default staging folder (`%USERPROFILE%\Documents\WebWorks ePublisher AutoMap\Staging`). An `[INFO]` line announces the staging location when counts are found there.
- Targets with non-zero counts get a one-line summary (`[WARNING]` on stdout when only warnings, `[ERROR]` on stderr when any errors). Clean targets emit nothing.
- Exit codes are unchanged — the scan is observational. A successful build that records warnings still exits 0.

**The scan matches the shipped localized markers.** `[WARN]`/`[ERROR]` are localized, and the scan covers every spelling ePublisher ships: German `[WARNUNG]`/`[FEHLER]`, French `[AVERTISSEMENT]`/`[ERREUR]`, Japanese `[警告]`/`[エラー]`. An install language with no translated resources falls back to the English markers, which the scan also matches, so counts are trustworthy on any install.

For a `.wacj`, the scanned `<job name>-log.txt` also contains **relayed member-build lines** that keep their markers. Those belong to the member's own ledger, so the wrapper's count is deliberately looser than the composition's own closing tally — see references/composition-jobs.md.

```text
[SUCCESS] Build completed in 43s
[WARNING] 3 warning(s), 0 error(s) in Logs/Reverb2/generate.log
```

### Investigating warnings and errors — read the log

The wrapper's minimal output already surfaces failures: AutoMap's stderr passes through, and the scan prints per-target counts. To see the per-line detail behind a reported count or a failed build, **read `generate.log`** — the wrapper has no verbose/streaming mode, and none is needed: the log holds every `[WARN]`/`[ERROR]` line.

```bash
# On a reported error/warning count or a non-zero exit, read the log:
grep -nE '\[ERROR\]|\[WARN\]' "<project-or-staging>/Logs/<target>/generate.log"
```

(To watch live progress interactively — a human need, not an agent one — run `WebWorks.Automap.exe` directly.)

</post_build_log_scan>

<completion_behavior>

## Completion Behavior

When invoked by another command or skill (component mode):

1. Execute the build via `Invoke-Automap.ps1` with the provided arguments
2. Wait for build completion
3. Report the result in the format below
4. **Immediately return control** — do not wait for follow-up questions
5. Do not offer to perform additional builds or related tasks
6. Do not use interactive prompts

The invoking command is responsible for interpreting results and deciding next steps.

### Output Format for Component Invocation

```
**Build [successful|failed].**

| Item | Value |
|------|-------|
| Project/job file | `path/to/file.waj` |
| Target(s) | Reverb2 |
| Output location | `full/path` |
| Build time | XXX seconds |
| Exit code | 0 |
| Log warnings/errors | 3 warning(s), 0 error(s) |
```

Do not add additional commentary or offers to help.

</completion_behavior>

<common_workflows>

## Common Workflows

### CI/CD Integration

```bash
#!/bin/bash
WRAPPER="<skill-dir>/scripts/Invoke-Automap.ps1"

# Production build: verbatim native semantics (deploys, reports)
if powershell -ExecutionPolicy Bypass -File "$WRAPPER" -NoDefaults -- -c -t "WebWorks Reverb 2.0" project.wep; then
    echo "Build successful"
else
    echo "Build failed" && exit 1
fi

# Job files: build the enabled target set, deploy to a folder
powershell -ExecutionPolicy Bypass -File "$WRAPPER" -AllTargets -- -l -d /deploy/path job.waj
```

### Iterative Development

```bash
# Incremental build (default), safe defaults applied
powershell -ExecutionPolicy Bypass -File "$WRAPPER" -- -t "WebWorks Reverb 2.0" project.wep

# Clean build when state is suspect
powershell -ExecutionPolicy Bypass -File "$WRAPPER" -- -c -t "WebWorks Reverb 2.0" project.wep

# Against a development build of AutoMap
powershell -ExecutionPolicy Bypass -File "$WRAPPER" -ExePath "C:\dev\WebWorks.Automap.exe" -- -t "WebWorks Reverb 2.0" project.wep
```
</common_workflows>

<common_mistakes>

## Common Mistakes

**Do not call the AutoMap CLI directly.** Always use `Invoke-Automap.ps1`, which handles installation detection, safe defaults, minimal output, and the post-build log scan. `Find-AutomapInstallation.ps1` is for the wrapper's internal use and troubleshooting — not for building a manual CLI invocation.

**Do not invent wrapper flags.** Older versions of this skill had wrapper-only flags (`--deploy`, `--no-clean`, `--with-reports`, `--all-targets`, `--verbose`). They are gone. Everything after `--` must be a **native AutoMap flag**; the only wrapper options are `-NoDefaults`, `-AllTargets`, `-ExePath`, and `-Help`, and they go **before** `--`. To deploy or generate reports, use `-NoDefaults` (or pass a deploy flag like `-d`, which suppresses the `-n` default).

**Do not use `-t` with job files expecting it to work like project files.** Job files (.waj) control which targets to build via `build="True"` attributes in the file itself. The `-t` option with job files is an override. To build the job's own enabled set, pass the wrapper option `-AllTargets`.

**Do not `cd` to a project directory before calling the wrapper.** The wrapper accepts project file paths as arguments. Always use the full path to the wrapper script (it lives in the skill directory, not the project directory).

</common_mistakes>

<troubleshooting>

## Troubleshooting

### "AutoMap installation not found"

**Cause:** AutoMap not installed or not in expected location.

**Solutions:**
1. Verify ePublisher AutoMap is installed
2. Check registry: `HKLM\SOFTWARE\WebWorks\ePublisher AutoMap`
3. Check filesystem: `C:\Program Files\WebWorks\ePublisher\[version]\`
4. Run `Find-AutomapInstallation.ps1 -Verbose` for detection diagnostics
5. Set `AUTOMAP_EXE_PATH` (or pass `-ExePath`) to the executable explicitly

### "Build failed with exit code 1"

**Cause:** ePublisher build encountered errors.

**Solutions:**
1. Read `generate.log` for the specific error lines — `grep -nE '\[ERROR\]|\[WARN\]' "<project-or-staging>/Logs/<target>/generate.log"`. AutoMap's stderr also passes through the wrapper, so genuine errors surface inline (see [Post-Build Log Scan](#post-build-log-scan)).
2. Verify source documents exist and are accessible
3. Open project in ePublisher Designer (`.wep`) or Express (`.wrp`) to check for issues
4. Try a clean build (`-c`)

### "No target specified" (exit 2)

**Cause:** The wrapper requires an explicit target by default.

**Solutions:**
1. Pass `-t "<name>"` or `--target="Name1,Name2"` (the error message lists the file's targets)
2. To build the file's full declared set intentionally, pass the wrapper option `-AllTargets`
3. For verbatim native CLI behavior, pass `-NoDefaults`

### "Target not found"

**Cause:** Specified target name doesn't exist in project.

**Solutions:**
1. Use the epublisher skill's `parse-targets.py` to list available targets
2. Verify target name spelling (case-sensitive)
3. Check project file for available `<Format>` elements

### Unknown option errors from AutoMap

**Cause:** A flag after `--` is not a native AutoMap option (for example, a retired wrapper flag such as `--deploy` or `--all-targets`), or the installed AutoMap predates the flag (`--skip-reports` requires 2025.1+).

**Solutions:**
1. Check the native option list in references/cli-reference.md
2. With pre-2025.1 versions, pass `-NoDefaults` so `--skip-reports` is not injected

### Job File Errors

- **Stationery not found** — check `<Project path="..."/>` (relative to the job file); run `python scripts/validate-job.py job.waj`
- **Format not found in Stationery** — target `format` attribute must match a Stationery format name (case-sensitive); run `python scripts/parse-stationery.py stationery.wxsp`
- **Document not found** — document paths are relative to the job file; run `python scripts/validate-job.py --check-documents job.waj`

</troubleshooting>

<success_criteria>

## Success Criteria

- AutoMap installation detected
- Build executed without errors
- Output generated at expected location
- Exit code indicates success (0)
</success_criteria>
