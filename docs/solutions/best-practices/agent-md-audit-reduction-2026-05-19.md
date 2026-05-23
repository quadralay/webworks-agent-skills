---
title: Agent MD files steer best when small and behavioral, not encyclopedic
date: 2026-05-19
category: best-practices
module: agent-context-files
problem_type: best_practice
component: documentation
severity: medium
applies_when:
  - Writing or editing a CLAUDE.md, AGENTS.md, GEMINI.md, or similar agent context file
  - Reviewing whether existing agent guidance still earns its place
  - Onboarding a new repository and deciding what its agent MD should contain
  - A CLAUDE.md has grown past ~60 lines or feels like a repo overview
related_components:
  - tooling
tags:
  - claude-md
  - agents-md
  - context-engineering
  - agent-prompting
  - skill-authoring
---

# Agent MD files steer best when small and behavioral, not encyclopedic

## Context

Coding agents read a project's `CLAUDE.md` (or `AGENTS.md`, `GEMINI.md`, etc.) on every prompt. The instinct is to make this file a thorough repo overview — directory layout, technology stack, architecture, conventions, the works. Recent research on context-file effectiveness inverts that instinct:

- LLM-generated context files **decreased** task completion by ~3%.
- Developer-written context files improved task completion by only ~4%.
- Both **increased cost by 20%+** as the model expanded its exploration and reasoning.
- Freshly generated files performed **worse than no file at all**.

Applied by hand to one real `CLAUDE.md`, this methodology reduced the file from 180 lines to 49 lines (~73% reduction) with no loss of useful steering. The skill `claude-md-audit` (added under `plugins/webworks-agent-skills/skills/claude-md-audit/`) codifies the approach.

## Guidance

The single rule:

> **If the model can find it in the codebase, it does not belong in the agent MD file.**

Three secondary principles follow:

- **Bias is real.** Mentioning a technology, framework, or pattern biases the model toward it even when the current task is unrelated (the "pink elephant" effect).
- **Stale entries actively mislead.** File paths, directory layouts, technology lists, and pattern guides go stale silently as code evolves; the agent has no way to detect the drift.
- **Discoverable noise costs context.** Anything restating what `glob`, `grep`, or reading project files would reveal is pure overhead on every prompt.

### The four-step audit

1. **Categorize every section** as KEEP, REMOVE, or REDUCE.
   - **KEEP** — steers away from real mistakes the model cannot self-correct: environment gotchas (SVN vs. Git, interpreter not in PATH), non-standard tool paths, behavioral rules the model would consistently violate (e.g., "update *all* locale resource files"), workflow pointers for custom tooling.
   - **REMOVE** — discoverable from the codebase: directory structure descriptions, technology lists, architecture overviews, dependency lists, installation requirements (those serve human onboarding), generic code-pattern guides.
   - **REDUCE** — keep the essential, drop the prose: build commands without the "what this does" explanation, configuration that isn't in config files, links without summaries of the linked content.

2. **Apply the Pink Elephant Test.** For each surviving section, ask: *does mentioning this bias the model toward it when the task is unrelated?* If yes, remove it — even if it is accurate.

3. **Apply the Staleness Test.** For each surviving section, ask: *will this go out of date, and would stale info cause harm?* Prefer entries that are stable over time (environment paths, behavioral rules, version-control system). Remove entries that will silently rot (file paths, technology descriptions, pattern guides).

4. **Draft the reduced file** in this four-section structure, omitting any section that is empty:
   1. **Environment** — gotchas, tool paths, version-control system.
   2. **Build Commands** — just the commands plus links to detailed docs.
   3. **Behavioral Rules** — only rules the model consistently violates without them.
   4. **Configuration** — settings, credentials, setup instructions for tooling the model interacts with directly.

### Backup before reducing

Always copy the original to `<original-name>.bak` (e.g., `CLAUDE.md.bak`) adjacent to the file before any edits land. A user who later notices they removed something they wanted can restore from the backup without rerunning the audit.

## Why This Matters

The cost of bloated agent MD files is paid on *every* prompt, not just once. Each unnecessary line:

- Inflates token cost (20%+ measured overhead, dominated by expanded exploration and reasoning).
- Biases the model toward technologies and patterns named in the file, even on unrelated tasks.
- Risks misleading the agent when the entry goes stale and the codebase moves on.
- Crowds out the entries that actually prevent mistakes.

A 180-line file that "documents the repo" is not steering — it's noise the agent has to read past. The model is *better at reading the codebase* than at trusting a stale summary of it. The agent MD file's only job is to handle the cases the model cannot self-correct from the code alone.

## When to Apply

- Creating a new `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` for a repository — start under 60 lines, add only what fails the discoverability bar.
- Reviewing an existing agent MD file that has grown past ~60 lines, feels like a repo overview, or lists technologies / architecture.
- Periodically auditing established agent MD files — content drifts as the codebase evolves, and entries that were useful at the start can become stale or pink-elephant traps.
- Whenever the `claude-md-audit` skill is invoked.

## Examples

### REMOVE: Directory structure block

```markdown
<!-- BEFORE (remove this) -->
## Architecture Overview
### Directory Structure
- **builds/**: Centralized build scripts
- **dev/source/**: Main functional code
- **files/**: Static files copied to installers
- **products/**: Installer projects
- **thirdparty/**: External dependencies
```

The model finds the directory structure by exploring with `glob` and `ls`. This block adds ten-plus lines to every prompt without preventing any mistake.

### REMOVE: Technology list

```markdown
<!-- BEFORE (remove this) -->
### Key Technologies
- Languages: C#, C++, VBA, Python, XSLT, JavaScript
- Build System: MSBuild with custom Python scripts
- Installers: NSIS for Windows installers
```

The model reads project files and knows what technologies are in use. Worse, the list invokes the Pink Elephant Test — the model will reach for `NSIS` or `MSBuild` even on tasks that have nothing to do with installers or builds.

### KEEP: Environment gotcha

```markdown
<!-- AFTER (keep this) -->
## Environment
- **Version Control**: This repository uses **SVN**, not Git.
- **Python**: Not in PATH. Always invoke the full interpreter path.
```

Without these lines the model would try `git status` and a bare `python` command. Both fail. The lines are short, stable over time, and prevent a real, repeated failure mode.

### KEEP: Behavioral rule

```markdown
<!-- AFTER (keep this) -->
### Localization
When adding user-facing strings, update **all** locale resource files:
- Base (English) resource file
- Each per-language variant (French, German, Japanese, etc.)
```

Without this rule the model updates only the base resource file. The mistake is consistent and the fix is hard to discover from one locale file — the model has no reason to even look at the others.

### REDUCE: Build commands

```markdown
<!-- BEFORE -->
### Debug Builds (Day-to-Day Development)
For building and debugging during development, use the product solutions
directly. The solutions include adapter projects as project references and
a copy-native-dependencies target that handles native runtime dependencies
automatically after Debug builds.
[full build command]
Full guide: docs/guides/setup-dev-build.md

<!-- AFTER -->
### Debug Builds
[full build command]
Full guide: docs/guides/setup-dev-build.md
```

Keep the command and the link. Remove the explanation — the model reads the project file to understand what the build target does, and the linked guide carries the authoritative narrative.

## Related

- Skill: `plugins/webworks-agent-skills/skills/claude-md-audit/SKILL.md` — the codified audit methodology.
- `docs/solutions/authoritative-skill-patterns.md` — adjacent concern: writing skill descriptions that actually trigger invocation. Both learnings target effective prompts the agent reads, but at different scopes (skill frontmatter vs. repo-level context file).
- GitHub issue #52 — original proposal and the 180→49 line motivating reduction.
