---
title: "fix: Format-Traits Guide schema corrections + Golden Test recipe"
type: fix
status: active
date: 2026-05-09
origin: docs/brainstorms/2026-05-09-issue-68-format-traits-schema-corrections-requirements.md
---

# fix: Format-Traits Guide schema corrections + Golden Test recipe

## Summary

Replace the broken `<Rules>` / `<Rule>` / `<FormatSettings>` examples in `epublisher/references/format-traits-guide.md` with the schema ePublisher actually accepts, document the `{WWDefaultRule}` literal and the `Source="Explicit"` requirement, add a "Global vs per-target overrides" section that places `<Rules>` correctly in `<GlobalConfiguration>` and `<FormatConfiguration TargetID="…">`, and bolt on a copy-pasteable Golden Test Project recipe (pretty-print + splash page + no page breaks) that uses the corrected schema end-to-end.

---

## Problem Frame

`format-traits-guide.md` is the only doc explaining how to wire Settings, Options, and Properties into a `.wep`. Its current per-style example uses `StyleName=`/`Category=` on `<Rule>` with no parent attributes on `<Rules>` — copying it produces `"The specified file is not a valid ePublisher project"` at load time. The `<FormatSettings>` example is shown only inside `<Target>`, so readers naturally drop the wrapper when working in `<FormatConfiguration>` and the build silently ignores their settings. Together these gaps make the guide actively harmful: following it produces hard or silent failures every time. (See origin: `docs/brainstorms/2026-05-09-issue-68-format-traits-schema-corrections-requirements.md`.)

---

## Assumptions

*This plan was authored without synchronous user confirmation. The items below are agent inferences that fill gaps in the input — un-validated bets that should be reviewed before implementation proceeds.*

- **End-to-end snippet uses two `<Rules>` categories (Paragraph + Page), not all six.** `templates/project.wep` shows the full six-category skeleton; this plan trims to two for readability in the guide. The full template remains the canonical "all categories" reference. Reviewer can override to four or six if the brevity feels too aggressive.
- **R11 (commented worked example in `templates/project.wep`) is included as a small in-scope unit, not deferred.** The brainstorm leaves it optional. Including it because the carrying cost is one XML comment block and it removes the only remaining "where do Options actually go" gap a reader can hit when starting from the template.
- **Insertion points for new sections in `format-traits-guide.md`:** `{WWDefaultRule}` documentation lands as a subsection inside "How Traits Appear in Project Files" (immediately after the corrected per-style example). "Global vs per-target style overrides" lands as a new H2 between "How Traits Appear in Project Files" and "Accessing Traits in XSL Transforms". "Golden Test Project" lands as a new H2 after "Looking Up Trait Names". Reviewer can re-order if a different reading flow is preferred.
- **The Golden Test recipe disables page breaks via `split-priority` set on `<Rule Key="{WWDefaultRule}">` for the Paragraph category.** `split-priority` is the .resx-confirmed Option for "Page break priority" and applying it to the prototype rule cascades the default to every Paragraph style. The `page-break-before/after/inside` CSS Properties are mentioned as alternatives but the recipe uses `split-priority` for simplicity.
- **`Source="Explicit"` applies only to `<Option>` and `<Property>`, not to `<FormatSetting>`.** The brainstorm's Assumption 6 is carried forward; `templates/project.wep` shows `<FormatSetting>` with only `Name`/`Value` so this matches observed behavior.

---

## Requirements

- R1. Replace the per-style Options/Properties example so `<Rules>` carries `Type="Paragraph"` and `Default="{WWDefaultRule}"`, and `<Rule>` carries `Key="…"` (not `StyleName=…`/`Category=…`).
- R2. Show `Source="Explicit"` on every `<Option>` and `<Property>` in examples, with a sentence explaining that omitting it causes load-time validation failure.
- R3. Add a complete, end-to-end snippet showing `<GlobalConfiguration>` with populated `<Rules>` for Paragraph + Page categories embedded in the surrounding `<Project>` skeleton.
- R4. Show the `<FormatSettings>` wrapper inside `<FormatConfiguration TargetID="…">`, with a note that bare `<FormatSetting>` siblings are silently ignored.
- R5. Document `{WWDefaultRule}` as the internal Key for the UI's `[Prototype]` row; explain that setting traits on this Key applies defaults to all styles of that category.
- R6. Add a "Global vs per-target style overrides" section explaining `<GlobalConfiguration>` (all targets) vs `<FormatConfiguration TargetID="…">` (one target), with the same `<Rules>` shape used in both scopes.
- R7. Enumerate the contents of `<FormatConfiguration>` beyond `<Rules>`: `<Conditions>`, `<Variables>`, `<XRefFormats>`, `<FormatSettings>`, `<MergeSettings>` — one line each.
- R8. Add a "Golden Test Project" section with a copy-pasteable `.wep` snippet for pretty-print + splash page + page-breaks-disabled, using the corrected schema and showing the `<FormatConfiguration TargetID="…">` context.
- R9. The Golden Test section must name the involved trait internals (`file-processing-pretty-print`, `show-first-document`, `split-priority`) and reference `FormatTraitInfoStrings.resx` for UI-name-to-internal-name lookups.
- R10. Add a one-sentence cross-reference in `project-parsing-guide.md` pointing to the new `{WWDefaultRule}` and Global-vs-per-target subsections.
- R11. Add an XML-comment worked example near a `<Rules>` block in `templates/project.wep` showing a populated `<Rule>` with one Option. Must not change the file's load behavior.

**Origin acceptance examples:** AE1 (covers R1, R2), AE2 (covers R4), AE3 (covers R5), AE4 (covers R8).

---

## Scope Boundaries

- No JSON Schema, XSD, or programmatic `.wep` validator. Documentation-only fix.
- No restructuring of `format-traits-guide.md` beyond the additions above. The Trait Types table, `.fti` definition examples, and XSL access section stay as-is.
- No new helper scripts (no `validate-rules.py`, no `apply-golden-test-config.py`).
- No migration of `FormatTraitInfoStrings.resx` content into the guide. Lookup pattern stays as-is.
- No deep schema docs for `<Conditions>`, `<Variables>`, `<XRefFormats>`, `<MergeSettings>`. Only the one-line enumeration.
- No `templates/project.wep` behavioral change. The R11 enrichment is comment-only.

---

## Context & Research

### Relevant Code and Patterns

- `plugins/webworks-claude-skills/skills/epublisher/references/format-traits-guide.md` — the file with the broken examples. Section "How Traits Appear in Project Files" (lines 64–94) is where the schema corrections land.
- `plugins/webworks-claude-skills/skills/epublisher/references/project-parsing-guide.md` — already shows the correct top-level `<Project>` structure (lines 13–37) including `<GlobalConfiguration>` and `<FormatConfigurations>`. Receives the cross-reference per R10.
- `plugins/webworks-claude-skills/skills/epublisher/templates/project.wep` — authoritative schema reference. Shows `<Rules Type="Paragraph" Default="{WWDefaultRule}">` with `<Rule Key="{WWDefaultRule}" />` for all six categories (lines 11–30). Receives the optional R11 commented example.
- `plugins/webworks-claude-skills/skills/epublisher/references/FormatTraitInfoStrings.resx` — confirms the Golden Test trait names: `file-processing-pretty-print` (line 1428), `show-first-document` (line 4293), `split-priority` (line 4401).

### Institutional Learnings

- `docs/solutions/authoritative-skill-patterns.md` — likely relevant to skill-doc edits; reviewed for "skill is the source of truth" pattern. The format-traits-guide's existing tone already follows this.
- `docs/solutions/integration-issues/` — checked for prior `.wep` schema lessons; none directly relevant.

### External References

- ePublisher Designer load-time validation behavior is verified against `templates/project.wep` (the file ePublisher itself ships as a clean baseline) rather than vendor docs, since proprietary schema docs are not externally available.

---

## Key Technical Decisions

- **Trait names verified against `FormatTraitInfoStrings.resx`, not inferred.** `file-processing-pretty-print`, `show-first-document`, and `split-priority` all exist in the .resx with the expected UI labels. The brainstorm's R8 deferred question is now resolved.
- **End-to-end snippet uses `<GlobalConfiguration>` for the populated `<Rules>` example, not `<FormatConfiguration>`.** Global is the simpler default scope; per-target is shown separately in the "Global vs per-target" section so readers don't conflate scope with schema.
- **Cross-reference in `project-parsing-guide.md` is a single sentence with two anchor links**, not a duplicate paragraph. Avoids drift if the format-traits-guide content evolves.
- **Schema corrections are made in-place** rather than adding a "before/after" pair. The current incorrect examples are removed entirely; keeping them would invite copy-paste of the wrong version.

---

## Open Questions

### Resolved During Planning

- **Internal trait names for the Golden Test recipe:** Resolved — `file-processing-pretty-print`, `show-first-document`, `split-priority` confirmed against `FormatTraitInfoStrings.resx`.
- **Two-category vs six-category end-to-end snippet:** Resolved — two-category (Paragraph + Page) for readability in the guide; the six-category template stays in `templates/project.wep` as the canonical "all categories" reference.

### Deferred to Implementation

- **Exact wording of the `Source="Explicit"` warning sentence.** Implementer to keep it under one sentence and cite the load-time validation failure mode.
- **Whether the Golden Test recipe disables page breaks via `split-priority` only or also adds CSS `page-break-*` Properties.** Default is `split-priority` only (simplest, prototype-rule-applied); implementer may add a one-line note pointing at the CSS Properties as a more granular alternative.

---

## Implementation Units

### U1. Correct existing schema examples in format-traits-guide.md

**Goal:** Replace the broken `<Rules>` / `<Rule>` example and the misleading `<FormatSettings>` example so that copy-pasting the guide produces a `.wep` that loads cleanly in ePublisher Designer.

**Requirements:** R1, R2, R4

**Dependencies:** None

**Files:**
- Modify: `plugins/webworks-claude-skills/skills/epublisher/references/format-traits-guide.md`

**Approach:**
- In "How Traits Appear in Project Files > Options and Properties (per style rule)" (around lines 78–94), replace the `<Rule StyleName="Heading 1" Category="Paragraph">` example with a corrected version: `<Rules Type="Paragraph" Default="{WWDefaultRule}"> <Rule Key="Heading 1"> …`.
- Keep the existing two-Option + one-Property body of the example (`split-priority`, `toc-level`, `font-size`) so the corrected example demonstrates the same trait coverage.
- Below the example, add one sentence: `Source="Explicit"` is required on every `<Option>` and `<Property>` — omitting it causes ePublisher to reject the project at load time.
- In "How Traits Appear in Project Files > FormatSettings (target-wide)" (around lines 66–76), keep the `<Target>` example as-is (it's correct in that scope), and add a second example showing the same wrapper inside `<FormatConfiguration TargetID="…">`. Add a one-sentence warning that bare `<FormatSetting>` placed as a direct child of `<FormatConfiguration>` is silently ignored.

**Patterns to follow:**
- `plugins/webworks-claude-skills/skills/epublisher/templates/project.wep` lines 11–30 — authoritative `<Rules>` / `<Rule>` shape.
- Existing example blocks in `format-traits-guide.md` already use fenced ` ```xml ` blocks; match that format.

**Test scenarios:**
- AE1 manual verification (covers AE1): copy the corrected per-style example into a fresh `.wep` based on `templates/project.wep`, open in ePublisher Designer, confirm no "not a valid ePublisher project" error and that the configured Option appears in the Style Designer with `Source: Explicit`.
- AE2 manual verification (covers AE2): wrap the `file-processing-pretty-print` setting inside `<FormatSettings>` per the corrected example, run an AutoMap build, confirm Reverb HTML is pretty-printed.
- Documentation lint scenario: every code block in the modified section uses `<Rule Key="…">` — no remaining `StyleName=` or `Category=` on `<Rule>`.

**Verification:**
- `grep -n 'StyleName=\|Category="Paragraph"' plugins/webworks-claude-skills/skills/epublisher/references/format-traits-guide.md` returns no matches in the modified examples (the `Category="Paragraph"` reference in the `.fti` `<RuleTraits>` section is a different concept and stays).
- The modified examples render cleanly when read top-to-bottom — no orphan `<Rules>` openings, no missing parent attributes.

---

### U2. Document {WWDefaultRule} and add Global-vs-per-target overrides section

**Goal:** Give readers the conceptual scaffolding to understand where `<Rules>` blocks live and what the `{WWDefaultRule}` literal does. Without this, even the corrected examples in U1 leave a reader unsure whether to put their `<Rules>` in `<GlobalConfiguration>` or per-target.

**Requirements:** R5, R6, R7

**Dependencies:** U1 (this section references the corrected examples)

**Files:**
- Modify: `plugins/webworks-claude-skills/skills/epublisher/references/format-traits-guide.md`

**Approach:**
- In "How Traits Appear in Project Files > Options and Properties (per style rule)", add a brief subsection (or trailing paragraph) titled "The `{WWDefaultRule}` prototype rule" that explains: the literal string `{WWDefaultRule}` (braces included) is the internal Key for the UI's `[Prototype]` row; setting Options or Properties on `<Rule Key="{WWDefaultRule}">` applies that value as the default for every style in the category. Mention the `Default="{WWDefaultRule}"` attribute on `<Rules>` ties the parent block to its prototype.
- Insert a new H2 section "Global vs per-target style overrides" after "How Traits Appear in Project Files" and before "Accessing Traits in XSL Transforms".
- Section content (in order):
  1. One paragraph: `<GlobalConfiguration>` carries traits that apply to every target; `<FormatConfiguration TargetID="…">` carries per-target overrides; both use the same `<Rules>` / `<Rule>` shape.
  2. A bulleted enumeration of `<FormatConfiguration>`'s child elements: `<Rules>` (style overrides), `<Conditions>` (target-specific conditions), `<Variables>` (target-specific variable values), `<XRefFormats>` (cross-reference format overrides), `<FormatSettings>` (UI's "Target Settings"), `<MergeSettings>` (group/document merge config). One line per element.
  3. A short note: traits resolve in this order — explicit per-target value, target inherit, explicit global value, prototype default. Implementer to keep this brief; deeper rule-resolution coverage is out of scope.

**Patterns to follow:**
- The existing "How Traits Are Defined (.fti Files)" section's tone — explanatory paragraph + small example.
- Heading depth: new H2 matches sibling sections; subsection inside "How Traits Appear in Project Files" uses H3 to match the existing FormatSettings/Options-and-Properties subsection structure.

**Test scenarios:**
- AE3 manual verification (covers AE3): apply `<Option Name="split-priority" Value="1" Source="Explicit" />` to `<Rule Key="{WWDefaultRule}">` inside `<GlobalConfiguration>`, build, confirm every Paragraph style inherits the default.
- Documentation completeness: the new section names all five `<FormatConfiguration>` children listed in R7 (Conditions, Variables, XRefFormats, FormatSettings, MergeSettings).
- Documentation completeness: `{WWDefaultRule}` appears at least once with a sentence connecting it to the UI's `[Prototype]` term.

**Verification:**
- The new "Global vs per-target style overrides" H2 exists between the existing "How Traits Appear in Project Files" and "Accessing Traits in XSL Transforms" sections.
- `grep -n 'WWDefaultRule\|\[Prototype\]' plugins/webworks-claude-skills/skills/epublisher/references/format-traits-guide.md` shows the term documented in prose (not just inside a code block).

---

### U3. Add end-to-end project-skeleton snippet

**Goal:** Show the corrected schema in a complete `<Project>` skeleton so a reader can see exactly where `<Rules>` and `<FormatConfiguration>` live without cross-referencing `templates/project.wep`.

**Requirements:** R3

**Dependencies:** U1, U2 (the snippet uses the corrected schema and the new section's framing)

**Files:**
- Modify: `plugins/webworks-claude-skills/skills/epublisher/references/format-traits-guide.md`

**Approach:**
- Within the new "Global vs per-target style overrides" section from U2, add a fenced XML block titled "End-to-end example" that shows a trimmed `<Project>` skeleton with:
  - The `<Project>` root element (matching `templates/project.wep`'s `Version`, `xmlns`).
  - A minimal `<Formats>` block with one Reverb target.
  - A `<GlobalConfiguration>` block with two `<Rules>` subtrees — Paragraph and Page — each containing the prototype `<Rule Key="{WWDefaultRule}">` plus one named `<Rule>` with one populated Option/Property to make the cascade visible.
  - A `<FormatConfigurations>` block with one `<FormatConfiguration TargetID="…">` containing a `<FormatSettings>` wrapper with one `<FormatSetting>`, demonstrating the per-target override pattern.
- Keep the snippet under ~50 lines; use `<!-- … -->` XML comments to elide bookkeeping (e.g., `ChangeID`, `<AdapterConfigurations>`) that aren't relevant to traits.

**Patterns to follow:**
- `plugins/webworks-claude-skills/skills/epublisher/templates/project.wep` for the surrounding `<Project>` element and its `xmlns`.
- `project-parsing-guide.md` lines 13–37 already shows a similar high-level skeleton; the new snippet expands on that with populated trait content.

**Test scenarios:**
- Manual ePublisher load: copy the snippet to a `.wep`, fill in unique IDs (`ProjectID`, `TargetID`, `GroupID`), open in Designer — expect clean load with both prototype defaults and the named-rule overrides visible.
- Snippet self-consistency: every `TargetID` referenced in `<FormatConfiguration TargetID="…">` matches a `<Format TargetID="…">` in the `<Formats>` block.
- Snippet self-consistency: every `<Option>` and `<Property>` carries `Source="Explicit"`.

**Verification:**
- The end-to-end snippet appears once, inside the "Global vs per-target style overrides" H2.
- The snippet uses two `<Rules>` categories (Paragraph + Page) with at least one named `<Rule>` per category.

---

### U4. Add Golden Test Project recipe

**Goal:** Collapse the recurring three-error setup task (pretty-print + splash + no-page-breaks) into a single copy-pasteable snippet using the corrected schema.

**Requirements:** R8, R9

**Dependencies:** U1, U2 (the recipe uses corrected schema and the per-target scope framing)

**Files:**
- Modify: `plugins/webworks-claude-skills/skills/epublisher/references/format-traits-guide.md`

**Approach:**
- Add a new H2 section "Golden Test Project" after "Looking Up Trait Names" (immediately before the Version/Last Updated footer).
- Section structure:
  1. One-paragraph framing: when running diff-based golden tests on Reverb output, three settings are commonly needed — pretty-print on, first document as splash page, in-document page breaks disabled — and the snippet below wires all three into a `<FormatConfiguration TargetID="…">`.
  2. A fenced XML block showing the `<FormatConfiguration TargetID="…">` block with a `<FormatSettings>` wrapper containing `file-processing-pretty-print="true"` and `show-first-document="true"`, plus a `<Rules Type="Paragraph" Default="{WWDefaultRule}">` containing `<Rule Key="{WWDefaultRule}">` with `<Option Name="split-priority" Value="0" Source="Explicit" />` to disable page breaks at the prototype level.
  3. A short trait-name reference table or bullet list mapping each setting to its UI label and `.resx` key (`file-processing-pretty-print` ↔ "Pretty Print"; `show-first-document` ↔ "Use first document as splash page"; `split-priority` ↔ "Page break priority"), plus a one-line cross-reference: "See `FormatTraitInfoStrings.resx` and the 'Looking Up Trait Names' section above for additional UI-to-internal-name mappings."
  4. A one-sentence note pointing out that `page-break-before/after/inside` Properties are an alternative to `split-priority` when a more granular per-style override is needed.

**Patterns to follow:**
- The existing "How Traits Appear in Project Files" subsection format — paragraph + fenced XML block + short note.
- Trait-name internals confirmed in `FormatTraitInfoStrings.resx` (lines 1428, 4293, 4401).

**Test scenarios:**
- AE4 manual verification (covers AE4): copy the snippet into a `.wep`'s `<FormatConfiguration TargetID="…">` for a Reverb target, run AutoMap build, expect: build succeeds; output HTML is pretty-printed (newline-indented); the first document renders as the splash page; no in-document page breaks emitted.
- Documentation completeness: all three trait-name internals from R9 appear in the snippet (`file-processing-pretty-print`, `show-first-document`, `split-priority`).
- Documentation completeness: the section explicitly references `FormatTraitInfoStrings.resx` for additional lookups.

**Verification:**
- A new "Golden Test Project" H2 exists, positioned after "Looking Up Trait Names" and before the version footer.
- The snippet uses the corrected schema (no `StyleName=`/`Category=` on `<Rule>`, all `<Option>` carry `Source="Explicit"`).

---

### U5. Cross-reference in project-parsing-guide and template enrichment

**Goal:** Make the new content discoverable from `project-parsing-guide.md` and add a worked-example breadcrumb to `templates/project.wep` so first-time readers see what a populated `<Rule>` looks like in context.

**Requirements:** R10, R11

**Dependencies:** U2, U4 (the cross-reference points to sections that must exist first)

**Files:**
- Modify: `plugins/webworks-claude-skills/skills/epublisher/references/project-parsing-guide.md`
- Modify: `plugins/webworks-claude-skills/skills/epublisher/templates/project.wep`

**Approach:**
- In `project-parsing-guide.md`, locate the "Project File Structure" section (around lines 13–37). After the high-level XML skeleton, add one sentence: "For per-style trait configuration inside `<GlobalConfiguration>` or `<FormatConfiguration>`, including the `{WWDefaultRule}` prototype literal and the global-vs-per-target scope distinction, see [`format-traits-guide.md`](./format-traits-guide.md)." Anchor links to specific subsections are not required — a file-level link is sufficient and avoids fragile anchor coupling.
- In `templates/project.wep`, immediately above the `<Rules Type="Paragraph" Default="{WWDefaultRule}" ChangeID="">` block (line 12), add an XML comment showing one populated `<Rule>` with one Option as a worked example. The comment must:
  - Be wrapped in `<!-- … -->` so it is inert at load time.
  - Use the corrected schema (`<Rule Key="Heading 1">`, `<Option … Source="Explicit" />`).
  - Be ~5–8 lines, not a full populated rule tree.
  - Carry a one-line lead-in like `<!-- Example populated rule (uncomment to use): -->` so the reader knows it is a sample.

**Patterns to follow:**
- `project-parsing-guide.md`'s existing "Related Documentation" section style for the cross-reference link format.
- The XML comments already in some `.wep` files in the repo; keep indentation matching the surrounding `<Rules>` block.

**Test scenarios:**
- ePublisher load: open the modified `templates/project.wep` in ePublisher Designer, expect clean load (the XML comment must not affect parsing).
- Discoverability: a reader landing on `project-parsing-guide.md` from a fresh search finds the trait-configuration link in the Project File Structure section.
- Schema correctness: the commented example in `templates/project.wep` uses `Key=` (not `StyleName=`), `Source="Explicit"`, and parent `<Rules>` already provides `Type=`/`Default=` context.

**Verification:**
- `git diff plugins/webworks-claude-skills/skills/epublisher/templates/project.wep` shows only an added XML comment block — no schema or attribute changes elsewhere.
- `grep -n 'format-traits-guide' plugins/webworks-claude-skills/skills/epublisher/references/project-parsing-guide.md` returns at least one new reference in the Project File Structure section.

---

## System-Wide Impact

- **Interaction graph:** None. Documentation-only change to skill references.
- **Error propagation:** N/A.
- **State lifecycle risks:** None. `templates/project.wep` is a static template; the comment-only enrichment cannot change its load behavior.
- **API surface parity:** None.
- **Integration coverage:** Manual verification per AE1–AE4 (load `.wep` in ePublisher Designer, run AutoMap build, observe Reverb output) is the only meaningful integration check for documentation correctness.
- **Unchanged invariants:** The `format-traits-guide.md` Trait Types table, `.fti` definition examples, XSL access section, and Looking Up Trait Names section all stay as-is. `templates/project.wep`'s default load behavior is unchanged.

---

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| Manual AE verification (AE1–AE4) requires a Windows machine with ePublisher Designer; CI cannot prove correctness | Reviewer with local install runs the four AEs before merge; the schema is also verified against `templates/project.wep` (which ePublisher itself produces) so the worst-case is silent staleness, not a regression |
| Adding sections changes anchor IDs; downstream skills or external docs linking to `format-traits-guide.md` could break | A repo-wide grep for `format-traits-guide.md#` before merge catches any stale anchors; existing links use file-level references, not anchors, per spot-check |
| The Golden Test recipe uses `split-priority=0` to disable page breaks at the prototype level — if `split-priority` semantics change in a future ePublisher release, the recipe silently breaks | Version compatibility note ("Compatibility: ePublisher 2024.1+") in the guide footer signals the supported range; future ePublisher upgrades will require a docs refresh anyway |

---

## Documentation / Operational Notes

- Bump the plugin patch version (`scripts/bump-version.sh patch`) before opening the PR — this is a documentation fix, not a new feature.
- No rollout, monitoring, or feature-flag concerns. Skills ship via the marketplace plugin update flow.

---

## Sources & References

- **Origin document:** [`docs/brainstorms/2026-05-09-issue-68-format-traits-schema-corrections-requirements.md`](../brainstorms/2026-05-09-issue-68-format-traits-schema-corrections-requirements.md)
- **Issue:** [#68 — format-traits guide schema corrections + Golden Test recipe](https://github.com/quadralay/webworks-claude-skills/issues/68)
- Related code: `plugins/webworks-claude-skills/skills/epublisher/references/format-traits-guide.md`, `plugins/webworks-claude-skills/skills/epublisher/references/project-parsing-guide.md`, `plugins/webworks-claude-skills/skills/epublisher/templates/project.wep`, `plugins/webworks-claude-skills/skills/epublisher/references/FormatTraitInfoStrings.resx`
- Related PRs/issues: #67 (markdown-integration skill restructure, merged at `c8b6c05` — `blocked-by` satisfied)
