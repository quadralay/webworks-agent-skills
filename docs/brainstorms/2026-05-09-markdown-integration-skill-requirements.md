# Markdown-Integration Skill — Requirements

**Date:** 2026-05-09
**Source:** Issue #67 — *Replace markdown-plus-plus skill with thinner ePublisher-integration skill*
**Scope:** Lightweight (well-bounded restructure)

## Context

The format-level Markdown++ skill (syntax, validation, best practices) has migrated to its own repo at `quadralay/markdown-plus-plus`. The `markdown-plus-plus` skill bundled with `webworks-claude-skills` now duplicates the format spec and conflates two different concerns:

- **Format-level concerns** — what Markdown++ syntax means, how to validate it, how it parses. Belongs with the format spec.
- **ePublisher-integration concerns** — how Markdown++ documents fit into ePublisher projects: where variables come from, how styles map to Stationery, how conditions are configured in targets, how output flows through AutoMap into Reverb.

This issue separates those by removing the format-level skill from this plugin and replacing it with a thinner integration-focused skill.

## Goals

- Eliminate duplication of the Markdown++ format spec between this plugin and `quadralay/markdown-plus-plus`.
- Keep ePublisher-specific Markdown++ guidance discoverable inside this plugin.
- Point users to `quadralay/markdown-plus-plus` for format-level questions.

## Non-Goals

- Migrating any content into `quadralay/markdown-plus-plus` (handled in that repo's PR).
- Adding `quadralay/markdown-plus-plus` as a git submodule (users install both plugins independently).
- Building cross-plugin discovery automation.

## Scope

**In:**

1. Delete `plugins/webworks-claude-skills/skills/markdown-plus-plus/` (SKILL.md, references/, scripts/, tests/).
2. Create `plugins/webworks-claude-skills/skills/markdown-integration/` with a thinner SKILL.md focused on:
   - Variable sources (ePublisher project Variables window, Stationery defaults, target overrides).
   - Style mapping (Stationery style definitions → format-specific CSS/XSL).
   - Condition configuration (ePublisher Conditions window, per-target visibility, job file overrides).
   - File-include conventions in ePublisher source-document groups.
   - AutoMap build integration for Markdown++ source documents.
   - Reverb output considerations (markers feeding search, alias-driven CSH topics).
3. Update `related_skills` blocks in `epublisher/SKILL.md` and `automap/SKILL.md` and the reference at `epublisher/references/product-foundations.md` line 69.
4. Update `README.md` skill table to describe the new integration skill.
5. Bump plugin version (minor: skill restructuring).

**Out:**

- Format-spec content (variables syntax rules, condition operators, marker JSON validation, etc.) — this lives in `quadralay/markdown-plus-plus`. The integration skill references that repo by URL.
- The validation/alias-generation scripts (`validate-mdpp.py`, `add-aliases.py`).
- The format-level test samples.

## Success Criteria

- The directory `plugins/webworks-claude-skills/skills/markdown-plus-plus/` no longer exists.
- The directory `plugins/webworks-claude-skills/skills/markdown-integration/` exists with a SKILL.md whose `description` makes clear it is an ePublisher-integration skill that defers format syntax to `quadralay/markdown-plus-plus`.
- No remaining `related_skills` entry references the old skill location.
- `epublisher/references/product-foundations.md` reflects the new skill name.
- README skill table reflects the new skill.
- Plugin and marketplace versions are bumped in lockstep (`2.8.0 → 2.9.0`).

## Assumptions

- `quadralay/markdown-plus-plus` is the canonical home for Markdown++ format docs going forward (per issue context).
- Users who need both format-level guidance and ePublisher integration will install both plugins. The integration skill links to the format repo URL but does not depend on the format plugin being installed.
- The existing skill name `markdown-plus-plus` is no longer needed in this plugin; renaming the directory to `markdown-integration` better reflects its purpose. Backward-compat for the keyword `markdown++` is preserved in the plugin/marketplace tags so discovery still works.
