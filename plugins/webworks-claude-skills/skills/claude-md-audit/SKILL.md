---
name: claude-md-audit
description: >
  Audits and reduces CLAUDE.md or other agent MD files (AGENTS.md, GEMINI.md,
  and similar context files) by removing content the model can discover on its
  own and keeping only behavioral steering that prevents repeated mistakes.
  Use when reviewing, reducing, shrinking, auditing, or creating a CLAUDE.md
  or agent MD file for any repository.
---

<objective>

# claude-md-audit

Audit a repository's `CLAUDE.md` (or other agent MD file, such as `AGENTS.md` or `GEMINI.md`) and reduce it to only the information that prevents real, repeated agent mistakes. Remove everything the model can discover on its own from the codebase.

**Why this skill exists.** Recent research on coding-agent context files reports that large agent MD files consistently hurt performance:

- LLM-generated context files decreased task completion by ~3%.
- Developer-written context files improved task completion by only ~4%.
- Both raised cost by 20%+ as the model expanded its exploration and reasoning.
- Freshly generated files performed worse than no file at all.

The methodology in this skill was applied by hand to one real `CLAUDE.md` and reduced it from 180 lines to 49 lines (~73% reduction) with no loss of useful steering. The skill codifies that approach so any agent can apply the same reduction to any repository.

These research numbers are reproduced as user-attested from the source the team relied on; a future maintainer should re-check them rather than treat them as canon.
</objective>

<overview>

## Overview

The core principle:

> **If the model can find it in the codebase, it does not belong in the agent MD file.**

Three secondary principles follow from it:

- **Bias is real.** Mentioning a technology, framework, or architectural pattern biases the model toward it even when the current task is unrelated. ("Pink elephant" effect.)
- **Stale entries actively mislead.** File paths, directory layouts, technology lists, and pattern guides go stale silently as code evolves; the agent can no longer tell whether a stale claim still holds.
- **Discoverable noise costs context.** Anything restating what `glob`, `grep`, or reading project files would reveal is pure overhead on every prompt.

The methodology applies four steps: categorize each section (KEEP / REMOVE / REDUCE), apply the Pink Elephant Test, apply the Staleness Test, then draft the reduced file in a four-section structure.

**Safety net.** Before applying any reduction, create a backup of the original file at `CLAUDE.md.bak` (or `AGENTS.md.bak`, etc.) adjacent to the original. This is non-negotiable — see Methodology Step 0 and Success Criteria.
</overview>

<methodology>

## Audit Methodology

### Step 0: Back up the original file

Before changing anything, copy the existing file to `<original-name>.bak` in the same directory.

- For `CLAUDE.md` → `CLAUDE.md.bak`.
- For `AGENTS.md` → `AGENTS.md.bak`.
- For other agent MD names, follow the same pattern.

The backup must exist before any edits land. A user who later realizes they removed something they wanted to keep can restore from the backup without rerunning the audit.

### Step 1: Categorize every section

Read the file and classify each section into exactly one of three buckets:

#### KEEP — Steers away from real mistakes the model cannot self-correct

Examples of content that earns its place:

- **Environment gotchas** the model would otherwise get wrong (e.g., "this repo uses SVN, not Git"; "Python is not in PATH").
- **Tool paths the model cannot discover** (e.g., a full path to a non-standard compiler or interpreter).
- **Behavioral rules the model would consistently violate** without the prompt (e.g., "when adding a user-facing string, update *all* locale resource files, not just the base").
- **Workflow pointers for custom tooling** the model cannot infer (e.g., a slash command name, a project-specific settings file).

#### REMOVE — Discoverable from the codebase

Examples that do not earn their place:

- **Directory structure descriptions** — the model finds these by exploring with `glob` and `ls`.
- **Technology lists** — the model reads `package.json`, `*.csproj`, imports, lock files.
- **Architecture overviews** — the model traces code paths.
- **Dependency lists** — the model reads lock files and project configs.
- **Installation requirements** — these serve human onboarding, not agent steering.
- **Code pattern guides** — the model finds patterns by reading existing code.

#### REDUCE — Partially useful, trim to essentials

Examples that need editing rather than removal:

- **Build commands**: keep the command; remove the explanation of what it does.
- **Configuration details**: keep only what cannot be found in config files.
- **Links to detailed docs**: keep the link; remove any prose summary of the linked content.

### Step 2: Apply the Pink Elephant Test

For each section that survived Step 1, ask:

> Does mentioning this bias the model toward it when the current task is unrelated?

If yes, remove it — even if it is otherwise true and accurate. The model that reads "this project uses TRPC" is more likely to reach for TRPC when the current task uses a completely different stack. The model that reads "the adapter architecture uses X" considers adapters even for unrelated UI changes. Mentioning a CLI option pattern biases the model toward that pattern when editing unrelated code.

The bar: if mentioning something could steer the model wrong in unrelated tasks, it must go.

### Step 3: Apply the Staleness Test

For each remaining section, ask:

> Will this go out of date, and would stale info cause harm?

Stable over time (good candidates to keep):

- Environment paths and tool paths.
- Behavioral rules about how to handle a category of change.
- Version-control system (SVN vs. Git rarely flips back and forth).

Goes stale fast (prefer to remove or link out instead):

- File paths and directory structures — they move when code is reorganized.
- Technology descriptions — they drift as dependencies change.
- Pattern guides — they age as conventions evolve.

Prefer entries that are stable. Remove entries that will silently rot.

### Step 4: Draft the reduced file

Use this four-section structure. **Omit any section that is empty** — do not leave a placeholder.

1. **Environment** — gotchas, tool paths, version-control system.
2. **Build Commands** — just the commands, plus links to detailed docs.
3. **Behavioral Rules** — only rules the model consistently violates without them.
4. **Configuration** — settings, credentials, setup instructions for tooling the model interacts with directly.

The four-section structure is empirical, not derived from first principles. If a real audit suggests a fifth durable section (for example, "Workflow pointers" or "Slash commands"), capture it as a follow-up refinement to this skill rather than inventing per-repo section names.
</methodology>

<examples>

## Before/After Examples

### REMOVE: Architecture overview

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

The model discovers directory structure by exploring. This block adds ten-plus lines of noise to every prompt without preventing any mistake.

### REMOVE: Technology list

```markdown
<!-- BEFORE (remove this) -->
### Key Technologies
- Languages: C#, C++, VBA, Python, XSLT, JavaScript
- Build System: MSBuild with custom Python scripts
- Installers: NSIS for Windows installers
```

The model reads project files and knows what technologies are in use. Worse, listing technologies invokes the Pink Elephant Test — the model will reach for `NSIS` or `MSBuild` even when the current task has nothing to do with installers or builds.

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

Without this rule the model updates only the base resource file. The mistake is consistent and the fix is hard to discover from a single locale file — the model has no reason to even look at the others. This is the canonical "the model would consistently get it wrong without it" case.

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

Keep the command and the link. Remove the explanation — the model reads the project file to understand what the build target actually does, and the linked guide carries the authoritative narrative.
</examples>

<success_criteria>

## Success Criteria

- A backup of the original file (e.g., `CLAUDE.md.bak`) exists adjacent to the original *before* any reduction is applied.
- The reduced file is **under 60 lines** for a typical repository. This is a guideline informed by one real reduction (180 → 49 lines), not a hard fail threshold.
- Every remaining line fails at least one test: the model could not discover it on its own, *or* the model consistently gets it wrong without it.
- No directory structure descriptions remain.
- No technology or dependency lists remain.
- No architecture overviews remain.
- No installation or onboarding instructions written for humans remain.
- Build commands are present as bare commands plus doc links — no prose summary of what the build does.
- The reduced file uses the four-section structure (Environment / Build Commands / Behavioral Rules / Configuration), omitting any section that is empty.
</success_criteria>
