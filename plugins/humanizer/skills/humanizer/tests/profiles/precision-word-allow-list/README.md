# Precision-word allow-list fixture

This fixture exercises the Rule 22 precision-word allow-list documented in
`plugins/humanizer/skills/humanizer/SKILL.md` (section: **22. Filler
Phrases**). The assertion is that the word `unchanged` survives a
filler-phrase rewrite when the surrounding text would otherwise look like a
canonical filler-phrase target.

## Cross-repo source

The failing phrase reproduced in `input.md` is

> *"continues to work unchanged when the file is later assembled"*

drawn verbatim from the worked-example diff at
`quadralay/markdown-plus-plus` PR #107, commit `6fda523`. In that commit a
humanizer pass over
`plugins/markdown-plus-plus/skills/markdown-plus-plus/references/best-practices.md`
rewrote the phrase to *"keeps working when the file is later assembled,"*
stripping `unchanged` and converting a normative claim about pipeline
behavior into an ambiguous one. The precision-word allow-list added by
issue #95 blocks that rewrite.

## Assertion

Under the `skill-file` profile (or under the default `audience=auto` once
the fixture's path puts it in a skill-file-classified location), Rule 22's
filler-phrase rewrite must preserve `unchanged` in the failing phrase. The
other filler-phrase rewrites in the surrounding sentences (for example
`"In order to"` → `"To"`) are still expected to fire — the allow-list
narrows Rule 22, it does not disable the rule.

A future test runner reads `input.md.expected` as a single token,
compares it against the assertion outcome, and reports pass/fail. The
token recorded here is `unchanged-preserved`, naming the assertion rather
than the classification.

## Path interpretation (important caveat)

This fixture is not directly runnable against the production classifier.
The on-disk path begins with
`plugins/humanizer/skills/humanizer/tests/profiles/`, which trips
heuristic 3's `plugins/<name>/skills/<name>/` pattern. If you pass
`input.md`'s real path to `/humanizer`, the classifier resolves the file
to `skill-file` regardless of any other heuristic.

To exercise the fixture in a way that exposes the rule-application
behavior, either:

- Copy `input.md` to a location outside any `skills/<name>/`,
  `.claude/`, or `plugins/<name>/skills/<name>/` ancestor and pass the
  copied path, or
- Force the profile explicitly:
  `/humanizer audience=skill-file plugins/humanizer/skills/humanizer/tests/profiles/precision-word-allow-list/input.md`

The same caveat applies to the sibling corpus
`plugins/humanizer/skills/humanizer/tests/auto-detection/`; see its
`README.md` for the original statement of the constraint.
