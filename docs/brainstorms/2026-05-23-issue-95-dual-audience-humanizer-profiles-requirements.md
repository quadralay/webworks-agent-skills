---
date: 2026-05-23
topic: dual-audience-humanizer-profiles
issue: 95
---

# Dual-Audience Rule Profiles in Humanizer

## Summary

Add two named rule profiles to the vendored humanizer skill — `skill-file` and `prose` — so the audience classifier added in issue #94 selects an audience-appropriate rule set per file instead of routing every file through the prose rules. The skill-file profile drops the rules that degrade agent-consumed text (em dashes, rule-of-three, inline-header lists, the PERSONALITY AND SOUL guidance), keeps the rules that target vagueness and inflated language, and protects specification-grade precision words from filler-phrase rewrites. Example blocks inside skill files continue to receive the prose profile so modeled-output examples read like the human-grade output they teach.

---

## Problem Frame

The humanizer skill currently applies one prose-oriented rule set to every input. Issue #94 added a classifier that records `skill-file` vs `prose` per file but does not yet branch behavior on the label — the SKILL.md notes that "until the companion dual-audience profile feature lands, every file ends up under the prose profile defined below."

A worked-example pass against `plugins/markdown-plus-plus/skills/markdown-plus-plus/references/best-practices.md` in the `quadralay/markdown-plus-plus` repo (PR #107, commit `6fda523`) produced roughly two genuine improvements per minor regression. The improvements clustered on rules targeting vagueness, inflated language, and anthropomorphization. The regressions clustered on rules targeting punctuation density, structural parallelism, and rhythm variation — patterns that are noise to a prose reader but load-bearing structure for an agent reading a skill.

One concrete failure mode from that pass: rule 22 ("filler phrases") rewrote *"continues to work unchanged when the file is later assembled"* to *"keeps working when the file is later assembled,"* stripping the word `unchanged`. In specification-adjacent prose, `unchanged` is doing real work — it is the assertion that the file's content is not modified between two pipeline stages. Filler-phrase rewriting that does not respect a small allow-list of precision words turns a normative claim into an ambiguous one.

A second concrete failure mode: the PERSONALITY AND SOUL section actively recommends patterns ("vary your rhythm," "use 'I' when it fits," "let some mess in") that degrade skill-file utility. Skill files want uniform structure, impersonal voice, and confident directives — the opposite of what that section advocates. A single profile cannot simultaneously serve a press-release rewrite and a SKILL.md edit; the cost of conflating them is borne by whichever audience the next humanizer run happens to be aimed at.

The classification plumbing exists. The remaining work is gating each rule on the active profile and routing example blocks back to prose treatment even inside skill files.

---

## Requirements

**Per-rule profile tagging**

- R1. Tag every rule section header in `plugins/humanizer/skills/humanizer/SKILL.md` with one of `[profile: both]`, `[profile: prose]`, or `[profile: skill-file]`. The tag appears in the section heading itself (e.g., `### 13. Em Dash Overuse  [profile: prose]`) so the agent reads the gating at the same moment it reads the rule.
- R2. Rules 1, 3, 4, 5, 7, 8, 11, 12, 19, 20, 21, 23, and 24 carry the `both` tag. These target vagueness, filler, inflated language, weasel words, AI vocabulary, copula avoidance, synonym cycling, false ranges, chatbot artifacts, knowledge-cutoff disclaimers, sycophantic tone, hedging, and generic positive conclusions — patterns that help agent consumption as much as human consumption.
- R3. Rules 9, 10, 13, 14, 15, 16, and 25 carry the `prose` tag. These target negative parallelisms, rule-of-three, em dashes, boldface, inline-header lists, title-case headings, and hyphenated word pairs — patterns that either ARE the preferred shape for skill-instruction surfaces (R15) or are scannable cues the agent relies on (R14), or whose churn does not help comprehension (R13, R16, R25).
- R4. Rule 22 (filler phrases) carries the `both` tag but includes a precision-word allow-list (see R6).
- R5. The PERSONALITY AND SOUL section carries the `prose` tag at the section header. Its guidance — rhythm variation, first-person voice, "let some mess in," opinions, mixed-feeling phrasing — is skipped wholesale under the skill-file profile.

**Precision-word allow-list**

- R6. Rule 22 (filler phrases) preserves a small allow-list of words even when surrounding filler is rewritten. The list contains: `unchanged`, `exactly`, `at least`, `at most`, `only`, `solely`, and the RFC 2119 keywords `MUST`, `MUST NOT`, `SHOULD`, `SHOULD NOT`, `MAY`, `REQUIRED`, `SHALL`, `SHALL NOT`, `RECOMMENDED`, `OPTIONAL` (and their lowercase forms when they appear in spec-adjacent prose). The allow-list applies under both profiles — the precision claim a word carries does not depend on the audience.
- R7. The "in order to" → "to" substitution and the other canonical filler rewrites in rule 22 remain in effect. The allow-list narrows the rule, it does not disable it.

**Example-block exception**

- R8. When a file is classified `skill-file`, the skill-file profile applies to instruction prose but NOT to embedded example output. Sample commit messages, sample PR descriptions, fenced "Before:"/"After:" blocks demonstrating desired output, and labeled example sections receive the full prose profile.
- R9. Detection of example regions inside a skill-file input covers, at minimum: fenced code blocks (` ``` ... ``` `), block-quoted contrast pairs labeled with `Before:` / `After:` (or equivalent shapes), and labeled example sections that introduce modeled output. The detection is conservative — when in doubt, treat a region as instruction prose under the skill-file profile rather than mistakenly switching to prose inside genuine instruction text.

**Profile selection**

- R10. The skill consults the audience label recorded by the issue #94 classifier and selects the rule set accordingly. Files labeled `skill-file` apply rules tagged `skill-file` or `both`. Files labeled `prose` apply rules tagged `prose` or `both`.
- R11. The skill respects the explicit `audience=skill-file` and `audience=prose` overrides already defined in issue #94's `audience=` argument. No new override argument is introduced by this issue.

**Reporting**

- R12. The output summary block reports the applied profile per file, in addition to the classification line already specified by issue #94. The format is:

  ```
  Applied profiles:
    plugins/humanizer/skills/humanizer/SKILL.md   -> skill-file (12 rules applied, 8 skipped)
    CHANGELOG.md                                  -> prose (24 rules applied, 0 skipped)
  ```

  The per-file rule-application counts give the operator a quick sanity check on whether profile gating fired as intended.

- R13. When the classification summary and the applied-profile summary appear together, they appear as two adjacent blocks (`Auto-detected audiences:` followed by `Applied profiles:`) so the operator can read classification and consequence in one place.

**Regression test**

- R14. Add a regression test that exercises the worked-example diff from `quadralay/markdown-plus-plus` PR #107 commit `6fda523`. Under the skill-file profile, the precision word `unchanged` in the phrase *"continues to work unchanged when the file is later assembled"* must survive the rewrite. The test lives under `plugins/humanizer/skills/humanizer/tests/` and joins the auto-detection fixture set added in issue #94.

---

## Acceptance Examples

- AE1. **Covers R1, R2, R3, R4, R5.** Given the updated `SKILL.md`, when an agent reads any rule's section header, then the header carries one of `[profile: both]`, `[profile: prose]`, or `[profile: skill-file]`. The PERSONALITY AND SOUL section header carries `[profile: prose]`. No rule is missing a tag.
- AE2. **Covers R6, R7, R14.** Given a skill-file-classified input containing the phrase *"continues to work unchanged when the file is later assembled,"* when the humanizer applies rule 22, then the word `unchanged` is preserved. The rewrite of canonical filler ("in order to" → "to") elsewhere in the same input still proceeds.
- AE3. **Covers R6.** Given an input containing the sentence *"The handler MUST validate the token before responding,"* when the humanizer processes the file under either profile, then `MUST` is preserved in its uppercase form.
- AE4. **Covers R8, R9.** Given a `skill-file`-classified input that contains a fenced code block labeled `**After:**` demonstrating desired human-style output, when the humanizer processes the file, then the instruction prose around the block receives the skill-file profile and the contents of the fenced block receive the prose profile.
- AE5. **Covers R10.** Given a single invocation passing one `SKILL.md` (auto-detected as `skill-file`) and one `CHANGELOG.md` (auto-detected as `prose`), when the humanizer runs under default `audience=auto`, then the `SKILL.md` is processed with the skill-file profile and the `CHANGELOG.md` with the prose profile, in the same run.
- AE6. **Covers R11.** Given a `SKILL.md` invoked with `audience=prose` forced, when the humanizer runs, then the prose profile is applied to the SKILL.md (including the rules tagged `prose`-only) and the applied-profile summary records `(forced)` per the issue #94 reporting convention.
- AE7. **Covers R12, R13.** Given a mixed-input invocation processing three files, when the run completes, then the output contains an `Auto-detected audiences:` block immediately followed by an `Applied profiles:` block. Each `Applied profiles:` row reports the file path, the resolved profile name, and the `(N rules applied, M skipped)` counts.

---

## Success Criteria

- An operator running humanizer on a `SKILL.md` no longer has to manually review the diff for stripped precision words or for skill-degrading rhythm/voice changes — the profile boundary catches those before the rewrite is proposed.
- The humanizer's pass on the worked-example file from `quadralay/markdown-plus-plus` PR #107 reproduces the original "two improvements per regression" pattern only on the improvement side, not on the regression side: rule 22 leaves `unchanged` intact, the PERSONALITY AND SOUL guidance does not fire, and em-dash / inline-header rewrites are skipped.
- A downstream agent reading `SKILL.md` can determine for any rule, in one pass, whether the rule applies to the file in front of it — the per-rule tag answers the gating question at the same moment the rule is read.
- The applied-profile summary in the output gives the operator a no-extra-tools sanity check: visible per-file profile selection, visible rule-application counts, visible `(forced)` markers when overrides are in play.

---

## Scope Boundaries

- **Not introducing additional profiles beyond `skill-file` and `prose`.** Profile granularity past two audiences (e.g., a separate `agent-prompt`, `commit-message`, or `release-notes` profile) is deferred until a real use case shows that two profiles is insufficient. Premature splitting fragments the rule tagging.
- **Not adding a per-file override syntax.** Issue #94's `audience=skill-file` / `audience=prose` argument is global to the invocation. If an operator needs split treatment, they run humanizer twice. A per-file override flag would add invocation complexity for a case that has not yet appeared in real workflow runs.
- **Not modifying the issue #94 heuristics or classifier.** This issue consumes the classification result; it does not change how the result is produced. Reclassification logic changes belong in a separate issue.
- **Not porting rule changes to upstream `blader/humanizer`.** Audience-awareness is out of scope upstream per issue #93's vendoring rationale. The profile tags and allow-list live only in this repo's vendored copy and are documented in `UPSTREAM.md` as a deliberate divergence.
- **Not auditing or rewriting the existing rule prose for clarity.** The scope is gating which rules fire, not rewriting how they explain themselves. Per-rule prose audits, if needed, are separate work.

---

## Key Decisions

- **Per-rule tags in the section header, not a separate config table.** The tag is read at the moment the agent reads the rule, so there is no consult-the-table step that can be skipped. The trade-off — repeating the tag once per rule rather than once per file — costs ~25 lines of markdown and saves an indirection that has historically been a source of rule-application drift in similar gating systems.
- **`both` is the default for any rule whose audience-applicability is genuinely the same.** Most rules carry `both`. The exceptions are explicitly enumerated (R3 and R5), which makes the carve-out auditable rather than implicit.
- **Allow-list lives in rule 22's body, not in a separate section.** The precision words are only meaningful in the context of the rule that would otherwise strip them. Splitting the allow-list into a top-level section would force a reader of rule 22 to follow a pointer to know what the rule actually does.
- **Example blocks switch profile based on region, not based on a new classification.** A skill-file-classified file does not get reclassified mid-pass — the file stays `skill-file` for reporting, and the example-region detection just selects which rule set fires within that region. This keeps the classification summary stable and the profile-switching logic localized to the rule-evaluation loop.

---

## Dependencies / Assumptions

- **Depends on issue #94 (CLOSED) — auto-detection plumbing.** The classifier, the `audience=` argument, and the per-file processing loop are already in place. This issue adds the profile branching on top of that plumbing.
- **Depends on issue #93 (CLOSED) — vendored copy.** The skill must be owned in-tree to accept the profile tags and the allow-list, since both diverge from the upstream `blader/humanizer` skill.
- **Assumes the worked-example file in `quadralay/markdown-plus-plus` PR #107 commit `6fda523` is reachable for the regression test as a fixture.** If the cross-repo reference is too brittle for a checked-in test, the failing phrase (*"continues to work unchanged when the file is later assembled"*) can be vendored into the fixture set as a minimal excerpt with attribution — the rewrite-survival assertion does not need the full file.
- **Assumes the RFC 2119 keyword set is sufficient for spec-adjacent precision words.** If skill files surface other normative vocabularies (e.g., domain-specific compliance terms), the allow-list can be extended in place without revisiting the architecture.

---

## Outstanding Questions

### Deferred to Planning

- [Affects R8, R9][Technical] What exact regex or parser shape is used to detect example regions inside a skill-file input? Fenced code blocks are unambiguous; `Before:` / `After:` constructs and "labeled example sections" admit several reasonable definitions, and the conservative-default rule (R9) leaves the precision-vs-recall trade-off to the implementer.
- [Affects R12][Technical] Are "skipped" rule counts in the applied-profile summary counted per-rule (a rule was tagged out-of-profile and not evaluated) or per-instance (a rule was evaluated and produced no rewrite)? Both are defensible; the first is cheaper to compute and probably more useful to the operator.
- [Affects R14][Needs research] Should the regression fixture be a minimal excerpt under `tests/` or a vendored copy of the relevant portion of the upstream file? Tied to the cross-repo reachability assumption above.
