# Positive fixture: companion reference

This file is `references/api.md`, sitting one directory below a
`SKILL.md`. Heuristic 4(b) walks up one level from `references/`
(a known companion-directory name) and finds `SKILL.md`, so the file
classifies as `skill-file`.

Heuristic 1 does not fire (filename is `api.md`, not `SKILL.md`).
Heuristic 2 does not fire (no YAML frontmatter). Heuristic 3 does not
fire (no `.claude/`, `skills/`, or `plugins/<name>/skills/<name>/`
component sequence when the path is read as
`positive-companion-references/references/api.md` relative to the
fixture root). Heuristic 4(a) does not fire (the immediate parent
`references/` contains no `SKILL.md`). Heuristic 4(b) wins.
