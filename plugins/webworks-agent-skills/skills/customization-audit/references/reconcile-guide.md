# Reconcile Guide (Phase 2 — applying the audit)

`reconcile` turns the audit findings into action: it removes noise, merges upstream changes into customized overrides, writes side-by-side artifacts where it cannot safely merge, and re-points the locked `FormatVersion`. It is the only command that writes.

```bash
# Preview (default — writes nothing):
python audit-overrides.py reconcile --project "C:\proj\my.wep" --to-version 2025.1

# Execute (backs up first):
python audit-overrides.py reconcile --project "C:\proj\my.wep" --to-version 2025.1 --apply
```

## Safety model

- **Dry-run by default.** Without `--apply`, `reconcile` prints the full action plan (real merge/conflict counts, computed via `git merge-file`) and writes nothing.
- **`--apply` backs up first.** Every file it will change or delete — and the project file — is copied to `--backup-dir` (default `<project>/.reconcile-backup-<to-version>`) before any write, and a `reconcile-manifest.json` records every action with its backup path. The whole operation is recoverable by restoring from that directory.
- **Aggressive is safe.** Migration step 1 is a baseline commit or folder copy, so even without the tool's backup the original is recoverable. Encourage users to commit/copy first, then let `reconcile` clear the noise.

## Verdict → action mapping

| Source finding | Action |
|----------------|--------|
| `cleanup`: retired-format / orphan (scope) | **delete the directory** |
| `cleanup`: duplicate-backup (cruft) | **delete the file** |
| `redundant` (cleanup or drift) | **delete the override** (patch fixed upstream) |
| `drift`: `fast-forward` | **delete the override** so it resolves to the new baseline |
| `drift`: `in-sync` | carry forward unchanged (no action) |
| `drift`: `auto-mergeable` | **3-way merge** — apply upstream changes, keep customizations |
| `drift`: `manual-merge` (or a merge that conflicts) | **side-by-side artifacts** for human resolution |
| the upgrade itself | **re-point the locked `FormatVersion`** to `--to-version` |

Files inside a directory slated for deletion, and overrides in retired formats, are skipped (the directory removal covers them). Disable categories with `--skip-removals`, `--skip-merge`, `--skip-lock-bump`.

## The 3-way merge engine

`reconcile` uses `git merge-file -p --diff3` (no git repository required — it operates on standalone files). The three inputs are:

- **mine** — the override.
- **base** — the fork-point baseline (`--from-version`, default the project's locked `FormatVersion`).
- **new** — the upgrade target (`--to-version`).

**Line endings are normalized to LF before merging.** A CRLF override against an LF baseline would otherwise make every line a conflict. Merged output is written back as LF.

**`git merge-file` is authoritative.** A divergence classified `auto-mergeable` by the line-interval heuristic but that `git merge-file` reports as conflicting is **downgraded to conflict artifacts** — `reconcile` never silently overwrites a customization.

> For a stale project (overrides forked well before the lock — see `discover` staleness depth), pass `--from-version <discovered-fork-point>` for a cleaner merge. Using the lock as the base inflates the "customization" diff with the un-received changes between the fork-point and the lock, producing more conflicts.

## Conflict artifacts

When a merge cannot be applied cleanly, the override is **left untouched** and four files are written beside it:

```
Footer.asp                       # original override — unchanged
Footer.asp.reconcile-base        # fork-point baseline
Footer.asp.reconcile-mine        # the override (normalized)
Footer.asp.reconcile-new         # upgrade-target baseline
Footer.asp.reconcile-merged      # 3-way merge with <<<<<<< / ||||||| / >>>>>>> markers
```

Resolve by editing `Footer.asp` using `.reconcile-merged` as a guide (or diffing `.mine` vs `.new`), then delete the four `.reconcile-*` files. `reconcile` lists every file needing manual resolution at the end of an apply run.

## Undo

Restore from the backup directory: copy each `backup` path in `reconcile-manifest.json` back to its `target`, re-create deleted directories from their backups, and (for `repoint-lock`) restore the backed-up project file. Then remove any `.reconcile-*` artifacts.

## Worked example (continuing the 2024.1 → 2025.1 customer upgrade)

`reconcile --to-version 2025.1 --apply` on the before-project produced 47 actions: 9 directory deletions (retired WWHelp 5.0 + Reverb 1.x targets/format), 17 file deletions (cruft + redundant + fast-forward drops), 4 clean 3-way merges (including `locales.xml` — the post-release CJK-search fix merged cleanly with the custom stopwords/synonyms), 16 conflict-artifact sets (the heavily customized Reverb templates), and the `FormatVersion` re-point to 2025.1 — taking the override surface from 144 files toward the reconciled set, with a full backup + manifest for undo.
