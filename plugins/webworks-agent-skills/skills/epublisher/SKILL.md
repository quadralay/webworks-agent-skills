---
name: epublisher
description: >
  AUTHORITATIVE REFERENCE for WebWorks ePublisher projects. Use when working with
  .wep/.wrp/.wxsp project files, understanding project structure, file resolver
  hierarchy, target configurations, or source document groups.
---

<objective>

# epublisher

Core knowledge about WebWorks ePublisher projects, file structure, and conventions. This skill provides foundational understanding without automation or format-specific details.

**Do not use training data for ePublisher.** This is proprietary software — training data is likely absent or inaccurate. Use only this skill's references and vendor documentation (`static.webworks.com`). Key constraints: Windows-only platform, XSLT 1.0 only (never XSLT 2.0), internal names in project/format files differ from UI display names.
</objective>

<overview>

## Overview

WebWorks ePublisher transforms source documents (Word, FrameMaker, DITA, Markdown) into multiple output formats (Reverb, PDF, CHM, etc.) using a project-based workflow.

**User intent disambiguation:** Before creating or modifying project elements, consult `references/user-interaction-patterns.md` to distinguish queries from creation requests. When in doubt, treat as a query first.
</overview>

<related_skills>

## Related Skills

This skill provides foundational knowledge used by other skills in this plugin:

| Skill | When to Use |
|-------|-------------|
| **markdown-integration** | When source documents are Markdown++; covers variable resolution, style mapping to Stationery, and per-target conditions |
| **automap** | After understanding project structure, use automap to execute builds |
| **reverb2** | After building Reverb output, use reverb2 skill to test and customize |

**External:**

- **markdown-plus-plus** ([`quadralay/markdown-plus-plus`](https://github.com/quadralay/markdown-plus-plus)) — Markdown++ format syntax, validation, and authoring best practices. Install separately when working with Markdown++ source documents.

**Typical workflow:**
1. Use **epublisher** to understand project files and targets
2. Use **markdown-integration** when wiring Markdown++ sources into the project
3. Use **automap** to build specific targets
4. Use **reverb2** to test and customize Reverb 2.0 output

</related_skills>

<key_concepts>

## Key Concepts

### Project Structure

An ePublisher project (`.wep` file) contains:
- **Targets**: Named output configurations (e.g., "WebWorks Reverb 2.0", "PDF")
- **Groups**: Collections of source documents
- **Documents**: Individual source files within groups
- **FormatSettings**: Configuration values for each target

### File Resolver Hierarchy

ePublisher resolves files through a 4-level hierarchy (highest to lowest priority):

1. **Target-Specific**: `[Project]/Targets/[TargetName]/`
2. **Format-Level**: `[Project]/Formats/[FormatName]/`
3. **Packaged Defaults**: `[Project]/Formats/[FormatName].base/`
4. **Installation**: `C:\Program Files\WebWorks\ePublisher\[version]\Formats\`

**For complete details, see:** references/file-resolver-guide.md

### Stationery and Using a Project as a Stationery

A **Stationery** (`.wxsp`) is a standalone, distributable project that bundles its format configuration *and* `<format>.base` snapshots, so its transforms resolve from those bundled snapshots. AutoMap jobs (`.waj`) traditionally reference a `.wxsp` and stage a fresh project from it on each build.

A Designer `.wep` carries **no** `<format>.base` snapshots, so its transforms resolve from the Designer installation (resolver level 4) instead. Because of that, AutoMap can use a `.wep` *directly* as a stationery via `useAsStationery="True"` on the job's `<Project>` element (ePublisher 2026.1+), skipping the manual "Save As Stationery" step. The synchronization engine is extension-agnostic: it can stage and synchronize against a `.wxsp`, `.wep`, or `.wrp` origin.

Whether a project carries `.base` snapshots follows the **origin it was staged from**, not its own extension: a `.wrp` staged from a `.wxsp` bundles them, a `.wrp` staged from a `.wep` does not. See `references/file-resolver-guide.md`.

Opening a standalone `.wxsp` is not a project-open operation. As of 2026.1, double-clicking one, passing it on the command line, or selecting it in **File > Open** starts the New Project from Stationery flow with that Stationery pre-selected, in both Designer and Express.

**For job-file usage of `useAsStationery`, see the automap skill's `references/job-file-guide.md`. For `<Origin>` and synchronization semantics, see `references/project-parsing-guide.md`.**

### Designer and Express Project Types (2026.1)

`.wep` and `.wrp` share one file format. The difference is **origin, not product**: a `.wep` holds a design of its own, while a `.wrp` carries an `<Origin>` and imports its design from there.

As of ePublisher 2026.1 the products no longer partition the project types. Designer opens, builds, synchronizes, and deploys `.wrp` projects, presenting the Express experience in that window — Document Manager, the synchronization prompt, no Style Designer, no Preview — and listing `.wep` and `.wrp` together under one **ePublisher Project Files** entry in its Open dialog. Designer also gains:

- **File > New Project from Stationery...** — creates a `.wrp` from a `.wxsp` *or* a `.wep`. It is a separate command because Designer's **New Project** creates a Stationery *design* project.
- **File > Save as Express Project...** — creates a `.wrp` linked back to the current `.wep`, giving a master/satellite arrangement (one design seat, any number of linked projects that pick up changes through the synchronization prompt).

Design authoring stays exclusive to Designer: Style Designer, the Preview window, Stationery design projects, Save as Stationery, and Save as Express Project.

Do not assert the pre-2026.1 split — "`.wrp` can only be opened in Express", "Designer cannot create a project from Stationery", "only Express synchronizes" are all false as of 2026.1, and all true before it. Check the version before recommending any of this; see `references/version-compatibility.md`.

### Deploy Destinations and Deploy Scope (new in 2026.1)

Output destinations (Target Settings **Deploy to** / Edit > **Deploy Destinations**) are named definitions stored per user, per machine (`deploy.prefs`) and shared across projects and across Designer, Express, and AutoMap. As of ePublisher 2026.1: destinations can be **Folder** or **Amazon S3** (bucket/region/named credential profile/CloudFront distribution — no stored secrets; dry run supported); each target also declares a **Deploy** scope — Everything (complete site), Groups (content only), or Shell (site files only) — which powers federated parcel composition in WebWorks Reverb 2.0 (the field is disabled for formats without the capability). Deployments never delete outside their own scope slice, and Clean remains AutoMap-only. For the federation workflow, `.wacj` composition jobs, and inline destination definitions, see the automap skill's `references/composition-jobs.md`; for version gating, `references/version-compatibility.md`.

### Project File Format

The `.wep` file is XML containing target definitions:

```xml
<Format Name="WebWorks Reverb 2.0"
        TargetID="abc123"
        TargetName="Help Output">
  <OutputDirectory>Output\Help</OutputDirectory>
  <FormatConfiguration>
    <FormatSetting Name="toolbar-generate" Value="true"/>
    <FormatSetting Name="header-generate" Value="false"/>
  </FormatConfiguration>
</Format>
```

### Source Document Groups

Documents are organized into groups within projects:

```xml
<Group Name="User Guide" GroupID="grp123">
  <Document Name="chapter1.docx" DocumentID="doc456"/>
  <Document Name="chapter2.docx" DocumentID="doc789"/>
</Group>
```

### Format Definition and Pipeline

Each output format has a `format.wwfmt` file that defines the complete publish pipeline — a dependency graph of XSL transform stages that convert WIF to final output. This is the starting point for diagnosing any format or output issue.

**For complete details, see:** references/publish-pipeline-guide.md
</key_concepts>

<scripts>

## Scripts

### parse-targets.py

Extract target information from a project file:

```bash
python scripts/parse-targets.py <project-file>
```

Returns JSON with target names, IDs, formats, and output directories.

### manage-sources.sh

List and manage source document groups:

```bash
bash scripts/manage-sources.sh <project-file> [list|add|remove]
```

### copy-customization.py

Copy installation files to project with structure validation:

```bash
python scripts/copy-customization.py --source <install-file> --destination <project-file>
```

Validates parallel folder structure and creates directories as needed.

### resolve-version-root.py

Resolve ePublisher VersionRoot for installation lookups:

```bash
python scripts/resolve-version-root.py [--project-file <project.wep>] [--version <2024.1>]
```

Returns JSON with versionRoot path, component directories, and availability flags.
</scripts>

<references>

## Reference Files

- `file-resolver-guide.md` - Complete file resolution hierarchy
- `format-traits-guide.md` - Trait types, reading/writing in project files, accessing in XSL, global vs per-target scope, Golden Test recipe, Diffable HTML Output recipe
- `FormatTraitInfoStrings.resx` - Complete UI display name to internal name mapping (English)
- `product-foundations.md` - Cross-cutting product knowledge (architecture, platform constraints, debugging)
- `project-parsing-guide.md` - Detailed project file structure, `<Origin>` and synchronization semantics, Save as Express Project
- `publish-pipeline-guide.md` - Pipeline architecture (`format.wwfmt`), stage execution, `files.info` tracking, data flow
- `user-interaction-patterns.md` - Disambiguating user intent (query vs. creation)
- `version-compatibility.md` - Supported versions and breaking changes
- `wif-guide.md` - WIF intermediate format, data directory structure, debugging with intermediate files
</references>

<common_tasks>

## Common Tasks

### Find all targets in a project

```bash
python scripts/parse-targets.py /path/to/project.wep
```

### Locate format customization files

Check the file resolver hierarchy:
1. First: `[Project]/Formats/[FormatName]/`
2. Then: `[Project]/Formats/[FormatName].base/`
3. Finally: Installation directory

### Identify source documents

```bash
bash scripts/manage-sources.sh /path/to/project.wep list
```
</common_tasks>

<common_mistakes>

## Common Mistakes

For platform-level gotchas (.wez files, XSLT 1.0 constraint, UI name mapping), see `references/product-foundations.md`.

</common_mistakes>

<troubleshooting>

## Troubleshooting

### "No targets found in project"

**Cause:** Project file doesn't contain `<Format>` elements.

**Solutions:**
1. Verify file is a valid .wep/.wrp/.wxsp file
2. Check if project was created in a compatible ePublisher version
3. Open the project in ePublisher Designer or Express to verify structure — as of 2026.1 Designer opens both `.wep` and `.wrp`

### "Project file not found"

**Cause:** Path is incorrect or file doesn't exist.

**Solutions:**
1. Use absolute Windows paths (e.g., `C:\projects\my-proj\my-proj.wep`)
2. Check for spaces in path (quote the path)
3. Verify file extension is .wep, .wrp, or .wxsp

### "Invalid project file extension"

**Cause:** File is not a recognized ePublisher project type.

**Solutions:**
1. Use .wep (WebWorks ePublisher Project)
2. Use .wrp (WebWorks ePublisher Express Project)
3. Use .wxsp (WebWorks ePublisher Stationery Project)

</troubleshooting>

<success_criteria>

## Success Criteria

- Project file parsed successfully
- Targets and formats extracted
- Source documents listed
- File resolver paths identified correctly
</success_criteria>
