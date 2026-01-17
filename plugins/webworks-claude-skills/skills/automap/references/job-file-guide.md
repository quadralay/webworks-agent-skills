# Job File Guide

## Table of Contents

- [Overview](#overview)
- [Job Files vs Project Files](#job-files-vs-project-files)
- [Stationery Inheritance](#stationery-inheritance)
- [XML Structure](#xml-structure)
- [Element Reference](#element-reference)
- [Creating Job Files](#creating-job-files)
- [Target Configuration](#target-configuration)
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
- Deploy target names
- Build flags (clean, build enabled)

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
            deployTarget=""
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
            deployTarget="Production Help"
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
            deployTarget=""
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
| `path` | Yes | Relative or absolute path to Stationery | `"stationery\main.wxsp"` |

**Path Resolution**: Paths are relative to the job file's directory.

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

**Path Resolution**: Paths are relative to the job file's directory.

### `<Targets>` Element

Container for build targets. Contains one or more `<Target>` elements.

### `<Target>` Element

| Attribute | Required | Description | Values |
|-----------|----------|-------------|--------|
| `name` | Yes | Target name (for CLI `-t` parameter) | Must match Stationery format |
| `format` | Yes | Format name from Stationery | Must match exactly (case-sensitive) |
| `formatType` | Yes | Format type | `"Application"`, `"Document"` |
| `build` | Yes | Build this target by default | `"True"`, `"False"` |
| `deployTarget` | No | Deployment target name | Empty string or name |
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

---

## Creating Job Files

### Using Scripts

```bash
# 1. Parse Stationery to see available formats
python ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/parse-stationery.py stationery.wxsp

# 2a. Create interactively
python ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/create-job.py --stationery stationery.wxsp

# 2b. Or generate a template and edit
python ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/create-job.py --template --stationery stationery.wxsp > config.json
# Edit config.json...
python ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/create-job.py --config config.json --output job.waj

# 3. Validate the result
python ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/validate-job.py --check-stationery job.waj
```

### Configuration File Format

When using `create-job.py` with `--config`, use this JSON format:

```json
{
  "name": "help-en",
  "stationery": "..\\stationery\\main.wxsp",
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
      "deployTarget": "Production",
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
python ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/parse-stationery.py stationery.wxsp
```

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
python ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/validate-job.py --check-stationery job.waj || exit 1

# Run build
./scripts/automap-wrapper.sh job.waj

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
4. Run: `python ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/validate-job.py job.waj`

### Invalid Format Name

**Error**: `Format "Unknown Format" not found in Stationery`

**Solutions**:
1. Format names are case-sensitive
2. List available formats: `python ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/parse-stationery.py stationery.wxsp`
3. Update the `format` attribute to match exactly

### Document Not Found

**Warning**: `Document not found: Source\missing.md`

**Solutions**:
1. Document paths are relative to job file location
2. Check for typos in the path
3. Verify the file exists
4. Run: `python ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/validate-job.py --check-documents job.waj`

### Build Flag Ignored

**Issue**: Target builds even with `build="False"`

**Explanation**: When using `-t TargetName` on the command line, the CLI may override the build flag. Without `-t`, only targets with `build="True"` are built.

### Setting Not Applied

**Issue**: Setting override doesn't take effect

**Solutions**:
1. Verify setting name exactly matches Stationery
2. Check that setting is valid for this format
3. List available settings: `python ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/parse-stationery.py stationery.wxsp`

---

## Script Reference

| Script | Purpose | Example |
|--------|---------|---------|
| `parse-stationery.py` | Extract formats/settings | `python parse-stationery.py stationery.wxsp` |
| `create-job.py` | Create job files | `python create-job.py --stationery stationery.wxsp` |
| `parse-job.py` | View job configuration | `python parse-job.py job.waj` |
| `validate-job.py` | Validate job files | `python validate-job.py --check-stationery job.waj` |
| `list-job-targets.py` | List targets | `python list-job-targets.py --enabled job.waj` |

---

## Related Documentation

- **SKILL.md** - Main automap skill documentation
- **cli-reference.md** - AutoMap CLI options
- **ePublisher Skill** - Understanding project/stationery structure
