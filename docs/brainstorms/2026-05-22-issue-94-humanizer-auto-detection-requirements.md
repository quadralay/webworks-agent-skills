---
date: 2026-05-22
topic: humanizer-skill-file-auto-detection
issue: 94
---

# Humanizer — Skill-File Auto-Detection

## Summary

Add a classifier to the vendored `humanizer` skill that decides, per input file, whether the file is a Claude Code skill artifact (`skill-file`) or general prose (`prose`), and applies the correct rule profile without operator intervention. The classifier runs at invocation time, evaluates four heuristics in priority order plus a fallback, supports an explicit `audience=` override, classifies each file independently when a single invocation mixes skill files and prose, and reports the per-file decision in the humanizer output. This issue delivers the classification plumbing only; the dual-audience profiles that consume the classification land in the companion issue.

---

## Problem Frame

Worker workflows that invoke humanizer routinely pass mixed inputs in a single run — a `SKILL.md` next to a `references/best-practices.md` next to a top-level `CHANGELOG.md`. The current humanizer treats every file the same. Two real consequences follow:

1. **Skill instructions get treated like prose.** Skill files are imperative agent guidance, not narrative writing. Applying "vary your rhythm" / "add soul" / "let some mess in" prose rules to a SKILL.md produces softened, chattier instructions that read less like an authoritative reference and more like a blog post — measurably worse for the agent that has to follow them.
2. **Per-file operator flags do not scale.** A worker workflow that runs humanizer over a PR diff cannot reasonably stop to flag each file's audience by hand. Either the operator pre-classifies the entire diff (wrong — most diffs are mixed), or the operator flags one global mode and accepts misapplication to the other half (also wrong).

The operator's framing on the 2026-05-22 design call: *"I'm in a skill folder of a plugin, therefore I'm a skill and need alternate treatment."* That intuition translates cleanly into filename, frontmatter, and path heuristics that the skill can evaluate without external state.

The companion issue (dual-audience profiles) builds the `skill-file` rule profile that consumes this classification. Both issues build on the vendored humanizer copy delivered in #93. This issue is the plumbing; the companion is the behavior. Until both land, there is no externally visible behavioral change — auto-detection runs but every file gets the prose profile because no other profile exists yet.

---

## Requirements

**Classification function**

- R1. Add a classifier inside the vendored `humanizer` skill that accepts a file path and returns one of `skill-file` or `prose`. The classifier evaluates the heuristics below in priority order; the first match wins.
- R2. **Heuristic 1 — Filename match.** Files literally named `SKILL.md` (case-sensitive) classify as `skill-file`. This is the canonical Claude Code skill manifest filename.
- R3. **Heuristic 2 — YAML frontmatter shape.** Files whose first non-empty content is a `---`-delimited YAML block containing all three of `name:`, `description:`, and `allowed-tools:` keys classify as `skill-file`, regardless of filename. This is the canonical skill manifest header shape; files with this shape are skills even when the filename diverges.
- R4. **Heuristic 3 — Path segment match.** Files whose path contains any of these segments classify as `skill-file`:
  - `/skills/<name>/`
  - `/.claude/skills/`
  - `/.claude/agents/`
  - `/plugins/<name>/skills/<name>/`
- R5. **Heuristic 4 — Sibling `SKILL.md`.** Files in a directory that also contains a `SKILL.md` classify as `skill-file`. This catches `references/`, `scripts/`, `tests/`, and `examples/` companion files under a skill root.
- R6. **Fallback.** Files that match none of the above classify as `prose`.
- R7. When the humanizer is invoked on raw text without a file path (operator pastes content into chat), the classifier returns `prose` by default. The operator can override via the explicit argument (R8).

**Explicit override**

- R8. Operators may override classification at invocation time with a global `audience=` argument:
  - `audience=skill-file` — every file in this invocation uses the skill-file profile.
  - `audience=prose` — every file uses the prose profile.
  - `audience=auto` (default) — each file is classified independently per R1–R7.
- R9. The override is global to the invocation. There is no per-file override in this issue; if mixed forcing is needed, the operator runs humanizer twice.

**Mixed-input handling**

- R10. When a single invocation passes multiple file paths under `audience=auto`, the skill classifies each path independently, processes each under its own profile, and accumulates the per-file decisions for the output summary (R11).

**Reporting**

- R11. After processing, humanizer emits a classification summary listing each input file and its resolved audience, formatted so each file appears on its own line with the path and the `-> skill-file` or `-> prose` decision. The format is illustrated by an example in the skill body; this issue does not pin the exact whitespace layout but does pin the content shape (repo-relative path, arrow, decision token).
- R12. When the operator forces `audience=skill-file` or `audience=prose`, the summary shows the forced decision and labels it as forced (e.g., `-> skill-file (forced)`), so a reader can tell at a glance that auto-detection was not consulted for that file.

**Test corpus**

- R13. Add a fixtures directory at `plugins/humanizer/skills/humanizer/tests/auto-detection/` containing:
  - **Positive fixtures** (must classify as `skill-file`): a copy of a real `SKILL.md`; a `references/<file>.md` sibling-detection case; a path-segment case under `.claude/skills/<name>/`; a file with SKILL.md-shaped frontmatter under an arbitrary filename.
  - **Negative fixtures** (must classify as `prose`): a top-level `README.md`; a `docs/whitepaper.md` with no SKILL.md sibling; a top-level `CHANGELOG.md`; an `.md` file with non-skill frontmatter (e.g., `date:`, `status:` only).
  - **Edge fixtures** (decision documented per case): a `docs/SKILL.md` (filename heuristic wins, even though the path is documentation-shaped); a skill-shaped file at a non-standard path such as `lib/agents/foo.md` (heuristic 3 does not fire — falls through to `prose` unless operator overrides).
- R14. Each fixture is paired with an assertion of its expected classification, in a format the future test runner can consume. This issue does not require executing the tests automatically; it requires the corpus to exist and to be unambiguous.

---

## Acceptance Examples

- AE1. **Covers R1–R7.** Given a humanizer invocation with five mixed file paths under `audience=auto` — a SKILL.md, a sibling `references/foo.md`, a file under `plugins/x/skills/y/`, a top-level `README.md`, and a `CHANGELOG.md` — when the classifier runs, then the three skill-related paths return `skill-file` and the two non-skill paths return `prose`, with no operator interaction required.
- AE2. **Covers R8, R9, R12.** Given `audience=skill-file` is passed with a mixed file list including a `CHANGELOG.md`, when humanizer processes the invocation, then every file (including `CHANGELOG.md`) is processed under the skill-file profile and the summary marks each row as `(forced)`.
- AE3. **Covers R10, R11.** Given a real worker workflow invocation that humanizes a PR diff covering a `SKILL.md`, a `references/best-practices.md`, and a top-level `CHANGELOG.md`, when humanizer completes, then the output ends with a classification summary block where the SKILL.md and references file are tagged `-> skill-file` and the CHANGELOG.md is tagged `-> prose`, and the operator can verify per-file decisions in a single glance.
- AE4. **Covers R13, R14.** Given the test corpus under `plugins/humanizer/skills/humanizer/tests/auto-detection/`, when a reader inspects it, then each fixture has an obvious expected classification and the edge cases include a written one-line note explaining which heuristic won and why.
- AE5. **Covers R3 specifically.** Given a `.md` file with no SKILL.md filename, no sibling SKILL.md, and no skill-path segments, but whose first YAML block contains `name`, `description`, and `allowed-tools`, when classified, then the result is `skill-file` — confirming the frontmatter heuristic fires independently of filename and path.

---

## Success Criteria

- A worker workflow operator can invoke humanizer against a mixed PR diff (SKILL.md + references/*.md + CHANGELOG.md) once, without per-file flags, and get the right profile applied to each file (once the companion profile issue lands) and a per-file decision row in the summary they can review.
- A reader who skims the humanizer SKILL.md after this issue lands can state the four heuristics and their priority order in their own words without re-reading the issue body.
- The auto-detection logic is exercised against the bundled test corpus; every positive fixture classifies as `skill-file`, every negative fixture classifies as `prose`, and every edge case classifies to its documented expected result.
- A misclassification (humanizer applied the wrong profile to a file) is immediately spottable from the summary block — the operator does not need to diff before/after to detect it.

---

## Scope Boundaries

- **Not building the dual-audience rule profiles in this issue.** The skill-file profile (and any retuned prose profile) is the companion issue's surface area. This issue ships the classifier and the reporting; the classifier returns a label that nothing yet acts on.
- **Not adding per-file override syntax.** `audience=` is global to the invocation. A future issue can add `audience.path=...` if a real need surfaces; until then, two invocations cover the rare mixed-force case.
- **Not auto-detecting non-Claude-Code skill formats** (e.g., other agent platforms' manifest shapes). The four heuristics target Claude Code skills as configured in this repository; cross-platform detection is out of scope.
- **Not running the test corpus through an automated test harness in this issue.** Fixtures exist and are inspectable; wiring them to a runner is a follow-up if value emerges.
- **Not classifying based on file extension alone.** A `.txt` file with skill-shaped frontmatter still gets classified by heuristic 2 (frontmatter), not rejected for extension. This keeps the classifier robust against future file-format variation.
- **Not modifying any humanizer rule, vocabulary list, or pattern detector in this issue.** Behavior under the prose profile remains identical to today's vendored copy.
- **Not bumping the plugin version in the brainstorm.** Version bump happens at PR time per `CLAUDE.md` instructions.

---

## Key Decisions

- **Heuristics in priority order, first-match-wins.** Avoids ambiguous double-counting. A `docs/SKILL.md` is classified as a skill-file (heuristic 1 wins) even though it sits under `docs/` — documented explicitly so the operator can override via `audience=prose` if the rare exception arises.
- **Frontmatter shape as a heuristic, not the primary signal.** Frontmatter is a strong signal but slower to evaluate than filename and path (requires opening the file). The filename and path heuristics fire first because they require no I/O beyond the file path itself. Frontmatter is heuristic 2, not heuristic 1, only because filename match is even cheaper.
- **Sibling-SKILL.md as a heuristic, not a deal-breaker.** Reference docs in a skill folder participate in the same instructional surface as the manifest. Classifying them under the skill-file profile is the right default — if the sibling check produces a false positive (rare), the operator can override per-invocation.
- **Default raw-text input to `prose`.** When the operator pastes content directly into chat, there is no path to evaluate. Treating pasted text as `prose` by default matches the most common case (the operator is drafting prose interactively) and gives a clean override path (`audience=skill-file`) for the rare exception.
- **Global override, not per-file.** A per-file override syntax is more flexible but adds CLI surface area that today has no demand behind it. The two-invocation workaround for mixed forcing is acceptable while the feature is new.
- **Report classification decisions in the output.** Without the summary, the operator has no way to verify that auto-detection landed correctly without spot-checking diffs by hand. The summary is a small carrying cost (one line per file) for a real verification surface.
- **Mark forced decisions explicitly in the summary.** Otherwise a reader cannot tell at a glance whether a wrong-looking classification came from a bad heuristic or from an operator override — distinguishing the two cases matters for debugging.
- **Defer companion-issue dependencies in the brainstorm, not the plumbing.** The classifier returns a label even before any consumer exists. This lets the two issues land in any order and lets the plumbing be tested in isolation against the fixture corpus.

---

## Dependencies / Assumptions

- **Depends on #93 (vendoring) for the SKILL.md to modify.** The current `plugins/humanizer/` directory only contains `.claude-plugin/plugin.json`; the `skills/humanizer/SKILL.md` body lands in #93. This issue's implementation cannot merge before #93 because there is no file to edit. Verified at brainstorm time by listing `plugins/humanizer/` (one file).
- **The vendored SKILL.md will follow the canonical Claude Code skill shape** — YAML frontmatter with `name`, `description`, `allowed-tools` — so the classifier's heuristic 2 self-applies (the humanizer's own SKILL.md classifies as `skill-file`). Verified against the cached upstream copy at `~/.claude/plugins/cache/webworks-claude-skills/humanizer/2.3.0/skills/humanizer/SKILL.md`.
- **The companion issue (dual-audience profiles) is implementable in parallel.** Order of merge is flexible. Until the companion lands, the classifier produces labels but every file ends up under the prose profile because no skill-file profile exists. This is acceptable — the plumbing is testable against fixtures even with no consumer.
- **The fixture corpus does not need to be exhaustive.** The corpus exists to make the heuristics' behavior legible and to catch obvious regressions. It is not a coverage matrix for every conceivable filename/path/frontmatter combination.
- **Workers that consume humanizer will pass repo-relative paths**, not absolute. The reporting format pins repo-relative paths. If a worker passes an absolute path, the classifier still works but the summary line becomes less portable.

---

## Outstanding Questions

### Resolvable at planning time

- [Affects R3] [Technical] Decide whether heuristic 3's path-segment match is implemented as literal substring search or as path-component-aware matching (e.g., `pathlib`-style split). Substring search is simpler but matches `/myskills/foo/` accidentally; component-aware matching is more correct. Planning picks the implementation and documents the choice in the skill body.
- [Affects R8, R11] [Technical] Decide how `audience=` is surfaced in the skill's `argument-hint` and where the parser lives. If the skill body relies on the agent reading the `$ARGUMENTS` literal, the planning step writes the small parser inline; if a helper script is introduced, planning weighs that against the existing skill structure (no scripts in `humanizer/` today, per #93's vendored copy).
- [Affects R11, R12] [Editorial] Pin the exact summary block format — header line, indentation, alignment of the arrow column. The issue body shows one shape; planning picks a final form and uses it in both the SKILL.md examples and the fixture expected outputs.
- [Affects R13] [Technical] Decide the on-disk format for fixture expected-classifications: alongside each fixture as a paired `.expected` file, in a single `expectations.yaml` index, or encoded in the filename. Planning picks the option that future test wiring will consume most cleanly.
- [Affects R14] [Editorial] Decide whether the edge-case notes live in a `tests/auto-detection/README.md` or as comments inside the expectations file. Either works; planning picks one.

### Genuinely uncertain — record as assumption

- [Affects R3] [Open] Whether the four path-segment patterns capture every real-world skill location across the team's repos and downstream consumers. The list is empirical, derived from the operator's framing on the 2026-05-22 call. If a downstream consumer organizes skills under `agents/` (no `.claude/` prefix) or a similar variant, heuristic 3 misses them and they fall back to heuristic 4 (sibling SKILL.md) or to `prose`. Recorded as assumption so a future maintainer knows the segment list is empirical, not exhaustive.
- [Affects R5] [Open] Whether sibling-SKILL.md detection should walk up the directory tree (a deeper `references/foo/bar.md` with a SKILL.md two levels up) or only inspect the immediate parent directory. The issue body says "sits in a directory that also contains a SKILL.md," which reads as immediate-parent. Planning picks one and documents it; if real skill layouts nest references more than one level deep, a follow-up tightens this.
- [Affects R10] [Open] Whether the per-file processing loop should short-circuit on the first file that misclassifies (operator review before continuing) or process all files and surface every decision in the summary. Default assumption: process all, summarize at end — matches the issue's reporting design. If a worker needs interactive review, that is a future feature.
