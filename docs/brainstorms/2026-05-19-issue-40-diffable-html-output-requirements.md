---
date: 2026-05-19
topic: diffable-html-output-configuration
---

# Configuring ePublisher Projects for Diffable HTML Output

## Summary

Extend the `epublisher` skill's `format-traits-guide.md` with a use-case-driven "Diffable HTML Output" subsection that ties the existing Golden Test Project recipe to the regression-testing, PR-review, and content-change-validation workflows from issue #40, and documents the explicit per-heading `split-priority` pattern as an alternative to the prototype-only cascade.

---

## Problem Frame

When a team starts using ePublisher output (Reverb HTML) in a diff-based workflow — comparing builds between releases, reviewing documentation changes in pull requests, or verifying that a source-document edit produced only the expected HTML changes — the default output shape works against them in two specific ways:

1. **Minified output is unreviewable.** Without `file-processing-pretty-print=true`, the generated HTML is emitted as long single-line blocks. Any byte-level change touches the whole line, so a `git diff` or PR review surface shows the entire file as changed even when only one phrase moved. Reviewers cannot reason about what actually changed.
2. **One source document becomes many HTML files.** ePublisher's default `split-priority` causes paragraph styles (most often Heading 1, Heading 2) to start a new output file. A single chapter renders as a tree of small HTML files whose names and contents shift when headings are reorganized — diffs end up showing file renames and large block moves rather than the content edits the reviewer cares about.

Issue #68 (merged 2026-05-19) addressed the underlying schema and added a "Golden Test Project" recipe to `format-traits-guide.md` that already configures pretty-print, splash page, and `split-priority="0"` on the Paragraph prototype rule. That recipe is correct for golden testing but is anchored under that name and frame. Issue #40 was filed before #68 landed, against the broader problem of "make HTML diffable for any review purpose," and assumes the schema work is being done in #68. The remaining gap is presentational and motivational: a reader who arrives at the guide looking for "how do I make ePublisher output reviewable in a PR" does not find a section addressing that question by name, and the documentation does not explain when to set `split-priority` on individual heading rules versus the `{WWDefaultRule}` prototype.

---

## Requirements

**Diffable Output subsection in `format-traits-guide.md`**

- R1. Add a `## Diffable HTML Output` section (or subsection within the existing Golden Test Project section — see Outstanding Questions) that names the three diff-workflow use cases from issue #40 explicitly: comparing HTML output between builds, regression testing during documentation migrations, validating that content changes do not introduce unexpected differences, and making HTML output reviewable in pull requests.
- R2. For each of the two diffability settings (`file-processing-pretty-print`, `split-priority`), the section must include a short "Effect" sentence describing the observable change in output. Example: "Effect: HTML output is multi-line with proper indentation instead of minified."
- R3. Cross-reference (not duplicate) the existing Golden Test Project snippet for the canonical XML shape, and call out that the two configurations share the same underlying settings — diffable output and golden testing are the same configuration applied with different intent.

**Explicit-per-heading pattern**

- R4. Document the alternative pattern of setting `<Option Name="split-priority" ... />` on each individual heading `<Rule>` (Heading 1, Heading 2, etc.) in addition to the `{WWDefaultRule}` prototype, framed as "defense in depth" or "explicit-everywhere" — contrasting it with the prototype-only cascade pattern already in the Golden Test recipe.
- R5. Provide one-paragraph guidance on when to choose each pattern: prototype-only (concise, relies on cascade) for greenfield projects, explicit-per-heading (verbose, no implicit behavior) when an existing project already overrides specific heading rules and the default cascade may be intercepted.
- R6. Show the GlobalConfiguration `<Rule Key="{WWDefaultRule}">` fallback explicitly in the explicit-per-heading example, with a sentence stating that the prototype rule still matters even when every named style is configured — it catches custom styles the user has not enumerated.

---

## Acceptance Examples

- AE1. **Covers R1, R2.** Given a developer landing on `format-traits-guide.md` looking for "how do I make my ePublisher HTML output reviewable in pull requests", when they search the document for "diff", "regression", "pull request", or "PR review", then they find the Diffable HTML Output section and each setting is annotated with an "Effect" sentence that states the observable change.
- AE2. **Covers R3.** Given the new Diffable HTML Output section, when a reader compares it side-by-side with the existing Golden Test Project section, then the two sections share the same XML snippet (by cross-reference, not duplication) and the relationship between golden testing and diffable output is stated explicitly.
- AE3. **Covers R4, R5, R6.** Given a user with an existing `.wep` that already overrides Heading 1 and Heading 2 rules, when they follow the explicit-per-heading pattern documented in the section, then their `split-priority="0"` (or `"none"` — see Outstanding Questions) Options appear on each heading rule and on `<Rule Key="{WWDefaultRule}">` in `<GlobalConfiguration>`, and the section explains why both placements matter even when every named heading is covered.

---

## Success Criteria

- A user searching `format-traits-guide.md` for diff-related terms ("diff", "pull request", "regression") lands on a section that directly addresses their workflow rather than having to translate "Golden Test" into their own use case.
- A downstream agent implementing this change does not have to invent the prose framing for the use cases — issue #40's four use cases (comparing builds, regression testing, content-change validation, PR review) appear as documented use cases in the section.
- A user choosing between the prototype-only and explicit-per-heading patterns can decide from the documentation alone, without reading source code or running a test build.
- The configuration claims in the new section are consistent with the existing Golden Test recipe: same internal trait names, same XML shape, same schema (`Source="Explicit"`, `Default="{WWDefaultRule}"`).

---

## Scope Boundaries

- Not adding a new top-level reference file in `plugins/webworks-claude-skills/skills/epublisher/references/`. The content belongs co-located with the Golden Test recipe in `format-traits-guide.md`.
- Not creating a new skill for "ePublisher project configuration" — the issue body lists that as a possibility, but it would fragment the trait-configuration story now consolidated in the `epublisher` skill.
- Not duplicating the full XML snippet from the Golden Test section. Diffable Output cross-references and adds the per-heading variant only.
- Not changing `templates/project.wep`. The template stays minimal-and-correct.
- Not documenting non-diff motivations for `split-priority` or pretty-print (e.g., publishing single-page tutorials, embedded help systems) — those use cases earn their own section if they come up.
- Not addressing the splash-page setting (`show-first-document`). The issue scope is the two diffability-specific settings; splash-page is a deterministic-entry-point concern that the Golden Test section already covers.
- Not validating the `Value="0"` vs `Value="none"` discrepancy here. That is a planning-time research item (see Outstanding Questions).
- Not adding helper scripts (no `apply-diffable-config.py` or similar). The recipe is static documentation.

---

## Key Decisions

- **Frame as a use-case section, not a new skill or new reference file.** Issue #68 already placed the canonical schema and snippet in `format-traits-guide.md`; #40's value is the reframing for diff workflows, not new infrastructure.
- **Cross-reference the Golden Test snippet rather than duplicating it.** Two snippets that must stay in sync are a maintenance hazard; one snippet referenced from two sections keeps the configuration authoritative in one place.
- **Document both patterns (prototype-only and explicit-per-heading), not pick a winner.** The issue body explicitly shows the explicit-per-heading pattern with "Repeat for all heading styles" plus the `{WWDefaultRule}` fallback. Users have real reasons to prefer either; the guide should explain the choice, not impose one.
- **Defer the `Value="0"` vs `Value="none"` question to planning.** Both values appear in source material (the issue body says `none`, the merged Golden Test snippet says `0`). Resolving this requires reading the `split-priority` Option class in the Reverb format's `.fti` files — that is research, not a brainstorm decision.

---

## Dependencies / Assumptions

- Issue #68 is merged on `main` (commits `890f424`, `acd181e`, `1a97c7d`); this issue's `blocked-by: #68` is satisfied. Verified via `git log` at brainstorm time.
- `format-traits-guide.md` is the right home for the new content. Verified by reading the file — it already contains the Golden Test Project section, `split-priority` examples, and `{WWDefaultRule}` documentation. Adding diff-workflow content elsewhere would fragment the story.
- The two settings named in the issue (`file-processing-pretty-print`, `split-priority`) are the complete set required for diffable output. The issue body does not name a splash-page setting; if a future reader hits non-determinism from "first page" behavior, the existing Golden Test section already documents `show-first-document` for that case.
- The issue body's `Value="none"` may be the user's recollection rather than verified configuration. Planning will confirm the correct value against the `.fti` definition before producing the final snippet.

---

## Outstanding Questions

### Deferred to Planning

- [Affects R4, R6, AE3] [Needs research] Confirm the correct `split-priority` value. The issue body uses `Value="none"`; the Golden Test recipe in `format-traits-guide.md` (merged via #68) uses `Value="0"`. Both are syntactically plausible — `split-priority` may be either an integer-typed or enum-typed Option. Verify against the Reverb 2.0 format's `.fti` definition for `split-priority` in the installation `Formats/WebWorks Reverb 2.0/Transforms/` directory, then use the verified value in both the new section and (if different) update the existing Golden Test snippet for internal consistency.
- [Affects R1] [Technical] Decide whether "Diffable HTML Output" is a standalone `##` section in `format-traits-guide.md` or a `###` subsection nested under the existing `## Golden Test Project`. A standalone section is more discoverable for the PR-review use case; a subsection emphasizes the configuration sharing. Planning weighs against guide-page length and table-of-contents navigation.
- [Affects R3] [Technical] Decide the cross-reference mechanism — anchor link to the existing Golden Test snippet, or a "See the Golden Test Project section for the full snippet" prose pointer. Anchor links risk silent breakage if the section is renamed; prose pointers do not.
- [Affects R4] [Technical] Decide how many heading levels to enumerate in the explicit-per-heading example. The issue body uses `Heading 1` with a "Repeat for all heading styles" comment; the explicit example could show Heading 1 and Heading 2 with a comment, or all six (Heading 1 through Heading 6) at the cost of vertical space. Planning chooses based on the section's reading flow.
