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
| **automap** | After understanding project structure, use automap to execute builds |
| **reverb2** | After building Reverb output, use reverb2 skill to test and customize |

**Typical workflow:**
1. Use **epublisher** to understand project files and targets
2. Use **automap** to build specific targets
3. Use **reverb2** to test and customize Reverb 2.0 output

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

Copy format files from installation to project with structure validation:

```bash
python scripts/copy-customization.py --source <install-file> --destination <project-file>
```

Validates parallel folder structure and creates directories as needed.
</scripts>

<references>

## Reference Files

- `product-foundations.md` - Cross-cutting product knowledge (architecture, platform, debugging)
- `file-resolver-guide.md` - Complete file resolution hierarchy
- `project-parsing-guide.md` - Detailed project file structure
- `user-interaction-patterns.md` - Disambiguating user intent (query vs. creation)
- `version-compatibility.md` - Supported versions and breaking changes
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

**`.wez` files are not format sources.** They look like format archives but are installer-only packaging artifacts. Always work with the extracted `Formats/<format name>/` directory, never `.wez` files.

**XSLT 2.0 features will fail.** ePublisher uses .NET `XslCompiledTransform` (XSLT 1.0 only). Never suggest `xsl:for-each-group`, `xsl:analyze-string`, or other 2.0/3.0 features in format transforms. The sole exception is DITA preprocessing, which uses DITA-OT and supports XSLT 2.0.

**UI names differ from internal names.** When users reference a setting by its display name (e.g., "Generate toolbar"), the corresponding internal name in `.fti` and project files is different (e.g., `toolbar-generate`). Do not guess the mapping — search `.fti` files or ask the user.

</common_mistakes>

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
