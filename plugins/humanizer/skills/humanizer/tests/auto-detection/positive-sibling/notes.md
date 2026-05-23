# Positive fixture: sibling SKILL.md

This file is `notes.md`, co-located with `SKILL.md` in the same
directory. The classifier checks the immediate parent directory and
finds `SKILL.md` next to this file, so heuristic 4 fires and the
file classifies as `skill-file`.

The filename `notes.md` does not match heuristic 1. There is no
YAML frontmatter, so heuristic 2 does not fire. The path (treated
as relative to the fixture directory) contains no skill-shaped
components, so heuristic 3 does not fire. Heuristic 4 wins.
