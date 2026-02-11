# Contributing to WebWorks Claude Skills

## How to Contribute

- Enhance existing skills
- Add new skills for other formats or workflows
- Improve helper scripts
- Report bugs and suggest features

## Repository Structure

```
plugins/webworks-claude-skills/
├── plugin.json
└── skills/
    └── skill-name/
        ├── SKILL.md           # Skill definition
        ├── scripts/           # Helper scripts (optional)
        │   └── lib/           # Shared Python modules
        └── references/        # Reference documentation
```

## SKILL.md Authoring

### Size Limit

Keep SKILL.md files under **500 lines**. If a skill exceeds this limit:

1. Move detailed examples to `references/examples.md`
2. Move edge cases and validation rules to `references/syntax-reference.md`
3. Keep only essential syntax and quick reference in SKILL.md

### Special Characters

Avoid these character sequences in markdown tables - they cause bash parsing errors during skill loading:

- `` `!` `` (backtick-exclamation-backtick)
- `` `$` `` (backtick-dollar-backtick)

Use bullet lists instead of tables for syntax documentation with special characters.

See [docs/solutions/bash-syntax-errors-in-skill-tables.md](docs/solutions/bash-syntax-errors-in-skill-tables.md) for details.

## Development Guidelines

- **Python scripts:** Parsing, validation, complex logic
- **Shell scripts:** Program wrappers with error handling
- **Documentation:** Clear language with examples
- **Testing:** Validate with real ePublisher projects

## Versioning

Bump the plugin version **before creating a PR** using the bump script:

```bash
scripts/bump-version.sh patch  # 2.1.0 → 2.1.1 (bug fixes)
scripts/bump-version.sh minor  # 2.1.0 → 2.2.0 (new features)
scripts/bump-version.sh major  # 2.1.0 → 3.0.0 (breaking changes)
```

The script updates both version locations automatically:
- `plugins/webworks-claude-skills/.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`

**When to bump:**

| Type | Use For | Example |
|------|---------|---------|
| `patch` | Bug fixes, docs, minor improvements | 2.1.0 → 2.1.1 |
| `minor` | New skills, new features, enhancements | 2.1.0 → 2.2.0 |
| `major` | Breaking changes, major restructuring | 2.1.0 → 3.0.0 |

**Note:** Claude Code is aware of this workflow via CLAUDE.md and will run the bump script when preparing PRs.

## Pull Requests

1. Fork and create a feature branch
2. Test thoroughly
3. Run `scripts/bump-version.sh <type>` to bump version
4. Submit PR with clear description

## License

Contributions are licensed under the project's MIT License.
