# Reverb 2.0 Customization Conventions

File-format-agnostic conventions for keeping every project customization locatable on upgrade. The SCSS-specific application of this principle (prefixed variables) is documented in `scss-architecture.md`; the conventions below cover non-SCSS override files and the `locales.xml` upgrade procedure.

## Grepable Annotations for Non-SCSS Overrides

Every project-specific change to a file in the override hierarchy should be locatable by a single grep across the project. SCSS files achieve this with a variable prefix (see `scss-architecture.md` § `$theme_` Naming Convention). All other file types use a comment containing a stable project identifier.

| File type | Comment form | Example |
|---|---|---|
| XML (`locales.xml`, configuration) | `<!-- PROJECT -->` or `<!-- PROJECT - description -->` | `<!-- DICAD - expanded stop words -->` |
| ASP / HTML templates (`Connect.asp`, `Page.asp`) | `<!-- PROJECT -->` or `<%-- PROJECT --%>` | `<%-- DICAD --%>` |
| SCSS | Use a prefixed variable (see scss-architecture) | `$dicad_primary_brand_color` |

### Why this matters

An upgrade auditor runs one grep per project tag (for example, `grep -r 'DICAD' Targets/`) to find every intentional deviation. Comments survive renames, reflows, and surrounding edits in ways that variables cannot — so the convention applies even to template files where SCSS-style prefixes aren't possible. The project tag should be short, stable, and unique enough to avoid accidental matches in unrelated content.

### Choosing the tag

- For consultant or customer-engagement projects, use a project identifier the team already recognizes (for example, `DICAD`, `QS`). The tag then doubles as project identification across multiple projects.
- For internal projects, a single stable tag (`THEME`, `CUSTOM`) is sufficient.
- Use the same tag across SCSS prefixes and non-SCSS annotations so a single grep covers both.

## `locales.xml` Upgrade Pattern

`locales.xml` contains localized strings and search configuration (stop words, synonyms). Projects often customize it for domain-specific search behavior. On format upgrade, the installed `locales.xml` may add new strings the customization has never seen — overwriting the customer's file would lose new defaults, and copying the customer's file forward would miss them.

### Procedure

1. Copy the installed `locales.xml` as the new base — this picks up all new strings automatically.
2. Re-apply project-specific customizations (for example, expanded stop words, domain-specific search synonyms).
3. Annotate each customization with a `<!-- PROJECT -->` or `<!-- PROJECT - description -->` comment so it remains locatable on the next upgrade.
4. Do not assume untranslated strings are intentional customizations — verify before preserving. A string that appears untranslated may simply have been overlooked by a previous translation pass, not deliberately left in the source language.

### Caveat

This procedure assumes the customer's `locales.xml` overrides the installed default through the file resolver hierarchy. If `locales.xml` is missing from the project override directory, no upgrade is required — the installed default already applies and will continue to apply after the format upgrade.

## Overrides That Go Inert on 2026.1

An override does not have to break to stop working — the format can simply stop
consulting it. Audit for these when upgrading a Reverb 2.0 project:

| Override | What changed | What to do instead |
|---|---|---|
| `Pages/images/splash.png` | No template references it any more (EPUB2907). The file still ships, so the override resolves and is copied — it just never renders. **Silent.** | Override `Pages/Splash.asp`, or restyle the Groups Grid via the `$splash_groups_*` variables and `custom.scss` |
| A pre-2026.1 `Pages/Splash.asp` | Still resolves and still renders — but it has no `<nav id="splash_groups">`, so the new Groups Grid never appears. **Silent.** | Re-base the override on the current `Splash.asp`. `scripts/lint-output.py` flags this (`splash-groups-container`, warn) |
| A copied `skin.scss` / `webworks.scss` whose only customization is an `@import "custom-*"` line | Still works. But `custom.scss` (2026.1+) needs no entry-point copy at all | Consider moving the rules to `custom.scss` and deleting the copied entry point — see `scss-architecture.md` § "Removing Redundant Overrides" |

Mechanism and hooks for the first two: `runtime-rendered-ui.md`.

---

**See also:**
- `scss-architecture.md` — `$theme_` and project-prefix variable conventions for SCSS files, and the `custom.scss` layer
- `runtime-rendered-ui.md` — splash Groups Grid and Assistant avatar (runtime-built DOM)
- `../epublisher/references/file-resolver-guide.md` — how overrides are resolved
