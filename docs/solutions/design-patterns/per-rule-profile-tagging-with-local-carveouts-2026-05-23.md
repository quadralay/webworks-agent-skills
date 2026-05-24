---
title: Tag rules with their profile in the heading and carve out precision words and example regions locally
date: 2026-05-23
category: design-patterns
module: humanizer-skill
problem_type: design_pattern
component: tooling
severity: medium
applies_when:
  - A prompt-only rule-based skill needs to apply audience-conditional subsets of its rules in one invocation
  - An audience classifier already records a per-file label; the open question is how the rule body consumes that label
  - One or more rules have a small, enumerable set of phrases that the rule's general guidance would regress on
  - The skill's instruction prose and its embedded example outputs serve different audiences inside the same file
related_components:
  - humanizer
  - skill-architecture
  - tooling
tags:
  - skill-design
  - rule-gating
  - audience-routing
  - prompt-engineering
  - in-heading-tagging
  - precision-words
  - example-region
---

# Tag rules with their profile in the heading and carve out precision words and example regions locally

## Context

Issue #94 added a per-file audience classifier to the humanizer skill — every input now resolves to a `skill-file` or `prose` label and the resolved label is reported in an `Auto-detected audiences:` block. Until issue #95, the label was recorded but never consumed: every rule in `SKILL.md` fired against every file regardless of label, and the skill's own SKILL.md acknowledged this with a placeholder note that *"until the companion dual-audience profile feature lands, every file ends up under the prose profile defined below."*

The worked-example evidence (a humanizer pass against `plugins/markdown-plus-plus/skills/markdown-plus-plus/references/best-practices.md` in `quadralay/markdown-plus-plus` PR #107 commit `6fda523`) produced roughly two genuine improvements per minor regression. The pattern was consistent: rules targeting vagueness, inflated language, and anthropomorphization helped skill-file inputs as much as prose; rules targeting punctuation density, structural parallelism, and rhythm variation regressed them. Two failure modes anchored the design:

1. Rule 22 (filler phrases) rewrote *"continues to work unchanged when the file is later assembled"* to *"keeps working when the file is later assembled,"* stripping the word `unchanged`. In specification-adjacent prose, `unchanged` carries a normative claim that the rewrite erased.
2. The `## PERSONALITY AND SOUL` section recommends patterns ("vary your rhythm," "use 'I' when it fits," "let some mess in") that actively degrade skill-file utility — skill files want uniform structure, impersonal voice, and confident directives.

The classifier exists. The question this work answered: *now how does the rule body actually use the label?*

## Guidance

When a prompt-only rule-based skill needs to consume an audience label, prefer these design choices:

- **Tag each rule's profile in the rule heading, not in a separate config table.** Append `[profile: <value>]` to the heading text itself (e.g., `### 13. Em Dash Overuse  [profile: prose]`). The agent reads the gating at the same moment it reads the rule, so there is no consult-the-table step that can be skipped. The cost is ~25 lines of markdown across the rule set; the saving is the indirection that has historically been a source of rule-application drift in similar gating systems.

- **Use two-space separation between the heading text and the tag.** Single-space looks like part of the title; a newline tag (`> **Profile:** prose`) doubles the line count per rule and is easy to skim past. Two spaces keep the tag visually distinct without breaking the heading parse.

- **Default each rule to `[profile: both]` and enumerate the carve-outs.** Make the exceptions auditable, not implicit. In humanizer's case, 18 rules carry `both` and 7 carry `prose`-only (rules 9, 10, 13, 14, 15, 16, 25); the `## PERSONALITY AND SOUL` section is tagged at the H2 root because the entire section opts out for skill-file inputs. Reserve the skill-file-only value as a valid tag for forward compatibility even when no current rule uses it — the symmetry documents the design intent.

- **Tag wholesale opt-out sections at the section root, not on every subsection.** When an entire section is profile-gated, a tag on the H2 heading suffices. Pushing the tag down to every `###` subsection signals false granularity (as if some subsections might keep firing) and triples the maintenance surface.

- **For "applied/skipped" rule-count reporting, count per-rule not per-instance.** A rule tagged out-of-profile and not evaluated counts as one skip per file; rules evaluated and producing no rewrite count as "applied with no rewrites," not as skips. Per-rule counting is cheaper to compute and more useful to the operator — it answers *"did the gating fire?"* rather than *"how many phrases matched?"*

- **Place the applied-profile summary block immediately after the classification summary block.** The two blocks read as classification → consequence in one place. Pin the indent and arrow style to match the upstream classification block exactly (two-space indent, two spaces around `->`, parenthesized count) so the operator sees one visual pattern, not two.

- **Document expected literal rule-application counts next to the format spec.** A bare `(N applied, M skipped)` placeholder leaves the operator no way to detect tag drift. Pinning the expected counts (e.g., `prose → 25 applied, 0 skipped` and `skill-file → 18 applied, 7 skipped` in the current rule set) gives the operator a one-line sanity check and surfaces tag drift the first time the run output disagrees.

For carve-outs *inside* a rule whose general guidance is right but regresses on specific phrases:

- **Keep the carve-out in the rule's own body, not in a top-level allow-list section.** Rule 22's precision-word allow-list (`unchanged`, `exactly`, `at least`, `at most`, `only`, `solely`, and the RFC 2119 keywords) is meaningful only in the context of the rule that would otherwise strip those words. Splitting it into a top-level section would force a reader of Rule 22 to follow a pointer to know what the rule actually does.

- **State that the carve-out narrows the rule, not replaces it.** Rule 22's canonical filler rewrites (`"in order to"` → `"to"`, `"Due to the fact that"` → `"Because"`, etc.) remain in effect; the allow-list only blocks rewrites that would *delete or substitute a listed word*. Stating this explicitly prevents the carve-out from being read as a general license to skip the rule.

- **The precision-word allow-list applies under all profiles.** The precision claim a word carries does not depend on the audience. A `prose` invocation that strips `unchanged` from spec-adjacent text is just as much a regression as a `skill-file` one.

- **Quote the worked-example regression in the rule body.** Stating *"continues to work unchanged when the file is later assembled stays as written — the word `unchanged` is preserved"* with attribution to the PR/commit that produced the regression turns the rule into its own regression test target. A future reader who is tempted to relax the allow-list sees the specific failure that motivated it.

For within-file profile switches when a single audience classification is too coarse:

- **Treat embedded example output as a different audience than the surrounding instruction prose.** When a `skill-file`-classified input contains fenced code blocks, `Before:`/`After:` contrast pairs, or labeled `Example:` sections demonstrating desired output, route those regions through the `prose` profile. The agent will mimic the register of examples it sees: if a skill teaches *"good output looks like this"* and the example is AI-slop, the agent's output will be AI-slop. The skill prose can be uniform and impersonal; the modeled-output examples must read like the human-grade output the agent is supposed to produce.

- **Keep the file's classification label stable across the example-region switch.** The within-file rule-set switch is local to the rule-evaluation loop; the file keeps its `skill-file` label in the classification summary. Reclassifying the file would corrupt the upstream classifier's auditable per-file decision.

- **Bias the example-region detector conservatively.** Cover the obvious shapes (fenced code blocks, `**Before:**`/`**After:**` blockquotes, `**Example:**` and `Example`/`Worked example` headings) and explicitly state *"when in doubt, treat a region as instruction prose under the file's primary profile."* The failure mode of *not* switching to prose inside an example region is the documented worked-example regression; the failure mode of switching unnecessarily is at worst a no-op when the surrounding skill prose is already in the `both`-tagged rule space.

- **Resolve nested example regions by outer-region first-match-wins.** A fenced code block inside a `Before:` blockquote inherits the outer region's profile selection. The alternative (innermost-wins) requires per-token region accounting and produces a more confusing operator model.

## Why this matters

A single prose-oriented rule set cannot simultaneously serve a press-release rewrite and a `SKILL.md` edit; the cost of conflating them is borne by whichever audience the next humanizer run happens to be aimed at. Issue #94 made per-file routing possible by recording the audience label; this work made per-file routing *consequential* by giving the rule body a way to consume it.

Three structural choices in the design do most of the work:

1. **In-heading tags are read at evaluation time.** Tagging in a separate table works in a runtime-coded system where the rule engine consults the table programmatically, but a prompt-only skill executes by having the model read the rule text. The tag must travel with the rule it gates. The pattern generalizes — any prompt-only skill whose rules need conditional gating has the same constraint.

2. **Local carve-outs inside a rule keep the rule auditable.** A general rule with a precision-word carve-out is easier to read and easier to extend than two near-duplicate rules (`Rule 22a: filler phrases, prose profile` / `Rule 22b: filler phrases, skill-file profile, with allow-list`). Splitting the rule for a small enumerable carve-out is a YAGNI-violation by structure: the carve-out is small enough that documenting it inside the rule is cheaper than maintaining two rule definitions in sync.

3. **The example-region exception is rule-application scope, not classification scope.** Reclassifying a file when its content contains an example would muddle the auditable per-file decision the classifier produces. Routing example regions through a different rule set inside an otherwise stably-classified file keeps the classification summary trustworthy and the rule application correct. The principle generalizes: when a within-file carve-out is needed, prefer to scope the carve-out at the rule-application layer, not the classification layer.

The pattern also illustrates "do as I say, not as I do" — the surrounding skill prose can be uniform and impersonal (because that is what skill consumers need), but the modeled-output examples must read like the human-grade output the agent is supposed to produce. Conflating those two registers is the failure mode that motivated the example-region exception in the first place.

## When to apply

- A prompt-only skill with a body of named rules needs to apply different subsets to different audiences in one invocation.
- An audience classifier already exists (per file or per invocation) and is recording the label; the open work is how the rule body uses it.
- A specific rule's general guidance is correct but produces a known regression on a small, enumerable set of phrases. Prefer an in-rule allow-list to splitting the rule.
- The skill's body contains embedded example output (fenced code blocks, `Before:`/`After:` contrast pairs, labeled `Example:` sections) that should not adopt the same profile as the instruction prose around them.
- An expected literal applied/skipped count can be pinned in the format spec so operators can detect tag drift in one glance.

Do not apply this pattern when:

- The rule set is small enough that audience routing can be expressed by splitting the skill in two. Two skills with disjoint rule sets are easier to reason about than one skill with profile-gated rules — the threshold for "small enough" is roughly 5-7 rules with disjoint tagging.
- The audience label changes mid-file in ways the detector cannot enumerate. A heuristic example-region detector covers the common shapes; arbitrary mid-file audience switching is a different problem and likely indicates the file should be split.

## Examples

The humanizer per-rule profile tags live in `plugins/humanizer/skills/humanizer/SKILL.md`. Each numbered rule heading carries `[profile: both]`, `[profile: prose]`, or (currently unused) `[profile: skill-file]`:

```markdown
### 8. Avoidance of "is"/"are" (Copula Avoidance)  [profile: both]
### 13. Em Dash Overuse  [profile: prose]
### 22. Filler Phrases  [profile: both]
```

The `## PERSONALITY AND SOUL` section opts out at the H2 root:

```markdown
## PERSONALITY AND SOUL  [profile: prose]
```

Rule 22's precision-word allow-list sits inside the rule body, with the worked-example regression quoted:

```markdown
**Precision-word allow-list:** Do not strip or substitute these words when applying
the filler-phrase rewrites above. They carry specification-grade precision that the
rewrite would otherwise erase.

- `unchanged`, `exactly`, `at least`, `at most`, `only`, `solely`
- RFC 2119 keywords: `MUST`, `MUST NOT`, `SHOULD`, `SHOULD NOT`, `MAY`, `REQUIRED`,
  `SHALL`, `SHALL NOT`, `RECOMMENDED`, `OPTIONAL` (and their lowercase forms when
  they appear in spec-adjacent prose)

Worked example: *"continues to work unchanged when the file is later assembled"*
stays as written — the word `unchanged` is preserved. (Regression target:
`quadralay/markdown-plus-plus` PR #107 commit `6fda523`, where a filler-phrase
rewrite stripped `unchanged` and converted a normative claim into an ambiguous one.)
```

The `## Example-region exception` section between `## Audience classification` and `## Your Task` documents the within-file rule-set switch and the conservative detection bias. The applied-profile summary format and its pinned expected literal counts (`prose → 25 applied, 0 skipped`; `skill-file → 18 applied, 7 skipped`) sit in the `### Applied-profile summary format` subsection alongside the existing classification summary spec, so the operator reads classification format and applied-profile format in one place.

The regression fixture at `plugins/humanizer/skills/humanizer/tests/profiles/precision-word-allow-list/` reproduces the PR #107 worked-example phrase. The fixture pairs `input.md` (the phrase as input) with `input.md.expected` (a single token `unchanged-preserved`) — the same shape issue #94's `tests/auto-detection/` corpus established.

A reviewer noted that hardcoded literal counts (25/0, 18/7) are a maintenance liability with no automated enforcement, but the decision was kept: the counts let the operator detect tag drift on the first surprised reading of a run summary, which is the only sanity check available without a runtime test harness. Removing the counts would also remove the only signal an operator has that a rule's tag changed without anyone noticing.

## Related

- Issue #95 (this work — dual-audience rule profiles consuming the classifier)
- Issue #94 (humanizer classifier plumbing — produced the per-file label this work consumes)
- Issue #93 (humanizer plugin vendoring — landed the base SKILL.md modified across all three issues)
- `docs/solutions/design-patterns/in-skill-heuristic-classifier-2026-05-22.md` — the classifier design pattern; this doc is its consumer counterpart
- `docs/solutions/architecture-patterns/format-spec-vs-integration-skill-separation-2026-05-09.md` — related skill-architecture decision
- `plugins/humanizer/skills/humanizer/SKILL.md` — the per-rule tags, allow-list, example-region exception, and applied-profile summary spec
- `plugins/humanizer/skills/humanizer/tests/profiles/precision-word-allow-list/` — the regression fixture
- `quadralay/markdown-plus-plus` PR #107 commit `6fda523` — the worked-example evidence
