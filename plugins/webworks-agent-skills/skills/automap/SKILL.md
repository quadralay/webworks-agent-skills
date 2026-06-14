---
name: automap
description: >
  AUTHORITATIVE REFERENCE for WebWorks AutoMap CLI. Use when working with
  .waj/.wep/.wrp/.wxsp files, executing builds, detecting installation,
  creating job files, or automating CI/CD publishing workflows.
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
</overview>

<usage>

## How to Use This Skill

**Always use the wrapper script to execute builds.** The wrapper:
- Automatically detects the AutoMap installation
- Handles path conversion between Unix and Windows formats
- Provides consistent error handling and exit codes
- Supports environment variable override via `AUTOMAP_EXE_PATH`
- Provides minimal token usage impact by default

Do NOT use `detect-installation.sh` to find the CLI path and call it directly. The wrapper is the execution interface.
</usage>

<script_paths>

## Script Path Convention

All `scripts/` paths in this skill are relative to the skill's base directory (the directory containing this SKILL.md file). When the skill loads, the base directory is provided in the "Base directory for this skill" header.

**When executing scripts, always use the full path from the base directory:**

```bash
# Correct: use the skill's base directory
bash /path/to/automap/scripts/automap-wrapper.sh [options] /absolute/path/to/project.waj

# Wrong: assumes scripts/ exists in the current working directory
bash scripts/automap-wrapper.sh project.waj
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

**External:**

- **markdown-plus-plus** ([`quadralay/markdown-plus-plus`](https://github.com/quadralay/markdown-plus-plus)) — Markdown++ format syntax and pre-build validation script. Install separately when authoring or validating Markdown++ source documents.

</related_skills>

<quick_start>

## Quick Start

### Run a Build

**Project files (.wep, .wrp)** - Use `-t` to specify target:

```bash
# Build single target (safe defaults: clean, no-deploy, skip-reports)
bash scripts/automap-wrapper.sh -t "WebWorks Reverb 2.0" project.wep

# CI/CD: Build all targets explicitly
bash scripts/automap-wrapper.sh --all-targets project.wep

# Production: Deploy with reports
bash scripts/automap-wrapper.sh --deploy --with-reports -t "Target" project.wep
```

**Job files (.waj)** - Targets determined by `build="True"` in file:

```bash
# Build job file (targets set in file, no -t needed)
bash scripts/automap-wrapper.sh job.waj

# With deployment
bash scripts/automap-wrapper.sh -l -d /path/to/deploy job.waj
```

The wrapper automatically detects the AutoMap installation and applies safe defaults.

### Safe Defaults (v2.4.0+)

The wrapper now applies these options by default:

| Default | Opt-Out Flag | Description |
|---------|--------------|-------------|
| `-c` (clean) | `--no-clean` | Clean build for consistency |
| `-n` (no deploy) | `--deploy` | Prevent accidental overwrites |
| `--skip-reports` | `--with-reports` | Faster builds *(2025.1+)* |

### Interactive Target Selection (Project Files Only)

When using project files (.wep, .wrp) with no target specified:
- **Single-target projects**: Auto-builds the only target
- **Multi-target projects**: Prompts for selection (interactive mode)
- **CI/CD (non-interactive)**: Requires `-t`, `--target=`, or `--all-targets`

**Note:** Job files (.waj) do not need target selection options — see overview for details.

### Environment Variable Override

Use `AUTOMAP_EXE_PATH` to bypass auto-detection:

```bash
# Cache detected path for multiple builds
export AUTOMAP_EXE_PATH=$(bash scripts/detect-installation.sh)

# Or point to a development/debug build
export AUTOMAP_EXE_PATH="/c/builds/debug/net48/WebWorks.Automap.exe"
```

### Verify Installation (Optional)

To check if AutoMap is installed and where:

```bash
bash scripts/detect-installation.sh --verbose
```
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

### Stationery Relationship

Job files reference their origin via `<Project path="..."/>`:
- Paths are relative to job file location
- All format settings inherited from the origin (Stationery `.wxsp`, or a `.wep`/`.wrp` project)
- Targets can override conditions, variables, settings
- A `.wep`/`.wrp` origin builds **in place** (its own documents, the job's `<Files>` ignored) unless `useAsStationery="True"` stages it as a **stationery** (job documents injected) — see the three job-origin modes in references/job-file-guide.md
</job_files>

<cli_reference>

## Wrapper Options

### Basic Syntax

```bash
# Project files (.wep, .wrp) - target selection required
bash scripts/automap-wrapper.sh [options] <project-file> [-t <target-name>]

# Job files (.waj) - targets set in file (no -t needed)
bash scripts/automap-wrapper.sh [options] <job-file>
```

### Target Selection

These options apply primarily to project files (.wep, .wrp). When used with job files, they override the `build="True"` settings.

| Option | Description |
|--------|-------------|
| `-t <name>` | Build single target |
| `--target=<name1>,<name2>` | Build multiple specific targets |
| `--all-targets` | Build all targets (bypasses interactive selection) |

### Build Options (Safe Defaults)

| Option | Default | Opt-Out | Description |
|--------|---------|---------|-------------|
| `-c, --clean` | Enabled | `--no-clean` | Clean build |
| `-n, --nodeploy` | Enabled | `--deploy` | Skip deployment |
| `--skip-reports` | Enabled | `--with-reports` | Skip report pipelines *(2025.1+)* |
| `-l, --cleandeploy` | Disabled | - | Clean deployment location |

### Other Options

| Option | Description |
|--------|-------------|
| `--verbose` | Show all build output (default: minimal) |
| `-d, --deployfolder PATH` | Override deployment destination (implies `--deploy`) |
| `-s, --stagingdir DIR` | Override staging directory for job-file (`.waj`) builds; output lands at `DIR/<JobName>/Output/<target>/` |

Any other option is passed through to the AutoMap executable (value-bearing pass-through options must use the `--flag=value` form).

**For complete CLI reference with examples, see:** references/cli-reference.md
</cli_reference>

<scripts>

## Scripts

| Script | Purpose |
|--------|---------|
| `detect-installation.sh` | Find AutoMap installation |
| `automap-wrapper.sh` | Execute builds with error handling |
| `parse-stationery.py` | Extract formats/settings from Stationery |
| `create-job.py` | Create job files interactively or from config |
| `parse-job.py` | Parse existing job files |
| `validate-job.py` | Validate job files before building |
| `list-job-targets.py` | List targets with build status |

### Installation Detection

```bash
bash scripts/detect-installation.sh
```

### Build Wrapper

```bash
# Project files - use -t to specify targets
bash scripts/automap-wrapper.sh [options] <project-file> [-t <target-name>]

# Job files - targets set in file (no -t needed)
bash scripts/automap-wrapper.sh [options] <job-file>
```

Supports both project files (.wep, .wrp) and job files (.waj). For project files with multiple targets, use `--target="Name1","Name2"` or `--all-targets`.
</scripts>

<references>

## Reference Files

- `cli-reference.md` - Complete CLI options and syntax
- `cli-vs-administrator.md` - When to use CLI vs GUI
- `installation-detection.md` - Installation paths and detection logic
- `job-file-guide.md` - Job file structure and Stationery inheritance
</references>

<requirements>

## Requirements

- WebWorks ePublisher 2024.1+ with AutoMap component
- Windows operating system
- Git Bash or similar Unix-like shell
- Python 3.10+ (for job file scripts)

### Python Dependencies

Install required packages before using job file scripts:

```bash
pip install -r scripts/requirements.txt
```

Or install directly:

```bash
pip install defusedxml
```
</requirements>

<exit_codes>

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Build successful |
| 1 | Build failed |
| 2 | Invalid arguments / user cancelled |
| 3 | AutoMap not installed |
| 4 | Project file not found |
</exit_codes>

<post_build_log_scan>

## Post-Build Log Scan

After a successful build (exit 0), the wrapper scans every `Logs/<TargetName>/generate.log` under the project directory and reports `[WARN]` and `[ERROR]` counts per target.

- Targets with non-zero counts get a one-line summary — yellow when only warnings are present, red when the target has any errors.
- Targets with zero counts emit nothing; missing `Logs/` directory emits nothing.
- `--verbose` additionally echoes each extracted `[WARN]`/`[ERROR]` line under a per-target header.
- Exit codes are unchanged — the scan is observational. A successful build that records warnings still exits 0.

```text
[SUCCESS] Build completed in 43s
[WARNING] 3 warning(s), 0 error(s) in Logs/Reverb2/generate.log
```

</post_build_log_scan>

<common_workflows>

## Common Workflows

### CI/CD Integration

```bash
#!/bin/bash
# Project files: use --all-targets
if bash scripts/automap-wrapper.sh --all-targets project.wep; then
    echo "Build successful"
else
    echo "Build failed" && exit 1
fi

# Job files: targets set in file, no -t needed
if bash scripts/automap-wrapper.sh -l -d /deploy/path job.waj; then
    echo "Build successful"
else
    echo "Build failed" && exit 1
fi
```

### Batch Building Multiple Projects

```bash
# Cache installation path for efficiency
export AUTOMAP_EXE_PATH=$(bash scripts/detect-installation.sh)

for project in projects/*.wep; do
    # --all-targets required in non-interactive (CI) mode
    bash scripts/automap-wrapper.sh --all-targets "$project" || echo "Failed: $project"
done
```

### Interactive Development

```bash
# No target specified - prompts for selection if multiple targets exist
bash scripts/automap-wrapper.sh project.wep

# Incremental build (skip clean)
bash scripts/automap-wrapper.sh --no-clean -t "WebWorks Reverb 2.0" project.wep
```
</common_workflows>

<common_mistakes>

## Common Mistakes

**Do not call the AutoMap CLI directly.** Always use `automap-wrapper.sh`, which handles installation detection, path conversion, safe defaults, and error handling. The `detect-installation.sh` script is for the wrapper's internal use and environment variable caching — not for building a manual CLI invocation.

**Do not use `-t` with job files expecting it to work like project files.** Job files (.waj) control which targets to build via `build="True"` attributes in the file itself. The `-t` option with job files is an override, not the primary mechanism. If a build seems to skip targets, check the job file's `build` attributes first.

**Do not `cd` to a project directory before calling the wrapper.** The wrapper accepts project file paths as arguments. Changing the working directory before calling the script causes `scripts/automap-wrapper.sh` to fail because `scripts/` is relative to the skill directory, not the project directory. Always use the full path to the wrapper script.

</common_mistakes>

<troubleshooting>

## Troubleshooting

### "AutoMap installation not found"

**Cause:** AutoMap not installed or not in expected location.

**Solutions:**
1. Verify ePublisher AutoMap is installed
2. Check registry: `HKLM\SOFTWARE\WebWorks\ePublisher AutoMap`
3. Check filesystem: `C:\Program Files\WebWorks\ePublisher\[version]\`
4. Use `--verbose` flag for detailed detection output

### "Build failed with exit code 1"

**Cause:** ePublisher build encountered errors.

**Solutions:**
1. Check AutoMap output for specific error messages
2. Verify source documents exist and are accessible
3. Open project in ePublisher Administrator to check for issues
4. Try building with `-c` (clean) flag

### "Target not found"

**Cause:** Specified target name doesn't exist in project.

**Solutions:**
1. Use the epublisher skill's `parse-targets.py` to list available targets
2. Verify target name spelling (case-sensitive)
3. Check project file for available `<Format>` elements

### Job File Errors

**Stationery not found**
```
Error: Stationery file not found: ..\stationery\main.wxsp
```
- Check `<Project path="..."/>` in job file
- Verify path is relative to job file location
- Run: `python scripts/validate-job.py job.waj`

**Invalid target format**
```
Error: Format "Unknown Format" not found in Stationery
```
- Target `format` attribute must match format name in Stationery
- Format names are case-sensitive
- Run: `python scripts/parse-stationery.py stationery.wxsp` to list available formats

**Document path errors**
```
Warning: Document not found: Source\missing.md
```
- Document paths are relative to job file location
- Check for typos in path
- Run: `python scripts/validate-job.py --check-documents job.waj`

</troubleshooting>

<success_criteria>

## Success Criteria

- AutoMap installation detected
- Build executed without errors
- Output generated at expected location
- Exit code indicates success (0)
</success_criteria>
