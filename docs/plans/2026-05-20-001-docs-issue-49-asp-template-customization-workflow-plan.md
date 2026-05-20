---
title: "docs: Document ASP template customization workflow for custom images and assets"
type: docs
status: completed
created: 2026-05-20
issue: 49
depth: lightweight
---

# docs: Document ASP Template Customization Workflow for Custom Images and Assets

## Summary

Add a new "Workflow 4: Customizing ASP Templates with Custom Assets" subsection to the epublisher skill's `file-resolver-guide.md` so an agent customizing `Header.asp`, `Footer.asp`, or `Connect.asp` knows the full end-to-end workflow — copy the template at the right override level, wrap (do not strip) existing `.ww_skin_*` classes that drive variable-based sizing, place assets alongside the template using the `wwpage:attribute-src` pattern (already documented by PR #86), and put new structural CSS in `_custom-skin.scss` rather than editing `skin.scss` directly. Bump the plugin patch version per repo convention.

---

## Problem Frame

The `wwpage:attribute-src` *mechanism* is now documented in `file-resolver-guide.md` under `## Advanced Topics` (added by PR #86, closing #48). The mechanism doc covers syntax, variants, file placement, the `Files/`-directory contrast, and a split-logo example. It does **not** cover the broader practical pitfalls that show up when an agent uses that mechanism inside a real Header/Footer override.

Three classes of mistake recur in real customizations (surfaced during the Radware customization, Case 00024362):

1. **Stripping existing class hierarchy.** When an agent restructures a Header template to add new layout containers (e.g., `.ww_skin_header_logo_left` / `.ww_skin_header_logo_right`), it tends to remove the intermediate wrapper `.ww_skin_header_logo_container` because the new outer divs *look* sufficient. Doing so silently disables the variable-driven sizing and padding that `skin.scss` applies through that exact class (`$header_logo_container_padding`, `$header_logo_height`, `$header_logo_width`). The build still succeeds; the output silently loses its theme.

2. **Putting new structural CSS in the wrong place.** When adding rules for new wrapper classes (`.ww_skin_header_logo_left`, `.ww_skin_header_logo_right`), an agent without guidance edits the copied `skin.scss` directly or invents a fresh `_custom.scss` that does not match the skill's established `_custom-skin.scss` / `_custom-webworks.scss` convention. Both choices undermine maintainability (skin.scss diffs against installation become noisy; an unconventional partial name is unfindable).

3. **Asset placement that drifts away from the override directory.** Even after PR #86, the natural agent failure mode is to drop logos into `Files/` (because that's the assets directory the agent already knew about) or to invent a project-root `assets/` folder. The `wwpage:attribute-src` doc explains the mechanism in isolation; the workflow doc has to make it the obvious first choice when the task is "add an image to Header.asp".

The fix is documentation-only: add a workflow-shaped section that walks the agent through the complete customization in dependency order (copy template → preserve existing wrappers → place assets → add structural CSS via `_custom-skin.scss`), cross-referencing the existing mechanism doc (#48) and SCSS override pattern (`Workflow 3`) rather than duplicating them.

---

## Requirements Traceability

The issue body specifies the content shape directly. The four lessons map to one implementation unit:

- **Lesson 1 — Preserve existing CSS class structure** (issue § 1: "do not remove intermediate wrapper elements"; wrap, do not strip) → U1
- **Lesson 2 — File placement for `copy-relative-to-output-root`** (issue § 2: `Pages/images/` next to the template, contrasted with `Files/`) → U1 (cross-references #48's mechanism doc; does not duplicate it)
- **Lesson 3 — Two variants of the attribute** (`copy-relative-to-output-root` vs `-with-generation-hash`) → U1 (already covered in detail by #48; workflow section just names which to pick for branding images and points to the existing variants table)
- **Lesson 4 — Custom CSS for new structural elements goes in `_custom-skin.scss`** (issue § 4 calls this file `_custom.scss`; the skill convention is `_custom-skin.scss` for chrome — see `references/file-resolver-guide.md` Workflow 3 and `../../reverb2/SKILL.md` SCSS Customization) → U1
- **Patch version bump** (project convention from `CLAUDE.md`: docs updates are `patch`) → U1
- **Suggested location: "Workflow 4: Customizing ASP Templates with Custom Assets"** (issue § "Suggested Documentation Location" first option) → U1

---

## Key Technical Decisions

- **Placement: under `## Common Customization Workflows`, not as a new reference file.** The issue suggests two locations: (a) a new "Workflow 4" subsection in the existing `Common Customization Workflows` section, or (b) a new `references/asp-template-customization.md` file. Option (a) wins because:
  - Workflows 1-3 in that section already cover related customizations (single-file format-level copy, target-specific copy, SCSS override pattern). A "Workflow 4" extends an established progression rather than creating a parallel surface.
  - A new top-level reference file would force the SKILL.md to add a new `<references>` entry and would split ASP customization context across two files (mechanism in `file-resolver-guide.md`, workflow in `asp-template-customization.md`).
  - Workflow-shaped content next to mechanism-shaped content in the same document is the same reading mode an agent already uses — they search the file for "ASP" or "Header.asp" and find both.

- **Cross-reference, do not duplicate, the mechanism documented by #48.** PR #86 added `### Copying Custom Assets in ASP Templates` under `## Advanced Topics` covering syntax, variants, file placement, the `Files/` contrast, the file-based vs setting-based resolver contrast, and the split-logo example. Workflow 4 should mention these in step order and link to that subsection rather than restating its content. Duplicate content drifts over time; a single sentence reference does not.

- **Use `_custom-skin.scss`, not `_custom.scss`.** The issue body uses the unprefixed name `_custom.scss`. The skill's established convention is `_custom-skin.scss` (chrome, `.ww_skin_*` selectors) and `_custom-webworks.scss` (content page inside iframe) — see `references/file-resolver-guide.md` Workflow 3 and `../reverb2/SKILL.md` Three-Layer Architecture. Header logo containers are chrome selectors, so the right file is `_custom-skin.scss`. The plan and resulting doc must use the skill convention so the new workflow lands in the same partial the rest of the skill points to. The doc should not silently rename the issue's example — it should call out the mapping ("chrome selectors like `.ww_skin_header_logo_*` go in `_custom-skin.scss`") so a reader who came from the issue understands the choice.

- **Use the `$theme_` prefix convention, not `$rad_`.** The issue uses `$rad_header_art_logo_*` (Radware project convention). The skill's established custom-variable prefix is `$theme_` — see `../reverb2/SKILL.md` `$theme_` Naming Convention and `references/file-resolver-guide.md`. The doc should use `$theme_` in the example and add a one-sentence note that projects may substitute their own prefix as long as it is greppable. This keeps the doc consistent with the rest of the skill while preserving the issue's intent.

- **Do not modify the `reverb2` skill.** The issue says to cross-reference reverb2 "if Header.asp/Footer.asp customization is documented there". It currently is not — `reverb2/SKILL.md` mentions `Pages/*.asp` only as a runtime-architecture pointer. PR #86 reached the same conclusion (its plan defers a reverb2 cross-reference). The workflow doc in `epublisher/` may link *to* the reverb2 SCSS layer model where helpful, but reverb2 itself is unchanged in this PR.

- **Patch version bump (2.12.2 → 2.12.3).** Per `CLAUDE.md` Version Management: "patch: Bug fixes, documentation updates, minor improvements". Documentation-only changes are patch. (Note on current numbering: this branch is based on `main` at `b425d37` which still shows `2.12.1` because PR #86 — which bumped to `2.12.2` — has not yet merged into this branch. When this work merges into main, the version flow is `2.12.1 → 2.12.2 (PR #86) → 2.12.3 (this PR)`. The bump script always increments from the current `plugin.json` value, so the implementer just runs `scripts/bump-version.sh patch` once whatever value `plugin.json` carries at the time.)

---

## Assumptions

- The four lessons described in issue #49 (wrap-don't-strip, `Pages/images/` placement, variant choice, `_custom-skin.scss` for new structural CSS) accurately describe the failure modes the customizer hit. Per `epublisher/SKILL.md`: "Do not use training data for ePublisher" — the issue body and the issue requester's direct experience (Case 00024362) are the authoritative sources. The plan reproduces the lessons without independent verification against ePublisher source.
- The variable names `$header_logo_container_padding`, `$header_logo_height`, `$header_logo_width` referenced in the issue body exist in the base install `skin.scss` for Reverb 2.0. The doc reproduces these names verbatim from the issue; if any are misremembered, the doc inherits the error but the surrounding guidance (preserve existing wrapper classes) remains correct regardless of the specific variable names.
- The `wwpage:attribute-src` mechanism documented by PR #86 is the canonical asset-copy pattern for ASP overrides — there is not a second equally-valid pattern this workflow should also document. (The `Files/` directory is documented as the contrast, not an alternative.)
- PR #86 will be merged before this PR is reviewed, so the workflow can reference the `### Copying Custom Assets in ASP Templates` subsection under `## Advanced Topics` by name. If by some accident PR #86 has not landed when the implementer starts, the implementer should rebase onto a main that includes it before writing the workflow — the workflow's whole structure depends on that section existing to link to.

---

## Implementation Units

### U1. Add "Workflow 4: Customizing ASP Templates with Custom Assets" and bump plugin version

**Goal:** Add a single new `### Workflow 4: Customizing ASP Templates with Custom Assets` subsection under the existing `## Common Customization Workflows` H2 in `file-resolver-guide.md`, sequenced after `### Workflow 3: SCSS Override Pattern (For Structural CSS Changes)` and before the next H2 (`## File Types and Locations`). Bump the plugin to the next patch version per repo convention.

**Requirements:** All four lessons from the issue body (preserve wrappers, asset placement, variant choice, `_custom-skin.scss` for new CSS) + version bump per `CLAUDE.md`.

**Dependencies:** PR #86 merged into main (the workflow links to the `### Copying Custom Assets in ASP Templates` subsection PR #86 introduced; rebase onto a post-#86 main before implementing).

**Files:**

- `plugins/webworks-claude-skills/skills/epublisher/references/file-resolver-guide.md` — modify (add new `### Workflow 4` subsection at the end of `## Common Customization Workflows`, after Workflow 3, before `## File Types and Locations`)
- `plugins/webworks-claude-skills/.claude-plugin/plugin.json` — modify (`version: 2.12.2 → 2.12.3`, assuming PR #86 has merged and brought the value to 2.12.2)
- `plugins/webworks-claude-skills/.claude-plugin/marketplace.json` — modify (kept in sync with `plugin.json` per `CLAUDE.md`; use `scripts/bump-version.sh patch`)

**Approach:**

Run `scripts/bump-version.sh patch` from the repo root to bump both manifests atomically.

In `file-resolver-guide.md`, add a new H3 subsection inside the existing `## Common Customization Workflows` H2. Place it after `### Workflow 3: SCSS Override Pattern (For Structural CSS Changes)` and before the `## File Types and Locations` H2. Header text: `### Workflow 4: Customizing ASP Templates with Custom Assets`.

The subsection covers, in this order:

1. **One-paragraph framing.** When customizing an ASP template (`Header.asp`, `Footer.asp`, `Connect.asp`) to add new structural elements that reference custom images or scripts, four decisions matter in order: which override level to copy to, what to do with the existing `.ww_skin_*` class hierarchy, where to place the asset files, and where to put any new structural CSS. Skipping any one of them produces a build that succeeds but silently loses theme or breaks paths.

2. **Step 1 — Copy the template to the right override level.** One short paragraph plus a code block. Reuse the override-level decision from Workflows 1 and 2 (target-level vs format-level) with a one-line pointer back to those workflows. Show a `copy-customization.py` invocation copying `Header.asp` from the installation to the format-level override directory.

3. **Step 2 — Wrap, do not strip, existing `.ww_skin_*` classes.** This is the centerpiece. Two fenced code blocks contrasting WRONG (strips `.ww_skin_header_logo_container`) and CORRECT (wraps new structural divs around the existing class hierarchy). Include the explanatory paragraph: `.ww_skin_header_logo_container` carries the variable-driven `padding`, `height`, and `width` rules from `skin.scss` (`$header_logo_container_padding`, `$header_logo_height`, `$header_logo_width`); removing the class disables those rules silently. A general rule follows the example: *when adding new structural elements around an existing themed element, the new elements should wrap the existing class hierarchy, not replace it.*

4. **Step 3 — Place custom assets in the override directory next to the ASP file.** Brief description plus an ASCII tree showing `Formats/WebWorks Reverb 2.0/Pages/Header.asp` alongside a `Pages/images/` subdirectory holding the custom logos. One sentence routing readers to the existing `### Copying Custom Assets in ASP Templates` subsection under `## Advanced Topics` for the `wwpage:attribute-src` syntax, variants table, and the `Files/` contrast — do not duplicate that content. One sentence answering the variant question: branding images that should match the rebuild cycle use `copy-relative-to-output-root`; scripts and assets that need cache-busting use `copy-relative-to-output-root-with-generation-hash` (the base install uses the hashed variant for `Connect.asp`, `Page.asp`, `Splash.asp` scripts and splash images).

5. **Step 4 — Add new structural CSS in `_custom-skin.scss`.** When the new wrappers (e.g., `.ww_skin_header_logo_left`, `.ww_skin_header_logo_right`) need their own rules, those rules belong in `_custom-skin.scss`, not in the copied `skin.scss` and not in a new arbitrarily-named partial. One sentence explaining why: keeps `skin.scss` diffable against the installation and keeps custom CSS greppable in one well-known partial. One-sentence pointer to `### Workflow 3: SCSS Override Pattern` for the `_custom-skin.scss` setup steps (creating the partial, adding the `@import` to the copied `skin.scss`) — do not duplicate. A fenced SCSS block shows the rules for the split-logo example using the `$theme_` prefix convention (`$theme_header_art_logo_height`, `$theme_header_art_logo_width`) with a one-sentence note that projects may substitute their own prefix as long as it is greppable.

6. **Common pitfall summary** — a tight three-row table listing each silent-failure pattern (Stripped existing class / Asset in `Files/` / New CSS in `skin.scss`), the symptom (theme variable not applied / wrong relative path in multi-group output / noisy diff against installation), and the fix (wrap don't strip / `Pages/images/` + `wwpage:attribute-src` / `_custom-skin.scss`). This serves as the agent's quick-reference and the human reviewer's checklist.

7. **End-to-end example** — a fenced HTML block reproducing the split-logo Header.asp markup (left/right wrappers, each containing `.ww_skin_header_logo_container` with a `.ww_skin_header_logo` image using `wwpage:attribute-src="copy-relative-to-output-root"`). Two-three lines of explanatory prose name the directory the assets sit in and the SCSS partial the wrapper rules live in. The HTML in this block must keep `.ww_skin_header_logo_container` present (matching the CORRECT block from Step 2), so the same example carries the workflow's central lesson all the way through.

**Patterns to follow:**

- **Workflow-section structure (numbered Steps under an H3 workflow heading)** — see existing `### Workflow 1`, `### Workflow 2`, `### Workflow 3` under `## Common Customization Workflows` in the same document (currently around lines 248-385 in the pre-#86 file; post-#86 line numbers will shift because PR #86 added content further down). Each existing workflow starts with `**Scenario:** ...` and then numbered `**Steps:**`. Workflow 4 should adopt the same shape so the new section reads continuously with the previous three.
- **Wrong/Right contrast block pattern** — match the `**INVALID Examples:**` block at lines 161-174 of the same file (case mismatches, missing intermediate folders). The wrap-don't-strip contrast in Step 2 is the same shape: a WRONG block followed by a CORRECT block, each annotated with a comment line explaining the contrast.
- **ASCII tree style** — match the project-structure tree at lines 11-23 and the override-path trees at lines 132-158. The asset-placement tree in Step 3 should use the same indent and `←` arrow style.
- **Two-column tables (When-to-Use / Pitfalls)** — match the existing two-column tables already used in the document (e.g., the override-file table at the top of Workflow 3 around lines 343-346, the SCSS partial inventory at lines 416-422). The pitfall summary table in step 6 uses the same shape with three columns.
- **Cross-reference style** — match the "see also" references already present elsewhere in the doc (e.g., "**For complete details, see:** references/file-resolver-guide.md" pattern used in `epublisher/SKILL.md`). Cross-references from Workflow 4 to (a) `### Copying Custom Assets in ASP Templates` under `## Advanced Topics`, (b) `### Workflow 3: SCSS Override Pattern`, and (c) `../reverb2/SKILL.md` SCSS Customization should all use the same `**See also:**` or inline "(see `...`)" style consistently.
- **Version bump procedure** — `CLAUDE.md` Version Management section; use `scripts/bump-version.sh patch`.

**Test scenarios:**

Test expectation: none — this is a documentation-only change. The unit modifies only Markdown reference content and version-manifest JSON; no runtime behavior changes. Verification is by reading the rendered section against the requirements list and Approach checklist above.

Manual verification scenarios for the implementer:

- An agent reading the new Workflow 4 cold (no chat context, no access to the issue body) can complete a Header.asp customization that adds left/right logos without (a) stripping `.ww_skin_header_logo_container`, (b) placing assets in `Files/`, or (c) editing the copied `skin.scss` to add the new wrapper rules.
- An agent searching `file-resolver-guide.md` for "Header.asp" finds Workflow 4 and, from there, can navigate to the `### Copying Custom Assets in ASP Templates` mechanism subsection and to Workflow 3 for the `_custom-skin.scss` setup.
- An agent searching for "_custom.scss" (the name used in the issue body) is not led astray — the doc consistently uses `_custom-skin.scss` and explains that chrome selectors belong in that file.
- The wrap-don't-strip rule survives copy-paste: an agent pasting the CORRECT block from Step 2 into a customized Header.asp keeps `.ww_skin_header_logo_container` present in the output.
- The end-to-end example in Step 7 matches the CORRECT block from Step 2 (i.e., both keep `.ww_skin_header_logo_container`) — readers comparing the two find no inconsistency.
- `plugin.json` and `marketplace.json` report the same new patch version (whatever increment the bump script produces — `2.12.3` if PR #86 has merged first).

**Verification:**

- New `### Workflow 4: Customizing ASP Templates with Custom Assets` heading appears under `## Common Customization Workflows` in `file-resolver-guide.md`, after Workflow 3 and before the next H2 (`## File Types and Locations`).
- The subsection covers all seven content elements listed in the Approach above, in the stated order.
- The wrap-don't-strip example in Step 2 is internally consistent with the end-to-end example in Step 7 (both keep `.ww_skin_header_logo_container`).
- The doc uses `_custom-skin.scss` and `$theme_` prefix throughout, with explicit notes mapping from the issue's `_custom.scss` / `$rad_` names.
- The doc cross-references (does not duplicate) the `### Copying Custom Assets in ASP Templates` subsection under `## Advanced Topics` and `### Workflow 3: SCSS Override Pattern`.
- `plugins/webworks-claude-skills/.claude-plugin/plugin.json` and `plugins/webworks-claude-skills/.claude-plugin/marketplace.json` report the same new patch version produced by `scripts/bump-version.sh patch`.
- No other files modified. Specifically, `reverb2/SKILL.md`, `epublisher/SKILL.md`, and the existing Workflows 1-3 are unchanged.

---

## Scope Boundaries

**In scope:**

- One new H3 subsection (`### Workflow 4: Customizing ASP Templates with Custom Assets`) in `plugins/webworks-claude-skills/skills/epublisher/references/file-resolver-guide.md`, under the existing `## Common Customization Workflows` H2.
- Patch version bump in both plugin manifests via `scripts/bump-version.sh patch`.

**Out of scope:**

- Creating a new `references/asp-template-customization.md` file. The issue lists this as an alternative location; Key Technical Decisions selected the Workflow 4 placement instead.
- Modifying `reverb2/SKILL.md` or any other skill. The issue conditions a reverb2 cross-reference on "if Header.asp/Footer.asp customization is documented there", which it currently is not.
- Documenting Footer.asp / Connect.asp specifics beyond naming them as templates the same workflow applies to. The issue's examples and lessons all come from Header.asp customization; the doc generalizes by saying "Header.asp, Footer.asp, or Connect.asp" but does not invent footer- or connect-specific lessons that have not been observed.
- Independent verification of `wwpage:attribute-src` behavior, `skin.scss` variable names, or the exact set of base-install templates that use the `-with-generation-hash` variant. See Assumptions.
- Adding executable validation (lint scripts, link checkers) for the new doc content. The skill currently has no such infrastructure; adding it is a separate concern.

**Deferred to Follow-Up Work:**

- If a Header/Footer ASP customization workflow is later added to `reverb2/SKILL.md`, that PR can add a cross-reference there pointing back to Workflow 4. (Same disposition PR #86 took for its mechanism subsection.)
- If repeated agent confusion shows that Footer.asp or Connect.asp have customization patterns that differ meaningfully from Header.asp, add per-template workflows in a follow-up.
- A `docs/solutions/` learnings entry (in the style of `docs/solutions/documentation-gaps/epublisher-wwpage-attribute-src-asp-template-assets-2026-05-20.md`) capturing the wrap-don't-strip rule and the workflow-shape decision could be added in the same PR if the implementer wants to consolidate, but it is not required by the issue and not strictly needed if the skill's doc itself is clear.

---

## Risks

- **The four lessons are reproduced from issue #49 without independent verification.** If `$header_logo_container_padding`, `$header_logo_height`, `$header_logo_width` are not the exact variable names in the base install, the doc inherits the error. Mitigation: the workflow's structural guidance (wrap don't strip, `_custom-skin.scss`, `Pages/images/`) holds regardless of the specific variable names. If a variable name is wrong, a follow-up edit fixes the example without restructuring the section. The doc may also frame the variable list illustratively ("variables like `$header_logo_*`") to soften the dependency on exact names.
- **The new Workflow 4 partly overlaps with the `### Copying Custom Assets in ASP Templates` subsection added by PR #86 (mechanism) and with `### Workflow 3: SCSS Override Pattern` (SCSS partial setup).** If readers stop at Workflow 4 without following the cross-references, they may miss mechanism syntax or the `@import` setup detail. Mitigation: Workflow 4 explicitly names the linked sections at the points where they matter (Step 3 for `wwpage:attribute-src`, Step 4 for `_custom-skin.scss` setup) and the linked sections are in the same file, one screen away.
- **The doc renames the issue's `_custom.scss` to `_custom-skin.scss` and the issue's `$rad_` prefix to `$theme_`.** A reader who came from the issue may briefly find the names different. Mitigation: the doc explicitly calls out the mapping ("the skill convention is `_custom-skin.scss` for chrome selectors" and "use the `$theme_` prefix or any greppable project-specific prefix") so the reader sees the alignment immediately rather than wondering whether they are reading the wrong section.
- **Dependency on PR #86 being merged first.** If this work somehow lands before PR #86, the cross-reference to `### Copying Custom Assets in ASP Templates` would point to a section that does not yet exist. Mitigation: the Dependencies field on U1 names this explicitly; the implementer rebases onto a post-#86 main before writing.
