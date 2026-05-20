---
title: Configuring ePublisher targets for diffable HTML output
date: 2026-05-19
category: best-practices
module: epublisher
problem_type: best_practice
component: documentation
severity: medium
applies_when:
  - Configuring a Reverb HTML target whose output will be compared via git diff or reviewed in a pull request
  - Setting up regression testing or golden testing on Reverb HTML output
  - Validating that a source-document edit produced only the expected output changes
  - Deciding between Value="0" and Value="none" for split-priority in a .wep, .wrp, or .wxsp file
  - Authoring or editing a project that already overrides individual heading rules (Heading 1, Heading 2, etc.)
related_components:
  - reverb2
  - automap
tags:
  - epublisher
  - format-traits
  - split-priority
  - pretty-print
  - golden-test
  - diff-workflow
  - wwdefaultrule
---

# Configuring ePublisher targets for diffable HTML output

## Context

Reverb HTML output from ePublisher is unreviewable by default in any diff-based workflow — comparing builds between releases, regression testing during documentation migrations, validating that a source edit produced only the expected change, or reviewing documentation in pull requests. Two specific defaults work against the reviewer:

1. **Minified output.** Without `file-processing-pretty-print=true`, generated HTML is emitted as long single-line blocks. Any byte-level change touches the whole line, so `git diff` shows the entire file as changed even when only one phrase moved.
2. **Heading-driven file splitting.** ePublisher's default `split-priority` causes paragraph styles (most often Heading 1, Heading 2) to start a new output file. A single chapter renders as a tree of small HTML files whose names and contents shift when headings move — diffs end up showing file renames and large block moves rather than the content edits the reviewer cares about.

The two settings that fix this are the same two used in golden-test fixtures. Issue #68 (merged 2026-05-19) consolidated the canonical XML snippet in `plugins/webworks-claude-skills/skills/epublisher/references/format-traits-guide.md` under the **Golden Test Project** heading. Issue #40 then framed the same configuration for the broader diff-workflow audience and surfaced two technical questions worth capturing for future agents: what value to use for `split-priority` (`"0"` or `"none"`), and how to handle projects that already override individual heading rules and may intercept the prototype cascade.

## Guidance

### Two settings, both required

For diffable Reverb HTML output, set both of these in the target's `<FormatConfiguration>`:

| Setting | Where it lives | Value | Effect |
|---|---|---|---|
| `file-processing-pretty-print` | `<FormatSettings>` (target-wide) | `true` | HTML is emitted with line breaks and indentation; a single edit shows as a localized diff instead of changing an entire minified line. |
| `split-priority` | `<Option>` on Paragraph `<Rule Key="{WWDefaultRule}">` | `none` | Headings no longer start new output files; each source document produces a single HTML file, so diffs show content edits rather than file additions, renames, and block moves. |

Setting only one is not enough. Pretty-print alone leaves output split across many files; no-split alone leaves the content unreadable as a diff. Both are required for the workflow to function.

### Use `Value="none"`, not `Value="0"`

Both values produce identical behavior at runtime — they suppress splits — and both pass project validation. Prefer `"none"` for these reasons:

- **The `.fti` declares `none` as a peer `OptionClass` to `number`.** In the Reverb 2.0 installation under `Formats/Shared/common/behaviors/document.fti`, the `split-priority` Option for the Paragraph category declares three OptionClass values: `use-toc-level` (the trait default), `none`, and `number`. The presence of `none` as a distinct class — separate from numeric values — signals it is the intended way to disable splitting.
- **The XSL predicate confirms semantic equivalence.** The split predicate in `Formats/Shared/common/splits/priorities.xsl` is `splitpriority != 'none' AND splitpriority > 0`. Both clauses must hold for a split to fire. `"none"` short-circuits via the first clause; `"0"` short-circuits via the second. Either value disables splitting.
- **`"none"` reads as "do not split here";** `"0"` reads as "priority zero," which the reader has to translate before understanding what it does. Self-documenting wins.

The same value applies whether the setting lives on the prototype rule or on individual heading rules.

### Prototype-only vs explicit-per-heading

Two patterns exist for placing the `split-priority="none"` Option. The choice depends on whether the project already overrides individual heading rules.

**Prototype-only cascade** — one Option on `<Rule Key="{WWDefaultRule}">` cascades to every Paragraph style. Concise. Use this for greenfield projects:

```xml
<Rules Type="Paragraph" Default="{WWDefaultRule}">
  <Rule Key="{WWDefaultRule}">
    <Options>
      <Option Name="split-priority" Value="none" Source="Explicit" />
    </Options>
  </Rule>
</Rules>
```

**Explicit-per-heading** — set `split-priority` on each heading rule as well as on the prototype. Verbose, but defensive. Use this when the project already overrides specific heading rules (Heading 1, Heading 2, etc.). Per-heading overrides can intercept the prototype cascade and re-enable splits silently:

```xml
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
```

Keep the `{WWDefaultRule}` row even when every named heading is enumerated. It catches custom Paragraph styles the project has not yet listed — the protection only holds for styles you explicitly mention or styles that fall back to the prototype.

### Cross-reference, do not duplicate

When framing the same configuration for a new audience (e.g., adding a use-case section for diff workflows when a Golden Test section already exists), cross-reference the canonical snippet rather than duplicating it. Two snippets that must stay in sync are a maintenance hazard — `format-traits-guide.md` keeps one snippet under `## Golden Test Project` and the new `## Diffable HTML Output` section links to it via the `#golden-test-project` anchor. Anchor links break silently if the section is renamed; the trade-off is acceptable for a small, maintained file.

## Why This Matters

ePublisher's defaults optimize for human reading of a finished documentation site, not for review of generated HTML. Minified output and heading-driven file splits are reasonable end-user defaults that make HTML output unusable for diff-based engineering workflows. Without these two settings, PR review of documentation changes degenerates into "the whole file changed" and regression testing produces noise that hides real differences.

The `split-priority` value question matters because both `"0"` and `"none"` look correct in isolation and produce identical behavior. An agent following a copy-paste recipe will not notice a drift between sections of the same guide, but an agent debugging "why does this XML look different here than there?" will burn time chasing a semantic difference that does not exist. Capturing the equivalence once prevents that loop.

The prototype-only versus explicit-per-heading distinction matters because the cascade is silent: a project that overrides `<Rule Key="Heading 1">` for unrelated reasons (font size, TOC level) can re-enable splitting just by being present, even when `<Rule Key="{WWDefaultRule}">` carries the suppress-splits Option. The build still succeeds; the output is just wrong.

## When to Apply

- When configuring a new Reverb target whose HTML output will be diffed, reviewed in a PR, or used as a regression-test fixture.
- When auditing an existing target whose output is multi-file or minified and the project needs to participate in a diff workflow.
- When updating documentation that references `split-priority` values — align on `"none"` for clarity and consistency.
- When a project already overrides individual heading rules — prefer explicit-per-heading to avoid silent cascade interception.

## Examples

**Minimal configuration for a diffable target.** Drop this `<FormatConfiguration>` into the project's `<FormatConfigurations>` block, substituting the actual `TargetID` (look it up with `python scripts/parse-targets.py --json <project.wep>`):

```xml
<FormatConfiguration TargetID="rvbDsgn001">
  <FormatSettings>
    <FormatSetting Name="file-processing-pretty-print" Value="true" />
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

For golden-testing specifically, add `<FormatSetting Name="show-first-document" Value="true" />` inside `<FormatSettings>` to make the entry point deterministic. The Golden Test section in `format-traits-guide.md` shows the full three-setting snippet.

**Verifying split-priority value equivalence in your installation.** If you want to confirm the semantics for a specific ePublisher version, the predicate lives in two files inside the installation:

```
Formats/Shared/common/behaviors/document.fti          # OptionClass declarations for split-priority
Formats/Shared/common/splits/priorities.xsl           # the split predicate (line 106 in 2026.1)
```

The predicate is `splitpriority != 'none' AND splitpriority > 0`. If a future ePublisher version changes this, the equivalence claim above no longer holds — re-verify before relying on it.

## Related

- `plugins/webworks-claude-skills/skills/epublisher/references/format-traits-guide.md` — `## Golden Test Project` and `## Diffable HTML Output` sections; the canonical XML snippet lives in Golden Test, Diffable HTML Output cross-references it.
- `docs/solutions/documentation-gaps/epublisher-format-traits-xml-schema-2026-05-09.md` — schema-correctness learning (which attribute names ePublisher actually parses). Same file, different topic; useful read before authoring any new `<Rules>`/`<Rule>`/`<Option>` content.
- `docs/solutions/architecture-patterns/format-spec-vs-integration-skill-separation-2026-05-09.md` — boundary pattern between format and product skills; relevant when deciding whether new content belongs in the `epublisher` skill or elsewhere.
- Issue #40 — origin of the diff-workflow framing.
- Issue #68 — schema corrections that produced the Golden Test recipe this learning builds on.
