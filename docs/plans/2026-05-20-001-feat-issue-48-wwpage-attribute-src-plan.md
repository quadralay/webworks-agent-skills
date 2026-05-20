---
title: "feat: Document wwpage:attribute-src for copying custom assets in ASP templates"
type: feat
status: active
created: 2026-05-20
issue: 48
depth: lightweight
---

# feat: Document `wwpage:attribute-src` for Copying Custom Assets in ASP Templates

## Summary

Add a new "Copying Custom Assets in ASP Templates" section to the epublisher skill's `file-resolver-guide.md` so an agent that customizes `Header.asp`, `Footer.asp`, or `Connect.asp` knows to use the `wwpage:attribute-src` attribute when referencing template-bundled images, scripts, or stylesheets — and does not misplace them in the `Files/` directory or hardcode brittle relative paths that break across output groups.

## Problem Frame

The epublisher skill's `file-resolver-guide.md` already explains the four-level override hierarchy and how to copy ASP templates and SCSS files. It does **not** explain how to include *custom static assets* (a custom logo image, a custom JavaScript snippet, a small stylesheet) that an overridden ASP template references.

Without this knowledge an agent will:

- Place template assets in the `Files/` directory (which is for source-document-level assets, not template-level assets), causing the assets to be copied into every output group folder.
- Reference images with bare `src="images/foo.png"` paths, which break in multi-group outputs where the published topic lives at a different depth than the chrome page.

The correct pattern is to place the asset alongside the ASP template (e.g., `Pages/images/logo.png`) and reference it with `wwpage:attribute-src="copy-relative-to-output-root"`, which signals ePublisher to copy the file into the output **and** rewrite the `src` attribute to a path relative to the output root.

This was surfaced during a real customization (Radware ePublisher project, Case 00024362) where the agent picked the wrong pattern. The fix is purely documentation — codify the pattern in the skill so future agents pick it correctly the first time.

## Requirements Traceability

The issue body specifies the content shape directly. The single implementation unit covers all of it:

- **New section in `file-resolver-guide.md`** titled "Copying Custom Assets in ASP Templates" → U1
- **Syntax documentation** for `wwpage:attribute-src` with both variants (`copy-relative-to-output-root`, `copy-relative-to-output-root-with-generation-hash`) → U1
- **File placement guidance** showing assets alongside the ASP template under `Pages/images/` or `Pages/scripts/` → U1
- **Comparison with `Files/` directory** (one-row table contrasting use cases) → U1
- **Contrast with setting-based resolvers** (`header-logo-src`, `company-logo-src`) so the agent does not confuse file-based vs. setting-based forms → U1
- **Real-world example** (split-logo Header.asp from the issue) → U1
- **Patch version bump** (project convention from `CLAUDE.md`: docs updates are `patch`) → U1

## Key Technical Decisions

- **Placement: under `## Advanced Topics`, not `## File Types and Locations`.** The existing "File Types and Locations" section describes what files exist and where they live; this new content is a usage pattern for an attribute, which fits the "Advanced Topics" register (which already houses "Multiple Override Levels", "Shared Formats Directory", and "Version Upgrade Considerations"). Adding a fourth subsection there preserves the existing structure better than expanding the ASP Templates description.
- **Do not modify the `reverb2` skill.** The issue says to also reference this in the reverb skill "if Header.asp/Footer.asp customization is documented there." It currently is not — `reverb2/SKILL.md` mentions `Pages/*.asp` only as a runtime-architecture pointer and has no ASP customization workflow. Adding a cross-reference now would attach guidance to a surface that does not exist yet. If a Header/Footer customization workflow is ever added to `reverb2`, that PR can pull in the cross-reference.
- **Do not introduce new files.** A single section in an existing reference file is the smallest change that satisfies the issue. No new examples directory, no new images, no new scripts.
- **Patch version bump (2.12.1 → 2.12.2).** Per `CLAUDE.md`: "patch: Bug fixes, documentation updates, minor improvements". Documentation-only changes are patch.

## Assumptions

- The `wwpage:attribute-src` attribute behavior described in the issue (file copying + path rewriting at publish time) is accurate as captured by the requester. The plan reproduces the issue's syntax and variant table verbatim rather than independently verifying against ePublisher source — the requester observed this in a real project (Case 00024362), and the existing skill explicitly states "Do not use training data for ePublisher" (see `epublisher/SKILL.md` line 15), so the issue body is the authoritative source.
- The `-with-generation-hash` variant's cache-busting behavior (hash query parameter appended for rebuild invalidation) is accurate as described. The issue notes this variant is used extensively in the base install (`Connect.asp`, `Page.asp`, `Splash.asp`); the doc reproduces that observation without claiming to enumerate every base-install consumer.
- "File-based" vs "setting-based" is the right framing for the contrast with `header-logo-src` / `company-logo-src`. The issue uses these terms; the doc adopts them so readers searching for either form land in the same place.

## Implementation Units

### U1. Add "Copying Custom Assets in ASP Templates" subsection and bump plugin version

**Goal:** Add a single new subsection under `## Advanced Topics` in `file-resolver-guide.md` that documents the `wwpage:attribute-src` pattern with syntax, variants, file placement, the `Files/`-directory contrast, the setting-based-resolver contrast, and the split-logo example. Bump the plugin to the next patch version per repo convention.

**Requirements:** All issue requirements (single-section addition + version bump per `CLAUDE.md`).

**Dependencies:** none

**Files:**

- `plugins/webworks-claude-skills/skills/epublisher/references/file-resolver-guide.md` — modify (add new subsection under `## Advanced Topics`, after "Version Upgrade Considerations" at line 559 and before "## Tools and Scripts" at line 569)
- `plugins/webworks-claude-skills/.claude-plugin/plugin.json` — modify (`version: 2.12.1 → 2.12.2`)
- `plugins/webworks-claude-skills/.claude-plugin/marketplace.json` — modify (kept in sync with `plugin.json` per `CLAUDE.md`; use `scripts/bump-version.sh patch`)

**Approach:**

- Run `scripts/bump-version.sh patch` from the repo root to perform the version bump in both manifests atomically (the script keeps them in sync per `CLAUDE.md`).
- In `file-resolver-guide.md`, add a new H3 subsection inside the existing `## Advanced Topics` H2. Place it after the existing "Version Upgrade Considerations" subsection and before the `## Tools and Scripts` H2 (insert at line 568, immediately before `## Tools and Scripts`). Header text: `### Copying Custom Assets in ASP Templates`.
- The subsection should cover, in this order:
  1. **One-paragraph framing.** When customizing an ASP template (`Header.asp`, `Footer.asp`, `Connect.asp`, etc.), referenced assets (images, scripts, stylesheets) placed alongside the template can be copied to the output and have their `src` paths rewritten automatically by tagging the element with `wwpage:attribute-src`.
  2. **How it works** — short bulleted list: (a) ePublisher copies the referenced file into the output, (b) ePublisher rewrites the `src` attribute to use the correct relative path from the output location.
  3. **Syntax** — fenced code block with one `<img>` and one `<script>` example using `copy-relative-to-output-root`.
  4. **Variants table** — two rows: `copy-relative-to-output-root` (copies file, rewrites path) and `copy-relative-to-output-root-with-generation-hash` (same, plus hash query for cache-busting). One-line note that the `-with-generation-hash` variant is used extensively in the base install (`Connect.asp`, `Page.asp`, `Splash.asp`) for scripts and images that need cache invalidation on rebuild.
  5. **File placement** — fenced ASCII tree showing `Formats/WebWorks Reverb 2.0/Pages/` containing `Header.asp`, an `images/` subdirectory with custom logos, and a `sass/` subdirectory with custom partials. The takeaway: place assets in the same override directory the ASP template lives in.
  6. **Comparison with `Files/` directory** — two-row table contrasting the two approaches. `Files/` is for source-document-level assets that get copied into every group folder. `wwpage:attribute-src` is for template-level assets copied once with paths corrected automatically. The doc does not need a deep dive into the `Files/` directory mechanics — a single contrast row is enough to keep an agent from picking the wrong tool.
  7. **Contrast with other `wwpage:attribute-src` values** — one paragraph noting that `Header.asp` uses setting-based resolver values like `wwpage:attribute-src="header-logo-src"` and `wwpage:attribute-src="company-logo-src"`, which read paths from target configuration. `copy-relative-to-output-root` is a *file-based* resolver that copies a specific file from the override location. This distinction matters because an agent reading existing `Header.asp` will see both forms and must know which one to use.
  8. **Real-world example** — fenced HTML block reproducing the split-logo Header.asp snippet from the issue body (left/right logo containers each with a `wwpage:attribute-src="copy-relative-to-output-root"` image).

**Patterns to follow:**

- Section structure (H3 inside H2, one paragraph of framing followed by code blocks and tables) — see existing subsections under `## Advanced Topics` in `plugins/webworks-claude-skills/skills/epublisher/references/file-resolver-guide.md` lines 530-567 ("Multiple Override Levels", "Shared Formats Directory", "Version Upgrade Considerations").
- Table style for the variants and the `Files/`-comparison — match the two-column "When to Use This Approach" / file inventory tables already used in the same document (e.g., the override-file table at lines 343-346, the SCSS partial inventory at lines 416-422).
- ASCII tree for the file placement — match the project-structure tree at lines 11-23 and the override-path trees at lines 132-158.
- Version bump procedure — `CLAUDE.md` Version Management section; use `scripts/bump-version.sh patch`.

**Test scenarios:**

Test expectation: none — this is a documentation-only change. Verification is by reading the rendered section against the requirements list above.

Manual verification scenarios for the implementer:

- An agent reading the new subsection cold (no chat context) can write a `<img src="images/logo.png" wwpage:attribute-src="copy-relative-to-output-root" />` line in a customized `Header.asp` and place `logo.png` at the correct path without further questions.
- An agent searching for "Files/" in the file-resolver guide lands on the contrast row in the new section and can articulate when to use `Files/` versus `wwpage:attribute-src`.
- An agent reading the contrast paragraph can distinguish the file-based variant (`copy-relative-to-output-root`) from setting-based variants (`header-logo-src`, `company-logo-src`) without further questions.
- The split-logo example from the issue renders verbatim in the doc as a `html` fenced code block.
- `plugin.json` and `marketplace.json` both show `2.12.2`.

**Verification:**

- New `### Copying Custom Assets in ASP Templates` heading appears under `## Advanced Topics` in `file-resolver-guide.md`, between "Version Upgrade Considerations" and "Tools and Scripts".
- The subsection covers all eight content elements listed in the Approach above, in the stated order.
- `plugins/webworks-claude-skills/.claude-plugin/plugin.json` and `plugins/webworks-claude-skills/.claude-plugin/marketplace.json` both report `2.12.2`.
- No other files modified. Specifically, `reverb2/SKILL.md` is unchanged.

## Scope Boundaries

**In scope:**

- One new H3 subsection in `plugins/webworks-claude-skills/skills/epublisher/references/file-resolver-guide.md`.
- Patch version bump (`2.12.1 → 2.12.2`) in both plugin manifests.

**Out of scope:**

- Changes to `reverb2/SKILL.md` or any other skill. The issue conditions this on "if Header.asp/Footer.asp customization is documented there", which it currently is not.
- Independent verification of `wwpage:attribute-src` behavior against ePublisher source code or the base-install ASP files. The issue body's description is treated as authoritative (see Assumptions).
- New examples beyond the split-logo snippet from the issue. The issue provides one concrete example; adding more would be scope creep and may introduce inaccuracies without source verification.
- Adding a `Files/` directory deep-dive section. The contrast row is enough for the agent to pick the right tool; a full `Files/` section is a separate documentation task.

**Deferred to Follow-Up Work:**

- If a Header/Footer ASP customization workflow is later added to `reverb2/SKILL.md`, add a cross-reference there pointing to this section in `file-resolver-guide.md`.
- If repeated agent confusion shows that the `Files/` directory needs its own documentation, add a dedicated subsection in a follow-up.

## Risks

- **Behavior drift across ePublisher versions.** The `wwpage:attribute-src` behavior may differ between ePublisher releases (e.g., 2020.2 vs 2024.1). The issue body does not name a specific version. Mitigation: the doc does not pin a version, and the `Base Format Version` section already in `file-resolver-guide.md` (lines 184-247) tells readers how to reason about version differences if behavior diverges in practice. If a version-specific discrepancy surfaces later, a follow-up can add a version-compatibility note.
- **Reproducing the issue body verbatim introduces no independent verification.** If any detail in the issue is wrong, the doc inherits the error. Mitigation: explicit Assumptions section above flags the inherited claims; future corrections can be made via a follow-up issue without restructuring the section.
