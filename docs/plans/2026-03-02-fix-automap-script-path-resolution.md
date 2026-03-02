---
title: "fix: AutoMap script path resolution and grep locale failure"
type: fix
status: implemented
date: 2026-03-02
---

# Fix AutoMap Script Path Resolution and grep Locale Failure

## Overview

Two related fixes to the automap skill that resolve build failures when Claude invokes the wrapper script from a project directory.

## Problem

When Claude invoked the automap skill, it would `cd` to the project directory and run `bash scripts/automap-wrapper.sh ...`. This failed because `scripts/` is relative to the skill directory, not the project directory.

A secondary issue: the wrapper's target-parsing logic used `grep -oP` (Perl-compatible regex), which fails in non-UTF-8 locales with `grep: -P supports only unibyte and UTF-8 locales`.

## Root Cause

1. **SKILL.md** showed all script paths as bare `scripts/automap-wrapper.sh` without stating they're relative to the skill's base directory. Claude had no instruction to prepend the base directory path.
2. **automap-wrapper.sh** used `grep -oP` with `\s` (Perl shorthand for whitespace) where a literal space would suffice. The `-P` flag requires a UTF-8 locale that isn't guaranteed in all Git Bash environments.

## Changes

### File 1: `skills/automap/SKILL.md`

**Change 1 — New `<script_paths>` section** (inserted between `</usage>` and `<related_skills>`):

- Defines convention: all `scripts/` paths are relative to the skill's base directory
- Instructs Claude to prepend the base directory (provided in the "Base directory for this skill" header) to all script paths
- States: do NOT `cd` to a project directory before calling scripts — pass file paths as arguments

**Change 2 — New entry in `<common_mistakes>`:**

- Reinforces that changing the working directory before calling the wrapper causes failure because `scripts/` resolves relative to the skill directory

### File 2: `skills/automap/scripts/automap-wrapper.sh`

**Change — `extract_targets()` function (lines 99-105):**

| Before | After |
|--------|-------|
| `grep -oP '<Target[^>]*\sname="[^"]*"'` | `grep -o '<Target[^>]* name="[^"]*"'` |
| `grep -oP 'name="[^"]*"'` | `grep -o 'name="[^"]*"'` |
| `grep -oP 'TargetName="[^"]*"'` | `grep -o 'TargetName="[^"]*"'` |

Dropped `-P` flag entirely. Replaced `\s` with a literal space. The XML is machine-generated with predictable formatting, so a literal space is sufficient.

## Verification

Tested by invoking the automap skill to build `automap-jobs/express-trial-guide.waj` from `C:\Projects\epublisher-express-trial`:

1. **Path fix confirmed:** Claude constructed `bash /full/path/to/automap/scripts/automap-wrapper.sh` using the skill's base directory instead of bare `scripts/...`
2. **grep fix confirmed:** Build succeeded without `LC_ALL=en_US.UTF-8` workaround — no more locale errors
3. **Build output:** Deployed successfully to `C:\Projects\epublisher-docs-publish\deploy\trial-guides\express`

## Scope

- **automap skill only.** The other three skills (epublisher, markdown-plus-plus, reverb2) use the same `scripts/` pattern but don't execute builds. They can be updated in follow-up if the convention works well.
- **No behavioral changes** to the wrapper script — only the regex engine changed, not the matching logic.
