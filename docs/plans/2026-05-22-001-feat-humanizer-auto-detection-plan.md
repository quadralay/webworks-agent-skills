---
title: "feat: Humanizer skill-file auto-detection"
type: feat
status: active
date: 2026-05-22
issue: 94
origin: docs/brainstorms/2026-05-22-issue-94-humanizer-auto-detection-requirements.md
depth: standard
---

# feat: Humanizer skill-file auto-detection

## Summary

Add a classifier to the vendored `humanizer` skill that decides per input file whether it is a Claude Code skill artifact (`skill-file`) or general prose (`prose`), and reports the per-file decision in the humanizer output. The classifier is described in `plugins/humanizer/skills/humanizer/SKILL.md` and exercised against a small fixture corpus in `plugins/humanizer/skills/humanizer/tests/auto-detection/`. This plan delivers the classification plumbing and reporting only — no rule profile changes; behavior under the existing prose profile is unchanged until the companion issue lands.

---

## Problem Frame

Worker workflows that invoke humanizer routinely pass mixed inputs in a single run (a `SKILL.md` next to a `references/best-practices.md` next to a top-level `CHANGELOG.md`). The current vendored humanizer treats every file the same, and asking the operator to pre-flag each file's audience by hand does not scale across a PR-sized diff. The operator's framing — *"I'm in a skill folder of a plugin, therefore I'm a skill and need alternate treatment"* — translates into filename, frontmatter, and path heuristics the classifier can evaluate at invocation time without external state. (See origin: `docs/brainstorms/2026-05-22-issue-94-humanizer-auto-detection-requirements.md`.)

---

## Requirements

Origin requirements R1-R14 and acceptance examples AE1-AE5 are addressed across the implementation units below:

- **R1-R7, AE1, AE5** — classifier algorithm (4 heuristics + fallback, raw-text default) → U1
- **R8, R9, R12, AE2** — explicit `audience=` override and forced-decision labelling → U1
- **R10, R11, AE3** — mixed-input loop and end-of-run summary block → U1
- **R13, R14, AE4** — fixture corpus and per-fixture expected classification → U2
- **Plugin version bump** (project convention from `CLAUDE.md`) → U3

---

## Scope Boundaries

- Not building the dual-audience rule profiles. The `skill-file` profile (and any retuned prose profile) is the companion issue's surface; this plan ships the classifier and the reporting only.
- Not adding per-file override syntax. `audience=` is global to the invocation.
- Not auto-detecting non-Claude-Code skill formats. The four heuristics target Claude Code skills as configured in this repo.
- Not wiring the fixture corpus into an automated test harness. The corpus is inspectable and paired with expected-classification files; a future issue can add a runner if value emerges.
- Not classifying by file extension alone. A `.txt` file with skill-shaped frontmatter still classifies via the frontmatter heuristic.
- Not modifying any humanizer rule, vocabulary list, or pattern detector. Behavior under the prose profile remains identical to today's vendored copy.

### Deferred to Follow-Up Work

- **Dual-audience rule profiles (companion issue).** The classifier returns a label that nothing yet consumes; the companion issue adds the `skill-file` profile that uses the label.
- **Automated test runner for the fixture corpus.** The `.expected` files are designed so a future runner can consume them, but wiring the runner is out of scope here.
- **Walking up the directory tree for sibling-SKILL.md detection.** Heuristic 4 inspects the immediate parent only (see Assumptions). If real skill layouts nest references deeper, a follow-up can extend this.
- **Per-file `audience.path=...` override syntax.** Two invocations cover the rare mixed-force case until real demand surfaces.

---

## Context & Research

### Relevant Code and Patterns

- `plugins/humanizer/skills/humanizer/SKILL.md` — vendored upstream copy (lands in #93). Single-file skill, no scripts directory, no helper modules. Frontmatter shape: `name`, `version`, `description`, `allowed-tools`. The classifier heuristic 2 self-applies — this file classifies as `skill-file`.
- `plugins/humanizer/.claude-plugin/plugin.json` — humanizer plugin manifest, currently version `2.3.0` (vendored from upstream `blader/humanizer`).
- `plugins/webworks-agent-skills/skills/claude-md-audit/SKILL.md` — recent example of a single-file, prose-only skill in this repo, including authoritative-skill description style and behavioral rules.
- `.claude-plugin/marketplace.json` — top-level marketplace manifest; lists `humanizer` as a sibling plugin under `./plugins/humanizer`. No per-plugin version in marketplace.json (each plugin owns its own version in its `.claude-plugin/plugin.json`).
- `scripts/bump-version.sh` — only bumps `plugins/webworks-agent-skills/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`. The humanizer plugin is **not covered** by this script; its version bump is manual (see U3).

### Institutional Learnings

- `docs/solutions/authoritative-skill-patterns.md` — declare authority and trigger phrases in skill `description` fields so the skill is actually invoked. The auto-detection feature is described inside `SKILL.md`; the skill's existing `description` already triggers on humanizer requests, so no description rewrite is required.
- `docs/solutions/best-practices/agent-md-audit-reduction-2026-05-19.md` — single-file skills with embedded methodology are the established pattern in this repo. The classifier methodology belongs inside the existing `SKILL.md`, not in a separate references file.

### External References

- Cached upstream humanizer copy at `~/.claude/plugins/cache/webworks-claude-skills/humanizer/2.3.0/skills/humanizer/SKILL.md` confirms the canonical frontmatter shape (`name`, `description`, `allowed-tools`) the classifier's heuristic 2 detects.

---

## Key Technical Decisions

- **Path-component-aware matching for heuristic 3.** Split the path on `/` and look for literal path components (`skills`, `.claude`, `agents`, `plugins`) by position, not by substring. Substring matching would falsely classify `/myskills/foo/bar.md` as `skill-file`; component matching correctly rejects it. The classifier explicitly normalizes path separators before splitting so Windows-style `\` paths from worker workflows behave identically.
- **No new script files; classifier logic lives in `SKILL.md`.** The vendored humanizer is prose-only — no scripts, no helper modules. Adding a runner script for this plumbing would diverge from the upstream shape and from how the other single-file skills in this repo are structured (`claude-md-audit`, `markdown-integration`). The skill body describes the algorithm so the invoking agent applies it directly from `$ARGUMENTS` and file reads.
- **Description-only triggering remains unchanged.** The existing `description` in `plugins/humanizer/skills/humanizer/SKILL.md` already triggers on humanizer requests. Adding auto-detection methodology inside the body does not require a `description` rewrite. (Per `docs/solutions/authoritative-skill-patterns.md`, the description is for invocation triggering, not feature enumeration.)
- **Heuristic order is priority order, first-match-wins.** Filename (heuristic 1) is cheapest, then frontmatter (heuristic 2) which requires opening the file, then path-segment (heuristic 3), then sibling-SKILL.md (heuristic 4). The order is also semantic: filename match wins over path so `docs/SKILL.md` classifies as `skill-file` even though the path looks documentation-shaped, and the operator can `audience=prose` override for that rare case.
- **Heuristic 4 inspects the immediate parent directory only.** No upward tree walk. This matches the brainstorm's "sits in a directory that also contains a `SKILL.md`" wording and avoids ambiguity in nested layouts. If a real layout nests references deeper, a follow-up can tighten.
- **Raw-text invocations default to `prose`.** When the operator pastes text directly with no path, there is no signal to evaluate. Default to `prose` (the common case) and rely on `audience=skill-file` for the rare exception.

---

## Assumptions

*This plan was authored without synchronous user confirmation. The items below are agent inferences that fill gaps in the input — un-validated bets that should be reviewed before implementation proceeds.*

- **Summary block format pinned as `<path>  -> <decision>` (two-space indent, one space around the arrow, `(forced)` suffix when overridden).** No column alignment — paths vary too much, and alignment would require a second pass. Example shape:

  ```
  Auto-detected audiences:
    plugins/humanizer/skills/humanizer/SKILL.md  -> skill-file
    plugins/humanizer/skills/humanizer/references/best-practices.md  -> skill-file
    CHANGELOG.md  -> prose
  ```

  When `audience=skill-file` or `audience=prose` is forced globally, each row appends `(forced)`: `CHANGELOG.md  -> skill-file (forced)`. The same shape is reused in fixture documentation under U2 so the format is exercised in two places.

- **Fixture expected-classifications are stored as paired `<fixture>.expected` files containing a single token (`skill-file` or `prose`).** Most legible — a reader scanning the directory sees the pairing immediately, and a future test runner can read the paired file without parsing YAML. Alternatives considered: a single `expectations.yaml` index (less legible), filename encoding (brittle for fixtures whose names matter to a heuristic, e.g., `SKILL.md`).

- **Edge-case prose notes live in `plugins/humanizer/skills/humanizer/tests/auto-detection/README.md`.** README.md is the canonical place for human-readable test corpus documentation; one paragraph per edge case explains which heuristic won and why.

- **Heuristic 3 path-segment list (`/skills/<name>/`, `/.claude/skills/`, `/.claude/agents/`, `/plugins/<name>/skills/<name>/`) is empirical, not exhaustive.** Derived from the operator's framing on the 2026-05-22 call. Downstream consumers that organize skills under non-standard paths (e.g., `agents/` with no `.claude/` prefix, `lib/agents/foo.md`) fall through heuristic 3 to heuristic 4 (sibling SKILL.md) or to `prose`. Documented in the SKILL.md so future maintainers know the list is empirical.

- **Per-file processing loop processes all files and emits a summary at the end** (no short-circuit on first misclassification). Matches the brainstorm's reporting design. If a worker needs interactive review, a future feature can add it.

- **Humanizer plugin version bump from 2.3.0 to 2.4.0 (minor — new feature).** Per the project versioning rule in `CLAUDE.md` ("minor: new skills, new features"). Bump is manual because `scripts/bump-version.sh` only targets `webworks-agent-skills`; the humanizer plugin is a sibling with its own `plugin.json`. The top-level `.claude-plugin/marketplace.json` has no per-plugin version field for humanizer, so no marketplace edit is needed for this issue — the marketplace tracks the `webworks-agent-skills` plugin's version, not humanizer's.

---

## Open Questions

### Resolved During Planning

- **Q (from origin Outstanding Questions, R3):** Substring vs path-component-aware matching for heuristic 3 → component-aware. See Key Technical Decisions.
- **Q (from origin, R8/R11):** Where the `audience=` parser lives → inline in the skill body, no helper script. See Key Technical Decisions.
- **Q (from origin, R11/R12):** Exact summary block format → pinned in Assumptions and exercised by U2 fixtures.
- **Q (from origin, R13):** Fixture on-disk format → paired `.expected` files, one token per file. See Assumptions.
- **Q (from origin, R14):** Edge-case notes location → `tests/auto-detection/README.md`. See Assumptions.

### Deferred to Implementation

- **Tie-breaking when a fixture matches multiple heuristics.** First-match-wins by priority order is the rule. The fixture corpus deliberately exercises one heuristic per fixture so this does not surface during implementation; if a downstream user constructs a fixture that hits both heuristic 1 and heuristic 3 (e.g., `plugins/foo/skills/foo/SKILL.md`), the priority order resolves it. Implementation just needs to follow the algorithm as written.

---

## Output Structure

```
plugins/humanizer/skills/humanizer/
  SKILL.md                                   # modified (U1)
  tests/
    auto-detection/                          # new (U2)
      README.md                              # edge-case notes
      positive-skill-md.md                   # heuristic 1
      positive-skill-md.md.expected
      positive-frontmatter-shape.md          # heuristic 2 (arbitrary filename)
      positive-frontmatter-shape.md.expected
      positive-path-segment/
        .claude/skills/example/example.md    # heuristic 3
        .claude/skills/example/example.md.expected
      positive-sibling/
        SKILL.md                             # the sibling
        references/foo.md                    # heuristic 4
        references/foo.md.expected
      negative-readme.md                     # fallback -> prose
      negative-readme.md.expected
      negative-whitepaper.md                 # fallback -> prose
      negative-whitepaper.md.expected
      negative-changelog.md                  # fallback -> prose
      negative-changelog.md.expected
      negative-non-skill-frontmatter.md      # YAML but not skill shape -> prose
      negative-non-skill-frontmatter.md.expected
      edge-docs-skill-md/
        docs/SKILL.md                        # filename heuristic wins
        docs/SKILL.md.expected
      edge-non-standard-path/
        lib/agents/foo.md                    # heuristic 3 misses -> prose
        lib/agents/foo.md.expected
```

The tree is a scope declaration; the implementer may flatten subdirectories if it keeps fixture intent legible. The per-unit `**Files:**` sections remain authoritative.

---

## Implementation Units

### U1. Add classifier, override, and summary to humanizer `SKILL.md`

**Goal:** Embed the classification algorithm, the `audience=` override syntax, the per-file mixed-input loop, and the end-of-run summary format into the humanizer skill body so an invoking agent can classify each input file independently and report decisions back to the operator.

**Requirements:** R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11, R12 (covers AE1, AE2, AE3, AE5)

**Dependencies:** Depends on #93 (vendoring) landing first — there is no `SKILL.md` to edit until that PR merges. The two issues are implementable in parallel but U1 cannot merge before #93.

**Files:**
- Modify: `plugins/humanizer/skills/humanizer/SKILL.md`

**Approach:**

Add a top-level section to the humanizer `SKILL.md` (placement: before the existing "Your Task" section, so the classifier runs before any rewriting) covering:

1. **Audience classification — when this runs.** One paragraph explaining that the classifier runs on every input path before any humanizing rules apply, and that its output (`skill-file` or `prose`) selects which profile is used. Note that until the companion issue lands, only the `prose` profile exists, so all files end up under the same rules — the classifier still records and reports its decision so misclassifications are visible.
2. **The four heuristics in priority order, first-match-wins.** Enumerated as a numbered list mirroring the brainstorm's R2-R5, each with a one-line rationale and a worked example. Explicitly call out the path-component-aware matching rule for heuristic 3 (split on `/`, normalize `\` to `/` first, then match path components by position, not substring) so the agent applying the classifier does not accidentally substring-match.
3. **Fallback.** One sentence: no heuristic matched → `prose`.
4. **Raw-text input default.** One sentence: no path → `prose` by default; operator override via `audience=` is the escape hatch.
5. **The `audience=` argument.** Document the three values (`auto`, `skill-file`, `prose`), state that the argument is global to the invocation, and show how to extract it from `$ARGUMENTS` inline (no helper script).
6. **Per-file processing loop.** Five-step recipe for the agent: (a) resolve the file list from the invocation, (b) for each file, run the heuristics and record the decision, (c) process each file under its own profile, (d) accumulate the decisions, (e) emit the summary block at the end.
7. **Summary block format.** Show the pinned format (see Assumptions) as a code block with two example lines — one auto, one forced. Make explicit that forced rows append `(forced)` so a reader can spot operator overrides at a glance.

Mention up front that this section adds *classification plumbing only* — the rules and rewriting passes below remain unchanged in this issue. The companion issue introduces the `skill-file` profile that will diverge from the current rules.

**Patterns to follow:**
- Embedded methodology inside a single `SKILL.md`, no helper scripts — see `plugins/webworks-agent-skills/skills/claude-md-audit/SKILL.md` for the in-body methodology pattern, and the cached upstream copy `~/.claude/plugins/cache/webworks-claude-skills/humanizer/2.3.0/skills/humanizer/SKILL.md` for the humanizer's own existing voice and section ordering.
- Frontmatter shape — leave the existing `name`, `version`, `description`, `allowed-tools` block intact (do not rename keys or reorder), but the `version` field's bump is U3's responsibility.

**Test scenarios:**

Test expectation: implementation verification is by reading the modified `SKILL.md` against the requirements traceability and by exercising the classifier against the U2 fixture corpus. The U2 fixtures serve as the test cases for this unit; U1 does not introduce its own test files.

Manual verification scenarios for the implementer:

- *Covers AE1.* Reading the algorithm section, an agent given the five mixed paths from AE1 can walk through the heuristics and produce the documented per-file decisions without re-reading the brainstorm.
- *Covers AE2.* The `audience=` documentation makes clear that forcing `audience=skill-file` overrides every file regardless of detection, and the summary section shows the `(forced)` suffix that distinguishes a forced row from an auto-detected row.
- *Covers AE3.* The mixed-input loop and summary section together describe an end-to-end run on a SKILL.md + references/best-practices.md + CHANGELOG.md that emits the documented summary block.
- *Covers AE5.* The frontmatter heuristic (heuristic 2) is described independently of filename, with a worked example of an arbitrary-filename file whose frontmatter contains `name`, `description`, and `allowed-tools`.

**Verification:**

- The modified `SKILL.md` parses as valid YAML frontmatter + markdown.
- The four heuristics, fallback, raw-text default, `audience=` argument, per-file loop, and summary format are all present and cross-referenced against the brainstorm's R1-R12.
- The summary block example in the `SKILL.md` body matches byte-for-byte the format used in the U2 fixtures' documentation.
- The skill's existing `description` field is unchanged (trigger surface preserved).
- The skill's existing rules and rewriting sections are unchanged below the new classifier section (scope boundary on rule changes preserved).

---

### U2. Add fixture corpus and per-fixture expected classifications

**Goal:** Provide a small, inspectable test corpus under `plugins/humanizer/skills/humanizer/tests/auto-detection/` covering all four positive heuristics, four negative cases, and the two documented edge cases, with each fixture paired with a `.expected` file containing the expected classification.

**Requirements:** R13, R14 (covers AE4)

**Dependencies:** U1 (the algorithm has to be specified before fixtures can be authored against it).

**Files:**
- Create: the directory tree shown in **Output Structure** above. Specifically, ten fixtures + ten paired `.expected` files + one `README.md`.

**Approach:**

- **Positive fixtures (4).** One per heuristic:
  - `positive-skill-md.md` — literally named `SKILL.md` (rename the fixture file accordingly in the implementation) → heuristic 1.
  - `positive-frontmatter-shape.md` — arbitrary filename with frontmatter containing `name`, `description`, `allowed-tools` → heuristic 2.
  - `positive-path-segment/.claude/skills/example/example.md` — path-segment match → heuristic 3.
  - `positive-sibling/references/foo.md` (sibling to `positive-sibling/SKILL.md`) → heuristic 4.
- **Negative fixtures (4).** Top-level `README.md`-style file, a `docs/whitepaper.md`-style file with no sibling SKILL.md, a top-level `CHANGELOG.md`-style file, and a `.md` file with non-skill frontmatter (e.g., `date:`, `status:` only). All classify as `prose`.
- **Edge fixtures (2):**
  - `edge-docs-skill-md/docs/SKILL.md` — filename heuristic wins even though path looks documentation-shaped. `.expected` = `skill-file`. Operator can override via `audience=prose` if the rare exception arises.
  - `edge-non-standard-path/lib/agents/foo.md` — skill-shaped path that is not in the heuristic 3 segment list. No sibling SKILL.md, no skill frontmatter. `.expected` = `prose`.
- **Paired `.expected` files.** Each fixture file gets a sibling `<fixture>.expected` containing exactly one line: `skill-file` or `prose`. No trailing whitespace, no header, no YAML — single-token format is what the future test runner will consume.
- **Edge-case `README.md`.** One paragraph per edge case explaining which heuristic won (or failed to fire) and why, so a reader skimming the corpus understands the documented behavior without re-deriving it from the algorithm.

Fixture content can be minimal — a couple of paragraphs of placeholder prose. The classifier evaluates path and frontmatter, not body content (except for non-skill-frontmatter fixtures, where the frontmatter is what's being tested).

**Patterns to follow:**
- Fixture directory layout — see `plugins/webworks-agent-skills/skills/automap/tests/fixtures/` for the existing repo convention of one fixture per subdirectory with self-contained inputs. The auto-detection fixtures follow the same shape (subdirectories where the path matters, flat files where only the filename or frontmatter matters).

**Test scenarios:**

Test expectation: none — these fixtures *are* the test cases for U1. The plan does not wire them into an automated runner (see Scope Boundaries). Verification is by inspection.

Manual verification scenarios for the implementer:

- *Covers AE4.* A reader inspecting the corpus can, for each fixture, name which heuristic governs and why, supported by the paired `.expected` file and the `README.md` notes on the two edge cases.
- Cross-check that for each of the four positive fixtures, exactly one heuristic from R2-R5 explains the `skill-file` classification.
- Cross-check that for each of the four negative fixtures, no heuristic from R2-R5 fires.

**Verification:**

- All ten fixture files and ten `.expected` files are present.
- Each `.expected` file contains exactly one of `skill-file` or `prose` on a single line.
- The `README.md` documents both edge cases and references the heuristic each one fires (or fails to fire).
- The fixtures live under `plugins/humanizer/skills/humanizer/tests/auto-detection/` (not at the repo root) so they ship with the skill.

---

### U3. Bump humanizer plugin version to 2.4.0

**Goal:** Apply the project's required version bump so the new feature ships under a new version of the humanizer plugin, per `CLAUDE.md` ("minor: new skills, new features").

**Requirements:** Project convention (not an origin requirement, but mandated by repo `CLAUDE.md`).

**Dependencies:** U1, U2 (the new feature must exist before the version is bumped to ship it).

**Files:**
- Modify: `plugins/humanizer/.claude-plugin/plugin.json` — change `"version": "2.3.0"` to `"version": "2.4.0"`.

**Approach:**

Edit the single `version` field in `plugins/humanizer/.claude-plugin/plugin.json`. Do not modify other fields (name, description, author, etc.). Do not touch `.claude-plugin/marketplace.json` — the top-level marketplace.json has no per-plugin version field for the humanizer plugin (verified at plan time). Do not run `scripts/bump-version.sh` — that script only handles `webworks-agent-skills`.

**Patterns to follow:**
- Manual single-field version bump — same shape as if `bump-version.sh` had run, but applied by hand because the humanizer is outside the script's coverage.

**Test scenarios:**

Test expectation: none — pure version-string change.

Manual verification scenarios for the implementer:

- After the edit, `jq -r '.version' plugins/humanizer/.claude-plugin/plugin.json` returns `2.4.0`.
- No other field in `plugin.json` changes.
- `.claude-plugin/marketplace.json` is not modified by this unit.

**Verification:**

- `plugins/humanizer/.claude-plugin/plugin.json` shows `"version": "2.4.0"`.
- `git diff` for this unit touches exactly one file with exactly one line changed.

---

## Sources & References

- **Origin requirements:** `docs/brainstorms/2026-05-22-issue-94-humanizer-auto-detection-requirements.md`
- **Companion issue context:** #93 (vendoring — must merge first) and the companion dual-audience profiles issue (consumes the classification labels).
- **Cached upstream skill copy:** `~/.claude/plugins/cache/webworks-claude-skills/humanizer/2.3.0/skills/humanizer/SKILL.md` — reference for the existing humanizer voice, section ordering, and frontmatter shape that the post-#93 vendored copy will mirror.
- **Repo convention sources:** `CLAUDE.md` (version bump policy), `scripts/bump-version.sh` (scope: webworks-agent-skills only), `docs/solutions/authoritative-skill-patterns.md` (skill description triggering), `docs/solutions/best-practices/agent-md-audit-reduction-2026-05-19.md` (single-file skill pattern).
