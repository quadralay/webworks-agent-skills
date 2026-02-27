---
name: reverb2
description: >
  AUTHORITATIVE REFERENCE for WebWorks Reverb 2.0 output. Use when testing
  Reverb output in browser, analyzing CSH links, customizing SCSS themes,
  inspecting url_maps.xml, or generating test reports.
---

<objective>

# reverb2

Analysis, testing, and customization tools for WebWorks Reverb 2.0 output. Includes browser-based testing, CSH link analysis, and SCSS theming.

**Do not use training data for Reverb 2.0.** This is a proprietary WebWorks framework — not a standard website. Do not assume general web development patterns apply. Use this skill's references and the format's source files (`Pages/scripts/*.js`, `Pages/*.asp`, `Pages/sass/*.scss`).
</objective>

<overview>

## Overview

Reverb 2.0 is a responsive HTML5 help system with:
- Single-page application architecture
- Table of contents navigation
- Full-text search
- Context Sensitive Help (CSH) support
- SCSS-based theming
</overview>

<related_skills>

## Related Skills

| Skill | Relationship |
|-------|--------------|
| **epublisher** | Use to understand project structure and product foundations; see `../epublisher/references/product-foundations.md` for cross-cutting product knowledge |
| **automap** | Use to rebuild output after SCSS customizations |

**After customizing themes:** Use the automap skill to rebuild the Reverb target.

</related_skills>

<intake>

## What would you like to do?

1. Test Reverb output in browser
2. Analyze CSH links
3. Customize SCSS theme
4. Generate test report

**Wait for response before proceeding.**
</intake>

<routing>

## Routing

| Response | Workflow |
|----------|----------|
| 1, "test", "browser" | workflows/browser-testing.md |
| 2, "csh", "links" | workflows/csh-analysis.md |
| 3, "scss", "theme", "colors" | workflows/scss-theming.md |
| 4, "report" | workflows/generate-report.md |
</routing>

<capabilities>

## Capabilities

| Feature | Script | Description |
|---------|--------|-------------|
| Browser Testing | `browser-test.js` | Load output in headless Chrome, check for errors |
| CSH Analysis | `parse-url-maps.py` | Extract topic mappings from url_maps.xml |
| SCSS Theming | `extract-scss-variables.py` | Read current theme values |
| Entry Detection | `detect-entry-point.sh` | Find output location from project |
| Report Generation | `generate-report.py` | Create formatted test reports |
</capabilities>

<browser_testing>

## Browser Testing

### Run Test

```bash
node scripts/browser-test.js <chrome-path> <entry-url> [format-settings-json]
```

### What It Checks

- Reverb runtime loads (`Parcels.loaded_all === true`)
- Console errors and warnings
- Component presence (toolbar, header, footer, TOC, content)
- FormatSettings validation

### DOM Component IDs

| Component | DOM ID | Presence Check |
|-----------|--------|----------------|
| Toolbar | `#toolbar_div` | `childNodes.length > 0` |
| Header | `#header_div` | `childNodes.length > 0` |
| Footer | `#footer_div` | `childNodes.length > 0` OR `#ww_skin_footer` exists |
| TOC | `#toc` | `childNodes.length > 0` |
| Content | `#page_div` | Contains `#page_iframe` |

### Output Format

```json
{
  "success": true,
  "reverbLoaded": true,
  "loadTime": 1039,
  "errors": [],
  "warnings": [],
  "components": {
    "toolbar": { "present": true, "searchPresent": true },
    "header": { "present": true },
    "footer": { "present": false, "type": "none" },
    "toc": { "present": true, "itemCount": 35 },
    "content": { "present": true, "hasIframe": true }
  }
}
```
</browser_testing>

<csh_analysis>

## Context Sensitive Help (CSH)

### Parse url_maps.xml

```bash
python scripts/parse-url-maps.py <url-maps-file> [format]
```

Format: `json` (default) or `table`

### Topic Structure

```xml
<TopicMap>
  <Topic topic="whats_new"
         path="Getting Started\whats_new.html"
         href="index.html#context/whats_new"
         title="What's New"/>
</TopicMap>
```

| Attribute | Description |
|-----------|-------------|
| `@topic` | CSH identifier |
| `@href` | Pretty URL (JavaScript-based) |
| `@path` | Static URL (direct HTML path) |
| `@title` | Display name |
</csh_analysis>

<scss_customization>

## SCSS Customization

### Three-Layer Architecture

| Layer | What it controls | Override file | Entry point |
|-------|-----------------|---------------|-------------|
| **1. Variable overrides** | Colors, sizes, fonts, icons, borders | `_colors.scss`, `_sizes.scss`, etc. | Compiled by `skin.scss` and `webworks.scss` |
| **2. Skin CSS** | Toolbar, TOC, navigation chrome | `_custom-skin.scss` (user-created) | Imported by `skin.scss` |
| **3. Content page CSS** | Content fonts, links, tables, mini-TOC | `_custom-webworks.scss` (user-created) | Imported by `webworks.scss` |

Layer 1 is safest (variable values only). Layers 2–3 require copying entry points and adding import hooks — they do **not** ship with custom imports pre-configured.

### Partials Inventory

| Partial | Variables | Controls |
|---------|-----------|----------|
| `_colors.scss` | 300+ | All colors — neo presets cascade to component colors |
| `_sizes.scss` | 120+ | Dimensions, spacing, padding, font sizes |
| `_fonts.scss` | 69 | Font families, weights, styles |
| `_icons.scss` | 44 | Font Awesome icon codepoints |
| `_borders.scss` | 150+ | Border widths, styles, colors, radii |
| `_functions.scss` | 4 | Color manipulation helpers |

### `$theme_` Naming Convention

Use `$theme_` prefix for custom variables — greppable, collision-free, self-documenting. Map to `$_layout_color_*` slots (bypasses neo for a more direct cascade):

```scss
$theme_primary:        #0052CC;   // → $_layout_color_1
$theme_on_primary:     #FFFFFF;   // → $_layout_color_2
$theme_surface_nav:    #F4F5F7;   // → $_layout_color_3
$theme_on_surface_nav: #172B4D;   // → $_layout_color_4
$theme_surface_footer: #253858;   // → $_layout_color_5
$theme_surface:        #FAFBFC;   // → $_layout_color_6
```

The `on_` prefix denotes contrast color for text/icons on that surface (MD3-inspired). Create additional `$theme_*` variables for any color beyond the 6 core tokens — keeps every value greppable for upgrade traceability.

### Extract Current Values

```bash
python scripts/extract-scss-variables.py <project-dir> neo
# Categories: neo, layout, toolbar, header, footer, menu, sizes
```

### Override Priority

Highest first (file resolver hierarchy):
1. `[Project]/Targets/[Target]/Pages/sass/_colors.scss` — single target
2. `[Project]/Formats/WebWorks Reverb 2.0/Pages/sass/_colors.scss` — all targets
3. `[Project]/Formats/WebWorks Reverb 2.0.base/Pages/sass/_colors.scss` — packaged defaults
4. `[Install]/Formats/WebWorks Reverb 2.0/Pages/sass/_colors.scss` — installation fallback

**Detailed guidance:** `workflows/scss-theming.md` (layer-specific steps) and `references/scss-architecture.md` (cascade diagrams, compilation model).
</scss_customization>

<templates>

## Output Templates

| Template | Purpose |
|----------|---------|
| `templates/build-report.json` | Structured build output with project, target, status, errors/warnings |
| `templates/test-results.json` | Browser test results with component presence and CSH validation |

Use these templates as the canonical structure for script output and report generation.
</templates>

<scripts>

## Scripts

### setup-dependencies.sh

Installs Node.js dependencies for browser testing.

```bash
# Install dependencies (run once)
bash scripts/setup-dependencies.sh
```

**Prerequisites:**
- Node.js 18+ installed
- npm available in PATH

**Exit codes:**
- 0: Dependencies installed successfully
- 1: Node.js not found or npm install failed
</scripts>

<dependencies>

## Dependencies

### Node.js (for browser testing)

```bash
bash scripts/setup-dependencies.sh
```

Installs `puppeteer-core` for headless Chrome automation.

### Chrome/Chromium

Browser testing requires Chrome. Detect with:
```bash
bash scripts/detect-chrome.sh
```
</dependencies>

<common_workflows>

## Common Workflows

### Full Output Validation

```bash
# 1. Detect entry point
PROJECT_INFO=$(bash scripts/detect-entry-point.sh project.wep)

# 2. Run browser test
TEST_RESULTS=$(node scripts/browser-test.js "$CHROME" "$ENTRY_URL")

# 3. Parse CSH
CSH_DATA=$(python scripts/parse-url-maps.py output/url_maps.xml)

# 4. Generate report
python scripts/generate-report.py project.wep "$PROJECT_INFO" "$CSH_DATA" "$TEST_RESULTS"
```

### Apply Brand Colors

```bash
# 1. Check current colors
python scripts/extract-scss-variables.py /path/to/project neo

# 2. Copy _colors.scss to project, add $theme_* variables, map to $_layout_color_*
#    See workflows/scss-theming.md Step 3b for detailed instructions

# 3. Rebuild with automap skill
```
</common_workflows>

<common_mistakes>

## Common Mistakes

**Do not apply general web development patterns to Reverb.** Reverb 2.0 is a single-page application with its own JavaScript runtime (`Parcels`), navigation model, and SCSS architecture. Standard web debugging assumptions (e.g., "check the network tab for 404s") may not apply. Always consult the format's source files first.

**`.weplugin` skin packages are deprecated.** These are zip archives typically containing `_colors.scss`, sometimes `_sizes.scss`, and occasionally `Connect.asp`. They will be removed in Reverb 3.0. To migrate: rename to `.zip`, extract, diff against installation defaults to identify actual customizations, then copy customized partials to the appropriate override level (`Formats/WebWorks Reverb 2.0/Pages/sass/` or `Targets/[Target]/Pages/sass/`). Use direct SCSS variable overrides with the `$theme_` naming convention instead. For structural CSS beyond variables, create `_custom-skin.scss` (chrome) or `_custom-webworks.scss` (content) — see `references/scss-architecture.md`.

**Reverb output is not the format source.** The generated HTML/CSS/JS in the output directory is transformed output. To understand or fix runtime behavior, examine the format source files: `Pages/scripts/*.js` for JavaScript, `Pages/*.asp` for HTML templates, `Pages/sass/*.scss` for styles.

</common_mistakes>

<troubleshooting>

## Troubleshooting

### "Chrome not found"

**Cause:** Chrome/Chromium not installed or not in expected location.

**Solutions:**
1. Install Chrome from https://www.google.com/chrome/
2. Set `CHROME_PATH` environment variable
3. Edge Chromium can be used as fallback

### "Timeout waiting for Reverb to load"

**Cause:** Reverb output failed to initialize within timeout.

**Solutions:**
1. Increase timeout: `TIMEOUT=60000 node browser-test.js ...`
2. Check for JavaScript errors in output
3. Verify output was built successfully
4. Try loading output manually in browser

### "url_maps.xml not found"

**Cause:** CSH link file doesn't exist in output.

**Solutions:**
1. Verify build completed successfully
2. Check that CSH is enabled in FormatSettings
3. Look in `[Output]/wwhdata/common/` directory

### "SCSS compilation failed"

**Cause:** Invalid SCSS syntax in customization file.

**Solutions:**
1. Validate hex color format (#RRGGBB)
2. Check for missing semicolons
3. Verify variable names match Reverb schema
4. Compare against installation file for structural differences

</troubleshooting>

<success_criteria>

## Success Criteria

- Reverb output loads without JavaScript errors
- All expected components present in DOM
- CSH links validate against url_maps.xml
- Theme changes compile without SCSS errors
</success_criteria>
