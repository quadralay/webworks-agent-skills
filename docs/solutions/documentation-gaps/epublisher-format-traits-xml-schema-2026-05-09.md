---
title: ePublisher format-traits XML schema documentation gap
date: 2026-05-09
category: documentation-gaps
module: epublisher
problem_type: documentation_gap
component: documentation
severity: high
applies_when:
  - Authoring or programmatically editing a .wep, .wrp, or .wxsp project file by following the epublisher skill's reference docs
  - Setting per-style Options/Properties on a Paragraph, Character, Table, Page, Marker, or Graphic style
  - Configuring target-wide trait values inside a per-target FormatConfiguration block
  - Writing Golden Test fixtures that need pretty-printed output, a splash document, or page breaks disabled
related_components:
  - automap
  - reverb2
tags:
  - epublisher
  - wep-schema
  - format-traits
  - wwdefaultrule
  - golden-test
  - documentation-gap
---

# ePublisher format-traits XML schema documentation gap

## Context

The `epublisher` skill's `references/format-traits-guide.md` taught an abstract example of per-style Options inside a `.wep` project file, but the attribute names and missing required attributes did not match what ePublisher actually parses. Following the documented schema produced one of two failure modes:

- **Hard failure** — `The specified file is not a valid ePublisher project` on load.
- **Silent failure** — the build succeeded but the trait values were silently ignored.

The gap surfaced while configuring a `.wep` programmatically for Golden Testing (pretty print, splash page, disable page breaks). Three distinct structural errors all traced back to the same docs gap. Issue #68 consolidates that diagnosis with #64.

## Guidance

When documenting an XML schema for a binary or proprietary format, **the docs must match what the parser actually accepts, byte-for-byte on attribute names and structural nesting**. For ePublisher specifically:

### 1. `<Rules>` carries the category and prototype pointer; `<Rule>` carries the key

Wrong (what the docs used to show):

```xml
<Rules>
  <Rule StyleName="Heading 1" Category="Paragraph">
    <Options>
      <Option Name="split-priority" Value="1" Source="Explicit" />
    </Options>
  </Rule>
</Rules>
```

Right:

```xml
<Rules Type="Paragraph" Default="{WWDefaultRule}">
  <Rule Key="Heading 1">
    <Options>
      <Option Name="split-priority" Value="1" Source="Explicit" />
    </Options>
  </Rule>
</Rules>
```

- Style category lives on the parent `<Rules>` as `Type=`, not on individual `<Rule>` elements as `Category=`.
- `<Rule>` is identified by `Key=`, not `StyleName=`.
- `<Rules>` requires `Default="{WWDefaultRule}"` — projects that omit it will not load.

### 2. `{WWDefaultRule}` is the literal Key for the UI's `[Prototype]` row

The braces are part of the string. Setting Options or Properties on `<Rule Key="{WWDefaultRule}">` applies that value as the default for every style in the category. Every `<Rules>` block ePublisher generates has `Default="{WWDefaultRule}"` and a matching `<Rule Key="{WWDefaultRule}">` child.

### 3. `<FormatSettings>` is a required wrapper, not optional sugar

Inside `<FormatConfiguration TargetID="...">`, target-wide trait values must be wrapped:

```xml
<FormatConfiguration TargetID="rvbDsgn001">
  <FormatSettings>
    <FormatSetting Name="file-processing-pretty-print" Value="true" />
  </FormatSettings>
</FormatConfiguration>
```

Bare `<FormatSetting>` elements placed as direct children of `<FormatConfiguration>` are silently ignored — the build succeeds, the values do nothing.

### 4. `Source="Explicit"` is load-bearing on every `<Option>` and `<Property>`

Omitting it causes project validation to fail. There is no implicit default.

### 5. `<FormatConfiguration>` holds five sibling collections, not just `<Rules>`

`<Conditions>`, `<Variables>`, `<XRefFormats>`, `<FormatSettings>` (= "Target Settings" in the UI), `<MergeSettings>`, plus `<Rules>` blocks. Documentation that shows only `<Rules>` leaves authors blind to the rest.

### 6. `<GlobalConfiguration>` vs `<FormatConfiguration TargetID="...">` is the scope axis

`<GlobalConfiguration>` applies to all targets; `<FormatConfiguration>` overrides per target. The docs must explain where to put the `<Rules>` block for each scope, otherwise authors guess.

## Why This Matters

ePublisher's parser is asymmetric: structural attribute mistakes produce a refused-to-load error (loud, recoverable), but missing wrappers like `<FormatSettings>` produce a successful build with silently ignored settings (quiet, costly). Documentation that does not match the schema steers authors toward both failure modes simultaneously.

For agents working from skill references, the asymmetry is worse: the silent failure passes an automated build check and only surfaces when a human inspects the output. Wrong docs become a force multiplier for wasted iterations.

The Golden Test setup amplifies this. A canonical fixture for diff-based regression testing must produce identical output across runs, which requires the wrappers and `Source="Explicit"` markers to actually take effect. A silently-ignored setting yields nondeterministic-looking diffs that derail the regression.

## When to Apply

- When writing or extending a skill that documents an XML schema for a third-party tool, validate every attribute name and required wrapper against a known-good fixture from the tool's own test suite or a project file the tool itself wrote.
- When the schema has both required and optional structural elements, call out the required ones explicitly — readers will not guess them from an example that uses defaults.
- When an attribute value is a literal sentinel like `{WWDefaultRule}`, document the literal string verbatim, including any punctuation that looks accidental (braces, brackets, leading slashes).
- When the parser is lenient on missing wrappers (silent ignore rather than error), warn loudly. Agents reading the docs cannot tell from a passing build that their settings were dropped.

## Examples

End-to-end skeleton for a `.wep` file with both a global Paragraph rule and a per-target Page rule (trimmed for clarity):

```xml
<Project>
  <GlobalConfiguration>
    <Rules Type="Paragraph" Default="{WWDefaultRule}">
      <Rule Key="{WWDefaultRule}">
        <Options>
          <Option Name="landmark-id-format" Value="source-id" Source="Explicit" />
        </Options>
      </Rule>
    </Rules>
  </GlobalConfiguration>

  <FormatConfigurations>
    <FormatConfiguration TargetID="rvbDsgn001">
      <Rules Type="Page" Default="{WWDefaultRule}">
        <Rule Key="{WWDefaultRule}">
          <Options>
            <Option Name="split-priority" Value="0" Source="Explicit" />
          </Options>
        </Rule>
      </Rules>

      <FormatSettings>
        <FormatSetting Name="file-processing-pretty-print" Value="true" />
        <FormatSetting Name="show-first-document" Value="true" />
      </FormatSettings>
    </FormatConfiguration>
  </FormatConfigurations>
</Project>
```

Trait names verified against `FormatTraitInfoStrings.resx`:

| Trait | Effect |
|-------|--------|
| `file-processing-pretty-print` | Indents output XHTML for diffable Golden Test fixtures |
| `show-first-document` | Treats the first source document as a splash page |
| `split-priority` | `0` on the Page prototype disables all page breaks |

## Related

- Issue #68 — schema corrections (consolidates #64)
- `plugins/webworks-claude-skills/skills/epublisher/references/format-traits-guide.md` — the corrected guide
- `plugins/webworks-claude-skills/skills/epublisher/references/project-parsing-guide.md` — now cross-references the format-traits guide
- `plugins/webworks-claude-skills/skills/epublisher/templates/project.wep` — commented worked example near the `<Rules>` blocks
- `docs/solutions/architecture-patterns/format-spec-vs-integration-skill-separation-2026-05-09.md` — related boundary pattern between format and product skills
