# CLAUDE.md

## Workflow Commands

This project uses workflow commands from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin).

### Plan

Use `/workflows:plan` to create implementation plans:

1. `/workflows:plan <description>` creates `plans/<name>.md`
2. Review and refine the plan locally
3. Create GitHub issue from plan (select "Create GitHub Issue" option)
4. Delete local plan file after issue creation

**Single source of truth:** Once a plan becomes a GitHub issue, the issue is authoritative. Local plan files are temporary working documents.

### Work

Use `/workflows:work` to implement from an issue:

1. `/workflows:work <issue number or URL>`
2. Creates feature branch from main
3. Implements changes following the plan
4. Commits and creates PR linking to issue

### Review

Use `/workflows:review` for code review:

1. `/workflows:review` (on PR branch) or `/workflows:review <PR number>`
2. Runs parallel review agents (simplicity, patterns, security, etc.)
3. Synthesizes findings by severity (P1/P2/P3)
4. Offers to simplify or fix issues before merge

## Version Management

Bump the plugin version before creating a PR using the bump script:

```bash
scripts/bump-version.sh patch  # 2.1.0 -> 2.1.1 (bug fixes)
scripts/bump-version.sh minor  # 2.1.0 -> 2.2.0 (new features)
scripts/bump-version.sh major  # 2.1.0 -> 3.0.0 (breaking changes)
```

The script updates both `plugin.json` and `marketplace.json` to keep versions synchronized.

**When to bump:**
- `patch`: Bug fixes, documentation updates, minor improvements
- `minor`: New skills, new features, enhancements
- `major`: Breaking changes, major restructuring

**Workflow:**
1. Make your changes
2. Run `scripts/bump-version.sh <type>`
3. Include the version bump in your PR
4. Merge PR - version is already updated

## New Python Tools

Create new skill Python tools by copying `templates/skill-python-tool.py` — it bakes in the UTF-8 conventions (stdio reconfigure, `PYTHONUTF8` for children, explicit encodings on file and subprocess I/O) that Windows locale codepages otherwise break. Rules in CONTRIBUTING.md "New Python Tools".

## Documented Solutions

`docs/solutions/` — documented solutions to past problems (bugs, best practices, workflow patterns), organized by category with YAML frontmatter (`module`, `tags`, `problem_type`). Relevant when implementing or debugging in documented areas.
