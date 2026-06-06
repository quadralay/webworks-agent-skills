# Known vs. Unknown Baseline

How the audit establishes its baseline, how confident it can be, and how to recover a baseline when the fork-point build is gone. Two **independent** axes govern this — detect both and report them up front.

## Axis 1 — Project lock state (from `FormatVersion`)

`FormatVersion` records whether the project is pinned to *ePublisher's* version or **locked** to a specific base format.

| `FormatVersion` | Meaning | Upgrade behavior |
|-----------------|---------|------------------|
| `{Current}` (with e.g. `RuntimeVersion="2026.1"`) | Tracks ePublisher's own version | **Auto-upgrade-safe when no advanced customizations exist.** When customizations are present, this audit decides whether they carry forward safely. |
| `2025.1` (a specific version) | **Locked** to that base format | **Will not auto-upgrade, even with zero customizations.** Upgrading means consciously re-pointing the project and re-validating. |

The effective **base format version** is `RuntimeVersion` when tracking, else the pinned `FormatVersion`. Report the lock state first — it determines whether "just upgrade it" is even on the table before customizations enter the picture.

## Axis 2 — Reference-version availability

A precise drift audit wants three inputs: `base-old` (the version the override was forked from), `base-new` (the upgrade target), and `mine` (the override).

### Mode A — 3-way (the normal case)

Upgrades usually run with **both** the current and upgrade-to format versions installed side by side, so all three inputs exist:

- `base-old → base-new` is **exactly** the upstream drift (positive and negative).
- `base-old → mine` is **exactly** the customization (annotated or not).

Cleanly separable, precise, and the basis for a real 3-way merge. Use whenever both builds are available — this is what the `drift` command does with `--from-version` (default: the lock) and `--to-version`.

### Mode B — 2-way + inference (the exception)

Only `base-new` and `mine` exist; the fork-point base is gone. This does **not** happen on a clean upgrade — it signals either an **earlier upgrade that was never properly completed** or a **patched / early-release build** no longer installed. A 2-way diff conflates customizations and drift in the same hunks, so classification falls back to inference (see `classification-heuristics.md`): the annotation test, git history, code-shape heuristics, and embedded version strings.

In Mode B the audit must **label classifications as inferred, not proven**, and report reduced confidence.

> `FormatVersion="{Current}"` does **not** imply Mode B. Lock state and baseline availability are independent — a `{Current}` project usually has its base on disk (Mode A). A project is only Mode B when its specific fork-point build is missing.

## Fork-point discovery (promoting Mode B → Mode A)

The `discover` command fingerprints each forked override against **every installed version** and, per format, finds the version that maximizes a size-weighted line-similarity — the most likely fork-point. This often recovers a usable `base-old` even in Mode B.

### Per-format, not project-wide

A project may span several formats forked at different times and evolving at different rates. A single project-wide fork-point is misleading; `discover` reports one per format. (In the worked customer case, `Shared` resolved to the current lock while `Reverb 2.0` resolved six releases older.)

### Staleness depth

For each non-retired format, `discover` compares the discovered fork-point against the project's lock:

- fork-point **== lock** → current.
- fork-point **< lock** → the overrides derive from an older base than the lock claims, by *N releases* — they were never re-synced when the lock was bumped. This is hidden, unreconciled drift.
- fork-point **> lock** → usually an artifact of heavy customization skewing the match; reported with a caveat.

### Confidence taxonomy

| Confidence | When | How to read it |
|------------|------|----------------|
| **high** | Strong cross-file agreement and a clear score margin | Trust the fork-point |
| **medium** | Partial agreement or a modest margin | Likely correct; corroborate |
| **low** | Plateau (many versions match near-equally) or scattered votes | Indeterminate from fingerprinting alone; lean on the lock and companion files |

A **plateau** (top candidates within a small epsilon) means the file barely changed across those versions — the fork-point is genuinely indeterminate from that file, not wrong. Heavy customization also pulls a single file's match older; the size-weighted cross-file aggregate is more robust than any one file's vote.

### Same-family limit

If the fork-point resolves to the same version family as the installed base (e.g. both `2026.1`), discovery cannot separate build-level differences within that family (a patched/early build shares the version folder). That residual is real drift but is not recoverable from disk — note it and rely on the per-file residual and the annotation test.

## Recovering a true baseline

Ranked best-to-worst:

1. **Install the fork-point build.** If `discover` (or the pinned `FormatVersion`) names a version, install it (EOL installer if needed) for a true 3-way.
2. **Recover from version control.** If the project is in git/SVN, the pristine fork-point file may be in history.
3. **Accept the installed build as the sole baseline.** Run 2-way and rely on inference; label confidence accordingly.

## Retired formats and EOL versions

- **Retired formats** — WebWorks Help 5.0, WebWorks Reverb 1.x (and older help formats). Their overrides should be removed wholesale; computing drift for them is not useful. `discover` marks them and skips fork-point analysis; `cleanup` recommends wholesale removal. Users are often afraid to delete retired formats — help them move forward confidently.
- **EOL format versions** — older than **2022.1** today; this moves to **2023.1** when 2026.1 ships. EOL versions are installable via the optional EOL installer for legacy/upgrade work, but encourage moving forward rather than staying on them.
