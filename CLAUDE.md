# CLAUDE.md

## Behavioral Rules

### Version bump before PR

Run the bump script before creating a PR; include the bump in the PR:

```bash
scripts/bump-version.sh [patch|minor|major]
```

### New Python Tools

Create new skill Python tools by copying `templates/skill-python-tool.py` — it bakes in the UTF-8 conventions that Windows locale codepages otherwise break. Rules in CONTRIBUTING.md "New Python Tools".

### Plans vs. Issues

Once a plan becomes a GitHub issue, the issue is authoritative; local plan files are temporary working documents. Convention: `docs/solutions/plan-documents-workflow.md`.

## Documented Solutions

`docs/solutions/` — documented solutions to past problems (bugs, best practices, workflow patterns). Consult when implementing or debugging in documented areas.
