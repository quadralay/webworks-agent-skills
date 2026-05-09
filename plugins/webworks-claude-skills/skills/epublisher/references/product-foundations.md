# Product Foundations

Cross-cutting knowledge that applies to all WebWorks ePublisher skills. Any skill that works with ePublisher projects, builds, or output should treat this as baseline context.

## Platform and Runtime

- **Windows-only**: ePublisher Designer, Express, and AutoMap run only on Windows. Shell scripts execute via Git Bash or WSL.
- **XSLT 1.0 only**: Output generation uses .NET `XslCompiledTransform`. Never suggest XSLT 2.0/3.0 features in format transforms. DITA preprocessing is the sole exception — it uses transforms from the DITA Open Toolkit (DITA-OT) at `Adapters/xml/scripts/dita/ant/xsl/`, supporting XSLT 1.0 and 2.0. The DITA-OT version is selected via ANT template files in `Adapters/xml/scripts/dita/ant/` (e.g., `webworks-4.1.xml` corresponds to `dita-ot-4.1`).
- **XSLT extension functions**: ePublisher provides custom XSLT extension functions callable from format `.xsl` files (e.g., `wwprojext:GetFormatSetting()`, `wwprojext:GetContextRule()`, `wwlog:Message()`). Published documentation:
  - **Stable link** (requires JavaScript): `https://static.webworks.com/docs/epublisher/latest/help/#/e5d3d31c42d8d1d4`
  - **Direct file link** (works without JavaScript, may change if docs restructure): `https://static.webworks.com/docs/epublisher/latest/help/Advanced%20Customizations_%20Overrides_%20and%20Extensions/_xslt-extensions.04.1.html`
- **.NET runtime**: The publish engine, adapters, and CLI are .NET applications.

## Product Architecture

### Adapter → WIF → Format Pipeline

All publishing follows this flow:

1. **Adapters** convert source documents into WIF (WebWorks Intermediate Format)
2. **Format transforms** (XSLT) process WIF into final output

Four core adapters exist (in `Adapters/`):
- **XML** (`xml/`) — handles XML and DITA input (DITA is a subset of the XML adapter)
- **helper** (`helper/`) — handles Markdown++ input (`helper/markdown/`)
- **Word** — handles Microsoft Word input
- **FrameMaker** — handles Adobe FrameMaker input

Adapter configurations (`AdapterConfigurations` in project files) are defined in `Adapters/<input format name>/adapter.fti`. These handle edge cases with different input formats. The `helper` (Markdown++) adapter has no configurations currently.

### Format Entry Point

Each output format lives in `Formats/<format name>/` and has a `format.wwfmt` file that defines pipelines, stages, and XSLT references. This is the starting point for diagnosing any format issue.

### File Resolver Hierarchy

Files are resolved through a 4-level priority chain (highest first):
1. Target-specific: `[Project]/Targets/[TargetName]/`
2. Format-level: `[Project]/Formats/[FormatName]/`
3. Packaged defaults: `[Project]/Formats/[FormatName].base/`
4. Installation: `C:\Program Files\WebWorks\ePublisher\[version]\Formats\`

`Shared` lives parallel to the named formats in `Formats/Shared/` and follows the same hierarchy. It is not an output format itself — it is a hierarchy of common resources (XSL, SCSS, locale files, etc.) that any output format can reference. Any output format can reference resources from `Shared` as if it were a named format in the hierarchy.

## Naming and Terminology

- **Internal names differ from UI display names**: Settings in `.fti` files and project files (`.wep/.wrp/.wxsp/.waj`) use internal names. The UI display name mapping is in the product source code, not in format files.
- **Use the product's terminology**: "Targets" not "configurations," "Stationery" not "templates," "Groups" not "collections."
- **`.wez` files are installer artifacts**: They look like format sources but are zip archives used only for packaging. Always work with the extracted `Formats/<format name>/` directory.

## Trusted Sources

When this skill's references are insufficient, use these authoritative sources in order:

1. **This plugin's skill references** — always check first
2. **Vendor documentation** — `https://static.webworks.com/docs/epublisher/latest/help/`
3. **Format source files** — `.xsl`, `.fti`, `.wwfmt` files in the Formats directory
4. **Adapter source files** — files in the Adapters directory

**Never use training data to fill gaps about ePublisher, AutoMap, Reverb, or Markdown++.** These are proprietary products with limited or no public documentation indexed by training data. When unsure, read the source files or ask the user.

## Skill Workflow

The four skills in this plugin form a pipeline:

1. **epublisher** — Understand project structure, targets, file resolver
2. **markdown-integration** — Wire Markdown++ source documents into the project (variable resolution, style mapping to Stationery, condition layering, helper-adapter behavior)
3. **automap** — Execute builds via CLI
4. **reverb2** — Test and customize Reverb 2.0 output

For Markdown++ format syntax, validation, and authoring best practices, install the separate **markdown-plus-plus** skill from the [`quadralay/markdown-plus-plus`](https://github.com/quadralay/markdown-plus-plus) plugin. The **markdown-integration** skill in this plugin assumes that knowledge and focuses on the ePublisher integration layer.

## Output Localization

Locale strings for generated output (e.g., "Table of Contents", "Search", "Index") are stored in `Formats/Shared/common/locale/locales.xml`. Each format can also have its own `Transforms/locales.xml` that overrides or extends Shared locale strings. This is distinct from the .NET application `.resx` files, which are for the UI applications, not generated output. Customers commonly customize or add locale strings in `locales.xml`.

## Debugging Fundamentals

- **Build log**: `generate.log` is written after generation to `Logs/<target-name>/` in the project directory
- **Data directory**: Intermediate files live in `%TEMP%/WebWorks/ePublisher/<workspace-hash>/Data/<target-guid>/`. Use the Designer/Express UI menu **View > Data Directory** to open it.
- **WIF files**: Adapter output (`.wif`) lives under the data directory at `<target-guid>/<group-guid>/<doc-guid>/<source-filename>.wif` — examine to diagnose adapter issues
- **XSLT logging**: Use `wwlog:Message(...)` extension functions in `.xsl` files — output appears in `generate.log`
- **Intermediate XML files**: Behavior, split, link, TOC, and index XML files in the Data directory are defined by `format.wwfmt` stage parameters — examine them to trace how content flows through the pipeline
- **Format settings**: Defined in `.fti` (Format Trait Info) files located alongside `.xsl` files in the Formats directory
- **Visual Studio debugger**: Can attach to step through transforms, but only practical for extreme development cases

## Testing Format and Adapter Changes

To validate changes to XSL transforms or adapters, use a golden output comparison workflow:

1. Generate output to produce the current baseline
2. Manually modify the output to produce the desired result, rename `Output` to `Output.golden`
3. Optionally, rename the unmodified output to `Output.baseline` (the "before" state)
4. Modify XSL files and/or adapter code, regenerate
5. Compare `Output` to `Output.golden` (or `Output.baseline`) to verify the changes produce the desired result

## Technical Support

Support cases are filed at `https://www.webworks.com/Support/`. Users must have an active Contract ID (GUID format: `XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX`) to submit a case. The Contract ID can be found in the product UI via **Help > License Keys... > "Register" button**.

## Available Output Formats

Dynamic HTML, Eclipse Help, Markdown++, Microsoft HTML Help 1.x, Oracle Help, PDF - XSL-FO, PDF, Sun JavaHelp 2.0, WebWorks Help 5.0, WebWorks Reverb, WebWorks Reverb 2.0, eBook - ePUB 2.0

`Shared` is common resources used across formats, not an output format itself.
