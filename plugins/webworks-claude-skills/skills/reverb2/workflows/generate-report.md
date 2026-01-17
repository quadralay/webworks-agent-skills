# Workflow: Test Report Generation

<required_reading>
**Templates:**
- `../templates/test-results.json` - Canonical structure for browser test output
- `../templates/build-report.json` - Canonical structure for build reports

This workflow orchestrates the other workflows and produces output matching these templates.
</required_reading>

<process>
## Step 1: Gather Project Information

Collect inputs for the report:

```bash
# Required: Project file path
bash ${CLAUDE_PLUGIN_ROOT}/skills/reverb2/scripts/detect-entry-point.sh <project.wep>
```

This provides:
- Project name
- Target/format information
- Output location
- Entry URL

## Step 2: Run Browser Test

Execute browser testing to get runtime results:

```bash
# Detect Chrome
CHROME=$(bash ${CLAUDE_PLUGIN_ROOT}/skills/reverb2/scripts/detect-chrome.sh | jq -r '.path')

# Run test
TEST_RESULTS=$(node ${CLAUDE_PLUGIN_ROOT}/skills/reverb2/scripts/browser-test.js "$CHROME" "<entry-url>")
```

Capture:
- Load success/failure
- Load time
- Console errors/warnings
- Component presence

## Step 3: Parse CSH Links

Extract Context Sensitive Help data:

```bash
CSH_DATA=$(bash ${CLAUDE_PLUGIN_ROOT}/skills/reverb2/scripts/parse-url-maps.sh <output>/url_maps.xml json)
```

Capture:
- Total topic count
- Topic IDs and titles
- Link validation status

## Step 4: Generate Formatted Report

Aggregate all results:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/skills/reverb2/scripts/generate-report.sh <project.wep> \
  "$PROJECT_INFO" \
  "$CSH_DATA" \
  "$TEST_RESULTS"
```

## Step 5: Present Report

Format and display the complete report to user:

```
================================
REVERB OUTPUT TEST REPORT
================================

Project: {project-name}
Target: {target-name}
Generated: {timestamp}

BROWSER TEST
------------
Status: {PASS/FAIL}
Load Time: {ms}
Errors: {count}
Warnings: {count}

COMPONENTS
----------
| Component | Status | Details |
|-----------|--------|---------|
| Toolbar   | {OK/MISSING} | {search present} |
| Header    | {OK/MISSING} | |
| Footer    | {OK/MISSING} | |
| TOC       | {OK/MISSING} | {item count} |
| Content   | {OK/MISSING} | |

CSH LINKS
---------
Topics: {count}
Valid: {count}
Broken: {count}

{list any broken links}

CONSOLE OUTPUT
--------------
{any errors or warnings}

================================
SUMMARY: {PASS/FAIL}
================================
```

## Step 6: Save Report (Optional)

If user requests, save report to file:

```bash
# Text format
bash ${CLAUDE_PLUGIN_ROOT}/skills/reverb2/scripts/generate-report.sh ... > reverb-test-report.txt

# JSON format (follows templates/test-results.json structure)
bash ${CLAUDE_PLUGIN_ROOT}/skills/reverb2/scripts/generate-report.sh ... --json > reverb-test-report.json
```

JSON output conforms to `../templates/test-results.json` for programmatic use.
</process>

<success_criteria>
This workflow is complete when:
- [ ] Project information gathered
- [ ] Browser test executed
- [ ] CSH data parsed
- [ ] Results aggregated
- [ ] Formatted report presented to user
- [ ] Report includes all sections: browser test, components, CSH, console output
- [ ] Overall pass/fail status determined
</success_criteria>
