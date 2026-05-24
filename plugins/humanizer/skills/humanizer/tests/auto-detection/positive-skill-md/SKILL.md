---
name: positive-skill-md-fixture
description: Fixture exercising heuristic 1 (filename match).
allowed-tools:
  - Read
---

# Positive fixture: filename match

This file is named `SKILL.md`. Heuristic 1 (filename) fires
immediately and classifies the file as `skill-file` without
opening the file or evaluating the path.

The body content is irrelevant to the classifier; only the filename
matters for heuristic 1.
