---
date: 2026-05-19
topic: claude-md-audit-skill
issue: 52
---

# `claude-md-audit` Skill — Reduce CLAUDE.md Files Based on Context-Management Research

## Summary

Add a new skill, `claude-md-audit`, to the `webworks-claude-skills` plugin that audits an arbitrary repository's `CLAUDE.md` (or other agent MD file) and reduces it to only the lines that prevent real, repeated agent mistakes. The methodology is rule-driven (KEEP / REMOVE / REDUCE) plus two stress tests ("Pink Elephant" bias, "Staleness"), grounded in published research showing that LLM-generated context files decrease task completion and that even developer-written files raise cost by 20%+ for marginal benefit. The skill is domain-neutral and intended for use across all repositories the team maintains.

---

## Problem Frame

Across the team's repositories, `CLAUDE.md` files have accumulated content that documents what the code looks like rather than what the agent should do. The accumulated content has measurable downsides:

1. **Cost without benefit.** Recent research found that LLM-generated `CLAUDE.md` files decrease task completion by ~3% and developer-written files improve it by only ~4%, while both increase costs by 20%+ as the model expands its exploration and reasoning around the additional context. Freshly generated files performed worse than no file at all.
2. **Bias toward the irrelevant.** Mentioning a technology, framework, or architectural pattern in the agent file biases the model toward reaching for it even when the current task is unrelated. ("Pink elephant" effect.)
3. **Stale entries actively mislead.** File paths, directory layouts, technology lists, and pattern guides go stale silently as the codebase evolves. The agent can no longer tell whether a stale claim still holds without re-reading the codebase — which it had to do anyway.
4. **Discoverable noise.** Most existing `CLAUDE.md` content restates what the model can already learn by glob, grep, and reading project files. That restatement is pure context overhead.

The team applied a reduction methodology by hand to the ePublisher `CLAUDE.md` and reduced it from 180 lines to 49 lines (~73% reduction) without losing useful steering. Codifying that methodology as a skill lets the team apply the same reduction systematically across every repository it maintains, and gives any future agent a consistent yardstick when reviewing or authoring agent MD files.

The current state of this repository's tree confirms the gap: `plugins/webworks-claude-skills/skills/automap/`, `epublisher/`, `markdown-integration/`, and `reverb2/` exist as skills, but no skill exists for auditing agent MD files. The methodology lives only in chat history and in one applied example.

---

## Requirements

**Skill scaffolding**

- R1. Create the skill at `plugins/webworks-claude-skills/skills/claude-md-audit/SKILL.md`, alongside the four existing skills in the plugin. Use the same frontmatter shape as the existing skills (`name`, `description`) and use a description that explicitly says the skill audits and reduces `CLAUDE.md` *or other agent MD files*, so it triggers on `AGENTS.md`, `GEMINI.md`, and similar variants.
- R2. The skill's `description` must read in a way that triggers when a user says "audit my CLAUDE.md", "reduce my agent MD file", "review my CLAUDE.md", or "shrink my context file" — not only when the literal word "audit" appears.

**Methodology body**

- R3. Document the **three-category audit**: KEEP (steers away from mistakes the model cannot self-correct), REMOVE (discoverable from the codebase), REDUCE (partially useful, trim to essentials). Each category must include at least two concrete examples drawn from the kinds of content commonly found in real `CLAUDE.md` files (environment gotchas, tool paths, behavioral rules, directory layouts, technology lists, build commands).
- R4. Document the **Pink Elephant Test**: "does mentioning this bias the model toward it when irrelevant?" Include at least two before/after examples where mentioning a technology or architectural pattern would steer the agent wrong on an unrelated task.
- R5. Document the **Staleness Test**: "will this go out of date, and would stale info cause harm?" Identify which kinds of content are stable over time (environment paths, behavioral rules) versus which require ongoing maintenance (file paths, directory structures, technology descriptions, pattern guides).
- R6. Provide a **reduced-file structure** with four sections (Environment, Build Commands, Behavioral Rules, Configuration) and explicit guidance to omit any section that is empty rather than leave a placeholder.

**Before/After examples**

- R7. Include at least four concrete before/after examples spanning REMOVE (architecture overview, technology list), KEEP (environment gotcha, behavioral rule), and REDUCE (build commands trimmed to "command + link to doc"). Examples must be self-contained (no need to reference an external repo to understand them) and should mirror the kinds of content that appeared in the team's pre-reduction ePublisher `CLAUDE.md`.

**Success criteria embedded in the skill**

- R8. The skill must state a measurable success criterion: the reduced file is under 60 lines for a typical repository, and every remaining line fails at least one test (model can't discover it on its own, or model consistently gets it wrong without it).
- R9. The skill must require a **backup of the original file** before any reduction is applied. The backup mechanism may be as simple as creating `CLAUDE.md.bak` adjacent to the original.

**Skill structure conventions**

- R10. Match the section conventions used by the existing skills (`<objective>`, `<overview>`, `<methodology>` or equivalent, `<examples>`, `<success_criteria>`) so the new skill is structurally consistent with `automap`, `epublisher`, etc.

---

## Acceptance Examples

- AE1. **Covers R1, R2, R10.** Given the new `claude-md-audit/SKILL.md` file, when an agent or user lists the plugin's skills, then `claude-md-audit` appears alongside the other four skills with a description that mentions auditing/reducing `CLAUDE.md` or agent MD files. Loading the skill produces sections that match the conventions of neighboring skills.
- AE2. **Covers R3, R4, R5.** Given a user asking the agent to audit an arbitrary `CLAUDE.md`, when the agent invokes the skill, then it categorizes each section as KEEP / REMOVE / REDUCE, applies the Pink Elephant Test, applies the Staleness Test, and produces a reduction proposal — without needing to ask the user how the methodology works.
- AE3. **Covers R6, R8.** Given a 180-line `CLAUDE.md` similar in shape to the pre-reduction ePublisher file, when the methodology is applied, then the resulting file is under 60 lines, uses the four-section structure (omitting empty sections), and every remaining line either documents an environment gotcha, a stable tool path, a behavioral rule, or a build command with a link.
- AE4. **Covers R7.** Given a reader skimming the skill for the first time, when they reach the examples section, then they can see at least four before/after pairs and understand from the examples alone why each REMOVE example was removed (discoverable from code) and why each KEEP example was kept (real failure mode without it).
- AE5. **Covers R9.** Given a user who asks the agent to reduce their `CLAUDE.md` and then realizes they removed something they wanted to keep, when they look in the same directory, then a backup of the pre-reduction file is present and they can restore from it without rerunning the workflow.

---

## Success Criteria

- A team member can run "audit my CLAUDE.md" against any repository the team maintains and get a reduction proposal whose decisions they can defend with the skill's methodology rather than aesthetic judgment.
- The team's `CLAUDE.md` files converge over time toward the under-60-line target without anyone having to remember the underlying research or the four section names.
- A reader landing on the skill for the first time can apply the methodology to a new repo's `CLAUDE.md` without reading the original research paper or the YouTube video — the skill itself is the authoritative reference.
- The skill survives the methodology applied to itself: it does not duplicate information that the example skills (`automap`, `epublisher`) already make discoverable through their own structure.

---

## Scope Boundaries

- **Not applying the methodology to this repository's own `CLAUDE.md` in the same change.** That is a follow-up application of the skill, not part of building it. The repo's current `CLAUDE.md` is 60 lines — under the target — and is not in the same category of accumulated noise as the ePublisher example.
- **Not generalizing to README.md, CONTRIBUTING.md, or other documentation.** Those serve human onboarding, which has different criteria. The skill is specifically about agent context files.
- **Not building an auto-runner, lint rule, pre-commit hook, or CI check.** The skill is invoked by a human or agent decision; it does not run on every commit.
- **Not enforcing a hard line limit.** The under-60-lines target in the skill is a guideline informed by the ePublisher reduction; it is not a fail criterion.
- **Not adding helper scripts under the skill directory (no `audit.py`, no `reduce.sh`).** The methodology is prose and decision rules, not automation, in line with how `epublisher` and `markdown-integration` are structured.
- **Not modifying the plugin's `plugin.json` or `marketplace.json` unless verification shows skills are individually registered there.** The four existing skills in the plugin are discovered by directory presence; the new skill should follow the same pattern. (See Outstanding Questions.)
- **Not bumping the plugin version in the same change as the brainstorm artifact.** Version bump happens at PR time per `CLAUDE.md` instructions.

---

## Key Decisions

- **Home the skill in `webworks-claude-skills` despite its domain neutrality.** The issue explicitly names this path. The plugin already hosts non-WebWorks-specific tooling concerns (e.g., markdown integration cuts across products), and splitting domain-neutral skills into a separate plugin is a larger structural decision than this issue should drive.
- **Trigger the skill on multiple agent MD names, not just `CLAUDE.md`.** Per the issue body's repeated "(or agent MD)" qualifier and the broader move in the ecosystem toward `AGENTS.md` as a vendor-neutral alternative. The skill's *content* uses `CLAUDE.md` as the canonical example for clarity, but the description triggers on the general concept.
- **Require a backup before reduction, not after.** Reduction is destructive in spirit even when reversible via git — the backup is the simplest, most legible safety net and removes any concern about working in a dirty tree or off a feature branch.
- **Keep the methodology prose-only, no scripts.** Two of the four existing skills (`epublisher`, `markdown-integration`) are reference-and-decision-tree shaped; adding code here would create an asymmetry that has to be justified, and the methodology is fundamentally judgment-based, not algorithmic.
- **Adopt the issue's proposed SKILL.md body as the working draft.** The issue body contains a near-complete proposed file; planning should use it as the baseline and adjust for structural alignment with neighboring skills rather than starting from scratch.
- **Defer "register in plugin manifest" to verification.** The acceptance criteria say "Registered in the plugin manifest" but the current plugin discovers skills by directory presence; no per-skill registration exists for the four current skills. Planning verifies the discovery mechanism and either confirms no registration is needed or adjusts both `plugin.json` and `marketplace.json` consistently.

---

## Dependencies / Assumptions

- The `blocked-by: #40` directive in the issue refers to PR #40 / issue #40 (diffable HTML output configuration), which is merged (see `git log`: commit `c066938` and `4ffc813` on 2026-05-19). Verified at brainstorm time.
- The four existing skills in `plugins/webworks-claude-skills/skills/` are discovered by directory presence: neither `plugin.json` nor `marketplace.json` enumerates them. Verified by reading both manifest files. Planning re-verifies before making any manifest changes.
- The skill body's research claims (3% completion decrease for LLM-generated files, 4% improvement for developer-written files, 20%+ cost increase) come from the source video the issue cites. Planning treats those numbers as user-attested and reproduces them as in the issue rather than re-deriving them.
- The current repo's `CLAUDE.md` is 60 lines and is in good shape; this brainstorm does not propose applying the skill to it. Verified by counting lines (60) and reading the file.
- The under-60-lines target is informed by the ePublisher reduction (180 → 49). Other repos may reasonably end up smaller or larger; the number is a guideline, not a contract.
- The four-section structure (Environment / Build Commands / Behavioral Rules / Configuration) is asserted as a useful default by the issue body. Planning may adjust the section names if the example pre-reduction content suggests a better split, but the count and shape of sections stay close to the issue's proposal.

---

## Outstanding Questions

### Resolvable at planning time

- [Affects R1, AE1] [Verification] Confirm by reading the four existing skill directories that no per-skill registration exists in `plugin.json` or `marketplace.json`. If confirmed, the acceptance criterion "Registered in the plugin manifest" requires no manifest changes — only the new skill directory and `SKILL.md`. Capture the verification result in the implementation PR.
- [Affects R10] [Technical] Decide whether to keep the issue body's section names (`<objective>`, `<overview>`, `<methodology>`, `<examples>`, `<success_criteria>`) or harmonize them with the exact section names used by `automap/SKILL.md` and `epublisher/SKILL.md`. Planning reads both example skills and picks the structurally-closer option.
- [Affects R9] [Technical] Decide the backup mechanism — `CLAUDE.md.bak` next to the original, a timestamped backup under `.claude-md-audit-backups/`, or instructions to verify the file is committed to git first. Planning picks the option that adds the least clutter to the user's tree.
- [Affects R7] [Editorial] Decide whether the before/after examples use the issue body's existing examples verbatim (Architecture Overview, Key Technologies, Environment gotcha, Localization rule, Debug Builds) or substitute domain-neutral examples that do not name SVN, NSIS, or `Python27`. The issue body's examples are more concrete; planning weighs concreteness against the risk that ePublisher-specific examples look out of place in a domain-neutral skill.

### Genuinely uncertain — record as assumption

- [Affects R3, R6] [Open] Whether the four-section structure (Environment / Build Commands / Behavioral Rules / Configuration) is the right durable shape or whether a real audit of multiple `CLAUDE.md` files would surface a fifth section (e.g., "Workflow pointers" or "Slash commands"). This brainstorm assumes four sections per the issue; the first real application of the skill to a second repo may suggest an addition. Recorded as an explicit assumption in the skill text so a future maintainer knows the shape is empirical, not derived from first principles.
