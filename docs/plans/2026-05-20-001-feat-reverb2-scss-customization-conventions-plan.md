---
title: "feat: Add SCSS customization best practices to Reverb 2.0 skill"
type: feat
status: active
created: 2026-05-20
issue: 51
depth: standard
---

# feat: Add SCSS Customization Best Practices to Reverb 2.0 Skill

## Summary

Extend the `reverb2` skill with five reusable customization patterns refined during Case 00024386 (DICAD Systeme GmbH): (1) stricter rules around the project-prefixed variable convention in `_colors.scss`, (2) grepable comment annotations for non-SCSS override files, (3) cascade-order rationale for the existing `_custom-skin.scss` / `_custom-webworks.scss` split, (4) guidance for deleting overrides that match the installed default, and (5) a `locales.xml` upgrade workflow. The skill already documents the two-file split and the `$theme_` prefix; this plan deepens and disambiguates that material rather than re-introducing it.

## Problem Frame

The current `reverb2` skill teaches the three-layer SCSS model and the `$theme_` naming convention (`references/scss-architecture.md`, `workflows/scss-theming.md`). What it does not teach:

- The stricter rules that make the prefix actually useful as an upgrade audit tool: never reference intermediate variables like `$_layout_color_2` in component overrides, never invent auxiliary variables like `$link_hover_color` — always reference the prefixed variable directly. Without these rules, a single `grep '<prefix>_'` no longer enumerates every customization, defeating the purpose.
- That non-SCSS override files (`locales.xml`, `Connect.asp`, ASP/HTML templates) need their own grepable annotation pattern — comments rather than variable prefixes — to remain auditable on upgrade.
- *Why* `_custom-skin.scss` and `_custom-webworks.scss` are two files instead of one. The cascade-order constraint (`webworks.css` loads before `skin.css`) is invisible to anyone who has not been bitten by misplacing a `a { }` rule.
- What to do when, after extracting customizations, a copied entry-point file matches the installed default exactly — the override should be deleted so the resolver hierarchy serves the installed version.
- How to upgrade `locales.xml` (copy installed as the new base, re-apply customizations, annotate; do not assume untranslated strings are intentional).

These gaps were filled by hand during Case 00024386. Codifying them in the skill lets future customization work apply the same conventions without re-deriving them.

## Requirements Traceability

The issue defines five concepts to document. Each maps to implementation units below.

- **Concept 1 — `_colors.scss` Customization Pattern (strict rules):** U2 strengthens the existing `$theme_` documentation in `references/scss-architecture.md` with the "no intermediate variables, no auxiliary new variables" rules and documents the project-specific prefix variant. U3 reinforces in the workflow steps.
- **Concept 2 — Grepable Comment Annotations:** U1 (new reference file) — XML and ASP/HTML comment conventions, with the SCSS file note pointing back to the variable-prefix pattern.
- **Concept 3 — `_custom-skin.scss` / `_custom-webworks.scss` cascade-order rationale:** U2 adds the rationale to `references/scss-architecture.md` (where the two-file pattern is introduced). U3 cross-links from Step 4 and Step 5 of `workflows/scss-theming.md`.
- **Concept 4 — Removing Redundant Overrides:** U2 adds a "Removing Redundant Overrides" subsection to `references/scss-architecture.md`. U3 adds a verification check to Step 7 (Rebuild and Verify).
- **Concept 5 — `locales.xml` Upgrade Pattern:** U1 (new reference file) — full procedure with annotation convention.
- **Plugin version bump** (project convention from root `CLAUDE.md`): U5.

## Key Technical Decisions

- **Project-specific prefix is presented as a complementary variant, not a replacement for `$theme_`.** The skill currently teaches `$theme_` as a universal, project-agnostic convention. The issue's `$dicad_` pattern is the same principle applied to consultant/customer-engagement work where the prefix doubles as project identification. Both achieve grep-ability; rationale for choosing one is added to U2. The strict rules (no intermediates, no auxiliary new variables) apply identically to both — they are properties of *the convention*, not of the prefix choice.
- **New customization conventions land in a new reference file, not stuffed into `scss-architecture.md`.** The grepable-annotation pattern and the `locales.xml` upgrade procedure span non-SCSS files and don't fit under "SCSS Architecture". A new `references/customization-conventions.md` keeps the file scope honest. Cross-links go in both directions.
- **SCSS-specific concepts (cascade-order rationale, removing-redundant-overrides) land in `scss-architecture.md`.** These are properties of the existing three-layer model and belong with it. Workflow steps cross-link to them.
- **Patch version bump (2.11.0 → 2.11.1).** Per root `CLAUDE.md`: "patch: Bug fixes, documentation updates, minor improvements." This adds no new skills and no new behavior — only deepens existing skill documentation.
- **No new scripts or templates.** Pure documentation work. The existing `extract-scss-variables.py` is unaffected. The new `customization-conventions.md` reference does not gain a corresponding helper.
- **Existing `$theme_`-prefixed examples in the skill remain in place.** They are not rewritten to use `$dicad_` — using a project name in examples would imply the prefix must be a project name. The new strict rules apply to the existing `$theme_` examples too; U2 updates them in-place where they currently violate the rules (e.g., the `references/scss-architecture.md` "Example" section ends with `$link_default_color: $theme_accent;` — this is allowed under the strict rules because `$link_default_color` is a *Reverb-defined component variable*, not an auxiliary intermediate. The rules forbid *new* auxiliary variables, not assignment to existing Reverb component variables. U2 makes this distinction explicit so the strict rule is unambiguous).

## Assumptions

- The Reverb 2.0 source files in the installed format directory contain `skin.scss`, `webworks.scss`, `_colors.scss`, and `print.scss` at the paths the issue and existing skill documentation assume. The pre-verified references block shows these files are not in *this repo's tree* — they belong to the installed ePublisher format, used illustratively in skill documentation. No code in this repo needs to read them; the documentation only describes their structure and behavior.
- The Page.asp loading order (`webworks.css` before `skin.css`) is a stable property of Reverb 2.0 output. The issue states this is the cause of the two-file split; the existing skill documentation does not contradict it.
- Issue #56 (the `blocked-by` reference in the issue body) is closed (verified: it merged with "Document Reverb 2.0 runtime architecture: Pages directory"). This plan is unblocked.
- The DICAD-specific case details (Case 00024386, expanded stop words, domain-specific search synonyms) are mentioned in the plan's Origin section but the skill documentation itself stays project-agnostic — the patterns generalize.

## Implementation Units

### U1. Add `references/customization-conventions.md`

**Goal:** New reference file documenting (a) the grepable comment annotation pattern for non-SCSS override files and (b) the `locales.xml` upgrade workflow. These are file-format-agnostic conventions that don't fit under the existing "SCSS Architecture" reference.

**Requirements:** Concept 2 (annotations), Concept 5 (locales.xml upgrade).

**Dependencies:** none

**Files:**
- `plugins/webworks-claude-skills/skills/reverb2/references/customization-conventions.md` — new file

**Approach:**

Structure the file with two top-level sections:

1. **Grepable Annotations for Non-SCSS Overrides** — explain the principle: every project-specific change to a file in the override hierarchy should be locatable by a single grep across the project. SCSS files use a variable prefix (cross-link to `scss-architecture.md` § `$theme_` Naming Convention). All other file types use a comment containing a stable project identifier.

   Provide a small table:

   | File type | Comment form | Example |
   |---|---|---|
   | XML (`locales.xml`, configuration) | `<!-- PROJECT -->` or `<!-- PROJECT - description -->` | `<!-- DICAD - expanded stop words -->` |
   | ASP / HTML templates (`Connect.asp`, `Page.asp`) | `<!-- PROJECT -->` or `<%-- PROJECT --%>` | `<%-- DICAD --%>` |
   | SCSS | Use a prefixed variable (see scss-architecture) | `$dicad_primary_brand_color` |

   Add a "Why" paragraph: an upgrade auditor runs one grep per project tag (`grep -r 'DICAD' Targets/`) to find every intentional deviation. Comments survive renames the way variables do not, so the convention applies even to template files where SCSS-style prefixes aren't possible.

2. **`locales.xml` Upgrade Pattern** — four-step procedure copied verbatim (with minor formatting normalization) from the issue:

   1. Copy the installed `locales.xml` as the new base (picks up all new strings automatically).
   2. Re-apply project-specific customizations (e.g., expanded stop words, domain-specific search synonyms).
   3. Annotate each customization with a `<!-- PROJECT -->` or `<!-- PROJECT - description -->` comment.
   4. Do not assume untranslated strings are intentional customizations — verify before preserving.

   Add a short caveat: this procedure assumes the customer's `locales.xml` overrides the installed default through the file resolver hierarchy. If `locales.xml` is missing from the project, no upgrade is required — the installed default already applies.

Close the file with a `See also:` block:
- `scss-architecture.md` — `$theme_` and project-prefix variable conventions
- `../epublisher/references/file-resolver-guide.md` — how overrides are resolved

**Patterns to follow:**

- Tone, header depth, and link style match `references/scss-architecture.md`.
- Tables use the existing skill's compact column convention.
- Cross-references use repo-relative paths within the skill (`scss-architecture.md`) and `../skill-name/...` for cross-skill references.

**Test expectation:** none — documentation-only file. Verification happens in U4 (cross-link integrity) and U5 (version bump triggers the skill to be picked up).

**Verification:** File exists at the listed path. Both top-level sections (`## Grepable Annotations for Non-SCSS Overrides` and `## `locales.xml` Upgrade Pattern`) are present. Cross-links resolve to existing files.

---

### U2. Extend `references/scss-architecture.md` with strict rules, cascade-order rationale, and remove-redundant guidance

**Goal:** Strengthen the existing `$theme_` convention section with the strict rules from Concept 1, document the project-specific prefix as a complementary variant, add the cascade-order rationale for the two-file pattern (Concept 3), and add a new "Removing Redundant Overrides" subsection (Concept 4).

**Requirements:** Concept 1 (strict rules + project-prefix variant), Concept 3 (cascade-order rationale), Concept 4 (removing redundant overrides).

**Dependencies:** none (U1 and U2 can land independently; U2 cross-links to U1's file via path, which will exist by merge time).

**Files:**
- `plugins/webworks-claude-skills/skills/reverb2/references/scss-architecture.md` — modify in place

**Approach:**

Four edits to `scss-architecture.md`:

1. **Add strict rules under § `$theme_` Naming Convention** (after the "Why `$theme_`" subsection, before "Standard Tokens"). New subsection titled "Strict Rules for Prefixed Variables":

   - **Always reference the prefixed variable, never an intermediate.** When overriding a component variable, reference `$theme_*` (or `$<project>_*`) directly. Do not reference `$_layout_color_2` or `$neo_main_text_color` in the override — those are intermediaries that obscure intent and break grep-ability.
   - **Do not introduce new auxiliary variables.** If a Reverb component variable like `$link_hover_color` doesn't exist, do not invent one. Reference the prefixed variable directly at the override site. (Note: assigning a Reverb-defined component variable like `$_menu_background_color` to a prefixed variable is correct — what's forbidden is introducing *new* names that aren't part of Reverb's variable schema.)
   - **Define brand colors once, at the top of the file.** Every prefixed variable has a single definition; component variables reference it.

   Show correct vs incorrect side-by-side (mirror the issue's examples but use `$theme_` so the example stays consistent with the rest of the file):

   ```scss
   // Correct
   $toolbar_background_color:     $theme_primary_text;
   $toolbar_tab_background_color: darken($theme_primary_text, 10%);

   // Incorrect — references intermediate variable, not grep-able
   $toolbar_background_color: $_layout_color_2;

   // Incorrect — introduces new auxiliary variable
   $link_hover_color: $theme_accent;

   // Incorrect — references another component variable as intermediate
   $toolbar_tab_background_color: darken($toolbar_tabs_container_background_color, 10%);
   ```

2. **Add a "Project-Specific Prefix Variant" subsection** immediately after "Strict Rules for Prefixed Variables":

   - When a project is a customer engagement or part of a consultant portfolio, replace `$theme_` with a project-identifying prefix (e.g., `$dicad_`, `$qs_`). The grep pattern then doubles as project identification across multiple projects.
   - All other rules (strict rules, mapping to layout slots, MD3-inspired `on_` naming) apply identically.
   - Choose one prefix per project and use it consistently across `_colors.scss`, `_sizes.scss`, etc.
   - Cross-link to U1: "For non-SCSS files that also need to be locatable by project, see `customization-conventions.md`."

3. **Add "Cascade-Order Rationale" subsection at the end of § Compilation Model** (or as a new sibling subsection):

   Title: "Why Two Custom Partials, Not One"

   Body: `Page.asp` loads `webworks.css` before `skin.css`. Putting content-page overrides (a bare `a { }` link rule, paragraph styling) in `_custom-skin.scss` would elevate their specificity in the cascade and override skin chrome styles like toolbar button link colors. Splitting along the same boundary as the installed `webworks.scss` / `skin.scss` keeps custom rules at the same cascade depth as the rules they intend to override.

   Add a small "What goes where" table:

   | File | Scope |
   |---|---|
   | `_custom-webworks.scss` | Content page overrides — custom fonts, link styling, paragraph/list formatting |
   | `_custom-skin.scss` | Skin chrome overrides — toolbar, TOC, navigation, breadcrumbs, lightbox, print styles |

   Add an "Upgrade workflow" note: when upgrading the format, replace `skin.scss` and `webworks.scss` with the new installed versions and re-append the `@import` line. The `_custom-*.scss` partials need no changes.

4. **Add new top-level section "Removing Redundant Overrides"** (between "`.weplugin` Migration" and "File Resolver Integration"):

   - After extracting customizations into `_custom-*.scss` partials and prefixed variables, the copied entry-point files (`skin.scss`, `webworks.scss`, `print.scss`, etc.) may end up byte-identical to the installed version (apart from the `@import "custom-*"` line).
   - If an entry-point file matches the installed default exactly *and* has no custom imports, delete it from the override directory. The file resolver hierarchy will fall through to the installed default.
   - Example: `print.scss` whose only customization is moved to `_custom-skin.scss` as an `@media print` rule. The copied `print.scss` then matches the installed default and should be deleted.
   - Add a one-line diff workflow note: `diff [Override]/Pages/sass/print.scss [Install]/Formats/WebWorks Reverb 2.0/Pages/sass/print.scss`.

**Patterns to follow:**

- Existing tone, table style, and code-fence style in `scss-architecture.md`.
- Keep the existing `$theme_*` examples elsewhere in the file unchanged (the "Example" code block near line 148 already mostly conforms; the line `$link_default_color: $theme_accent;` is correct under the new rules because `$link_default_color` is a Reverb-defined variable, not an auxiliary).
- Maintain the existing `See also:` footer; append the new `customization-conventions.md` reference.

**Test expectation:** none — documentation-only edits. Verify by reading rendered Markdown for header hierarchy and cross-link correctness.

**Verification:** New subsections present at expected positions. Strict rules examples render with correct/incorrect labeling intact. Cascade-order section explains the loading order causally, not just descriptively. "Removing Redundant Overrides" section names the diff workflow. `See also:` footer links to `customization-conventions.md`.

---

### U3. Extend `workflows/scss-theming.md` with cascade-order cross-links and remove-redundant verification step

**Goal:** Surface the cascade-order rationale and the remove-redundant-overrides check at the point in the workflow where they apply, so an agent following the step-by-step procedure does not have to consult `scss-architecture.md` to discover them.

**Requirements:** Concept 3 (cascade-order rationale, surfacing into the workflow), Concept 4 (remove-redundant overrides, in the Rebuild and Verify step).

**Dependencies:** U2 (cross-links resolve to the new subsections in `scss-architecture.md`).

**Files:**
- `plugins/webworks-claude-skills/skills/reverb2/workflows/scss-theming.md` — modify in place

**Approach:**

Three edits to `scss-theming.md`:

1. **At the top of Step 4 (Layer 2 — Skin CSS Overrides)** add a one-line note immediately under the section heading:

   > Skin CSS overrides target the *chrome* (toolbar, TOC, navigation, breadcrumbs, popups). For why this is split from content-page overrides, see `references/scss-architecture.md` § "Why Two Custom Partials, Not One".

2. **At the top of Step 5 (Layer 3 — Content Page CSS Overrides)** add the parallel note:

   > Content page overrides target the iframe content (fonts, links, tables, mini-TOC, code blocks). Keep `a { }`, paragraph, and table rules here — putting them in `_custom-skin.scss` would incorrectly elevate their cascade specificity. See `references/scss-architecture.md` § "Why Two Custom Partials, Not One".

3. **Insert a new subsection in Step 7 (Rebuild and Verify), after the "Verify" subsection, before "Report":**

   ```
   ### Remove Redundant Overrides

   After verifying the rebuild, check whether any copied entry-point files
   (e.g., `print.scss`, `skin.scss`, `webworks.scss`) match the installed
   default. If they do — meaning all customization was extracted to
   `_custom-*.scss` partials or prefixed variables — delete the redundant
   copy. The file resolver hierarchy will fall through to the installed
   version, reducing the surface area for upgrade-time merge conflicts.

   See `references/scss-architecture.md` § "Removing Redundant Overrides"
   for the diff workflow.
   ```

   Update the success_criteria checklist at the bottom of the file to add: `[ ] Redundant override files deleted if they match installed defaults`.

**Patterns to follow:**

- Existing Step heading style (`## Step N: Title`) and subsection style (`### Subtitle`).
- Cross-references use `references/<file>.md` form, consistent with existing links in the workflow.

**Test expectation:** none — documentation-only edits.

**Verification:** Step 4 and Step 5 both have cascade-order pointers near the top. Step 7 has the "Remove Redundant Overrides" subsection placed between "Verify" and "Report". Success criteria checklist includes the redundant-override item.

---

### U4. Update `SKILL.md` to surface the new conventions reference

**Goal:** Add a pointer to `customization-conventions.md` from `SKILL.md` so an agent loading the skill discovers the broader customization conventions (not just SCSS) on first read.

**Requirements:** Cross-cutting — supports discoverability of U1 and U2 additions.

**Dependencies:** U1, U2

**Files:**
- `plugins/webworks-claude-skills/skills/reverb2/SKILL.md` — modify in place

**Approach:**

Three small edits:

1. **In the `<scss_customization>` section**, after the "Override Priority" subsection, append one line to the existing "**Detailed guidance:**" paragraph (currently the last line of the section) to add the new reference:

   > **Detailed guidance:** `workflows/scss-theming.md` (layer-specific steps), `references/scss-architecture.md` (cascade diagrams, compilation model, strict variable rules), `references/customization-conventions.md` (annotations for non-SCSS overrides, `locales.xml` upgrade).

2. **In the `<common_mistakes>` section**, update the existing `.weplugin` paragraph's tail (currently `...see references/scss-architecture.md.`) to also mention the conventions reference:

   > ... For structural CSS beyond variables, create `_custom-skin.scss` (chrome) or `_custom-webworks.scss` (content) — see `references/scss-architecture.md` § "Why Two Custom Partials, Not One". For non-SCSS overrides (`locales.xml`, ASP templates), see `references/customization-conventions.md`.

3. **No new top-level section.** Resist adding a new XML tag like `<customization_conventions>` — discoverability is via the references list, not a duplicate prose section. Avoids drift between SKILL.md prose and the reference file.

**Patterns to follow:**

- The `**Detailed guidance:**` line convention already in use at the end of `<scss_customization>`.
- Backticks for file references, exactly as the surrounding lines use them.

**Test expectation:** none — documentation-only edits.

**Verification:** The two cross-references appear in the listed locations. No duplicated content between SKILL.md and the new reference file.

---

### U5. Bump plugin version 2.11.0 → 2.11.1

**Goal:** Increment plugin version to publish the documentation update through the plugin marketplace.

**Requirements:** Project convention from root `CLAUDE.md` Version Management section.

**Dependencies:** U1, U2, U3, U4 (bump happens last, after the documentation is final).

**Files:**
- `plugins/webworks-claude-skills/.claude-plugin/plugin.json` — version field
- `.claude-plugin/marketplace.json` — version field (must stay in lockstep)

**Approach:**

Use the project's bump script per `CLAUDE.md`:

```
scripts/bump-version.sh patch
```

This updates both files atomically. Patch level is correct because the change is "documentation updates, minor improvements" per `CLAUDE.md` versioning rules — no new skills, no new behavior, no breaking changes.

**Patterns to follow:**

- The existing version-bump workflow in `CLAUDE.md` § Version Management.
- Existing recent PRs (e.g., 2.10.x → 2.11.0 lineage) for commit-message shape.

**Test expectation:** none — version-bump only. Verification is the version-equality check below.

**Verification:**
- `plugin.json` and `marketplace.json` both read `"version": "2.11.1"`.
- Running `scripts/bump-version.sh patch` did not error.

## Scope Boundaries

In scope:

- Documentation additions and edits to the `reverb2` skill covering the five concepts from issue #51.
- One new reference file (`customization-conventions.md`) under `reverb2/references/`.
- Cross-references between SKILL.md, the existing scss-architecture reference, the existing scss-theming workflow, and the new conventions reference.
- Plugin version bump (patch).

Out of scope:

- Changes to the `epublisher` skill (file resolver hierarchy is already documented there; this plan only cross-links to it).
- Changes to the `automap` or `markdown-integration` skills.
- New helper scripts under `reverb2/scripts/` — this is a documentation-only change.
- Rewriting the existing `$theme_` examples to use a different prefix. The existing examples stay; the strict rules apply to them, but the rules already permit the existing forms.
- Generalizing the `locales.xml` upgrade pattern to all XML files in the project. The issue scopes it to `locales.xml`; broader XML guidance can come later if patterns emerge.

### Deferred to Follow-Up Work

- A dedicated "Upgrade Workflow" reference or workflow file that consolidates upgrade guidance across SCSS files, `locales.xml`, and `.weplugin` migration. The current plan adds the new pieces to existing locations; a future consolidation pass can extract them if upgrade work becomes frequent enough to warrant a unified entry point.
- An `extract-customizations.sh` helper that runs the grep patterns (`grep '<prefix>_'`, `grep 'PROJECT'`) and prints a customization inventory. Useful but not requested; the manual grep commands in the documentation are sufficient for now.

## Risks

- **Strict-rule subsection contradicts an existing example.** The existing "Example" block in `scss-architecture.md` ends with `$link_default_color: $theme_accent;`. The strict rules forbid auxiliary new variables but not assignment to existing Reverb component variables. U2 must call this distinction out explicitly, or future readers will read the strict rules as contradicting the example. Mitigation: U2 adds a parenthetical clarification ("Note: assigning a Reverb-defined component variable like `$_menu_background_color` to a prefixed variable is correct — what's forbidden is introducing *new* names that aren't part of Reverb's variable schema.").
- **Cascade-order rationale could be misread as prescribing implementation detail.** The reason for two files is the cascade-order constraint; future Reverb versions could in principle re-order CSS loading. Mitigation: phrase the rationale as "Reverb 2.0 loads `webworks.css` before `skin.css`" — version-scoped, not "always".
- **`locales.xml` upgrade procedure may not apply if the customer never overrides it.** A user reading the conventions reference might assume the procedure is universally required. Mitigation: the U1 caveat ("If `locales.xml` is missing from the project, no upgrade is required") addresses this directly.
- **Project-prefix variant could be misread as encouraging deviation from `$theme_`.** Mitigation: U2 frames `$theme_` as the default; the project-specific prefix is described as a variant for consultant/customer-engagement scenarios where the prefix doubles as project identification.

## System-Wide Impact

- **Skill discovery:** Existing skill triggers in the description (`Use when ... customizing SCSS themes`) already match this work — no description update needed.
- **Plugin consumers:** Users who already invoke the SCSS theming workflow will see deeper guidance on next invocation. No behavior change for consumers who do not touch SCSS or `locales.xml`.
- **Other skills:** `epublisher` skill references unchanged. `automap` skill (used to rebuild after SCSS changes) unaffected. `markdown-integration` skill unaffected.
- **Tests:** No automated tests in the reverb2 skill currently cover SCSS documentation. Existing tests (`tests/verify-landmark-resolver.py`) are unaffected.

## Verification Strategy

After all units land:

1. Load the `reverb2` skill in a fresh session and request "SCSS customization for project X using a project-specific prefix" — the agent should surface the strict rules, the cascade-order rationale, and the project-prefix variant.
2. Request "I'm upgrading the format version, what do I need to do for `locales.xml`?" — the agent should surface the four-step procedure from `customization-conventions.md`.
3. Request "I have a `print.scss` override that matches the installed default" — the agent should suggest deletion per the new "Removing Redundant Overrides" section.
4. Confirm version is `2.11.1` in both `plugin.json` and `marketplace.json`.
5. Skim rendered Markdown for each modified file to check header hierarchy and link integrity.

## Origin

These patterns were developed and validated during Case 00024386 (DICAD Systeme GmbH), where a customer project was upgraded from mixed 2024.1/2025.1 to clean 2025.1 and then refactored to follow these conventions. The customer-specific prefix (`$dicad_`) and the `locales.xml` customizations (expanded stop words, domain-specific search synonyms) were the proving ground; the patterns themselves generalize to any Reverb 2.0 customization engagement.
