---
title: Bash Syntax Errors from Character Sequences in SKILL.md Tables
category: skill-authoring
component:
  - skill-loading
  - bash-parsing
symptoms:
  - Skill fails to load with bash syntax error
  - "syntax error near unexpected token" message
  - Error mentions backticks, pipes, or exclamation marks
root_cause: Backticks, exclamation marks, and pipes in markdown tables are interpreted by bash during skill loading
date_solved: 2025-12-27
related_files:
  - CONTRIBUTING.md
---

# Bash Syntax Errors from Character Sequences in SKILL.md Tables

## Problem

When loading a SKILL.md file, Claude Code throws a bash syntax error:

```
Error: Bash command failed for pattern "!` | `": [stderr]
/usr/bin/bash: eval: line 1: syntax error near unexpected token `|'
/usr/bin/bash: eval: line 1: `| < /dev/null'
```

The skill fails to load and cannot be invoked.

## Root Cause

Certain character sequences in markdown tables are interpreted by bash during skill loading:

- **Backticks** (`) are shell command substitution operators
- **Exclamation marks** (!) trigger history expansion in bash
- **Pipes** (|) are command piping operators

When these appear together in a table cell (especially `` `!` | ``), bash attempts to parse them as shell commands.

## Problematic Pattern

This table format causes the error:

```markdown
| Operator | Syntax | Meaning |
|----------|--------|---------|
| `!` | `!a` | NOT operator |
```

The sequence `` | `!` | `` triggers bash parsing.

## Solution

Convert tables containing special character sequences to bullet lists:

**Before (causes error):**
```markdown
| Operator | Syntax | Meaning |
|----------|--------|---------|
| Space | `a b` | AND - all must match |
| Comma | `a,b` | OR - any can match |
| `!` | `!a` | NOT - negation |
```

**After (safe):**
```markdown
- **Space** (AND): `a b` - all must match
- **Comma** (OR): `a,b` - any can match
- **Exclamation** (NOT): `!a` - negation
```

## Why This Works

Bullet lists avoid the problematic interaction between:
1. Table cell delimiters (`|`)
2. Backtick-wrapped special characters
3. Bash's interpretation of these sequences

The content is identical but the formatting doesn't trigger bash parsing.

## Dangerous Sequences to Avoid in Tables

| Sequence | Risk |
|----------|------|
| `` `!` `` | History expansion + command substitution |
| `` `$` `` | Variable expansion |
| `` `|` `` | Pipe operator confusion |
| `` $() `` | Command substitution |

## Prevention Checklist

Before publishing a SKILL.md file:

- [ ] No backticks with `!` in table cells
- [ ] No backticks with `$` in table cells
- [ ] Complex syntax examples in code blocks, not inline in tables
- [ ] Tables reserved for simple text comparisons

## Related

- PR #11: [Fix skill bash syntax error in operators table](https://github.com/quadralay/webworks-claude-skills/pull/11) — original fix landed in the bundled `markdown-plus-plus` SKILL.md (since migrated to `quadralay/markdown-plus-plus` in issue #67)
- `CONTRIBUTING.md` — repo-wide guidance citing this learning
