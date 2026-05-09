---
title: Separate format-spec skills from product-integration skills when the format outlives the product
date: 2026-05-09
category: architecture-patterns
module: plugin-skill-architecture
problem_type: architecture_pattern
component: documentation
severity: medium
applies_when:
  - A skill describes a content format (syntax, validation rules, authoring guidance) that is also useful outside the product that originated it
  - A skill documents product-specific workflows (project files, build pipelines, output formats) that depend on a content format but are not the format itself
  - A single skill currently mixes format-level rules with product-level integration and you need to evolve them on different cadences
related_components:
  - markdown-integration
  - markdown-plus-plus
  - epublisher
  - automap
  - reverb2
tags:
  - skill-architecture
  - plugin-boundaries
  - separation-of-concerns
  - markdown-plus-plus
  - skill-cross-references
---

# Separate format-spec skills from product-integration skills when the format outlives the product

## Context

The `markdown-plus-plus` skill in `webworks-claude-skills` originally bundled two distinct concerns: (1) the Markdown++ format itself — syntax for variables, styles, conditions, includes, markers, aliases, multiline tables, validation rules, authoring best practices — and (2) ePublisher integration — how those documents become source files in `.wep`/`.wrp`/`.wxsp` projects, how Stationery maps style names to CSS/XSL, how AutoMap drives the helper adapter, how Reverb consumes markers and aliases.

Markdown++ as a format is potentially useful outside ePublisher: any tool that wants to author conditional, variable-driven, multi-target Markdown could adopt it. Bundling the format spec inside a product-specific plugin made the format harder to consume independently and made the product-integration skill carry redundant format-level material that drifted from the spec.

Issue #67 split the bundled skill into two: a thin product-integration skill (`markdown-integration`) staying in `webworks-claude-skills`, and an authoritative format skill (`markdown-plus-plus`) migrated to its own repository at `quadralay/markdown-plus-plus`.

## Guidance

When a skill mixes a portable content format with product-specific integration, prefer two skills in two repositories over one bundled skill — but only when the format genuinely has independent value.

**Decision criteria — split when all three are true:**

1. The format spec describes syntax/validation/authoring rules that are coherent without referencing the product (someone could implement a different tool that reads the same files).
2. The product-integration material describes how the format plugs into product-specific concepts (project files, build pipelines, output formats, configuration windows) that are themselves stable artifacts.
3. The two layers evolve on different cadences — format additions don't track product releases, and product configuration changes don't require format updates.

**Decision criteria — do NOT split when:**

- The "format" is really a product-specific syntax that doesn't make sense outside the product (e.g., an internal job-file XML schema).
- The integration material is thin enough that two skills is more friction than one — a few paragraphs is not a separate skill.
- The skill's primary users will always have both plugins installed; the cost of cross-references and the "is the companion plugin here?" check exceeds the benefit of independent evolution.

**Cross-skill referencing pattern (when split):**

In the product-integration skill:

- State up front in the description and overview that the format spec lives elsewhere, name the external skill and plugin, and link to its repository.
- For each integration point, document the ePublisher-side concept (how it is configured, how it maps to a project setting, how it surfaces in output) and explicitly defer format-level rules to the external skill rather than restating them.
- For tooling that lives with the format (e.g., format validators, bulk-syntax-edit scripts), name the external skill as the source. Note the script's role, but do not duplicate its invocation contract — the external plugin owns that and the path may differ across installations. Direct the reader to load the external skill for current invocation guidance.
- When the external plugin is not installed in the user's environment, treat the loss of format tooling as a graceful degradation: do the work manually, or ask the user to install the companion plugin. Do not silently invoke a tool that may not exist.

In the format skill:

- Stay strictly format-level. Do not document product-specific workflows, even briefly. The point of the split is that the format skill is consumable without the product context.
- If specific products use the format, list them as known consumers without describing their integration.

**Companion-plugin description language:**

In `plugin.json` and `marketplace.json`, describe the integration plugin as covering "<format> integration" rather than "<format> authoring." This preserves discoverability for users searching for the format name while accurately signaling that authoring/syntax concerns live elsewhere.

## Why This Matters

A bundled skill where format and integration drift apart causes three concrete problems:

1. **Stale format guidance in the product skill.** When the format adds a new construct, the product-integration skill's redundant format material lags. Users get conflicting guidance depending on which section they read.
2. **Format consumers carry product baggage.** A project that uses the format without the product still has to install the entire product plugin, and its agents see product-specific instructions that don't apply.
3. **Versioning becomes painful.** Format-only changes force product-plugin version bumps, and product-only changes ship alongside format material that hasn't moved. Splitting decouples version cadence.

The cost of splitting is real but bounded: cross-references, an explicit "external skill" handoff, graceful degradation when the companion plugin is absent. These costs are paid once. The benefit accrues every time either layer evolves independently.

## When to Apply

- Building a skill for a content format that has, or could have, consumers outside one product.
- Refactoring a bundled skill where the format-level material has grown large enough to be its own coherent reference (the `markdown-plus-plus` SKILL.md before the split was 297 lines of mostly format spec).
- Adding a new product integration for a format that already has its own published skill — start by building only the integration layer and reference the external format skill from the start.
- Considering pulling out a sub-skill: ask whether the layer being extracted is a coherent reference on its own, whether it has independent users or independent evolution, and whether the cross-reference cost is worth the decoupling.

Do not apply when the format is genuinely product-specific, when the integration material is too thin to stand as a separate skill, or when no real evolution-cadence asymmetry exists.

## Examples

**Before — bundled skill (single plugin, mixed concerns):**

```
plugins/webworks-claude-skills/skills/markdown-plus-plus/
├── SKILL.md                       # 297 lines: format spec + ePublisher
├── references/
│   ├── syntax-rules.md            # format-level
│   ├── validation-rules.md        # format-level
│   ├── best-practices.md          # 521 lines, format + product mixed
│   └── integration-patterns.md    # ePublisher-level
└── scripts/
    ├── validate-mdpp.py           # format-level tool
    └── add-aliases.py             # format-level tool
```

**After — split across two plugins:**

```
quadralay/markdown-plus-plus/      # external repo, format spec only
└── skills/markdown-plus-plus/
    ├── SKILL.md                   # format syntax, validation, authoring
    ├── references/
    │   ├── syntax-rules.md
    │   └── validation-rules.md
    └── scripts/
        ├── validate-mdpp.py
        └── add-aliases.py

plugins/webworks-claude-skills/    # this repo, integration only
└── skills/markdown-integration/
    ├── SKILL.md                   # ePublisher integration of Markdown++
    └── references/
        └── integration-patterns.md
```

**Cross-skill referencing example — product-integration skill SKILL.md:**

```markdown
**Format syntax lives elsewhere.** For Markdown++ syntax (variables, styles,
aliases, conditions, includes, markers, multiline tables), validation rules,
and authoring best practices, use the **markdown-plus-plus** skill in the
`quadralay/markdown-plus-plus` plugin. This skill assumes that knowledge and
focuses on what changes when those documents become source files in an
ePublisher project.
```

**Cross-skill tool deferral example:**

```markdown
**For format-level pre-build validation, use the `markdown-plus-plus` skill's
validation script** (in the `quadralay/markdown-plus-plus` plugin). Invocation
depends on the companion plugin's installed location — load the
`markdown-plus-plus` skill for the current script path and arguments. If the
companion plugin is not installed, ask the user to install it from
`quadralay/markdown-plus-plus` or skip pre-build validation.
```

**Related-skills table updates** in adjacent skills (`epublisher`, `automap`, `reverb2`) name both the new local integration skill and the external format skill, so an agent reading any of them learns the boundary:

```markdown
| Skill                  | Plugin                                  | When to Use                              |
|------------------------|-----------------------------------------|------------------------------------------|
| **markdown-integration**| this plugin                            | Wiring Markdown++ into ePublisher        |
| **markdown-plus-plus** | `quadralay/markdown-plus-plus`          | Format syntax, validation, authoring     |
```

## Related

- Issue: #67 — refactor: replace markdown-plus-plus skill with thinner markdown-integration skill
- Implementation commit: `f4130ac`
- Plan: `docs/plans/2026-05-09-refactor-markdown-integration-skill-plan.md`
- Existing learning: `docs/solutions/authoritative-skill-patterns.md` (its `related_files` reference to the old `markdown-plus-plus/SKILL.md` is now stale; the authority pattern itself still applies and is followed by both new skills)
