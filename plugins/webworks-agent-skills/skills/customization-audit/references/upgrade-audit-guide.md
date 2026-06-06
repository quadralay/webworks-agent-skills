# Upgrade Audit Guide

End-to-end workflow for auditing a project's advanced customizations (overrides) on upgrade, with a worked example from a real customer upgrade.

All commands are `python scripts/audit-overrides.py <command> --project <path.wep>`. The audit is **report-only** — it never writes to the project.

## When to run this

- Before or after bumping a project's ePublisher version.
- When inheriting a customized project of unknown provenance.
- When an override "isn't taking effect" or output looks wrong after an upgrade.
- Periodically, to keep the override surface lean.

## Recommended sequence

Prune first, then analyze what survives — there is no point computing drift for files you are about to delete.

```
enumerate   ->   cleanup   ->   discover   ->   audit   ->   drift
(inventory)     (prune)        (baseline)      (health)     (plan merge)
```

### 1. `enumerate` — inventory and classify

Establishes the lock state, resolves every target to its format, and classifies each override as **forked-copy** (has a baseline counterpart) or **net-new**.

```bash
python audit-overrides.py enumerate --project "C:\proj\my.wep"
```

Read the header first: `lock=tracking|locked`, the base format version, and whether that baseline is on disk. A `locked` project will not auto-upgrade; a missing baseline means Mode B (see `known-vs-unknown-baseline.md`).

### 2. `cleanup` — remove the noise

Recommends removals in four categories: **retired-format**, **orphan-target/format**, **duplicate-backup** (cruft), **redundant-override**. Aggressive by design — migration step 1 is a baseline commit/copy, so anything removed is recoverable.

```bash
python audit-overrides.py cleanup --project "C:\proj\my.wep"
```

Act on the high-confidence removals before continuing; they shrink everything downstream.

### 3. `discover` — establish the fork-point baseline

Fingerprints each forked override against every installed version and reports a **per-format** fork-point plus **staleness depth** (how many releases behind the project's lock the overrides actually derive from). Retired formats are marked and skipped.

```bash
python audit-overrides.py discover --project "C:\proj\my.wep"
```

Use this to (a) confirm the baseline in Mode B, and (b) spot formats whose overrides were never re-synced to their own lock.

### 4. `audit` — health check

2-way diff of each forked override against the resolved baseline, plus the three customization signals and the SCSS missing-variable, partial-wiring, and dangling-reference checks.

```bash
python audit-overrides.py audit --project "C:\proj\my.wep"
```

Watch for: `POSITIVE DRIFT suspect` (large baseline-only delta), `UNANNOTATED` override changes (run `discover` to recover intent), `BUILD-BREAK RISK` (missing SCSS variable), `INCOMPLETE TEMPLATE` (custom partial not imported), and `NEGATIVE DRIFT` (dangling reference).

### 5. `drift` — plan the reconciliation

3-way classifier: fork-point/lock (`--from-version`) → upgrade target (`--to-version`) → override. Assigns each surviving forked override a verdict.

```bash
python audit-overrides.py drift --project "C:\proj\my.wep" --to-version 2025.1
```

| Verdict | Meaning | Action |
|---------|---------|--------|
| `in-sync` | Baseline unchanged between versions | Carry the override forward as-is |
| `fast-forward` | Override is an unmodified copy; baseline changed | Adopt the new baseline (or drop the override) |
| `auto-mergeable` | Customizations and upstream changes touch disjoint regions | Copy new baseline, re-apply customizations |
| `manual-merge` | Customized regions also changed upstream | Hand-merge and re-test |
| `redundant` | Identical to baseline, no upstream change | Remove |

## Worked example — a real 2024.1 → 2025.1 upgrade

A customer project running on the 2026.1 runtime but **locked** to `FormatVersion="2024.1"`, being moved to `2025.1`. Both 2024.1 and 2025.1 base formats were installed (Mode A). The override tree spanned **5 formats** and **12 targets** — 144 override files.

**`enumerate`** reported `lock=locked, base=2024.1`, resolved all 12 targets to their formats (including the subtlety that one test target used the retired Reverb 1.x while others used Reverb 2.0), and classified 65 forked-copy / 79 net-new. The inflated net-new count was the first cruft signal.

**`cleanup`** recommended removing **111 of 144** files:
- 9 scopes as **retired-format** (94 files): the entire WebWorks Help 5.0 format and every target bound to it, plus the Reverb 1.x test target.
- 11 **duplicate-backup** files: `*_orig.*`, `*_with_version.*`, `Good_*`, date-stamped pages, `_old` images, alternate splash variants — each an unreferenced duplicate of an existing override.
- 6 **redundant-override** files identical to the 2024.1 baseline.

This matched the customer's own manual reconciliation (they pruned 144 → 24) almost exactly. The only divergences were appropriate: the tool did **not** auto-remove a valid Reverb 2.0 target the customer chose to retire as a business decision (it flagged only that target's cruft), and it flagged one extra dated splash variant the customer had conservatively kept.

**`discover`** showed the per-format truth that a single project-wide number would have hidden:
- `Shared` — fork-point 2024.1, **current** (matches lock).
- `WebWorks Reverb 2.0` — fork-point ~2019.1, **6 releases behind** the 2024.1 lock: the overrides were never re-synced when the lock was bumped (low confidence, because heavy customization skews the match — reported honestly).
- `PDF - XSL-FO` — fork-point ~2021.1, 3 behind.
- The two retired formats — marked RETIRED, no fork-point.

**`audit`** surfaced the `locales.xml` story: heavy upstream change (a post-release CJK-search bugfix and new strings) plus substantial custom stopwords/synonyms — auto-mergeable because they sit in disjoint regions.

**`drift --to-version 2025.1`** classified the survivors: `PDF Body.asp` **in-sync** (no upstream change), `locales.xml` **auto-mergeable**, `uilocales.xml` **fast-forward** (unmodified copy), several Reverb 2.0 templates **manual-merge**, and `Unsupported_Browser.asp` flagged **dropped upstream** (removed in 2025.1). The handful of manual-merges on the surviving target was the entire real reconciliation workload — exactly what the customer hand-merged.

**Takeaway:** prune aggressively first (`cleanup` removed ~77% of the surface), then the drift work that remains is small and well-scoped (`drift` named the few files needing a hand-merge).
