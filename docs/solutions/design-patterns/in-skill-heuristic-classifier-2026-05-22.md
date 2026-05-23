---
title: Embed a first-match-wins heuristic classifier inside a prompt-only skill before its alternate profile lands
date: 2026-05-22
category: design-patterns
module: humanizer-skill
problem_type: design_pattern
component: tooling
severity: medium
applies_when:
  - A prompt-only skill needs to apply different rule profiles to different input files in one invocation
  - Operator-flagging each file's audience does not scale (workflow automation passes mixed PR diffs)
  - The skill has no runtime code, so the classifier itself must be prose instructions the model executes
  - The alternate rule profile is tracked in a companion issue and may merge before or after the classifier
  - At least two of the available signals (filename, content shape, path, sibling filesystem) overlap on real inputs
related_components:
  - humanizer
  - skill-architecture
  - tooling
tags:
  - skill-design
  - classifier
  - first-match-wins
  - heuristics
  - audience-routing
  - prompt-engineering
  - plumbing-before-consumers
---

# Embed a first-match-wins heuristic classifier inside a prompt-only skill before its alternate profile lands

## Context

The humanizer skill rewrites prose to strip AI-isms. Issue #94 needed it to also handle Claude Code skill manifests (`SKILL.md` files and their companion docs), which want a different rule profile than essay prose. Workflow invocations routinely mix file types in one run: a PR diff might include a `SKILL.md`, a `references/best-practices.md`, and a `CHANGELOG.md`. Asking the operator to flag each file's audience does not scale, so the skill itself has to classify per file.

Three constraints shaped the design:

1. Humanizer is a prompt-only skill. No runtime code is available to host the classifier; the rules have to be model-executable instructions in `SKILL.md`.
2. The alternate (skill-file) rule profile is tracked in a companion issue. The two issues must be parallelizable and merge in any order.
3. Mixed-input runs are the common case, not the edge case, so the classifier has to be per-file, not per-invocation.

## Guidance

When a prompt-only skill needs to discriminate between input types in mixed-input runs, embed a first-match-wins heuristic ladder in `SKILL.md` with these properties:

- **Priority order is explicit and frozen.** Number each heuristic and state the rule "first match wins; later heuristics are not evaluated for that file" once at the top of the ladder. The model reads it as an `if/elif/else` chain, not as a scoring rubric. Without the explicit priority statement, the model is free to weigh heuristics and produce non-reproducible classifications.
- **Each heuristic has a single decisive signal.** Filename literal, YAML frontmatter shape (specific required keys), path-component match, sibling filesystem check. Don't combine signals inside one heuristic; combine them by stacking the heuristics in order.
- **The path-segment heuristic is component-aware, not substring.** Document the normalization the model should perform (replace `\` with `/`, split on `/`, compare path components). Substring matching turns `myskills/foo/bar.md` into a false positive against `skills/`.
- **The sibling-filesystem heuristic is bounded.** A walk-up looking for `SKILL.md` can chase arbitrary depth. Split it into (a) co-located parent and (b) a single-level walk-up only when the immediate parent is one of a small, named whitelist of companion directory names (e.g., `references`, `scripts`, `tests`, `examples`). Names outside the list and depths beyond one fall through.
- **A fallback label is documented.** When no heuristic fires, the file gets the safer default (here, `prose`). Avoid "no classification" states.
- **Add a global override token.** Parse `audience=skill-file|prose|auto` from `$ARGUMENTS`. The override is global to the invocation, not per-file; operators rerun for mixed forcing. Forced classifications carry a `(forced)` suffix in the summary so a reviewer can tell heuristic decisions from operator decisions at a glance.
- **Emit a per-file classification summary.** When file paths are processed, list each file with its resolved label in a fixed block (`Auto-detected audiences:` followed by indented `path -> label` rows). This summary is the only externally observable signal that the classifier ran correctly; it lets the operator verify on first invocation.
- **Land plumbing before consumers.** When the alternate profile is tracked separately, the classifier still runs, records, and reports even while every label routes to the same profile. This decouples the two issues and makes the classifier independently verifiable.

## Why this matters

Heuristics for input typing usually have overlapping false-positive surfaces. In humanizer's case:

- The filename heuristic catches `docs/SKILL.md` (a documentation file that happens to share the name). That is intentional — it is the canonical signal — but it means the override path (`audience=prose`) must be documented for the rare cases where a doc inherits the name without inheriting the role.
- The frontmatter heuristic catches skill manifests under nonstandard filenames.
- The path-segment heuristic catches skill files without the frontmatter signal — companion docs and reference material that don't carry the manifest header.
- The sibling-filesystem heuristic catches vendored layouts (`vendor/<name>/references/api.md`) where the path-segment heuristic fails because the layout omits the `skills/` segment.

If the model is allowed to score these and pick a best fit, the same input file can classify differently across invocations. A frozen priority order makes the decision deterministic without requiring runtime code.

Decoupling plumbing from consumers (this issue lands the classifier; a companion issue lands the alternate profile) means the two issues can be parallelized and merged in either order. The classifier records and reports even when every label routes through the same rules today. The cost is that the classifier runs every invocation while changing nothing about the output, which is a cheap trade for the merge-order flexibility — and the summary block makes it easy to verify the classifier is doing its job once the consumer lands.

## When to apply

- A skill needs per-file routing in one invocation and operator-flagging does not scale.
- The skill is prompt-only and a runtime classifier is not available.
- The decision can be expressed as a small ladder of decisive heuristics, not a probabilistic score.
- The mechanism must be observable to the operator without instrumenting a runtime; a `path -> label` summary block per file is enough.
- The alternate rule profile lives in a separate issue and merge-order needs to be flexible.

## Examples

The humanizer classifier lives in `plugins/humanizer/skills/humanizer/SKILL.md` under the "Audience classification" section. The fixture corpus is at `plugins/humanizer/skills/humanizer/tests/auto-detection/`.

Two recurring design choices in the corpus generalize to any in-skill classifier with a fixture set:

- **Fixtures sitting under a real skill path will trip the path-segment heuristic on themselves.** The outer worktree path `plugins/humanizer/skills/humanizer/` matches heuristic 3 directly, so naively running each fixture through the classifier classifies every fixture as `skill-file` regardless of its content. The corpus `README.md` documents that any future runner must evaluate each fixture's logical path *relative to its own subdirectory*, not the outer worktree path. The alternative — relocating the corpus outside any `skills/` directory — was considered and rejected because tests should sit next to the artifact they test.
- **Each fixture pairs with a single-token `.expected` file.** No test framework, no harness — just `path` and `path.expected`. The runner reads the path, classifies it, compares the token. This keeps fixtures usable by whatever runner the project picks later.

A review pass during implementation surfaced the bounded-walk split. The original heuristic 4 was a single "sibling SKILL.md" rule, written with `references/`, `scripts/`, `tests/`, `examples/` as motivating examples but with no upward walk in the rule itself. That contradiction was caught and the heuristic was split into (a) co-located and (b) one-level companion walk-up bounded by the whitelist of companion-directory names. The lesson: when the motivation for a heuristic implies traversal but the rule text says "no walk," reviewers will find the gap; bound the walk explicitly rather than leaving it implicit.

## Related

- Issue #94 (humanizer skill-file auto-detection plumbing — this work)
- Issue #93 (humanizer plugin vendoring — landed the base `SKILL.md` modified here)
- Companion issue for dual-audience profiles (consumer of this classifier; tracked separately)
- `plugins/humanizer/skills/humanizer/SKILL.md` — the classifier itself
- `plugins/humanizer/skills/humanizer/tests/auto-detection/` — fixture corpus
- `docs/solutions/architecture-patterns/format-spec-vs-integration-skill-separation-2026-05-09.md` — related skill-architecture decision pattern
