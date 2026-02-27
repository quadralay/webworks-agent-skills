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

Override at any tier. Tier 1 changes cascade everywhere; Tier 3 overrides affect only one element.

## `$theme_` Naming Convention

When adding custom variables to override files, use the `$theme_` prefix with MD3-inspired naming:

### Why `$theme_`

- **Greppable:** `grep 'theme_'` finds every project customization across all partials
- **No collisions:** Avoids Reverb internal prefixes (`$neo_`, `$_layout_color_`, `$ww_skin_`)
- **Self-documenting:** Signals "this is a project-level theming decision"

### Standard Tokens

| Variable | Role | Cascade target |
|----------|------|----------------|
| `$theme_primary` | Brand primary color | `$neo_main_color` |
| `$theme_on_primary` | Text/icons on primary | `$neo_main_text_color` |
| `$theme_surface` | Page background | `$neo_page_color` |
| `$theme_surface_nav` | Sidebar/TOC background | `$neo_secondary_color` |
| `$theme_on_surface_nav` | Text on sidebar | `$neo_secondary_text_color` |
| `$theme_surface_footer` | Header/footer background | `$neo_tertiary_color` |

### Example

```scss
// Project brand colors — grep 'theme_' to find all customizations
$theme_primary:          #0052CC;
$theme_on_primary:       #FFFFFF;
$theme_surface:          #FAFBFC;
$theme_surface_nav:      #F4F5F7;
$theme_on_surface_nav:   #172B4D;
$theme_surface_footer:   #253858;

// Map to neo cascade
$neo_main_color:           $theme_primary;
$neo_main_text_color:      $theme_on_primary;
$neo_page_color:           $theme_surface;
$neo_secondary_color:      $theme_surface_nav;
$neo_secondary_text_color: $theme_on_surface_nav;
$neo_tertiary_color:       $theme_surface_footer;
```

The `on_` prefix denotes the contrast color for text/icons placed on that surface — a pattern borrowed from Material Design 3.

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
- GitHub issue: quadralay/epublisher-express-trial#9 — `$theme_` convention rationale
