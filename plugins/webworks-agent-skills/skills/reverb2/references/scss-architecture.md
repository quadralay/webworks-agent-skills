# Reverb 2.0 SCSS Architecture

## Theming Layers

Reverb 2.0 CSS customization uses independent layers, each with its own entry point and scope:

| Layer | Entry Point | Scope | Override File |
|-------|-------------|-------|---------------|
| **1. Variable overrides** | `skin.scss` / `webworks.scss` / `custom.scss` | Change values used by existing rules | `_colors.scss`, `_sizes.scss`, `_fonts.scss`, `_icons.scss`, `_borders.scss` |
| **2. Custom selectors** *(2026.1+)* | `custom.scss` — ships pre-wired, compiled to `css/custom.css` and linked **last** on every page | Any selector, any page type, chrome and content alike | `custom.scss` (replace the stock file) |
| **2a. Skin CSS** *(pre-2026.1 convention)* | `skin.scss` | Chrome: toolbar, TOC, navigation, breadcrumbs, popups | `_custom-skin.scss` (user-created) |
| **2b. Content page CSS** *(pre-2026.1 convention)* | `webworks.scss` | Content: fonts, links, tables, mini-TOC, code blocks | `_custom-webworks.scss` (user-created) |

**Layer 1** is the safest — you only change variable values, never selectors or rules.
**Layer 2** gives full CSS control but requires understanding Reverb's DOM structure. On 2026.1+ prefer `custom.scss`; layers 2a/2b remain supported and are the only option on earlier builds — see [The `custom.scss` Layer](#the-customscss-layer) for how the two relate.

## Recommended Setup for New Projects: No Skin

For a **new** project, leave the *Skin* target setting unset and customize the Reverb 2.0 format directly. This is the recommended starting point — not just a `.weplugin` migration endpoint.

Do **not** start from a packaged skin (a `.weplugin` selected via the *Skin* target setting). Packaged skins are deprecated (see [.weplugin Migration](#weplugin-migration) below) and insert an extra indirection layer between your overrides and the output. Customizing the unskinned format keeps every customization greppable and on the file-resolver fall-through path, which is far easier to audit and upgrade.

Customize the unskinned format using the layers above:

- **Layer 1 — variable overrides** with the `$theme_` convention (`_colors.scss`, `_sizes.scss`, …)
- **Layer 2 — `custom.scss`** for structural CSS of any kind (2026.1+)
- **Layers 2a/2b — `_custom-skin.scss` / `_custom-webworks.scss`** for structural chrome and content-page CSS on pre-2026.1 builds, or when a rule must sit at a specific cascade depth

Apply these at the **Formats** level (`Formats/WebWorks Reverb 2.0/Pages/sass/`) to affect all targets, or at the **Targets** level (`Targets/[Target]/Pages/sass/`) for a single target — see [File Resolver Integration](#file-resolver-integration) below for the full override priority.

## Compilation Model

Reverb compiles independent SCSS entry points during publishing. The three that matter for customization:

```
skin.scss          → skin.css      (toolbar, TOC, navigation chrome)
webworks.scss      → webworks.css  (content page inside iframe)
custom.scss        → custom.css    (user layer; linked LAST on every page)  [2026.1+]
```

These are separate stylesheets loaded by different parts of the Reverb runtime. Variables defined in one are **not visible** to the other — each imports its own copy of the partials. (`connect.scss`, `search.scss`, `social.scss`, `print.scss`, and the `menu_initial_*.scss` pair compile the same way; they are rarely customization targets.)

## The `custom.scss` Layer

> **New in ePublisher 2026.1** (EPUB2908). Earlier builds have no `custom.scss`
> and no `css/custom.css` link — use `_custom-skin.scss` / `_custom-webworks.scss`
> there.

The format ships a stock `Pages/sass/custom.scss`. It compiles to
`css/custom.css`, which **every** page template links as its **last**
stylesheet:

| Template | Published as | Sheets linked before `custom.css` |
|----------|--------------|-----------------------------------|
| `Connect.asp` | `index.html` | `connect.css`, `skin.css`, `menu_initial_open/closed.css` |
| `Page.asp` | topic pages | `webworks.css`, `skin.css`, `social.css`, `catalog.css`, `document.css`, `print.css` |
| `Splash.asp` | `splash.html` | `webworks.css`, `skin.css`, `social.css`, `print.css` |
| `NotFound.asp` | `not-found.html` | `webworks.css`, `skin.css`, `social.css`, `print.css` |
| `Popup.asp` | popups | `webworks.css`, `catalog.css`, `document.css` |
| `Search.asp` | `search.html` | `search.css`, `skin.css` |

(All six also link `font-awesome/css/all.min.css` first.)

Last position is the whole point: a rule in `custom.scss` wins every
**equal-specificity** cascade contest against the stock sheets, on every page
type including popups. Print rules belong here too, inside `@media print`
blocks — `custom.css` is `media="all"` and is linked *after* the `media="print"`
`print.css`, so an equal-specificity `@media print` rule in `custom.scss` wins.

### What the stock file contains

Comments plus the variable-partial imports, and nothing else:

```scss
@import "functions";
@import "colors";
@import "fonts";
@import "icons";
@import "sizes";
@import "borders";
```

Those imports emit no CSS on their own, so the compiled `custom.css` contributes
**no rules** by default. Their job is to make every skin variable — including
project overrides of the partials, which flow through the same resolver —
usable inside your custom rules (`$link_default_color`, `$theme_primary`, …).

> **The stock file carries no component design.** It is an empty seam. The
> 2026.1 splash Groups Grid design, for example, lives in `skin.scss` and
> `webworks.scss`, **not** here — so overriding `custom.scss` does not take
> ownership of it. Keep the `@import` block when you replace the file, though;
> dropping it breaks every variable reference in your own rules.

### How to customize

Copy `custom.scss` into the project at either level and edit the copy. It
**replaces** the stock file entirely — there is no merge:

```
[Project]/Targets/[Target]/Pages/sass/custom.scss    ← single target
[Project]/Formats/WebWorks Reverb 2.0/Pages/sass/custom.scss  ← all targets
```

No entry point to copy, no `@import` hook to add, and nothing to re-apply at
upgrade time — the link is already in every shipped template.

### Relationship to `_custom-skin.scss` / `_custom-webworks.scss`

The older pair still works and is not deprecated. The difference is mechanical:

| | `custom.scss` (2026.1+) | `_custom-skin.scss` / `_custom-webworks.scss` |
|---|---|---|
| Setup | Copy one file. Already linked. | Copy `skin.scss` and/or `webworks.scss`, create the partial, add `@import "custom-skin";` / `@import "custom-webworks";` |
| Upgrade cost | None — no entry point is overridden | Re-apply the `@import` line to each new installed entry point |
| Cascade position | After **both** `skin.css` and `webworks.css`, on every page type | Inside whichever sheet imports it |
| Reaches popups, search, splash, not-found | Yes | Only where that sheet is linked (`skin.css` is not linked by `Popup.asp`) |

Use `custom.scss` by default on 2026.1+. Reach for the older pair when:

- the project targets a pre-2026.1 build, or already has the partials wired
  (leave them; they keep working alongside `custom.scss`), or
- a rule **must not** outrank the other sheet. The two-partial split exists
  because `webworks.css` loads before `skin.css`: a bare `a { }` content rule
  placed in `_custom-skin.scss` would outrank toolbar link colors. `custom.css`
  loads after both, so the same bare rule in `custom.scss` reaches chrome links
  too. One file means one cascade depth — **scope your selectors** (`.ww_skin_*`
  for chrome, content-page selectors for content) instead of relying on sheet
  order to do it for you.

Do **not** invent a third partial name (`_custom.scss`, `_project.scss`).
Between `custom.scss` and the well-known `_custom-skin.scss` /
`_custom-webworks.scss` pair, the next customizer already has two places to
look; a third hides the rules.

### Key guardrail

The installed `skin.scss` and `webworks.scss` do **not** ship with custom import hooks. To use layer 2a or 2b, you must:

1. Copy the relevant entry point (`skin.scss` and/or `webworks.scss`) to your project
2. Create your custom partial (`_custom-skin.scss` or `_custom-webworks.scss`)
3. Add the `@import` line to the copied entry point

`custom.scss` (2026.1+) has no equivalent step — its link ships in every page template.

### Why Two Custom Partials, Not One

Reverb 2.0 loads `webworks.css` before `skin.css` in the page template. Putting content-page overrides (a bare `a { }` link rule, paragraph styling) in `_custom-skin.scss` would elevate their specificity in the cascade and override skin chrome styles like toolbar button link colors. Splitting custom rules along the same boundary as the installed `webworks.scss` / `skin.scss` keeps custom rules at the same cascade depth as the rules they intend to override.

| File | Scope |
|---|---|
| `_custom-webworks.scss` | Content page overrides — custom fonts, link styling, paragraph/list formatting |
| `_custom-skin.scss` | Skin chrome overrides — toolbar, TOC, navigation, breadcrumbs, lightbox, print styles |

**Upgrade workflow:** When upgrading the format, replace `skin.scss` and `webworks.scss` with the new installed versions and re-append the `@import` line for the corresponding custom partial. The `_custom-*.scss` partials need no changes. Moving those rules into `custom.scss` on 2026.1+ retires this step entirely — at the cost of the cascade-depth separation described above.

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

All partials live in `Pages/sass/` within the format directory structure. The stock `custom.scss` imports all six, so every variable and helper below is available in your custom rules.

2026.1 adds the `$splash_groups_*` family across `_sizes.scss`, `_colors.scss`, `_borders.scss`, and `_fonts.scss` for the splash Groups Grid — inventoried in `runtime-rendered-ui.md` § "Splash Groups Grid".

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
$toolbar_background_color:  $_layout_color_1;
$toolbar_text_color:        $_layout_color_2;
$menu_background_color:     $_layout_color_3;
$footer_background_color:    $_layout_color_5;
```

> **Slot varies by configuration.** The layout slot wired to a given component variable is **not** universal — it can differ between configurations. For example, `$toolbar_background_color` is `$_layout_color_1` in the base Reverb 2.0 format, but under a packaged skin it may be wired to a different slot. Before overriding, verify the slot→property mapping in the actual `_colors.scss` you are editing rather than assuming the base-format mapping holds.

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
- **Do not introduce new auxiliary variables.** If a Reverb component variable like `$link_hover_color` doesn't exist, do not invent one. Reference the prefixed variable directly at the override site. Assigning a Reverb-defined component variable like `$menu_background_color` to a prefixed variable *is* correct — what's forbidden is introducing *new* names that aren't part of Reverb's variable schema.
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
$menu_background_color:    $theme_surface_menu;
$page_background_color:     $theme_surface_content;
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
$menu_background_color: $theme_surface_menu;
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

### Migration Delivery Pattern

The steps above extract a skin's *files*. When the goal is to move a customer off a *skinned look* entirely — a redesign, not a like-for-like port — deliver three targets so the old and new output can be compared side by side and the customer has a clean base to design against:

| Target | *Skin* setting | Purpose |
|--------|----------------|---------|
| *reference* | skinned (old) | The old look, unchanged — **comparison only**, never the redesign base |
| *match* | unset (no skin) | Reproduces the old look on the unskinned format — proves the unskinned format can hit parity |
| *no-skin* | unset (no skin) | Clean unskinned format — the **recommended redesign base** |

The *reference* target preserves the old output for side-by-side comparison. The *match* target de-risks the move by demonstrating the unskinned format can reproduce the existing look. The *no-skin* target is where the redesign actually happens, customized directly per [Recommended Setup for New Projects](#recommended-setup-for-new-projects-no-skin) above.

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

The same hierarchy applies to all partials, `skin.scss`, `webworks.scss`, `custom.scss`, and any custom files.

---

**See also:**
- `../epublisher/references/file-resolver-guide.md` — full override hierarchy (its Workflow 3 documents the `_custom-skin.scss` / `_custom-webworks.scss` route; [The `custom.scss` Layer](#the-customscss-layer) above is the 2026.1+ alternative)
- `runtime-rendered-ui.md` — splash Groups Grid and Assistant avatar: runtime-built DOM, `$splash_groups_*` variables, `ww_skin_*` hooks
- `workflows/scss-theming.md` — step-by-step theming workflow
- `customization-conventions.md` — annotations for non-SCSS overrides and `locales.xml` upgrade
- GitHub issue: quadralay/epublisher-express-trial#9 — `$theme_` convention rationale
