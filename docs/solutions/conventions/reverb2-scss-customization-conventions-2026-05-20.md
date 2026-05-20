---
title: SCSS Customization Conventions for Reverb 2.0 Projects
date: 2026-05-20
category: conventions
module: reverb2
problem_type: convention
component: documentation
severity: medium
applies_when:
  - Customizing colors, fonts, or layout in a Reverb 2.0 ePublisher target
  - Creating or editing _custom-skin.scss or _custom-webworks.scss partials
  - Overriding non-SCSS files (locales.xml, header.asp, footer.asp) for a customer project
  - Upgrading an existing customer project to a newer Reverb 2.0 baseline
  - Auditing a Reverb 2.0 customization for grep-ability and maintainability
tags: [reverb2, scss, customization, conventions, epublisher, theming, upgrade-pattern, grepable]
---

# SCSS Customization Conventions for Reverb 2.0 Projects

## Context

WebWorks Reverb 2.0 customer projects accumulate SCSS and template customizations across multiple ePublisher upgrades. When the next upgrade arrives, those customizations are nearly impossible to find: brand colors are buried inside generic variables like `$_layout_color_3`, override files diverge silently from installed defaults, and untranslated strings in `locales.xml` look indistinguishable from intentional changes. The result is upgrade pain measured in days — engineers diff every override file by hand, guess at which variables encode brand intent, and frequently re-introduce drift.

Case 00024386 (DICAD Systeme GmbH, upgrade from mixed 2024.1/2025.1 to clean 2025.1) made the pattern explicit: customizations need to be self-locating, cascade-aware, and survivable across upgrades without manual archaeology. These conventions were captured in the `reverb2` skill (issue #51) so future Claude Code work applies them consistently.

## Guidance

Apply these five conventions to every Reverb 2.0 / ePublisher customization.

### 1. Prefix every `_colors.scss` customization with a project variable

Define brand colors at the top of `_colors.scss` with a project-specific prefix (e.g., `$dicad_`, `$qs_`). Map `$_layout_color_1` through `$_layout_color_6` to those prefixed brand colors. Every downstream customization must reference the prefixed variable directly — never the `$_layout_color_N` intermediate, never a newly invented variable like `$link_hover_color`. The whole project's customizations then become discoverable with one command:

```bash
grep 'dicad_' _colors.scss
```

Correct:

```scss
$toolbar_background_color: $dicad_primary_text_color;
$toolbar_tab_background_color: darken($dicad_primary_text_color, 10%);
```

Incorrect:

```scss
$toolbar_background_color: $_layout_color_2;                              // not grep-able
$my_hover_color: $dicad_accent_color;                                     // unnecessary new variable
$toolbar_tab_background_color: darken($toolbar_tabs_container_background_color, 10%);  // intermediate variable
```

### 2. Annotate non-SCSS overrides with a grepable project comment

Every customization in `locales.xml`, `Connect.asp`, or other non-SCSS override files carries a project-name comment so it can be located with `grep`:

```xml
<!-- DICAD -->
<!-- DICAD - expanded German stop words for technical search -->
```

```asp
<%-- DICAD --%>
<!-- DICAD -->
```

SCSS files do not need comments — the `$prefix_` variable pattern from convention 1 is already self-documenting.

### 3. Use paired `_custom-skin.scss` and `_custom-webworks.scss` partials

SCSS rule overrides that cannot be expressed as variable changes go into dedicated partial files imported at the end of the corresponding standard file:

| Standard file   | Custom override file    | Import line                              |
| --------------- | ----------------------- | ---------------------------------------- |
| `skin.scss`     | `_custom-skin.scss`     | `@import "custom-skin"; // WEBWORKS`     |
| `webworks.scss` | `_custom-webworks.scss` | `@import "custom-webworks"; // WEBWORKS` |

Two files, not one, because `webworks.css` loads before `skin.css` in `Page.asp`. Placing a bare `a { }` content-link rule into `_custom-skin.scss` would inherit skin-level specificity and clobber toolbar button link colors.

- `_custom-webworks.scss` — content-page overrides: custom fonts, link styling, paragraph and list formatting
- `_custom-skin.scss` — skin chrome overrides: toolbar, TOC, navigation, breadcrumbs, lightbox, print styles

Upgrade workflow: replace `skin.scss` and `webworks.scss` with the new installed versions, re-append the `@import` line, and leave the `_custom-*.scss` files untouched.

### 4. Delete overrides that match the installed default

After extracting customizations into the `_custom-*.scss` partials, diff each override file against the installed version. If they match exactly, delete the override so the file resolver hierarchy serves the installed default. Example from Case 00024386: `print.scss`'s only customization moved into `_custom-skin.scss` as an `@media print` rule, so the project's `print.scss` override was removed.

### 5. Rebase `locales.xml` on the installed version each upgrade

1. Copy the installed `locales.xml` as the new base — this picks up every new string the release added.
2. Re-apply project-specific customizations (expanded stop words, domain-specific search synonyms, etc.).
3. Annotate each customization with `<!-- PROJECT_NAME -->` or `<!-- PROJECT_NAME - description -->`.
4. Verify before preserving anything that looks untranslated — an untranslated string is usually a release gap, not an intentional customization.

## Why This Matters

- **Discoverability.** A single `grep '<prefix>_'` across the SCSS tree and `grep '<!-- PROJECT_NAME'` across templates surfaces every customization in the project. Without the prefix convention, customizations hide behind generic variable names and are only found by diffing against installed defaults.
- **Cascade correctness.** Splitting overrides into `_custom-skin.scss` and `_custom-webworks.scss` preserves the load order Reverb depends on. Collapsing them produces real bugs: toolbar links inheriting body-link colors, content paragraphs inheriting skin-chrome rules.
- **Upgrade survivability.** When customizations live in `_custom-*.scss` partials and prefixed variables, upgrading is mechanical: replace standard files, re-append one `@import` line, rebase `locales.xml`. Engineers stop hand-merging diffs.
- **No silent drift.** Convention 4 keeps the override surface minimal — every override file in the project is there because it differs from the installed default, not because it was forgotten.
- **No phantom variables.** Forbidding ad-hoc variables like `$link_hover_color` keeps the SCSS dialect identical to upstream Reverb, so future maintainers don't have to learn project-local vocabulary.

## When to Apply

- Customizing colors, typography, or layout variables in `_colors.scss` for a Reverb 2.0 project.
- Adding SCSS rule overrides that cannot be expressed as variable assignments.
- Editing `locales.xml`, `Connect.asp`, or any non-SCSS template in a customer project.
- Upgrading an ePublisher project from one release to another (e.g., 2024.1 to 2025.1).
- Auditing an inherited project to find every customization before refactoring.
- Reviewing a customer-delivered project before merging it back into a maintained branch.

## Examples

### `_colors.scss` — incorrect vs. correct

Incorrect (customizations hide behind generic variables and invented names):

```scss
// _colors.scss — drift-prone
$_layout_color_1: #003366;
$_layout_color_2: #ffffff;

$toolbar_background_color: $_layout_color_2;
$my_hover_color: #ff6600;
$toolbar_tab_background_color: darken($toolbar_tabs_container_background_color, 10%);

a:hover { color: $my_hover_color; }
```

Correct (every customization is prefixed and grep-able):

```scss
// _colors.scss — DICAD brand
$dicad_primary_brand_color: #003366;
$dicad_primary_text_color:  #ffffff;
$dicad_accent_color:        #ff6600;

$_layout_color_1: $dicad_primary_brand_color;
$_layout_color_2: $dicad_primary_text_color;

$toolbar_background_color:     $dicad_primary_text_color;
$toolbar_tab_background_color: darken($dicad_primary_text_color, 10%);

a:hover { color: $dicad_accent_color; }
```

```bash
grep 'dicad_' _colors.scss   # lists every DICAD customization in one pass
```

### `locales.xml` — annotated customization

```xml
<!-- DICAD - German technical stop words -->
<string id="search_stop_words">der die das und oder aber CAD CAM PLM</string>
```

### Upgrade flow (2024.1 to 2025.1)

```text
1. Replace skin.scss, webworks.scss, print.scss, locales.xml with 2025.1 installed versions.
2. Re-append the import lines to the standard SCSS files:
     @import "custom-skin";     // WEBWORKS     (end of skin.scss)
     @import "custom-webworks"; // WEBWORKS     (end of webworks.scss)
3. Diff each remaining override against the installed 2025.1 default; delete any that match.
4. Rebase locales.xml: copy 2025.1 installed file, re-apply <!-- DICAD --> entries.
5. Verify customizations:
     grep 'dicad_'        _colors.scss
     grep '<!-- DICAD'    locales.xml Connect.asp
6. Build, smoke-test toolbar/TOC/content link colors and print styles.
```

## Related

- Skill reference: `plugins/webworks-claude-skills/skills/reverb2/references/customization-conventions.md` (grepable annotations + locales upgrade pattern)
- Skill reference: `plugins/webworks-claude-skills/skills/reverb2/references/scss-architecture.md` (prefixed-variable rules, cascade-order rationale, redundant-override removal)
- Skill workflow: `plugins/webworks-claude-skills/skills/reverb2/workflows/scss-theming.md` (Steps 4-5 cascade cross-links, Step 7 redundant-override removal)
- GitHub issue: #51 (Add SCSS customization best practices to Reverb 2.0 skill)
