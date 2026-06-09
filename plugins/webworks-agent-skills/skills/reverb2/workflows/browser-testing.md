# Workflow: Browser Testing

*From SKILL.md intake item 1.*

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
node scripts/browser-test.js "<chrome-path>" "<entry-url>" [format-settings-json] [--vanilla]
```

Arguments:
- `chrome-path` - From detect-chrome.sh output
- `entry-url` - From detect-entry-point.sh or user-provided
- `format-settings-json` - Optional, for validating feature toggles
- `--vanilla` - Optional **no-bypass mode** (or `VANILLA=1`). The default launch uses `--disable-web-security --allow-file-access-from-files`, which can **mask `file://`-only breakage**. Run once in default mode and, when validating a build users open from disk, again with `--vanilla` to reproduce a real double-click. A pass in default mode but a fail in `--vanilla` means the output is broken on bare `file://`.

## Step 4: Analyze Results

The **pass/fail decision is the `preload` signal** — `success` is true only when `preload` was removed from `body#connect_body` (the first content page rendered). Everything else is a secondary diagnostic.

| Check | Pass Condition | Role |
|-------|---------------|------|
| **Reverb fully loaded** | **`preloadCleared === true`** (== `success`, == `reverbLoaded`) | **Primary** |
| Parcels accounting | `parcelsLoadedAll === true` | Diagnostic only — **unreliable**, can be true on a stuck build |
| No console errors | `errors.length === 0` | Diagnostic only — `connect.js` catches exceptions |
| Toolbar | `components.toolbar.present === true` | Diagnostic |
| TOC | `components.toc.present === true` | Diagnostic |
| Content | `components.content.present === true` | Diagnostic |

> **Do not report a pass on `parcelsLoadedAll` or "no errors" alone.** A broken build can show `parcelsLoadedAll: true` with an empty `errors` array while stuck on the spinner. Only `preloadCleared: true` confirms a real load.

## Step 5: Report Findings

Present results to user:

**If `preloadCleared` is true:**
```
Reverb output fully loaded (preload cleared on body#connect_body).
- Mode: {vanillaMode ? "vanilla (no-bypass file://)" : "default (bypass)"}
- Load time: {loadTime}ms
- TOC items: {toc.itemCount}
- All components present
```

**If `preloadCleared` is false:**
```
Reverb output did NOT fully load — preload still present on body#connect_body (stuck spinner).
- Diagnostics: parcelsLoadedAll={parcelsLoadedAll}, firstPageLoaded={diagnostics.firstPageLoaded}
- {include any console errors as supporting detail}
- {suggest remediation}
```

Common issues and remediation:
- `preloadCleared: false` with `parcelsLoadedAll: true` - runtime reports complete but the first page never rendered; inspect `connect.js`, the parcel manifest, and the screenshot
- Passes in default mode, fails with `--vanilla` - `file://`-only breakage (cross-origin iframe access); the build needs a web server or a fix
- `bodyId` warning - entry URL is not the Reverb shell `index.html`
- Missing toolbar - Check FormatSettings.xml toolbar options
- Missing TOC - Build may have failed or no topics published
</process>

<success_criteria>
This workflow is complete when:
- [ ] Chrome installation detected (or user informed it's missing)
- [ ] Node dependencies verified
- [ ] Entry point located
- [ ] Browser test executed
- [ ] Results analyzed and reported to user
- [ ] Reverb load confirmed via the **primary** signal: `preloadCleared === true` (`preload` removed from `body#connect_body`)
- [ ] Secondary diagnostics noted (`parcelsLoadedAll`, console errors, component presence) — not used as the pass condition
- [ ] If validating a `file://`/disk build, `--vanilla` run performed to rule out no-bypass breakage
</success_criteria>
