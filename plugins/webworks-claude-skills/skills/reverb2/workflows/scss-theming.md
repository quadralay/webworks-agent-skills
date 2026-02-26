# Workflow: SCSS Theme Customization

*From SKILL.md intake item 3.*

<required_reading>
**No additional references needed** - all information is in this file and the SKILL.md scss_customization section.
</required_reading>

<process>
## Step 1: Understand the Request

Determine what the user wants to customize:

| Request Type | Action |
|--------------|--------|
| "Show current colors" | Extract and display neo variables |
| "Change brand colors" | Generate color override file |
| "Custom theme" | More detailed SCSS guidance needed |

## Step 2: Identify Customization Level

SCSS overrides follow the file resolver hierarchy:

| Level | Location | Scope |
|-------|----------|-------|
| Target-specific | `[Project]/Targets/[Target]/Pages/sass/_colors.scss` | Single target only |
| Format-level | `[Project]/Formats/WebWorks Reverb 2.0/Pages/sass/_colors.scss` | All targets using format |

Ask user: "Apply to single target or all Reverb 2.0 targets?"

## Step 3: Extract Current Values

Show existing theme configuration:

```bash
python scripts/extract-scss-variables.py <project-dir> neo
```

This displays the 6 "neo" quick-theming variables:

```scss
$neo_main_color: #008bff;           // Primary (toolbar, buttons, links)
$neo_main_text_color: #222222;      // Text on primary backgrounds
$neo_secondary_color: #eeeeee;      // Sidebar background
$neo_secondary_text_color: #fefefe; // Text on dark backgrounds
$neo_tertiary_color: #222222;       // Header/footer background
$neo_page_color: #fefefe;           // Page background
```

For detailed exploration:
```bash
# All categories
python scripts/extract-scss-variables.py <project-dir>

# Specific category
python scripts/extract-scss-variables.py <project-dir> [layout|toolbar|header|footer|menu|sizes]
```

## Step 4: Generate Color Override

Create a `_colors.scss` override file with new brand colors:

```bash
bash scripts/generate-color-override.sh <output-path> \
  --main-color "#E63946" \
  --main-text "#FFFFFF" \
  --secondary-color "#F1FAEE" \
  --secondary-text "#1D3557" \
  --tertiary-color "#457B9D" \
  --page-color "#F1FAEE"
```

Output path examples:
- Target-specific: `[Project]/Targets/MyTarget/Pages/sass/_colors.scss`
- Format-level: `[Project]/Formats/WebWorks Reverb 2.0/Pages/sass/_colors.scss`

Only specify colors that differ from defaults.

## Step 5: Rebuild Output

After generating the override file, rebuild to apply changes:

**Invoke the automap skill** to run a build:
```
Use the automap skill to rebuild the target with the updated SCSS.
```

## Step 6: Verify Changes

After rebuild, run browser test to verify:
- Output loads without SCSS compilation errors
- Colors applied correctly
- No console errors

**Invoke browser-testing workflow** if verification needed.

## Step 7: Report Results

Confirm to user:
```
Theme customization applied:
- Override file: {path}
- Colors changed: {list}
- Status: Ready to rebuild (or already rebuilt)

Next steps:
- Rebuild target using automap skill
- Test output using browser-testing workflow
```
</process>

<success_criteria>
This workflow is complete when:
- [ ] Current SCSS variables extracted and shown
- [ ] Customization level determined (target vs format)
- [ ] Color override file generated at correct location
- [ ] User informed of next steps (rebuild)
- [ ] Build completes without SCSS errors (if rebuild performed)
</success_criteria>
