---
date: 2026-05-09
topic: format-traits-schema-corrections
---

# Format-Traits Guide — Schema Corrections + Golden Test Recipe

## Summary

Correct the `<Rules>` / `<Rule>` / `<FormatSettings>` examples in the `epublisher` skill's `format-traits-guide.md` so they match what real `.wep` files require, document `{WWDefaultRule}` and the `Source="Explicit"` rule, explain when traits live in `<GlobalConfiguration>` vs `<FormatConfiguration TargetID="…">`, and add a copy-pasteable "Golden Test Project" snippet for pretty-print + splash-page + page-breaks-disabled.

---

## Problem Frame

The `epublisher` skill is the authoritative reference for working with `.wep`/`.wrp`/`.wxsp` files. When a user (or a downstream agent) follows `references/format-traits-guide.md` to add per-style Options/Properties to a project, they hit one of two failure modes:

1. **Hard failure** — ePublisher refuses to load the project: "The specified file is not a valid ePublisher project." This happens when the documented attributes (`StyleName=`, `Category=` on `<Rule>`) are used instead of the schema ePublisher actually expects (`Key=` on `<Rule>`, `Type=` and `Default=` on `<Rules>`, `Source="Explicit"` on `<Option>`/`<Property>`).
2. **Silent failure** — the build succeeds but the configuration is silently ignored because the `<FormatSettings>` wrapper inside `<FormatConfiguration>` was omitted. ePublisher is lenient about parsing but does not honor `<FormatSetting>` siblings outside the wrapper.

The skill's `templates/project.wep` already shows the correct schema (`<Rules Type="Paragraph" Default="{WWDefaultRule}">`, `<Rule Key="{WWDefaultRule}">`), so the project file format itself is well-understood — the gap is entirely in the documentation that explains it. The `{WWDefaultRule}` literal (the internal name for the UI's `[Prototype]` style row) is also undocumented; without it, a user can't apply a default Option to all styles in a category.

A second, related gap: configuring Reverb output for diff-friendly Golden Testing (pretty-print on, first document as splash page, page breaks disabled) repeatedly hits all three structural errors above. A canonical snippet would prevent the same trial-and-error each time.

---

## Assumptions

*This requirements doc was authored without synchronous user confirmation. The items below are agent inferences that fill gaps in the input — un-validated bets that should be reviewed before planning proceeds.*

- The Golden Test recipe is meant to live in `format-traits-guide.md` (the issue says "Add a 'Golden Test Project' recipe" without naming a file). Inferring this because (a) the recipe is anchored in `<FormatSetting>` and `<Rule>` content the guide already covers, and (b) splitting it into a new file would fragment the trait-configuration story. An alternative placement would be a new `golden-test-recipe.md` reference; choosing the simpler co-located option.
- "Pretty print enabled, first document as splash page, all page breaks disabled" maps to the Reverb 2.0 `FormatSetting` keys `file-processing-pretty-print=true`, the splash-page mechanism documented in the Reverb skill, and the per-Paragraph-rule `split-priority` Option (or the global page-break Option) — exact internal names will be verified during planning against `FormatTraitInfoStrings.resx` and the shipped `.fti` files.
- The `<Rule>` `Key` attribute accepts both the literal `{WWDefaultRule}` and a style name (e.g., `"Heading 1"`) as its value; the issue's "Correct" example uses `Key="Heading 1"`. Treating the `Key` attribute as polymorphic (default sentinel OR style-name string) per the issue's framing.
- The skill should not introduce a new top-level reference file just for `{WWDefaultRule}`; it belongs inline in `format-traits-guide.md` near the `<Rules>` example. `project-parsing-guide.md` gets a one-line cross-reference rather than duplicate content.
- This is a documentation-only change — no script, schema, or template behavior changes are needed. The `templates/project.wep` already conforms to the correct schema; only a single optional commented example would be added.
- The `Source="Explicit"` requirement applies to every `<Option>` and `<Property>`, but NOT to `<FormatSetting>` (which has `Name`/`Value` only based on `templates/project.wep` and the existing guide). Applying it narrowly to where the issue called it out.

---

## Requirements

**Schema corrections in `format-traits-guide.md`**

- R1. Replace the per-style Options/Properties example so that `<Rules>` carries `Type="Paragraph"` (style category) and `Default="{WWDefaultRule}"` (prototype rule key), and `<Rule>` carries `Key="…"` instead of `StyleName=…`/`Category=…`. The corrected example must round-trip through ePublisher load without "not a valid ePublisher project" errors.
- R2. The corrected example must show `Source="Explicit"` on every `<Option>` and `<Property>`, with a sentence explaining that omitting it causes load-time validation failure.
- R3. Add a complete, end-to-end snippet showing a populated `<GlobalConfiguration>` block (with `<Rules>` for at least Paragraph and one other category) embedded in the surrounding `<Project>` skeleton, so a reader can see where the block lives without cross-referencing another file.
- R4. The corrected `<FormatSettings>` example must show the wrapper element inside `<FormatConfiguration TargetID="…">` (not only inside `<Target>`), with a note that `<FormatSetting>` placed as a direct child of `<FormatConfiguration>` is silently ignored.

**Conceptual additions**

- R5. Document `{WWDefaultRule}` as the internal Key for the UI's `[Prototype]` row, and explain that setting Options/Properties on this Key applies defaults to all styles of that category.
- R6. Add a "Global vs per-target style overrides" section explaining: `<GlobalConfiguration>` applies to all targets; `<FormatConfiguration TargetID="…">` overrides for a specific target; and the same `<Rules>` shape is used in both scopes.
- R7. Briefly enumerate the contents of `<FormatConfiguration>` beyond `<Rules>`: `<Conditions>`, `<Variables>`, `<XRefFormats>`, `<FormatSettings>` (the UI's "Target Settings"), and `<MergeSettings>`. A bulleted list with a one-line description per element is sufficient.

**Golden Test recipe**

- R8. Add a "Golden Test Project" section that gives a copy-pasteable `.wep` snippet wiring the three Reverb-output settings commonly needed for diffable golden tests: pretty-print on, first document as splash page, all page breaks disabled. The snippet must use the corrected schema (R1–R4) and must include the surrounding `<FormatConfiguration TargetID="…">` context so a reader knows where to place it.
- R9. The Golden Test section must call out which trait-name internals are involved (e.g., `file-processing-pretty-print`) and reference `FormatTraitInfoStrings.resx` for UI-name-to-internal-name lookups, so the recipe stays adaptable when settings change.

**Cross-reference and template polish**

- R10. Add a single-sentence cross-reference in `project-parsing-guide.md` pointing to the new `{WWDefaultRule}` and Global-vs-per-target subsections in `format-traits-guide.md`, so a reader who lands on the parsing guide first finds the configuration content.
- R11. (Optional, low-cost.) Add an XML comment to `templates/project.wep` near one of the `<Rules>` blocks showing a populated `<Rule>` with one Option as a worked example. The comment must not change the file's load behavior.

---

## Acceptance Examples

- AE1. **Covers R1, R2.** Given the abstract per-style example in `format-traits-guide.md`, when a user copies it verbatim into a new `.wep` and opens the project in ePublisher Designer, then ePublisher loads the project without a "not a valid ePublisher project" error and the configured Option appears as `Source: Explicit` in the Style Designer pane.
- AE2. **Covers R4.** Given the corrected `<FormatConfiguration>` example, when a user wraps `<FormatSetting Name="file-processing-pretty-print" Value="true" />` inside `<FormatSettings>` and runs an AutoMap build, then the resulting Reverb HTML files are pretty-printed (newline-indented) rather than minified.
- AE3. **Covers R5.** Given a user wants to set a default `split-priority` for every Paragraph style, when they apply the Option to `<Rule Key="{WWDefaultRule}">` inside `<GlobalConfiguration>`, then ePublisher applies that default to every Paragraph style in the project unless overridden by a more specific rule.
- AE4. **Covers R8.** Given the Golden Test recipe, when a user copies the snippet into the `<FormatConfiguration TargetID="…">` for their Reverb target and runs an AutoMap build, then the build succeeds, the output is pretty-printed, the first document renders as the splash page, and no in-document page breaks are emitted.

---

## Success Criteria

- An agent or developer following `format-traits-guide.md` from top to bottom can produce a `.wep` that loads cleanly in ePublisher and whose Options/Properties take effect at build time, without consulting `templates/project.wep` or product source code.
- A downstream agent (`/workflows:work` on a future ePublisher-configuration issue) does not need to invent or guess the schema for `<Rules>`, `<Rule>`, `<FormatSettings>`, or `{WWDefaultRule}`.
- The Golden Test recipe collapses a recurring 3-error setup task (pretty-print + splash + no-page-breaks) into a single copy-paste, with no per-attempt debugging round.
- `format-traits-guide.md`'s "How Traits Appear in Project Files" section, the new "Global vs per-target style overrides" section, and the Golden Test recipe are internally consistent — every snippet uses the corrected schema.

---

## Scope Boundaries

- Not adding a JSON Schema, XSD, or programmatic validator for `.wep` files. Documentation-only fix.
- Not refactoring `format-traits-guide.md`'s existing structure beyond what the corrections require. The Trait Types table, `.fti` definitions section, and XSL-access section stay as-is.
- Not adding new helper scripts (no `validate-rules.py`, no `apply-golden-test-config.py`). The recipe is a static snippet.
- Not migrating `FormatTraitInfoStrings.resx` content into the guide. Keep the existing pattern of `.resx` lookup.
- Not documenting the full set of `<Conditions>`, `<Variables>`, `<XRefFormats>`, `<MergeSettings>` schemas — only enumerating that they exist and live in `<FormatConfiguration>`. Each may earn its own section in a follow-up issue.
- Not changing `templates/project.wep`'s default behavior. Optional comment-only enrichment per R11.
- Not addressing other reported gaps in `epublisher` skill references that are outside the trait-configuration scope of this issue.

---

## Key Decisions

- **Co-locate the Golden Test recipe inside `format-traits-guide.md`** rather than creating a new reference file: the recipe is anchored in trait configuration content and a separate file would fragment the story.
- **Treat `{WWDefaultRule}` documentation as inline content in `format-traits-guide.md`** with a one-line cross-reference from `project-parsing-guide.md`: avoids duplicating the same explanation in two files.
- **Keep the `<FormatConfiguration>` enumeration deliberately brief** (one line per child element): the issue scope is trait corrections, not a full schema reference. Each child element can earn deeper coverage in a focused follow-up.
- **Make the `templates/project.wep` enrichment optional**: the template is currently minimal-and-correct; a worked example as an XML comment is helpful but not required for the schema-correction fix to be complete.

---

## Dependencies / Assumptions

- Issue #67 (markdown-integration skill restructure) is merged on `main` (commit `c8b6c05`); this issue's `blocked-by: #67` is satisfied.
- The exact internal names for the Golden Test settings (pretty-print, splash page, page-break disable) will be confirmed during planning against `plugins/webworks-claude-skills/skills/epublisher/references/FormatTraitInfoStrings.resx` and the shipped `.fti` files.
- The corrected schema in the issue body matches the schema in `plugins/webworks-claude-skills/skills/epublisher/templates/project.wep` (verified during this brainstorm). The template is treated as authoritative.

---

## Outstanding Questions

### Deferred to Planning

- [Affects R8] [Needs research] Confirm the exact internal trait names and per-rule placement for "first document as splash page" and "all page breaks disabled" in current Reverb 2.0 — the issue describes the behaviors but doesn't pin internal names. Verify against `FormatTraitInfoStrings.resx` and the Reverb format `.fti` files.
- [Affects R3] [Technical] Decide whether the end-to-end `<GlobalConfiguration>` snippet should mirror the six-category `<Rules>` skeleton already in `templates/project.wep` or use a trimmed-down two-category example for readability. Planning chooses based on guide-page length and density.
- [Affects R11] [Technical] Decide whether `templates/project.wep` gets the optional commented worked-example or stays minimal. Planning weighs the small carrying cost of a comment block against the value to first-time readers.
