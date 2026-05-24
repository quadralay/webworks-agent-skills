# Negative fixture: README-style file

A typical top-level `README.md` (renamed here so the fixture name
documents its purpose). When evaluating against the classifier,
treat the logical path as `README.md`.

The filename is not `SKILL.md`. There is no YAML frontmatter. The
path has no skill-shaped components. There is no sibling
`SKILL.md`. All four heuristics fail and the file falls through to
the `prose` default.

## What this README would normally contain

Just regular project documentation — overview, installation steps,
usage examples. Nothing in the body content influences the
classification; the classifier looks at the path and frontmatter
only.
