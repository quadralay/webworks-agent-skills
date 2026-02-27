# Publish Pipeline Guide

How the ePublisher engine transforms source documents into output using the pipeline architecture defined in `format.wwfmt`.

## format.wwfmt — The Orchestration Blueprint

Each output format has a `format.wwfmt` file at `Formats/<format name>/format.wwfmt`. This XML file defines:

- **Capabilities** — format family, supported HTML/CSS/XHTML versions, merge behavior
- **TaskGroups** — UI-visible tasks (Generate, Reports) with entry points linking to pipeline outputs
- **Pipelines** — the execution graph of XSL transforms that convert WIF to final output

```xml
<Format version="1.0" xmlns="urn:WebWorks-Engine-Format-Schema">
  <Capabilities>
    <Capability name="family" value="XHTML 1.0" />
    <Capability name="merge-hierarchy" value="toc" />
  </Capabilities>
  <TaskGroups>
    <TaskGroup name="generate">
      <Task name="Generate">
        <EntryPoint scope="document" type="page:output" category="pages" />
        <EntryPoint scope="project" type="connect:entry" category="merge" />
      </Task>
    </TaskGroup>
  </TaskGroups>
  <Pipelines>
    <!-- Pipeline definitions -->
  </Pipelines>
</Format>
```

### TaskGroups and EntryPoints

TaskGroups define what the UI shows as available actions. Each `<Task>` has `<EntryPoint>` elements that reference pipeline output types, telling the engine which files to present in the UI and at what scope:

- `scope="document"` — per-document files (HTML pages)
- `scope="group"` — per-group files (group-level reports)
- `scope="project"` — project-wide files (entry point, merged output)

The `category` attribute classifies files for deployment (pages, navigation, merge, report, etc.).

## Pipeline Execution Model

### Dependency-Driven Execution

Pipelines declare dependencies on other pipelines using `<Depends>` elements:

```xml
<Pipeline name="Page">
  <Depends pipeline="Locale" />
  <Depends pipeline="Splits" />
  <Depends pipeline="Behaviors" />
  <Depends pipeline="Links" />
  <Depends pipeline="TOC" />
  <!-- ... more dependencies -->
</Pipeline>
```

The engine builds a dependency graph and executes pipelines when all their dependencies are fulfilled. Independent pipelines (no dependencies) can execute in parallel. Execution continues until all pipelines complete.

### Stages Within a Pipeline

Each pipeline contains sequential `<Stage>` elements. Stages execute in order, with each stage typically being an XSL transform:

```xml
<Pipeline name="TOC">
  <Depends pipeline="Locale" />
  <Depends pipeline="Links" />
  <Depends pipeline="Variables" />

  <Stage type="xsl" action="wwtransform:common/toc/document.xsl">
    <Parameter name="ParameterDependsType" value="engine:wif" />
    <Parameter name="ParameterType" value="toc:document" />
    <Parameter name="ParameterLocaleType" value="locale:project" />
  </Stage>
  <Stage type="xsl" action="wwtransform:common/toc/collapse.xsl">
    <Parameter name="ParameterDependsType" value="toc:document" />
    <Parameter name="ParameterType" value="toc:collapse" />
  </Stage>
  <!-- more stages... -->
</Pipeline>
```

### Data Flow: Parameters

Parameters connect stages by referencing typed intermediate files:

| Parameter | Purpose |
|-----------|---------|
| `ParameterDependsType` | **Primary input** — the file type this stage consumes. `engine:wif` means the adapter-generated WIF file. |
| `ParameterType` | **Output** — the file type this stage produces. Becomes the input for the next stage or another pipeline. |
| `ParameterLocaleType` | Locale strings file |
| `ParameterUILocaleType` | UI locale strings file |
| `ParameterLinksType` | Cross-document links |
| `ParameterSplitsType` | Page split data |
| `ParameterBehaviorsType` | Behavior rules |
| `ParameterProjectVariablesType` | Project variables |
| `ParameterSegmentsType` | Content segments |
| `ParameterTOCDataType` | Table of contents data |
| `ParameterPageTemplateURI` | HTML template (`.asp` file) |
| `ParameterCategory` | File category for deployment grouping |
| `ParameterDeploy` | Whether the output should be deployed to the output directory |

**Data flow example** (TOC pipeline):
```
engine:wif → toc:document → toc:collapse → toc:group → toc:project → toc:resolve
```

Each typed value corresponds to an XML file written in the Data directory. The engine tracks these in `files.info`.

### XSL Path Resolution

Stage `action` attributes use path prefixes to locate XSL files:

| Prefix | Resolves To | Example |
|--------|-------------|---------|
| `wwtransform:` | `Formats/Shared/` | `wwtransform:common/toc/document.xsl` → `Formats/Shared/common/toc/document.xsl` |
| `wwformat:` | `Formats/<format name>/` | `wwformat:Transforms/pages.xsl` → `Formats/WebWorks Reverb 2.0/Transforms/pages.xsl` |

This separation allows shared logic (common across all formats) to live in `Shared/` while format-specific transforms live in the format directory.

### Processing Scope

Stages operate at different scopes based on what they process:

- **Document-level**: Processes each source document independently (e.g., `behaviors_document.xml`, `toc_document.xml`)
- **Group-level**: Aggregates document-level outputs within a group (e.g., `toc_group.xml`, `baggage_group.xml`)
- **Project-level**: Aggregates across all groups (e.g., `toc_project.xml`, `links_project.xml`, `locale_project.xml`)

The naming convention in `ParameterType` values reflects this: `toc:document` → `toc:group` → `toc:project` → `toc:resolve`.

## Pipeline Inventory (WebWorks Reverb 2.0)

### Core Processing Pipelines

| Pipeline | Dependencies | Purpose |
|----------|-------------|---------|
| **Locale** | *(none)* | Loads locale strings from `locales.xml` for generated output |
| **CompanyInfo** | *(none)* | Loads company information |
| **CSS** | *(none)* | Loads CSS configuration from `.fti` |
| **SASS** | *(none)* | Compiles SCSS to CSS, copies font assets (Font Awesome) |
| **ImageTypes** | *(none)* | Builds image format registry from `.fti` |

### Document Analysis Pipelines

| Pipeline | Dependencies | Purpose |
|----------|-------------|---------|
| **DocumentBehaviors** | *(WIF)* | Applies behavior rules to document elements (document → pullup) |
| **DocumentSplits** | DocumentBehaviors | Calculates page split priorities and collapse points |
| **Behaviors** | DocumentBehaviors, DocumentSplits | Finalizes behaviors with split awareness (splits → finalize → minimal) |
| **Baggage** | *(WIF)* | Collects baggage files (referenced assets) at document, group, and filter levels |

### Resolution Pipelines

| Pipeline | Dependencies | Purpose |
|----------|-------------|---------|
| **Splits** | Baggage, Behaviors, DocumentSplits, ImageTypes, Locale, SASS | Resolves page splits: names → uniquenames → project |
| **Copy** | Splits | Copies static format files to output |
| **Segment** | Splits | Segments content for output pages |
| **Links** | Splits, Segment | Resolves cross-document links (document → group → project → minimal) |
| **Variables** | Splits | Resolves project variables |

### Content Generation Pipelines

| Pipeline | Dependencies | Purpose |
|----------|-------------|---------|
| **TOC** | Locale, Links, Variables | Builds table of contents (document → collapse → group → project → resolve) |
| **Index** | Locale, Links, Variables | Builds index (document → group → combine → sections → hierarchy → resolve → output) |
| **Styles** | Splits | Generates per-document CSS |
| **Image** | Splits | Processes images (by-reference, media, converted images, long descriptions) |
| **PDF** | Splits, TOC | Generates PDF files (document → group → project level) |
| **Splash** | Locale, Variables | Generates splash/landing page |
| **NotFound** | Locale, Variables | Generates 404 page |

### Output Assembly Pipelines

| Pipeline | Dependencies | Purpose |
|----------|-------------|---------|
| **Page** | Locale, Copy, Splits, Behaviors, Variables, Links, Styles, TOC, Image, PDF, Segment | **Main output** — generates HTML pages (popups, wrappers, pages, knowledge-base pages, landmarks) |
| **Connect** | Locale, Splash, Splits, TOC, Index, Page, Copy | Generates entry point, search page, header/footer, parcel data, API files |
| **Search** | Connect | Builds full-text search index from content and baggage files |
| **URL-Maps** | Locale, Connect, Links, Copy | Generates `url_maps.xml` and `sitemap.xml` |

### Report Pipelines

All report pipelines follow the same pattern: document-level → group-level → printable variants.

| Pipeline | Dependencies |
|----------|-------------|
| **Report-Styles** | Locale, Segment, Links |
| **Report-Links** | Locale, Segment, Links |
| **Report-Accessibility** | Locale, Links |
| **Report-Filenames** | Locale, Splits, Links |
| **Report-Topics** | Locale, Links |
| **Report-Images** | Locale, Splits, Links |
| **Report-Conditions** | Locale |
| **Report-Baggage-Files** | Locale, Splits, Baggage |

## files.info — Dependency Tracking

The `files.info` file at `Data/<target-guid>/files.info` is the master manifest tracking every file produced during a build. It enables incremental builds by recording dependencies and checksums.

### Structure

```xml
<Files version="1.0" xmlns="urn:WebWorks-Engine-Files-Schema">
  <!-- Location references -->
  <File path="..." type="location:filesinfopath" />
  <File path="..." type="location:outputpath" />

  <!-- Generated files with dependencies -->
  <File path="...quantum-sync.wif"
        type="engine:wif"
        checksum="639077517772509816:73338"
        groupID="QeGxWoyPnS0"
        documentID="fID4z7dZCjw"
        pipeline=""
        actionchecksum="wIhWZB/nD8PuMWkfiULlROyY13o="
        deploy="">
    <Depends path="...quantum-sync.mdwif"
             checksum="639077517760986849:18546"
             groupID="QeGxWoyPnS0"
             documentID="fID4z7dZCjw" />
  </File>
</Files>
```

### File Attributes

| Attribute | Purpose |
|-----------|---------|
| `type` | File type identifier (matches `ParameterType` values from `format.wwfmt`) |
| `checksum` | Timestamp and file size for change detection (format: `timestamp:size`) |
| `projectchecksum` | Project-level checksum for detecting project file changes |
| `groupID` | Group GUID this file belongs to (empty for project-level files) |
| `documentID` | Document GUID this file belongs to (empty for group/project-level files) |
| `pipeline` | Which pipeline produced this file (e.g., `Locale`, `DocumentBehaviors`, `SASS`) |
| `actionchecksum` | Hash of the XSL transform action — detects when the transform itself changes |
| `category` | Deployment category (pages, navigation, merge, report, etc.) |
| `deploy` | `"true"` if this file should be deployed to the output directory |

### Dependency Chain

`<Depends>` elements record which files a given file depends on. This enables:

- **Incremental builds**: Only re-run stages when inputs have changed
- **Cache invalidation**: If a source file changes, all dependent files are regenerated
- **Source tracing**: Track any output file back to its source documents

Example dependency chain from `files.info`:
```
quantum-sync.md (source)
  → quantum-sync.mdwif (pre-WIF, pipeline: adapter)
    → quantum-sync.wif (WIF, pipeline: adapter)
      → behaviors_document.xml (pipeline: DocumentBehaviors)
        → behaviors_pullup.xml (pipeline: DocumentBehaviors)
          → splits_priorities.xml (pipeline: DocumentSplits)
            → behaviors_splits.xml (pipeline: Behaviors)
              → behaviors_finalize.xml (pipeline: Behaviors)
                → behaviors_minimal.xml (pipeline: Behaviors)
```

### Special File Types

| Type Prefix | Purpose |
|-------------|---------|
| `location:*` | Reference paths (not actual files) — `filesinfopath`, `outputpath` |
| `engine:wif` | Adapter-generated WIF file |
| `engine:conversion` | Adapter pre-WIF file (`.mdwif`, `.docxwif`, etc.) |
| `behaviors:*` | Behavior analysis files (document, pullup, splits, finalize, minimal) |
| `splits:*` | Page splitting files (priorities, collapse, names, uniquenames, project) |
| `baggage:*` | Baggage (asset) tracking files |
| `toc:*` | Table of contents files |
| `links:*` | Link resolution files |
| `locale:*` / `uilocale:*` | Localization files |
| `page:*` | Generated HTML pages (popup, wrapper, output) |
| `connect:*` | Entry point and navigation files |
| `search:*` | Search index files |
| `sass:css` | Compiled CSS from SCSS |
| `reports:*` | Report output files |
| `pdf:*` | PDF output files |

## Practical Usage

### Diagnosing Pipeline Issues

1. **Identify which pipeline is failing** — check `generate.log` in `Logs/<target-name>/` for error messages mentioning specific XSL files
2. **Find the pipeline** — look up the XSL file in `format.wwfmt` to identify which pipeline and stage
3. **Check dependencies** — verify the pipeline's dependent pipelines completed successfully
4. **Inspect intermediate files** — examine the typed XML files in the Data directory that serve as inputs to the failing stage

### Tracing Output to Source

To understand how a specific output file was generated:

1. Open `files.info` and search for the output file path
2. Follow the `<Depends>` chain backward to the source document
3. The `pipeline` attribute on each `<File>` tells you which pipeline stage produced it
4. The `type` attribute maps to `ParameterType` values in `format.wwfmt`

### Understanding the XSL Transform Chain

To find which XSL files are involved in generating a specific output type:

1. Search `format.wwfmt` for the `ParameterType` value (e.g., `page:output`)
2. The containing `<Stage>` shows the XSL file (`action` attribute)
3. Trace backward through `ParameterDependsType` to find upstream stages
4. The pipeline's `<Depends>` elements show which other pipelines must complete first
