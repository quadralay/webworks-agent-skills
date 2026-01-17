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
</objective>

<overview>

## Overview

WebWorks ePublisher transforms source documents (Word, FrameMaker, DITA, Markdown) into multiple output formats (Reverb, PDF, CHM, etc.) using a project-based workflow.
</overview>

<related_skills>

## Related Skills

This skill provides foundational knowledge used by other skills in this plugin:

| Skill | When to Use |
|-------|-------------|
| **automap** | After understanding project structure, use automap to execute builds |
| **reverb** | After building Reverb output, use reverb skill to test and customize |

**Typical workflow:**
1. Use **epublisher** to understand project files and targets
2. Use **automap** to build specific targets
3. Use **reverb** to test and customize Reverb 2.0 output

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
</key_concepts>

<scripts>

## Scripts

### parse-targets.sh

Extract target information from a project file:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/epublisher/scripts/parse-targets.sh <project-file>
```

Returns JSON with target names, IDs, formats, and output directories.

### manage-sources.sh

List and manage source document groups:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/epublisher/scripts/manage-sources.sh <project-file> [list|add|remove]
```

### copy-customization.py

Copy format files from installation to project with structure validation:

```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/epublisher/scripts/copy-customization.py --source <install-file> --destination <project-file>
```

Validates parallel folder structure and creates directories as needed.
</scripts>

<references>

## Reference Files

- `file-resolver-guide.md` - Complete file resolution hierarchy
- `project-parsing-guide.md` - Detailed project file structure
- `user-interaction-patterns.md` - UX patterns for ePublisher workflows
- `version-compatibility.md` - Supported versions and breaking changes
</references>

<common_tasks>

## Common Tasks

### Find all targets in a project

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/epublisher/scripts/parse-targets.sh /path/to/project.wep
```

### Locate format customization files

Check the file resolver hierarchy:
1. First: `[Project]/Formats/[FormatName]/`
2. Then: `[Project]/Formats/[FormatName].base/`
3. Finally: Installation directory

### Identify source documents

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/epublisher/scripts/manage-sources.sh /path/to/project.wep list
```
</common_tasks>

<troubleshooting>

## Troubleshooting

### "No targets found in project"

**Cause:** Project file doesn't contain `<Format>` elements.

**Solutions:**
1. Verify file is a valid .wep/.wrp/.wxsp file
2. Check if project was created in a compatible ePublisher version
3. Open project in ePublisher Administrator to verify structure

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
2. Use .wrp (WebWorks ePublisher Report Project)
3. Use .wxsp (WebWorks ePublisher Stationery Project)

</troubleshooting>

<success_criteria>

## Success Criteria

- Project file parsed successfully
- Targets and formats extracted
- Source documents listed
- File resolver paths identified correctly
</success_criteria>
