---
title: "feat: Add claude-md-audit skill"
type: feat
status: active
created: 2026-05-19
issue: 52
origin: docs/brainstorms/2026-05-19-issue-52-claude-md-audit-skill-requirements.md
depth: lightweight
---

# feat: Add `claude-md-audit` Skill

## Summary

Add a new skill, `claude-md-audit`, to the `webworks-claude-skills` plugin. The skill codifies a methodology for auditing and reducing `CLAUDE.md` (or other agent MD) files, keeping only content that prevents real, repeated agent mistakes and removing content the model can discover from the codebase. The methodology is prose-only (no scripts), domain-neutral, and structurally aligned with the four existing skills in the plugin.

## Problem Frame

`CLAUDE.md` files accumulate content that describes the codebase rather than steering the agent. Recent research shows LLM-generated context files decrease task completion ~3% and developer-written files improve it only ~4%, while both increase cost 20%+. The team applied a reduction methodology by hand to the ePublisher `CLAUDE.md` (180 → 49 lines) and wants to codify it as a reusable skill that any agent can apply against any repo. (See origin: `docs/brainstorms/2026-05-19-issue-52-claude-md-audit-skill-requirements.md`.)

## Requirements Traceability

Origin requirements R1-R10 and acceptance examples AE1-AE5 are addressed across the implementation units below. Specifically:

- **R1, R2, R10, AE1** — skill scaffolding and structural alignment → U1
- **R3, R4, R5, AE2** — methodology body (KEEP/REMOVE/REDUCE + Pink Elephant + Staleness) → U1
- **R6, R8, AE3** — reduced-file structure and under-60-line success criterion → U1
- **R7, AE4** — at least four before/after examples → U1
- **R9, AE5** — backup-before-reduction safety net → U1
- **Plugin version bump** (project convention from `CLAUDE.md`) → U2

## Key Technical Decisions

- **Skill structure mirrors existing skills.** Use the same XML-style section tags the four existing skills use (`<objective>`, `<overview>`, `<methodology>`, `<examples>`, `<success_criteria>`). This is the structure the issue body proposes and matches `automap/SKILL.md` and `epublisher/SKILL.md`. Resolves origin Outstanding Question on section names.
- **No plugin manifest changes required.** Verified at planning time: neither `plugins/webworks-claude-skills/.claude-plugin/plugin.json` nor `.claude-plugin/marketplace.json` enumerate per-skill entries — skills are discovered by directory presence. Resolves origin Outstanding Question on manifest registration. The acceptance criterion "Registered in the plugin manifest" is satisfied by creating the directory.
- **Backup mechanism: `CLAUDE.md.bak` adjacent to the original.** Simplest, most legible safety net; no extra directory needed; survives across git states. Resolves origin Outstanding Question on backup mechanism. (R9, AE5.)
- **Use the issue body's concrete before/after examples (SVN, NSIS, `Python27`, localization).** Concreteness wins over domain-neutrality here — readers learn the pattern faster from a real example with a name attached. The skill description and framing remain domain-neutral so the skill itself is not ePublisher-specific. Resolves origin Outstanding Question on example selection.
- **Description triggers on multiple agent MD names, not just `CLAUDE.md`.** Per origin R2 — wording must trigger on "audit my CLAUDE.md", "reduce my agent MD file", "review my AGENTS.md", etc.
- **Minor version bump (2.9.2 → 2.10.0).** New skill is an additive feature per `CLAUDE.md` versioning rules ("minor: new skills, new features").

## Assumptions

- The under-60-line target in the skill text is a guideline informed by the ePublisher reduction (180 → 49). Other repos may end up smaller or larger; the number is not a contract.
- The four-section structure (Environment / Build Commands / Behavioral Rules / Configuration) is the right durable shape based on the issue's proposal and the ePublisher application. A real audit of additional repos may suggest a fifth section (e.g., "Workflow pointers"); the skill text should treat the shape as empirical, not derived from first principles.
- Research claims in the skill body (3% completion decrease, 4% improvement, 20%+ cost increase) come from the source the issue cites and are reproduced as user-attested.

## Output Structure

```
plugins/webworks-claude-skills/skills/claude-md-audit/
  SKILL.md
```

A single-file skill, matching the shape of skills that are reference-and-decision-tree rather than script-driven (e.g., `markdown-integration` is also a single `SKILL.md` plus a `references/` directory; this skill needs only `SKILL.md`).

## Implementation Units

### U1. Create `claude-md-audit/SKILL.md`

**Goal:** Add the new skill file with the full methodology, before/after examples, and success criteria so an agent invoked against any repo's `CLAUDE.md` can apply the reduction without re-deriving the approach.

**Requirements:** R1, R2, R3, R4, R5, R6, R7, R8, R9, R10 (covers AE1, AE2, AE3, AE4, AE5)

**Dependencies:** none

**Files:**
- `plugins/webworks-claude-skills/skills/claude-md-audit/SKILL.md` — new file

**Approach:**

- Use the same frontmatter shape as neighboring skills: `name`, `description`. The `description` must explicitly mention `CLAUDE.md` *or other agent MD files* and should read in a way that triggers on phrases like "audit my CLAUDE.md", "reduce my agent MD file", "review my AGENTS.md", "shrink my context file".
- Use the section structure the issue body proposes, which also matches the existing skills' XML-tag-with-markdown pattern:
  - `<objective>` — what the skill does and why it exists (the research framing)
  - `<overview>` — the core principle ("if the model can find it in the codebase, it does not belong in the agent MD file")
  - `<methodology>` — the four-step audit (categorize → Pink Elephant Test → Staleness Test → draft reduced file with the four sections)
  - `<examples>` — before/after pairs spanning REMOVE (architecture overview, technology list), KEEP (environment gotcha, behavioral rule), and REDUCE (build commands trimmed to "command + link")
  - `<success_criteria>` — measurable success: under 60 lines, every line fails at least one test, backup exists
- Embed the backup requirement (`CLAUDE.md.bak` adjacent to the original) in the methodology section *and* repeat it as a line item in success criteria so it cannot be skipped.
- Use the issue body's existing examples (SVN, NSIS, `Python27`, localization resource files) — they are concrete and self-contained.
- Keep the skill prose-only — no Python helper, no shell script, no auto-runner. Per origin scope boundary "no helper scripts under the skill directory."

**Patterns to follow:**
- Frontmatter shape and `<objective>` framing — see `plugins/webworks-claude-skills/skills/automap/SKILL.md` lines 1-16 and `plugins/webworks-claude-skills/skills/epublisher/SKILL.md` lines 1-16
- `<success_criteria>` shape — see `plugins/webworks-claude-skills/skills/epublisher/SKILL.md` lines 231-239 (bulleted, measurable outcomes)
- Domain-neutral prose style — see `plugins/webworks-claude-skills/skills/markdown-integration/SKILL.md` for the prose-heavy, no-script pattern

**Test scenarios:**

Test expectation: none — this is a skill document (prose-only, no executable code). Verification is by reading the file against the requirements traceability list above.

Manual verification scenarios for the implementer:

- *Covers AE1.* The new skill loads alongside `automap`, `epublisher`, `markdown-integration`, and `reverb2` when the plugin is enabled, and its `description` surfaces in the user-invocable skills list. Resolved by directory presence + frontmatter shape.
- *Covers AE2.* Read the methodology section: it explicitly names KEEP / REMOVE / REDUCE, the Pink Elephant Test, and the Staleness Test. An agent reading only the skill (no chat context) can categorize a sample section without asking the user how the methodology works.
- *Covers AE3.* The success criteria section explicitly states the under-60-line target and the four-section structure (Environment / Build Commands / Behavioral Rules / Configuration), with explicit guidance to omit empty sections.
- *Covers AE4.* The examples section contains at least four before/after pairs spanning REMOVE, KEEP, and REDUCE, each self-contained (no external references required to understand them).
- *Covers AE5.* The methodology requires creating `CLAUDE.md.bak` (or equivalent backup) before applying changes, and the success criteria repeats this requirement.

**Verification:**

- File exists at `plugins/webworks-claude-skills/skills/claude-md-audit/SKILL.md`.
- File parses as valid YAML frontmatter + markdown (no broken frontmatter, no missing closing tags).
- `description` field mentions both `CLAUDE.md` and agent MD files (broader trigger surface).
- Each of R1-R10 is visibly addressed in the file (cross-check against the traceability list above).

---

### U2. Bump plugin version to 2.10.0

**Goal:** Apply the project's required version bump so the new skill ships under a new version, per `CLAUDE.md` ("minor: new skills, new features").

**Requirements:** Project convention (not an origin requirement, but mandated by repo `CLAUDE.md`).

**Dependencies:** U1 (the new skill must exist before the version is bumped to ship it).

**Files:**
- `plugins/webworks-claude-skills/.claude-plugin/plugin.json` — version field
- `.claude-plugin/marketplace.json` — version field

**Approach:**

- Run `scripts/bump-version.sh minor`. The script reads `plugin.json`, increments minor (2.9.2 → 2.10.0), zeros the patch, and writes the same version back into both `plugin.json` and `marketplace.json`. This keeps the two manifests in lockstep, which is the script's stated purpose.
- Do not hand-edit the JSON files — using the script is the documented workflow in `CLAUDE.md`.

**Patterns to follow:**
- `scripts/bump-version.sh` — the canonical bump path. Recent commits in `git log` follow this same pattern when introducing new skills.

**Test scenarios:**

Test expectation: none — this is a metadata bump. Verification is by reading the diff.

- *Manual verification.* After running the script, both manifest files show `"version": "2.10.0"`. The script's own output reports the same new version.

**Verification:**

- `jq -r '.version' plugins/webworks-claude-skills/.claude-plugin/plugin.json` returns `2.10.0`.
- `jq -r '.version' .claude-plugin/marketplace.json` returns `2.10.0`.
- `git diff --stat` shows changes only to those two files (plus the new skill from U1).

---

## Scope Boundaries

### In scope

- New skill directory and `SKILL.md`.
- Minor version bump.

### Out of scope

- **Not applying the methodology to this repository's own `CLAUDE.md`.** The repo's `CLAUDE.md` is already 60 lines and is in good shape; applying the new skill to it is a separate, follow-up application of the skill, not part of building it. (Origin scope boundary.)
- **Not generalizing the methodology to `README.md`, `CONTRIBUTING.md`, or other human-facing documentation.** Those serve human onboarding with different criteria. (Origin scope boundary.)
- **Not building an auto-runner, lint rule, pre-commit hook, or CI check.** The skill is invoked by a human or agent decision. (Origin scope boundary.)
- **Not enforcing a hard line limit.** The under-60-line target is a guideline, not a fail criterion. (Origin scope boundary.)
- **Not adding helper scripts under the skill directory.** Methodology is judgment-based, not algorithmic. (Origin scope boundary.)
- **Not modifying plugin manifests beyond the version bump.** Verified at planning time: skills are discovered by directory presence. (Origin scope boundary + planning verification.)

### Deferred to Follow-Up Work

- **Apply the new skill to other repositories the team maintains.** The skill itself is the deliverable; the team's broader rollout of the methodology across other `CLAUDE.md` files is downstream work and may surface refinements (e.g., a fifth section name) that get folded back into the skill in a later PR.
- **Empirical refinement of the four-section structure.** If the first real applications of the skill to additional repos suggest a fifth section (e.g., "Workflow pointers" or "Slash commands"), capture it as a separate refinement issue.

## Risks

- **Risk: the skill drifts from the research over time.** Mitigated by citing the source video / paper inside the skill (the issue body already does this) so a future maintainer can re-check the numbers if they want to update them. Low likelihood, low impact.
- **Risk: ePublisher-specific examples (SVN, `Python27`, NSIS) feel out of place in a domain-neutral skill.** Mitigated by framing them as concrete illustrations of generic categories ("environment gotcha", "tool path", "behavioral rule") rather than as recommendations. Low likelihood, low impact — concreteness aids understanding more than neutrality would.

## Final Checks

Before commit:

- [ ] `plugins/webworks-claude-skills/skills/claude-md-audit/SKILL.md` exists, has valid frontmatter, has all required sections (objective, overview, methodology, examples, success_criteria).
- [ ] R1-R10 each visibly addressed in the skill text (per the traceability list in U1's Test scenarios).
- [ ] `plugin.json` and `marketplace.json` both report `2.10.0`.
- [ ] No unrelated files changed.
- [ ] Commit uses conventional commit format (`feat:`) per repo `CLAUDE.md`.
