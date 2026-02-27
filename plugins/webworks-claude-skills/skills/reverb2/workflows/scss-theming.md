# Workflow: SCSS Theme Customization

*From SKILL.md intake item 3.*

<required_reading>
Read before proceeding:
- `references/scss-architecture.md` — three-layer model, color cascade, `$theme_` convention
- `../epublisher/references/file-resolver-guide.md` — override hierarchy and parallel structure rules
</required_reading>

<process>

## Step 1: Determine Request Type

Ask the user what they want to customize, then route to the correct layer:

| Request | Layer | Jump to |
|---------|-------|---------|
| "Change brand colors" | 1 — Variable overrides | Step 3b (recommended) or Step 3a (legacy script) |
| "Adjust font sizes / spacing" | 1 — Variable overrides | Step 3b |
| "Customize toolbar / TOC / navigation look" | 2 — Skin CSS | Step 4 |
| "Style content page elements" | 3 — Content page CSS | Step 5 |
| "Show current theme values" | — | Step 2 only |
| "Migrate .weplugin skin" | — | Step 6 |

## Step 2: Determine Override Level

Ask: "Apply to a single target or all Reverb 2.0 targets?"

| Scope | Override location |
|-------|-------------------|
| Single target | `[Project]/Targets/[Target]/Pages/sass/` |
| All targets | `[Project]/Formats/WebWorks Reverb 2.0/Pages/sass/` |

Extract current values to show what exists:

```bash
python scripts/extract-scss-variables.py <project-dir> neo
```

For detailed exploration of other categories:
```bash
python scripts/extract-scss-variables.py <project-dir> [layout|toolbar|header|footer|menu|sizes]
```

**Script limitation:** `extract-scss-variables.py` only reads `_colors.scss` and `_sizes.scss`. For variables in `_fonts.scss`, `_icons.scss`, or `_borders.scss`, read those files directly from the resolved location.

## Step 3a: Layer 1 — Legacy Quick Colors (Script-Assisted)

**Note:** This script sets `$neo_*` variables directly without the `$theme_` naming convention. It works but produces output that is harder to maintain during upgrades. **Prefer Step 3b** for new projects.

```bash
bash scripts/generate-color-override.sh <output-path> \
  --main-color "#E63946" \
  --main-text "#FFFFFF" \
  --secondary-color "#F1FAEE" \
  --secondary-text "#1D3557" \
  --tertiary-color "#457B9D" \
  --page-color "#F1FAEE"
```

Output path follows the override level from Step 2:
- Target: `[Project]/Targets/[Target]/Pages/sass/_colors.scss`
- Format: `[Project]/Formats/WebWorks Reverb 2.0/Pages/sass/_colors.scss`

Skip to **Step 7** after generating.

## Step 3b: Layer 1 — Manual Variable Override (With `$theme_` Convention)

Use when the user needs fine-grained control or wants the recommended naming pattern.

### 1. Copy the target partial to the project

Copy from the installation matching the project's Base Format Version (see file-resolver-guide.md):

```bash
# Example: copy _colors.scss to format level
cp "[Install]/Formats/WebWorks Reverb 2.0/Pages/sass/_colors.scss" \
   "[Project]/Formats/WebWorks Reverb 2.0/Pages/sass/_colors.scss"
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

### 4. Add `$theme_*` variables for additional color needs

Create new `$theme_*` variables for any color that doesn't map through the 6 layout slots. This keeps every intentional value greppable for upgrade traceability:

```scss
// Additional brand colors beyond the 6 layout slots
$theme_accent:          #0088CC;
$theme_surface_menu:    #E8EEF2;

// Map to specific component variables
$_menu_background_color: $theme_surface_menu;
$link_default_color:     $theme_accent;
```

**Upgrade workflow:** `grep 'theme_'` finds every project customization instantly, making it easy to audit overrides against new Reverb defaults.

See `references/scss-architecture.md` for the full cascade diagram.

### Other partials

The same copy-and-edit pattern applies to all partials:

| Partial | When to use |
|---------|-------------|
| `_colors.scss` | Color scheme changes |
| `_sizes.scss` | Spacing, padding, dimensions, font sizes |
| `_fonts.scss` | Font families, weights, styles |
| `_icons.scss` | Font Awesome icon codepoints |
| `_borders.scss` | Border widths, styles, colors, radii |

Skip to **Step 7** after editing.

## Step 4: Layer 2 — Skin CSS Overrides

Use when SCSS variables are insufficient and structural CSS changes are needed for the chrome (toolbar, TOC, navigation, breadcrumbs, popups).

### 1. Copy `skin.scss` to the project

```bash
cp "[Install]/Formats/WebWorks Reverb 2.0/Pages/sass/skin.scss" \
   "[Project]/Formats/WebWorks Reverb 2.0/Pages/sass/skin.scss"
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

## Step 5: Layer 3 — Content Page CSS Overrides

Use when customizing the content page inside the iframe (fonts, links, tables, mini-TOC, code blocks).

### 1. Copy `webworks.scss` to the project

```bash
cp "[Install]/Formats/WebWorks Reverb 2.0/Pages/sass/webworks.scss" \
   "[Project]/Formats/WebWorks Reverb 2.0/Pages/sass/webworks.scss"
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

`.weplugin` files are deprecated zip archives. To migrate:

1. Rename `.weplugin` to `.zip` and extract
2. Diff extracted files against installation defaults to find actual customizations
3. Copy customized `_*.scss` partials to the appropriate override level (Step 2)
4. If `Connect.asp` was customized, copy to `Pages/` at the same override level
5. Remove the `.weplugin` from the project
6. Rebuild to verify (Step 7)

See `references/scss-architecture.md` § `.weplugin` Migration for details.

## Step 7: Rebuild and Verify

### Rebuild

Invoke the **automap skill** to rebuild the target with updated SCSS.

### Verify

After rebuild, confirm:
- Output loads without SCSS compilation errors
- Visual changes applied correctly
- No console errors in browser

Invoke the **browser-testing workflow** if automated verification is needed.

### Report

Confirm to user:
```
Theme customization applied:
- Layer: {1/2/3}
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
- [ ] Import hooks added to copied entry points (Layers 2–3)
- [ ] User informed of next steps (rebuild)
- [ ] Build completes without SCSS errors (if rebuild performed)
</success_criteria>
