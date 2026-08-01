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
"C:\Program Files\WebWorks\ePublisher\<version>\ePublisher AutoMap\WebWorks.Automap.exe" -c -n -t "WebWorks Reverb 2.0" project.wep
```

`<version>` is the installed release (`2024.1`, `2025.1`, `2026.1`, ...). Do not
hard-code it — use `Find-AutomapInstallation.ps1`, or better, the wrapper.

**Input files it accepts:**

| Extension | What it is |
|-----------|------------|
| `.wep`, `.wrp` | Designer / Express project — builds every target unless `-t` narrows it |
| `.wxsp` | Stationery |
| `.waj` | AutoMap job — builds its `build="True"` set unless `-t` overrides |
| `.wacj` | AutoMap **composition job** *(2026.1+)* — composes already-deployed output; generation options do not apply |

One executable runs all of them, dispatching on the root element for the two
job kinds (`<Job>` vs `<CompositionJob>`).

**Command-Line Arguments:** the option surface is documented once, in
[cli-reference.md](./cli-reference.md#native-command-options) — including the
2026.1 additions (`-q`/`--quiet`, `--deployscope`, `--deploysettings`,
`--destination`, `--dryrun`). It is not repeated here.

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
"C:\Program Files\WebWorks\ePublisher\<version>\ePublisher AutoMap\WebWorks.Automap.Administrator.exe"
```

**Features:**
- Create and configure AutoMap jobs (publishing and composition)
- Schedule automated builds through the Windows Task Scheduler
- Manage the Jobs folder, staging folder, and file mappings
- Configure build options visually
- Test job configurations interactively
- Define and edit deploy destinations
- Preview deployed output in a browser

### Administrator capabilities added in 2026.1

Four additions change what "only the GUI can do" means. Know them before
telling a user something requires hand-editing a file.

**Composition jobs are first-class.** `File > New Job` offers a third intent —
**Compose published parcels into a website (Composition Job)** — which creates
a `.wacj` in the Jobs folder and opens a composition editor (members grid with
role and Build, **Output target:** combo, destination, Merge Settings). Full
detail: [composition-jobs.md](./composition-jobs.md#authoring-a-composition-in-the-automap-administrator).

**Deploy Destinations moved to the Edit menu.** `Edit > Deploy Destinations...`
opens the destination editor **without opening a job or selecting a target** —
destinations are shared state, not job-owned, so they no longer hide behind a
target's configuration page. Adding an entry offers **Folder** and **Amazon
S3**; entries created for other transports remain editable there.

- Designer and Express gained the same top-level access this release (their own
  **Edit** menus, plus a **Deploy Destinations** toolbar button). All three
  consoles read and write **one shared list, stored per Windows user** on the
  machine (`deploy.prefs`).
- Separately, a job can carry its own destination **definitions** on the job
  editor's **Job Deploy Destinations** page. Those travel with the job file and
  win over a same-named local destination when the job runs. Folder and Amazon
  S3 only — no credentials are stored.
- The target's **Deploy to** list labels where each name comes from:
  `<name> (this job)` for a job-inline definition, `<name> (local)` for one from
  this computer's `deploy.prefs`.
- A name that resolves to **neither** is still listed, as
  `<name> (not defined on this computer)`. This is deliberate: hiding it would
  read as "this job has no destination" and would discard the name on the next
  save. **The name is preserved on save, and the label reports only what *this
  computer* knows** — a build server that defines the name runs the job without
  complaint. Treat the label as a local-resolution report, not as a defect in
  the job.

**Preview Output in Browser.** A `Job` menu command sitting immediately beside
**Explore Output** (right-click reaches it too). Explore opens the deployed
*files* — a folder, or the S3 console; Preview opens the deployed *site*. It
drops down one entry per deploying target for a publishing job, or the single
destination for a composition job; a target the job does not generate is listed
as *(not generated)* and cannot be selected.

| Destination | What opens |
|-------------|------------|
| Folder | the entry document directly, as a `file://` URL. The entry document name comes from the deployed shell record when one is present, else `index.html`. |
| Amazon S3 | an address **derived at click time**, first success wins: (1) the CloudFront distribution's domain, read with one authenticated `GetDistribution` call, when the destination has a distribution ID; (2) the S3 static-website endpoint; (3) the virtual-hosted REST address of the entry object. |

- **Every rung is verified before the browser opens**, but not identically:
  rung 1 is verified by the authenticated `GetDistribution` call itself (so it
  works for private buckets and is not probed further), rungs 2 and 3 are
  HEAD-probed — which is what lets the failure message distinguish "not public"
  (403) from "not found" and from "website hosting is not enabled".
- **Nothing about the serving URL is persisted.** No new fields exist on the
  destination; every address is recomputed per click. It is therefore
  explicitly a *preview*, not necessarily the production URL — custom domains
  and CDN configuration are outside ePublisher's knowledge. Presigned URLs are
  deliberately never attempted (a signature covers one object; Reverb output
  fetches many).
- When no rung succeeds, the dialog reports **which derivations failed and
  why** rather than a bare error.
- A target that deploys with **Groups** scope publishes only the content layer,
  so the destination carries no site entry page of *its* making. On an S3
  destination the preview reports that scope instead of deriving a misleading
  address. On a Folder destination it opens **the job's own group entry page**
  when the destination has chrome to render it (a shell deployed there), and
  otherwise explains why there is nothing to open. Preview the composition job
  for that destination, or deploy a shell there.

**Job-level build options.** The job editor's **Job Info** tab has a **Build
options** area (**Skip reports**, **Verbose logging**) whose values are stored
in the job file, so they apply on a schedule, from **Run**, and from a bare CLI
invocation alike. They **combine with** the equivalent CLI switches rather than
being overridden by them — see
[job-file-guide.md](./job-file-guide.md#build-options-skip-reports--verbose-logging).

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

✅ Creating new AutoMap jobs, including composition jobs (`.wacj`)
✅ Configuring job settings and parameters
✅ Setting up build schedules
✅ Testing job configurations interactively
✅ Defining and editing deploy destinations (`Edit > Deploy Destinations...`)
✅ Previewing deployed output in a browser
✅ Visual configuration of complex builds
✅ Learning AutoMap features

## Detection Script Behavior

The `Find-AutomapInstallation.ps1` script:

1. Detects the Administrator executable (via registry or filesystem)
2. Normalizes the path to the CLI executable
3. Returns the CLI path for automation use

This ensures the wrapper script always uses the CLI version regardless of
how detection succeeds.

**Example:**

```bash
# Detection finds Administrator
Found: C:\Program Files\WebWorks\ePublisher\2026.1\ePublisher AutoMap\WebWorks.Automap.Administrator.exe

# Script normalizes to CLI
Returns: C:\Program Files\WebWorks\ePublisher\2026.1\ePublisher AutoMap\WebWorks.Automap.exe
```

## Installation Directory Structure

```
C:\Program Files\WebWorks\ePublisher\<version>\ePublisher AutoMap\
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
C:\Program Files\WebWorks\ePublisher\<version>\ePublisher AutoMap\WebWorks.Automap.exe
                                                 ^^^^^^^^                 ^^^^^^^
                                                capital M              lowercase m
```

## Exit Codes

| Code | Meaning | Who returns it |
|------|---------|----------------|
| 0 | Success — the run completed and reported no errors | CLI (and wrapper) |
| 1 | Failure — the run reported errors | CLI (and wrapper) |
| 2 | Invalid arguments / no target specified | wrapper only |
| 3 | AutoMap installation not detected | wrapper only |
| 4 | Project file not found | wrapper only |

The CLI's own contract is 0/1. Codes 2–4 are the wrapper's, raised before
AutoMap is ever launched. A scheduled task that runs a job through the launcher
therefore only ever records `0x0` or `0x1` (plus `0x41301` while running).

### Using Exit Codes in Scripts

```bash
#!/bin/bash

WRAPPER="<skill-dir>/scripts/Invoke-Automap.ps1"
powershell -ExecutionPolicy Bypass -File "$WRAPPER" -- -t "WebWorks Reverb 2.0" project.wep

# Check exit code
case $? in
    0) echo "Build succeeded" ;;
    2) echo "Bad arguments (no target?)"; exit 2 ;;
    3) echo "AutoMap not installed"; exit 3 ;;
    4) echo "Project file not found"; exit 4 ;;
    *) echo "Build failed"; exit 1 ;;
esac
```

## Common Use Cases

### Automated CI/CD Build

```bash
#!/bin/bash
# Jenkins/GitHub Actions build script

WRAPPER="<skill-dir>/scripts/Invoke-Automap.ps1"

# Clean build, no deploy (wrapper injects -n and --skip-reports)
powershell -ExecutionPolicy Bypass -File "$WRAPPER" -- -c -t "Production Target" my-project.wep

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

WRAPPER="<skill-dir>/scripts/Invoke-Automap.ps1"

for project in "${projects[@]}"; do
    echo "Building $project..."
    powershell -ExecutionPolicy Bypass -File "$WRAPPER" -AllTargets -- -c "$project"

    if [ $? -ne 0 ]; then
        echo "Failed to build $project"
        exit 1
    fi
done

echo "All projects built successfully"
```

### Scheduled Builds

There are two ways to run AutoMap on a schedule. Prefer the first.

**1. Let the Administrator own the schedule (jobs).** For a `.waj` or `.wacj`
in the Jobs folder, use `Job > Schedule Job`. The Administrator registers a
Windows Task Scheduler task named `waj <job name>` whose action is the
**version-independent launcher** — `<ProgramFiles>\WebWorks\ePublisher\WebWorks.AutoMap.exe`
— not the versioned CLI. That indirection is the point: the task survives an
ePublisher upgrade without being re-created, because only the launcher's
configuration is rewritten per release.

Consequences worth knowing:

- **The running process is the launcher.** In Task Manager it appears as
  **WebWorks ePublisher AutoMap Launcher**. Match on that name for
  process-based monitoring or "is a job running" checks — not on
  `WebWorks.Automap.exe`, which is the child it spawns.
- **`Last Run Result` is the job's verdict.** The CLI's exit code propagates
  through the launcher to the Task Scheduler:

  | `Last Run Result` | Meaning |
  |-------------------|---------|
  | `0x0` | the run completed and reported no errors |
  | `0x1` | the run completed but reported errors — read the job log |
  | `0x41301` | the task is still running |

  Checking this column is cheaper than opening the log, and it is reliable as
  of 2026.1: earlier launchers could lose the exit code entirely when a console
  text selection froze output, which also silently skipped the next scheduled
  run under the default single-instance policy.
- **The task action embeds an absolute, bitness-specific launcher path.** With
  an x86 and an x64 install coexisting, a pre-existing task keeps firing
  whichever install created it. The Administrator's Schedule… dialog is the
  full task editor (Actions tab included) — fix it there. To diagnose which
  install actually ran, read the `Running WebWorks ePublisher AutoMap version …`
  line in the job log.
- **Build behavior belongs in the job, not the command line.** A scheduled task
  invokes the CLI with no flags, so the job's stored
  [build options](./job-file-guide.md#build-options-skip-reports--verbose-logging)
  (Skip reports, Verbose logging) are what a scheduled run honors.

**2. Schedule your own script (projects, or CI-shaped work).** For a `.wep`/`.wrp`
that is not registered as a job, schedule a script that calls the wrapper — not
`WebWorks.Automap.exe` directly, which skips installation detection, the safe
defaults, and the post-build log scan:

```powershell
# Windows Task Scheduler action: powershell.exe -ExecutionPolicy Bypass -File C:\ci\nightly.ps1

$Wrapper     = "<skill-dir>\scripts\Invoke-Automap.ps1"
$ProjectFile = "C:\projects\my-proj\my-proj.wep"

# Production semantics: deploy per the target's configuration, generate reports
& powershell -ExecutionPolicy Bypass -File $Wrapper -NoDefaults -- -c -l -t "WebWorks Reverb 2.0" $ProjectFile

if ($LASTEXITCODE -eq 0) {
    Send-MailMessage -To "team@company.com" -Subject "Build Succeeded" -Body "Daily build completed successfully"
} else {
    Send-MailMessage -To "team@company.com" -Subject "Build Failed" -Body "Daily build failed with exit code $LASTEXITCODE"
}
```

Exit the script with `$LASTEXITCODE` so the Task Scheduler's `Last Run Result`
stays meaningful.

## Troubleshooting

### GUI Launches Instead of CLI

**Problem:** Running the wrapper script launches a GUI window instead of running headless.

**Cause:** Detection script returned Administrator executable path instead of CLI path.

**Solution:**
1. Check detection script output: `powershell -ExecutionPolicy Bypass -File Find-AutomapInstallation.ps1 -Verbose`
2. Verify output ends with `WebWorks.Automap.exe` (not `.Administrator.exe`)
3. If incorrect, verify the normalization function is working

### No Display Server Error

**Problem:** Error message about missing display server when running in headless environment.

**Cause:** Administrator executable was launched instead of CLI.

**Solution:**
- Ensure detection script returns CLI executable path
- Verify the `.Administrator.exe` to `.exe` normalization is being applied
- Check that CLI executable exists at normalized path

### Exit Code Always 0

**Problem:** Script always returns success even when build fails.

**Cause:** Not capturing exit code correctly, or UI application returns success.

**Solution:**
- Use `$?` immediately after AutoMap execution
- Verify CLI executable is being used (not Administrator)
- For a scheduled job, read `Last Run Result` in the Task Scheduler rather than
  inferring from the console; a pre-2026.1 launcher could lose the exit code
  when a console text selection froze output

### Scheduled Job Never Runs Again After One Bad Run

**Problem:** A scheduled job ran once, the window stayed open, and later
triggers silently did nothing.

**Cause:** A pre-2026.1 launcher whose console was put into text-selection mode
blocked output forever, so no exit code was recorded. With the default
single-instance policy, the Task Scheduler treats the task as still running and
skips subsequent triggers.

**Solution:**
1. Press Esc in the console (its title carries a `Select ` prefix), or end the
   task
2. Upgrade — 2026.1 disables QuickEdit for the run's duration and captures the
   exit code before draining output

## Best Practices

### For Automation Scripts

1. **Go through `Invoke-Automap.ps1`** - Never invoke the Administrator for automation, and do not build a manual `WebWorks.Automap.exe` invocation either; the wrapper owns installation detection, safe defaults, and the log scan
2. **Capture exit codes** - Check return value after execution
3. **Use absolute paths** - Avoid relying on PATH environment variable
4. **Validate project files** - Check file exists before execution
5. **Put build behavior in the job** - A scheduled task passes no flags, so a job's stored build options are what it honors
6. **Handle errors gracefully** - Provide clear error messages
7. **Test in target environment** - Verify headless execution works

### For Interactive Usage

1. **Use Administrator for configuration** - Easier to set up complex jobs
2. **Test jobs interactively first** - Verify settings before automation
3. **Preview before publishing** - `Job > Preview Output in Browser` confirms the deployed site actually serves
4. **Document custom settings** - Record non-default options used

## Related Documentation

- [cli-reference.md](./cli-reference.md) - The complete native option surface
- [composition-jobs.md](./composition-jobs.md) - `.wacj` grammar and the composition editor
- [job-file-guide.md](./job-file-guide.md) - Job file structure, origin modes, build options
- [installation-detection.md](./installation-detection.md) - How detection works
- WebWorks ePublisher User Guide - Official documentation

