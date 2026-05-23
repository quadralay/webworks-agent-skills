# Edge fixture: non-standard skill path

Treat the logical path as `lib/agents/foo.md`. The path looks
skill-shaped (contains an `agents` component), but heuristic 3's
pattern list requires `agents` to be preceded by a `.claude/`
component (i.e., `.claude/agents/`). A bare `lib/agents/` does not
match.

The filename is not `SKILL.md`. There is no YAML frontmatter. There
is no sibling `SKILL.md`. All four heuristics fail and the file
falls through to `prose`.

If real-world skill layouts consistently use this shape, the
documented fix is to extend heuristic 3's pattern list rather than
relax the matching rule. For now, an operator with this layout can
force `audience=skill-file` for the invocation.
