# Reverb 2.0 SCSS Architecture

## Three-Layer Theming Model

Reverb 2.0 CSS customization uses three independent layers, each with its own entry point and scope:

| Layer | Entry Point | Scope | Override File |
|-------|-------------|-------|---------------|
| **1. Variable overrides** | `skin.scss` / `webworks.scss` | Change values used by existing rules | `_colors.scss`, `_sizes.scss`, `_fonts.scss`, `_icons.scss`, `_borders.scss` |
| **2. Skin CSS** | `skin.scss` | Chrome: toolbar, TOC, navigation, breadcrumbs, popups | `_custom-skin.scss` (user-created) |
| **3. Content page CSS** | `webworks.scss` | Content: fonts, links, tables, mini-TOC, code blocks | `_custom-webworks.scss` (user-created) |

**Layer 1** is the safest — you only change variable values, never selectors or rules.
**Layers 2–3** give full CSS control but require understanding Reverb's DOM structure.

## Compilation Model

Reverb compiles two independent SCSS entry points during publishing:

```
skin.scss          → skin.css      (toolbar, TOC, navigation chrome)
webworks.scss      → webworks.css  (content page inside iframe)
```

These are separate stylesheets loaded by different parts of the Reverb runtime. Variables defined in one are **not visible** to the other — each imports its own copy of the partials.

### Key guardrail

The installed `skin.scss` and `webworks.scss` do **not** ship with custom import hooks. To use Layer 2 or Layer 3, you must:

1. Copy the relevant entry point (`skin.scss` and/or `webworks.scss`) to your project
2. Create your custom partial (`_custom-skin.scss` or `_custom-webworks.scss`)
3. Add the `@import` line to the copied entry point

### Why Two Custom Partials, Not One

Reverb 2.0 loads `webworks.css` before `skin.css` in the page template. Putting content-page overrides (a bare `a { }` link rule, paragraph styling) in `_custom-skin.scss` would elevate their specificity in the cascade and override skin chrome styles like toolbar button link colors. Splitting custom rules along the same boundary as the installed `webworks.scss` / `skin.scss` keeps custom rules at the same cascade depth as the rules they intend to override.

| File | Scope |
|---|---|
| `_custom-webworks.scss` | Content page overrides — custom fonts, link styling, paragraph/list formatting |
| `_custom-skin.scss` | Skin chrome overrides — toolbar, TOC, navigation, breadcrumbs, lightbox, print styles |

**Upgrade workflow:** When upgrading the format, replace `skin.scss` and `webworks.scss` with the new installed versions and re-append the `@import` line for the corresponding custom partial. The `_custom-*.scss` partials need no changes.

## SCSS Partials Inventory

Six partials control all variable-driven styling:

| Partial | Variables | Controls |
|---------|-----------|----------|
| `_colors.scss` | 300+ | All colors — neo presets, layout slots, component colors |
| `_sizes.scss` | 120+ | Dimensions, spacing, padding, font sizes |
| `_fonts.scss` | 69 | Font families, weights, styles per component |
| `_icons.scss` | 44 | Font Awesome icon codepoints for UI elements |
| `_borders.scss` | 150+ | Border widths, styles, colors, radii |
| `_functions.scss` | 4 | Helper functions (color manipulation) |

All partials live in `Pages/sass/` within the format directory structure.

## Color Cascade

The color system uses a three-tier cascade:

```
Tier 1: Neo presets (6 variables)
   ↓ map to
Tier 2: Layout slots ($_layout_color_1 through $_layout_color_6)
   ↓ cascade to
Tier 3: Component variables (300+ specific UI element colors)
```

### Tier 1 — Neo Presets

Quick-theming entry point. Changing these 6 variables propagates to all UI elements:

```scss
$neo_main_color           // Primary — toolbar, buttons, links
$neo_main_text_color      // Text on primary backgrounds
$neo_secondary_color      // Sidebar background
$neo_secondary_text_color // Text on dark backgrounds
$neo_tertiary_color       // Header/footer background
$neo_page_color           // Page background
```

### Tier 2 — Layout Slots

Internal intermediaries. Neo values map to these, which then feed component variables:

```scss
$_layout_color_1  ← $neo_main_color
$_layout_color_2  ← $neo_main_text_color
$_layout_color_3  ← $neo_secondary_color
$_layout_color_4  ← $neo_secondary_text_color
$_layout_color_5  ← $neo_tertiary_color
$_layout_color_6  ← $neo_page_color
```

### Tier 3 — Component Variables

Individual UI element colors derived from layout slots. Examples:

```scss
$_toolbar_background_color:  $_layout_color_1;
$_toolbar_text_color:        $_layout_color_2;
$_menu_background_color:     $_layout_color_3;
$_footer_background_color:   $_layout_color_5;
```

Override at any tier. Tier 2 (layout slots) is the recommended entry point for the `$theme_` convention — it bypasses neo entirely, providing a more direct cascade with fewer indirection layers. Neo presets exist as a quick-theming convenience but are not needed when using named `$theme_*` variables.

## `$theme_` Naming Convention

When adding custom variables to override files, use the `$theme_` prefix with MD3-inspired naming:

### Why `$theme_`

- **Greppable:** `grep 'theme_'` finds every project customization across all partials
- **No collisions:** Avoids Reverb internal prefixes (`$neo_`, `$_layout_color_`, `$ww_skin_`)
- **Self-documenting:** Signals "this is a project-level theming decision"

### Strict Rules for Prefixed Variables

The prefix is only useful as an upgrade audit tool if every customization actually references it. Three rules keep the convention honest:

- **Always reference the prefixed variable, never an intermediate.** When overriding a component variable, reference `$theme_*` (or `$<project>_*`) directly. Do not reference `$_layout_color_2` or `$neo_main_text_color` in the override — those are intermediaries that obscure intent and break grep-ability.
- **Do not introduce new auxiliary variables.** If a Reverb component variable like `$link_hover_color` doesn't exist, do not invent one. Reference the prefixed variable directly at the override site. Assigning a Reverb-defined component variable like `$_menu_background_color` to a prefixed variable *is* correct — what's forbidden is introducing *new* names that aren't part of Reverb's variable schema.
- **Define brand colors once, at the top of the file.** Every prefixed variable has a single definition; component variables reference it.

```scss
// Correct
$toolbar_background_color:     $theme_primary_text;
$toolbar_tab_background_color: darken($theme_primary_text, 10%);

// Incorrect — references intermediate variable, not grep-able
$toolbar_background_color: $_layout_color_2;

// Incorrect — introduces new auxiliary variable (`$my_hover_color` is not in Reverb's schema)
$my_hover_color: $theme_accent;

// Incorrect — references another component variable as intermediate
$toolbar_tab_background_color: darken($toolbar_tabs_container_background_color, 10%);
```

### Project-Specific Prefix Variant

When a project is a customer engagement or part of a consultant portfolio, replace `$theme_` with a project-identifying prefix (for example, `$dicad_`, `$qs_`). The grep pattern then doubles as project identification across multiple projects:

```scss
$dicad_primary_brand_color: #00407A;
$dicad_primary_text_color:  #FFFFFF;

$_layout_color_1: $dicad_primary_brand_color;
$_layout_color_2: $dicad_primary_text_color;
```

The Strict Rules above apply identically — only the prefix string changes. Choose one prefix per project and use it consistently across `_colors.scss`, `_sizes.scss`, and any other partials in the override.

For non-SCSS files that also need to be locatable by project (`locales.xml`, ASP templates), see `customization-conventions.md`.

### Standard Tokens

The six core tokens map directly to layout color slots, bypassing the neo layer:

| Variable | Role | Cascade target |
|----------|------|----------------|
| `$theme_primary` | Brand primary color | `$_layout_color_1` |
| `$theme_on_primary` | Text/icons on primary | `$_layout_color_2` |
| `$theme_surface_nav` | Sidebar/TOC background | `$_layout_color_3` |
| `$theme_on_surface_nav` | Text on sidebar | `$_layout_color_4` |
| `$theme_surface_footer` | Header/footer background | `$_layout_color_5` |
| `$theme_surface` | Page background | `$_layout_color_6` |

The `on_` prefix denotes the contrast color for text/icons placed on that surface — a pattern borrowed from Material Design 3.

### Extending Beyond the Six Core Tokens

Create additional `$theme_*` variables for any color need beyond the six layout slots. This ensures **every intentional color value has a greppable name**, which is critical for upgrade traceability:

```scss
// Additional brand colors beyond the 6 layout slots (values are project-specific)
$theme_accent:           #0088CC;   // Highlight color for links, buttons
$theme_surface_menu:     #E8EEF2;   // Sidebar distinct from content
$theme_surface_content:  #f4f7fa;   // Content area background
```

These map directly to component variables rather than layout slots:

```scss
$_menu_background_color:    $theme_surface_menu;
$_page_background_color:    $theme_surface_content;
```

**Why this matters for upgrades:** When upgrading to a new Reverb version, `grep 'theme_'` finds every intentional customization in seconds. Without named variables, raw hex values scattered through 300+ component assignments are nearly impossible to audit against new defaults.

### Example

```scss
// Project brand colors — grep 'theme_' to find all customizations
$theme_primary:          #0052CC;
$theme_on_primary:       #FFFFFF;
$theme_surface:          #FAFBFC;
$theme_surface_nav:      #F4F5F7;
$theme_on_surface_nav:   #172B4D;
$theme_surface_footer:   #253858;
$theme_accent:           #0088CC;
$theme_surface_menu:     #E8EEF2;

// Map to layout color slots (bypasses neo — more direct)
$_layout_color_1: $theme_primary;
$_layout_color_2: $theme_on_primary;
$_layout_color_3: $theme_surface_nav;
$_layout_color_4: $theme_on_surface_nav;
$_layout_color_5: $theme_surface_footer;
$_layout_color_6: $theme_surface;

// Additional component overrides beyond the 6-slot cascade
$_menu_background_color: $theme_surface_menu;
$link_default_color:     $theme_accent;
```

## `.weplugin` Migration

`.weplugin` files are **deprecated** and will be removed in Reverb 3.0. They are zip archives typically containing:

- `_colors.scss` — color variable overrides
- `_sizes.scss` — dimension overrides (sometimes)
- `Connect.asp` — HTML template modifications (sometimes)

### Migration Steps

1. Rename `.weplugin` to `.zip` and extract
2. Identify which files contain actual customizations (diff against installation defaults)
3. Copy customized `_*.scss` partials to the appropriate override level:
   - `Formats/WebWorks Reverb 2.0/Pages/sass/` for format-wide
   - `Targets/[TargetName]/Pages/sass/` for target-specific
4. If `Connect.asp` was customized, copy to `Pages/` at the same level
5. Remove the `.weplugin` from the project

## Removing Redundant Overrides

After extracting customizations into `_custom-*.scss` partials and prefixed variables, the copied entry-point files (`skin.scss`, `webworks.scss`, `print.scss`, and similar) may end up byte-identical to the installed version, apart from the `@import "custom-*"` line. Any entry-point file that matches the installed default exactly *and* has no custom imports should be deleted from the override directory. The file resolver hierarchy will fall through to the installed default, reducing the surface area for upgrade-time merge conflicts.

**Example.** A `print.scss` whose only customization is moved to `_custom-skin.scss` as an `@media print` rule then matches the installed default and should be deleted.

**Diff workflow:**

```bash
diff "[Override]/Pages/sass/print.scss" \
     "[Install]/Formats/WebWorks Reverb 2.0/Pages/sass/print.scss"
```

If the diff is empty (or contains only the `@import` line and that import is now redundant), delete the override file.

## File Resolver Integration

All SCSS files follow the ePublisher file resolver hierarchy. See `../epublisher/references/file-resolver-guide.md` for the complete four-level system.

**Override priority for SCSS** (highest first):

1. `Targets/[Target]/Pages/sass/_colors.scss` — single target
2. `Formats/WebWorks Reverb 2.0/Pages/sass/_colors.scss` — all targets
3. `Formats/WebWorks Reverb 2.0.base/Pages/sass/_colors.scss` — packaged defaults
4. `[Install]/Formats/WebWorks Reverb 2.0/Pages/sass/_colors.scss` — installation fallback

The same hierarchy applies to all partials, `skin.scss`, `webworks.scss`, and any custom files.

---

**See also:**
- `../epublisher/references/file-resolver-guide.md` — full override hierarchy
- `workflows/scss-theming.md` — step-by-step theming workflow
- `customization-conventions.md` — annotations for non-SCSS overrides and `locales.xml` upgrade
- GitHub issue: quadralay/epublisher-express-trial#9 — `$theme_` convention rationale
