---
name: reverb2
description: >
  AUTHORITATIVE REFERENCE for WebWorks Reverb 2.0 output. Use when testing
  Reverb output in browser, statically linting output for structural breakage
  (self-closed elements, manifest/parcel GroupID consistency), analyzing CSH
  links, customizing SCSS themes (including the 2026.1 `custom.scss` layer),
  inspecting url_maps.xml, generating test reports, or (2026.1+) inspecting
  federated/composed sites and their wwcomposition descriptors, the splash
  Groups Grid, or the Assistant avatar.
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

<runtime_architecture>

## Runtime Architecture

Reverb 2.0 runtime output is built from three source types in `<format name>/Pages/`. Start here when diagnosing any runtime issue.

| Source | Published as | Role |
|--------|--------------|------|
| `Pages/scripts/*.js` | `.js` (loaded by runtime) | JavaScript behavior — keyboard shortcuts, search, navigation, runtime initialization |
| `Pages/*.asp` | `.html` / `.htm` | HTML templates rendered into the published topic and chrome pages |
| `Pages/sass/*.scss` | `.css` | Stylesheets compiled during publish; `_*.scss` partials are configurable variable collections |

When investigating a runtime issue — a theme override that didn't apply, a broken search, a navigation glitch, a missing chrome element — look in `Pages/` first. The published output is transformed; the source of truth lives in these three directories.

**Detailed SCSS guidance:** `## SCSS Customization` (below) and `references/scss-architecture.md`.

**Some chrome is built at runtime, not published (2026.1).** Two surfaces have no markup in the `.asp` at all — the template ships an empty container and JavaScript fills it:

| Surface | Container in the template | Built by |
|---------|---------------------------|----------|
| Splash **Groups Grid** (EPUB2907) | `Splash.asp` → `<nav id="splash_groups" class="ww_skin_splash_groups">` | `connect.js` collects card data from the master TOC → `page.js` builds the DOM |
| Assistant **avatar** (EPUB2911) | — (every assistant slot) | `assistant.js` `Assistant_RenderAvatar` |

Reading the template or grepping the published HTML for the card markup finds nothing; read the JavaScript instead. `splash.png` is **no longer referenced by any template** — a project that overrode it must now override `Splash.asp`. Full treatment, including the `$splash_groups_*` variables and the `ww_skin_*` hooks: `references/runtime-rendered-ui.md`.

**Federated parcel composition (new in 2026.1):** a Reverb site can be assembled from independently built parcels under a shared shell. Builds emit `wwcomposition*` descriptor files (inert in standalone sites), shells legitimately have an empty `#parcels` tree, and a composed mirror mixes GroupIDs and generation hashes from different builds — all of which changes what linting and browser testing should expect. Where each parcel lands in the composed TOC follows a three-rung ladder (composition Merge Settings → the parcel's own declared containers → discovery order), and every placement problem degrades to top-level placement rather than failing the compose. See `references/federation-architecture.md` before flagging any of those as breakage.
</runtime_architecture>

<related_skills>

## Related Skills

| Skill | Relationship |
|-------|--------------|
| **epublisher** | Use to understand project structure and product foundations; see `../epublisher/references/product-foundations.md` for cross-cutting product knowledge |
| **markdown-integration** | When Markdown++ sources feed Reverb output; covers how aliases drive `url_maps.xml` entries and how markers feed the search index |
| **automap** | Use to rebuild output after SCSS customizations |

**External:**

- **markdown-plus-plus** ([`quadralay/markdown-plus-plus`](https://github.com/quadralay/markdown-plus-plus)) — Markdown++ format syntax for marker and alias authoring. Install separately when authoring the source documents that feed Reverb output.

**After customizing themes:** Use the automap skill to rebuild the Reverb target.

</related_skills>

<intake>

## What would you like to do?

1. Test Reverb output in browser
2. Analyze CSH links
3. Customize SCSS theme
4. Generate test report
5. Resolve a stable Reverb landmark URL (or hash) to a direct file path
6. Lint output for structural breakage (static, no browser)

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
| 5, "resolve", "landmark", "hash" | workflows/landmark-resolution.md |
| 6, "lint", "validate", "static", "pre-flight" | workflows/output-linting.md |
</routing>

<capabilities>

## Capabilities

| Feature | Script | Description |
|---------|--------|-------------|
| Output Linting | `lint-output.py` | Static pre-flight (no browser): self-closed non-void elements, manifest↔parcel GroupID consistency, parcel deploy-unit completeness, asset reference integrity, splash Groups Grid container. CI-friendly exit codes |
| Browser Testing | `browser-test.js` | Load output in headless Chrome; pass/fail on the `preload` load signal (`--vanilla` for no-bypass file:// mode) |
| CSH Analysis | `parse-url-maps.py` | Extract topic mappings from url_maps.xml |
| SCSS Theming | `extract-scss-variables.py` | Read current theme values |
| Entry Detection | `detect-entry-point.sh` | Find output location from project |
| Report Generation | `generate-report.py` | Create formatted test reports |
| Landmark Resolution | `resolve-landmarks.py` | Resolve Reverb stable URLs (#/<id>) to direct file paths using _lx.js chunks |
</capabilities>

<output_linting>

## Output Linting (static pre-flight)

`lint-output.py` statically scans a built or assembled Reverb 2.0 output
directory for structural breakages that kill the runtime **silently** — the page
hangs on the spinner with no console error — and that are detectable without a
browser. Run it in CI or before a deploy.

### Run

```bash
python scripts/lint-output.py <output-dir> [--json] [--strict] [--no-color]
```

`<output-dir>` is the folder containing `index.html` (e.g.
`"Output/WebWorks Reverb 2.0"`).

### Checks

| Check | Severity | What it catches |
|-------|----------|-----------------|
| `self-closed-element` | error | A non-void element in XML self-closing form (`<script/>`, `<iframe/>`, `<div/>`, …). In `text/html` the `/` is ignored, so the element swallows the rest of the document — the first page never renders, with **zero** console errors. (Trac #2792.) Void elements (`<meta/>`, `<link/>`, …) and `<svg>`/`<math>` foreign content are exempt. |
| `manifest-parcel-groupid` | error | The parcel's own GroupID disagrees with what the `#parcels` manifest binds. `connect.js` reads `id.split(':')[1]` from each anchor `<a id="<ctx>:<GID>" href="<Name>.html">` and looks up `toc:<GID>`/`data:<GID>`/`page:<GID>` inside the fetched parcel; a mismatch means every lookup returns null, the parcel never attaches, and the spinner hangs. Arises when output is assembled from multiple builds. Also flags a `<li id="group:<GID>">`-vs-anchor desync. |
| `parcel-deploy-unit` | error | A manifest parcel `<Name>` is missing a deploy-unit member: `<Name>.html` and `<Name>/` (always), plus the runtime chunks `<Name>_ix.html`/`<Name>_lx.js`/`<Name>_sx.js`. The required chunk set is version/feature dependent (older builds omit `_lx.js`, search-off builds omit `_sx.js`), so it is read from the build's own `scripts/connect.js`. |
| `reference-integrity` | warn | A local `scripts/`/`css/` asset referenced by `index.html` (`<script src>`, `<link href>`) is missing on disk. Remote (`http(s)://`, `//`) and `data:` refs are skipped. |
| `splash-groups-container` | warn | `splash.html` lacks the `id="splash_groups"` container that this build's `page.js` renders the Groups Grid into — the splash comes up empty with no console error. Usually a pre-2026.1 `Splash.asp` override carried through an upgrade (EPUB2907). Skipped when `page.js` has no `splash_groups` lookup, so pre-2026.1 output is never flagged. |

The check set is extensible — add new known-breakage checks to `lint-output.py`
as they are discovered.

### Exit codes (CI-friendly)

| Code | Meaning |
|------|---------|
| `0` | Clean — no errors (and no warnings under `--strict`). |
| `1` | At least one error-severity finding (or any warning under `--strict`). |
| `2` | The linter could not run — `<output-dir>` missing or not a directory. |

Files scanned for self-closed elements: `index.html`, the root shell pages
(`search.html`, `splash.html`, `not-found.html`), and each parcel's `<Name>.html`
and `<Name>_ix.html`.

### Relationship to browser testing

The linter is the **static** pre-flight (cheap, no browser). `browser-test.js` is
the **runtime** confirmation (the `preload` load signal; needs Chrome). A good
flow runs the linter first to catch structural breakage, then the browser test to
confirm the build actually loads. See `workflows/output-linting.md`.

</output_linting>

<browser_testing>

## Browser Testing

### Run Test

```bash
node scripts/browser-test.js <chrome-path> <entry-url> [format-settings-json] [--vanilla]
```

### Pass/Fail Signal (read this first)

**Primary signal — the only reliable one:** a load succeeded when the **`preload` class is removed from `<body id="connect_body">`**. `connect.js` removes it only in its `page_load_complete` handler, which fires when the **first content page** actually renders inside `page_iframe`.

- **Loaded OK** → `preloadCleared: true` (spinner cleared, first page rendered) → `success: true`, exit 0.
- **Broken / stuck** → `preload` still present after the load settles → `preloadCleared: false` → `success: false`, exit 1.

**Do not gate on `Parcels.loaded_all` or "no console errors."** `connect.js` catches exceptions internally, so a broken build can report `Parcels.loaded_all === true` (or fail silently) while the page is stuck on the spinner with no content. These are recorded only as **secondary diagnostics** (`parcelsLoadedAll`, `errors`, `warnings`, `components`).

### Vanilla (no-bypass) mode

By default `browser-test.js` launches Chrome with `--disable-web-security --allow-file-access-from-files`. Those flags let the parent read cross-origin iframe DOM that a real double-click cannot, so they **mask `file://`-only breakage** — the test can pass on output that is broken for users opening it from disk.

Pass `--vanilla` (or set `VANILLA=1`) to launch **without** the bypass flags and reproduce exactly what a user gets double-clicking `index.html`. Use it to catch `file://`-only regressions. The preload signal works in both modes because it reads the top-level `body#connect_body`, which is always same-origin.

### What It Checks

- **Primary:** `preload` removed from `body#connect_body` (`preloadCleared`)
- Secondary diagnostics: `Parcels.loaded_all`, console errors/warnings, component presence (toolbar, header, footer, TOC, content), FormatSettings validation

### DOM Component IDs

| Component | DOM ID | Presence Check |
|-----------|--------|----------------|
| **Load signal** | `body#connect_body` | **`preload` class absent** (primary pass/fail) |
| Toolbar | `#toolbar_div` | `childNodes.length > 0` |
| Header | `#header_div` | `childNodes.length > 0` |
| Footer | `#footer_div` | `childNodes.length > 0` OR `#ww_skin_footer` exists |
| TOC | `#toc` | `childNodes.length > 0` |
| Content | `#page_div` | Contains `#page_iframe` |

### Output Format

```json
{
  "success": true,
  "preloadCleared": true,
  "reverbLoaded": true,
  "vanillaMode": false,
  "loadTime": 1039,
  "parcelsLoadedAll": true,
  "diagnostics": {
    "bodyId": "connect_body",
    "hasPreloadClass": false,
    "parcelsLoadedAll": true,
    "firstPageLoaded": true,
    "readyState": "complete"
  },
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

`success`, `preloadCleared`, and `reverbLoaded` all reflect the same primary signal. `parcelsLoadedAll` is the secondary, **unreliable** diagnostic — never treat it as the pass condition.
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

**Recommended setup (new projects):** Leave the *Skin* target setting unset and customize the Reverb 2.0 format directly — Layer 1 variable overrides plus, for structural CSS, `custom.scss` on 2026.1+ (or `_custom-skin.scss` / `_custom-webworks.scss` on earlier builds), applied at the Formats or Targets level. Don't start from a packaged skin (`.weplugin`/Skin); those are deprecated. Full rationale, plus the customer-migration delivery pattern (reference / match / no-skin targets), in `references/scss-architecture.md` § "Recommended Setup for New Projects: No Skin" and § "Migration Delivery Pattern".

### Theming Layers

| Layer | What it controls | Override file | Entry point |
|-------|-----------------|---------------|-------------|
| **1. Variable overrides** | Colors, sizes, fonts, icons, borders | `_colors.scss`, `_sizes.scss`, etc. | Compiled by `skin.scss`, `webworks.scss`, `custom.scss` |
| **2. Custom selectors** *(2026.1+)* | Anything, any page type — chrome and content alike | `custom.scss` (replace the stock file) | Ships pre-wired: `css/custom.css`, linked **last** |
| **2a. Skin CSS** | Toolbar, TOC, navigation chrome | `_custom-skin.scss` (user-created) | Imported by `skin.scss` |
| **2b. Content page CSS** | Content fonts, links, tables, mini-TOC | `_custom-webworks.scss` (user-created) | Imported by `webworks.scss` |

Layer 1 is safest (variable values only). Layers 2a–2b require copying entry points and adding import hooks — they do **not** ship with custom imports pre-configured.

**`custom.scss` (EPUB2908, 2026.1+)** is the seam to prefer for structural CSS. The stock `Pages/sass/custom.scss` compiles to `css/custom.css`, which `Connect.asp`, `Page.asp`, `Splash.asp`, `NotFound.asp`, `Popup.asp`, and `Search.asp` all link **last** — so its rules win equal-specificity contests against every stock sheet, on every page type including popups, and `@media print` rules there beat `print.css`. It imports the variable partials (so skin variables are usable) and emits no rules of its own. Customize by copying it into `Targets/<Target>/Pages/sass/` or `Formats/WebWorks Reverb 2.0/Pages/sass/` — the copy replaces it entirely, so keep the `@import` block. No entry point to copy, no import hook, nothing to re-apply at upgrade. The trade-off is that one sheet means one cascade depth: `custom.css` loads after **both** `webworks.css` and `skin.css`, so scope your selectors instead of relying on sheet order. The older two-partial pair still works and is not deprecated — comparison table in `references/scss-architecture.md` § "The `custom.scss` Layer".

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

> **Slot varies by config:** which `$_layout_color_*` slot a component variable (e.g. `$toolbar_background_color`) is wired to can differ between the base format and a packaged skin. Verify the slot→property mapping in the actual `_colors.scss` rather than assuming — see `references/scss-architecture.md` § "Tier 3 — Component Variables".

**Strict rules** (full treatment: `references/scss-architecture.md` § "Strict Rules for Prefixed Variables"):

- Define each brand color once with a `$theme_` / `$<project>_` prefix and assign it to the layout slots first.
- **Reference the prefixed variable at every override site** — never a `$_layout_color_*` slot or a `$neo_*` variable.
- **Don't introduce new auxiliary variables.** Pass the prefixed var straight into `darken()` / `lighten()` (`darken($theme_primary, 10%)`); don't create a derived `$..._d15`.

### Extract Current Values

```bash
python scripts/extract-scss-variables.py <project-dir> neo
# Categories: neo, layout, colors, sizes, toolbar, header, footer, menu, page, search, link, all
```

### Override Priority

Highest first (file resolver hierarchy):
1. `[Project]/Targets/[Target]/Pages/sass/_colors.scss` — single target
2. `[Project]/Formats/WebWorks Reverb 2.0/Pages/sass/_colors.scss` — all targets
3. `[Project]/Formats/WebWorks Reverb 2.0.base/Pages/sass/_colors.scss` — packaged defaults
4. `[Install]/Formats/WebWorks Reverb 2.0/Pages/sass/_colors.scss` — installation fallback

**Detailed guidance:** `workflows/scss-theming.md` (layer-specific steps), `references/scss-architecture.md` (cascade diagrams, compilation model, `custom.scss` layer, strict variable rules), `references/runtime-rendered-ui.md` (splash Groups Grid and Assistant avatar — runtime-built DOM, `$splash_groups_*` variables, `ww_skin_*` hooks), `references/customization-conventions.md` (annotations for non-SCSS overrides, `locales.xml` upgrade).
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

# 2. Static pre-flight — fail fast on structural breakage before launching Chrome
python scripts/lint-output.py "output/WebWorks Reverb 2.0" || exit 1

# 3. Run browser test (runtime confirmation)
TEST_RESULTS=$(node scripts/browser-test.js "$CHROME" "$ENTRY_URL")

# 4. Parse CSH
CSH_DATA=$(python scripts/parse-url-maps.py output/url_maps.xml)

# 5. Generate report
python scripts/generate-report.py project.wep "$PROJECT_INFO" "$CSH_DATA" "$TEST_RESULTS"
```

### Apply Brand Colors

```bash
# 1. Check current colors
python scripts/extract-scss-variables.py /path/to/project neo

# 2. Copy _colors.scss to project, add $theme_* variables, map to $_layout_color_*
#    See workflows/scss-theming.md Step 3 for detailed instructions

# 3. Rebuild with automap skill
```
</common_workflows>

<common_mistakes>

## Common Mistakes

**Do not apply general web development patterns to Reverb.** Reverb 2.0 is a single-page application with its own JavaScript runtime (`Parcels`), navigation model, and SCSS architecture. Standard web debugging assumptions (e.g., "check the network tab for 404s") may not apply. Always consult the format's source files first.

**`.weplugin` skin packages are deprecated.** These are zip archives typically containing `_colors.scss`, sometimes `_sizes.scss`, and occasionally `Connect.asp`. They will be removed in Reverb 3.0. To migrate: rename to `.zip`, extract, diff against installation defaults to identify actual customizations, then copy customized partials to the appropriate override level (`Formats/WebWorks Reverb 2.0/Pages/sass/` or `Targets/[Target]/Pages/sass/`). Use direct SCSS variable overrides with the `$theme_` naming convention instead. For structural CSS beyond variables, override `custom.scss` on 2026.1+ (see `references/scss-architecture.md` § "The `custom.scss` Layer") or create `_custom-skin.scss` (chrome) / `_custom-webworks.scss` (content) on earlier builds — see § "Why Two Custom Partials, Not One". A packaged skin that ships its own full `connect.scss` also has to carry format-side fixes to that sheet forward by hand (the 2026.1 Assistant avatar rules, for instance) — one more reason not to start from one. When moving a customer off a *skinned look* (a redesign, not a like-for-like port), follow the reference / match / no-skin delivery pattern in `references/scss-architecture.md` § "Migration Delivery Pattern". For non-SCSS overrides (`locales.xml`, ASP templates), see `references/customization-conventions.md`.

**Reverb output is not the format source.** The generated HTML/CSS/JS in the output directory is transformed output. To understand or fix runtime behavior, examine the format source files: `Pages/scripts/*.js` for JavaScript, `Pages/*.asp` for HTML templates, `Pages/sass/*.scss` for styles.

**Some chrome isn't in the template either (2026.1).** The splash Groups Grid and the Assistant avatar are built at runtime by `page.js` / `connect.js` / `assistant.js` into containers the templates ship empty. Reading `Splash.asp` — or grepping the published HTML for card markup — finds nothing and proves nothing. See `references/runtime-rendered-ui.md`.

</common_mistakes>

<troubleshooting>

## Troubleshooting

### "Chrome not found"

**Cause:** Chrome/Chromium not installed or not in expected location.

**Solutions:**
1. Install Chrome from https://www.google.com/chrome/
2. Set `CHROME_PATH` environment variable
3. Edge Chromium can be used as fallback

### "Reverb never finished loading: 'preload' class still present"

**Cause:** The `preload` class was never removed from `body#connect_body` within the timeout — the first content page never rendered, so the spinner is stuck. This is a genuine broken-load signal, **not** a flaky timeout. Note that `parcelsLoadedAll: true` and an empty `errors` array can both still appear here — that is exactly the false-"passed" case this signal exists to catch.

**Solutions:**
1. Inspect `diagnostics` (`firstPageLoaded`, `parcelsLoadedAll`, `readyState`) and the saved screenshot (`SCREENSHOT_PATH`) — a stuck spinner confirms the broken load.
2. Re-run with `--vanilla` to check whether the breakage is `file://`-only (the default bypass flags can hide it).
3. If the build is large/slow, increase the timeout: `TIMEOUT=60000 node browser-test.js ...` — but a truly stuck build will still fail at any timeout.
4. Check the format source (`Pages/scripts/connect.js`, parcel manifest) and rebuild.

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

- Reverb output fully loads — `preload` removed from `body#connect_body` (`preloadCleared: true`)
- All expected components present in DOM (secondary diagnostic)
- CSH links validate against url_maps.xml
- Theme changes compile without SCSS errors
</success_criteria>
