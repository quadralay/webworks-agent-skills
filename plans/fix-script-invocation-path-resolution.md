# Fix: Script Invocation Path Resolution

## Overview

When the automap skill is invoked, Claude attempts to run wrapper scripts using incorrect relative paths, causing first-attempt failures. This fix standardizes script invocation patterns across all four webworks-claude-skills using `${CLAUDE_PLUGIN_ROOT}` for reliable path resolution.

## Problem Statement

**Current behavior:**
```bash
./scripts/automap-wrapper.sh  # Fails - relative to user's CWD
./.claude/plugins/cache/...    # Fails - wrong directory prefix
```

**Expected behavior:**
```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/automap-wrapper.sh  # Works
```

### Root Causes

1. **Path confusion**: `./.claude/` is CWD-relative, but plugins are cached in `~/.claude/plugins/cache/`
2. **Windows compatibility**: Git Bash requires explicit `bash` prefix for `.sh` scripts
3. **Missing documentation**: No guidance on using `${CLAUDE_PLUGIN_ROOT}` environment variable

### Environment

- Windows 11, Git Bash
- Claude Code CLI
- Affects all four skills: automap, epublisher, reverb2, markdown-plus-plus

## Proposed Solution

Add "Invoking Scripts" documentation to each skill and update all script path references to use the portable `${CLAUDE_PLUGIN_ROOT}` pattern.

### Invocation Patterns by Script Type

| Type | Pattern |
|------|---------|
| Shell (.sh) | `bash ${CLAUDE_PLUGIN_ROOT}/skills/<skill>/scripts/<script>.sh` |
| Python (.py) | `python ${CLAUDE_PLUGIN_ROOT}/skills/<skill>/scripts/<script>.py` |
| Node.js (.js) | `node ${CLAUDE_PLUGIN_ROOT}/skills/<skill>/scripts/<script>.js` |

## Acceptance Criteria

- [ ] All SKILL.md files include "Invoking Scripts" subsection in `<usage>` section
- [ ] All script path examples use `${CLAUDE_PLUGIN_ROOT}` instead of `./scripts/`
- [ ] Shell scripts prefixed with `bash` for Windows compatibility
- [ ] Reference docs and workflow docs updated with correct paths
- [ ] Troubleshooting section added for "Script not found" errors
- [ ] Scripts work on first invocation (Windows Git Bash, macOS, Linux)

## Technical Approach

### Phase 1: Add "Invoking Scripts" Documentation

Add this subsection to each skill's `<usage>` section:

```markdown
### Invoking Scripts

All scripts must be invoked using the `${CLAUDE_PLUGIN_ROOT}` environment variable:

\`\`\`bash
# Shell scripts - always use 'bash' prefix for Windows compatibility
bash ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/automap-wrapper.sh [options] <project-file>

# Python scripts
python ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/parse-stationery.py stationery.wxsp
\`\`\`

**Why this pattern?**
- `${CLAUDE_PLUGIN_ROOT}` provides the absolute path to the plugin directory
- Relative paths like `./scripts/` fail because they're relative to your working directory, not the plugin cache
- The `bash` prefix ensures Windows Git Bash executes `.sh` scripts correctly
```

### Phase 2: Update All Script References

#### Automap Skill (~60 occurrences)

**SKILL.md** (18 occurrences):
- Lines 70, 73, 76: Quick start examples
- Lines 104, 115: Environment variable examples
- Lines 143-174: Python script references
- Lines 192, 275, 307, 320, 324, 332, 335: Additional examples

**cli-reference.md** (40+ occurrences):
- Lines 56, 59-61, 70, 100, 103, 111, 151-152, 159
- Lines 209, 214, 221, 226, 233, 238, 264, 269, 286
- Lines 447-448, 455, 462, 469, 476-480, 487, 494, 501

**job-file-guide.md** (9 occurrences):
- Lines 263-274, 362, 428, 431, 455, 463, 474, 489

#### Epublisher Skill (~4 occurrences)

**SKILL.md**:
- Lines 142, 155: Script references

**file-resolver-guide.md**:
- 1 occurrence

#### Reverb2 Skill (~14 occurrences)

**SKILL.md** (10 occurrences):
- Lines 89, 136, 180, 188, 227, 256, 268-277, 284, 287

**Workflow docs** (12 occurrences across 4 files):
- `browser-testing.md`: 3 occurrences
- `csh-analysis.md`: 2 occurrences
- `generate-report.md`: 5 occurrences
- `scss-theming.md`: 4 occurrences

#### Markdown-plus-plus Skill (~3 occurrences)

**SKILL.md**:
- Lines 143, 427, 447

**best-practices.md**:
- 1 occurrence

### Phase 3: Add Troubleshooting Section

Add to each SKILL.md:

```markdown
### Troubleshooting: Script Not Found

If you see "No such file or directory" when running scripts:

1. **Verify the variable is set**: `echo ${CLAUDE_PLUGIN_ROOT}`
2. **Use `bash` prefix on Windows**: Required for Git Bash
3. **Use forward slashes only**: Never use backslashes in paths
4. **Check the full path**: Plugin cache is at `~/.claude/plugins/cache/`, not `./.claude/`
```

## Files Requiring Changes

### Must Update (skill documentation)

| File | Occurrences | Priority |
|------|-------------|----------|
| `skills/automap/SKILL.md` | 18 | P1 |
| `skills/automap/references/cli-reference.md` | 40+ | P1 |
| `skills/automap/references/job-file-guide.md` | 9 | P1 |
| `skills/epublisher/SKILL.md` | 3 | P1 |
| `skills/epublisher/references/file-resolver-guide.md` | 1 | P2 |
| `skills/reverb2/SKILL.md` | 10 | P1 |
| `skills/reverb2/workflows/browser-testing.md` | 3 | P2 |
| `skills/reverb2/workflows/csh-analysis.md` | 2 | P2 |
| `skills/reverb2/workflows/generate-report.md` | 5 | P2 |
| `skills/reverb2/workflows/scss-theming.md` | 4 | P2 |
| `skills/markdown-plus-plus/SKILL.md` | 2 | P1 |
| `skills/markdown-plus-plus/references/best-practices.md` | 1 | P2 |

### Do NOT Update (correct as-is)

| File | Reason |
|------|--------|
| `CLAUDE.md` (project root) | Project-level script, CWD is repo root |
| `CONTRIBUTING.md` | Project-level script, CWD is repo root |
| `scripts/bump-version.sh` | Project script, not plugin script |
| `automap-wrapper.sh` (internal `$SCRIPT_DIR`) | Uses runtime path resolution correctly |

## Search and Replace Patterns

### Shell Scripts

```
# Find
./scripts/automap-wrapper.sh
./scripts/detect-installation.sh

# Replace with
bash ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/automap-wrapper.sh
bash ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/detect-installation.sh
```

### Python Scripts

```
# Find
python scripts/parse-stationery.py
python scripts/validate-job.py

# Replace with
python ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/parse-stationery.py
python ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/validate-job.py
```

### Node.js Scripts

```
# Find
node scripts/browser-test.js

# Replace with
node ${CLAUDE_PLUGIN_ROOT}/skills/reverb2/scripts/browser-test.js
```

## Testing Plan

### Pre-deployment Verification

1. **Windows + Git Bash**: Primary test environment (issue reporter's environment)
2. **macOS**: Verify no regression
3. **Linux**: Verify no regression

### Test Cases

| Test | Command | Expected Result |
|------|---------|-----------------|
| First invocation | `/automap` then run wrapper | Script executes without path error |
| Detect installation | Run detect-installation.sh | Returns AutoMap path or error message |
| Python script | Run parse-stationery.py | Parses stationery file correctly |
| From different CWD | Navigate to `/tmp`, invoke skill | Script still works |

### Validation Commands

```bash
# Verify CLAUDE_PLUGIN_ROOT is set
echo ${CLAUDE_PLUGIN_ROOT}

# Test shell script
bash ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/detect-installation.sh

# Test Python script
python ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/parse-stationery.py --help
```

## Success Metrics

- Scripts execute successfully on first invocation
- No "path not found" errors in normal usage
- Works consistently across Windows Git Bash, macOS, and Linux

## Dependencies

- `CLAUDE_PLUGIN_ROOT` environment variable (set by Claude Code when loading skills)
- Git Bash installed on Windows (for shell script execution)

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `CLAUDE_PLUGIN_ROOT` not set in older Claude Code versions | Low | Document minimum version requirement |
| Search/replace misses edge cases | Medium | Manual review of all changes |
| Breaks working configurations | Low | Paths were already broken; this is additive fix |

## References

### Internal References
- Issue: #42
- Pattern source: `git-worktree` skill (compound-engineering plugin)
- Current wrapper: `skills/automap/scripts/automap-wrapper.sh:36` (correct `$SCRIPT_DIR` usage)

### External References
- [Claude Code Skills Documentation](https://code.claude.com/docs/en/skills)
- [Claude Code Plugins Reference](https://code.claude.com/docs/en/plugins-reference)
- Related issues: anthropics/claude-code#17257 (Windows compatibility), #18527 (path separators)

### Research Notes
- The `git-worktree` skill in compound-engineering demonstrates the correct pattern
- Python scripts need `python` prefix, Node.js scripts need `node` prefix
- Internal script-to-script references using `$SCRIPT_DIR` are already correct
