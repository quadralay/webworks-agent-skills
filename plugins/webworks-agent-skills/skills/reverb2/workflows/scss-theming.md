# Workflow: SCSS Theme Customization

*From SKILL.md intake item 3.*

<required_reading>
Read before proceeding:
- `references/scss-architecture.md` — theming layers, the `custom.scss` seam, color cascade, `$theme_` convention
- `../epublisher/references/file-resolver-guide.md` — override hierarchy and parallel structure rules
- `references/runtime-rendered-ui.md` — only when the request touches the splash page or the Assistant avatar (2026.1+): those surfaces are built at runtime, so styling them means `$splash_groups_*` / `ww_skin_assistant_avatar*`, not template edits
</required_reading>

<process>

## Step 1: Determine Request Type

Ask the user what they want to customize, then route to the correct layer:

| Request | Layer | Jump to |
|---------|-------|---------|
| "Change brand colors" | 1 — Variable overrides | Step 2, then Step 3 |
| "Adjust font sizes / spacing" | 1 — Variable overrides | Step 2, then Step 3 |
| "Add custom CSS rules" (2026.1+) | 2 — `custom.scss` | Step 2, then Step 3B |
| "Customize toolbar / TOC / navigation look" | 2a — Skin CSS | Step 2, then Step 3B, then Step 4 if needed |
| "Style content page elements" | 2b — Content page CSS | Step 2, then Step 3B, then Step 5 if needed |
| "Restyle the splash page" (2026.1+) | 1 + 2 | Step 2, then `references/runtime-rendered-ui.md` § "Splash Groups Grid" |
| "Show current theme values" | — | Step 2 (extract only) |
| "Migrate .weplugin skin" | — | Step 2, then Step 6 |

## Step 2: Determine Override Level

Ask: "Apply to a single target or all Reverb 2.0 targets?"

| Scope | `[Override]` directory |
|-------|----------------------|
| Single target | `[Project]/Targets/[Target]` |
| All targets | `[Project]/Formats/WebWorks Reverb 2.0` |

Set `[Override]` to the chosen directory. All subsequent steps use `[Override]` for the destination root.

Extract current values to show what exists:

```bash
python scripts/extract-scss-variables.py <project-dir> neo
```

For detailed exploration of other categories:
```bash
python scripts/extract-scss-variables.py <project-dir> [layout|colors|sizes|toolbar|header|footer|menu|page|search|link|all]
```

**Script limitation:** `extract-scss-variables.py` only reads `_colors.scss` and `_sizes.scss`. For variables in `_fonts.scss`, `_icons.scss`, or `_borders.scss`, read those files directly from the resolved location.

## Step 3: Layer 1 — Variable Override (With `$theme_` Convention)

**SCSS customization rules** (full treatment: `references/scss-architecture.md` § "Strict Rules for Prefixed Variables"):

- Define each brand color once with a `$theme_` / `$<project>_` prefix and assign it to the layout slots first.
- **Reference the prefixed variable at every override site** — never a `$_layout_color_*` slot or a `$neo_*` variable.
- **Don't introduce new auxiliary variables.** Pass the prefixed var straight into `darken()` / `lighten()` (`darken($theme_primary, 10%)`); don't create a derived `$..._d15`.

### 1. Copy the target partial to the project

Resolve the installation path using `resolve-version-root.py` (from the epublisher skill):

```bash
python scripts/resolve-version-root.py --project-file <project.wep> --path-only
```

Then copy from that installation to the override directory:

```bash
cp "[Install]/Formats/WebWorks Reverb 2.0/Pages/sass/_colors.scss" \
   "[Override]/Pages/sass/_colors.scss"
```

### 2. Add `$theme_` variables at the top of the copied file

```scss
// Project brand colors — grep 'theme_' to find all customizations
$theme_primary:          #0052CC;
$theme_on_primary:       #FFFFFF;
$theme_surface:          #FAFBFC;
$theme_surface_nav:      #F4F5F7;
$theme_on_surface_nav:   #172B4D;
$theme_surface_footer:   #253858;
```

### 3. Map `$theme_` variables to layout color slots

Map directly to `$_layout_color_*` (bypasses neo — more direct cascade):

```scss
$_layout_color_1: $theme_primary;
$_layout_color_2: $theme_on_primary;
$_layout_color_3: $theme_surface_nav;
$_layout_color_4: $theme_on_surface_nav;
$_layout_color_5: $theme_surface_footer;
$_layout_color_6: $theme_surface;
```

> **Slot wiring varies by config:** which component a `$_layout_color_*` slot feeds is set in `_colors.scss` and can differ between the base format and a packaged skin (e.g. `$toolbar_background_color` is `$_layout_color_1` in the base format but may be a different slot under a skin). If a slot override doesn't reach the component you expected, verify the slot→property mapping in the actual `_colors.scss` — see `references/scss-architecture.md` § "Tier 3 — Component Variables".

### 4. Add `$theme_*` variables for additional color needs

Create new `$theme_*` variables for any color that doesn't map through the 6 layout slots. This keeps every intentional value greppable for upgrade traceability:

```scss
// Additional brand colors beyond the 6 layout slots
$theme_accent:          #0088CC;
$theme_surface_menu:    #E8EEF2;

// Map to specific component variables
$menu_background_color: $theme_surface_menu;
$link_default_color:     $theme_accent;
```

See `references/scss-architecture.md` for the full cascade diagram and upgrade traceability workflow.

### Other partials

The same copy-and-edit pattern applies to all partials (`_colors.scss`, `_sizes.scss`, `_fonts.scss`, `_icons.scss`, `_borders.scss`). See `references/scss-architecture.md` § "SCSS Partials Inventory" for the full list with variable counts.

Skip to **Step 7** after editing.

## Step 3B: Layer 2 — `custom.scss` (ePublisher 2026.1+, preferred)

Use when SCSS variables are insufficient and structural CSS is needed — chrome or content, either one. On 2026.1+ Reverb 2.0 this is the seam to reach for first. **Check the build first:** if the installed format has no `Pages/sass/custom.scss`, the project is on a pre-2026.1 build — use Step 4 / Step 5 instead.

### 1. Copy `custom.scss` to the project

```bash
cp "[Install]/Formats/WebWorks Reverb 2.0/Pages/sass/custom.scss" \
   "[Override]/Pages/sass/custom.scss"
```

The copy **replaces** the stock file entirely. Keep its `@import` block (`functions`, `colors`, `fonts`, `icons`, `sizes`, `borders`) — dropping it breaks every skin-variable reference in your own rules.

### 2. Add rules below the imports

```scss
@import "functions";
@import "colors";
@import "fonts";
@import "icons";
@import "sizes";
@import "borders";

// Chrome — scope with .ww_skin_*
.ww_skin_search_input {
  width: 300px;
}

// Content page
table {
  border-collapse: collapse;
  width: 100%;
}

@media print {
  .ww_skin_page_toolbar { display: none; }
}
```

No entry point to copy and no import hook to add — `css/custom.css` is already linked **last** by `Connect.asp`, `Page.asp`, `Splash.asp`, `NotFound.asp`, `Popup.asp`, and `Search.asp`, so these rules win equal-specificity contests against every stock sheet on every page type.

**Scope your selectors.** `custom.css` loads after **both** `webworks.css` and `skin.css`, so a bare `a { }` rule here reaches chrome links too — the boundary the `_custom-skin.scss` / `_custom-webworks.scss` split enforces by sheet order does not exist in this one file.

Skip to **Step 7** after editing.

## Step 4: Layer 2a — Skin CSS Overrides (pre-2026.1, or when cascade depth matters)

Use when SCSS variables are insufficient and structural CSS changes are needed for the chrome (toolbar, TOC, navigation, breadcrumbs, popups) — on a pre-2026.1 build, in a project that already wires this partial, or when a rule must stay inside `skin.css`'s cascade depth. For why this is split from content-page overrides, see `references/scss-architecture.md` § "Why Two Custom Partials, Not One".

### 1. Copy `skin.scss` to the project

```bash
cp "[Install]/Formats/WebWorks Reverb 2.0/Pages/sass/skin.scss" \
   "[Override]/Pages/sass/skin.scss"
```

### 2. Create `_custom-skin.scss` in the same directory

```scss
// Custom skin overrides
// Targets .ww_skin_* selectors in the toolbar, TOC, and navigation chrome

.ww_skin_search_input {
  width: 300px;
}
```

### 3. Add import to the end of the copied `skin.scss`

```scss
// ... existing skin.scss content ...

// Custom skin overrides — keep this import last
@import "custom-skin";
```

**Selector reference:** Reverb chrome elements use `.ww_skin_*` class prefixes. Inspect the generated `skin.css` or the installed `skin.scss` to find the selector you need.

Skip to **Step 7** after editing.

## Step 5: Layer 2b — Content Page CSS Overrides (pre-2026.1, or when cascade depth matters)

Use when customizing the content page inside the iframe (fonts, links, tables, mini-TOC, code blocks) via the partial route. Keep `a { }`, paragraph, and table rules here — putting them in `_custom-skin.scss` would incorrectly elevate their cascade specificity. See `references/scss-architecture.md` § "Why Two Custom Partials, Not One".

### 1. Copy `webworks.scss` to the project

```bash
cp "[Install]/Formats/WebWorks Reverb 2.0/Pages/sass/webworks.scss" \
   "[Override]/Pages/sass/webworks.scss"
```

### 2. Create `_custom-webworks.scss` in the same directory

```scss
// Custom content page overrides
// Targets elements inside the content iframe

.ww_skin_page_font {
  line-height: 1.6;
}

table {
  border-collapse: collapse;
  width: 100%;
}
```

### 3. Add import to the end of the copied `webworks.scss`

```scss
// ... existing webworks.scss content ...

// Custom content overrides — keep this import last
@import "custom-webworks";
```

Skip to **Step 7** after editing.

## Step 6: Migrate `.weplugin` Skin

`.weplugin` files are deprecated zip archives. Follow the detailed migration steps in `references/scss-architecture.md` § `.weplugin` Migration, using:
- `[Override]/Pages/sass/` for copied `_*.scss` partials
- `[Override]/Pages/` for copied `Connect.asp` (if present)

If the goal is to move the customer off a *skinned look* entirely (a redesign, not a like-for-like port), deliver a *reference* / *match* / *no-skin* target set per `references/scss-architecture.md` § "Migration Delivery Pattern".

Then rebuild to verify (Step 7).

## Step 7: Rebuild and Verify

### Rebuild

Invoke the **automap skill** to rebuild the target with updated SCSS.

### Verify

After rebuild, confirm:
- Output loads without SCSS compilation errors
- Visual changes applied correctly
- No console errors in browser

Invoke the **browser-testing workflow** if automated verification is needed.

### Remove Redundant Overrides

After verifying the rebuild, check whether any copied entry-point files (for example, `print.scss`, `skin.scss`, `webworks.scss`) match the installed default. If they do — meaning all customization was extracted to `_custom-*.scss` partials or prefixed variables — delete the redundant copy. The file resolver hierarchy will fall through to the installed version, reducing the surface area for upgrade-time merge conflicts.

See `references/scss-architecture.md` § "Removing Redundant Overrides" for the diff workflow.

### Report

Confirm to user:
```
Theme customization applied:
- Layer: {1 / 2 (custom.scss) / 2a (skin) / 2b (content)}
- Override level: {target-specific / format-level}
- Files modified: {list}
- Status: Ready to rebuild (or already rebuilt)
```

</process>

<success_criteria>
This workflow is complete when:
- [ ] Request type identified and routed to correct layer
- [ ] Override level determined (target vs format)
- [ ] Override files created at correct location with parallel structure
- [ ] `$theme_` naming convention used for custom variables (Layer 1)
- [ ] For Layer 2 (`custom.scss`): the `@import` block was preserved and selectors are scoped (chrome vs content)
- [ ] Import hooks added to copied entry points (Layers 2a–2b only)
- [ ] User informed of next steps (rebuild)
- [ ] Build completes without SCSS errors (if rebuild performed)
- [ ] Redundant override files deleted if they match installed defaults
</success_criteria>
