---
title: "refactor: Replace markdown-plus-plus skill with thinner markdown-integration skill"
type: refactor
status: implemented
date: 2026-05-09
origin: docs/brainstorms/2026-05-09-markdown-integration-skill-requirements.md
issue: 67
---

# Replace markdown-plus-plus Skill with Thinner markdown-integration Skill

## Summary

The Markdown++ format spec (syntax, validation, best practices) has migrated to `quadralay/markdown-plus-plus` as a standalone plugin. This plan removes the duplicated format-level skill from `webworks-claude-skills` and replaces it with a thinner ePublisher-integration skill that defers format-level concerns to the new plugin.

## Problem Frame

The bundled `markdown-plus-plus` skill conflated two concerns:

- **Format-level** — what Markdown++ syntax means, how it validates, how it parses. Belongs with the format spec.
- **ePublisher-integration** — how Markdown++ documents become source files in `.wep`/`.wrp`/`.wxsp` projects: where variables resolve, how styles map to Stationery, how conditions layer per target, how AutoMap builds them, how Reverb consumes markers and aliases.

With the format spec now living in its own repo, keeping a duplicate format skill in this plugin creates drift risk and obscures the ePublisher-specific guidance that genuinely belongs here.

## Goals

- Eliminate format-spec duplication between this plugin and `quadralay/markdown-plus-plus`.
- Keep ePublisher-specific Markdown++ guidance discoverable inside this plugin.
- Direct users to `quadralay/markdown-plus-plus` for format-level questions.

## Scope Boundaries

**In scope:**

- Delete the existing `markdown-plus-plus/` skill directory in this plugin.
- Create a new `markdown-integration/` skill focused on the integration layer.
- Update cross-references (`related_skills` blocks, README, product-foundations) to point at the new skill and the external plugin.
- Bump plugin and marketplace versions in lockstep (minor).

**Deferred to Follow-Up Work:**

- None. The companion `quadralay/markdown-plus-plus` plugin is tracked in its own repo (PR quadralay/markdown-plus-plus#1).

**Outside this plugin's identity:**

- Migrating any content into `quadralay/markdown-plus-plus` (handled in that repo).
- Adding `quadralay/markdown-plus-plus` as a git submodule — users install both plugins independently.
- Cross-plugin discovery automation.

## Key Technical Decisions

1. **Rename the directory rather than edit the existing skill in place.** `markdown-plus-plus` no longer accurately describes the skill's purpose once the format spec is removed. `markdown-integration` signals the integration-layer focus and avoids confusion with the external `markdown-plus-plus` plugin of the same name.

2. **Reference the format plugin by URL, not by submodule.** Users install both plugins independently. The integration skill links to `https://github.com/quadralay/markdown-plus-plus` in its `description` and prose. No runtime coupling.

3. **Keep the `markdown++` keyword in plugin/marketplace tags.** Discovery for users searching "markdown++" should still surface this plugin even though the directory name changed.

4. **Preserve the `description`-as-routing-contract pattern.** The new skill's frontmatter `description` field starts with the AUTHORITATIVE REFERENCE phrasing and explicitly defers format syntax to the external plugin, so Claude's skill-selection heuristics correctly route format questions away from this skill.

## Implementation Units

### U1. Remove the format-level markdown-plus-plus skill

**Goal:** Delete the duplicated format skill from this plugin.

**Files:**

- `plugins/webworks-claude-skills/skills/markdown-plus-plus/` (delete directory and all contents — `SKILL.md`, `references/`, `scripts/`, `tests/`)

**Approach:** Recursive delete. The format spec, validation script (`validate-mdpp.py`), alias-generation script (`add-aliases.py`), and test samples now live in `quadralay/markdown-plus-plus`. Keeping them here would mean two places to maintain the same rules.

**Test scenarios:** none — pure removal. Verified by U5's grep check.

**Verification:** Directory does not exist after the change.

---

### U2. Create the markdown-integration skill

**Goal:** Add a thinner skill focused on ePublisher integration patterns for Markdown++ sources.

**Files:**

- `plugins/webworks-claude-skills/skills/markdown-integration/SKILL.md` (new)
- `plugins/webworks-claude-skills/skills/markdown-integration/references/integration-patterns.md` (new)

**Approach:**

- `SKILL.md` — frontmatter `description` opens with AUTHORITATIVE REFERENCE for ePublisher integration of Markdown++ and explicitly defers format syntax to the `markdown-plus-plus` skill in `quadralay/markdown-plus-plus`. Body sections cover: Variables (Stationery → project → target → job-file resolution), Styles (Stationery style definitions → format CSS/XSL), Conditions (Conditions window, per-target visibility, job-file overrides), Includes (source-document group resolution), Markers (search index, index entries, CSH), Aliases (stable URL endpoints in Reverb `url_maps.xml`), Helper adapter behavior, and AutoMap silent-fallback diagnosis.
- `references/integration-patterns.md` — extended walkthroughs for variable layering, style-to-Stationery resolution, condition layering across targets, and source-document group composition.
- Both files explicitly redirect format-level questions to the external plugin to avoid duplication drift.

**Patterns to follow:** Match the section structure of `epublisher/SKILL.md` and `automap/SKILL.md` (XML-tagged sections, `<related_skills>` block, vendor-doc citation conventions).

**Test scenarios:** none — content-only skill files; correctness is reviewed editorially. The `<related_skills>` cross-reference is exercised by U3 and verified by U5.

**Verification:** Both files exist; `description` field clearly identifies the skill as ePublisher integration and points format questions at the external plugin.

---

### U3. Update cross-references in sibling skills

**Goal:** Point `related_skills` blocks and prose references at the new skill name and external plugin.

**Files:**

- `plugins/webworks-claude-skills/skills/epublisher/SKILL.md` — `related_skills` table row + external-plugin entry + numbered workflow step
- `plugins/webworks-claude-skills/skills/automap/SKILL.md` — `related_skills` table row + external-plugin entry
- `plugins/webworks-claude-skills/skills/reverb2/SKILL.md` — `related_skills` table row
- `plugins/webworks-claude-skills/skills/epublisher/references/product-foundations.md` — skill workflow description (line ~67) and the format-spec deferral note (line ~71)

**Approach:** Replace `markdown-plus-plus` row entries with `markdown-integration` rows describing the integration role. Add a separate entry under each `related_skills` block for the external `quadralay/markdown-plus-plus` plugin, framed as "install separately for format syntax." In `product-foundations.md`, update the numbered workflow step to call out wiring Markdown++ sources into the project and add a deferral note pointing to the external plugin.

**Patterns to follow:** Existing `related_skills` table format in each SKILL.md; existing prose-linking style for external resources.

**Test scenarios:** none — descriptive cross-reference edits. Verified by U5's grep check.

**Verification:** No `related_skills` row references the old `markdown-plus-plus` skill location inside this plugin; every sibling skill that previously referenced it now references `markdown-integration` plus a separate entry for the external plugin.

---

### U4. Update top-level documentation and metadata

**Goal:** Reflect the skill restructuring in user-facing surfaces and bump versions.

**Files:**

- `README.md` — skill table row + prose paragraph about the companion plugin + requirements table row
- `plugins/webworks-claude-skills/.claude-plugin/plugin.json` — `description` field + version
- `.claude-plugin/marketplace.json` — `description` field + version (kept in sync via `scripts/bump-version.sh`)

**Approach:**

- README skill table now lists `markdown-integration` with an integration-focused description, and a paragraph below the table directs format-syntax users to install the companion `quadralay/markdown-plus-plus` plugin. Requirements table mentions the pairing.
- `plugin.json` and `marketplace.json` `description` fields shift from "Markdown++ authoring" to "Markdown++ integration".
- Run `scripts/bump-version.sh minor` to bump 2.8.0 → 2.9.0 (skill restructuring is a minor change, not breaking — existing references that used the keyword `markdown++` for discovery still work via tags).

**Patterns to follow:** Existing README skill-table column layout; existing `bump-version.sh` workflow.

**Test scenarios:** none — documentation and metadata only.

**Verification:** README skill table matches the new skill set; `plugin.json` and `marketplace.json` both report `2.9.0`; descriptions reflect "integration" framing.

---

### U5. Verify no stale references remain

**Goal:** Catch any lingering text references to the old skill location before commit.

**Files:** none modified — verification only.

**Approach:** Grep the working tree for `markdown-plus-plus` and confirm every remaining occurrence is either (a) an intentional reference to the external `quadralay/markdown-plus-plus` plugin, (b) a tag/keyword preserved for backward-compat discovery, or (c) inside a docs/brainstorms/docs/plans artifact describing the migration.

**Test scenarios:** none — verification step.

**Verification:** `grep -r "skills/markdown-plus-plus" plugins/ README.md` returns no matches; `grep -r "markdown-plus-plus" .` only returns external-plugin references, tags, and historical artifacts.

## Requirements Trace

| Requirement (origin) | Implementation Unit |
|----------------------|---------------------|
| Delete `skills/markdown-plus-plus/` | U1 |
| Create thinner `skills/markdown-integration/` SKILL.md | U2 |
| Update `related_skills` in epublisher and automap | U3 |
| Update `epublisher/references/product-foundations.md` line 69 | U3 |
| Update README skill table | U4 |
| Bump plugin version (minor) | U4 |
| `markdown-plus-plus/` no longer exists (success criterion) | U1, U5 |
| `markdown-integration/` exists with deferring `description` (success criterion) | U2 |
| No `related_skills` references old location (success criterion) | U3, U5 |
| `product-foundations.md` reflects new name (success criterion) | U3 |
| README reflects new skill (success criterion) | U4 |
| Plugin/marketplace versions bumped in lockstep (success criterion) | U4 |

Origin: `docs/brainstorms/2026-05-09-markdown-integration-skill-requirements.md`.

## Risks and Considerations

- **Discovery regression for "markdown++" searches.** Mitigated by keeping `markdown++` in plugin/marketplace tags so the keyword still surfaces this plugin, plus updating the README prose to direct format-syntax users to the companion plugin.
- **Cross-skill description drift.** The integration skill's frontmatter and the sibling skills' `related_skills` blocks all carry deferral language pointing at `quadralay/markdown-plus-plus`. If the external plugin changes name or location, every site needs updating. Acceptable risk — there is no automated enforcement, and the plugin landscape is small enough that grep catches drift.
- **Existing users with the old skill cached locally.** A version bump signals the change; the plugin install/update cycle removes the old directory. No migration step needed for end users.

## Verification Strategy

After all units land:

1. Directory shape — `plugins/webworks-claude-skills/skills/markdown-plus-plus/` is gone; `plugins/webworks-claude-skills/skills/markdown-integration/` exists with `SKILL.md` and `references/integration-patterns.md`.
2. Cross-references — every `related_skills` block in `epublisher`, `automap`, `reverb2` references `markdown-integration` (not the old name) and includes a separate entry for the external `quadralay/markdown-plus-plus` plugin.
3. Documentation — README skill table and requirements table list `markdown-integration`; `product-foundations.md` reflects the new skill name and deferral note.
4. Versioning — `plugin.json` and `marketplace.json` both report `2.9.0`; descriptions say "Markdown++ integration".
5. Grep audit — no stale references inside `plugins/` or `README.md`.

## Outcome

Implemented in commit `f4130ac` on branch `claude/issue-67`. Plugin version bumped 2.8.0 → 2.9.0. Closes #67.
