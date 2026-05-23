---
name: positive-companion-references-fixture
description: SKILL.md serving as the parent that triggers heuristic 4(b) for references/api.md.
allowed-tools:
  - Read
---

# Companion-directory skill manifest

This `SKILL.md` exists only to make heuristic 4(b) (one-level companion)
fire for `references/api.md` sitting one directory below. The classifier
walks up one level from the `references/` directory and finds this
`SKILL.md`.

This file itself classifies as `skill-file` via heuristic 1 (filename),
not heuristic 4.
