# Format Traits Guide

How to look up, read, write, and access format trait values (Settings, Options, and Properties) across ePublisher project files, `.fti` definitions, and XSL transforms.

## Trait Types

ePublisher has three types of format traits, each serving a different purpose:

| Type | Scope | Defined In | Used In Project File As | Accessed In XSL Via |
|------|-------|-----------|------------------------|---------------------|
| **Setting** | Global to the target | `.fti` `<Setting>` | `<FormatSetting>` | `wwprojext:GetFormatSetting()` |
| **Option** | Per style rule (Paragraph, Character, Table, Page, Marker, Graphic) | `.fti` `<Option>` | `<Option>` inside a `<Rule>` | `GetContextRule()` then `wwproject:Options/wwproject:Option` |
| **Property** | Per style rule (CSS-like properties) | `.fti` `<Property>` | `<Property>` inside a `<Rule>` | `GetContextRule()` then `wwproject:Properties/wwproject:Property` |

**Key distinction:** Settings are target-wide configuration. Options and Properties are per-style-rule — they apply to specific Paragraph, Character, Table, Page, Marker, or Graphic styles as configured by the user.

## The Name Mapping Problem

**Internal names differ from UI display names.** The `.fti` files and project files use internal names (e.g., `connect-browser-tab-title`). The ePublisher Designer/Express UI shows display names (e.g., "Browser Tab Title"). The mapping between them is defined in `FormatTraitInfoStrings.resx` in the product source code, not in the format files.

**When a user refers to a setting by its UI name**, you must translate to the internal name before reading or writing project files. Search the `.resx` file in this directory for the mapping, or search `.fti` files by keyword for edge cases.

## How Traits Are Defined (.fti Files)

Format Trait Info (`.fti`) files live alongside `.xsl` transform files in `Formats/<format>/Transforms/`. ePublisher discovers them by traversing the `.xsl` references in `format.wwfmt` and looking for `.fti` files in the same directories.

### Settings

```xml
<Setting name="connect-browser-tab-title" group="connect" default="">
  <SettingClass name="string" />
</Setting>
```

### Options (inside RuleTraits)

```xml
<RuleTraits category="Paragraph">
  <Options>
    <Option name="use-numbering" group="options" default="true">
      <OptionClass name="boolean" />
    </Option>
    <Option name="dropdown" group="options" default="continue">
      <OptionClass name="dropdown" />
    </Option>
  </Options>
</RuleTraits>
```

### Properties (inside RuleTraits)

```xml
<RuleTraits category="Page">
  <Properties>
    <Property name="breadcrumbs-separator" group="navigation" default=" : ">
      <PropertyClass name="breadcrumbs-separator" />
    </Property>
  </Properties>
</RuleTraits>
```

The `category` attribute determines which style types this trait applies to: `Paragraph`, `Character`, `Table`, `Page`, `Marker`, or `Graphic`.

## How Traits Appear in Project Files

### FormatSettings (target-wide)

In a `.wwfmt` target definition:

```xml
<Target Name="WebWorks Reverb 2.0" ...>
  <FormatSettings>
    <FormatSetting Name="connect-browser-tab-title" Value="My Help System" />
    <FormatSetting Name="company-copyright" Value="© 2025 WebWorks" />
    <FormatSetting Name="encoding" Value="UTF-8" />
  </FormatSettings>
</Target>
```

In a `.wep` project file, the same `<FormatSettings>` wrapper appears inside a per-target `<FormatConfiguration>`:

```xml
<FormatConfiguration TargetID="rvbDsgn001">
  <FormatSettings>
    <FormatSetting Name="file-processing-pretty-print" Value="true" />
    <FormatSetting Name="connect-browser-tab-title" Value="My Help System" />
  </FormatSettings>
</FormatConfiguration>
```

The `<FormatSettings>` wrapper is required. Bare `<FormatSetting>` elements placed as direct children of `<FormatConfiguration>` are silently ignored — the build succeeds but the values do not take effect.

### Options and Properties (per style rule)

```xml
<Rules Type="Paragraph" Default="{WWDefaultRule}">
  <Rule Key="Heading 1">
    <Options>
      <Option Name="split-priority" Value="1" Source="Explicit" />
      <Option Name="toc-level" Value="1" Source="Explicit" />
    </Options>
    <Properties>
      <Property Name="font-size" Value="18pt" Source="Explicit" />
    </Properties>
  </Rule>
</Rules>
```

The style category (`Paragraph`, `Character`, `Table`, `Page`, `Marker`, or `Graphic`) lives on the parent `<Rules>` element as `Type=`, not on individual `<Rule>` elements. The `Default=` attribute names the prototype rule that supplies inherited defaults — see [The `{WWDefaultRule}` prototype rule](#the-wwdefaultrule-prototype-rule) below. Each `<Rule>` is identified by `Key=` (a style name string, or the `{WWDefaultRule}` literal for the prototype).

`Source="Explicit"` is required on every `<Option>` and `<Property>` — omitting it causes ePublisher to reject the project at load time with `"The specified file is not a valid ePublisher project"`. Use `Source="Inherit"` only when explicitly recording an inherited value.

### The `{WWDefaultRule}` prototype rule

The literal string `{WWDefaultRule}` (braces included) is the internal `Key` for the row the ePublisher Designer UI displays as `[Prototype]`. Setting Options or Properties on `<Rule Key="{WWDefaultRule}">` applies that value as the default for every style in the category — every Paragraph style inherits from the Paragraph prototype, every Page style from the Page prototype, and so on.

The `Default="{WWDefaultRule}"` attribute on the parent `<Rules>` element ties the block to its prototype rule. ePublisher writes this exact attribute pair on every `<Rules>` block it generates; project files that omit `Default=` will not load.

```xml
<Rules Type="Paragraph" Default="{WWDefaultRule}">
  <Rule Key="{WWDefaultRule}">
    <Options>
      <Option Name="split-priority" Value="1" Source="Explicit" />
    </Options>
  </Rule>
  <Rule Key="Heading 1">
    <!-- Heading 1 inherits split-priority=1 from the prototype unless overridden here -->
  </Rule>
</Rules>
```

## Global vs per-target style overrides

Trait values can be configured at two scopes inside a `.wep`. Both scopes use the same `<Rules>` / `<Rule>` shape shown above.

- **`<GlobalConfiguration>`** carries traits that apply to every target in the project. Use this for project-wide defaults — an Option on the Paragraph prototype here cascades into every target's build.
- **`<FormatConfiguration TargetID="…">`** carries per-target overrides. The `TargetID` must match the `TargetID` on a `<Format>` element in `<Formats>`. Values placed here only apply to that one target and override anything inherited from `<GlobalConfiguration>`.

`<FormatConfiguration>` holds more than just `<Rules>`. Its children:

- `<Rules>` — per-target style rule overrides (Options and Properties), grouped by category.
- `<Conditions>` — target-specific condition values (which conditions are on or off for this target).
- `<Variables>` — target-specific variable values that override the project-wide defaults.
- `<XRefFormats>` — target-specific cross-reference format strings.
- `<FormatSettings>` — what the UI labels "Target Settings" — target-wide trait values.
- `<MergeSettings>` — group/document merge configuration for this target's output.

Trait resolution order at build time: explicit per-target value → per-target inherit → explicit global value → prototype default.

### End-to-end example

A trimmed `<Project>` skeleton showing both scopes wired up correctly:

```xml
<?xml version="1.0" encoding="utf-8"?>
<Project Version="1.1.2.0"
         ProjectID="hMDzxVACF5I"
         RuntimeVersion="2025.1"
         FormatVersion="{Current}"
         xmlns="urn:WebWorks-Publish-Project">
  <Formats>
    <Format TargetName="Reverb Design"
            Name="WebWorks Reverb 2.0"
            Type="Application"
            TargetID="rvbDsgn001">
      <OutputDirectory>Output\Reverb Design</OutputDirectory>
    </Format>
  </Formats>

  <!-- ... <Groups> elided ... -->

  <GlobalConfiguration>
    <Rules Type="Paragraph" Default="{WWDefaultRule}">
      <Rule Key="{WWDefaultRule}">
        <Options>
          <Option Name="split-priority" Value="1" Source="Explicit" />
        </Options>
      </Rule>
      <Rule Key="Heading 1">
        <Options>
          <Option Name="toc-level" Value="1" Source="Explicit" />
        </Options>
        <Properties>
          <Property Name="font-size" Value="18pt" Source="Explicit" />
        </Properties>
      </Rule>
    </Rules>
    <Rules Type="Page" Default="{WWDefaultRule}">
      <Rule Key="{WWDefaultRule}">
        <Properties>
          <Property Name="breadcrumbs-separator" Value=" : " Source="Explicit" />
        </Properties>
      </Rule>
    </Rules>
  </GlobalConfiguration>

  <FormatConfigurations>
    <FormatConfiguration TargetID="rvbDsgn001">
      <FormatSettings>
        <FormatSetting Name="file-processing-pretty-print" Value="true" />
      </FormatSettings>
    </FormatConfiguration>
  </FormatConfigurations>
  <!-- ... <AdapterConfigurations>, <ProjectSettings /> elided ... -->
</Project>
```

`ChangeID` attributes were elided from this skeleton for readability. Real `.wep` files carry a `ChangeID` attribute on `<GlobalConfiguration>`, each `<Rules>` block, and each `<FormatConfiguration>`. See `templates/project.wep` for the empty-string placeholder pattern (`ChangeID=""`) used when authoring new elements by hand; ePublisher populates the value when the project is opened and saved.

## Accessing Traits in XSL Transforms

### FormatSettings

Use `wwprojext:GetFormatSetting()` to retrieve a target-wide setting:

```xml
<!-- Get a setting with a default fallback -->
<xsl:variable name="VarTabTitle"
  select="wwprojext:GetFormatSetting('connect-browser-tab-title', 'Help')" />

<!-- Test a boolean setting -->
<xsl:if test="wwprojext:GetFormatSetting('footer-generate') = 'true'">
  <!-- generate footer -->
</xsl:if>
```

### Options and Properties (via Context Rule)

Options and Properties require a two-step process:

1. Get the context rule for the current element using `wwprojext:GetContextRule()` or `wwprojext:GetOverrideRule()`
2. Navigate the returned node-set to find the specific Option or Property

```xml
<!-- Step 1: Get the context rule -->
<xsl:variable name="VarContextRule"
  select="wwprojext:GetContextRule('Paragraph',
    $ParamParagraph/@stylename,
    $ParamSplit/@documentID,
    $ParamParagraph/@id)" />

<!-- Step 2: Read an Option value -->
<xsl:variable name="VarGenerateOutput"
  select="$VarContextRule/wwproject:Options/wwproject:Option[@Name = 'generate-output']/@Value" />

<!-- Step 2: Read a Property value -->
<xsl:variable name="VarBreadcrumbsSep"
  select="$VarContextRule/wwproject:Properties/wwproject:Property[@Name = 'breadcrumbs-separator']/@Value" />
```

**`GetContextRule` parameters:** `(category, stylename, documentID, elementID)`
- `category`: `'Paragraph'`, `'Character'`, `'Table'`, `'Page'`, `'Marker'`, or `'Graphic'`
- `stylename`: The source document style name (from `@stylename` attribute in WIF)
- `documentID`: The document identifier (from split context)
- `elementID`: The element identifier (from `@id` attribute in WIF)

**`GetOverrideRule`** works the same way but retrieves the override rule specifically.

### Key for looking up properties by name

Properties are also accessible via an XSL key defined in the transform:

```xml
<xsl:key name="wwproject-property-by-name"
  match="wwproject:Property" use="@Name"/>
```

## Looking Up Trait Names

### Using the .resx File

The `FormatTraitInfoStrings.resx` file in this directory contains the complete mapping between internal trait names and English UI display names. It is XML with `<data>` elements mapping internal names to display strings:

```xml
<data name="connect-browser-tab-title" xml:space="preserve">
  <value>Browser Tab Title</value>
</data>
```

To find the internal name for a UI display name, search the English `.resx` file for the display text in `<value>` elements. The corresponding `name` attribute is the internal name used in `.fti` and project files.

### Naming Conventions in .resx

The `name` attribute follows patterns that help identify trait type and category:

- **Settings**: Named directly (e.g., `connect-browser-tab-title`, `footer-generate`, `company-name`)
- **Options/Properties**: Same naming pattern, but used within `<RuleTraits>` in `.fti` files
- **Descriptions**: Suffixed with `.Description` (e.g., `connect-browser-tab-title.Description`) — these are tooltip/help text in the full product source
- **Group headers**: Suffixed with `.Group` — these are category labels in the full product source

**Note:** The shipped `.resx` file contains only display name entries. The `.Description` and `.Group` entries exist in the full product source code but are not included here — they are not needed for trait name lookups.

### Searching .fti Files

When the `.resx` lookup is insufficient (e.g., you need to know the default value or which category a trait belongs to):

1. **Search `.fti` files** for the internal name: look in `C:\Program Files\WebWorks\ePublisher\<version>\Formats\` or in the project's `Formats/` directory
2. **Search by pattern**: `grep -r "keyword" --include="*.fti" Formats/`
3. **Check the group**: `.fti` entries have a `group` attribute that clusters related traits (e.g., `group="connect"` for Reverb settings)

### Updating .resx Files

This file is sourced from the ePublisher product source code at `dev/source/windows/dotnet/WebWorks/Publish/Core/Resources/FormatTraitInfoStrings.resx`. Update it when a new ePublisher version is released. The format is backward compatible — new entries are added but existing entries are not renamed or removed.

**Note:** Settings and Options have a direct one-to-one mapping between their `.resx` UI display name and their internal `.fti` name. Properties do not — the UI organizes Properties into a hierarchical tree (e.g., `text-indent` appears under **Text > Flow > Indent**), so there is no single UI label that matches the internal name. Property internal names follow the standard CSS property naming model, so they can usually be extrapolated from the CSS property name (e.g., `font-size`, `margin-left`, `text-indent`, `color`).

## Golden Test Project

When running diff-based golden tests on Reverb output, three target settings are commonly needed: pretty-print enabled (so HTML diffs are human-readable line-by-line), first document used as the splash page (so the entry point is deterministic), and in-document page breaks disabled (so a single document does not split into multiple HTML files). The snippet below wires all three into a `<FormatConfiguration TargetID="…">` using the corrected schema.

Before adapting the snippet to a real project, look up the actual `TargetID` for your test target by running `python scripts/parse-targets.py --json <project.wep>` and copy the `targetId` for the format you want to configure. The placeholder `rvbDsgn001` will not match an existing `<Format>` element in your project, and ePublisher silently ignores `<FormatConfiguration>` blocks whose `TargetID` does not resolve.

```xml
<FormatConfiguration TargetID="rvbDsgn001">
  <FormatSettings>
    <FormatSetting Name="file-processing-pretty-print" Value="true" />
    <FormatSetting Name="show-first-document" Value="true" />
  </FormatSettings>
  <Rules Type="Paragraph" Default="{WWDefaultRule}">
    <Rule Key="{WWDefaultRule}">
      <Options>
        <Option Name="split-priority" Value="none" Source="Explicit" />
      </Options>
    </Rule>
  </Rules>
</FormatConfiguration>
```

Trait names used here, with their UI labels:

| Internal name | UI label | Where it lives |
|---|---|---|
| `file-processing-pretty-print` | "Pretty Print" | `<FormatSetting>` (target-wide) |
| `show-first-document` | "Use first document as splash page" | `<FormatSetting>` (target-wide) |
| `split-priority` | "Page break priority" | `<Option>` on a Paragraph `<Rule>` |

See `FormatTraitInfoStrings.resx` and the [Looking Up Trait Names](#looking-up-trait-names) section above for additional UI-to-internal-name mappings.

Setting `split-priority` to `none` on the Paragraph prototype rule cascades to every Paragraph style, suppressing the splits that would otherwise produce multi-file output. For finer-grained control over individual style behavior, the CSS `page-break-before`, `page-break-after`, and `page-break-inside` Properties are the per-style alternative.

## Diffable HTML Output

When Reverb HTML output participates in a diff workflow — comparing builds across releases, regression testing during a documentation migration, validating that a content change produced only the expected differences, or reviewing documentation edits in a pull request — two target settings control whether the output is reviewable or unreadable as a diff.

Diffable HTML output and golden testing share the same two settings; they differ only in the intent that motivates the configuration. See [the Golden Test Project section](#golden-test-project) for the canonical `<FormatConfiguration>` snippet that wires both settings into a target.

| Setting | Value | Effect |
|---|---|---|
| `file-processing-pretty-print` | `true` | HTML output is emitted with line breaks and indentation; a single edit shows as a localized diff instead of changing an entire minified line. |
| `split-priority` (on Paragraph `{WWDefaultRule}`) | `none` | Headings no longer start new output files; each source document produces a single HTML file, so diffs show content edits rather than file additions, renames, and block moves. |

### Prototype-only vs explicit-per-heading

The Golden Test snippet sets `split-priority="none"` on `<Rule Key="{WWDefaultRule}">` once — the prototype-only cascade. Every Paragraph style inherits the value unless that style carries an explicit override.

When a project already overrides specific heading rules (Heading 1, Heading 2, etc.), those overrides can intercept the cascade and re-enable splits unintentionally. In that case, set `split-priority` explicitly on each heading rule as well as on the prototype:

```xml
<GlobalConfiguration>
  <Rules Type="Paragraph" Default="{WWDefaultRule}">
    <Rule Key="{WWDefaultRule}">
      <Options>
        <Option Name="split-priority" Value="none" Source="Explicit" />
      </Options>
    </Rule>
    <Rule Key="Heading 1">
      <Options>
        <Option Name="split-priority" Value="none" Source="Explicit" />
      </Options>
    </Rule>
    <Rule Key="Heading 2">
      <Options>
        <Option Name="split-priority" Value="none" Source="Explicit" />
      </Options>
    </Rule>
    <!-- Repeat for Heading 3 through Heading 6 -->
  </Rules>
</GlobalConfiguration>
```

Keep the `{WWDefaultRule}` row even when every named heading is enumerated — it catches custom Paragraph styles the project has not yet listed.

**When to choose which pattern:** prefer the prototype-only cascade for greenfield projects where no Paragraph styles are individually overridden. Prefer explicit-per-heading when an existing project already overrides heading rules, or when a reviewer needs every behavior to be visible at the rule level rather than inherited.

---

**Version**: 1.0.0
**Last Updated**: 2026-05-19
**Compatibility**: ePublisher 2024.1+
