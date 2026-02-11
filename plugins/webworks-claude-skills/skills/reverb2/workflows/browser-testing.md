# Workflow: Browser Testing

<required_reading>
**Templates:**
- `../templates/test-results.json` - Canonical structure for browser test output

All other information is in this file and the SKILL.md capabilities section.
</required_reading>

<process>
## Step 1: Check Dependencies

Ensure Chrome and Node.js dependencies are available:

```bash
# Detect Chrome installation
bash scripts/detect-chrome.sh
```

If Chrome not found, report to user with manual installation instructions.

```bash
# Check/install Node dependencies
bash scripts/setup-dependencies.sh
```

## Step 2: Locate Reverb Entry Point

Find the output location from the project file:

```bash
bash scripts/detect-entry-point.sh <project.wep>
```

This returns JSON with:
- `entryUrl` - Path to index.html
- `formatSettingsPath` - Path to FormatSettings.xml (if exists)

If no project file provided, ask user for the path to the Reverb output's `index.html`.

## Step 3: Run Browser Test

Execute the headless browser test:

```bash
node scripts/browser-test.js "<chrome-path>" "<entry-url>" [format-settings-json]
```

Arguments:
- `chrome-path` - From detect-chrome.sh output
- `entry-url` - From detect-entry-point.sh or user-provided
- `format-settings-json` - Optional, for validating feature toggles

## Step 4: Analyze Results

Parse the JSON output and check:

| Check | Pass Condition |
|-------|---------------|
| Reverb Loaded | `reverbLoaded === true` |
| No Errors | `errors.length === 0` |
| Toolbar | `components.toolbar.present === true` |
| TOC | `components.toc.present === true` |
| Content | `components.content.present === true` |

## Step 5: Report Findings

Present results to user:

**If all checks pass:**
```
Reverb output loaded successfully.
- Load time: {loadTime}ms
- TOC items: {toc.itemCount}
- All components present
```

**If any checks fail:**
```
Issues found in Reverb output:
- {list specific failures}
- {include any console errors}
- {suggest remediation}
```

Common issues and remediation:
- `reverbLoaded: false` - JavaScript error preventing initialization
- Missing toolbar - Check FormatSettings.xml toolbar options
- Missing TOC - Build may have failed or no topics published
- Console errors - Check for missing resources or script errors
</process>

<success_criteria>
This workflow is complete when:
- [ ] Chrome installation detected (or user informed it's missing)
- [ ] Node dependencies verified
- [ ] Entry point located
- [ ] Browser test executed
- [ ] Results analyzed and reported to user
- [ ] Reverb runtime confirmed loaded (`Parcels.loaded_all === true`)
- [ ] No console errors present (or errors reported)
- [ ] All expected components present in DOM (or issues reported)
</success_criteria>
