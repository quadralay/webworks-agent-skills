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

---

**See also:**
- `scss-architecture.md` — `$theme_` and project-prefix variable conventions for SCSS files
- `../epublisher/references/file-resolver-guide.md` — how overrides are resolved
