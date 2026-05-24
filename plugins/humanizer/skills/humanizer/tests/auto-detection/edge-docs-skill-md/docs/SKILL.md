# Edge fixture: docs/SKILL.md

Treat the logical path as `docs/SKILL.md`. The path is
documentation-shaped (a `docs/` directory at the root), but the
filename is exactly `SKILL.md` (case-sensitive).

Heuristic 1 (filename) fires first because it has the highest
priority in the first-match-wins ordering. The file classifies as
`skill-file` even though the surrounding directory suggests
documentation. This is the documented behavior — the rare case
where a documentation file happens to use the exact filename
`SKILL.md` needs an explicit `audience=prose` override.

Note that this fixture has no YAML frontmatter. If it did, heuristic
2 would also classify it as `skill-file`. The first-match-wins
priority means heuristic 1 wins regardless.
