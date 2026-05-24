# Negative fixture: CHANGELOG-style file

A typical top-level `CHANGELOG.md` (renamed for fixture purposes).
Treat the logical path as `CHANGELOG.md`.

No filename match (heuristic 1). No YAML frontmatter (heuristic 2).
No skill-shaped path components (heuristic 3). No sibling
`SKILL.md` (heuristic 4). The file falls through to `prose`.

## 1.0.0 — sample entry

- Added feature X.
- Fixed bug Y.

The body content does not influence the classifier.
