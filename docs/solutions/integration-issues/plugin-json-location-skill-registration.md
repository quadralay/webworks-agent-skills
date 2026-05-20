---
title: "Claude Code Plugin Skills Not Registering - plugin.json Path Issue"
category: "integration-issues"
tags:
  - claude-code
  - plugin-structure
  - skill-registration
  - marketplace
  - configuration
  - github-actions
problem_type: "Configuration/Architecture"
components_affected:
  - plugin.json
  - .claude-plugin/
  - skill discovery
  - version-bump workflow
date_solved: "2026-01-08"
severity: "High"
status: "Resolved"
related_prs:
  - 26
  - 27
---

# Claude Code Plugin Skills Not Registering

## Problem

Skills in the webworks-claude-skills plugin were not being registered with Claude Code's Skill tool. Attempting to invoke any skill resulted in:

```
Unknown skill: webworks-claude-skills:automap
```

All four skills (automap, epublisher, markdown-plus-plus, reverb2) were affected.

## Root Cause

The `plugin.json` file was in the **wrong location**. Claude Code expects plugin configuration to be in a `.claude-plugin/` subdirectory.

**Incorrect (not working):**
```
plugins/webworks-claude-skills/
├── plugin.json              ← WRONG
└── skills/
```

**Correct (working):**
```
plugins/webworks-claude-skills/
├── .claude-plugin/
│   └── plugin.json          ← CORRECT
└── skills/
```

## Investigation

Compared the webworks-claude-skills plugin structure against the working compound-engineering plugin:

| Plugin | plugin.json Location | Skills Working? |
|--------|---------------------|-----------------|
| compound-engineering | `.claude-plugin/plugin.json` | Yes |
| webworks-claude-skills | `plugin.json` (root) | No |

The compound-engineering plugin cache showed the expected structure:
```
~/.claude/plugins/cache/every-marketplace/compound-engineering/2.22.0/.claude-plugin/plugin.json
```

## Solution

### 1. Move plugin.json

```bash
mkdir -p plugins/webworks-claude-skills/.claude-plugin
git mv plugins/webworks-claude-skills/plugin.json plugins/webworks-claude-skills/.claude-plugin/
```

### 2. Update plugin.json Schema

Changed from simple string author to object format matching Claude Code's official schema:

**Before:**
```json
{
  "name": "webworks-claude-skills",
  "version": "2.0.8",
  "author": "Quadralay Corporation",
  "skills": [
    { "name": "automap", "path": "skills/automap" },
    ...
  ]
}
```

**After:**
```json
{
  "name": "webworks-claude-skills",
  "version": "2.1.0",
  "author": {
    "name": "Quadralay Corporation",
    "email": "support@webworks.com",
    "url": "https://github.com/quadralay"
  },
  "homepage": "https://github.com/quadralay/webworks-claude-skills",
  "repository": "https://github.com/quadralay/webworks-claude-skills",
  "license": "MIT"
}
```

**Key changes:**
- Removed explicit `skills` array (skills are auto-discovered from `skills/*/SKILL.md`)
- Changed `author` from string to object with name/email/url
- Added `homepage`, `repository`, `license` fields
- Bumped version to 2.1.0

### 3. Update Marketplace Version

Updated `.claude-plugin/marketplace.json` version from 2.0.8 to 2.1.0 to match.

### 4. Fix Version-Bump Path References (Secondary Issue)

After the plugin.json move, the version-bump tooling broke because it referenced the old path.

At the time of this fix, version bumping ran through `.github/workflows/version-bump.yml`, which had three references to `plugins/webworks-claude-skills/plugin.json` that needed to be updated to `plugins/webworks-claude-skills/.claude-plugin/plugin.json`.

That workflow was later removed (commit `fd51c6e`) and replaced by a manual script: `scripts/bump-version.sh`. The script reads the same `.claude-plugin/plugin.json` path, so the principle still applies — when moving plugin config, audit every consumer (CI workflows, scripts, docs) that references the old location.

> **Note (2026-05-09):** The automated version-bump workflow was later removed (commit `fd51c6e`) and replaced with the manual `scripts/bump-version.sh` script. Version bumps are now run locally before opening a PR. The path-cascade lesson still applies — when moving config files, update every script and workflow that references the old path.

## Verification

After the fix:
1. Clear plugin cache: Delete `~/.claude/plugins/cache/webworks-claude-skills`
2. Restart Claude Code
3. Test skill invocation: `webworks-claude-skills:automap`

All four skills now register and are invokable.

## Key Learnings

1. **Plugin structure matters**: Claude Code requires `.claude-plugin/plugin.json`, not `plugin.json` at root
2. **Skills are auto-discovered**: No need for explicit `skills` array - Claude scans `skills/*/SKILL.md`
3. **Author must be object**: String format doesn't match official schema
4. **CI/CD paths cascade**: When moving config files, update all workflow references
5. **Compare to working examples**: The compound-engineering plugin served as the reference implementation

## Prevention

### Pre-commit Check
Verify plugin.json exists at correct path:
```bash
test -f plugins/*/\.claude-plugin/plugin.json || echo "ERROR: plugin.json in wrong location"
```

### CI/CD Validation
Add workflow step to validate plugin structure before merge.

### Documentation
Always document the correct plugin structure for new developers.

## Related Files

- `plugins/webworks-claude-skills/.claude-plugin/plugin.json` - Plugin configuration
- `.claude-plugin/marketplace.json` - Marketplace definition
- `scripts/bump-version.sh` - Manual version-bump script (replaced the prior `.github/workflows/version-bump.yml` automation in commit `fd51c6e`)
- `plans/fix-plugin-structure-for-skill-registration.md` - Original investigation plan

## References

- [PR #26](https://github.com/quadralay/webworks-claude-skills/pull/26) - Plugin structure fix
- [PR #27](https://github.com/quadralay/webworks-claude-skills/pull/27) - Workflow path fix
- compound-engineering plugin - Reference implementation
