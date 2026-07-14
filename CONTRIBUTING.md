# Contributing to WebWorks Agent Skills

## How to Contribute

- Enhance existing skills
- Add new skills for other formats or workflows
- Improve helper scripts
- Report bugs and suggest features

## Repository Structure

```
plugins/
├── webworks-agent-skills/         # Native plugin (owned by this repo)
│   ├── .claude-plugin/plugin.json
│   └── skills/
│       └── skill-name/
│           ├── SKILL.md           # Skill definition
│           ├── scripts/           # Helper scripts (optional)
│           │   └── lib/           # Shared Python modules
│           └── references/        # Reference documentation
└── humanizer/                     # Vendored from blader/humanizer
    ├── .claude-plugin/plugin.json # Plugin wrapper (owned by this repo)
    ├── README.md                  # Vendoring decision and divergence plan
    └── skills/
        └── humanizer/             # Vendored copy (see UPSTREAM.md)
            ├── SKILL.md
            ├── LICENSE            # Upstream MIT license, preserved unchanged
            └── UPSTREAM.md        # Source URL, last sync SHA, port process
```

## Pre-Release Feature Annotations

Skills track ePublisher **trunk**, not the shipped release: content for features
that have landed in source but not yet shipped is written immediately, annotated
with the target release, and the annotations are stripped at GA. This keeps the
skills authoritative for early-access/dev builds while protecting users of the
shipped release from being told about functionality they don't have.

**Annotating (pre-GA):**

- A wholly new reference for an unshipped feature opens with a blockquote banner:
  `> **Applies to ePublisher <version> and later** (new in <version>).`
- A new section or sentence inside an existing file carries the inline marker
  `(new in <version>)` or `(<version>+)` — e.g. `(new in 2026.1)`, `(2026.1+)`.
- List the feature under a `### ePublisher <version>` heading in the epublisher
  skill's `references/version-compatibility.md` so agents can gate on the
  user's installed version.

**Stripping (at GA):**

1. `grep -rn "new in <version>\|<version>+\|Applies to ePublisher <version>" plugins/`
2. Remove banners and inline markers; keep the content. Version-compatibility
   entries stay (they become the historical record).
3. Bump the plugin version; note the stripped release in the PR.

The cycle then resets for the next release's features. Precedents:
`useAsStationery` (annotated pre-2026.1-GA) and the 2026.1 federated parcel
composition set.

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
- **PowerShell scripts (Windows PowerShell 5.1 baseline):** Program wrappers with error handling for Windows-only tools (e.g., AutoMap)
- **Documentation:** Clear language with examples
- **Testing:** Validate with real ePublisher projects

### New Python Tools

Start new Python tools from [`templates/skill-python-tool.py`](templates/skill-python-tool.py). ePublisher content is Unicode-first (Japanese outputs, CJK landmark IDs, non-ASCII group names), and Python on Windows defaults console I/O, subprocess pipes, and text-mode file I/O to the locale codepage (cp1252/cp932) — so a tool written without explicit encodings breaks on real projects the first time it meets non-ASCII content (#118). The template bakes in the three rules:

1. Call `ensure_utf8()` first thing in `main()` — Python children spawned later start in full UTF-8 mode, and the tool's own stdout/stderr print Unicode safely on any console.
2. Always pass `encoding='utf-8'` to text-mode `open()` / `read_text()` / `write_text()`.
3. Never use bare `text=True` with `subprocess.run` — use the template's `run_utf8()` or pass `encoding='utf-8'` explicitly (pipe decoding ignores `PYTHONIOENCODING`).

Rules 2 and 3 are per-call-site because UTF-8 mode cannot be enabled retroactively for a running interpreter — `ensure_utf8()` covers children and stdio only.

Verify before submitting a PR:

```bash
python scripts/check-python-utf8.py
```

The checker statically enforces all three rules (plus the entry-point preamble) across `plugins/`, `templates/`, and `scripts/`, and exits 1 with `file:line` findings on any violation.

## Versioning

Bump the plugin version **before creating a PR** using the bump script:

```bash
scripts/bump-version.sh patch  # 2.1.0 → 2.1.1 (bug fixes)
scripts/bump-version.sh minor  # 2.1.0 → 2.2.0 (new features)
scripts/bump-version.sh major  # 2.1.0 → 3.0.0 (breaking changes)
```

The script updates both version locations automatically:
- `plugins/webworks-agent-skills/.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`

**Note:** The `humanizer` plugin version in `plugins/humanizer/.claude-plugin/plugin.json` is owned by this repo (the skill is now vendored, not a submodule). It is **not** managed by `bump-version.sh` — bump it manually when humanizer behavior diverges from the vendored baseline. See [plugins/humanizer/skills/humanizer/UPSTREAM.md](plugins/humanizer/skills/humanizer/UPSTREAM.md).

**When to bump:**

| Type | Use For | Example |
|------|---------|---------|
| `patch` | Bug fixes, docs, minor improvements | 2.1.0 → 2.1.1 |
| `minor` | New skills, new features, enhancements | 2.1.0 → 2.2.0 |
| `major` | Breaking changes, major restructuring | 2.1.0 → 3.0.0 |

**Note:** Claude Code is aware of this workflow via CLAUDE.md and will run the bump script when preparing PRs.

## Vendored Plugins

The `humanizer` plugin is a vendored copy of [blader/humanizer](https://github.com/blader/humanizer). It used to be a git submodule but is now maintained as plain files in this repo. No `git submodule init` step is required — a plain `git clone` is sufficient.

**Modifying the vendored skill:** Edit the files under `plugins/humanizer/skills/humanizer/` directly. Behavior changes diverge from upstream by design (skill-file auto-detection, dual-audience profiles). Bump `plugins/humanizer/.claude-plugin/plugin.json` manually when behavior diverges.

**Porting upstream changes:** Review the process in [plugins/humanizer/skills/humanizer/UPSTREAM.md](plugins/humanizer/skills/humanizer/UPSTREAM.md). Manual port only — no automated sync.

## Pull Requests

1. Fork and create a feature branch
2. Test thoroughly
3. Run `scripts/bump-version.sh <type>` to bump version
4. Submit PR with clear description

## License

Contributions are licensed under the project's MIT License.
