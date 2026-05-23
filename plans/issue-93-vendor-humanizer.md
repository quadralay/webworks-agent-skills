# Issue #93 — Vendor humanizer plugin and detach the upstream submodule

**Status:** Planned
**Issue:** [#93](https://github.com/quadralay/webworks-agent-skills/issues/93)
**Workflow:** `builder-auto`

## Goal

Detach `plugins/humanizer/skills/humanizer/` from the `blader/humanizer` git submodule and absorb its contents as a plain vendored copy in this repo. Behavior is unchanged in this phase — this is a refactor that unlocks the audience-aware skill-file work tracked in follow-up issues.

## Why vendor (and not fork)

The issue describes the decision in full. Summary for this plan:

- **Visibility of divergence.** Future skill-file behavior changes will diff cleanly against the vendored copy in normal PRs against `main`. A submodule pointer bump would hide the real diff.
- **No accidental sync regression.** A fork stays close to upstream by default. Vendoring forces deliberate manual ports, matching the actual maintenance posture (no close upstream tracking).
- **Simpler plugin lifecycle.** `plugins/humanizer/` becomes a normal first-party plugin alongside the rest, removing a submodule-init step for new contributors.

Trade-off: when upstream ships a new high-value rule, porting requires manual review. `UPSTREAM.md` (described below) records the last sync commit and divergence so a future port is tractable.

## Current state (verified)

- `.gitmodules` contains a single submodule entry pointing `plugins/humanizer/skills/humanizer` at `https://github.com/blader/humanizer.git`.
- `git submodule status` reports the submodule as uninitialized in this worktree (`-` prefix). The submodule SHA recorded in the index is `12881abf6671c4ab62eceeb56f911b752f9fd6d2`.
- The submodule working tree is empty in this worktree (`plugins/humanizer/skills/humanizer/` exists as a directory but contains no files).
- `plugins/humanizer/.claude-plugin/plugin.json` wraps the submodule — name `humanizer`, version `2.3.0`, author `blader`, MIT license. No path changes needed; the relative skill path stays the same.
- `.claude-plugin/marketplace.json` references the plugin via `./plugins/humanizer` — no change needed.
- `CONTRIBUTING.md` contains a "Git Submodules" section (lines 22 to 110 reference the submodule). Needs rewriting to describe the vendored model.
- `README.md` line 31 calls humanizer a `[submodule]` — needs an update to point at `UPSTREAM.md` (or equivalent) instead.

## Implementation phases

Each phase is a self-contained commit. Run them in order on the existing branch `claude/issue-93`.

### Phase 1 — Initialize submodule and capture the import SHA

The submodule is currently uninitialized in this worktree. Before detaching, we need the upstream tree on disk so we can copy it. This phase produces no committed changes — it just stages the working tree for Phase 2.

1. `git submodule update --init --recursive plugins/humanizer/skills/humanizer`
2. Record `git -C plugins/humanizer/skills/humanizer rev-parse HEAD` — this is the SHA that `UPSTREAM.md` will reference. Expected to match `12881abf6671c4ab62eceeb56f911b752f9fd6d2` from the index; if it differs (upstream advanced after the gitlink was last bumped), note the actual SHA fetched.
3. Verify the upstream `LICENSE` file is present at `plugins/humanizer/skills/humanizer/LICENSE` and is MIT.

If `git submodule update` fails (network, upstream gone), stop and surface the error — the vendoring cannot proceed without the upstream contents.

### Phase 2 — Detach the submodule

1. Edit `.gitmodules`: remove the `[submodule "plugins/humanizer/skills/humanizer"]` block. If that was the only entry, the file is now empty — delete it rather than leaving a zero-byte file in tree.
2. `git submodule deinit -f -- plugins/humanizer/skills/humanizer` to drop the submodule's `.git/config` entry.
3. **Stash the upstream working-tree contents** outside the worktree before the next step (e.g., copy to a temp directory). `git rm --cached` followed by re-copying is cleaner than trying to keep files in place while changing their git state.
4. `git rm --cached plugins/humanizer/skills/humanizer` to remove the gitlink from the index. Confirm `git status` shows the submodule entry deleted and `.gitmodules` modified.
5. Remove the now-stale gitdir: `rm -rf .git/modules/plugins/humanizer/skills/humanizer` (the worktree's `.git` is a file pointer; resolve it first — the actual git directory lives in the main repo at `C:/Users/mcdow/AppData/Local/claude-windows-worker/workdir/repos/quadralay-webworks-agent-skills/.git/modules/plugins/humanizer/skills/humanizer`). If the path does not exist, this is a no-op — fine, no error.
6. Re-create `plugins/humanizer/skills/humanizer/` as a plain directory and copy the stashed upstream working-tree contents back into it. Preserve file modes (executable bits on any scripts). Do not include the upstream `.git` directory.
7. Verify with `git status` that the path is now untracked-as-files, not as a submodule.

**Commit:** `chore(humanizer): detach upstream submodule and vendor contents`

### Phase 3 — Add divergence documentation

1. Create `plugins/humanizer/skills/humanizer/UPSTREAM.md` with the following fields, populated from Phase 1:
   - **Source:** `https://github.com/blader/humanizer`
   - **Last sync commit:** the SHA captured in Phase 1
   - **Last sync date:** the date of this phase (today, 2026-05-22 if completed today)
   - **License:** MIT (upstream `LICENSE` preserved unchanged at `plugins/humanizer/skills/humanizer/LICENSE`)
   - **Reason for divergence:** skill-file auto-detection and dual-audience rule profiles, both out of scope for the upstream project (which targets general-purpose human-audience humanization).
   - **Process for future manual ports:** review upstream commits since the recorded SHA, evaluate each new rule against the WebWorks profile criteria (does it help or hurt skill-file utility?), port selectively, update this file with the new SHA on each port.
2. Confirm `plugins/humanizer/skills/humanizer/LICENSE` is present, unchanged from upstream, and not edited.
3. Confirm the upstream attribution in `SKILL.md` (Wikipedia citation and WikiProject AI Cleanup credit) is preserved verbatim — the vendoring step should not have touched it, but verify.

**Commit:** `docs(humanizer): add UPSTREAM.md tracking vendored source SHA`

### Phase 4 — Update repo-level documentation

1. **`README.md`** — change line 31 (`humanizer` row in the Skills table) to drop the "[submodule]" language and replace the link with one to `UPSTREAM.md`. Keep the description compact; the divergence rationale belongs in `UPSTREAM.md`, not in the top-level README.
2. **`CONTRIBUTING.md`** — rewrite the "Git Submodules" section (currently lines 83 to 110) and the "Note:" callout at line 71. The new content should:
   - Remove the `git submodule update`, `git submodule set-url`, and submodule-clone instructions.
   - Add a brief "Vendored plugins" section describing the humanizer-vendor model: the skill is owned in-tree, upstream is tracked manually via `UPSTREAM.md`, and porting upstream changes is a deliberate manual review per [plugins/humanizer/skills/humanizer/UPSTREAM.md](plugins/humanizer/skills/humanizer/UPSTREAM.md).
   - Keep the version-script callout but rephrase: the humanizer version in `plugin.json` is owned by this repo now, not upstream — it can be bumped by the standard `scripts/bump-version.sh` flow when behavior diverges from `2.3.0`.
3. **`plugins/humanizer/README.md`** — create this file. Short — describe what the plugin does, that it was vendored from `blader/humanizer` (link), point at `UPSTREAM.md` for sync state, and note the planned divergence (skill-file auto-detection, dual-audience profiles) at a one-paragraph level. Do not duplicate `SKILL.md`.
4. **`plugins/humanizer/.claude-plugin/plugin.json`** — leave untouched in this issue. The `author`, `homepage`, and `repository` fields still legitimately credit `blader/humanizer` as the source. When behavior diverges in a follow-up issue, those fields can be revisited.

**Commit:** `docs: describe vendored humanizer model in README and CONTRIBUTING`

## Verification

After all phases, run these checks before declaring done:

- `git submodule status` returns no entries for `humanizer`.
- `cat .gitmodules` returns "No such file or directory" (or the file is empty and we deleted it).
- `ls plugins/humanizer/skills/humanizer/` shows plain files including `SKILL.md`, `LICENSE`, and `UPSTREAM.md`.
- `git ls-files plugins/humanizer/skills/humanizer/ | head` shows real file paths, not a gitlink entry.
- A fresh `git clone` of this branch (in a scratch directory) yields the humanizer skill files without needing `git submodule init`.
- `Grep` for `submodule` across the repo returns no references to the humanizer path. CONTRIBUTING.md may still mention submodules historically but should not instruct contributors to manage one for humanizer.
- The humanizer skill itself loads and behaves identically to its pre-vendor behavior (smoke-test by invoking it via the Skill tool on a small sample).

## Success criteria (from the issue)

- `plugins/humanizer/skills/humanizer/` is a plain directory, not a submodule. `.gitmodules` no longer contains a `humanizer` entry. ✅ (Phase 2)
- `LICENSE` (MIT) is present and unchanged. Attribution in `SKILL.md` preserved. ✅ (Phase 2 + Phase 3 verification)
- `UPSTREAM.md` documents source, last-sync SHA, divergence rationale, future-port process. ✅ (Phase 3)
- Top-level and plugin-level READMEs describe the vendoring decision. ✅ (Phase 4)
- Skill continues to function identically to its pre-vendor behavior. ✅ (Verification step)
- Follow-up issues for auto-detection and dual-audience profiles are filed and linked from this issue. **Out of scope for this PR** — that linking happens after the PR for this issue merges. Note in the PR description that those follow-ups remain to be filed.

## Risks and decisions

- **Worktree submodule state.** The submodule is uninitialized in this worktree but the upstream SHA is recorded in the index of the main repo. Phase 1's `git submodule update --init` is the correct way to populate it; abort if that fails rather than vendoring from a possibly-stale local copy elsewhere.
- **Upstream SHA drift.** If `blader/humanizer` HEAD has moved past `12881abf6671c4ab62eceeb56f911b752f9fd6d2`, `git submodule update --init` will fetch but check out the gitlinked SHA (not HEAD). Vendor what the gitlink points to, not what `main` points to — that is the version this repo has been using.
- **File mode preservation on Windows.** `git rm` then file-copy may lose executable bits if any scripts are present in the upstream. After Phase 2, spot-check any `.sh` or `.py` scripts in the vendored tree for executable bit (`git ls-files -s` shows mode `100755` for executable). The upstream skill is mostly markdown, so this is unlikely to bite.
- **Version bump.** Per `CLAUDE.md`, PRs bump the plugin version via `scripts/bump-version.sh`. This change is a refactor with no user-visible behavior change — `patch` is appropriate. Do not bump the humanizer plugin's own version (`2.3.0` in `plugins/humanizer/.claude-plugin/plugin.json`) — that is reserved for behavior changes in a later issue.

## Out of scope

- Skill-file auto-detection logic (follow-up issue).
- Dual-audience rule profiles (follow-up issue).
- Changes to the humanizer rules themselves.
- Renaming the plugin or skill.
- Changing the plugin author/homepage/repository fields in `plugin.json` — those still legitimately credit upstream.
