# Product Foundations

Cross-cutting knowledge that applies to all WebWorks ePublisher skills. Any skill that works with ePublisher projects, builds, or output should treat this as baseline context.

> **Maintenance note:** Some content here (XSLT 1.0 constraint, file resolver hierarchy, .wez warning) is intentionally duplicated from individual SKILL.md files so this document is self-contained. When updating shared facts, check both this file and the relevant SKILL.md `<common_mistakes>` sections.

## Platform and Runtime

- **Windows-only**: ePublisher Designer, Express, and AutoMap run only on Windows. Shell scripts execute via Git Bash or WSL.
- **XSLT 1.0 only**: Output generation uses .NET `XslCompiledTransform`. Never suggest XSLT 2.0/3.0 features in format transforms. DITA preprocessing is the sole exception (uses DITA-OT, which supports XSLT 2.0).
- **.NET runtime**: The publish engine, adapters, and CLI are .NET applications.

## Product Architecture

### Adapter → WIF → Format Pipeline

All publishing follows this flow:

1. **Adapters** convert source documents into WIF (WebWorks Intermediate Format)
2. **Format transforms** (XSLT) process WIF into final output

Four core adapters exist:
- **XML** — handles XML and DITA input
- **helper** — handles Markdown++ input
- **Word** — handles Microsoft Word input
- **FrameMaker** — handles Adobe FrameMaker input

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

The four skills form a pipeline:

1. **epublisher** — Understand project structure, targets, file resolver
2. **automap** — Execute builds via CLI
3. **reverb2** — Test and customize Reverb 2.0 output
4. **markdown-plus-plus** — Author/edit Markdown++ source documents (peer skill, used alongside any of the above)

## Debugging Fundamentals

- **Build log**: `generate.log` is written after generation to `Logs/<target-name>/` in the project directory
- **Data directory**: Intermediate files live in `%TEMP%/WebWorks/ePublisher/<workspace-hash>/Data/<target-guid>/`. Use the Designer/Express UI menu **View > Data Directory** to open it.
- **WIF files**: Adapter output (`.wif`) lives under the data directory at `<target-guid>/<group-guid>/<doc-guid>/<source-filename>.wif` — examine to diagnose adapter issues
- **XSLT logging**: Use `wwlog:Message(...)` extension functions in `.xsl` files — output appears in `generate.log`
- **Format settings**: Defined in `.fti` (Format Trait Info) files located alongside `.xsl` files in the Formats directory

## Available Output Formats

Dynamic HTML, Eclipse Help, Markdown++, Microsoft HTML Help 1.x, Oracle Help, PDF - XSL-FO, PDF, Sun JavaHelp 2.0, WebWorks Help 5.0, WebWorks Reverb, WebWorks Reverb 2.0, eBook - ePUB 2.0

`Shared` is common resources used across formats, not an output format itself.
