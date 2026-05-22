# AutoMap CLI vs. Administrator Executables

## Overview

WebWorks ePublisher includes two separate AutoMap executables with different purposes.
Understanding the distinction is important for automation and integration.

## Executable Comparison

### WebWorks.Automap.exe (CLI)

- **Purpose:** Command-line automation and scripting
- **Usage:** Headless builds, CI/CD integration, batch processing
- **Interface:** Command-line arguments only
- **Output:** Text to stdout/stderr
- **Return:** Exit codes for success/failure
- **Requires Display:** No

**Example Usage:**
```cmd
"C:\Program Files\WebWorks\ePublisher\2024.1\ePublisher AutoMap\WebWorks.Automap.exe" -c -n -t "WebWorks Reverb 2.0" project.wep
```

**Command-Line Arguments:**
- `-c` - Clean build (remove cached files)
- `-n` - No deploy (skip copying to deployment location)
- `-l` - Clean deploy (remove existing files at deployment location)
- `-t "Target Name"` - Build specific target only
- `--deployfolder "Path"` - Override deployment destination
- `<project-file>` - Path to .wep, .wrp, or .wxsp project file

### WebWorks.Automap.Administrator.exe (UI)

- **Purpose:** Interactive job creation and scheduling
- **Usage:** Manual job configuration, schedule management
- **Interface:** Graphical user interface (GUI)
- **Output:** Visual windows and dialogs
- **Return:** Interactive user actions
- **Requires Display:** Yes

**Example Usage:**
```cmd
# Launches GUI application
"C:\Program Files\WebWorks\ePublisher\2024.1\ePublisher AutoMap\WebWorks.Automap.Administrator.exe"
```

**Features:**
- Create and configure AutoMap jobs
- Schedule automated builds
- Manage job templates
- Configure build options visually
- Test job configurations interactively

## When to Use Each

### Use CLI (WebWorks.Automap.exe) for:

✅ Automated builds in CI/CD pipelines
✅ Batch processing multiple projects
✅ Scheduled tasks (Windows Task Scheduler, cron)
✅ Docker/container deployments
✅ Remote execution via SSH
✅ Integration with other automation tools
✅ Headless server environments
✅ Script-based workflows

### Use Administrator (WebWorks.Automap.Administrator.exe) for:

✅ Creating new AutoMap jobs
✅ Configuring job settings and parameters
✅ Setting up build schedules
✅ Testing job configurations interactively
✅ Managing job templates
✅ Visual configuration of complex builds
✅ Learning AutoMap features

## Detection Script Behavior

The `detect-installation.sh` script:

1. Detects the Administrator executable (via registry or filesystem)
2. Normalizes the path to the CLI executable
3. Returns the CLI path for automation use

This ensures the wrapper script always uses the CLI version regardless of
how detection succeeds.

**Example:**

```bash
# Detection finds Administrator
Found: C:\Program Files\WebWorks\ePublisher\2024.1\ePublisher AutoMap\WebWorks.Automap.Administrator.exe

# Script normalizes to CLI
Returns: C:\Program Files\WebWorks\ePublisher\2024.1\ePublisher AutoMap\WebWorks.Automap.exe
```

## Installation Directory Structure

```
C:\Program Files\WebWorks\ePublisher\2024.1\ePublisher AutoMap\
├── WebWorks.Automap.exe                    ← CLI (for automation)
├── WebWorks.Automap.Administrator.exe      ← UI (for job management)
├── [supporting DLLs and resources]
└── ...
```

Both executables are installed together in the same directory.

## Naming Convention Note

There is a quirk in the naming convention:

- **Product Name:** AutoMap (capital M)
- **Directory Name:** ePublisher AutoMap (capital M)
- **Executable Names:** Automap (lowercase m)

This quirk is maintained throughout the codebase for consistency with
WebWorks naming conventions.

**Example:**
```
C:\Program Files\WebWorks\ePublisher\2024.1\ePublisher AutoMap\WebWorks.Automap.exe
                                                ^^^^^^^^                 ^^^^^^^
                                               capital M              lowercase m
```

## Exit Codes

### CLI Executable Exit Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 0 | Success | Build completed successfully |
| 1 | Failure | Build failed (errors occurred) |
| 2 | Invalid Arguments | Command-line arguments were invalid |
| 3 | Not Found | AutoMap installation not detected |
| 4 | File Not Found | Project file does not exist |

### Using Exit Codes in Scripts

```bash
#!/bin/bash

# Execute AutoMap build
automap_path="/c/Program Files/WebWorks/ePublisher/2024.1/ePublisher AutoMap/WebWorks.Automap.exe"
"$automap_path" -c -n project.wep

# Check exit code
if [ $? -eq 0 ]; then
    echo "Build succeeded"
    exit 0
else
    echo "Build failed"
    exit 1
fi
```

## Common Use Cases

### Automated CI/CD Build

```bash
#!/bin/bash
# Jenkins/GitHub Actions build script

# Detect AutoMap CLI
AUTOMAP_CLI=$(./detect-installation.sh)

# Clean build, no deploy
"$AUTOMAP_CLI" -c -n -t "Production Target" my-project.wep

# Check result
if [ $? -eq 0 ]; then
    echo "Build succeeded, proceeding to deployment..."
else
    echo "Build failed, stopping pipeline"
    exit 1
fi
```

### Batch Processing Multiple Projects

```bash
#!/bin/bash
# Build multiple projects in sequence

projects=(
    "project1.wep"
    "project2.wep"
    "project3.wep"
)

AUTOMAP_CLI=$(./detect-installation.sh)

for project in "${projects[@]}"; do
    echo "Building $project..."
    "$AUTOMAP_CLI" -c -n "$project"

    if [ $? -ne 0 ]; then
        echo "Failed to build $project"
        exit 1
    fi
done

echo "All projects built successfully"
```

### Scheduled Build Task

```powershell
# Windows Task Scheduler PowerShell script

$AutoMapCLI = "C:\Program Files\WebWorks\ePublisher\2024.1\ePublisher AutoMap\WebWorks.Automap.exe"
$ProjectFile = "C:\projects\my-proj\my-proj.wep"

# Execute build
& $AutoMapCLI -c -l -t "WebWorks Reverb 2.0" $ProjectFile

# Email notification based on exit code
if ($LASTEXITCODE -eq 0) {
    Send-MailMessage -To "team@company.com" -Subject "Build Succeeded" -Body "Daily build completed successfully"
} else {
    Send-MailMessage -To "team@company.com" -Subject "Build Failed" -Body "Daily build failed with exit code $LASTEXITCODE"
}
```

## Troubleshooting

### GUI Launches Instead of CLI

**Problem:** Running the wrapper script launches a GUI window instead of running headless.

**Cause:** Detection script returned Administrator executable path instead of CLI path.

**Solution:**
1. Check detection script output: `./detect-installation.sh --verbose`
2. Verify output ends with `WebWorks.Automap.exe` (not `.Administrator.exe`)
3. If incorrect, verify the normalization function is working

### No Display Server Error

**Problem:** Error message about missing display server when running in headless environment.

**Cause:** Administrator executable was launched instead of CLI.

**Solution:**
- Ensure detection script returns CLI executable path
- Verify `normalize_to_cli_path()` function is being called
- Check that CLI executable exists at normalized path

### Exit Code Always 0

**Problem:** Script always returns success even when build fails.

**Cause:** Not capturing exit code correctly, or UI application returns success.

**Solution:**
- Use `$?` immediately after AutoMap execution
- Verify CLI executable is being used (not Administrator)
- Check wrapper script's `execute_automap()` function

## Best Practices

### For Automation Scripts

1. **Always use CLI executable** - Never use Administrator for automation
2. **Capture exit codes** - Check return value after execution
3. **Use absolute paths** - Avoid relying on PATH environment variable
4. **Validate project files** - Check file exists before execution
5. **Log output** - Capture stdout/stderr for troubleshooting
6. **Handle errors gracefully** - Provide clear error messages
7. **Test in target environment** - Verify headless execution works

### For Interactive Usage

1. **Use Administrator for configuration** - Easier to set up complex jobs
2. **Test jobs interactively first** - Verify settings before automation
3. **Export job configurations** - Save templates for reuse
4. **Document custom settings** - Record non-default options used

## Related Documentation

- [installation-detection.md](./installation-detection.md) - How detection works
- AutoMap Wrapper Script - Usage and examples
- WebWorks ePublisher User Guide - Official documentation

