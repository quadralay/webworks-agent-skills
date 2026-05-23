---
title: Reverb 2.0 runtime architecture documentation gap (Pages/ source tree)
date: 2026-05-20
category: documentation-gaps
module: reverb2
problem_type: documentation_gap
component: documentation
severity: medium
applies_when:
  - Diagnosing a Reverb 2.0 runtime issue (theme not applying, broken search, navigation glitch, missing chrome element)
  - Looking for the source of an HTML/CSS/JS artifact in published Reverb output
  - Authoring a Reverb 2.0 customization and unsure which source directory owns the behavior
  - Adding a "where do I start?" breadcrumb to a skill that documents a runtime built by transformation
related_components:
  - epublisher
  - automap
tags:
  - reverb2
  - runtime-architecture
  - pages-directory
  - skill-breadcrumbs
  - documentation-gap
  - diagnostic-starting-point
---

# Reverb 2.0 runtime architecture documentation gap (Pages/ source tree)

## Context

The `reverb2` skill described what Reverb 2.0 is (responsive HTML5 help system, SPA, full-text search, CSH, SCSS theming) but never named the runtime file structure that builds those features. The three source types in `<format name>/Pages/` were mentioned twice in passing — the `<objective>` proprietary-knowledge warning at SKILL.md:15 and a `<common_mistakes>` source-vs-output note (now at SKILL.md:336, line 319 before PR #82 inserted the new section) — but neither gave a structured, discoverable explanation of what lives there or how each source transforms into runtime output.

A reader investigating a theme override that didn't apply, a broken search, a navigation glitch, or any other runtime symptom had no single "start here" section to anchor diagnosis. They would either guess from the published output (which is transformed and not the source of truth) or fall back to training data (which is wrong for Reverb 2.0 specifically because it is not a standard website).

This gap was item #16 in `plans/knowledge-gaps-from-audit.md`, discovered during a Q&A session testing Claude's ability to work effectively as an ePublisher developer. PR #82 closed it by adding a focused `<runtime_architecture>` section to `plugins/webworks-agent-skills/skills/reverb2/SKILL.md` between `<overview>` and `<related_skills>`.

## Guidance

When a skill documents a runtime built by transformation (source files → published artifacts), the skill must surface the **source tree** as a top-level diagnostic breadcrumb — not bury it inside references, and not only mention it in passing inside warnings or gotchas.

### What the breadcrumb must contain

1. **Name the source root explicitly.** For Reverb 2.0 it is `<format name>/Pages/`. The reader needs a single path they can `cd` into.
2. **Enumerate the source types as a table** mapping source path → published output → role. Tables make the transformation visible at a glance; prose buries it.
3. **State the diagnostic-starting-point claim out loud** — "Start here when diagnosing any runtime issue" — so readers do not have to infer it. The published output is transformed; the source of truth lives in the source tree.
4. **Cross-reference any deeper guidance** (e.g., a dedicated SCSS architecture reference) rather than duplicating it. Duplication drifts; cross-references stay coherent.

### Where the breadcrumb lives

In the **SKILL.md** itself as a key-concept section, placed immediately after `<overview>` and before `<related_skills>`. Co-locating with other top-level concepts (Overview, Related Skills, Routing, Capabilities) ensures the breadcrumb is on first-read; burying it under `references/runtime-architecture.md` puts it a click away from the reader who is trying to diagnose a live issue.

The reverb2 implementation:

```markdown
<runtime_architecture>

## Runtime Architecture

Reverb 2.0 runtime output is built from three source types in `<format name>/Pages/`. Start here when diagnosing any runtime issue.

| Source | Published as | Role |
|--------|--------------|------|
| `Pages/scripts/*.js` | `.js` (loaded by runtime) | JavaScript behavior — keyboard shortcuts, search, navigation, runtime initialization |
| `Pages/*.asp` | `.html` / `.htm` | HTML templates rendered into the published topic and chrome pages |
| `Pages/sass/*.scss` | `.css` | Stylesheets compiled during publish; `_*.scss` partials are configurable variable collections |

When investigating a runtime issue — a theme override that didn't apply, a broken search, a navigation glitch, a missing chrome element — look in `Pages/` first. The published output is transformed; the source of truth lives in these three directories.

**Detailed SCSS guidance:** `## SCSS Customization` (below) and `references/scss-architecture.md`.
</runtime_architecture>
```

### When NOT to rewrite adjacent content

The pre-existing references at SKILL.md:15 (`<objective>` proprietary-knowledge warning) and SKILL.md:336 (`<common_mistakes>` source-vs-output note; was SKILL.md:319 prior to this PR) both name the same three source paths. Do not rewrite them when adding the structured section — they frame complementary points (the warning frames training-data avoidance; the common-mistake frames output-vs-source confusion). Removing or rewording them risks losing that framing. The new structured section consolidates the *explanation*; the existing mentions continue to *gesture* toward it.

## Why This Matters

Reverb 2.0 is a proprietary WebWorks framework, not a standard website. An agent that does not know where the source tree lives will fall back to one of two wrong moves:

1. **Read the published HTML/CSS/JS and try to edit it directly.** The published output is generated; edits do not survive a republish, and there is no transform-aware diff to compare against. The agent burns iterations chasing a moving target.
2. **Apply general web-development patterns from training data.** Reverb's chrome, navigation, search, and theming layers do not look like a standard SPA. Generic patterns produce changes that pass cursory inspection but break runtime behavior because they fight the framework's own conventions.

Both failure modes are quiet: they produce changes that look reasonable in isolation but do not survive the publish pipeline or the runtime. A structured breadcrumb that names `Pages/` as the source root, lists the three transformation paths, and tells the reader explicitly to start there short-circuits both wrong moves on first read.

The pattern generalizes beyond Reverb. Any skill that documents a runtime built by transformation — `.xsl` → `.html` formats, `.fti` → published behavior, source SCSS → compiled CSS — should carry a similar "here is the source tree, here is what each type becomes, start here for diagnosis" breadcrumb. The cost is one short section; the benefit is every future investigation starts from the right directory.

## When to Apply

- When auditing a skill and finding that the runtime/source tree is implied but never named as a structured diagnostic entry point.
- When writing a new skill for a tool whose runtime artifacts are generated from source files (the reader must know which directory is source-of-truth and which is generated).
- When the only existing mentions of the source tree are inside warnings, gotchas, or proprietary-knowledge notes — those frame complementary points but do not serve as a "start here" breadcrumb.
- When a reader trying to diagnose a runtime issue would have to read the published output, training data, or several scattered sections to figure out where to look first.

Do not apply when the runtime artifacts *are* the source (no transformation step), or when the source tree is already surfaced as a top-level concept in the skill with the diagnostic-starting-point framing intact.

## Examples

**Before — Reverb 2.0 source paths only in passing:**

```markdown
<objective>
# reverb2
Analysis, testing, and customization tools for WebWorks Reverb 2.0 output...

**Do not use training data for Reverb 2.0.** This is a proprietary WebWorks
framework — not a standard website. Do not assume general web development
patterns apply. Use this skill's references and the format's source files
(`Pages/scripts/*.js`, `Pages/*.asp`, `Pages/sass/*.scss`).
</objective>

<overview>
## Overview
Reverb 2.0 is a responsive HTML5 help system with:
- Single-page application architecture
- Table of contents navigation
- Full-text search
- Context Sensitive Help (CSH) support
- SCSS-based theming
</overview>

<related_skills>
...
```

The three source paths appear inside the proprietary-knowledge warning, but a reader skimming the skill for "where do I look to fix a broken search?" gets no structured answer.

**After — structured Runtime Architecture section between `<overview>` and `<related_skills>`:**

```markdown
<overview>
## Overview
Reverb 2.0 is a responsive HTML5 help system with:
- Single-page application architecture
...
</overview>

<runtime_architecture>
## Runtime Architecture

Reverb 2.0 runtime output is built from three source types in
`<format name>/Pages/`. Start here when diagnosing any runtime issue.

| Source | Published as | Role |
|--------|--------------|------|
| `Pages/scripts/*.js` | `.js` (loaded by runtime) | JavaScript behavior — keyboard shortcuts, search, navigation, runtime initialization |
| `Pages/*.asp` | `.html` / `.htm` | HTML templates rendered into the published topic and chrome pages |
| `Pages/sass/*.scss` | `.css` | Stylesheets compiled during publish; `_*.scss` partials are configurable variable collections |

When investigating a runtime issue — a theme override that didn't apply, a
broken search, a navigation glitch, a missing chrome element — look in
`Pages/` first. The published output is transformed; the source of truth
lives in these three directories.

**Detailed SCSS guidance:** `## SCSS Customization` (below) and
`references/scss-architecture.md`.
</runtime_architecture>

<related_skills>
...
```

The reader now sees the source tree, the transformation table, and the diagnostic-starting-point claim before they encounter any operational mechanics, related skills, or workflows.

**Parallel pattern in the epublisher skill (item #1 of the same audit):**

> Each output format lives in `Formats/<format name>/` and has a `format.wwfmt` file that defines the format and references `.xsl` transform files. This is the starting point for diagnosing any format issue.

The audit identified the same gap for `epublisher` (format entry point) and `reverb2` (runtime architecture). Both received the same treatment: name the source root, enumerate the structure, declare the diagnostic-starting-point framing.

## Related

- Issue: #56 — close audit gap #16 (Reverb 2.0 runtime architecture)
- PR: #82
- Implementation commit: `4dce438` — `docs(reverb2): add Runtime Architecture section to SKILL.md`
- Plan: `docs/plans/2026-05-20-001-feat-reverb2-runtime-architecture-plan.md`
- Audit source: `plans/knowledge-gaps-from-audit.md` (item #16, lines 121-129)
- Sibling skill file: `plugins/webworks-agent-skills/skills/reverb2/SKILL.md`
- Related deep reference (cross-linked from the new section): `plugins/webworks-agent-skills/skills/reverb2/references/scss-architecture.md`
- Sibling Reverb learning (different angle — runtime ID resolution): `docs/solutions/design-patterns/reverb-landmark-resolver-static-mirror-2026-05-20.md`
- Parallel documentation-gap pattern (epublisher schema): `docs/solutions/documentation-gaps/epublisher-format-traits-xml-schema-2026-05-09.md`
- Related architectural learning (skill placement): `docs/solutions/architecture-patterns/format-spec-vs-integration-skill-separation-2026-05-09.md`
