---
title: Vendor third-party skills in-tree when ecosystem-specific divergence is planned
date: 2026-05-22
category: tooling-decisions
module: plugin-dependency-management
problem_type: tooling_decision
component: tooling
severity: medium
applies_when:
  - "A plugin consumes a third-party skill from an upstream repository whose maintainers do not share your audience or scope"
  - "You have evidence — not speculation — that the upstream behavior diverges from what your ecosystem needs"
  - "Planned divergence will land as ongoing rule, profile, or behavior changes, not a one-time tweak"
  - "Upstream is permissively licensed (MIT, BSD, Apache-2.0) so an in-tree copy is unconditionally clean"
related_components:
  - documentation
  - development_workflow
tags:
  - plugin-architecture
  - dependency-management
  - vendoring
  - git-submodules
  - upstream-divergence
  - third-party-skills
  - humanizer
---

# Vendor third-party skills in-tree when ecosystem-specific divergence is planned

## Context

`webworks-agent-skills` had been consuming the `humanizer` skill as a Git submodule of `blader/humanizer` at `plugins/humanizer/skills/humanizer/`. The submodule pointer kept the wrapper repo close to upstream by default, which was the right posture while we were still evaluating whether the skill fit our use cases.

A worked-example humanizer pass on a Markdown++ best-practices reference document produced roughly two genuine improvements per minor regression. The pattern was consistent: rules targeting vagueness, filler, promotional language, and anthropomorphization helped agent-readable content; rules targeting punctuation density, structural parallelism, length, and rhythm variation hurt it by stripping precision wording that was doing specification-grade work. That worked example was the first hard evidence that the skill needed audience-aware behavior — a per-rule profile decision specific to the WebWorks plugin ecosystem and out of scope for the general-purpose upstream.

At that point, three options were on the table: stay on the submodule and patch behavior in a wrapper layer, fork the repo on GitHub and point the submodule at the fork, or vendor the working tree in-tree as plain files. Issue #93 chose vendoring.

## Guidance

When a third-party skill is going to diverge from upstream in ways that are ongoing rather than one-off, vendor the working tree in-tree as plain files rather than keeping a submodule or pointing a submodule at a GitHub fork.

Use the following criteria to choose between the three options:

**Vendor in-tree when all of these are true:**

1. You have a concrete worked example — not speculation — showing upstream behavior diverges from what your ecosystem needs.
2. The planned divergence is ongoing (new rules, audience profiles, ecosystem-specific logic) and will land as multiple changes over time, not a single patch.
3. The upstream scope explicitly excludes your divergence (different target audience, different consumer profile) so contributing back is not a realistic path.
4. Upstream is permissively licensed (MIT, BSD, Apache-2.0) so an in-tree copy is unconditionally clean.
5. You accept the maintenance posture of pulling future upstream improvements by hand rather than tracking them automatically.

**Keep the submodule (or use a GitHub fork pointed-to by submodule) when any of these are true:**

- You are still evaluating whether the skill fits and have not committed to divergence.
- Divergence would be a small, well-bounded patch rather than ongoing audience-specific logic.
- You expect to contribute changes back to upstream and want to keep the merge path open.
- Upstream is on a license that constrains redistribution of in-tree copies (uncommon for skills, but possible).

**Why vendoring beats a GitHub fork in this scenario specifically:**

- **Visibility of divergence.** Vendored changes live in the same repo as the rest of the consumer code, reviewable in normal PRs against the consumer repo's main branch. Submodule pointer bumps hide the actual diff in the wrapper repo, so reviewers see "humanizer SHA changed from X to Y" with no context.
- **No accidental sync regression.** A fork stays close to upstream by default — a periodic `git pull upstream main` will silently reintroduce the rules the consumer ecosystem deliberately removed. Vendoring forces a deliberate manual port when an upstream change is worth pulling, which matches the actual maintenance posture (consumer will not be tracking upstream closely).
- **Simpler plugin lifecycle.** The plugin directory becomes a normal first-party plugin alongside the rest, removing a submodule-init step for new contributors. A `git clone` is sufficient; no `git submodule update --init --recursive` is required.

## Why This Matters

Submodule wrappers and forks both encode an unspoken assumption: that the consumer is mostly aligned with upstream and only occasionally needs to deviate. When that assumption is wrong — when the consumer's audience is genuinely different and divergence will be active — those mechanisms generate ongoing friction:

- **Submodule pointer bumps** that hide the actual diff make reviewers approve changes without seeing them, which lets behavior drift land without scrutiny.
- **Forks that track upstream** will reintroduce the rules you removed every time you sync, unless you build (and remember to apply) a rebase or rewrite workflow on top.
- **Contributor friction** from the submodule init step pays off only if the submodule pointer rarely changes; if you are touching the vendored content regularly, the init step is a tax on every fresh clone with no compensating benefit.

Vendoring makes the cost of divergence visible up front (the full vendored copy lands in one commit, with explicit attribution and a port-process document) and amortizes the maintenance cost across ordinary PR review of normal in-tree files.

The hidden cost: when upstream ships a high-value change, porting requires manual review against your ecosystem's profile criteria. That is the trade-off the maintenance posture accepts. An `UPSTREAM.md` file tracking the last imported commit and divergence rationale makes the manual port feasible without re-deriving the context each time.

## When to Apply

- A plugin consumes a third-party skill (or any vendored content) and your ecosystem has audience requirements upstream does not share.
- A worked-example pass on real content has surfaced divergence that is both substantial and patterned — not isolated.
- The planned divergence is at the rule, profile, or behavior level, not a one-line config tweak.
- Upstream license permits redistribution of an in-tree copy.

Do **not** apply this guidance when divergence is speculative, one-off, or contributable upstream — those are submodule or upstream-contribution cases, not vendoring cases.

## Examples

**Vendoring layout used for the `humanizer` plugin:**

```
plugins/humanizer/
├── .claude-plugin/plugin.json   # Plugin wrapper, owned by this repo
├── README.md                    # Vendoring decision and divergence plan
└── skills/humanizer/
    ├── SKILL.md                 # Vendored unchanged from upstream
    ├── LICENSE                  # MIT, preserved unchanged
    ├── README.md                # Vendored unchanged
    └── UPSTREAM.md              # Source URL, last sync SHA, port process
```

`UPSTREAM.md` records the four facts a future maintainer needs to do a port:

- **Source**: upstream repo URL.
- **Last sync commit**: SHA at the time of import (`12881abf6671c4ab62eceeb56f911b752f9fd6d2` for the initial humanizer import).
- **Reason for divergence**: one paragraph stating what is out of scope upstream and why.
- **Process for future manual ports**: explicit steps — compare `git log <last-sync-sha>..HEAD`, evaluate each candidate against ecosystem profile criteria, apply as a normal PR, update the sync SHA.

**Detach procedure used to replace the submodule with vendored files:**

1. Back up the upstream working tree contents.
2. Remove the entry from `.gitmodules` (delete the file entirely if no other submodules remain).
3. `git submodule deinit -- <path>` and `git rm --cached <path>` to detach the submodule pointer.
4. Clear any leftover state under `.git/modules/<path>/` (in a worktree setup, this lives under the common gitdir, not the worktree's `.git` file).
5. Copy the backed-up upstream tree back into the directory as plain files.
6. Verify each vendored file is byte-identical to the backup (`diff -q` per file).
7. Add `UPSTREAM.md` with the sync metadata.
8. Confirm `LICENSE` and attribution sections in the vendored files are preserved unchanged.

**Plugin-version bump rationale.** Vendoring is a refactor with no behavior change, so a `patch` bump on the plugin version is the correct semver step. The behavioral divergence work that follows — audience-aware logic, dual-rule profiles — is what justifies a minor or major bump on the vendored plugin's own version, independent of the main plugin's bump cadence. Document this clearly in the contributor guide so the manual-bump rule for vendored plugins is discoverable.

## Related

- Issue #93 — initial vendoring of the `humanizer` skill (this learning's source).
- `plugins/humanizer/README.md` — vendoring decision and divergence plan, in-plugin.
- `plugins/humanizer/skills/humanizer/UPSTREAM.md` — sync metadata and port process for this specific vendored copy.
- `CONTRIBUTING.md` — "Vendored Plugins" section, contributor-facing edit and port guidance.
- `docs/solutions/architecture-patterns/format-spec-vs-integration-skill-separation-2026-05-09.md` — related decision about when to split a bundled skill into two repos (different question: same-repo vs separate-repo upstream-owned content).
