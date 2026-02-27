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

**When a user refers to a setting by its UI name**, you must translate to the internal name before reading or writing project files. Search the `.resx` files in this directory for the mapping, or search `.fti` files by keyword for edge cases.

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

```xml
<Target Name="WebWorks Reverb 2.0" ...>
  <FormatSettings>
    <FormatSetting Name="connect-browser-tab-title" Value="My Help System" />
    <FormatSetting Name="company-copyright" Value="© 2025 WebWorks" />
    <FormatSetting Name="encoding" Value="UTF-8" />
  </FormatSettings>
</Target>
```

### Options and Properties (per style rule)

```xml
<Rules>
  <Rule StyleName="Heading 1" Category="Paragraph">
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

The `Source` attribute indicates whether the value was explicitly set (`Explicit`) or inherited (`Inherit`).

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

### Using the .resx Files

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
- **Descriptions**: Suffixed with `.Description` (e.g., `connect-browser-tab-title.Description`) — these are tooltip/help text
- **Group headers**: Suffixed with `.Group` — these are category labels in the UI

### Searching .fti Files

When the `.resx` lookup is insufficient (e.g., you need to know the default value or which category a trait belongs to):

1. **Search `.fti` files** for the internal name: look in `C:\Program Files\WebWorks\ePublisher\<version>\Formats\` or in the project's `Formats/` directory
2. **Search by pattern**: `grep -r "keyword" --include="*.fti" Formats/`
3. **Check the group**: `.fti` entries have a `group` attribute that clusters related traits (e.g., `group="connect"` for Reverb settings)

### Updating .resx Files

This file is sourced from the ePublisher product source code at `dev/source/windows/dotnet/WebWorks/Publish/Core/Resources/FormatTraitInfoStrings.resx`. Update it when a new ePublisher version is released. The format is backward compatible — new entries are added but existing entries are not renamed or removed.

**Note:** Settings and Options have a direct one-to-one mapping between their `.resx` display name and their internal `.fti` name. Properties do not — the UI organizes Properties into a hierarchical tree (e.g., `text-indent` appears under **Text > Flow > Indent**), so there is no single UI label that matches the internal name. Property internal names follow the standard CSS property naming model, so they can usually be extrapolated from the CSS property name (e.g., `font-size`, `margin-left`, `text-indent`, `color`).
