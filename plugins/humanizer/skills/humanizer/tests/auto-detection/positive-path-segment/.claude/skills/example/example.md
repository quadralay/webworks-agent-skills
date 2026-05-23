# Positive fixture: path segment

This file lives at `.claude/skills/example/example.md` (treat the
path as relative to the fixture directory). The path component
sequence `.claude/skills/` matches heuristic 3 and classifies the
file as `skill-file`.

The filename is `example.md`, not `SKILL.md`, so heuristic 1 does
not fire. The file has no YAML frontmatter, so heuristic 2 does not
fire. Heuristic 3 wins.
