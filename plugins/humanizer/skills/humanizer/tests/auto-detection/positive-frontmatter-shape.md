---
name: positive-frontmatter-shape-fixture
description: Fixture exercising heuristic 2 (YAML frontmatter shape).
allowed-tools:
  - Read
  - Grep
---

# Positive fixture: frontmatter shape

The filename here is not `SKILL.md`, so heuristic 1 does not fire.
The path contains no skill-shaped components, so heuristic 3 does
not fire. There is no sibling `SKILL.md`, so heuristic 4 does not
fire.

Heuristic 2 fires because the first non-empty content is a `---`
YAML block containing all three required keys: `name`,
`description`, and `allowed-tools`. The file classifies as
`skill-file` regardless of the arbitrary filename.
