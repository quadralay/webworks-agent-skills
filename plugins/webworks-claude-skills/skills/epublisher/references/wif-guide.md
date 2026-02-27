# WIF (WebWorks Intermediate Format) Guide

How ePublisher adapters convert source documents into WIF, where WIF files live, and how to inspect them for debugging.

## What Is WIF

WIF is the central intermediate format in the ePublisher pipeline. All input adapters (Word, FrameMaker, XML/DITA, Markdown++) convert source documents into WIF, and all output format transforms (XSL) consume WIF as their input.

WIF has no formal schema — it is designed to evolve easily. The structure is consistent across adapters, but the XML is not validated against a fixed XSD.

## Adapter Processing: Source → Pre-WIF → WIF

Each adapter produces WIF in two stages:

1. **Pre-WIF** (`<source-name>.<ext>wif`): The adapter's intermediate file. For Markdown++, this is the expanded document with includes resolved, variables substituted, and conditions evaluated. The file extension reflects the source type:
   - `.mdwif` — Markdown++ source
   - `.fmwif` — FrameMaker source
   - `.docxwif` — Word source
   - `.ditamapwif` — DITA source

2. **WIF** (`<source-name>.wif`): The final intermediate format consumed by output transforms. Contains full style definitions, paragraph/character structure, markers, links, tables, graphics, and index entries.

Both files are generated in the same directory within the data directory hierarchy.

## Data Directory Structure

Intermediate files live in a temp directory organized by GUID-based hierarchy:

```
%TEMP%/WebWorks/ePublisher/
  <workspace-hash>/
    Data/
      <target-guid>/                    ← target-level files
        <group-guid>/
          <doc-guid>/                   ← document-level files
            <source-name>.mdwif         ← pre-WIF
            <source-name>.wif           ← final WIF
```

### How to Find the Data Directory

**Easiest method:** In Designer/Express, use the menu **View > Data Directory** to open the temp folder for the current project.

**Programmatic method:** The workspace hash is computed from the project path and project ID:

1. Concatenate `"{projectPath}:{projectID}"` (ProjectID is a GUID stored in the `.wep` file's `<Project ProjectID="...">` attribute)
2. UTF-8 encode, then SHA1 hash (20 bytes)
3. XOR-fold to 10 bytes: `xorBytes[i] = hash[i*2] ^ hash[i*2+1]`
4. Base64 encode, then replace `/`→`_`, `+`→`-`, remove `=`

### Mapping GUIDs to Project Elements

The GUIDs in the directory path correspond to IDs in the project file (`.wep`):

| Path Segment | Project File Attribute | Example |
|-------------|----------------------|---------|
| `<workspace-hash>` | Computed from project path + `ProjectID` | `VJklpVfMqfYAGQ` |
| `<target-guid>` | `<Format TargetID="...">` | `Lf3DjZlhl_A` |
| `<group-guid>` | `<Group GroupID="...">` | `QeGxWoyPnS0` |
| `<doc-guid>` | `<Document DocumentID="...">` | `fID4z7dZCjw` |

### Working Example

Given a project file:

```xml
<Project ProjectID="hMDzxVACF5I" ...>
  <Formats>
    <Format TargetName="Web Help" Name="WebWorks Reverb 2.0" TargetID="Lf3DjZlhl_A">
  </Formats>
  <Groups>
    <Group Name="Help" GroupID="QeGxWoyPnS0">
      <Document DocumentID="fID4z7dZCjw" Path="Source Docs\quantum-sync.md" />
    </Group>
  </Groups>
</Project>
```

The WIF file for `quantum-sync.md` built for the "Web Help" target is at:

```
%TEMP%/WebWorks/ePublisher/VJklpVfMqfYAGQ/Data/Lf3DjZlhl_A/QeGxWoyPnS0/fID4z7dZCjw/quantum-sync.wif
```

## WIF File Structure

A WIF file is an XML document with namespace `urn:WebWorks-Document-Schema`. Its top-level structure:

```xml
<?xml version="1.0" encoding="utf-8"?>
<Document version="1.1" xmlns="urn:WebWorks-Document-Schema">
  <Styles>
    <ParagraphStyles>...</ParagraphStyles>
    <CharacterStyles>...</CharacterStyles>
    <MarkerStyles>...</MarkerStyles>
    <TableStyles>...</TableStyles>
    <GraphicStyles>...</GraphicStyles>
    <PageStyles>...</PageStyles>
  </Styles>
  <Content>
    <!-- Paragraphs, tables, graphics, links, markers -->
  </Content>
</Document>
```

### Styles Section

Each style type defines named styles with CSS-like attributes:

```xml
<ParagraphStyle name="Heading 2">
  <Style>
    <Attribute name="font-family" value="Arial" />
    <Attribute name="font-size" value="18pt" />
    <Attribute name="font-weight" value="bold" />
    <Attribute name="toc-level" value="3" />
  </Style>
</ParagraphStyle>
```

### Content Elements

**Paragraphs** — the primary content unit:

```xml
<Paragraph id="p100003" stylename="Title 1">
  <Aliases><Alias value="quantum-sync-documentation" /></Aliases>
  <TextRun>
    <Marker id="m100006" name="Keywords">
      <TextRun id="tr100009">
        <Text value="quantum sync, documentation" />
      </TextRun>
    </Marker>
  </TextRun>
  <TextRun id="tr100018">
    <Text value="Quantum Sync Documentation" />
  </TextRun>
</Paragraph>
```

Key attributes:
- `@id` — unique element identifier (used by XSLT extensions like `GetContextRule`)
- `@stylename` — maps to a style defined in `<Styles>`
- `<Aliases>` — topic aliases for CSH and cross-references
- `<Marker>` — metadata markers (Keywords, Description, IndexMarker, PassThrough)
- `<TextRun>` — text content, optionally with character style references
- `<Link>` — cross-references and hyperlinks
- `<IndexMarker>` — index entries

### Pre-WIF vs WIF (Markdown++ Example)

**Source** (`quantum-sync.md`):
```markdown
Welcome to the $ProductName; documentation.
<!-- include:topics/overview.md -->
```

**Pre-WIF** (`quantum-sync.mdwif`) — variables resolved, includes expanded:
```markdown
Welcome to the Quantum Sync documentation.

<!-- markers:{"Keywords": "..."}; #overview -->
## Overview
[full content of topics/overview.md appears here]
```

**WIF** (`quantum-sync.wif`) — full XML with styles and structure:
```xml
<Paragraph id="p100021" stylename="Paragraph">
  <TextRun id="tr100024">
    <Text value="Welcome to the Quantum Sync documentation." />
  </TextRun>
</Paragraph>
```

## Target-Level Intermediate Files

These files are generated at the `Data/<target-guid>/` level and aggregate data across all documents:

| File | Purpose |
|------|---------|
| `files.info` | Master tracking file — all generated files, dependencies, checksums, deploy flags |
| `splits_project.xml` | Page split points across all documents |
| `links_project.xml` | Cross-document link resolution |
| `links_minimal.xml` | Minimal link data for output |
| `anchors_project.xml` | Cross-document anchor resolution |
| `locale_project.xml` | Locale strings for output |
| `uilocale_project.xml` | UI locale strings |
| `variables_project.xml` | Project-level variables |
| `images_types.xml` | Image type registry |
| `css/` | Compiled CSS (if SASS processing enabled) |
| `reverb_header.xml` | Reverb header data (Reverb formats only) |
| `reverb_footer.xml` | Reverb footer data (Reverb formats only) |

## Document-Level Intermediate Files

These files are generated at the `Data/<target-guid>/<group-guid>/<doc-guid>/` level for each document:

| File | Purpose |
|------|---------|
| `<source>.mdwif` | Pre-WIF (adapter intermediate) |
| `<source>.wif` | Final WIF |
| `behaviors_document.xml` | Behavioral rules applied to document elements |
| `behaviors_pullup.xml` | Pulled-up behaviors |
| `behaviors_splits.xml` | Split-aware behaviors |
| `behaviors_minimal.xml` | Minimal behaviors for output |
| `behaviors_finalize.xml` | Finalized behaviors |
| `splits_priorities.xml` | Page split priorities for this document |
| `splits_nameinfo.xml` | Output filename assignments |
| `toc_document.xml` | Table of contents entries |
| `index_document.xml` | Index entries |
| `links_document.xml` | Document links |
| `variables_document.xml` | Document-level variables |
| `baggage_document.xml` | Baggage file references |
| `reports_*.xml` | Report data (styles, images, links, topics, etc.) |

## files.info — Dependency Tracking

The `files.info` file at `Data/<target-guid>/files.info` is the master manifest tracking every file produced during a build. For complete details on its structure, attributes, dependency chains, and special file types, see the **files.info** section in `publish-pipeline-guide.md`.

## Debugging with WIF

### When to Inspect WIF

- **Adapter issues**: If output is missing content, has wrong styles, or has broken structure, examine the `.wif` to see what the adapter produced
- **Style mapping problems**: Check that source styles are correctly mapped in the `<Styles>` section
- **Missing markers/links**: Verify that markers, index entries, and cross-references made it into the WIF
- **Include/variable issues** (Markdown++): Compare the `.mdwif` (pre-WIF) to the source to verify includes were resolved and variables substituted

### Inspection Tips

1. **Use View > Data Directory** in Designer/Express to open the data directory
2. **WIF files are large** — use search/grep to find specific content rather than reading the entire file
3. **Compare pre-WIF to source** to verify adapter preprocessing (includes, variables, conditions)
4. **Check `files.info`** to understand the dependency chain and identify which pipeline stage produced each file
5. **Intermediate XML files** (behaviors, splits, links) are defined by `format.wwfmt` stage parameters — examine that file to understand what each intermediate file represents
