# Job File Guide

## Table of Contents

- [Overview](#overview)
- [Job Files vs Project Files](#job-files-vs-project-files)
- [Stationery Inheritance](#stationery-inheritance)
- [Job Origin Modes (Stationery vs Project)](#job-origin-modes-stationery-vs-project)
- [XML Structure](#xml-structure)
- [Element Reference](#element-reference)
- [Output Location (Staging Folder)](#output-location-staging-folder)
- [Build Options (Skip reports / Verbose logging)](#build-options-skip-reports--verbose-logging)
- [Creating Job Files](#creating-job-files)
- [Target Configuration](#target-configuration)
- [Merge Settings (Multivolume / Merged TOC)](#merge-settings-multivolume--merged-toc)
- [Common Patterns](#common-patterns)
- [Troubleshooting](#troubleshooting)

---

## Overview

AutoMap Job files (`.waj`) are XML configuration files that define automated build workflows for ePublisher. They provide a lean approach to build automation by inheriting format configuration from Stationery projects.

### Key Benefits

- **Lean**: Only define what to build, not how to format
- **Portable**: Same job file works across machines with the Stationery
- **Flexible**: Override conditions, variables, and settings per target
- **Scriptable**: Supports pre/post build script execution

---

## Job Files vs Project Files

| Aspect | Project File (`.wep`, `.wrp`) | Job File (`.waj`) |
|--------|-------------------------------|-------------------|
| Purpose | Complete self-contained project | Build automation definition |
| References | N/A (self-contained) | Stationery (`.wxsp`) |
| Format config | Full configuration embedded | Inherited from Stationery |
| Source docs | Defined in project | Defined in job file |
| Per-target overrides | FormatSettings | Conditions, Variables, Settings |
| Size | Large (complete config) | Small (references Stationery) |
| Created by | ePublisher Designer/Express | AutoMap Administrator or scripts |
| Scripts | No | Yes (pre/post build) |

### When to Use Job Files

Use job files when:
- Multiple users share the same format configuration
- You need to build the same content with different settings
- You want script execution before/after builds
- You're automating builds in CI/CD pipelines
- You need locale-specific builds from the same Stationery

---

## Stationery Inheritance

Job files reference a Stationery project (`.wxsp`) to inherit format configuration:

```
Stationery (.wxsp)              Job File (.waj)
├── Format definitions    ←──── References via <Project path="..."/>
├── Style mappings              ├── Source documents
├── Target settings             ├── Target overrides
└── Customizations              └── Build flags
```

### What Job Files Inherit

- Format names and types
- Output directory defaults
- Style mappings
- Adapter configurations
- File type mappings

### What Job Files Define

- Source documents and organization
- Which targets to build
- Target-specific overrides (conditions, variables, settings)
- Destination names
- Build flags (clean, build enabled)

---

## Job Origin Modes (Stationery vs Project)

The `<Project>` element's `path` decides where the build's format configuration comes from. As of ePublisher 2026.1 there are **three** origin modes, selected by the referenced file's extension and the optional `useAsStationery` attribute:

| # | `<Project path>` points at | `useAsStationery` | Behavior |
|---|----------------------------|-------------------|----------|
| 1 | Stationery (`.wxsp`) | n/a (ignored) | Stage a fresh project from the Stationery, inject the job's `<Files>` and target overrides, then build. *(Existing behavior — the common case.)* |
| 2 | Project (`.wep`, `.wrp`) | absent / `"False"` | **Build in place.** AutoMap builds the referenced project using *its own* documents and configuration; the job's `<Files>` are **ignored**. *(Existing behavior.)* |
| 3 | Project (`.wep`, `.wrp`) | `"True"` | **Project used as a stationery (new in 2026.1).** AutoMap uses the live project directly as a stationery: it stages a fresh project from the project's format configuration (stripping the project's own documents, document groups, **merge settings**, `ProjectID`, and `<Origin>`), injects the job's `<Files>` and target overrides, then builds — exactly like mode 1, but sourced from a Designer/Express project instead of a generated Stationery. |

### Why mode 3 exists

Mode 3 removes the manual **"Save As Stationery"** step from CI. Instead of regenerating a `.wxsp` every time the design changes, the job points straight at the live Designer/Express project and synchronizes from it on every build. Without it, a design change that never reached the Stationery is a build that silently publishes the previous design.

### What the origin supplies, and what it does not

The origin project supplies the **design**: output formats, targets and target settings, styles, and any format/target overrides it carries. Everything publication-specific comes from the job.

Not carried into the build: the origin's own **source documents**, **document groups**, and **merge settings**. A design project that holds sample documents for previewing therefore cannot leak those samples — or their TOC arrangement — into the job's output. A job that needs a multivolume TOC declares its own `<MergeSettings>` on the target (see [Merge Settings (Multivolume / Merged TOC)](#merge-settings-multivolume--merged-toc)).

### Keep the installation and the design project on the same version

A design project used as a stationery does **not** carry its own copy of the output format files — a Designer `.wep` has no `<format>.base` snapshots, so its transforms resolve from the ePublisher installation that runs the job, the same way a hollow stationery's would. (See the epublisher skill's `references/file-resolver-guide.md` for the `.base` resolution hierarchy.)

**Keep the installation that runs your jobs at the same version as the one the design project is maintained in.** A version mismatch resolves the design against a different format build than the designer sees. That is silent fidelity drift, not a build error — nothing in the log flags it.

### Creating one: the two New Job intents

In the AutoMap Administrator, both mode 2 and mode 3 name a `.wep`/`.wrp` file; the intent selected on the **New Job** window decides which one you get, and AutoMap records the difference in the job file:

| New Job option | Origin picker | Resulting mode |
|----------------|---------------|----------------|
| **Create a new publishing job** | *Choose ePublisher stationery or project* — accepts `.wxsp`, `.wep`, `.wrp` | mode 1 for a `.wxsp`; **mode 3** (`useAsStationery="True"`) for a `.wep`/`.wrp` |
| **Automate an existing project** | *Choose ePublisher project* — accepts `.wep`, `.wrp` | **mode 2** (build in place) |

The picker for the first option is the tell: one field, one filter, three extensions. Selecting a project there routes through the stationery wizard — the one with the Files page — because the job still supplies its own documents.

### Staging behavior

Modes 1 and 3 are identical from the staging point of view: AutoMap stages a temporary Express project (`.wrp`) under the **Staging Folder** and builds there — see [Output Location (Staging Folder)](#output-location-staging-folder). Only mode 2 builds in place, into the referenced project's own `Output/` folder.

### Designer project as stationery — CI without regenerating Stationery

A job that uses a live Designer project as its stationery looks exactly like a Stationery-based job, except the `<Project>` reference points at a `.wep` and opts in with `useAsStationery="True"`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<Job name="docs-ci" version="1.0">
  <!-- Designer project used as a stationery: build straight from the live project -->
  <Project path="..\design\design.wep" useAsStationery="True" />

  <Files>
    <Group name="Guide">
      <Document path="Source\intro.md" />
      <Document path="Source\reference.md" />
    </Group>
  </Files>

  <Targets>
    <Target name="WebWorks Reverb 2.0"
            format="WebWorks Reverb 2.0"
            formatType="Application"
            build="True"
            destination=""
            cleanOutput="False" />
  </Targets>
</Job>
```

On each build AutoMap re-reads `design.wep`, stages a stationery from its current format configuration, injects the `<Files>` above, and builds — no `.wxsp` to regenerate when the design changes.

> **Without** `useAsStationery="True"`, the same `<Project path="..\design\design.wep" />` reference would fall into mode 2: AutoMap would build `design.wep` in place using *its* documents and ignore the `<Files>` above entirely.

---

## XML Structure

### Minimal Job File

```xml
<?xml version="1.0" encoding="utf-8"?>
<Job name="en" version="1.0">
  <Project path="stationery\main.wxsp" />
  <Files>
    <Group name="Book">
      <Document path="Source\document.md" />
    </Group>
  </Files>
  <Targets>
    <Target name="WebWorks Reverb 2.0"
            format="WebWorks Reverb 2.0"
            formatType="Application"
            build="True"
            destination=""
            cleanOutput="False" />
  </Targets>
</Job>
```

### Complete Job File with Overrides

```xml
<?xml version="1.0" encoding="utf-8"?>
<Job name="help-en" version="1.0">
  <Project path="..\stationery\main.wxsp" />

  <Files>
    <Group name="Getting Started">
      <Document path="Source\en\intro.md" />
      <Document path="Source\en\installation.md" />
      <Document path="Source\en\quickstart.md" />
    </Group>
    <Group name="Reference">
      <Document path="Source\en\api.md" />
      <Document path="Source\en\troubleshooting.md" />
    </Group>
  </Files>

  <Targets>
    <Target name="WebWorks Reverb 2.0"
            format="WebWorks Reverb 2.0"
            formatType="Application"
            build="True"
            destination="Production Help"
            cleanOutput="False">

      <Conditions Expression="" UseClassicConditions="False" UseDocumentExpression="True">
        <Condition name="OnlineOnly" value="True" Passthrough="False" UseDocumentValue="False" />
        <Condition name="PrintOnly" value="False" Passthrough="False" UseDocumentValue="False" />
      </Conditions>

      <Variables>
        <Variable name="ProductVersion" value="2025.1" UseDocumentValue="False" />
        <Variable name="PublicationDate" value="December 2025" UseDocumentValue="False" />
      </Variables>

      <Settings>
        <Setting name="locale" value="en-US" />
        <Setting name="show-first-document" value="true" />
      </Settings>
    </Target>

    <Target name="PDF Output"
            format="PDF - XSL-FO"
            formatType="Document"
            build="False"
            destination=""
            cleanOutput="False" />
  </Targets>
</Job>
```

---

## Element Reference

### `<Job>` Element (Root)

| Attribute | Required | Description | Example |
|-----------|----------|-------------|---------|
| `name` | Yes | Job identifier | `"en"`, `"help-production"` |
| `version` | Yes | Schema version | `"1.0"` |

### `<Project>` Element

| Attribute | Required | Description | Example |
|-----------|----------|-------------|---------|
| `path` | Yes | Relative or absolute path to the Stationery (`.wxsp`) **or** project (`.wep`/`.wrp`) origin | `"stationery\main.wxsp"`, `"..\design\design.wep"` |
| `useAsStationery` | No | When `"True"`, use a `.wep`/`.wrp` project directly as a stationery (mode 3 below). `"True"`/`"False"`, default `"False"`. Applies **only** when `path` points at a `.wep`/`.wrp`; ignored for `.wxsp`. *(camelCase, consistent with `build`/`cleanOutput`.)* | `"True"` |

The attribute selects which of the three [Job Origin Modes (Stationery vs Project)](#job-origin-modes-stationery-vs-project) applies. It is optional and backward compatible: omitting it preserves the existing behavior for every existing job file.

**Path Resolution**: Paths are relative to the job file's directory. **Prefer a relative path** to the Stationery — including parent-relative (`..\`) traversal when the Stationery lives outside the job file's folder (e.g. `..\stationery\main.wxsp`). Relative paths keep the job portable across machines. Reach for an **absolute path only when** a relative one is impossible or impractical:

1. The Stationery is on a **different drive** than the job file (no shared path root exists)
2. The Stationery is on a **different network share**
3. The job file and the Stationery share **only the drive letter or share root** as a common ancestor — a relative path technically works but is long and unmaintainable (e.g. `..\..\..\..\Other\Tree\main.wxsp`), so absolute is preferable

### `<Options>` Element

*(2026.1+)* Optional direct child of `<Job>`, written after `<Project>`. Stores the job's **build options** — behavior that travels with the job file, so it applies however the job runs: on its schedule, from **Run**, or from a direct CLI invocation. See [Build Options (Skip reports / Verbose logging)](#build-options-skip-reports--verbose-logging).

| Attribute | Required | Description | Values | Default |
|-----------|----------|-------------|--------|---------|
| `skipReports` | No | Skip report generation for every target the job builds | `"True"`, `"False"` | `False` |
| `verboseLogging` | No | Record the generation engine's step-by-step progress in the console and job log | `"True"`, `"False"` | `True` |

```xml
<Job name="nightly" version="1.0">
  <Project path="stationery\main.wxsp" />
  <Options skipReports="True" verboseLogging="False" />
  ...
</Job>
```

**Written only when non-default.** A job that keeps both defaults carries no `<Options>` element at all, so jobs saved before the element existed load unchanged and round-trip byte-stable. On load, `skipReports` is true only for an explicit `"true"`; `verboseLogging` is false only for an explicit `"false"`.

### `<Files>` Element

Container for document groups. Contains one or more `<Group>` elements.

### `<Group>` Element

| Attribute | Required | Description | Example |
|-----------|----------|-------------|---------|
| `name` | Yes | Group name | `"Getting Started"`, `"Reference"` |

Contains one or more `<Document>` elements.

### `<Document>` Element

| Attribute | Required | Description | Example |
|-----------|----------|-------------|---------|
| `path` | Yes | Path to source document | `"Source\en\intro.md"` |

**Path Resolution**: Paths are relative to the job file's directory. **Prefer a relative path** to each source document — including parent-relative (`..\`) traversal when a document lives outside the job file's folder (e.g. `..\Source\Word\Overview.docx`). Relative paths keep the job portable. Use an absolute path only in the narrow cases listed under the [`<Project>` element](#project-element) (different drive, different network share, or only the drive/share root as a common ancestor).

### `<Targets>` Element

Container for build targets. Contains one or more `<Target>` elements.

### `<Target>` Element

| Attribute | Required | Description | Values |
|-----------|----------|-------------|--------|
| `name` | Yes | Target name (for CLI `-t` parameter) | Must match Stationery format |
| `format` | Yes | Format name from Stationery | Must match exactly (case-sensitive) |
| `formatType` | Yes | Format type | `"Application"`, `"Document"` |
| `build` | Yes | Build this target by default | `"True"`, `"False"` |
| `destination` | No | Named destination (pre-release spelling `deployTarget` still read for one release) | Empty string or name |
| `cleanOutput` | Yes | Clean output before build | `"True"`, `"False"` |

### `<Conditions>` Element

| Attribute | Description |
|-----------|-------------|
| `Expression` | Condition expression (if using expressions) |
| `UseClassicConditions` | Use legacy condition syntax |
| `UseDocumentExpression` | Inherit expression from document |

### `<Condition>` Element

| Attribute | Description | Values |
|-----------|-------------|--------|
| `name` | Condition name | String |
| `value` | Condition value | `"True"`, `"False"` |
| `Passthrough` | Pass through unchanged | `"True"`, `"False"` |
| `UseDocumentValue` | Use value from document | `"True"`, `"False"` |

### `<Variables>` Element

Container for variable overrides.

### `<Variable>` Element

| Attribute | Description |
|-----------|-------------|
| `name` | Variable name |
| `value` | Variable value |
| `UseDocumentValue` | Use value from source document |

### `<Settings>` Element

Container for format setting overrides.

### `<Setting>` Element

| Attribute | Description |
|-----------|-------------|
| `name` | Setting name (must exist in Stationery) |
| `value` | Setting value |

### `<MergeSettings>` Element

Optional child of `<Target>`. Defines a multivolume / merged TOC for Reverb-family formats. Maps to the project's `<FormatConfiguration><MergeSettings>`. See [Merge Settings (Multivolume / Merged TOC)](#merge-settings-multivolume--merged-toc).

| Attribute | Required | Description | Example |
|-----------|----------|-------------|---------|
| `title` | No | Title of the merged master TOC | `"MasterTOC"` |

Contains `<TOC>` and/or `<Group>` child nodes, in document order, describing the TOC layout.

### `<TOC>` Element (within `<MergeSettings>`)

A custom container (a TOC folder) that groups parcels under a labeled node. Nestable.

| Attribute | Required | Description | Example |
|-----------|----------|-------------|---------|
| `name` | Yes | Container display name | `"Layer1"` |

Contains nested `<TOC>` and/or `<Group>` nodes.

### `<Group>` Element (within `<MergeSettings>`)

Places a document group as a parcel (a volume) in the merged TOC. **Distinct from the `<Group>` under `<Files>`**: here it is a reference *by name* to a `<Files>` group, not a container of `<Document>` elements.

| Attribute | Required | Description | Example |
|-----------|----------|-------------|---------|
| `name` | Yes | Name of a **top-level** `<Files>` group to place | `"Group1"` |
| `title` | No | Display-title override for this parcel | `"Group One"` |
| `context` | No | Context (CSH) value for this parcel | `"admin"` |

**Resolution**: Groups are referenced by name. AutoMap resolves each name to the staged project's GroupID — you never write GroupIDs by hand — so only top-level `<Files>` groups can be placed. This maps to the project's `<MergeGroup GroupID Title>`.

---

## Output Location (Staging Folder)

When AutoMap builds a Stationery-based job file (`.waj`), it does **not** build in place next to the `.waj`. It stages a temporary Express project (`.wrp`) under the **Staging Folder** and builds there:

```
<stagingDir>/<JobName>/<JobName>.wrp        ← staged project
<stagingDir>/<JobName>/Output/<TargetName>/ ← built output
```

`<JobName>` is the `name` attribute of the `<Job>` root element; `<TargetName>` is the target's `name`.

**Default Staging Folder** (an AutoMap preference, set in the AutoMap Administrator):

```
%USERPROFILE%\Documents\WebWorks ePublisher AutoMap\Staging
```

**Override per run** with `-s` / `--stagingdir` (accepted by the AutoMap executable and exposed by the wrapper):

| Option | Description |
|--------|-------------|
| `-s <dir>`, `--stagingdir <dir>` | Use `<dir>` as the staging directory for this build |

```bash
# Via the wrapper
powershell -ExecutionPolicy Bypass -File "<skill-dir>/scripts/Invoke-Automap.ps1" -- -t "WebWorks Reverb 2.0" --stagingdir "C:\automap\staging" merged-help.waj

# Directly
"path/to/WebWorks.Automap.exe" --stagingdir "C:\automap\staging" merged-help.waj

# Output -> C:\automap\staging\merged-help\Output\WebWorks Reverb 2.0\
```

**Notes**:

- The staged project (and its `Output/`) persists after the build by default (the AutoMap "Remove temporary files" preference is off), which is why output can be retrieved from the Staging Folder. Deployment (`-d`/`--deployfolder`, or a `destination`) copies output elsewhere; without it, the Staging Folder is the only place output lands.
- This staging behavior applies to Stationery-based jobs (mode 1) **and** to `.wep`/`.wrp` jobs that opt in with `useAsStationery="True"` (mode 3) — both stage a temporary `.wrp` under the Staging Folder. A `.waj` that references a `.wep`/`.wrp` master project **without** `useAsStationery` (mode 2) instead builds in place, into that project's own `Output/` folder, ignoring the job's `<Files>`. See [Job Origin Modes (Stationery vs Project)](#job-origin-modes-stationery-vs-project).

---

## Build Options (Skip reports / Verbose logging)

*(2026.1+)* A job can store two build options in the job file itself, in the [`<Options>` element](#options-element). The AutoMap Administrator exposes them on the job editor's **Job Info** tab, in the **Build options** area. Because they live in the job, they apply on a schedule, from **Run**, and from a direct command-line invocation alike — which matters because a scheduled task invokes the CLI with no flags at all.

| Build option | Job attribute | Default | Effect |
|--------------|---------------|---------|--------|
| **Skip reports** | `skipReports="True"` | cleared | Skips report generation for every target the job builds. Reports add time, so this shortens large conversions. |
| **Verbose logging** | `verboseLogging="False"` | selected | Clearing it omits the generation engine's step-by-step progress messages from the console and the job log, leaving milestone, warning, and error messages. |

### The stored option and the CLI switch combine — they do not override

Each option has an equivalent CLI switch, and the two sources are **combined**, never resolved as a precedence:

| Sources | Rule | Result |
|---------|------|--------|
| `skipReports="True"` **or** `--skip-reports` | OR | reports are skipped |
| `verboseLogging="False"` **or** `-q` / `--quiet` | either quiets | progress messages suppressed |

So a job that stores Skip reports skips reports even on a bare `WebWorks.Automap.exe job.waj`, and a job that leaves Verbose logging selected can still be run quietly from a script. Neither switch can turn a stored option back *on* — there is no `--with-reports` and no un-quiet switch.

> **Note:** Clearing Verbose logging affects the console and the job log only. The per-target `generate.log` is a separate sink and always keeps full detail.

### Consequence for the wrapper

`Invoke-Automap.ps1` injects `--skip-reports` unconditionally (unless already present, or `-NoDefaults` is given). Given the OR rule, that injection is **idempotent with a job's stored option** — a job with `skipReports="True"` behaves the same either way, and a job with the option cleared still gets reports skipped for that run because the switch was passed. The wrapper's `[INFO]` line reports the injected flag, not the job's stored option, so a job that stores Skip reports shows no extra signal. When you need a run's report behavior to match exactly what the job declares (verifying a scheduled task's output, for example), use `-NoDefaults`.

The wrapper never injects `-q`. Its own stdout suppression is a separate mechanism — see cli-reference.md's [Console Output](./cli-reference.md#console-output).

---

## Creating Job Files

### Using Scripts

```bash
# 1. Parse Stationery to see available formats
python scripts/parse-stationery.py stationery.wxsp

# 2a. Create interactively
python scripts/create-job.py --stationery stationery.wxsp

# 2b. Or generate a template and edit
python scripts/create-job.py --template --stationery stationery.wxsp > config.json
# Edit config.json...
python scripts/create-job.py --config config.json --output job.waj

# 3. Validate the result
python scripts/validate-job.py --check-stationery job.waj
```

`validate-job.py` and `parse-job.py` dispatch on the root element (`<Job>` vs `<CompositionJob>`) and report a rename when the file extension and root disagree. For `.wacj` composition jobs, see composition-jobs.md's Tooling section.

### Configuration File Format

When using `create-job.py` with `--config`, use this JSON format:

```json
{
  "name": "help-en",
  "stationery": "..\\stationery\\main.wxsp",
  "useAsStationery": false,
  "groups": [
    {
      "name": "Getting Started",
      "documents": [
        "Source\\en\\intro.md",
        "Source\\en\\installation.md"
      ]
    }
  ],
  "targets": [
    {
      "name": "WebWorks Reverb 2.0",
      "format": "WebWorks Reverb 2.0",
      "formatType": "Application",
      "build": true,
      "cleanOutput": false,
      "destination": "Production",
      "conditions": [
        {"name": "OnlineOnly", "value": "True"}
      ],
      "variables": [
        {"name": "ProductVersion", "value": "2025.1"}
      ],
      "settings": [
        {"name": "locale", "value": "en-US"}
      ]
    }
  ]
}
```

`useAsStationery` is optional and defaults to `false`. Set it to `true` only when `stationery` points at a `.wep`/`.wrp` project you want staged as a stationery (mode 3); `create-job.py` then emits `useAsStationery="True"` on the `<Project>` element, and `parse-job.py --config` round-trips it back. For a `.wxsp` Stationery, leave it `false` (or omit it).

---

## Target Configuration

### Conditions

Conditions control conditional content processing:

```xml
<Conditions Expression="" UseClassicConditions="False" UseDocumentExpression="True">
  <Condition name="OnlineOnly" value="True" Passthrough="False" UseDocumentValue="False" />
  <Condition name="PrintOnly" value="False" Passthrough="False" UseDocumentValue="False" />
</Conditions>
```

**Common Conditions**:
- `OnlineOnly` / `PrintOnly` - Output-specific content
- `DesignerOnly` / `ExpressOnly` - Product edition content
- `Internal` / `External` - Audience-specific content

### Variables

Variables override document-level values:

```xml
<Variables>
  <Variable name="ProductVersion" value="2025.1" UseDocumentValue="False" />
  <Variable name="PublicationDate" value="December 2025" UseDocumentValue="False" />
  <Variable name="CompanyName" value="WebWorks" UseDocumentValue="False" />
</Variables>
```

### Settings

Settings override format-level configuration from Stationery:

```xml
<Settings>
  <Setting name="locale" value="en-US" />
  <Setting name="show-first-document" value="true" />
  <Setting name="header-generate" value="false" />
</Settings>
```

**To see available settings**, run:
```bash
python scripts/parse-stationery.py stationery.wxsp
```

### Deployment (new in 2026.1: scope and inline definitions)

A `<Target>` element routes deployment through `destination` (a named
destination; the 2026.1 pre-release spelling `deployTarget` is still read for
one release) and, as of ePublisher 2026.1, can scope what the deployment
publishes with `deployScope`:

```xml
<Targets>
  <Target name="WebWorks Reverb 2.0" format="WebWorks Reverb 2.0"
          formatType="Application" build="True"
          destination="ProductionMirror" deployScope="groups" />
</Targets>
```

- `deployScope` — `everything` (default), `groups` (content only), or
  `shell` (site files only). Overrides the scope declared in the project;
  `--deployscope` on the CLI overrides both. Supports federated parcel
  composition in WebWorks Reverb 2.0.
- The job can carry the **definition** of its named destinations inline in a
  `<DeploySettings>` element (a direct child of `<Job>`, exact deploy.prefs
  entry schema), so a version-controlled job runs on machines with no seeded
  deploy preferences. Folder and Amazon S3 definitions only; any other
  action is rejected at parse time. Precedence per name: job inline >
  `--deploysettings` overlay file > deploy.prefs.

**For the full federation workflow (.wacj composition jobs, S3 + CloudFront
destinations, dry run), see:** references/composition-jobs.md

---

## Merge Settings (Multivolume / Merged TOC)

Reverb-family formats can combine several document groups into one output with a single, multivolume table of contents. Each top-level `<Files>` group becomes a **parcel** (a volume); `<MergeSettings>` defines how those parcels are titled and arranged in the master TOC.

`<MergeSettings>` is an optional child of `<Target>`. The AutoMap Administrator's Merge Settings dialog generates it, and it can be authored by hand.

### Structure

- `<MergeSettings title="...">` — the merged master TOC (optional title).
  - `<TOC name="...">` — a custom container (TOC folder); nestable.
  - `<Group name="..." title="..." />` — places a `<Files>` group as a parcel, with an optional display-title override.

Groups are referenced **by name** (matching a top-level `<Files>` group). AutoMap resolves each name to that group's GroupID in the staged project, so you never write GroupIDs by hand.

### Worked Example

```xml
<?xml version="1.0" encoding="utf-8"?>
<Job name="merged-help" version="1.0">
  <Project path="stationery\main.wxsp" />

  <!-- Each top-level group is a parcel (a volume in the merged TOC) -->
  <Files>
    <Group name="Group1">
      <Document path="Source\admin\admin-guide.md" />
    </Group>
    <Group name="Group2">
      <Document path="Source\user\user-guide.md" />
    </Group>
  </Files>

  <Targets>
    <Target name="WebWorks Reverb 2.0"
            format="WebWorks Reverb 2.0"
            formatType="Application"
            build="True"
            destination=""
            cleanOutput="False">

      <!-- Define the merged TOC: title, containers, and parcel placement -->
      <MergeSettings title="MasterTOC">
        <TOC name="Layer1">
          <Group name="Group1" title="Group One" />
        </TOC>
        <Group name="Group2" title="Group Two" />
      </MergeSettings>
    </Target>
  </Targets>
</Job>
```

This yields a master TOC titled "MasterTOC" containing:

- **Layer1** (container)
  - **Group One** (parcel, from `Group1`)
- **Group Two** (parcel, from `Group2`)

### How It Maps to the Project

The inline job `<MergeSettings>` is applied onto the staged project's `<FormatConfiguration>`:

| Job file (`.waj`) | Project (`.wrp` / `.wep`) |
|-------------------|---------------------------|
| `<MergeSettings title="MasterTOC">` | `<MergeSettings Title="MasterTOC">` |
| `<TOC name="Layer1">` | `<TOC Name="Layer1">` |
| `<Group name="Group1" title="Group One" />` | `<MergeGroup GroupID="..." Title="Group One" />` |

### Skeleton Master Pattern

A **skeleton master** is a job whose groups carry only minimal stub content, built solely to produce the merged master TOC and the output shell (parcel containers + titles). The real content is built separately — one or more "satellite" parcel jobs — then joined to the master **by group name**. This supports updating individual parcels without rebuilding the whole merged output (federated parcel composition — see composition-jobs.md).

- Give each group at least one stub document. An empty group fails group verification and produces no TOC entry; empty containers are pruned.
- The master is authoritative for the TOC hierarchy and the title overrides — both live only in `<MergeSettings>`. A standalone parcel build cannot reproduce them.

---

## Common Patterns

### Multi-Locale Jobs

Create separate job files for each locale, all referencing the same Stationery:

```
project/
├── stationery/
│   └── main.wxsp
├── Source/
│   ├── en/
│   ├── de/
│   └── fr/
├── automap-en.waj
├── automap-de.waj
└── automap-fr.waj
```

Each job file sets the locale-specific settings:

```xml
<!-- automap-en.waj -->
<Target ...>
  <Settings>
    <Setting name="locale" value="en" />
  </Settings>
</Target>
```

### Conditional Output Types

Use multiple targets with different conditions:

```xml
<Targets>
  <!-- Online help with full content -->
  <Target name="Online Help" format="WebWorks Reverb 2.0" build="True">
    <Conditions>
      <Condition name="OnlineOnly" value="True" />
      <Condition name="PrintOnly" value="False" />
    </Conditions>
  </Target>

  <!-- Print version with limited content -->
  <Target name="Print PDF" format="PDF - XSL-FO" build="False">
    <Conditions>
      <Condition name="OnlineOnly" value="False" />
      <Condition name="PrintOnly" value="True" />
    </Conditions>
  </Target>
</Targets>
```

### CI/CD Integration

```bash
#!/bin/bash
# Build all enabled targets from job file

# Validate first
python scripts/validate-job.py --check-stationery job.waj || exit 1

# Run build (job's enabled target set; wrapper defaults still apply)
powershell -ExecutionPolicy Bypass -File "<skill-dir>/scripts/Invoke-Automap.ps1" -AllTargets -- job.waj

# Check result
if [ $? -eq 0 ]; then
    echo "Build successful"
    # Deploy output...
else
    echo "Build failed"
    exit 1
fi
```

---

## Troubleshooting

### Stationery Not Found

**Error**: `Stationery file not found: ..\stationery\main.wxsp`

**Solutions**:
1. Check the `<Project path="..."/>` value
2. Paths are relative to the job file's location
3. Verify the file exists at the resolved path
4. Run: `python scripts/validate-job.py job.waj`

### Invalid Format Name

**Error**: `Format "Unknown Format" not found in Stationery`

**Solutions**:
1. Format names are case-sensitive
2. List available formats: `python scripts/parse-stationery.py stationery.wxsp`
3. Update the `format` attribute to match exactly

### Job Target Missing from the Stationery

**Error**: `Target "<name>" is not defined by the job's stationery (<path>). Resave the stationery with this target, or remove or rename the job target, then run again.`

Distinct from [Invalid Format Name](#invalid-format-name) above: there the target's `format` attribute names a format the Stationery lacks; here the **target itself** — a `<Target name="...">` the job declares — has no same-named target in the Stationery. The job declares *how* a target builds; the Stationery declares *what* exists. The two have drifted, usually because a target was renamed or removed in the Stationery after the job was written.

**This is a hard error as of 2026.1.** Earlier versions silently recreated the missing target using the output format's **default settings**. The job kept producing output, but that output was configured with format defaults rather than the Stationery author's settings, and nothing indicated the substitution. The error message names both the target and the Stationery so the drift is unambiguous.

**Solutions**:
1. Resave the Stationery with that target, or
2. Remove or rename the job target so the two agree, then run again

A composition raises the same error, with the same remedy wording, for a member's declared target — but **before any member build starts**, prefixed with `Member '<name>': `. See composition-jobs.md.

### Document Not Found

**Warning**: `Document not found: Source\missing.md`

**Solutions**:
1. Document paths are relative to job file location
2. Check for typos in the path
3. Verify the file exists
4. Run: `python scripts/validate-job.py --check-documents job.waj`

### Build Flag Ignored

**Issue**: Target builds even with `build="False"`

**Explanation**: When using `-t TargetName` on the command line, the CLI may override the build flag. Without `-t`, only targets with `build="True"` are built.

### Setting Not Applied

**Issue**: Setting override doesn't take effect

**Solutions**:
1. Verify setting name exactly matches Stationery
2. Check that setting is valid for this format
3. List available settings: `python scripts/parse-stationery.py stationery.wxsp`

### Can't Find Build Output

**Issue**: Built a `.waj` but there's no `Output/` next to the job file.

**Explanation**: Stationery-based job files build into the **Staging Folder**, not next to the `.waj`. Look in `<stagingDir>/<JobName>/Output/<TargetName>/` — by default `<My Documents>\WebWorks ePublisher AutoMap\Staging\<JobName>\Output\<TargetName>\`.

**Solutions**:
1. Check the Staging Folder (see [Output Location (Staging Folder)](#output-location-staging-folder))
2. Set the staging location explicitly with `-s` / `--stagingdir`
3. Deploy the output to a known location with `-d` / `--deployfolder`

### Merge Settings Group Not Appearing

**Issue**: A `<Group>` listed in `<MergeSettings>` doesn't show in the merged TOC.

**Solutions**:
1. The `name` must match a **top-level** group in `<Files>` (nested/child groups cannot be placed)
2. The referenced group must contain at least one document (empty groups are dropped)
3. Group names are matched exactly

---

## Script Reference

| Script | Purpose | Example |
|--------|---------|---------|
| `parse-stationery.py` | Extract formats/settings | `python scripts/parse-stationery.py stationery.wxsp` |
| `create-job.py` | Create job files | `python scripts/create-job.py --stationery stationery.wxsp` |
| `parse-job.py` | View job configuration | `python scripts/parse-job.py job.waj` |
| `validate-job.py` | Validate job files | `python scripts/validate-job.py --check-stationery job.waj` |
| `list-job-targets.py` | List targets | `python scripts/list-job-targets.py --enabled job.waj` |

---

## Related Documentation

- **SKILL.md** - Main automap skill documentation
- **cli-reference.md** - AutoMap CLI options
- **ePublisher Skill** - Understanding project/stationery structure
