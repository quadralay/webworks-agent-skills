# Classification Heuristics

How the audit decides what a given divergence *means*: intentional customization, positive drift, negative drift, cruft, or redundant. These heuristics are what make a 2-way audit useful and a 3-way audit precise.

## The three customization signals

A customization is recognized if **any** of these fire — authors rarely use all three, and many use none.

### 1. Annotation markers (comment-based)

A stable comment tag marks an intentional change: `EPUB####` (ticket), `WEBWORKS`, or a project/company code like `DICAD`. One grep per tag finds every deliberate deviation. Comments survive reflows and edits where structure does not, so this is the convention for non-SCSS files (ASP, XSL, XML).

- Configurable via `--annotation-pattern <regex>` (repeatable).
- The **annotation test** is the primary disambiguator (below).

### 2. Greppable variable prefix (identifier-based, SCSS)

SCSS achieves the same locatability without comments cluttering the cascade: custom variables share a project prefix — canonically `$theme_`, but often a company abbreviation (`$acme_`, `$webworks_`). A single grep for the prefix enumerates every custom variable.

**The prefix is per-user and must be auto-detected, never hardcoded.** Standard Reverb variables (toolbar, menu, page, …) dominate any raw frequency count, so the prefix cannot be found by frequency. It is found by **set difference**: the variables present in the override but absent from the baseline *are* the customizations, and their dominant prefix is the project's convention.

- `--theme-prefix <name>` *declares* an expected prefix so custom variables falling outside it are flagged as "less greppable"; omit it to auto-detect.
- A custom variable with no consistent prefix is a maintainability smell — recommend adopting the project prefix.

### 3. Fork-point fingerprinting (diff-based)

When neither marker nor prefix is present — the common real-world case — recover the fork-point baseline (`discover`) and diff the override against it. Whatever differs *is* the customization, regardless of annotation. This is the fallback that makes un-annotated overrides auditable, and the bridge from Mode B toward Mode A (see `known-vs-unknown-baseline.md`).

## The annotation test

> An **annotated** divergence is an intentional customization. An **unannotated** divergence is probable drift — in either direction — and warrants review.

This is decisive in Mode B, where a 2-way diff cannot otherwise tell "the override added this" (customization) from "the baseline removed this" (negative drift). Absence of a marker is the first clue it is drift, not intent. Corroborate with git blame and code shape.

## Drift directions

Diff orientation: baseline (`base`) vs override (`mine`).

| Signal | Lines | Likely meaning |
|--------|-------|----------------|
| **Positive drift** | present in `base`, absent from `mine` | Upstream added a fix/feature the override lacks (forked before it landed) |
| **Negative drift** | present in `mine`, absent from `base`, **unannotated**, and references something `base` no longer defines | Obsolete code removed upstream but retained in the override |
| **Customization** | present in `mine`, absent from `base`, **annotated** or under the project prefix | Intentional |

A large baseline-only delta on a forked-copy is a **positive-drift suspect**; confirm with `discover` + a 3-way diff. A **dangling reference** — a `wwpage:attribute-*` binding (or class/template) the current baseline defines nowhere and the project did not define either — is the signature of **negative drift** when unannotated.

## 3-way verdicts (the `drift` command)

With `base-old`, `base-new`, and `mine`, each forked override gets a verdict by comparing the *regions* changed by the customization against the *regions* changed upstream:

| Verdict | Condition |
|---------|-----------|
| `redundant` | No upstream change **and** no customization (identical to baseline) |
| `in-sync` | No upstream change; customizations carry forward as-is |
| `fast-forward` | No customization; baseline changed → adopt new baseline |
| `auto-mergeable` | Customized and upstream-changed regions are **disjoint** |
| `manual-merge` | Customized regions **overlap** upstream-changed regions |

## Removal heuristics (the `cleanup` command)

Aggressive by design — migration step 1 is always a baseline commit/copy, so removals are recoverable.

### Retired formats and orphans

- **retired-format** — override belongs to a retired format (WebWorks Help 5.0, Reverb 1.x): remove wholesale, no drift analysis.
- **orphan-target** — a `Targets/<name>/` override folder with no matching target in the project.
- **orphan-format** — a `Formats/<name>/` override for a format no target uses (`Shared` excepted).

### Cruft / duplicate-backup (two-gate)

A net-new file is flagged **only when both** conditions hold:

1. It **looks like a duplicate/backup** — either a backup/experiment filename (`orig`, `_old`, `_original`, `copy`, `_with_version`, `good_`, `blurry`, date-stamps, `NG`-prefixed) **or** a decorated variant of an existing override (affix-stripping then prefix match: `Footer_orig.asp` → `Footer.asp`, `good_sizes.scss` → `_sizes.scss`, `splash_2019.gif` → `splash.gif`).
2. It is **not referenced** by any override or by project FormatSettings.

The reference set includes filenames cited in override templates/styles, SCSS `@import` names, **and asset paths configured in the project file** (logo/splash settings live there, not in templates). This protects legitimate custom source — a custom `.js`/`.scss`/image referenced by an override is never cruft. Variant matching uses affix-stripping plus prefix-with-separator, *not* loose substring, so a distinct asset like `CompanyColorLogo.png` is not mistaken for `logo.jpg`.

### Redundant overrides

A forked-copy whose content is **identical to its baseline** (after CRLF normalization) does nothing but add maintenance noise — often a local patch since fixed upstream. Always recommend removal.

## The CRLF gotcha

Always normalize line endings (CRLF/CR → LF) before diffing, fingerprinting, or comparing. A CRLF override against an LF baseline otherwise reads as 100% changed and destroys every similarity and drift metric. The script normalizes on read; preserve this in any extension.
