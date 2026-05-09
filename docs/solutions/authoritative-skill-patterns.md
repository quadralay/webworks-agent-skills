---
title: Authoritative Skill Patterns
category: skill-authoring
component:
  - skill-descriptions
  - invocation-triggering
symptoms:
  - Skill not invoked when it should be
  - Generic descriptions fail to trigger skill selection
  - Users must manually invoke skills that should auto-activate
root_cause: Skill descriptions lacking explicit authority claims, file patterns, and trigger phrases are not selected by Claude's skill matching
date_solved: 2025-12-27
related_files:
  - plugins/webworks-claude-skills/skills/markdown-integration/SKILL.md
  - plugins/webworks-claude-skills/skills/epublisher/SKILL.md
  - plugins/webworks-claude-skills/skills/automap/SKILL.md
  - plugins/webworks-claude-skills/skills/reverb2/SKILL.md
---

# Authoritative Skill Patterns

This document captures patterns for creating skills that serve as authoritative references and are automatically invoked when relevant.

## The Problem

Skills with generic descriptions often fail to be invoked when they should be. For example, a skill with this description:

```yaml
description: Read and write Markdown++ documents with extended syntax...
```

Was **not invoked** during a content migration and cleanup session, even though:
- The entire project was Markdown++ documentation
- The task involved fixing Markdown++ syntax errors
- The project CLAUDE.md had incorrect Markdown++ syntax

## Solution: Authoritative Skill Descriptions

### Key Principles

1. **Declare authority explicitly** - Use "AUTHORITATIVE REFERENCE" at the start
2. **List file patterns** - Specify what file types/patterns trigger the skill
3. **Include action verbs** - editing, fixing, migrating, correcting, validating
4. **Add trigger phrases** - Common phrases users might use
5. **Use numbered scenarios** - Make it easy to scan when the skill applies

### Before and After

**Before (weak triggers):**
```yaml
description: Read and write Markdown++ documents with extended syntax for
  variables, conditions, custom styles, file includes, and markers. Use when
  creating Markdown++ source documents for ePublisher, generating documentation
  with conditional content, or working with extended Markdown formats.
```

**After (strong triggers):**
```yaml
description: >
  AUTHORITATIVE REFERENCE for Markdown++ syntax. Use this skill WHENEVER working with
  .md files containing Markdown++ extensions (<!--style:-->, <!--condition:-->, $variable;,
  <!--include:-->, <!--marker:-->, <!--#alias-->). This includes: (1) editing or fixing
  Markdown++ syntax, (2) migrating content from FrameMaker, Word, or DITA to Markdown++,
  (3) performing content audits or cleanup, (4) correcting invalid Markdown++ patterns,
  (5) validating syntax, (6) writing new Markdown++ documents. ALWAYS consult this skill
  before making Markdown++ edits to ensure correct syntax. Triggers: fix markdown, correct
  syntax, migrate to markdown++, content audit, cleanup documentation, invalid comment syntax.
```

### Description Template

```yaml
description: >
  AUTHORITATIVE REFERENCE for [DOMAIN]. Use this skill WHENEVER working with
  [FILE_PATTERNS] containing [IDENTIFYING_FEATURES]. This includes: (1) [ACTION_1],
  (2) [ACTION_2], (3) [ACTION_3], (4) [ACTION_4], (5) [ACTION_5], (6) [ACTION_6].
  ALWAYS consult this skill before [PRIMARY_ACTION] to ensure [QUALITY_GOAL].
  Triggers: [trigger1], [trigger2], [trigger3], [trigger4], [trigger5].
```

## Belt-and-Suspenders: Project CLAUDE.md Integration

For projects that heavily rely on a skill, add an explicit directive in the project's CLAUDE.md:

```markdown
### IMPORTANT: [Skill Name] Skill Requirement

**When editing [file types] in this repository, ALWAYS invoke the `[skill-name]` skill first.**

This skill is the authoritative reference for [domain]. Use it before:
- [Action 1]
- [Action 2]
- [Action 3]

To invoke: Use the Skill tool with `skill: "[plugin-name]:[skill-name]"`
```

This provides redundant triggering - if the skill description doesn't trigger, the CLAUDE.md directive will.

## Skill Invocation Naming

Skills are invoked as `plugin-name:skill-name`. To avoid redundant names like `markdown-plus-plus:markdown-plus-plus`, consider:

1. **Option A (CHOSEN)**: Consolidate product-integration skills into one plugin
   - Plugin: `webworks-claude-skills`
   - Skills: `markdown-integration`, `epublisher`, `automap`, `reverb2`
   - Invocation: `webworks-claude-skills:markdown-integration`
   - Format-level Markdown++ guidance lives in a separate plugin (`quadralay/markdown-plus-plus`) — see `docs/solutions/architecture-patterns/format-spec-vs-integration-skill-separation-2026-05-09.md` for the rationale.

2. **Option B**: Name the plugin broadly, skills specifically
   - Plugin: `webworks-authoring`
   - Skills: `markdown-plus-plus`, `framemaker-tips`, `dita-patterns`
   - Invocation: `webworks-authoring:markdown-plus-plus`

3. **Option C**: Single-skill plugins with different names
   - Plugin: `mdpp`
   - Skill: `markdown-plus-plus`
   - Invocation: `mdpp:markdown-plus-plus`

4. **Option D**: Accept the redundancy
   - Plugin: `markdown-plus-plus`
   - Skill: `markdown-plus-plus`
   - Invocation: `markdown-plus-plus:markdown-plus-plus`

## Checklist for Authoritative Skills

- [ ] Description starts with "AUTHORITATIVE REFERENCE"
- [ ] File patterns are explicitly listed
- [ ] Common action verbs included (edit, fix, migrate, correct, validate)
- [ ] Numbered scenarios for when to use
- [ ] "ALWAYS consult" directive included
- [ ] Trigger phrases at the end
- [ ] Related project CLAUDE.md files updated with explicit directive
- [ ] Skill tested with common task descriptions to verify triggering

## Real-World Example

The `markdown-plus-plus` skill (originally bundled in this plugin, since migrated to `quadralay/markdown-plus-plus`) was enhanced following these patterns. Key changes:

1. Added "AUTHORITATIVE REFERENCE" positioning
2. Listed specific file patterns: `<!--style:-->`, `<!--condition:-->`, `$variable;`
3. Added migration scenarios: FrameMaker, Word, DITA
4. Added audit/cleanup scenarios
5. Added explicit trigger phrases

The project's CLAUDE.md was also updated with an explicit directive and a corrected syntax quick-reference table.

The thinner `markdown-integration` skill that replaced the bundled skill in this repo (issue #67) follows the same pattern — its description names file extensions (`.wep`, `.wrp`, `.wxsp`), lists integration scenarios, and points format-level questions to the external `markdown-plus-plus` skill.
