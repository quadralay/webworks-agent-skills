---
title: ePublisher wwpage:attribute-src documentation gap (custom assets in ASP templates)
date: 2026-05-20
category: documentation-gaps
module: epublisher
problem_type: documentation_gap
component: documentation
severity: medium
applies_when:
  - Customizing an ASP template (Header.asp, Footer.asp, Connect.asp, Page.asp, Splash.asp) and the template references a custom static asset (logo, script, stylesheet)
  - Deciding where in an override directory to place a template-bundled image, script, or stylesheet
  - Reading an existing ASP template that contains both file-based and setting-based wwpage:attribute-src values and deciding which form to copy
  - Auditing a customized format for hardcoded relative paths that break across output group depths
related_components:
  - reverb2
  - automap
tags:
  - epublisher
  - wwpage-attribute-src
  - asp-templates
  - file-resolver
  - override-assets
  - documentation-gap
---

# ePublisher wwpage:attribute-src documentation gap (custom assets in ASP templates)

## Context

The `epublisher` skill's `references/file-resolver-guide.md` already explains the four-level override hierarchy and how to override `.asp` templates and `.scss` partials. It did not explain how to include **custom static assets** (a custom logo image, a small JavaScript snippet, a template-bundled stylesheet) that an overridden ASP template references. Two failure modes followed from the gap:

1. **Wrong location.** The agent placed template assets in the format's `Files/` directory (which is for source-document-level assets) and the assets were copied into every output group folder instead of once at the output root.
2. **Hardcoded relative paths.** The agent referenced images with bare `src="images/foo.png"` paths. The path resolved correctly from the chrome page during development but broke in multi-group outputs where the published topic lives at a different depth than the chrome page.

Both failure modes are quiet: the publish succeeds, the build artifact looks structurally correct, and the broken paths only surface in browser-rendered output after deployment. The agent has no signal during build that the chosen pattern is wrong.

The gap was discovered during a real customization on a Radware ePublisher project (Case 00024362). PR #86 closed it (issue #48) by adding a `### Copying Custom Assets in ASP Templates` subsection under `## Advanced Topics` in `plugins/webworks-agent-skills/skills/epublisher/references/file-resolver-guide.md`.

## Guidance

When documenting an override system that bundles **custom assets** alongside template overrides, the docs must surface the asset-handling attribute as a first-class pattern — not as a corollary of the override hierarchy and not as an example buried under the file type that uses it. For ePublisher's `wwpage:attribute-src` specifically:

### 1. Name the attribute and both variant values explicitly

The attribute is `wwpage:attribute-src`. The two file-copy variant values are:

| Value | Behavior |
|-------|----------|
| `copy-relative-to-output-root` | Copies file, rewrites path relative to output root |
| `copy-relative-to-output-root-with-generation-hash` | Same, plus appends a generation hash query parameter for cache-busting on rebuild |

Both are file-based resolvers. Both expect the asset to live in a subdirectory alongside the overridden ASP template (typically `Pages/images/` or `Pages/scripts/`).

### 2. Distinguish file-based from setting-based resolvers in the same doc

The same `wwpage:attribute-src` attribute is also used with **setting-based** values like `header-logo-src` and `company-logo-src` in the base `Header.asp`. These read the asset path from target configuration (the `Header Logo` / `Company Logo` settings) rather than copying a file from the override directory.

An agent reading an existing `Header.asp` will see both forms in the same template. The docs must say out loud which form does what and when to choose each:

- **File-based** (`copy-relative-to-output-root`, `copy-relative-to-output-root-with-generation-hash`) — when the asset is bundled with the override and should ship with the format.
- **Setting-based** (`header-logo-src`, `company-logo-src`, ...) — when the asset path should remain configurable per target via the project's settings UI.

### 3. Contrast `Files/` directory with `wwpage:attribute-src` as a one-row decision rule

Both mechanisms copy assets into the output, so the agent needs a brisk decision rule. The contrast lives in the same section as the `wwpage:attribute-src` documentation — not in a separate `Files/` deep-dive — so the agent making the choice does not have to chase a cross-reference.

| Approach | Use case |
|----------|----------|
| `Files/` directory | Source-document-level assets (icons, CSS referenced from content). Copied into every output group folder. |
| `wwpage:attribute-src` | Template-level assets (logos in headers/footers, custom scripts loaded by `Connect.asp`). Copied once, path-corrected automatically. |

Placing template-level assets in `Files/` works incidentally but yields broken paths from chrome pages in multi-group outputs and duplicates the asset across every group folder. The one-row contrast is enough to steer the agent away from the wrong tool without requiring a full `Files/` chapter.

### 4. Show a real example, not a synthetic one

The split-logo Header.asp from the originating issue serves as the canonical example because it demonstrates the pattern in production-realistic context — two `<img>` tags inside layout containers inside `wwpage:condition` — rather than a synthetic single-element snippet:

```html
<div class="ww_skin_header" wwpage:condition="header-enabled">
  <div class="ww_skin_header_logo_container_outer">
    <div class="ww_skin_header_logo_left">
      <img class="ww_skin_header_logo" src="images/logo-text.png" wwpage:attribute-src="copy-relative-to-output-root" />
    </div>
    <div class="ww_skin_header_logo_right">
      <img class="ww_skin_header_logo" src="images/logo-art.png" wwpage:attribute-src="copy-relative-to-output-root" />
    </div>
  </div>
</div>
```

With this example, the agent learns the typical placement (`Pages/images/`), the typical filename style, and the fact that the `src` is template-relative (not output-relative) in one read.

### Where the section lives

Under `## Advanced Topics` in `file-resolver-guide.md`, between "Version Upgrade Considerations" and `## Tools and Scripts`. The "File Types and Locations" section above describes **what files exist and where**; this section is a **usage pattern for an attribute**, which belongs in the Advanced Topics register alongside "Multiple Override Levels", "Shared Formats Directory", and "Version Upgrade Considerations". Expanding the "ASP Templates" file-type entry to cover asset handling would tangle the file-type catalog with attribute mechanics.

## Why This Matters

ePublisher's asset-resolution behavior is quiet: a misplaced asset or a hardcoded path produces a successful build with no diagnostic signal. The asymmetry between the failure modes makes this especially costly:

1. **Files in the wrong place.** Assets placed in `Files/` get copied into every group folder. The build succeeds, the storage cost is invisible until someone audits the output tree, and the chrome page's `src` reference resolves to a path that may or may not exist depending on group depth.
2. **Hardcoded relative paths.** A bare `src="images/foo.png"` resolves from the chrome page during single-group development but breaks the moment the published topic lives at a different depth. The break shows up only in browser-rendered output, not in the build log.

For agents working from skill references, the silent-failure surface is worse. The agent has no way to tell from a passing build that the chosen pattern is wrong — unlike a hard parse error (e.g., `format-traits` schema mistakes, which fail loudly at load time), the asset-handling mistake passes every automated check.

Documenting `wwpage:attribute-src` as a first-class pattern with the file-based-vs-setting-based contrast and the `Files/` decision rule short-circuits the wrong moves on the agent's first read. The cost is one Advanced-Topics subsection; the benefit is every future template customization picks the right tool the first time.

The pattern generalizes. Any skill that documents an override system bundling assets alongside templates — Reverb 2.0 `Pages/`, ePublisher `Formats/<name>/`, custom AutoMap deliverables — should surface the asset-copy attribute as a top-level pattern rather than leaving the agent to infer it from template examples.

## When to Apply

- When auditing a skill that documents an override hierarchy and finding that asset handling is implied (via template examples) but never named as a structured pattern.
- When the same attribute supports both a file-based and a setting-based variant — an agent reading an existing template will see both and needs explicit guidance on which to choose.
- When two mechanisms (e.g., `Files/` directory and `wwpage:attribute-src`) overlap incidentally — the docs need a one-row decision rule co-located with the new pattern, not a separate chapter.
- When the failure modes are quiet (silent ignore, broken paths only visible in rendered output) — the docs cannot rely on the build log to teach the agent the right pattern.

Do not apply when the attribute is purely setting-based (no file copy involved) or when the failure mode is loud (parser refuses to load, build errors visibly).

## Examples

**Before — agent customizing `Header.asp` reads `file-resolver-guide.md` and sees only the override hierarchy:**

```
Formats/WebWorks Reverb 2.0/Pages/Header.asp   ← customizable
Formats/WebWorks Reverb 2.0/Pages/sass/_*.scss  ← customizable
```

The agent picks one of the two wrong moves:

```html
<!-- WRONG: bare src breaks across group depths -->
<img src="images/logo.png" />
```

```
# WRONG: places asset in Files/, copied into every group folder
Files/images/logo.png
```

The publish succeeds. The agent declares the customization done. The broken paths surface in QA.

**After — `file-resolver-guide.md` documents `wwpage:attribute-src` as a first-class pattern under Advanced Topics:**

```html
<!-- Correct: wwpage:attribute-src signals copy + path rewrite -->
<img src="images/logo.png" wwpage:attribute-src="copy-relative-to-output-root" />
```

```
# Correct: asset alongside the ASP template under Pages/images/
Formats/WebWorks Reverb 2.0/Pages/Header.asp
Formats/WebWorks Reverb 2.0/Pages/images/logo.png
```

The agent reading the new section cold can write the customization, place the asset in the right directory, and pick file-based vs setting-based correctly on the first attempt.

**Parallel pattern in the same skill (item #1 of the same audit family):**

The earlier `docs/solutions/documentation-gaps/epublisher-format-traits-xml-schema-2026-05-09.md` learning closed a related but distinct gap — the `.wep` XML schema documentation did not match what the parser accepts. The pattern is the same: ePublisher's failure surface is asymmetric (silent ignore on some mistakes, loud refusal on others), and the docs must teach the agent how to avoid both without relying on the build log to flag the wrong move.

## Follow-Up Opportunities

The Phase 3 code review surfaced two P2 documentation-improvement opportunities scoped beyond the original issue's eight committed content elements. They are recorded here so a follow-up can pick them up cleanly:

1. **Forward reference from the `ASP Templates (.asp)` file-type entry.** An agent navigating from `## File Types and Locations` lands on the ASP Templates entry, sees "Add company logos" as a customization use case, and may imitate the setting-based `header-logo-src` pattern visible there before discovering the file-based `copy-relative-to-output-root` guidance in Advanced Topics. A one-sentence forward reference at the ASP Templates entry would close the loop. (Suggested location: `file-resolver-guide.md:388`.)
2. **Hash-variant decision rule.** The variants table describes what `-with-generation-hash` does but does not state when to choose it over the plain variant. One sentence — plain for assets that rarely change (logos, brand artwork); `-with-generation-hash` for assets actively modified that should invalidate browser caches (scripts, stylesheets) — would make the choice mechanical rather than inferred. (Suggested location: `file-resolver-guide.md:585`.)

Neither is load-bearing for the current learning; both improve agent decision speed on the second-order question of *which* variant to pick or *where* to discover the pattern.

## Related

- Issue: #48 — document `wwpage:attribute-src` for ASP template assets
- PR: #86
- Implementation commit: `325a15b` — `docs(epublisher): document wwpage:attribute-src for ASP template assets`
- Plan: `docs/plans/2026-05-20-001-feat-issue-48-wwpage-attribute-src-plan.md`
- Originating context: Radware ePublisher project, Case 00024362
- Implementation target: `plugins/webworks-agent-skills/skills/epublisher/references/file-resolver-guide.md` — new `### Copying Custom Assets in ASP Templates` subsection under `## Advanced Topics`
- Sibling epublisher documentation-gap learning (different angle — XML schema mismatch): `docs/solutions/documentation-gaps/epublisher-format-traits-xml-schema-2026-05-09.md`
- Related skill-structure learning (where to surface a diagnostic-starting-point breadcrumb): `docs/solutions/documentation-gaps/reverb2-runtime-architecture-pages-directory-2026-05-20.md`
- Related architectural learning (format vs integration-skill boundary): `docs/solutions/architecture-patterns/format-spec-vs-integration-skill-separation-2026-05-09.md`
- Deferred cross-reference: `plugins/webworks-agent-skills/skills/reverb2/SKILL.md` — when a Header/Footer ASP customization workflow is added there, link to this section in `file-resolver-guide.md`
