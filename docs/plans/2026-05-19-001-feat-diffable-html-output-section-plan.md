---
title: "feat: Add Diffable HTML Output section to format-traits-guide"
type: feat
status: active
date: 2026-05-19
origin: docs/brainstorms/2026-05-19-issue-40-diffable-html-output-requirements.md
---

# feat: Add Diffable HTML Output section to format-traits-guide

## Summary

Add a use-case-driven `## Diffable HTML Output` section to `plugins/webworks-claude-skills/skills/epublisher/references/format-traits-guide.md` that frames the existing Golden Test settings for the diff-workflow audience (PR review, regression testing, content-change validation, build-to-build comparison) and documents the explicit-per-heading `split-priority` pattern as a verbose alternative to the prototype-only cascade. Align the value used for `split-priority` to `none` across both the existing Golden Test snippet and the new section for internal consistency.

---

## Problem Frame

Issue #68 (merged 2026-05-19) added a Golden Test Project recipe to `format-traits-guide.md` that already documents the two settings issue #40 asks for (`file-processing-pretty-print`, `split-priority`). Issue #40 was filed earlier against the same configuration but a broader audience — anyone who wants their Reverb output to diff cleanly in PR review or regression testing, not just the golden-test workflow. A reader searching the guide for "diff", "PR review", or "regression" today does not land on a section that names their workflow, and the guide does not yet document the explicit-per-heading `<Rule>` variant that the issue body presents as an alternative to the prototype-only cascade. See origin: `docs/brainstorms/2026-05-19-issue-40-diffable-html-output-requirements.md`.

---

## Assumptions

*This plan was authored without synchronous user confirmation. The items below are agent inferences that fill gaps in the input — un-validated bets that should be reviewed before implementation proceeds.*

- **Place `## Diffable HTML Output` as a standalone H2 section immediately after `## Golden Test Project`, not as an H3 subsection nested inside it.** Standalone H2 maximizes discoverability for the diff-workflow audience (AE1 hinges on keyword search hits), and adjacency to Golden Test keeps the configuration-sharing story visible. A subsection would emphasize the shared configuration but would not surface the use-case framing in the document outline. If the user prefers nesting, this is straightforward to invert at review time.
- **Show two heading-level examples (Heading 1, Heading 2) plus a `<!-- Repeat for Heading 3 through Heading 6 -->` comment in the explicit-per-heading example.** Two examples prove the pattern is mechanical repetition without consuming vertical space for all six. One example could be read as a special case; six is bloat. Adjust if reviewers prefer either extreme.

---

## Requirements

- R1. Add `## Diffable HTML Output` section that names the four diff-workflow use cases from issue #40 by keyword (comparing HTML output between builds, regression testing, validating content-change diffs, PR review). (Carried from origin R1.)
- R2. Annotate each of the two settings (`file-processing-pretty-print`, `split-priority`) with a one-sentence "Effect:" line describing the observable change in output. (Carried from origin R2.)
- R3. Cross-reference the existing Golden Test Project snippet rather than duplicating it; state the relationship between diffable-output and golden-testing as same configuration, different intent. (Carried from origin R3.)
- R4. Document the explicit-per-heading pattern — `<Option Name="split-priority" Value="none" Source="Explicit" />` on each individual heading `<Rule>` plus the `{WWDefaultRule}` fallback — as an alternative to the prototype-only cascade. (Carried from origin R4.)
- R5. Provide one-paragraph guidance on when to choose each pattern: prototype-only for greenfield projects; explicit-per-heading when an existing project already overrides specific heading rules. (Carried from origin R5.)
- R6. Show the `<GlobalConfiguration>` `<Rule Key="{WWDefaultRule}">` fallback explicitly in the explicit-per-heading example and explain why the prototype rule still matters even when every named style is enumerated (catches custom styles). (Carried from origin R6.)
- R7. **Plan-derived.** Align the existing Golden Test snippet's `split-priority` value from `"0"` to `"none"` and update the surrounding prose at `format-traits-guide.md:339` so the entire guide uses one verified value. (Origin acknowledged this consistency cleanup as a planning-time decision item — see "Resolved During Planning" below.)

**Origin acceptance examples:** AE1 (covers R1, R2), AE2 (covers R3), AE3 (covers R4, R5, R6).

---

## Scope Boundaries

- Not creating a new top-level reference file under `plugins/webworks-claude-skills/skills/epublisher/references/`. Content belongs co-located with the Golden Test recipe in `format-traits-guide.md`.
- Not creating a new skill for "ePublisher project configuration"; the trait-configuration story stays consolidated in the `epublisher` skill.
- Not duplicating the full XML snippet from the Golden Test section. The new section cross-references it and adds only the per-heading variant.
- Not modifying `plugins/webworks-claude-skills/skills/epublisher/templates/project.wep`. The template stays minimal-and-correct (its current `Value="1"` is a per-style example, not a default that affects splitting behavior).
- Not documenting non-diff motivations for `split-priority` or pretty-print (e.g., single-page tutorials, embedded help). Those earn their own section if they come up.
- Not addressing the `show-first-document` splash-page setting; the Golden Test section already covers it.
- Not adding helper scripts. The recipe is static documentation.
- Not modifying `plugins/webworks-claude-skills/skills/epublisher/references/format-traits-guide.md` content outside the Golden Test section (the value-alignment edits) and the new Diffable HTML Output section. No restructuring of other sections.

---

## Context & Research

### Relevant Code and Patterns

- `plugins/webworks-claude-skills/skills/epublisher/references/format-traits-guide.md` — target file. Existing sections relevant to this plan: `## Golden Test Project` (lines 307-339), `### The {WWDefaultRule} prototype rule` (lines 113-130), `### End-to-end example` (lines 150-208).
- The doc already uses anchor-link cross-references in two places (`[The {WWDefaultRule} prototype rule](#the-wwdefaultrule-prototype-rule)` at line 109, `[Looking Up Trait Names](#looking-up-trait-names)` at line 337). The new section's cross-reference to Golden Test should follow this established pattern.
- The doc already documents the `<Rule Key="{WWDefaultRule}">` shape and the `Source="Explicit"` requirement (line 111). The new explicit-per-heading example must follow the same shape: `<Rule Key="Heading 1">` (not `<StylingRule Name="Heading 1">` as shown in the issue body).
- `plugins/webworks-claude-skills/skills/epublisher/SKILL.md` — should be checked to confirm no front-matter or table-of-contents reference needs updating when a new H2 lands.

### Institutional Learnings

- `docs/solutions/documentation-gaps/epublisher-format-traits-xml-schema-2026-05-09.md` — captures the schema lessons from issue #68 that produced the Golden Test recipe. The new section builds on the schema this learning hardened.

### External References

- ePublisher 2026.1 installation: `C:\Program Files\WebWorks\ePublisher\2026.1\Formats\Shared\common\behaviors\document.fti` (lines 16-23) — the `.fti` definition for `split-priority` in the Paragraph category declares three OptionClass values: `use-toc-level` (the trait default), `none`, and `number`. Both `"none"` and any integer (`"0"`, `"1"`, …) are syntactically valid.
- `C:\Program Files\WebWorks\ePublisher\2026.1\Formats\Shared\common\splits\priorities.xsl` (line 106) — the XSL split predicate is `($VarBehaviorsNode/@splitpriority != 'none') and ($VarBehaviorsNode/@splitpriority > 0)`. A paragraph triggers a split only when both clauses hold. This means `"none"` short-circuits via the first clause and `"0"` short-circuits via the second; the two values are semantically equivalent for suppressing splits.

---

## Key Technical Decisions

- **Use `Value="none"` everywhere split-priority is set to suppress splits.** Both `"none"` and `"0"` produce identical XSL behavior (see External References for the predicate). Choose `"none"` because (1) the issue body uses it, (2) it reads as "do not split here" which is semantically self-documenting versus the ambiguous "priority zero", and (3) the `.fti` declares `none` as a distinct `OptionClass` peer to `number`, indicating it is the intended way to disable splitting. Applies to both the new section and the existing Golden Test snippet for internal consistency.
- **Cross-reference the Golden Test snippet with an anchor link** (`[the Golden Test Project section](#golden-test-project)`), matching the doc's existing pattern (lines 109, 337). Anchor links carry a known silent-break risk if the section is renamed, but the doc is small and maintained, and the navigation value outweighs the risk. Section heading text must remain stable; reviewers renaming `## Golden Test Project` must update this back-link.
- **Place the new section immediately after `## Golden Test Project`** (between current line 339 and the `---` / version footer). Adjacency keeps the configuration-sharing relationship visible while preserving each section's distinct framing.

---

## Open Questions

### Resolved During Planning

- **`Value="none"` vs `Value="0"`** (origin Outstanding Question, affects R4, R6, AE3, plus R7 added during planning). Researched via `.fti` definition and `priorities.xsl` predicate. Both are valid and equivalent; `"none"` chosen for clarity (see Key Technical Decisions). The Golden Test snippet at `format-traits-guide.md:322` and the surrounding prose at line 339 will be updated to `"none"` so the doc speaks with one voice.
- **Section vs subsection** (origin Outstanding Question, affects R1). Standalone H2 chosen; rationale recorded under Assumptions because the trade-off is judgment, not research.
- **Cross-reference mechanism** (origin Outstanding Question, affects R3). Anchor link chosen; matches the doc's existing pattern (see Key Technical Decisions).
- **Heading enumeration depth** (origin Outstanding Question, affects R4). Two-heading example with a "Repeat for..." comment chosen; rationale recorded under Assumptions.

### Deferred to Implementation

- Exact prose wording for the use-case-naming sentence (R1) and the two "Effect:" lines (R2). The implementer writes copy that matches the doc's existing voice — concise, declarative, no unnecessary qualifiers.
- Whether the section needs a trait-name table (mirroring the Golden Test section's `| Internal name | UI label | Where it lives |` table at lines 331-335). If the cross-reference handles the trait-name burden, the new section can rely on the Golden Test table by reference rather than restating it. Implementer's call once the prose is drafted.

---

## Implementation Units

### U1. Align Golden Test snippet's split-priority value to "none"

**Goal:** Update the existing Golden Test snippet and surrounding prose so the entire `format-traits-guide.md` document uses `Value="none"` consistently before the new Diffable HTML Output section is added. This avoids a guide that contradicts itself between adjacent sections.

**Requirements:** R7.

**Dependencies:** None.

**Files:**
- Modify: `plugins/webworks-claude-skills/skills/epublisher/references/format-traits-guide.md` (line 322: `<Option Name="split-priority" Value="0" Source="Explicit" />` → `<Option Name="split-priority" Value="none" Source="Explicit" />`; line 339: "Setting `split-priority` to `0` on the Paragraph prototype rule cascades..." → "Setting `split-priority` to `none` on the Paragraph prototype rule cascades...")

**Approach:**
- One-line XML change in the snippet, one prose update referring to it.
- No other instances of `Value="0"` in the doc need changing — the other `split-priority` examples in the file (lines 99, 123, 176) use `Value="1"` as illustrative non-zero priorities and are not about suppressing splits; they remain unchanged.

**Patterns to follow:**
- The existing snippet's overall shape (`<FormatConfiguration>`, `<Rules Type="Paragraph" Default="{WWDefaultRule}">`, `<Rule Key="{WWDefaultRule}">`, `<Option ... Source="Explicit" />`) is the canonical shape and is preserved unchanged.

**Test scenarios:**
- Verification: read `format-traits-guide.md` end-to-end after the edit and confirm that no remaining occurrence of `split-priority="0"` appears, and that the prose at line 339 (post-edit) refers to `none` rather than `0`. `Covers AE2.` (the AE2 expectation is that the Golden Test snippet and the new section share the same XML — making them agree on the value is precondition for AE2 to hold.)

**Verification:**
- `grep -n 'split-priority' plugins/webworks-claude-skills/skills/epublisher/references/format-traits-guide.md` shows `Value="none"` at the Golden Test snippet location and `Value="1"` only at the existing illustrative-priority examples.

---

### U2. Add Diffable HTML Output section with both configuration patterns

**Goal:** Add a `## Diffable HTML Output` H2 section to `format-traits-guide.md` immediately after the `## Golden Test Project` section, framing the two settings for the diff-workflow audience and documenting the explicit-per-heading `<Rule>` pattern as an alternative to the prototype-only cascade.

**Requirements:** R1, R2, R3, R4, R5, R6.

**Dependencies:** U1 (so the cross-referenced Golden Test snippet already uses `Value="none"` when this section is added).

**Files:**
- Modify: `plugins/webworks-claude-skills/skills/epublisher/references/format-traits-guide.md` (insert the new section between line 339 and the trailing `---` / version footer at line 341)

**Approach:**
- Open the new section with a use-case sentence that names all four diff workflows from issue #40 explicitly: comparing HTML output between builds, regression testing during documentation migrations, validating that content changes do not introduce unexpected differences, and making HTML output reviewable in pull requests. This is the keyword-hit surface for AE1.
- State the relationship to Golden Test before the configuration content: "Diffable HTML output and golden testing share the same two settings; they differ only in the intent that motivates the configuration." Link to the Golden Test snippet with the anchor `[the Golden Test Project section](#golden-test-project)` for the canonical XML rather than duplicating it.
- For each of the two settings, give a brief "Effect:" line:
  - `file-processing-pretty-print="true"` — *Effect: HTML output is emitted with line breaks and indentation; a single edit shows as a localized diff instead of changing an entire minified line.*
  - `split-priority="none"` (on the Paragraph prototype rule) — *Effect: Headings no longer start new output files; each source document produces a single HTML file, so diffs show content edits rather than file additions, renames, and block moves.*
- Add a sub-area covering the prototype-only versus explicit-per-heading choice:
  - Briefly describe the prototype-only cascade as the default approach (one Option on `<Rule Key="{WWDefaultRule}">` cascades to every Paragraph style) and refer to the Golden Test snippet as its canonical example.
  - Introduce the explicit-per-heading pattern with its trade-off: more verbose, no implicit cascade, safe to use in projects that already override specific heading rules and might intercept the prototype cascade unexpectedly.
  - Provide the one-paragraph "when to choose" guidance: prototype-only for greenfield projects (concise, relies on cascade); explicit-per-heading when an existing project already overrides specific heading rules or when the team wants every behavior visible at the rule level.
  - Show the explicit-per-heading XML example: a `<Rules Type="Paragraph" Default="{WWDefaultRule}">` block inside `<GlobalConfiguration>` containing `<Rule Key="{WWDefaultRule}">`, `<Rule Key="Heading 1">`, `<Rule Key="Heading 2">`, each with `<Option Name="split-priority" Value="none" Source="Explicit" />`, followed by an XML comment `<!-- Repeat for Heading 3 through Heading 6 -->`. End with a sentence stating that the `{WWDefaultRule}` row matters even when every named style is enumerated — it catches custom Paragraph styles the user has not yet listed.
- Use the file's existing voice (declarative, concise, no qualifiers). No emojis; no second-person ("you") unless mirroring an existing usage in the same file.

**Technical design** *(directional sketch — not implementation specification):*

```markdown
## Diffable HTML Output

When the Reverb HTML output of your project participates in a diff workflow — comparing
builds across releases, regression-testing a documentation migration, validating that a
content change produced only the expected differences, or reviewing documentation edits
in a pull request — two target settings control whether the output is reviewable or
unreadable as a diff.

Diffable HTML output and golden testing share the same two settings; they differ only
in the intent that motivates the configuration. See [the Golden Test Project
section](#golden-test-project) for the canonical `<FormatConfiguration>` snippet that
configures both.

| Setting | Value | Effect |
|---|---|---|
| `file-processing-pretty-print` | `true` | HTML output is emitted with line breaks and indentation; a single edit shows as a localized diff instead of changing an entire minified line. |
| `split-priority` (on Paragraph `{WWDefaultRule}`) | `none` | Headings no longer start new output files; each source document produces a single HTML file, so diffs show content edits rather than file additions, renames, and block moves. |

### Prototype-only vs explicit-per-heading

The Golden Test snippet sets `split-priority="none"` on `<Rule Key="{WWDefaultRule}">`
once — the prototype-only cascade. Every Paragraph style inherits the value unless
that style carries an explicit override.

When a project already overrides specific heading rules (Heading 1, Heading 2, etc.),
those overrides can intercept the cascade and re-enable splits unintentionally. In that
case, set `split-priority` explicitly on each heading rule as well as on the prototype:

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

Keep the `{WWDefaultRule}` row even when every named heading is enumerated — it catches
custom Paragraph styles the project has not yet listed.

**When to choose which pattern:** prefer the prototype-only cascade for greenfield
projects where no Paragraph styles are individually overridden. Prefer
explicit-per-heading when an existing project already overrides heading rules, or when
a reviewer needs every behavior to be visible at the rule level rather than inherited.
```

**Patterns to follow:**
- Section heading style and adjacent section structure: `## Golden Test Project` at line 307. Match its tone (no second-person, no qualifiers like "simply" or "just").
- XML example formatting: lines 119-130 (`<Rule Key="{WWDefaultRule}">`) and lines 313-327 (Golden Test snippet) — 2-space indentation, `Source="Explicit"` on every Option, `Default="{WWDefaultRule}"` on every `<Rules>`.
- Anchor link form: `[The {WWDefaultRule} prototype rule](#the-wwdefaultrule-prototype-rule)` at line 109.

**Test scenarios:**
- Verification (search-discoverability): after the edit, searching the file for each of the four diff-workflow keywords — `diff`, `regression`, `pull request`, `PR review` — surfaces the new section. `Covers AE1.`
- Verification (cross-reference resolves): the markdown anchor `#golden-test-project` resolves to the existing `## Golden Test Project` heading (GitHub-flavored anchor slug computation matches that heading verbatim). `Covers AE2.`
- Verification (Effect annotations present): each of the two settings (`file-processing-pretty-print`, `split-priority`) has an "Effect" sentence describing the observable output change. `Covers AE1, R2.`
- Verification (explicit-per-heading example completeness): the XML example contains `<Rule Key="{WWDefaultRule}">`, at least one `<Rule Key="Heading N">` per heading enumerated, a "Repeat for..." comment for the remaining heading levels, and every `<Option>` carries `Source="Explicit"`. `Covers AE3, R4, R6.`
- Verification (XML schema conformance): every `<Rules>` in the example carries `Type=` and `Default="{WWDefaultRule}"`; every `<Option>` carries `Source="Explicit"`; nothing in the example violates the schema constraints stated elsewhere in the same doc (lines 109, 111, 117). `Covers AE3, R6.`
- Verification (when-to-choose paragraph present): the prose explicitly names "prototype-only" and "explicit-per-heading" patterns and gives a one-paragraph rule for choosing between them. `Covers R5.`

**Verification:**
- A reader can answer "how do I make my ePublisher HTML output diff cleanly in pull requests" from the new section alone, without consulting source code, the Reverb installation, or other documentation.
- The Golden Test section and the new Diffable HTML Output section both use `Value="none"`; no consistency drift remains.

---

## System-Wide Impact

- **Interaction graph:** Documentation-only change inside one file. No code, no scripts, no template (`plugins/webworks-claude-skills/skills/epublisher/templates/project.wep`) modifications. The skill's `SKILL.md` does not maintain a manual TOC of section headings in `format-traits-guide.md`, so no auto-generated index needs updating; the implementer should still confirm this assumption before landing.
- **Error propagation:** Not applicable.
- **State lifecycle risks:** Not applicable.
- **API surface parity:** Not applicable.
- **Integration coverage:** Not applicable.
- **Unchanged invariants:** The schema rules stated elsewhere in the file (`Source="Explicit"` required, `Default="{WWDefaultRule}"` required on `<Rules>`, `<FormatSettings>` wrapper required, etc.) are preserved verbatim by both U1 and U2; the new examples must conform to them.

---

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| Anchor link `#golden-test-project` silently breaks if a future edit renames the `## Golden Test Project` heading. | Documented in Key Technical Decisions. A future renamer who runs `ce-doc-review` on the changed section will see the broken anchor flagged; until then, the implementer adds no additional safeguard. |
| The single-source `split-priority="none"` value drifts back to `"0"` if a future docs edit re-runs Golden Test against output that records the integer form. | U1 anchors the alignment in the guide; the parallel risk lives in the Golden Test workflow itself. Out of scope for this plan to enforce in tooling. |
| `format-traits-guide.md` gains another H2 section and may eventually need a table-of-contents at the top of the file. | Out of scope. The file is still short enough that section count is manageable; revisit if it crosses ~600 lines. |
| The two-heading example mis-signals to a reader that only Heading 1 and Heading 2 need treatment. | The `<!-- Repeat for Heading 3 through Heading 6 -->` comment + the prose "explicit-per-heading pattern" framing keep the intent explicit. The "when-to-choose" paragraph reinforces that the choice is about the project's existing override surface, not about heading depth. |

---

## Documentation / Operational Notes

- No external rollout. The skill's documentation is read by Claude agents and humans at use-time; the next agent that loads `format-traits-guide.md` after this PR merges will see the new section.
- No version bump required for the skill itself; this is documentation that lives inside the skill. The repository's `scripts/bump-version.sh` (per `CLAUDE.md`) still applies at the plugin level for the PR itself.
- The `**Last Updated**` footer at `format-traits-guide.md:344` should be updated to the merge date by the implementer.

---

## Sources & References

- **Origin document:** `docs/brainstorms/2026-05-19-issue-40-diffable-html-output-requirements.md`
- Target file: `plugins/webworks-claude-skills/skills/epublisher/references/format-traits-guide.md`
- Related PR (Issue #68, merged 2026-05-19): commits `890f424`, `acd181e`, `1a97c7d` (Golden Test recipe, format-traits schema corrections, project-parsing-guide skeleton fix).
- Related learning: `docs/solutions/epublisher-format-traits-schema-gap.md`.
- External research: `C:\Program Files\WebWorks\ePublisher\2026.1\Formats\Shared\common\behaviors\document.fti` (split-priority OptionClass declarations); `C:\Program Files\WebWorks\ePublisher\2026.1\Formats\Shared\common\splits\priorities.xsl` (split predicate at line 106).
- GitHub issue: #40.
