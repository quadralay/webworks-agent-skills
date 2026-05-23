# Negative fixture: whitepaper-style file

A documentation file with no SKILL.md sibling, no skill-shaped
frontmatter, and no skill-shaped path. Treat the logical path as
`docs/whitepaper.md`.

The path component sequence `docs/whitepaper.md` matches none of
heuristic 3's patterns. The file has no YAML frontmatter, so
heuristic 2 does not fire. The filename is not `SKILL.md`. No
sibling `SKILL.md` exists in the same directory. Fallback applies
and the file classifies as `prose`.

## A made-up whitepaper section

Real whitepapers go on for pages about a problem space, a proposed
solution, and the data that supports the proposal. None of that
matters to the classifier. The path and frontmatter shape are what
get evaluated.
