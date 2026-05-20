---
title: "feat: Document Reverb 2.0 runtime architecture (Pages directory)"
type: feat
status: active
date: 2026-05-20
origin: plans/knowledge-gaps-from-audit.md (item #16)
issue: 56
---

# feat: Document Reverb 2.0 runtime architecture (Pages directory)

## Summary

Add a focused `## Runtime Architecture` section to `plugins/webworks-claude-skills/skills/reverb2/SKILL.md` that names the three source types in `<format name>/Pages/` (`scripts/*.js`, `*.asp`, `sass/*.scss`) and explains how each maps to published output. Frame the section as the starting point for diagnosing any Reverb 2.0 runtime issue. Bump the plugin version with `scripts/bump-version.sh patch`.

---

## Problem Frame

The reverb2 skill has no dedicated description of the runtime file structure within a Reverb 2.0 format. The `Pages/` source tree is mentioned twice in passing — once in the `<objective>` proprietary-knowledge warning at SKILL.md:15 and once in the `<common_mistakes>` "Reverb output is not the format source" note at SKILL.md:319 — but neither location gives a structured, discoverable explanation of what lives there or how each source type transforms into runtime output. A reader investigating a runtime bug, theme override, or generated HTML/CSS/JS discrepancy has no single "start here" section to anchor diagnosis.

This gap is item #16 in `plans/knowledge-gaps-from-audit.md`. PR #55 closed items 0-15 (the epublisher skill gaps); items 16-17 cover the reverb2 skill. Item #16 is the architecture/discovery breadcrumb; item #17 (deprecated `.weplugin` cleanup, already covered in SKILL.md `<common_mistakes>` at lines 317-319) is a separate concern handled outside this plan.

---

## Requirements

- R1. State explicitly that Reverb 2.0 runtime output is built from three source types in `<format name>/Pages/`. (Carried from audit item #16.)
- R2. Document `scripts/*.js` — JavaScript behavior (keyboard shortcuts, search, navigation, etc.). (Carried from audit item #16.)
- R3. Document `*.asp` — HTML templates that become `.html`/`.htm` in published output. (Carried from audit item #16.)
- R4. Document `sass/*.scss` — styles that become `.css` in published output; `_*.scss` files are configurable variable collections. (Carried from audit item #16.)
- R5. Frame the section as the starting point for diagnosing any runtime issue in Reverb 2.0 output. (Carried from audit item #16.)
- R6. **Plan-derived.** Cross-reference the existing `references/scss-architecture.md` and the `## SCSS Customization` section for readers who land on the new section and need deeper SCSS guidance — avoid duplicating partials inventory or theming workflows.
- R7. **Plan-derived.** Bump the plugin version with `scripts/bump-version.sh patch` per CLAUDE.md (documentation update qualifies as patch).

---

## Assumptions

*This plan was authored without synchronous user confirmation. The items below are agent inferences that fill gaps in the input — un-validated bets that should be reviewed before implementation proceeds.*

- **Place the new content in `SKILL.md` as a key-concept section, not in a new reference file under `references/`.** The audit breadcrumb is short (about five bullets) and explicitly foundational ("starting point for diagnosing any runtime issue"). Co-locating it with `<overview>` matches how the skill currently surfaces top-level concepts (Overview, Related Skills, Routing, Capabilities). A standalone reference file would bury the breadcrumb behind a click; readers diagnosing a runtime issue need it on first read. If reviewers prefer a `references/runtime-architecture.md` file instead, the prose lifts cleanly with no other restructuring required.
- **Insert the new section as `<runtime_architecture>` between `<overview>` and `<related_skills>`.** This places it where the proprietary-knowledge warning at SKILL.md:15 already gestures at the `Pages/` paths, giving readers the structured explanation immediately after the conceptual overview. Alternative placements (after `<capabilities>`, after `<common_mistakes>`) bury foundational architecture below operational mechanics.
- **Do not rewrite the existing SKILL.md:15 proprietary-knowledge warning or the SKILL.md:319 `<common_mistakes>` note.** Both mention `Pages/scripts/*.js`, `Pages/*.asp`, and `Pages/sass/*.scss` and remain accurate. Removing or rewording them risks losing the "do not use training data" framing that those sections carry and is out of scope for this gap. The new `<runtime_architecture>` section consolidates the structured explanation; the existing references continue to gesture toward it.
- **Match the existing skill's table-first presentation style.** Other skill sections (Capabilities, SCSS Partials Inventory, Override Priority, DOM Component IDs) lead with a markdown table summarizing the structured content, followed by prose for the framing claim. The new section should follow the same shape: a three-row table mapping source path → published output → role, preceded by the framing sentence and followed by the cross-reference and diagnostic-starting-point note.

---

## Scope Boundaries

- Not creating `plugins/webworks-claude-skills/skills/reverb2/references/runtime-architecture.md`. The breadcrumb belongs co-located with key concepts in SKILL.md.
- Not modifying existing references in SKILL.md to `Pages/scripts/*.js`, `Pages/*.asp`, `Pages/sass/*.scss` at SKILL.md:15 and SKILL.md:319. They remain factually correct and frame complementary points (training-data warning, output-vs-source distinction).
- Not duplicating SCSS partials inventory, override priority hierarchy, or theming workflows from the existing `## SCSS Customization` section (SKILL.md:166-222) or `references/scss-architecture.md`. The new section cross-references them.
- Not documenting `.asp` template syntax, server-side processing, or how ASP-style tags transform into published HTML. Beyond the breadcrumb scope; if readers need transform internals, that's a separate gap.
- Not addressing audit item #17 (`.weplugin` deprecation guidance). Already covered in SKILL.md `<common_mistakes>` at lines 317-319; no additional work needed for this PR.
- Not touching `plugins/webworks-claude-skills/skills/reverb2/workflows/`, `scripts/`, or `templates/`. No workflow changes; documentation only.
- Not updating `marketplace.json` or `plugin.json` directly. The `scripts/bump-version.sh` helper updates both atomically.

### Deferred to Follow-Up Work

- None. Item #17 lives in the same audit doc but is already covered by existing SKILL.md content and is explicitly out of scope here.

---

## Context & Research

**Source location:** `plugins/webworks-claude-skills/skills/reverb2/`

**Files touched in this plan:**
- `plugins/webworks-claude-skills/skills/reverb2/SKILL.md` (modify — add `<runtime_architecture>` section)
- `plugins/webworks-claude-skills/plugin.json` (modify via `scripts/bump-version.sh patch`)
- `plugins/webworks-claude-skills/marketplace.json` (modify via `scripts/bump-version.sh patch`)

**Existing patterns to mirror:**
- Table-first section structure: SKILL.md:78-86 (`<capabilities>`), SKILL.md:106-114 (DOM Component IDs), SKILL.md:182-189 (Partials Inventory), SKILL.md:215-219 (Override Priority).
- XML-tag section anchors: every major section in SKILL.md uses lowercase XML tags (`<overview>`, `<related_skills>`, `<capabilities>`, etc.). New section follows the same convention.
- Cross-reference pattern: SKILL.md:221 references `workflows/scss-theming.md` and `references/scss-architecture.md` in a single line — same pattern works for pointing readers to deeper SCSS guidance from the new section.

**Adjacent content already in SKILL.md:**
- `<objective>` at SKILL.md:9-16 warns against using training data and lists the three source paths.
- `<common_mistakes>` at SKILL.md:319 reiterates the source-vs-output distinction with the same three paths.
- `<scss_customization>` at SKILL.md:166-222 documents the SCSS three-layer architecture, partials inventory, and override priority.
- `references/scss-architecture.md` carries the deep SCSS cascade and compilation model.

**Audit origin:** `plans/knowledge-gaps-from-audit.md:121-129` (item #16). The breadcrumb text in the audit doc is the canonical content source — preserve the three source-type explanations verbatim where possible, then add the diagnostic-starting-point framing and cross-reference.

**Version bump rationale:** Per CLAUDE.md, documentation updates qualify as `patch`. Current version is `2.11.0` (from latest commit `abc5ec8 chore: bump version to 2.11.0`). Target: `2.11.1`.

---

## Implementation Units

### U1. Add `<runtime_architecture>` section to reverb2 SKILL.md

**Goal.** Introduce a focused `## Runtime Architecture` section in `plugins/webworks-claude-skills/skills/reverb2/SKILL.md` that documents the three source types in `<format name>/Pages/` and frames the section as the starting point for runtime diagnosis.

**Requirements.** R1, R2, R3, R4, R5, R6.

**Dependencies.** None.

**Files.**
- `plugins/webworks-claude-skills/skills/reverb2/SKILL.md` (modify)

**Approach.**

1. Insert a new `<runtime_architecture>` XML-tagged section between the existing `</overview>` close tag (SKILL.md:28) and the `<related_skills>` open tag (SKILL.md:30).
2. Lead with a one-sentence framing claim: Reverb 2.0 runtime output is built from three source types in `<format name>/Pages/`.
3. Provide a three-row markdown table mapping source path → published output → role. Suggested columns: `Source`, `Published as`, `Role`. Rows:
   - `Pages/scripts/*.js` | `.js` (loaded by runtime) | JavaScript behavior — keyboard shortcuts, search, navigation, runtime initialization.
   - `Pages/*.asp` | `.html` / `.htm` | HTML templates rendered into the published topic and chrome pages.
   - `Pages/sass/*.scss` | `.css` | Stylesheets compiled during publish; `_*.scss` partials are configurable variable collections.
4. Follow with a short prose paragraph that names the diagnostic-starting-point role: when investigating any Reverb 2.0 runtime issue (theme override not applied, search broken, navigation glitch, missing chrome element), look in `Pages/` first.
5. Add a cross-reference line pointing readers to `## SCSS Customization` (SKILL.md:166-222) and `references/scss-architecture.md` for deeper SCSS guidance, mirroring the cross-reference pattern at SKILL.md:221.
6. Keep the section compact — under ~25 lines total including the table. The goal is a discoverable breadcrumb, not an exhaustive architectural reference.

**Patterns to follow.**
- Section header convention: `## Runtime Architecture` wrapped in `<runtime_architecture>` / `</runtime_architecture>` XML tags, matching every other section in SKILL.md.
- Table style: markdown pipe tables, single-line cells, header row uses sentence case (matches Partials Inventory at SKILL.md:184).
- Cross-reference style: trailing `**Detailed guidance:** ...` paragraph or inline `(see ...)` — match SKILL.md:221.
- Source-path formatting: backticked paths with `Pages/` prefix relative to format root, matching SKILL.md:15 and SKILL.md:319.

**Test scenarios.**

Test expectation: none — pure documentation addition with no executable behavior, no scripts, and no helpers. Verification is by manual read of the rendered SKILL.md and the audit checks in U2.

**Verification.**
- The new `<runtime_architecture>` section appears between `</overview>` and `<related_skills>` in SKILL.md.
- All three source types from audit item #16 (`scripts/*.js`, `*.asp`, `sass/*.scss`) are named and mapped to their published output (`.js`, `.html`/`.htm`, `.css`).
- The `_*.scss` partials-as-variable-collections statement is preserved (R4).
- The diagnostic-starting-point framing appears in prose (R5).
- A cross-reference to `## SCSS Customization` and `references/scss-architecture.md` is present (R6).
- Existing content at SKILL.md:15 and SKILL.md:319 is unchanged.
- The section fits in under ~25 lines.

---

### U2. Bump plugin version to 2.11.1

**Goal.** Increment the plugin version via the project's helper script so `plugin.json` and `marketplace.json` stay synchronized.

**Requirements.** R7.

**Dependencies.** U1.

**Files.**
- `plugins/webworks-claude-skills/plugin.json` (modified by helper)
- `plugins/webworks-claude-skills/marketplace.json` (modified by helper)

**Approach.**

1. Run `scripts/bump-version.sh patch` from the repo root.
2. The script updates both `plugin.json` and `marketplace.json` atomically (per CLAUDE.md guidance).
3. Confirm the new version is `2.11.1` in both files.

**Patterns to follow.**
- Per CLAUDE.md: use `scripts/bump-version.sh` rather than hand-editing either JSON file. The script's purpose is to keep the two files in lockstep; manual edits drift.

**Test scenarios.**

Test expectation: none — version bump is a mechanical helper invocation with no behavioral logic to test. Verification is by inspecting the resulting JSON.

**Verification.**
- `plugins/webworks-claude-skills/plugin.json` reports version `2.11.1`.
- `plugins/webworks-claude-skills/marketplace.json` reports version `2.11.1` for the `webworks-claude-skills` entry.
- Both files were modified in the same commit as U1's SKILL.md change.

---

## Verification Summary

- New `<runtime_architecture>` section present in `plugins/webworks-claude-skills/skills/reverb2/SKILL.md` with the three source-type rows, framing claim, diagnostic-starting-point prose, and cross-reference.
- Existing SKILL.md content unchanged outside the inserted section.
- `plugin.json` and `marketplace.json` both at version `2.11.1`.
- Git commit captures both the documentation change and the version bump in a single commit per the project convention.
- Manual review of the rendered SKILL.md confirms the section reads as a discoverable diagnostic entry point — not as an SCSS deep-dive, build-pipeline explanation, or `.asp` template internals doc.

---

## Risks

- **Low: scope creep into adjacent gaps.** The audit doc contains item #17 in the same section. Resist the temptation to "while we're here" rewrite the deprecated-weplugin guidance. Item #17 is already adequately covered by the existing `<common_mistakes>` note at SKILL.md:317-319; expanding it earns a separate plan if the audit shows further gaps.
- **Low: duplicating SCSS guidance.** The new section sits adjacent to the existing `<scss_customization>` section. Lean on cross-references rather than re-explaining partials, the cascade, or override priority. The new section is a *pointer*, not a competing source.
- **Low: version-bump skipped.** Easy to forget after a docs-only change. The verification checklist includes both `plugin.json` and `marketplace.json` reads to catch it.

---

## Out of Scope

- Restructuring the existing SKILL.md `<objective>` or `<common_mistakes>` sections.
- Creating new reference files under `plugins/webworks-claude-skills/skills/reverb2/references/`.
- Documenting `.asp` template syntax, server-side rendering, or how ASP-style markers transform into published HTML.
- Documenting the Reverb runtime JavaScript modules (`Parcels`, navigation, search) at API granularity.
- Closing audit item #17 — already addressed by existing SKILL.md content.
- Updating any non-reverb2 skill or the repo-level CLAUDE.md.
