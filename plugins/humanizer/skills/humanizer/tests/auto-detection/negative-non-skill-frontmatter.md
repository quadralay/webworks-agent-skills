---
date: 2026-05-22
status: draft
tags:
  - documentation
  - planning
---

# Negative fixture: non-skill frontmatter

This file has YAML frontmatter but the keys (`date`, `status`,
`tags`) are not the skill manifest shape. Heuristic 2 requires all
three of `name:`, `description:`, and `allowed-tools:`; none of the
three is present here, so heuristic 2 does not fire.

The filename is arbitrary (heuristic 1 does not fire). The path has
no skill-shaped components (heuristic 3 does not fire). There is no
sibling `SKILL.md` (heuristic 4 does not fire). Fallback applies
and the file classifies as `prose`.

This fixture exists to confirm that the frontmatter heuristic
checks for the *shape* of the manifest header, not merely the
presence of frontmatter.
