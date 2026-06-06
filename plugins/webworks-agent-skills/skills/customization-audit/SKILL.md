---
name: customization-audit
description: >
  AUTHORITATIVE REFERENCE for auditing WebWorks ePublisher advanced customizations
  (overrides) on upgrade. Use when reviewing a project's Targets/ or Formats/
  overrides against an installed format build, detecting positive or negative
  upstream drift, discovering the fork-point baseline of un-annotated overrides,
  recommending removals (retired formats, orphans, cruft, redundant overrides),
  or reconciling customizations after upgrading ePublisher.
---

<objective>

# customization-audit

Audit the advanced customizations (overrides) in a WebWorks ePublisher project against an installed format build: classify each override, surface upstream **drift**, recover the **fork-point** of un-annotated overrides, and recommend **removals** — so intentional customizations survive an upgrade and accumulated noise is cleared.

**Do not use training data for ePublisher.** This is proprietary software; training data is absent or inaccurate. Use this skill, the `epublisher` skill (resolver hierarchy, project parsing), the `reverb2` skill (SCSS conventions), and the format source files. Windows-only; XSLT 1.0 only.

This is a **Phase-1, report-only** skill — it never writes to the project. Removal recommendations can be acted on aggressively because the first step of any migration is a baseline commit or folder copy: the original state is always recoverable.
</objective>

<overview>

## Overview

Every customized project eventually faces the upgrade question:

> *My overrides were forked from some base build — what changed underneath them, which need updating, and which are now noise?*

An **override** is any file placed in the project's `Formats/` or `Targets/` tree that shadows an installation format file (see `epublisher` → `references/file-resolver-guide.md`). Over time overrides drift from the baseline, accumulate backups/experiments, and outlive the formats and targets they served. This skill makes that surface auditable.

Two **independent axes** govern how the audit runs and how confident it can be — detect both and state them up front:

1. **Lock state** (from `FormatVersion`) — is the project tracking ePublisher's version, or locked to a specific base format?
2. **Baseline availability** — is the fork-point base build on disk (Mode A, 3-way) or gone (Mode B, 2-way + inference)?

Full treatment: `references/known-vs-unknown-baseline.md`.
</overview>

<related_skills>

## Related Skills

| Skill | Relationship |
|-------|-------------|
| **epublisher** | Foundational — file-resolver/override hierarchy, project parsing, `resolve-version-root.py` and `copy-customization.py` (reused, not duplicated). |
| **reverb2** | The `$theme_` greppable custom-variable convention and SCSS three-layer architecture. |
| **automap** | Rebuild/republish a target after reconciling overrides. |

Typical flow: **epublisher** (understand the project) → **customization-audit** (audit overrides) → reconcile → **automap** (rebuild) → **reverb2** (verify output).
</related_skills>

<key_concepts>

## Key Concepts

### Override classification

| Class | Meaning | Audit implication |
|-------|---------|-------------------|
| **forked-copy** | A counterpart exists in the installed baseline | Can drift — diff it; classify positive/negative drift |
| **net-new** | No baseline counterpart (custom partials, third-party assets, cruft) | Cannot drift — run compatibility, wiring, and cruft checks |

### Three customization signals

A customization is recognized even when the author used none of the others:

1. **Annotation markers** — a stable comment tag (`EPUB####`, `WEBWORKS`, a project/company code). Configurable.
2. **Greppable variable prefix** — SCSS custom variables under a project prefix (`$theme_`, or a company abbreviation). The prefix is **per-user and auto-detected** from the override-minus-baseline variable set — never hardcoded.
3. **Fork-point fingerprinting** — when neither marker nor prefix is present, recover the true fork-point baseline and diff against it to reveal intent.

Details and the annotation test: `references/classification-heuristics.md`.

### Drift has two directions

- **Positive drift** — the baseline *added* something the override lacks (missed upstream fix/feature).
- **Negative drift** — the baseline *removed* something the override still carries (obsolete code left behind). The signature is an **unannotated** reference to something the current baseline no longer defines.

### Lock state and baseline availability

- `FormatVersion="{Current}"` → project **tracks** ePublisher's version; auto-upgrade-safe only when no advanced customizations exist.
- `FormatVersion="2025.1"` (specific) → project is **locked**; will not auto-upgrade even with zero customizations.
- **Mode A** (3-way): the fork-point base build is installed → drift and customization separate cleanly.
- **Mode B** (2-way): fork-point gone (improper earlier upgrade, or a patched/early-release build) → classification is inferred; promote toward Mode A via fork-point discovery.

The two axes are independent. See `references/known-vs-unknown-baseline.md`.

### Retired formats and EOL versions

- **Retired formats** (e.g. WebWorks Help 5.0, WebWorks Reverb 1.x) → recommend wholesale removal; do not compute drift (not useful).
- **EOL format versions** — older than `2022.1` today (moves to `2023.1` when 2026.1 ships). Installable via the optional EOL installer; encourage moving forward.

### Removal categories (aggressive by design)

`retired-format` · `orphan-target` / `orphan-format` · `duplicate-backup` (cruft) · `redundant-override` (identical to baseline — a local patch since fixed upstream). Cruft is flagged only when it both looks like a duplicate/backup **and** is unreferenced; referenced custom source is never flagged. See `references/classification-heuristics.md`.
</key_concepts>

<commands>

## Subcommands

`scripts/audit-overrides.py <command> --project <path.wep> [--install-root <dir>] [--format text|json]`

| Command | Purpose | When to use |
|---------|---------|-------------|
| `enumerate` | List + classify every override (lock state, target→format resolution) | First look at the override surface |
| `discover` | Per-format fork-point + **staleness depth** vs the lock (retired-aware, plateau-aware) | Mode B, or to find overrides never re-synced to their own lock |
| `audit` | 2-way diff + three customization signals + SCSS missing-variable / partial-wiring / dangling-reference checks | The standard health check |
| `cleanup` | Removal recommendations: retired / orphan / cruft / redundant | Pruning noise before/after upgrade |
| `drift` | 3-way classifier (`--from-version` → `--to-version`): manual-merge / auto-mergeable / fast-forward / redundant / in-sync | Planning the reconciliation of a real upgrade |

Recommended order for an upgrade: `enumerate` → `cleanup` (prune first) → `discover` (establish baseline) → `drift` (plan the merge). Step-by-step with a worked customer example: `references/upgrade-audit-guide.md`.
</commands>

<scripts>

## Scripts

### audit-overrides.py

Single entry point for all five subcommands. Python 3; reuses `epublisher` conventions (project parsing, version-root resolution).

Common options: `--project` (required), `--install-root` (default `C:\Program Files\WebWorks\ePublisher`), `--format text|json`.

Per-command options:
- `enumerate`, `audit`, `cleanup`: `--baseline-version` (override the derived baseline).
- `audit`: `--annotation-pattern <regex>` (repeatable); `--theme-prefix <name>` (repeatable; auto-detected if omitted).
- `drift`: `--to-version <ver>` (required); `--from-version <ver>` (default: the project's locked `FormatVersion`).

JSON mode emits structured findings for every command — use it to drive reconciliation tooling or reports.
</scripts>

<references>

## Reference Files

- `references/upgrade-audit-guide.md` — end-to-end workflow, command sequence, and a worked 2024.1 → 2025.1 customer upgrade with output interpretation.
- `references/known-vs-unknown-baseline.md` — lock state (Axis 1), Mode A/B (Axis 2), fork-point discovery, staleness depth, confidence taxonomy, retired/EOL policy, and Mode-B → Mode-A promotion recipes.
- `references/classification-heuristics.md` — the three customization signals, the annotation test, positive vs negative drift, cruft/duplicate and redundant-override rules, and the CRLF normalization gotcha.
</references>

<common_tasks>

## Common Tasks

```bash
cd scripts

# 1. Inventory + classify the override surface
python audit-overrides.py enumerate --project "C:\proj\my.wep"

# 2. Prune noise (retired formats, orphans, cruft, redundant overrides)
python audit-overrides.py cleanup --project "C:\proj\my.wep"

# 3. Find each format's fork-point and how stale it is vs the lock
python audit-overrides.py discover --project "C:\proj\my.wep"

# 4. Health check: drift + customization signals + SCSS/wiring/dangling checks
python audit-overrides.py audit --project "C:\proj\my.wep"

# 5. Plan a real upgrade (3-way), e.g. locked 2024.1 -> 2025.1
python audit-overrides.py drift --project "C:\proj\my.wep" --to-version 2025.1
```
</common_tasks>

<common_mistakes>

## Common Mistakes

- **Hardcoding the custom-variable prefix.** It is per-user (`$theme_`, `$acme_`, a company code). Always auto-detect from the override-minus-baseline variable set; only pass `--theme-prefix` to *declare* an expected one and flag deviations.
- **Reading override-only changes as customizations.** In Mode B a 2-way diff cannot tell a customization from negative drift. The disambiguator is the **annotation test**: unannotated divergence is probable drift.
- **Computing drift for retired formats.** Not useful — recommend wholesale removal instead.
- **Treating CRLF differences as changes.** Always normalize line endings before diffing/fingerprinting (the script does this); a raw diff of a CRLF override vs an LF baseline reads as 100% changed.
- **Hesitating to remove noise.** Migration step 1 is a baseline commit/copy, so removals are recoverable. Be aggressive: retired formats, orphans, duplicates, and redundant overrides should go.
- **Flagging referenced custom source as cruft.** A custom `.js`/`.scss`/image referenced by an override is intentional source, never cruft — the reference set (including project FormatSettings) protects it.
</common_mistakes>

<success_criteria>

## Success Criteria

- Project lock state and baseline mode (A/B) reported up front.
- Every override classified (forked-copy vs net-new) with target→format resolution.
- Forked overrides classified for positive/negative drift; customizations surfaced via annotation, prefix, or fork-point.
- SCSS missing-variable, partial-wiring, and dangling-reference checks run.
- Removal recommendations produced (retired / orphan / cruft / redundant) without flagging referenced source.
- For an upgrade: a 3-way verdict per surviving override (manual-merge / auto-mergeable / fast-forward / redundant / in-sync).
- No writes to the project (Phase 1).
</success_criteria>
