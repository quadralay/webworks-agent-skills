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
| **epublisher** | Use to understand project structure before testing |
| **automap** | Use to rebuild output after SCSS customizations |

**After customizing themes:** Use the automap skill to rebuild:
```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/automap/scripts/automap-wrapper.sh -c -n -t "WebWorks Reverb 2.0" project.wep
```

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
| CSH Analysis | `parse-url-maps.sh` | Extract topic mappings from url_maps.xml |
| SCSS Theming | `extract-scss-variables.sh` | Read current theme values |
| Color Override | `generate-color-override.sh` | Generate brand color files |
| Entry Detection | `detect-entry-point.sh` | Find output location from project |
| Report Generation | `generate-report.sh` | Create formatted test reports |
</capabilities>

<browser_testing>

## Browser Testing

### Run Test

```bash
node ${CLAUDE_PLUGIN_ROOT}/skills/reverb2/scripts/browser-test.js <chrome-path> <entry-url> [format-settings-json]
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
bash ${CLAUDE_PLUGIN_ROOT}/skills/reverb2/scripts/parse-url-maps.sh <url-maps-file> [format]
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

### Theme Variables

Reverb uses 6 "neo" variables for quick theming:

```scss
$neo_main_color: #008bff;           // Primary (toolbar, buttons, links)
$neo_main_text_color: #222222;      // Text on primary
$neo_secondary_color: #eeeeee;      // Sidebar background
$neo_secondary_text_color: #fefefe; // Text on dark backgrounds
$neo_tertiary_color: #222222;       // Header/footer background
$neo_page_color: #fefefe;           // Page background
```

### Extract Current Values

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/reverb2/scripts/extract-scss-variables.sh <project-dir> [category]
```

Categories: `neo`, `layout`, `toolbar`, `header`, `footer`, `menu`, `sizes`

### Generate Color Override

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/reverb2/scripts/generate-color-override.sh <output-path> \
  --main-color "#E63946" \
  --main-text "#FFFFFF" \
  --secondary-color "#F1FAEE" \
  --secondary-text "#1D3557" \
  --tertiary-color "#457B9D" \
  --page-color "#F1FAEE"
```

### SCSS File Locations

Override priority (highest first):
1. `[Project]/Targets/[Target]/Pages/sass/_colors.scss`
2. `[Project]/Formats/WebWorks Reverb 2.0/Pages/sass/_colors.scss`
3. `[Project]/Formats/WebWorks Reverb 2.0.base/Pages/sass/_colors.scss`
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
bash ${CLAUDE_PLUGIN_ROOT}/skills/reverb2/scripts/setup-dependencies.sh
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
cd skills/reverb
npm install
```

Installs `puppeteer-core` for headless Chrome automation.

### Chrome/Chromium

Browser testing requires Chrome. Detect with:
```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/reverb2/scripts/detect-chrome.sh
```
</dependencies>

<common_workflows>

## Common Workflows

### Full Output Validation

```bash
# 1. Detect entry point
PROJECT_INFO=$(bash ${CLAUDE_PLUGIN_ROOT}/skills/reverb2/scripts/detect-entry-point.sh project.wep)

# 2. Run browser test
TEST_RESULTS=$(node ${CLAUDE_PLUGIN_ROOT}/skills/reverb2/scripts/browser-test.js "$CHROME" "$ENTRY_URL")

# 3. Parse CSH
CSH_DATA=$(bash ${CLAUDE_PLUGIN_ROOT}/skills/reverb2/scripts/parse-url-maps.sh output/url_maps.xml)

# 4. Generate report
bash ${CLAUDE_PLUGIN_ROOT}/skills/reverb2/scripts/generate-report.sh project.wep "$PROJECT_INFO" "$CSH_DATA" "$TEST_RESULTS"
```

### Apply Brand Colors

```bash
# 1. Check current colors
bash ${CLAUDE_PLUGIN_ROOT}/skills/reverb2/scripts/extract-scss-variables.sh /path/to/project neo

# 2. Generate override
bash ${CLAUDE_PLUGIN_ROOT}/skills/reverb2/scripts/generate-color-override.sh \
  /path/to/project/Formats/WebWorks\ Reverb\ 2.0/Pages/sass/_colors.scss \
  --main-color "#0052CC" --main-text "#FFFFFF"

# 3. Rebuild with automap skill
```
</common_workflows>

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
4. Use `--validate-only` flag to check before copying

</troubleshooting>

<success_criteria>

## Success Criteria

- Reverb output loads without JavaScript errors
- All expected components present in DOM
- CSH links validate against url_maps.xml
- Theme changes compile without SCSS errors
</success_criteria>
