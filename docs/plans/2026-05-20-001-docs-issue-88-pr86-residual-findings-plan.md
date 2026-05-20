---
title: "docs(epublisher): address PR #86 residual findings (forward reference + hash variant decision rule)"
type: docs
status: active
created: 2026-05-20
depth: lightweight
origin: https://github.com/quadralay/webworks-claude-skills/issues/88
---

# docs(epublisher): address PR #86 residual findings

## Summary

Two P2 documentation fixes in `plugins/webworks-claude-skills/skills/epublisher/references/file-resolver-guide.md` flagged by ce-code-review on PR #86:

1. The `ASP Templates (.asp)` customization-use-cases list does not point forward to the new `### Copying Custom Assets in ASP Templates` section under `## Advanced Topics`. An agent that lands at the ASP Templates entry sees "Add company logos" as a use case and may imitate the setting-based `header-logo-src` pattern instead of finding the file-based `copy-relative-to-output-root` guidance.
2. The hash variant Variants table describes what `-with-generation-hash` does but does not state when to choose it over the plain variant.

## Problem Frame

These are discoverability and decision-rule gaps in a doc that was just added in PR #86. Both findings were classified P2 — non-blocking polish on otherwise-sound documentation. The fixes are local, additive, and confined to two sentences in one file.

## Scope Boundaries

In scope:
- One forward-reference sentence in the `### ASP Templates (`.asp`)` section's `**Customization Use Cases:**` list (or directly after it).
- One decision-rule sentence in the `### Copying Custom Assets in ASP Templates` section, attached to the `**Variants:**` table / trailing note.
- Patch version bump (`2.12.2 → 2.12.3`) per project convention for docs-only changes (`scripts/bump-version.sh patch`).

Out of scope:
- Rewriting or restructuring either section beyond the two additions.
- Cross-skill references (e.g., `reverb2/SKILL.md`).
- Adding additional examples, diagrams, or new subsections.

### Deferred to Follow-Up Work

None.

## Key Technical Decisions

- **Forward reference placement.** Add the reference as a short sentence immediately after the `**Customization Use Cases:**` bullet list, not embedded inside a bullet. Rationale: keeps the bullet list parallel and scannable, and the sentence reads naturally as a "see also" callout. Use the wording suggested by the reviewer: a one-sentence forward reference using markdown link syntax to the in-document anchor.
- **Decision-rule placement.** Add the rule as a short sentence directly after the Variants table, before the existing "used extensively by the base install" sentence. Rationale: keeps the decision adjacent to the table that introduces the choice. Use the reviewer-suggested split: plain variant for assets that rarely change (logos, brand artwork); `-with-generation-hash` for assets actively modified that should invalidate browser caches (scripts, stylesheets).
- **Version bump tier.** Patch (docs-only, no behavior change) per the convention in CLAUDE.md.

## Implementation Units

### U1. Add forward reference and decision rule sentences, then bump version

**Goal:** Apply both P2 fixes in a single docs commit and bump the plugin patch version.

**Requirements:** Issue #88 sub-tasks 1 and 2.

**Dependencies:** PR #86's `### Copying Custom Assets in ASP Templates` section must already exist in the file (it does, via merge of `origin/dev-worker` into this branch).

**Files:**
- `plugins/webworks-claude-skills/skills/epublisher/references/file-resolver-guide.md` (modify)
- `plugins/webworks-claude-skills/.claude-plugin/plugin.json` (modify via bump script)
- `.claude-plugin/marketplace.json` (modify via bump script)

**Approach:**

1. In the `### ASP Templates (`.asp`)` section (around the `**Customization Use Cases:**` list), add one sentence after the bullet list pointing to the new section:

   > For copying custom assets (logos, scripts) referenced by overridden ASP templates, see [Copying Custom Assets in ASP Templates](#copying-custom-assets-in-asp-templates) under Advanced Topics.

2. In the `### Copying Custom Assets in ASP Templates` section, immediately after the `**Variants:**` table and before the "used extensively by the base install" sentence, add one sentence stating the decision rule:

   > Use the plain variant for assets that rarely change (logos, brand artwork); use `-with-generation-hash` for assets that are actively modified and should invalidate browser caches on rebuild (scripts, stylesheets).

3. Run `scripts/bump-version.sh patch` to bump `2.12.2 → 2.12.3` in both `plugin.json` and `marketplace.json`.

**Patterns to follow:**
- Inline markdown link to the section anchor (already a convention in the file; section IDs are kebab-cased GitHub-flavored slugs of the heading text).
- Sentence-level additions, not new subsections or bullets.

**Test scenarios:**

- Test expectation: none — pure documentation prose additions and a version-string bump. No code path, configuration, or runtime behavior changes. Manual verification by reading the rendered section is sufficient.

**Verification:**
- The forward-reference sentence renders below the use-cases list in `### ASP Templates (`.asp`)` and the link anchor resolves to `### Copying Custom Assets in ASP Templates`.
- The decision-rule sentence appears between the Variants table and the "used extensively by the base install" sentence in the new section.
- `plugin.json` and `marketplace.json` both show `2.12.3` after the bump.
- No other lines in the file changed.

## Risks

- **Anchor mismatch.** If the section heading is later renamed, the forward-reference link breaks. Mitigated by using the existing heading text verbatim; if a rename happens, the link is easy to spot during diff review.
- **Reviewer disagreement on placement.** The reviewer's suggestion was directional ("add a one-sentence forward reference", "add one decision sentence"). The placement choices above (after the list, before the existing trailing sentence) are judgment calls; either landing spot should satisfy the spirit of the findings.
