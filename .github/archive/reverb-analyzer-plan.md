# Reverb Output Analyzer Skill - Implementation Plan

**Status:** Planning
**Priority:** High
**Estimated Effort:** 50-72 hours (5-7 working days)
**Created:** 2025-10-31

---

## Overview

Create a new skill within the `epublisher-automation` plugin that can load, analyze, and test WebWorks Reverb 2.0 output. This skill will provide automated testing of generated Reverb output, including JavaScript runtime verification, console error detection, Context Sensitive Help (CSH) link validation, and visual component analysis.

## Problem Statement

### Current Gap

After generating Reverb output with AutoMap, developers have no automated way to:

1. **Verify JavaScript Execution** - Confirm the Reverb runtime loads and executes correctly
2. **Detect Console Errors** - Catch JavaScript errors, failed resources, or runtime issues
3. **Validate CSH Links** - Test Context Sensitive Help integration from `url_maps.xml`
4. **Analyze Layout Components** - Inspect toolbar, header, footer, menu, and content area configuration
5. **Test Entry Points** - Confirm the correct entry point (default `index.html`) is accessible
6. **Preview Customizations** - Validate skin, color, and layout changes before deployment

### Why This Matters

**For Development:**
- Automated quality checks catch issues before deployment
- Faster feedback loop for customization changes
- Consistent testing across different projects and targets

**For Debugging:**
- Immediate visibility into JavaScript errors
- Resource loading failures detected early
- CSH integration issues identified quickly

**For Future Customization:**
- Foundation for skin design workflows
- Visual component inspection for custom layouts
- Color scheme testing and validation

---

## Browser Automation Technology Decision

### Technology Comparison Summary

| Feature | Playwright | **Puppeteer (Recommended)** | CDP Direct |
|---------|-----------|---------------------------|------------|
| **Abstraction Level** | High | High | Low |
| **Browser Support** | Multi-browser | Chrome/Chromium | Chrome only |
| **Installation Size** | ~200MB | **~5MB*** | 0MB |
| **Learning Curve** | Easy | Easy | Steep |
| **Auto-Waiting** | ✅ | ✅ | ❌ Manual |
| **Console Monitoring** | ✅ Built-in | ✅ Built-in | ⚠️ Manual setup |
| **Screenshots** | ✅ Simple | ✅ Simple | ❌ Complex |
| **DOM Inspection** | ✅ Rich API | ✅ Rich API | ⚠️ Raw protocol |
| **Maintenance** | Microsoft | Google | Chrome native |

_* Using `puppeteer-core` with system Chrome avoids browser download_

### Why Puppeteer?

**Chosen Technology:** Puppeteer (via `puppeteer-core`)

**Rationale:**

✅ **Lightweight** - Uses system Chrome, no browser download (5MB vs 200MB)
✅ **High-Level API** - Simple console monitoring and DOM inspection
✅ **Chrome-Focused** - Reverb output typically tested in Chrome/Edge
✅ **Feature-Rich** - Built-in waiting, error handling, screenshots
✅ **Google-Backed** - Stable, well-documented, actively maintained
✅ **Windows Compatible** - Works seamlessly in Git Bash environment

**vs Playwright:**
- Lighter weight (5MB vs 200MB)
- Don't need multi-browser support for this use case
- Can always upgrade later if cross-browser testing needed

**vs Direct CDP:**
- Much simpler API for console monitoring
- Built-in retry and wait logic
- Better error messages
- Faster development time

### Rejected Alternatives

#### ❌ Playwright (Too Heavy)
- 200MB download with bundled browsers
- Overkill for Chrome-only testing
- Unnecessary overhead for our use case

#### ❌ Direct Chrome DevTools Protocol (Too Complex)
- Low-level protocol requires extensive code
- Manual wait/retry logic
- Steep learning curve
- More development time

#### ❌ Selenium WebDriver (Outdated)
- Requires WebDriver binary management
- Slower than modern tools
- Less suitable for headless testing
- Superseded by Puppeteer/Playwright

---

## Proposed Solution

### Four Core Capabilities

#### 1. Output Loading & Browser Automation
- Detect Reverb output directory from project configuration
- Determine entry point (default `index.html`, configurable via project settings)
- Launch headless browser to load Reverb output
- Wait for Reverb JavaScript runtime to fully initialize
- Capture page load metrics and timing

#### 2. Console Error Detection
- Monitor browser console for errors, warnings, and failures
- Categorize issues by severity (error, warning, info)
- Report failed resource loads (images, CSS, JS)
- Detect JavaScript runtime errors with stack traces
- Filter out expected warnings from third-party libraries

#### 3. Context Sensitive Help Analysis
- Parse `url_maps.xml` from output directory
- Extract CSH links from `<TopicMap>` element
- Display CSH mappings in friendly format (ID → URL → Title)
- Test CSH link navigation in browser
- Report broken or misconfigured CSH links

#### 4. Visual Component Analysis
- Inspect Reverb layout components:
  - **Toolbar** - Logo, search, navigation buttons
  - **Header** - Presence, content, customizations
  - **Footer** - Presence, content, copyright info
  - **Menu** - TOC structure, expand/collapse state
  - **Content Area** - Main content rendering
- Report which components are enabled/disabled
- Capture component configurations from FormatSettings
- Screenshot capabilities for visual verification

---

## Architecture

### File Structure

```
plugins/epublisher-automation/skills/epublisher-reverb-analyzer/
├── SKILL.md                              # Skill documentation and prompts
├── package.json                          # Node.js dependencies (puppeteer-core)
├── scripts/
│   ├── analyze-reverb-output.sh          # Main analysis orchestrator
│   ├── parse-url-maps.sh                 # CSH link extraction
│   ├── detect-entry-point.sh             # Determine index.html location
│   ├── detect-chrome.sh                  # Find system Chrome installation
│   ├── browser-test.js                   # Puppeteer test script
│   ├── setup-dependencies.sh             # npm install wrapper
│   └── generate-report.sh                # Report generation
├── references/
│   ├── REVERB_STRUCTURE.md               # Reverb output file organization
│   ├── URL_MAPS_FORMAT.md                # url_maps.xml schema documentation
│   ├── BROWSER_AUTOMATION_GUIDE.md       # Puppeteer patterns and examples
│   ├── CHROME_DETECTION.md               # Finding Chrome on Windows
│   └── COMPONENT_IDS.md                  # Reverb DOM element reference
└── templates/
    └── test-report-template.md           # Analysis report format
```

### Main Orchestrator Flow

```bash
#!/bin/bash
# analyze-reverb-output.sh

# 1. Detect output directory from project file
output_dir=$(./scripts/detect-entry-point.sh "$project_file")

# 2. Find system Chrome
chrome_path=$(./scripts/detect-chrome.sh)

# 3. Ensure dependencies installed
./scripts/setup-dependencies.sh

# 4. Parse CSH links
csh_data=$(./scripts/parse-url-maps.sh "$output_dir/url_maps.xml")

# 5. Run browser tests
test_results=$(node ./scripts/browser-test.js "$chrome_path" "file://$output_dir/index.html")

# 6. Generate report
./scripts/generate-report.sh "$test_results" "$csh_data"
```

---

## ePublisher Reference Library

This section provides comprehensive reference information for WebWorks ePublisher Reverb format, including FormatSettings, SASS customization, and component mappings. These references will be created during implementation and serve as the knowledge base for the analyzer skill.

### FormatSettings Complete Reference

FormatSettings control Reverb component behavior and appearance. These settings are defined in the project file within `<FormatSettings>` elements.

#### Entry Point & File Configuration

| Setting Name | Default Value | Component Affected | Description |
|--------------|---------------|-------------------|-------------|
| `connect-entry` | `index.html` | Entry point | Initial HTML file loaded by Reverb runtime |
| `connect-url-maps-name` | `url_maps.xml` | CSH mapping file | Context Sensitive Help mapping file name |
| `show-first-document` | `true` | Initial navigation | Whether to show first document on load |

**Detection Pattern:**
```xml
<FormatSetting Name="connect-entry" Value="index.html" />
```

**Parsing Logic:**
```bash
# Extract entry point from project file
entry_point=$(grep -oP '<FormatSetting Name="connect-entry" Value="\K[^"]+' project.wep)
if [ -z "$entry_point" ]; then
  entry_point="index.html"  # Default
fi
```

#### Toolbar Configuration

| Setting Name | Default Value | Component Affected | Description |
|--------------|---------------|-------------------|-------------|
| `toolbar-logo` | `none` | #ww-toolbar img.ww-logo | Toolbar logo display mode |
| `toolbar-logo-linked` | `false` | Toolbar logo link | Whether toolbar logo is clickable |
| `toolbar-generate` | `true` | #ww-toolbar | Enable/disable entire toolbar |
| `toolbar-search` | `true` | Toolbar search box | Show/hide search functionality |

**Component Mapping:**
- `toolbar-logo = "none"` → No logo element in DOM
- `toolbar-logo = "left"` → Logo on left side of toolbar
- `toolbar-logo = "center"` → Logo centered in toolbar
- `toolbar-generate = "false"` → No `#ww-toolbar` element

#### Header Configuration

| Setting Name | Default Value | Component Affected | Description |
|--------------|---------------|-------------------|-------------|
| `header-generate` | `false` | #ww-header | Enable/disable header section |
| `header-logo` | `none` | #ww-header img.ww-logo | Header logo display mode |
| `header-logo-linked` | `false` | Header logo link | Whether header logo is clickable |
| `header-location` | `before-toolbar` | Header position | Where header appears in layout |

**Component Mapping:**
- `header-generate = "false"` → No `#ww-header` element in DOM
- `header-generate = "true"` → `#ww-header` present with configured logo

#### Footer Configuration

| Setting Name | Default Value | Component Affected | Description |
|--------------|---------------|-------------------|-------------|
| `footer-generate` | `false` | #ww-footer | Enable/disable footer section |
| `footer-logo` | `none` | #ww-footer img.ww-logo | Footer logo display mode |
| `footer-logo-linked` | `false` | Footer logo link | Whether footer logo is clickable |
| `footer-location` | `end-of-layout` | Footer position | Where footer appears (end-of-page or end-of-layout) |

**Component Mapping:**
- `footer-generate = "false"` → No `#ww-footer` element
- `footer-location = "end-of-page"` → Footer inside content pages
- `footer-location = "end-of-layout"` → Footer at bottom of viewport

#### TOC Menu Configuration

| Setting Name | Default Value | Component Affected | Description |
|--------------|---------------|-------------------|-------------|
| `toc-generate` | `true` | #ww-toc | Enable/disable table of contents |
| `toc-initial-state` | `expanded` | TOC initial display | Whether TOC starts expanded or collapsed |
| `toc-width` | `300px` | TOC panel width | Width of TOC sidebar |

**Component Mapping:**
- `toc-generate = "false"` → No `#ww-toc` element
- `toc-initial-state = "expanded"` → TOC has `.expanded` class on load

### SASS Variable Files Reference

Reverb uses SASS for styling with variables organized into modular files. Each file controls specific aspects of the design.

#### File: `_colors.scss`

**Purpose:** Defines all color variables used throughout Reverb

**Variable Categories:**
- **Brand Colors:** Primary, secondary, accent colors
- **Background Colors:** Page, panel, sidebar backgrounds
- **Text Colors:** Body, heading, link colors
- **Component Colors:** Toolbar, header, footer specific colors
- **State Colors:** Hover, active, disabled states

**Common Variables:**
```scss
$color-primary: #0066cc;          // Primary brand color
$color-secondary: #6c757d;        // Secondary/accent color
$color-background: #ffffff;       // Main background
$color-text: #212529;             // Body text color
$color-link: $color-primary;      // Link color
$color-link-hover: darken($color-primary, 10%);
```

**Usage in Phase 5:**
- Color scheme testing and customization
- Before/after screenshot comparisons
- Theme generation

#### File: `_fonts.scss`

**Purpose:** Typography definitions including font families, sizes, and weights

**Variable Categories:**
- **Font Families:** Body, heading, monospace
- **Font Sizes:** Base size and scale
- **Line Heights:** For readability
- **Font Weights:** Normal, bold, light

**Common Variables:**
```scss
$font-family-base: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto;
$font-family-heading: $font-family-base;
$font-family-mono: "Courier New", monospace;

$font-size-base: 16px;
$font-size-h1: 2rem;
$font-size-h2: 1.75rem;

$line-height-base: 1.5;
$font-weight-normal: 400;
$font-weight-bold: 700;
```

#### File: `_sizes.scss`

**Purpose:** Spacing, dimensions, and layout measurements

**Variable Categories:**
- **Spacing:** Margins, padding scales
- **Component Sizes:** Toolbar height, sidebar width
- **Layout Breakpoints:** Responsive design points
- **Border Radii:** Corner rounding

**Common Variables:**
```scss
$spacing-unit: 8px;               // Base spacing unit
$spacing-xs: $spacing-unit * 0.5; // 4px
$spacing-sm: $spacing-unit;       // 8px
$spacing-md: $spacing-unit * 2;   // 16px
$spacing-lg: $spacing-unit * 3;   // 24px

$toolbar-height: 60px;
$sidebar-width: 300px;
$border-radius: 4px;
```

#### File: `_borders.scss`

**Purpose:** Border styles, widths, and colors

**Variable Categories:**
- **Border Widths:** Thin, medium, thick
- **Border Colors:** Default, light, dark
- **Border Styles:** Solid, dashed, dotted

**Common Variables:**
```scss
$border-width: 1px;
$border-color: #dee2e6;
$border-style: solid;
$border: $border-width $border-style $border-color;
```

#### File: `_icons.scss`

**Purpose:** Icon sizes, colors, and SVG definitions

**Variable Categories:**
- **Icon Sizes:** Small, medium, large
- **Icon Colors:** Default, hover, active states
- **SVG Paths:** Common icon definitions

**Usage:**
- Navigation icons
- Search icon
- Menu toggle icons
- Print/download icons

### Component Detection to FormatSettings Mapping

This table shows how to correlate detected DOM elements with their controlling FormatSettings:

| DOM Element | CSS Selector | FormatSetting | Expected Value |
|-------------|-------------|---------------|----------------|
| Toolbar | `#ww-toolbar` | `toolbar-generate` | `true` if present |
| Toolbar Logo | `#ww-toolbar img.ww-logo` | `toolbar-logo` | `none`, `left`, or `center` |
| Header | `#ww-header` | `header-generate` | `true` if present |
| Header Position | `#ww-header` parent | `header-location` | Check DOM position |
| Footer | `#ww-footer` | `footer-generate` | `true` if present |
| Footer Position | `#ww-footer` parent | `footer-location` | Check DOM position |
| TOC Menu | `#ww-toc` | `toc-generate` | `true` if present |
| TOC State | `#ww-toc.expanded` | `toc-initial-state` | `expanded` if class present |
| Content Area | `#ww-content` | Always present | N/A |

**Validation Logic:**
```javascript
// Example: Validate toolbar-logo setting
const toolbarLogo = await page.$('#ww-toolbar img.ww-logo');
const logoSetting = getFormatSetting('toolbar-logo'); // From project file

if (logoSetting === 'none' && toolbarLogo !== null) {
  console.warn('Mismatch: toolbar-logo=none but logo element exists');
} else if (logoSetting !== 'none' && toolbarLogo === null) {
  console.warn('Mismatch: toolbar-logo set but no logo in DOM');
}
```

### Reference Documents to Create During Implementation

These reference documents will be created as deliverables in each phase:

**Phase 1 Deliverables:**
- `FORMAT_SETTINGS_REFERENCE.md` - Complete catalog with defaults and mappings
- `REVERB_STRUCTURE.md` - Output directory organization

**Phase 3 Deliverables:**
- `COMPONENT_IDS.md` - DOM element reference with selectors
- `COMPONENT_FORMATSETTINGS_MAP.md` - Correlation matrix

**Phase 5 Deliverables (Future):**
- `SASS_CUSTOMIZATION_GUIDE.md` - Variable file deep-dive
- `COLOR_SCHEME_EXAMPLES.md` - Pre-built color schemes
- `LAYOUT_PATTERNS.md` - Common layout configurations

---

## Implementation Phases

### Phase 1: Foundation & Detection (Week 1)

**Duration:** 8-12 hours

**Deliverables:**
- `detect-entry-point.sh` - Parse project file to find output directory and entry point
- `detect-chrome.sh` - Locate system Chrome installation (common Windows paths)
- `parse-url-maps.sh` - Extract CSH data from `url_maps.xml`
- `setup-dependencies.sh` - Install puppeteer-core if not present
- SKILL.md documentation framework

**Success Criteria:**
- ✅ Can parse project file to determine output location
- ✅ Can find Chrome executable on Windows
- ✅ Can extract CSH mappings from url_maps.xml
- ✅ Dependencies install without errors

**Files to Create:**
- `scripts/detect-entry-point.sh` (~100 lines)
- `scripts/detect-chrome.sh` (~80 lines)
- `scripts/parse-url-maps.sh` (~120 lines)
- `scripts/setup-dependencies.sh` (~60 lines)
- `references/REVERB_STRUCTURE.md` (~200 lines)
- `references/FORMAT_SETTINGS_REFERENCE.md` (~400 lines) - Complete FormatSettings catalog with defaults, component mappings, and XML extraction patterns

**Chrome Detection Example:**
```bash
#!/bin/bash
# detect-chrome.sh

CHROME_PATHS=(
  "/c/Program Files/Google/Chrome/Application/chrome.exe"
  "/c/Program Files (x86)/Google/Chrome/Application/chrome.exe"
  "$LOCALAPPDATA/Google/Chrome/Application/chrome.exe"
)

for path in "${CHROME_PATHS[@]}"; do
  if [ -f "$path" ]; then
    echo "$path"
    exit 0
  fi
done

# Allow manual override
if [ -n "$CHROME_PATH" ]; then
  echo "$CHROME_PATH"
  exit 0
fi

echo "ERROR: Chrome not found. Set CHROME_PATH environment variable." >&2
exit 1
```

---

### Phase 2: Browser Automation & Console Monitoring (Week 2)

**Duration:** 12-16 hours

**Deliverables:**
- `browser-test.js` - Puppeteer script for loading Reverb and monitoring console
- Console error categorization (error/warning/info)
- Resource loading failure detection
- JavaScript runtime initialization verification
- JSON output format for bash integration

**Success Criteria:**
- ✅ Can launch headless Chrome with Reverb output
- ✅ Detects JavaScript console errors
- ✅ Reports failed resource loads (images, CSS, JS)
- ✅ Waits for Reverb runtime to fully initialize
- ✅ Returns structured error data to bash script

**Files to Create:**
- `scripts/browser-test.js` (~300 lines)
- `references/BROWSER_AUTOMATION_GUIDE.md` (~400 lines)

**Key Implementation Example:**
```javascript
// browser-test.js outline
const puppeteer = require('puppeteer-core');

async function testReverbOutput(chromePath, outputUrl) {
  const browser = await puppeteer.launch({
    executablePath: chromePath,
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();
  const errors = [];
  const warnings = [];

  // Monitor console messages
  page.on('console', msg => {
    if (msg.type() === 'error') errors.push(msg.text());
    if (msg.type() === 'warning') warnings.push(msg.text());
  });

  // Monitor failed resources
  page.on('requestfailed', request => {
    errors.push(`Failed to load: ${request.url()}`);
  });

  // Load Reverb output
  await page.goto(outputUrl, { waitUntil: 'networkidle2' });

  // Wait for Reverb runtime (adjust timeout as needed)
  await page.waitForFunction(() => window.WWReverb !== undefined, {
    timeout: 10000
  });

  await browser.close();

  // Return results as JSON
  return JSON.stringify({
    errors,
    warnings,
    reverbLoaded: true
  });
}

// CLI interface
const [chromePath, url] = process.argv.slice(2);
testReverbOutput(chromePath, url).then(console.log);
```

---

### Phase 3: Visual Component Analysis (Week 3)

**Duration:** 10-14 hours

**Deliverables:**
- DOM inspection for Reverb components
- Component presence detection (toolbar, header, footer, menu)
- FormatSetting correlation (map enabled components to project settings)
- Screenshot capture for visual verification
- Component configuration reporting

**Success Criteria:**
- ✅ Correctly identifies which components are present
- ✅ Maps component presence to FormatSettings in project file
- ✅ Can capture screenshots of specific components
- ✅ Reports layout structure in friendly format

**Files to Modify:**
- `scripts/browser-test.js` (+150 lines for component analysis)
- `scripts/analyze-reverb-output.sh` (integrate component reporting)

**Files to Create:**
- `references/COMPONENT_IDS.md` (~250 lines) - DOM element reference with CSS selectors
- `references/COMPONENT_FORMATSETTINGS_MAP.md` (~150 lines) - Correlation matrix between DOM elements and FormatSettings

**Component Detection Example:**
```javascript
// Add to browser-test.js

async function analyzeComponents(page) {
  const components = {};

  // Check for toolbar
  components.toolbar = {
    present: await page.$('#ww-toolbar') !== null,
    logo: await page.evaluate(() => {
      const logo = document.querySelector('#ww-toolbar img.ww-logo');
      return logo ? logo.src : null;
    })
  };

  // Check for header
  components.header = {
    present: await page.$('#ww-header') !== null
  };

  // Check for footer
  components.footer = {
    present: await page.$('#ww-footer') !== null
  };

  // Check for TOC menu
  components.menu = {
    present: await page.$('#ww-toc') !== null,
    expanded: await page.evaluate(() => {
      const toc = document.querySelector('#ww-toc');
      return toc ? toc.classList.contains('expanded') : false;
    })
  };

  // Check for content area
  components.content = {
    present: await page.$('#ww-content') !== null
  };

  return components;
}

// Correlate with FormatSettings from project file
async function validateComponentSettings(page, formatSettings) {
  const components = await analyzeComponents(page);
  const mismatches = [];

  // Check toolbar-generate
  if (formatSettings['toolbar-generate'] === 'false' && components.toolbar.present) {
    mismatches.push('toolbar-generate=false but toolbar exists in DOM');
  }

  // Check header-generate
  if (formatSettings['header-generate'] === 'false' && components.header.present) {
    mismatches.push('header-generate=false but header exists in DOM');
  }

  // Check footer-generate
  if (formatSettings['footer-generate'] === 'false' && components.footer.present) {
    mismatches.push('footer-generate=false but footer exists in DOM');
  }

  // Check toc-generate
  if (formatSettings['toc-generate'] === 'false' && components.menu.present) {
    mismatches.push('toc-generate=false but TOC menu exists in DOM');
  }

  return { components, mismatches };
}
```

**FormatSettings Extraction:**
```bash
# In detect-entry-point.sh, also extract FormatSettings
extract_format_settings() {
  local project_file="$1"
  local target_id="$2"

  # Find FormatConfiguration for target
  local settings=$(xmllint --xpath "//FormatConfiguration[@TargetID='$target_id']/FormatSettings/FormatSetting" "$project_file" 2>/dev/null)

  # Convert to JSON for browser-test.js
  echo "$settings" | python3 -c "
import sys, re, json
settings = {}
for line in sys.stdin:
    match = re.search(r'Name=\"([^\"]+)\" Value=\"([^\"]+)\"', line)
    if match:
        settings[match.group(1)] = match.group(2)
print(json.dumps(settings))
"
}
```

---

### Phase 4: Integration & Reporting (Week 4)

**Duration:** 8-12 hours

**Deliverables:**
- `analyze-reverb-output.sh` - Main orchestrator script
- Comprehensive test report generation
- Integration with existing epublisher-core patterns
- SKILL.md complete documentation
- Error handling and user-friendly messages

**Success Criteria:**
- ✅ Single command analyzes entire Reverb output
- ✅ Report includes all findings in clear format
- ✅ Integrates seamlessly with other skills
- ✅ Handles errors gracefully with helpful messages
- ✅ Documentation complete and tested

**Files to Create:**
- `scripts/analyze-reverb-output.sh` (~250 lines)
- `scripts/generate-report.sh` (~180 lines)
- `SKILL.md` (~800 lines)

**Example Report Output:**
```
╔══════════════════════════════════════════════════════════════
║ Reverb Output Analysis Report
║ Project: reverb-logo-images-per-target.wep
║ Target: Target 1
║ Generated: 2025-10-31 00:02:15
╚══════════════════════════════════════════════════════════════

✅ BROWSER TEST
   • Reverb runtime loaded successfully
   • Page load time: 1.2s
   • No JavaScript errors detected
   • All resources loaded (15/15)

✅ CONTEXT SENSITIVE HELP
   • url_maps.xml found and parsed
   • CSH Links: 0 configured
   • Note: No Context Sensitive Help configured for this project

✅ COMPONENT ANALYSIS
   • Toolbar: ✅ Present (logo: none)
   • Header: ❌ Not configured
   • Footer: ✅ Present (end-of-layout)
   • TOC Menu: ✅ Present (expanded)
   • Content Area: ✅ Present

📊 SUMMARY
   Status: PASS
   Total Issues: 0 errors, 0 warnings
   Components Active: 3/5 (toolbar, footer, menu)

Report generated in 2.3 seconds
```

---

## Acceptance Criteria

### Functional Requirements

#### Browser Automation
- [ ] Can launch Chrome headless on Windows (Git Bash environment)
- [ ] Loads Reverb index.html from file:// URL
- [ ] Waits for Reverb JavaScript runtime to initialize (`window.WWReverb`)
- [ ] Handles timeouts gracefully (configurable, default 30s)

#### Console Error Detection
- [ ] Captures JavaScript console errors with full messages
- [ ] Captures console warnings separately from errors
- [ ] Detects failed resource loads (404s, network errors)
- [ ] Reports errors in structured format (JSON or parseable text)
- [ ] Filters out known benign warnings (configurable)

#### CSH Link Analysis
- [ ] Parses url_maps.xml correctly
- [ ] Extracts all entries from `<TopicMap>` element
- [ ] Displays CSH mappings in readable format
- [ ] Shows CSH ID, target URL, and page title
- [ ] Reports empty TopicMap (no CSH configured)

#### Visual Component Analysis
- [ ] Detects toolbar presence and configuration
- [ ] Detects header presence and configuration
- [ ] Detects footer presence and configuration
- [ ] Detects TOC menu presence and state
- [ ] Detects content area and main content
- [ ] Maps findings to FormatSettings in project file
- [ ] Can capture screenshots of components (optional)

### Non-Functional Requirements

#### Performance
- [ ] Analysis completes in under 60 seconds for typical project
- [ ] Uses system Chrome (no browser download)
- [ ] Minimal memory footprint (headless mode)
- [ ] Can analyze multiple targets sequentially

#### Usability
- [ ] Single command interface for full analysis
- [ ] Clear, actionable error messages
- [ ] Progress indicators for long operations
- [ ] Friendly output formatting (not just JSON dumps)
- [ ] Works in Git Bash on Windows

#### Reliability
- [ ] Handles missing Chrome installation gracefully
- [ ] Handles corrupted url_maps.xml
- [ ] Handles Reverb runtime initialization failures
- [ ] Provides fallback detection methods
- [ ] Validates all file paths before use

### Quality Gates

#### Code Quality
- [ ] All bash scripts pass `shellcheck` linting
- [ ] JavaScript code uses ES6+ modern syntax
- [ ] Error handling for all failure modes
- [ ] Logging for debugging (verbose mode)
- [ ] No hardcoded paths (all configurable)

#### Documentation
- [ ] SKILL.md complete with examples
- [ ] Reference docs for url_maps.xml structure
- [ ] Reference docs for Reverb component IDs
- [ ] Browser automation guide with Puppeteer patterns
- [ ] Troubleshooting section for common issues

#### Testing
- [ ] Manual testing with reverb-logo-images-per-target project
- [ ] Test with project missing CSH configuration
- [ ] Test with project having JavaScript errors
- [ ] Test with missing components (no header/footer)
- [ ] Test error handling for missing files

---

## Dependencies & Prerequisites

### Software Dependencies

**Required:**
- Node.js 14+ (for running Puppeteer)
- Git Bash (MINGW64 environment on Windows)
- System Chrome installation (any recent version)

**Node Packages:**
- `puppeteer-core` (~5MB, uses system Chrome)

**Optional:**
- Chrome DevTools for manual debugging
- VS Code for editing scripts

### Project Dependencies

**Depends On:**
- `epublisher-core` skill (for project file parsing)
- AutoMap wrapper scripts (for build integration)
- File resolver understanding (from existing skills)

**Enables:**
- Future skin customization workflows
- Automated CI/CD testing
- Pre-deployment validation

### Installation Prerequisites

**System Requirements:**
- Windows 10/11 with Git Bash
- Chrome browser installed (standard path)
- Write permissions in project directory (for node_modules)

**First-Time Setup:**
```bash
# Run once per skill installation
cd plugins/epublisher-automation/skills/epublisher-reverb-analyzer
./scripts/setup-dependencies.sh
```

---

## Risk Analysis & Mitigation

### High Priority Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| Chrome not found on system | High | Medium | Auto-detect common paths, provide manual override |
| Node.js not installed | High | Low | Check in setup script, provide clear install instructions |
| Reverb runtime doesn't load | Medium | Low | Timeout with helpful error, suggest manual browser test |
| Puppeteer API changes | Medium | Low | Pin to specific version, document upgrade path |

### Medium Priority Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| File:// URLs blocked by security | Medium | Low | Document workaround, offer local server option |
| Large projects timeout | Medium | Medium | Configurable timeout, chunked analysis option |
| Permission issues in Git Bash | Low | Medium | Document required permissions, provide fixes |
| url_maps.xml format changes | Low | Low | Validate XML schema, fail gracefully |

### Mitigation Examples

**Chrome Detection Failure:**
```bash
# Multiple fallback paths
CHROME_PATHS=(
  "/c/Program Files/Google/Chrome/Application/chrome.exe"
  "/c/Program Files (x86)/Google/Chrome/Application/chrome.exe"
  "$LOCALAPPDATA/Google/Chrome/Application/chrome.exe"
)

# Environment variable override
if [ -n "$CHROME_PATH" ]; then
  echo "$CHROME_PATH"
  exit 0
fi
```

**Node.js Missing:**
```bash
if ! command -v node &> /dev/null; then
  echo "ERROR: Node.js not found."
  echo "Install from: https://nodejs.org/"
  echo "Minimum version: 14.0.0"
  exit 1
fi
```

**Timeout Handling:**
```javascript
try {
  await page.goto(url, {
    waitUntil: 'networkidle2',
    timeout: parseInt(process.env.TIMEOUT || '30000')
  });
} catch (error) {
  if (error.name === 'TimeoutError') {
    console.error('Timeout waiting for Reverb to load.');
    console.error('Try: export TIMEOUT=60000  # Increase to 60 seconds');
  }
  throw error;
}
```

---

## Resource Requirements

### Development Resources

**Time Allocation:**
- Phase 1-2: 20-28 hours (foundation + automation)
- Phase 3-4: 18-26 hours (analysis + integration)
- **Total Development:** 38-54 hours (5-7 working days)

**Testing & Documentation:**
- Manual testing: 8-12 hours
- Documentation review: 4-6 hours
- **Total Testing:** 12-18 hours

**Grand Total:** 50-72 hours

### Infrastructure

**Development:**
- Windows 10/11 machine with Git Bash
- Chrome browser
- Node.js development environment
- ~50MB disk space (skill files + node_modules)

**CI/CD (Future):**
- Jenkins/GitHub Actions with Windows runner
- Chrome installation on build agent
- Node.js on build agent

---

## Future Considerations

### Phase 5: Design Customization Support (Future)

Once analysis is working, extend to support design workflows using SASS variable files and real-time preview.

**Color Scheme Testing:**
- Read current values from `_colors.scss`
- Apply CSS customizations via browser injection
- Reload with new color variables
- Capture before/after screenshots
- Compare visual differences
- Generate custom `_colors.scss` file

**Layout Experimentation:**
- Modify `_sizes.scss` variables (spacing, toolbar height, sidebar width)
- Toggle component visibility via FormatSettings
- Adjust component positions using `header-location`, `footer-location`
- Preview changes in real-time with live reload
- Export working customizations to project Targets/ directory

**Typography Customization:**
- Read font variables from `_fonts.scss`
- Preview different font families and sizes
- Test readability with various combinations
- Generate custom `_fonts.scss`

**Skin Design:**
- Load custom skin files (complete SASS variable set)
- Validate skin structure (all required variables present)
- Test responsiveness at different viewport sizes
- Preview skin with actual content
- Generate complete skin package for deployment

**Reference Documents to Create:**
- `references/SASS_CUSTOMIZATION_GUIDE.md` (~600 lines)
  - Detailed breakdown of each SASS variable file
  - Variable dependencies and relationships
  - Common customization patterns
  - Code injection techniques

- `references/COLOR_SCHEME_EXAMPLES.md` (~300 lines)
  - Pre-built color schemes (dark, light, high-contrast)
  - Corporate/brand color templates
  - Accessibility-compliant schemes

- `references/LAYOUT_PATTERNS.md` (~250 lines)
  - Common layout configurations
  - Component positioning strategies
  - Responsive design breakpoints

### Integration Opportunities

**CI/CD Pipeline:**
```yaml
# .github/workflows/reverb-test.yml
- name: Build Reverb Output
  run: ./scripts/automap-wrapper.sh -c -n project.wep

- name: Analyze Output
  run: ./scripts/analyze-reverb-output.sh project.wep

- name: Check for Errors
  run: |
    if grep -q "ERROR" analysis-report.txt; then
      echo "Reverb output has errors"
      exit 1
    fi
```

**Pre-Deployment Validation:**
- Run analysis before deployment
- Block deployment if errors found
- Generate QA report for stakeholders

**Regression Testing:**
- Compare before/after customizations
- Detect unintended changes
- Track component configuration history

---

## Documentation Plan

### User Documentation

**SKILL.md Sections:**
1. Overview and purpose
2. Installation and setup
3. Basic usage examples
4. Advanced configuration
5. Troubleshooting guide
6. Integration with other skills

**Quick Start Guide:**
```bash
# Analyze Reverb output for a project
cd /path/to/project
analyze-reverb-output project.wep

# Analyze specific target
analyze-reverb-output -t "Target 1" project.wep

# Verbose output for debugging
analyze-reverb-output --verbose project.wep

# Generate screenshot
analyze-reverb-output --screenshot project.wep
```

### Technical Documentation

**Reference Docs to Create:**
1. `REVERB_STRUCTURE.md` - File organization and paths
2. `URL_MAPS_FORMAT.md` - CSH XML schema
3. `BROWSER_AUTOMATION_GUIDE.md` - Puppeteer patterns
4. `CHROME_DETECTION.md` - Finding Chrome on Windows
5. `COMPONENT_IDS.md` - Reverb DOM element reference

**Code Documentation:**
- JSDoc comments for all JavaScript functions
- Bash function documentation headers
- Inline comments for complex logic
- Examples in function documentation

---

## References

### Internal References

**Existing Skills:**
- `epublisher-core/SKILL.md` - Project file parsing patterns
- `epublisher-core/scripts/parse-targets.sh` - Target extraction logic
- `epublisher-reverb-css/SKILL.md` - Reverb customization patterns
- `epublisher-reverb-toolbar/SKILL.md` - Toolbar configuration reference

**Project Files:**
- `reverb-logo-images-per-target/reverb-logo-images-per-target.wep:2-9` - Target configuration
- `reverb-logo-images-per-target/reverb-logo-images-per-target.wep:40-48` - FormatSettings example
- `Output.fixed/Target 1/url_maps.xml:3-8` - CSH structure

### External References

**Puppeteer:**
- Official Docs: https://pptr.dev/
- API Reference: https://pptr.dev/api
- Troubleshooting: https://pptr.dev/troubleshooting
- Chrome DevTools Protocol: https://chromedevtools.github.io/devtools-protocol/

**Node.js:**
- Installation: https://nodejs.org/
- ES6+ Features: https://developer.mozilla.org/en-US/docs/Web/JavaScript
- Async/Await: https://javascript.info/async-await

### Quick Reference Summary

For detailed information, see the **ePublisher Reference Library** section earlier in this document.

**Key FormatSettings:**
- `connect-entry` - Entry point HTML file (default: `index.html`)
- `connect-url-maps-name` - CSH mapping file (default: `url_maps.xml`)
- `toolbar-generate`, `header-generate`, `footer-generate`, `toc-generate` - Component toggles
- Component locations: `header-location`, `footer-location`
- Component logos: `toolbar-logo`, `header-logo`, `footer-logo`

**SASS Variable Files for Phase 5:**
- `_colors.scss` - Color scheme (brand, background, text colors)
- `_fonts.scss` - Typography (families, sizes, weights)
- `_sizes.scss` - Spacing and dimensions
- `_borders.scss` - Border styles
- `_icons.scss` - Icon definitions

See comprehensive tables and code examples in the ePublisher Reference Library section above.

---

## Success Metrics

### Primary Metrics

✅ **Automation Success** - Can analyze Reverb output without manual browser testing
✅ **Error Detection** - Catches JavaScript errors before deployment
✅ **Time Savings** - Reduces manual testing from 10 minutes to < 1 minute
✅ **CSH Validation** - Confirms Context Sensitive Help integration automatically

### Secondary Metrics

✅ **Developer Experience** - Single command produces comprehensive report
✅ **Reliability** - 95%+ success rate across different projects
✅ **Coverage** - Tests all major Reverb components (toolbar, header, footer, menu, content)

---

## Next Steps

1. **Review & Approve Plan** - Stakeholder review of approach and timeline
2. **Begin Phase 1** - Create detection scripts and foundational infrastructure
3. **Setup Development Environment** - Install Node.js, verify Chrome availability
4. **Create Skill Directory Structure** - Initialize file organization
5. **Track Progress** - Use this document to track completion of each phase

---

**Document Version:** 1.0
**Last Updated:** 2025-10-31
**Status:** Planning Complete, Ready for Implementation
