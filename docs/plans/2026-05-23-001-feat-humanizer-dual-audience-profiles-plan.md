---
title: "feat: Humanizer dual-audience rule profiles"
type: feat
status: active
date: 2026-05-23
issue: 95
origin: docs/brainstorms/2026-05-23-issue-95-dual-audience-humanizer-profiles-requirements.md
depth: standard
---

# feat: Humanizer dual-audience rule profiles

## Summary

Add two named rule profiles — `skill-file` and `prose` — to the vendored `humanizer` skill so the per-file audience label recorded by issue #94's classifier actually selects which rules fire. Tag every rule section header in `plugins/humanizer/skills/humanizer/SKILL.md` with `[profile: both]`, `[profile: prose]`, or `[profile: skill-file]`; tag the entire `## PERSONALITY AND SOUL` section as `[profile: prose]`; add a precision-word allow-list to Rule 22 that preserves spec-grade words even under filler-phrase rewrites; gate the rule-evaluation loop on the per-file profile; route fenced code blocks and `Before:`/`After:` example regions inside `skill-file`-classified inputs back to the `prose` rule set; and add an `Applied profiles:` reporting block that sits adjacent to issue #94's existing `Auto-detected audiences:` block. Ship a single regression fixture exercising the worked-example diff from `quadralay/markdown-plus-plus` PR #107 commit `6fda523` so the precision-word `unchanged` survives the skill-file profile.

---

## Problem Frame

Issue #94 (merged 2026-05-22) added the audience classifier to `plugins/humanizer/skills/humanizer/SKILL.md`. The skill records `skill-file` vs `prose` per file and reports the decision in an `Auto-detected audiences:` block, but the body of the skill still applies a single prose-oriented rule set to every file — the SKILL.md explicitly notes that *"until the companion dual-audience profile feature lands, every file ends up under the prose profile defined below."* This plan is that companion work.

The motivating evidence is a humanizer pass against `plugins/markdown-plus-plus/skills/markdown-plus-plus/references/best-practices.md` in the `quadralay/markdown-plus-plus` repo (PR #107, commit `6fda523`) that produced roughly two genuine improvements per minor regression. The improvements clustered on rules targeting vagueness, inflated language, and anthropomorphization. The regressions clustered on rules targeting punctuation density, structural parallelism, and rhythm variation — patterns that are noise to a prose reader but load-bearing structure for an agent reading a skill.

Two concrete failure modes from that pass anchor this plan:

1. Rule 22 (filler phrases) rewrote *"continues to work unchanged when the file is later assembled"* to *"keeps working when the file is later assembled,"* stripping the word `unchanged`. In specification-adjacent prose, `unchanged` is doing real work — it is the assertion that the file's content is not modified between two pipeline stages. Filler-phrase rewriting that does not respect a small allow-list of precision words turns a normative claim into an ambiguous one.
2. The `## PERSONALITY AND SOUL` section recommends patterns ("vary your rhythm," "use 'I' when it fits," "let some mess in") that actively degrade skill-file utility. Skill files want uniform structure, impersonal voice, and confident directives — the opposite of what that section advocates. A single profile cannot simultaneously serve a press-release rewrite and a `SKILL.md` edit; the cost of conflating them is borne by whichever audience the next humanizer run happens to be aimed at.

The classification plumbing exists. The remaining work is per-rule profile tagging, the precision-word carve-out, the example-region exception, the profile-gated rule-evaluation loop, the new reporting block, and a regression fixture. (See origin: `docs/brainstorms/2026-05-23-issue-95-dual-audience-humanizer-profiles-requirements.md`.)

---

## Requirements

Origin requirements R1-R14 and acceptance examples AE1-AE7 are addressed across the implementation units below:

- **R1-R5, AE1** — per-rule profile tagging on every rule section header (rules 1-25) and on the `## PERSONALITY AND SOUL` section → U1
- **R6, R7, AE2, AE3** — precision-word allow-list under Rule 22 (`unchanged`, `exactly`, `at least`, `at most`, `only`, `solely`, RFC 2119 keywords) without disabling the canonical filler rewrites → U1
- **R8, R9, AE4** — example-block exception (fenced code blocks, `Before:`/`After:` constructs, labeled example sections inside `skill-file`-classified inputs apply the prose profile) → U1
- **R10, R11, AE5, AE6** — profile selection in the per-file processing loop; consume the existing classifier label and the existing `audience=` override unchanged → U1
- **R12, R13, AE7** — `Applied profiles:` reporting block emitted adjacent to the existing `Auto-detected audiences:` block, with per-file `(N rules applied, M skipped)` counts → U1
- **R14, AE2** — regression fixture exercising the worked-example precision-word case from PR #107 commit `6fda523` → U2
- **Plugin version bump** (project convention from `CLAUDE.md`) → U3

---

## Scope Boundaries

- Not introducing additional profiles beyond `skill-file` and `prose`. Granularity past two audiences (e.g., a separate `agent-prompt`, `commit-message`, or `release-notes` profile) is deferred until a real use case shows two is insufficient. (Origin scope boundary.)
- Not adding per-file override syntax. Issue #94's `audience=skill-file` / `audience=prose` argument remains global to the invocation; if an operator needs split treatment, they run humanizer twice. (Origin scope boundary.)
- Not modifying the issue #94 heuristics, classifier algorithm, the `audience=` argument grammar, or the `Auto-detected audiences:` summary format. This issue consumes the classification result; it does not change how the result is produced. (Origin scope boundary.)
- Not porting the profile tags, the allow-list, or the example-block exception upstream to `blader/humanizer`. Audience-awareness is out of scope upstream per issue #93's vendoring rationale and is documented as deliberate divergence in `plugins/humanizer/skills/humanizer/UPSTREAM.md`. (Origin scope boundary.)
- Not auditing or rewriting the existing per-rule prose for clarity. The scope is gating which rules fire, not rewriting how they explain themselves. (Origin scope boundary.)
- Not wiring the regression fixture into an automated test runner. The fixture is inspectable and paired with an `.expected` artifact in the shape established by issue #94's `tests/auto-detection/` corpus. A future runner can consume it without rewriting it.
- Not generalizing the precision-word allow-list beyond the brainstorm's enumerated set. Domain-specific compliance vocabularies can be added in place when a real workflow surfaces them; that extension does not change the architecture.

### Deferred to Follow-Up Work

- **A third profile.** If a real workflow surfaces an audience neither `skill-file` nor `prose` serves well, capture it as a separate issue with the worked-example evidence the brainstorm uses for this split.
- **Per-file `audience.path=...` override syntax.** Two invocations cover the rare mixed-force case until real demand surfaces.
- **Automated test runner for the regression fixture.** The `.expected` companion is designed so a future runner can consume it; wiring the runner is out of scope here.
- **Extending the example-block region detector beyond fenced code blocks and `Before:`/`After:` constructs.** Other "labeled example section" shapes (e.g., admonitions, custom callouts) can be added when a real input demonstrates one is missed.

---

## Context & Research

### Relevant Code and Patterns

- `plugins/humanizer/skills/humanizer/SKILL.md` — the file edited by U1. Already carries the issue #94 `## Audience classification` section (lines 24-103), the per-file processing loop (lines 68-80), and the `Auto-detected audiences:` summary format (lines 82-103). The 25 rule sections live at lines 154-460; the `## PERSONALITY AND SOUL` section sits at lines 119-149.
- `plugins/humanizer/.claude-plugin/plugin.json` — humanizer plugin manifest, currently version `2.4.0` (bumped by issue #94). U3 bumps to `2.5.0`.
- `plugins/humanizer/skills/humanizer/tests/auto-detection/` — issue #94's fixture corpus and its `README.md`. Establishes the pattern for in-repo fixtures: subdirectory per fixture when path matters, paired `<fixture>.expected` files containing a single token, README documenting any caveats. U2's regression fixture sits next to this corpus under a sibling `tests/profiles/` directory.
- `plugins/humanizer/skills/humanizer/UPSTREAM.md` — already notes "Dual-audience rule profiles so each rule can be opted in or out per audience" as planned divergence. No edit required by this plan; the divergence is already documented.
- `scripts/bump-version.sh` — only bumps `plugins/webworks-agent-skills/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`. The humanizer plugin is outside the script's coverage; U3 edits its `plugin.json` by hand (same constraint issue #94 hit).
- `.claude-plugin/marketplace.json` — has no per-plugin version field for the humanizer plugin (verified at plan time and reconfirmed against issue #94's planning notes). U3 does not modify it.

### Institutional Learnings

- `docs/solutions/design-patterns/in-skill-heuristic-classifier-2026-05-22.md` — captures the design choices behind the issue #94 classifier. This plan layers profile gating on top of those choices and inherits the same "first-match-wins, priority order, fallback documented, summary block as the externally observable signal" discipline.
- `docs/solutions/authoritative-skill-patterns.md` — declare authority and trigger phrases in skill `description` fields so the skill is invoked. The dual-audience feature is described inside `SKILL.md` body; the skill's existing `description` already triggers on humanizer requests, so no description rewrite is required.
- `docs/solutions/best-practices/agent-md-audit-reduction-2026-05-19.md` — single-file skills with embedded methodology are the established pattern in this repo. The profile tagging and the rule-evaluation loop belong inside the existing `SKILL.md`, not in a separate references file.

### External References

- `quadralay/markdown-plus-plus` PR #107 commit `6fda523` — the worked-example diff. The failing-phrase rewrite (`"continues to work unchanged"` → `"keeps working"`) is the regression test target. The relevant phrase can be vendored into the U2 fixture as a minimal excerpt with attribution; the rewrite-survival assertion does not need the full source file (see Assumptions).

---

## Key Technical Decisions

- **Per-rule tags in the section header, not a separate config table.** The tag appears as `[profile: <value>]` appended to the rule's heading text (e.g., `### 13. Em Dash Overuse  [profile: prose]`). The agent reads the gating at the same moment it reads the rule, so there is no consult-the-table step that can be skipped. The trade-off — repeating the tag once per rule rather than once per file — costs roughly 25 lines of markdown and saves an indirection that has historically been a source of rule-application drift in similar gating systems. (Origin Key Decision.)
- **`both` is the default tag.** Most rules carry `both`; the exceptions (rules 9, 10, 13, 14, 15, 16, 25 → `prose`; and the `## PERSONALITY AND SOUL` section → `prose`) are explicitly enumerated in R3 and R5 so the carve-out is auditable rather than implicit. No rule receives a `skill-file`-only tag; no rule in the current set is helpful only for skill files but actively harmful for prose. The `skill-file` value is documented as a valid tag for symmetry and forward-compatibility, but is not used by any rule in this iteration.
- **Allow-list lives in Rule 22's body, not in a separate section.** The precision words are only meaningful in the context of the rule that would otherwise strip them. Splitting the allow-list into a top-level section would force a reader of Rule 22 to follow a pointer to know what the rule actually does. The allow-list applies under both profiles — the precision claim a word carries does not depend on the audience. (Origin Key Decision.)
- **Rule 22's canonical filler rewrites remain in effect.** The allow-list narrows the rule, not replaces it. "In order to" → "to," "Due to the fact that" → "Because," and the other canonical Before → After pairs in Rule 22 still fire. The allow-list only blocks rewrites that would *delete or substitute a listed word*.
- **Example-region detection switches profile *within* a file, not reclassifies the file.** A skill-file-classified input keeps the `skill-file` label in the `Auto-detected audiences:` block; the example-region detector only selects which rule set fires inside an example region. The classification summary and the applied-profile summary remain stable; the profile-switching logic is local to the rule-evaluation loop. (Origin Key Decision.)
- **Example-region detection is conservative.** Detection covers fenced code blocks (` ``` … ``` `), block-quoted contrast pairs labeled with `Before:` / `After:` (or equivalent labels like `Draft:` / `Final:`, `Before (AI-sounding):` / `After:`), and labeled example sections introduced by a heading or bold-label of the form `**Example:**`. When in doubt, treat a region as instruction prose under the skill-file profile rather than mistakenly switching to prose inside genuine instruction text. False positives are preferable to false negatives because the failure mode of *not* switching to prose inside an example region is the documented worked-example regression; the failure mode of switching unnecessarily is at worst a no-op when the surrounding skill prose is already in the `both`-tagged rule space.
- **"Skipped" rule counts in the applied-profile summary count per-rule, not per-instance.** A rule tagged out-of-profile and not evaluated counts as one skip per file; rules evaluated and producing no rewrite do not count as skips (they count as "applied with no rewrites"). Per-rule counting is cheaper to compute and more useful to the operator (it answers "did the gating fire?" rather than "how many phrases matched?"). Resolves origin Outstanding Question on count semantics.
- **The applied-profile summary appears immediately after the existing `Auto-detected audiences:` block.** The two blocks read as classification → consequence in one place. Per R13.

---

## Assumptions

*This plan was authored without synchronous user confirmation. The items below are agent inferences that fill gaps in the input — un-validated bets that should be reviewed before implementation proceeds.*

- **Tag format `[profile: <value>]` is appended to the existing rule heading with two spaces of separation** (e.g., `### 13. Em Dash Overuse  [profile: prose]`). Two-space separation keeps the tag visually distinct from the rule title without breaking the heading parse. An alternative — putting the tag on the next line as `> **Profile:** prose` — was considered and rejected because it adds a second line per rule and risks being skimmed past. The in-header placement is what R1 specifies and is what the brainstorm shows.

- **The `## PERSONALITY AND SOUL` section carries its tag on the H2 heading itself** (`## PERSONALITY AND SOUL  [profile: prose]`), not on each subsection. The section is opted out wholesale under R5; a single tag at the section root suffices. If a future profile selectively keeps part of the section (e.g., the "Have opinions" guidance under a hypothetical `op-ed` profile), the tag can be moved down to subsection level at that time.

- **Applied-profile summary format pinned as:**

  ```
  Applied profiles:
    plugins/humanizer/skills/humanizer/SKILL.md  -> skill-file (12 rules applied, 8 skipped)
    CHANGELOG.md                                  -> prose (24 rules applied, 0 skipped)
  ```

  Two-space indent, two spaces around `->`, the resolved profile name, a space, then the parenthesized count. No column alignment — paths vary too much, and alignment would require a second pass over all rows. When the example-block exception fires within a file, the counts reflect the rules applied to the *instruction prose* under the file's primary profile; example-region rule applications are not separately counted (counting them would require per-region accounting that does not earn its complexity at the operator level). The summary uses the same indentation and arrow style as issue #94's `Auto-detected audiences:` block for consistency.

- **The 25 rules currently in `SKILL.md` are exhaustive for this issue.** No new rules are added by this plan; only tags are appended. Rule numbering remains stable so external references (institutional learnings, issue comments) continue to resolve. If issue #95 implementation surfaces a missed rule that needs tagging, the implementer adds the tag without renumbering; if it surfaces a rule that needs to be split (e.g., Rule 22 grows into "Rule 22a: filler phrases" and "Rule 22b: precision-word preservation"), that is an explicit out-of-scope decision flagged in the PR rather than a silent rewrite.

- **The example-region detector's "labeled example section" definition.** Recognized labels include `Before:`, `After:`, `Draft:`, `Final:`, `Example:`, `Before (AI-sounding):`, and `Draft rewrite:`, plus the `**Bold:**` and `> Blockquote:` shapes that wrap them in the humanizer's own Full Example section (lines 491-552). Other ad-hoc labels fall through and are treated as instruction prose under the file's primary profile; the conservative-default rule (R9) makes this the safer failure mode.

- **Regression fixture lives at `plugins/humanizer/skills/humanizer/tests/profiles/precision-word-allow-list/`.** Subdirectory keeps the fixture grouped with anything else that exercises profile gating in the future, and parallels the `tests/auto-detection/` directory issue #94 established. The fixture is a minimal excerpt — one paragraph reproducing the failing phrase from `quadralay/markdown-plus-plus` PR #107 commit `6fda523`, with attribution in a comment or sibling `README.md` so the cross-repo reference is not lost. The full source file is not vendored.

- **Regression fixture `.expected` companion is a single-token file containing `unchanged-preserved`** (not a token from the issue #94 corpus's vocabulary). Issue #94's vocabulary (`skill-file` / `prose`) names classifications; this corpus names assertions. A two-vocabulary distinction keeps a future runner from conflating "the classification is X" with "the rewrite preserves Y." If implementation prefers reusing issue #94's token shape, the implementer can substitute a plain pass/fail token instead — the assertion semantics, not the literal token, are what U2 must deliver.

- **Humanizer plugin version bumps from 2.4.0 to 2.5.0 (minor — new feature).** Per the project versioning rule in `CLAUDE.md` ("minor: new skills, new features"). Bump is manual because `scripts/bump-version.sh` only targets `webworks-agent-skills`; the humanizer plugin is a sibling with its own `plugin.json`. The top-level `.claude-plugin/marketplace.json` has no per-plugin version field for humanizer, so no marketplace edit is needed for this issue — same as issue #94.

---

## Open Questions

### Resolved During Planning

- **Q (from origin Outstanding Questions, R8/R9):** What exact shape detects example regions inside a skill-file input? → Fenced code blocks, block-quoted `Before:`/`After:` (and variants like `Draft:` / `Final:`), and labeled `**Example:**` sections; conservative default keeps instruction prose under the skill-file profile when the region label is ambiguous. See Key Technical Decisions and Assumptions.
- **Q (from origin, R12):** Per-rule vs per-instance counting for "skipped" → per-rule. See Key Technical Decisions.
- **Q (from origin, R14):** Regression fixture as minimal excerpt under `tests/` or vendored copy of upstream file → minimal excerpt with attribution. See Assumptions.
- **Q (planning-time):** Tag placement (in-heading vs sub-line) → in-heading with two-space separation. See Assumptions.
- **Q (planning-time):** PERSONALITY AND SOUL section tag granularity (root H2 vs per subsection) → root H2 only. See Assumptions.

### Deferred to Implementation

- **Tie-breaking when an example region is nested inside another example region** (e.g., a fenced code block inside a `Before:` blockquote). First-match-wins by outer region: the outer region's profile selection governs the inner content. The implementer follows the priority order without revisiting the design; the conservative-default rule (R9) makes ambiguous nesting resolve toward instruction-prose treatment, which under the file's primary `skill-file` profile means rule-skipping rather than rule-applying — the safer failure mode.
- **Exact `(N applied, M skipped)` counts that fall out of the literal tag mapping.** Counting rule: `applied = rules whose tag matches the active profile or is "both"; skipped = rules whose tag is the other-audience-only value`. With the tag mapping in U1 (no rule tagged `skill-file`-only; rules 9, 10, 13, 14, 15, 16, 25 tagged `prose`; the remaining 18 numbered rules tagged `both`; the `## PERSONALITY AND SOUL` section tagged `prose` but not counted as a numbered rule), the literal counts are: `prose`-classified file → `applied = 25, skipped = 0`; `skill-file`-classified file → `applied = 18, skipped = 7`. The illustrative numbers in the brainstorm's R12 example (`24 rules applied, 0 skipped` for a CHANGELOG; `12 rules applied, 8 skipped` for a SKILL.md) are descriptive of the block's shape, not derived from the tag mapping — U1's count semantics note should state the literal mapping above so the operator can sanity-check the emitted counts against a fixed expected value.

---

## Output Structure

```
plugins/humanizer/skills/humanizer/
  SKILL.md                                              # modified (U1)
  tests/
    profiles/                                           # new (U2)
      precision-word-allow-list/
        input.md                                        # minimal excerpt reproducing PR #107 6fda523 failing phrase
        input.md.expected                               # single token: unchanged-preserved
        README.md                                       # attribution and assertion description
plugins/humanizer/.claude-plugin/
  plugin.json                                           # version bump 2.4.0 -> 2.5.0 (U3)
```

The tree is a scope declaration; the implementer may rename `precision-word-allow-list/` if a more descriptive label emerges during implementation. The per-unit `**Files:**` sections remain authoritative.

---

## Implementation Units

### U1. Add per-rule profile tags, allow-list, example-block exception, profile selection, and reporting block to humanizer `SKILL.md`

**Goal:** Modify `plugins/humanizer/skills/humanizer/SKILL.md` so every rule section header carries a profile tag, Rule 22 carries a precision-word allow-list in its body, the per-file processing loop gates rule evaluation on the resolved profile and routes example regions inside skill-file inputs back to the prose rule set, and a new `Applied profiles:` summary block reports per-file profile selection and rule-application counts adjacent to the existing `Auto-detected audiences:` block.

**Requirements:** R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11, R12, R13 (covers AE1, AE2, AE3, AE4, AE5, AE6, AE7)

**Dependencies:** Depends on issue #94 (CLOSED) landing the classifier, the `audience=` argument, and the per-file processing loop. All present in the current `SKILL.md`. No upstream blocker.

**Files:**
- Modify: `plugins/humanizer/skills/humanizer/SKILL.md`

**Approach:**

The edit happens in five distinguishable areas of the existing `SKILL.md`. Each area lists what to add or change; nothing in the file is moved or deleted outside the named edits.

1. **Per-rule profile tags on every numbered rule header (R1, R2, R3, R4) and on the PERSONALITY AND SOUL section (R5).**

   Append `  [profile: <value>]` (two-space separator) to each of the 25 rule headings and to the `## PERSONALITY AND SOUL` heading. The exact mapping follows R2, R3, R4, R5 verbatim:

   - **`[profile: both]`** — rules 1, 2, 3, 4, 5, 6, 7, 8, 11, 12, 17, 18, 19, 20, 21, 22, 23, 24. Plus the brainstorm-stated `both` rules (1, 3, 4, 5, 7, 8, 11, 12, 19, 20, 21, 22, 23, 24) explicitly; rules 2, 6, 17, 18 are not enumerated in R2 or R3 but follow the `both` default per the Key Decision ("`both` is the default tag"). Implementer cross-checks against R2 + the default-rule reasoning before tagging.
   - **`[profile: prose]`** — rules 9, 10, 13, 14, 15, 16, 25 plus the `## PERSONALITY AND SOUL` section heading. Exactly as enumerated in R3 and R5.

   Rule 22 carries `[profile: both]` per R4; its precision-word allow-list (added in area 2) applies under both profiles.

   For each tag added, leave the rest of the rule body unchanged. No rewording of the rule prose, no resequencing.

2. **Precision-word allow-list inside Rule 22's body (R6, R7).**

   Inside the existing Rule 22 section (lines 417-426 of the current file), append a new subsection immediately after the canonical Before → After examples list:

   ```markdown
   **Precision-word allow-list:** Do not strip or substitute these words when applying the
   filler-phrase rewrites above. They carry specification-grade precision that the rewrite
   would otherwise erase.

   - `unchanged`, `exactly`, `at least`, `at most`, `only`, `solely`
   - RFC 2119 keywords: `MUST`, `MUST NOT`, `SHOULD`, `SHOULD NOT`, `MAY`, `REQUIRED`,
     `SHALL`, `SHALL NOT`, `RECOMMENDED`, `OPTIONAL` (and their lowercase forms when they
     appear in spec-adjacent prose)

   The allow-list applies under both `prose` and `skill-file` profiles. The canonical
   filler rewrites ("in order to" → "to," "Due to the fact that" → "Because," etc.) remain
   in effect; the allow-list only blocks rewrites that would delete or substitute a listed
   word. Worked example: *"continues to work unchanged when the file is later assembled"*
   stays *as written* — the word `unchanged` is preserved.
   ```

   The worked-example phrase from `quadralay/markdown-plus-plus` PR #107 commit `6fda523` appears verbatim in the allow-list body so an agent reading Rule 22 sees the regression case it is supposed to prevent at the same moment it reads the rule. (R6 + R14 share the same surface; the regression fixture in U2 exercises the same phrase against the rule.)

3. **Example-block exception in the rule-evaluation loop (R8, R9).**

   Add a new subsection immediately after `## Audience classification` and before `## Your Task` (so it reads as the bridge between classification and rule application). Working title for the new subsection: `## Example-region exception`. Content:

   - **One paragraph framing.** When a file is classified `skill-file`, the skill-file profile applies to *instruction prose* but not to *embedded example output*. Sample commit messages, sample PR descriptions, fenced "Before:"/"After:" blocks demonstrating desired output, and labeled example sections receive the full `prose` profile because the agent will mimic the register of examples it sees. If a skill teaches "good output looks like this" and the example is AI-slop, the agent's output will be AI-slop.
   - **Region detector enumeration.** Three explicit shapes the agent should detect:
     - Fenced code blocks delimited by ` ``` ` (any language tag or none).
     - Block-quoted contrast pairs introduced by a label of the form `**Before:**`, `**After:**`, `**Draft:**`, `**Final:**`, `**Before (AI-sounding):**`, `**Draft rewrite:**`, or `**Now make it not obviously AI generated.**` (the labels used in the humanizer's own Full Example section).
     - Labeled example sections introduced by `**Example:**` or by a heading whose title begins with `Example` or `Worked example`.
   - **Conservative-default rule.** When a region's label is ambiguous, treat the region as instruction prose under the file's primary profile rather than mistakenly switching to prose inside genuine instruction text. The failure mode of not switching is the documented worked-example regression; the failure mode of switching unnecessarily is at worst a no-op.
   - **Reporting consequence.** Example-region rule applications are not separately counted in the `Applied profiles:` summary. The summary's count reflects rules applied to the file's *instruction prose* under its primary profile; the example-region exception is a within-file behavior, not a separate file. (Documented in the count-semantics note in area 5 below.)

4. **Profile-gated rule evaluation in the per-file processing loop (R10, R11).**

   The existing per-file processing loop (current SKILL.md lines 68-80) ends with step 3 stating *"Until the companion profile lands, every label is handled by the prose rules below, but the per-file label is still recorded."* Replace that sentence with the profile-selection rule:

   - Step 3 (revised): *"Process each file under the rule set selected by its label. Files labeled `skill-file` apply rules tagged `[profile: skill-file]` or `[profile: both]`; files labeled `prose` apply rules tagged `[profile: prose]` or `[profile: both]`. Within a `skill-file`-classified file, apply the example-region exception (see `## Example-region exception`) so embedded examples are rewritten under the `prose` rule set."*

   No change to steps 1, 2, 4, 5 of the loop. No change to the `audience=` argument grammar (R11 explicitly: no new override argument).

5. **Applied-profile reporting block (R12, R13).**

   Add a new subsection `### Applied-profile summary format` immediately after the existing `### Classification summary format` subsection (current SKILL.md lines 82-103). Content:

   - **One paragraph framing.** After the `Auto-detected audiences:` block, emit an `Applied profiles:` block immediately following it (no blank line between is fine; the operator reads the two blocks as classification → consequence). The new block reports the resolved profile per file and a `(N rules applied, M skipped)` count.
   - **Format example.** Show the pinned shape:

     ```
     Applied profiles:
       plugins/humanizer/skills/humanizer/SKILL.md  -> skill-file (12 rules applied, 8 skipped)
       CHANGELOG.md                                 -> prose (24 rules applied, 0 skipped)
     ```

     Two-space indent. Two spaces around `->`. Resolved profile name. Space. Parenthesized count.

   - **Count semantics.** `applied` = rules whose tag matches the active profile or is `both`; `skipped` = rules whose tag is the other-audience-only value. The `## PERSONALITY AND SOUL` section is a section, not a numbered rule, and is not included in either count. Example-region rule applications within a file are not separately counted (within-file behavior, not separate file).

   - **Forced-profile interaction.** When the `audience=` argument forces a profile globally, the `Applied profiles:` rows append `(forced)` after the count, matching the same convention issue #94's `Auto-detected audiences:` block uses:

     ```
     Applied profiles:
       plugins/humanizer/skills/humanizer/SKILL.md  -> prose (25 rules applied, 0 skipped) (forced)
     ```

   - **Update the `## Output Format` section** (current SKILL.md lines 481-488) to add a new item 6: *"Applied-profile summary — the `Applied profiles:` block (see `### Applied-profile summary format`). Always emit immediately after the `Auto-detected audiences:` block when one or more file paths were processed; omit only when the invocation was raw text with no file paths."*

**Patterns to follow:**
- Embedded methodology inside a single `SKILL.md`, no helper scripts — same as issue #94, same as `plugins/webworks-agent-skills/skills/claude-md-audit/SKILL.md`.
- Summary block shape and indentation — match `### Classification summary format` (current SKILL.md lines 82-103) byte-for-byte on indentation, arrow style, and `(forced)` placement so the two blocks read as siblings.
- Two-space tag separator on rule headings — established by the brainstorm's worked example `### 13. Em Dash Overuse  [profile: prose]`.

**Test scenarios:**

Test expectation: verification is by reading the modified `SKILL.md` against the requirements traceability and by exercising the regression fixture from U2 against the new Rule 22 allow-list. The U2 fixture is the executable assertion that U1's Rule 22 edit landed correctly; U1 does not introduce its own test files.

Manual verification scenarios for the implementer:

- *Covers AE1.* Reading any of the 25 rule sections (or the `## PERSONALITY AND SOUL` section), an agent sees the `[profile: <value>]` tag in the heading. No rule is missing a tag. The PERSONALITY AND SOUL section header carries `[profile: prose]`.
- *Covers AE2.* Reading Rule 22's allow-list subsection, an agent given a `skill-file`-classified input containing *"continues to work unchanged when the file is later assembled"* preserves `unchanged` and still rewrites canonical filler ("in order to" → "to") elsewhere in the same input.
- *Covers AE3.* Reading Rule 22's allow-list under either profile, an agent processing the sentence *"The handler MUST validate the token before responding"* preserves `MUST` in uppercase.
- *Covers AE4.* Reading the `## Example-region exception` subsection plus the revised per-file loop step 3, an agent given a `skill-file`-classified input with a fenced code block labeled `**After:**` applies the skill-file profile to the surrounding instruction prose and the prose profile to the fenced contents.
- *Covers AE5.* Reading the revised per-file loop step 3 plus the existing `audience=auto` default, an agent given one `SKILL.md` (auto-detected as `skill-file`) and one `CHANGELOG.md` (auto-detected as `prose`) processes the SKILL.md with the skill-file profile and the CHANGELOG.md with the prose profile in the same run.
- *Covers AE6.* Reading the `audience=` argument section (unchanged from issue #94) plus the new `Applied profiles:` summary, an agent given a `SKILL.md` invoked with `audience=prose` forced applies the prose profile (including the prose-tagged rules) and reports `(forced)` on the row.
- *Covers AE7.* Reading the new `### Applied-profile summary format` subsection plus the updated `## Output Format`, an agent given a mixed-input invocation emits an `Auto-detected audiences:` block immediately followed by an `Applied profiles:` block with the documented per-row count.

**Verification:**

- The modified `SKILL.md` parses as valid YAML frontmatter + markdown.
- Each of the 25 numbered rule headings carries one of `[profile: both]`, `[profile: prose]`, or `[profile: skill-file]`. The `## PERSONALITY AND SOUL` heading carries `[profile: prose]`. No rule is missing a tag (grep for `^### \d` and confirm each match has the tag suffix).
- Rule 22's body contains the precision-word allow-list with the enumerated words and RFC 2119 keywords. The worked-example phrase from PR #107 commit `6fda523` appears verbatim in the allow-list explanation.
- A new `## Example-region exception` subsection sits between `## Audience classification` and `## Your Task`.
- Per-file loop step 3 is revised to gate on the resolved profile and to apply the example-region exception.
- A new `### Applied-profile summary format` subsection follows the existing `### Classification summary format`.
- `## Output Format` is updated to include the new `Applied profiles:` block at item 6.
- The skill's existing `description` field is unchanged (trigger surface preserved).
- The 25 rule bodies are otherwise unchanged below the heading (scope boundary on rule rewording preserved).

---

### U2. Add regression fixture for the precision-word allow-list

**Goal:** Provide a single inspectable fixture under `plugins/humanizer/skills/humanizer/tests/profiles/precision-word-allow-list/` that exercises the worked-example diff from `quadralay/markdown-plus-plus` PR #107 commit `6fda523`. The fixture asserts that under the `skill-file` profile, Rule 22's filler-phrase rewrite preserves the word `unchanged` in the failing phrase.

**Requirements:** R14 (covers AE2 alongside U1's Rule 22 edit)

**Dependencies:** U1 (the allow-list has to be in `SKILL.md` for the fixture to assert against it).

**Files:**
- Create: `plugins/humanizer/skills/humanizer/tests/profiles/precision-word-allow-list/input.md`
- Create: `plugins/humanizer/skills/humanizer/tests/profiles/precision-word-allow-list/input.md.expected`
- Create: `plugins/humanizer/skills/humanizer/tests/profiles/precision-word-allow-list/README.md`

**Approach:**

- **`input.md`** — a minimal excerpt of three to five sentences reproducing the failing phrase from PR #107 commit `6fda523`. The phrase *"continues to work unchanged when the file is later assembled"* appears verbatim. Surrounding sentences provide enough context that a humanizer pass naturally encounters Rule 22's filler-phrase rewrite candidate. No vendoring of the full upstream file; the excerpt is the assertion target. The frontmatter shape (or lack of it) should be irrelevant to the assertion; the fixture's classification is forced via the operator's invocation (`/humanizer audience=skill-file plugins/humanizer/skills/humanizer/tests/profiles/precision-word-allow-list/input.md`) so the assertion does not depend on the path tripping heuristic 3 (which it will, because of the corpus-path caveat issue #94's README documents — same caveat applies here).
- **`input.md.expected`** — a single line containing one token. Recommended: `unchanged-preserved`. The token names the assertion ("the word `unchanged` survives the rewrite"), not the classification. A future test runner reads this token and reports pass/fail. The implementer can substitute a different single-token spelling if a runner already exists with vocabulary preferences; the semantics are what matter.
- **`README.md`** — one short page documenting:
  - The cross-repo reference: `quadralay/markdown-plus-plus` PR #107 commit `6fda523`, the file that contained the original failing phrase, and the rewrite that triggered the regression.
  - The assertion: under the `skill-file` profile (or under default `audience=auto` once the fixture's path puts it in a skill-file-classified location), Rule 22's filler-phrase rewrite must preserve `unchanged` in the failing phrase.
  - The corpus-path caveat (same as `tests/auto-detection/README.md`): the fixture's real on-disk path begins with `plugins/humanizer/skills/humanizer/tests/profiles/`, which trips heuristic 3 on the outer `plugins/<name>/skills/<name>/` segment. A runner should evaluate the fixture's logical path relative to its own subdirectory, or the operator forces `audience=skill-file` to make the assertion target explicit.
  - How a future runner reads the `.expected` file: single token, compare against pass/fail.

**Patterns to follow:**
- Fixture directory layout — see `plugins/humanizer/skills/humanizer/tests/auto-detection/` for the established repo convention (subdirectory per fixture when path or surrounding files matter, paired `.expected` files, README documenting any caveats).
- README shape and corpus-path caveat language — directly modeled on `plugins/humanizer/skills/humanizer/tests/auto-detection/README.md` (lines 15-43) so the two corpora read as siblings.

**Test scenarios:**

Test expectation: none — the fixture *is* the test case for U1's Rule 22 allow-list. The plan does not wire it into an automated runner (see Scope Boundaries). Verification is by inspection plus a manual humanizer invocation against the fixture.

Manual verification scenarios for the implementer:

- *Covers AE2.* Running `/humanizer audience=skill-file plugins/humanizer/skills/humanizer/tests/profiles/precision-word-allow-list/input.md` produces a humanized output in which the phrase *"continues to work unchanged when the file is later assembled"* is unchanged. The canonical filler rewrites elsewhere in the input (if any) still proceed.
- *Cross-check.* The `input.md.expected` file contains exactly one token. The `README.md` documents the cross-repo source and the corpus-path caveat. The fixture sits under `tests/profiles/precision-word-allow-list/`, not at the corpus root.

**Verification:**

- All three files exist at the documented paths.
- `input.md` contains the verbatim failing phrase from PR #107 commit `6fda523`.
- `input.md.expected` is a single-line single-token file.
- `README.md` documents source, assertion, corpus-path caveat, and `.expected` token semantics.
- The fixture lives under `plugins/humanizer/skills/humanizer/tests/profiles/` (not under `tests/auto-detection/`) so the two corpora stay distinct.

---

### U3. Bump humanizer plugin version to 2.5.0

**Goal:** Apply the project's required version bump so the new feature ships under a new version of the humanizer plugin, per `CLAUDE.md` ("minor: new skills, new features").

**Requirements:** Project convention (not an origin requirement, but mandated by repo `CLAUDE.md`).

**Dependencies:** U1, U2 (the new feature must exist before the version is bumped to ship it).

**Files:**
- Modify: `plugins/humanizer/.claude-plugin/plugin.json` — change `"version": "2.4.0"` to `"version": "2.5.0"`.

**Approach:**

Edit the single `version` field in `plugins/humanizer/.claude-plugin/plugin.json`. Do not modify other fields (name, description, author, etc.). Do not touch `.claude-plugin/marketplace.json` — the top-level marketplace.json has no per-plugin version field for the humanizer plugin (verified at plan time and at issue #94 plan time). Do not run `scripts/bump-version.sh` — that script only handles `webworks-agent-skills`.

**Patterns to follow:**
- Manual single-field version bump — same shape as issue #94 used for the 2.3.0 → 2.4.0 bump. The humanizer plugin sits outside `scripts/bump-version.sh` coverage; the bump is applied by hand.

**Test scenarios:**

Test expectation: none — pure version-string change.

Manual verification scenarios for the implementer:

- After the edit, `jq -r '.version' plugins/humanizer/.claude-plugin/plugin.json` returns `2.5.0`.
- No other field in `plugin.json` changes.
- `.claude-plugin/marketplace.json` is not modified by this unit.

**Verification:**

- `plugins/humanizer/.claude-plugin/plugin.json` shows `"version": "2.5.0"`.
- `git diff` for this unit touches exactly one file with exactly one line changed.

---

## Sources & References

- **Origin requirements:** `docs/brainstorms/2026-05-23-issue-95-dual-audience-humanizer-profiles-requirements.md`
- **Dependency (CLOSED):** Issue #94 (humanizer skill-file auto-detection plumbing) — the classifier, `audience=` argument, per-file loop, and `Auto-detected audiences:` summary that this issue consumes.
- **Dependency (CLOSED):** Issue #93 (humanizer plugin vendoring) — the in-tree copy this issue edits.
- **Worked-example evidence:** `quadralay/markdown-plus-plus` PR #107 commit `6fda523` — the regression that motivates the precision-word allow-list and Rule 22 carve-out; reproduced by U2's fixture.
- **Companion issue #94 plan (now removed via post-merge cleanup):** recovered from `git show 284d3b9:docs/plans/2026-05-22-001-feat-humanizer-auto-detection-plan.md` for the standard-tier plan shape this plan mirrors.
- **Repo convention sources:** `CLAUDE.md` (version bump policy), `scripts/bump-version.sh` (scope: webworks-agent-skills only), `docs/solutions/authoritative-skill-patterns.md` (skill description triggering), `docs/solutions/design-patterns/in-skill-heuristic-classifier-2026-05-22.md` (in-skill classifier design pattern this plan extends).
- **GitHub issue:** #95.
