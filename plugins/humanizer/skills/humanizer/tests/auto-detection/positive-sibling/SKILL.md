---
name: positive-sibling-fixture
description: SKILL.md serving as the sibling that triggers heuristic 4 for notes.md.
allowed-tools:
  - Read
---

# Sibling skill manifest

This `SKILL.md` exists only to make heuristic 4 fire for the
co-located `notes.md` in the same directory. The classifier checks
the immediate parent directory for a `SKILL.md`; if one is present,
companion files in that directory classify as `skill-file`.

This file itself would classify as `skill-file` via heuristic 1
(filename), not heuristic 4.
