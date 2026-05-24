# Auto-detection fixtures

This corpus exercises the audience classifier documented in
`plugins/humanizer/skills/humanizer/SKILL.md` (section: **Audience
classification**). Each fixture pairs a sample file with a sibling
`<fixture>.expected` file containing a single token — either
`skill-file` or `prose` — that names the classification the
heuristics should produce.

The corpus is inspectable today. A future test runner can consume
the `.expected` files without parsing YAML. This issue does not wire
up a runner; verification is by reading the fixtures against the
heuristic algorithm.

## Path interpretation (important caveat)

The classifier evaluates a file's path against four heuristics
(filename, frontmatter shape, path-segment match, sibling
`SKILL.md`). When evaluating a fixture, treat the path *as it
appears within the fixture's own subdirectory* — not the absolute
path on disk.

**This corpus is not directly runnable against the production
classifier.** Every fixture's real on-disk path begins with
`plugins/humanizer/skills/humanizer/tests/auto-detection/`, which
trips heuristic 3's `plugins/<name>/skills/<name>/` pattern. If you
pass a fixture's real path to `/humanizer`, every negative case will
misclassify as `skill-file`.

To exercise the fixtures against the classifier, copy them to a
location outside any `skills/<name>/`, `.claude/`, or
`plugins/<name>/skills/<name>/` ancestor — or use a runner that
strips the corpus-root prefix before applying heuristic 3.

Concretely:

- `positive-path-segment/.claude/skills/example/example.md` is
  tested as if its path were `.claude/skills/example/example.md`.
- `edge-non-standard-path/lib/agents/foo.md` is tested as if its
  path were `lib/agents/foo.md`.
- Flat fixtures like `negative-readme.md` are tested as if their
  path were just the filename (e.g., `README.md`).

## Fixtures

### Positive (must classify as `skill-file`)

- `positive-skill-md/SKILL.md` — heuristic 1 (filename match).
- `positive-frontmatter-shape.md` — heuristic 2. Arbitrary filename
  with YAML frontmatter containing `name`, `description`, and
  `allowed-tools`.
- `positive-path-segment/.claude/skills/example/example.md` —
  heuristic 3. Path component sequence `.claude/skills/` fires.
- `positive-sibling/notes.md` — heuristic 4(a) (co-located). The
  file's immediate parent directory also contains `SKILL.md`.
- `positive-companion-references/references/api.md` — heuristic 4(b)
  (one-level companion). The immediate parent directory is named
  `references`, and the directory one level up contains `SKILL.md`.

### Negative (must classify as `prose`)

- `negative-readme.md` — top-level `README.md`-shaped file. No
  heuristic fires. Fallback → `prose`.
- `negative-whitepaper.md` — documentation file with no SKILL.md
  sibling. Fallback → `prose`.
- `negative-changelog.md` — top-level `CHANGELOG.md`-shaped file.
  Fallback → `prose`.
- `negative-non-skill-frontmatter.md` — file with YAML frontmatter
  whose keys (`date:`, `status:`) are not the skill manifest shape.
  Heuristic 2 requires all three of `name:`, `description:`, and
  `allowed-tools:`. Fallback → `prose`.

### Edge cases (decision documented per case)

- `edge-docs-skill-md/docs/SKILL.md` — the filename is `SKILL.md`
  but the path is documentation-shaped (`docs/`). Heuristic 1
  (filename) wins because it has the highest priority. Classification:
  `skill-file`. An operator who genuinely has a documentation file
  with that exact name (rare) can force `audience=prose` for the
  invocation.

- `edge-non-standard-path/lib/agents/foo.md` — the path looks
  skill-shaped but does not match heuristic 3's component list (the
  `agents` component is only recognized when preceded by `.claude`).
  No sibling `SKILL.md`. No skill-shaped frontmatter. Falls through
  to `prose`. If real-world layouts consistently miss this way, the
  fix is to extend heuristic 3's pattern list rather than relax
  matching.
