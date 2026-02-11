# Fix: Script Invocation Path Resolution

**Status: COMPLETED (superseded)**

## Original Problem

When skills referenced scripts using `${CLAUDE_PLUGIN_ROOT}`, the environment variable expanded with OS-native path separators. On Windows, this produced backslash paths (e.g., `C:\Users\...\skills\automap\scripts\`) which broke bash script execution.

## Solution Applied

Replaced all `${CLAUDE_PLUGIN_ROOT}/skills/<skill>/scripts/` references with paths relative to each skill's SKILL.md location:

| Reference Type | Old Pattern | New Pattern |
|---|---|---|
| Same-skill | `${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/foo.sh` | `scripts/foo.sh` |
| Cross-skill | `${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/foo.sh` (from reverb2) | `../automap/scripts/foo.sh` |

### Why Relative Paths

- **Cross-platform**: No OS-specific path separator issues
- **No environment variable dependency**: Works regardless of whether `CLAUDE_PLUGIN_ROOT` is set or how it expands
- **Simpler**: Claude resolves relative paths from the SKILL.md location

### Files Updated

| Skill | Files Changed |
|---|---|
| automap | SKILL.md (already done), references/cli-reference.md, references/job-file-guide.md |
| epublisher | SKILL.md, references/file-resolver-guide.md |
| markdown-plus-plus | SKILL.md, references/best-practices.md |
| reverb2 | SKILL.md, workflows/browser-testing.md, workflows/csh-analysis.md, workflows/generate-report.md, workflows/scss-theming.md |

**Total: 105 occurrences replaced across 12 files.**

---

**Completed**: 2026-02-11
**Original Plan**: 2025-01-xx (introduced `${CLAUDE_PLUGIN_ROOT}` pattern)
