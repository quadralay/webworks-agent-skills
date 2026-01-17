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
</objective>

<overview>

## Overview

AutoMap is the command-line build tool for ePublisher. It processes source documents and generates output without requiring the GUI application.

### Supported File Types

- **Project files (.wep, .wrp)**: Complete self-contained projects
- **Job files (.waj)**: Lean automation files that reference Stationery

### Job Files and Stationery

Job files inherit format configuration from Stationery projects (.wxsp), enabling:
- Separation of format design from build automation
- Lean, portable job definitions
- Pre/post build script execution (hook-like capability)

**For job file details, see:** references/job-file-guide.md
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

<related_skills>

## Related Skills

| Skill | Relationship |
|-------|--------------|
| **epublisher** | Use first to understand project structure and target names |
| **reverb** | Use after building Reverb output to test and customize |

</related_skills>

<quick_start>

## Quick Start

### Run a Build

```bash
# Build single target (safe defaults: clean, no-deploy, skip-reports)
bash ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/automap-wrapper.sh -t "WebWorks Reverb 2.0" project.wep

# CI/CD: Build all targets explicitly
bash ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/automap-wrapper.sh --all-targets project.wep

# Production: Deploy with reports
bash ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/automap-wrapper.sh --deploy --with-reports -t "Target" project.wep
```

The wrapper automatically detects the AutoMap installation and applies safe defaults.

### Safe Defaults (v2.4.0+)

The wrapper now applies these options by default:

| Default | Opt-Out Flag | Description |
|---------|--------------|-------------|
| `-c` (clean) | `--no-clean` | Clean build for consistency |
| `-n` (no deploy) | `--deploy` | Prevent accidental overwrites |
| `--skip-reports` | `--with-reports` | Faster builds *(2025.1+)* |

### Interactive Target Selection

When no target is specified:
- **Single-target projects**: Auto-builds the only target
- **Multi-target projects**: Prompts for selection (interactive mode)
- **CI/CD (non-interactive)**: Requires `-t`, `--target=`, or `--all-targets`

### Environment Variable Override

Use `AUTOMAP_EXE_PATH` to bypass auto-detection:

```bash
# Cache detected path for multiple builds
export AUTOMAP_EXE_PATH=$(bash ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/detect-installation.sh)

# Or point to a development/debug build
export AUTOMAP_EXE_PATH="/c/builds/debug/net48/WebWorks.Automap.exe"
```

### Verify Installation (Optional)

To check if AutoMap is installed and where:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/detect-installation.sh --verbose
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
python ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/parse-stationery.py stationery.wxsp

# Create job file interactively
python ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/create-job.py --stationery stationery.wxsp

# Create job from config file
python ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/create-job.py --config config.json --output job.waj

# Generate a config template from Stationery
python ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/create-job.py --template --stationery stationery.wxsp > template.json
```

### Working with Existing Job Files

```bash
# Parse job file to view configuration
python ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/parse-job.py job.waj

# Export to editable config format
python ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/parse-job.py --config job.waj > job-config.json

# Validate job file before building
python ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/validate-job.py job.waj

# Validate with full checks
python ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/validate-job.py --check-documents --check-stationery job.waj

# List targets with build status
python ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/list-job-targets.py job.waj

# Show only enabled targets
python ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/list-job-targets.py --enabled job.waj
```

### Stationery Relationship

Job files reference Stationery via `<Project path="..."/>`:
- Paths are relative to job file location
- All format settings inherited from Stationery
- Targets can override conditions, variables, settings
</job_files>

<cli_reference>

## Wrapper Options

### Basic Syntax

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/automap-wrapper.sh [options] <project-file> [-t <target-name>]
```

### Target Selection

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
| `--deployfolder PATH` | Override deployment destination |

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
bash ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/detect-installation.sh
```

### Build Wrapper

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/automap-wrapper.sh [options] <project-or-job-file> [-t <target-name>]
```

Supports both project files (.wep) and job files (.waj). For multiple targets use `--target="Name1", "Name2"`.
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

<common_workflows>

## Common Workflows

### CI/CD Integration

```bash
#!/bin/bash
# Build all targets (safe defaults applied automatically)
if bash ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/automap-wrapper.sh --all-targets project.wep; then
    echo "Build successful"
    # Deploy output...
else
    echo "Build failed"
    exit 1
fi
```

### Batch Building Multiple Projects

```bash
# Cache installation path for efficiency
export AUTOMAP_EXE_PATH=$(bash ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/detect-installation.sh)

for project in projects/*.wep; do
    # --all-targets required in non-interactive (CI) mode
    bash ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/automap-wrapper.sh --all-targets "$project" || echo "Failed: $project"
done
```

### Interactive Development

```bash
# No target specified - prompts for selection if multiple targets exist
bash ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/automap-wrapper.sh project.wep

# Incremental build (skip clean)
bash ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/automap-wrapper.sh --no-clean -t "WebWorks Reverb 2.0" project.wep
```
</common_workflows>

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
1. Use `parse-targets.sh` to list available targets
2. Verify target name spelling (case-sensitive)
3. Check project file for available `<Format>` elements

### Job File Errors

**Stationery not found**
```
Error: Stationery file not found: ..\stationery\main.wxsp
```
- Check `<Project path="..."/>` in job file
- Verify path is relative to job file location
- Run: `python ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/validate-job.py job.waj`

**Invalid target format**
```
Error: Format "Unknown Format" not found in Stationery
```
- Target `format` attribute must match format name in Stationery
- Format names are case-sensitive
- Run: `python ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/parse-stationery.py stationery.wxsp` to list available formats

**Document path errors**
```
Warning: Document not found: Source\missing.md
```
- Document paths are relative to job file location
- Check for typos in path
- Run: `python ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/validate-job.py --check-documents job.waj`

</troubleshooting>

<success_criteria>

## Success Criteria

- AutoMap installation detected
- Build executed without errors
- Output generated at expected location
- Exit code indicates success (0)
</success_criteria>
