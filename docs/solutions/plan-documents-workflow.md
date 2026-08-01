---
title: Plan Documents as Development Artifacts
category: workflow-improvements
component:
  - plans
  - documentation
  - code-review
symptoms:
  - Code review flags plan files as "process artifacts" that shouldn't be merged
  - Confusion about whether plans belong in the repository
  - Unclear distinction between plans and GitHub Issues
root_cause: No documented convention for when plans should be kept vs discarded, and how they relate to GitHub Issues as the repository transitions from private development to public contribution
date_solved: 2025-12-30
related_files:
  - plans/README.md
  - plans/add-skip-reports-option.md
---

# Plan Documents as Development Artifacts

## Problem

During code review, a plan file was flagged as a "process artifact" that shouldn't be merged:

> "The plan is 6x longer than the changes it describes. Plans belong in PRs/issues, not merged into the repo."

However, the plan served as the **problem statement** (equivalent to a GitHub Issue) for work done before the repository had public issue tracking. This created a conflict:

- Review agents see plans as disposable scaffolding
- Developer sees plans as the canonical record of "why" decisions were made

## Root Cause

No convention existed for:
1. When plan documents should be kept vs discarded
2. How plans relate to GitHub Issues
3. What happens to plans when transitioning from private development to public contribution

## Solution

### Establish Clear Workflow Phases

**Development Phase (Private):**
- `plans/` serves as the issue tracker
- Plans contain problem statements, proposed solutions, and implementation notes
- Plans are merged with the code as historical record

**Public Phase (After Launch):**
- GitHub Issues become the canonical problem statement
- Plans are optional for complex implementations
- Existing plans remain as historical context

### Create `plans/README.md`

Document the convention explicitly:

```markdown
# Plans

Implementation plans for features and improvements.

## Workflow

**For new work:** Create a GitHub Issue first, then optionally
create a detailed plan here for complex implementations.

**Naming convention:** `issue-{number}-{description}.md` or
`{description}.md` for pre-issue exploration.

## Archive

Plans created before the repo went public remain here for
historical context. They document early design decisions
and implementation rationale.
```

### Update Review Expectations

Plans in `plans/` are valid artifacts when:
- They document the problem statement (pre-public phase)
- They provide implementation rationale for complex changes
- They serve as decision records (lightweight ADRs)

## Prevention

- Document workflow conventions in `plans/README.md`
- Reference the convention in CONTRIBUTING.md when the repo goes public
- For complex work: create issue first, then `plans/issue-{number}-*.md`

## When to Keep vs Discard Plans

| Scenario | Keep | Discard |
|----------|------|---------|
| Documents design decisions | ✓ | |
| Contains problem statement (no issue) | ✓ | |
| Trivial implementation details only | | ✓ |
| Complex multi-step implementation | ✓ | |
| References external research | ✓ | |

## Current Convention (2026)

Plan files are no longer retained in the repository. A plan is a temporary local working document; once it becomes a GitHub issue, the issue is the canonical problem statement and the local plan file is deleted. The earlier conventions — merged plans in `plans/`, then date-prefixed plans in `docs/plans/` — were retired when the retained plans were removed as process artifacts (commit 8d76cc8).

## Related

- PR #17: Added `plans/README.md` establishing the original workflow (file since removed)
- Commit 8d76cc8: removed retained plans from `plans/` and `docs/plans/`
