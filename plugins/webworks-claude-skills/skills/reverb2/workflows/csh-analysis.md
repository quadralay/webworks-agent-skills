# Workflow: CSH Link Analysis

*From SKILL.md intake item 2.*

<required_reading>
**No additional references needed** - all information is in this file and the SKILL.md csh_analysis section.
</required_reading>

<process>
## Step 1: Locate url_maps.xml

Find the CSH mapping file in the Reverb output:

```bash
# If project file available
bash scripts/detect-entry-point.sh <project.wep>
# Then look for url_maps.xml in the output directory
```

Standard location: `<output>/url_maps.xml`

If not found, ask user for the path to the Reverb output directory.

## Step 2: Parse Topic Mappings

Extract CSH topic information:

```bash
python scripts/parse-url-maps.py <url-maps-file> [format]
```

Format options:
- `json` (default) - Structured output for programmatic use
- `table` - Human-readable table format

## Step 3: Analyze Link Structure

For each topic, verify:

| Attribute | Description | Example |
|-----------|-------------|---------|
| `@topic` | CSH identifier used in help calls | `whats_new` |
| `@href` | JavaScript-based pretty URL | `index.html#context/whats_new` |
| `@path` | Static HTML path for direct linking | `Getting Started\whats_new.html` |
| `@title` | Display name | `What's New` |

## Step 4: Validate Links (Optional)

If requested, verify that referenced HTML files exist:

```bash
# For each topic in url_maps.xml
# Check if @path file exists in output directory
```

Report:
- Total topics found
- Valid links (file exists)
- Broken links (file missing)
- Duplicate topic IDs (if any)

## Step 5: Report Findings

Present CSH analysis to user:

**Summary:**
```
CSH Analysis for: {project-name}
- Total Topics: {count}
- Valid Links: {count}
- Broken Links: {count}
```

**Topic List (if requested):**
```
| Topic ID | Title | Path |
|----------|-------|------|
| {topic}  | {title} | {path} |
```

**Common Issues:**
- Missing url_maps.xml - CSH not enabled in FormatSettings
- Broken links - Topics may have been excluded from build
- Duplicate IDs - Multiple topics assigned same CSH identifier
</process>

<success_criteria>
This workflow is complete when:
- [ ] url_maps.xml located in output
- [ ] Topic mappings parsed successfully
- [ ] Topic count reported
- [ ] Link structure explained
- [ ] Any issues (broken links, duplicates) reported
</success_criteria>
