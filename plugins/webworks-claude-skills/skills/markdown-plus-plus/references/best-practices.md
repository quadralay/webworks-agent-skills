# Markdown++ Best Practices

Guidelines for effective use of Markdown++ extensions in documentation projects.

## When to Use Each Extension

### Variables

**Use variables for:**
- Product names that might change
- Version numbers updated per release
- URLs that may be environment-specific
- Repeated content across multiple documents
- Values defined in ePublisher project settings

**Avoid variables for:**
- One-time text that won't repeat
- Content that varies significantly between uses
- Complex formatted content (use includes instead)

**Example - Good:**
```markdown
Welcome to $product_name; version $version;.
Download from $download_url;.
```

**Example - Avoid:**
```markdown
$intro_paragraph;  <!-- Too much content in a variable -->
```

### Custom Styles

**Use styles for:**
- Consistent formatting across documents
- Semantic meaning beyond basic Markdown
- Output format-specific rendering
- Tables, code blocks, callouts that need custom treatment

**Avoid styles for:**
- Every heading and paragraph (overuse)
- Content where standard Markdown formatting suffices
- Styles that aren't defined in your Stationery

**Block vs. Inline:**
- Use **block styles** for headings, paragraphs, lists, code blocks, tables
- Use **inline styles** for emphasized text within paragraphs
- Block commands must be attached (no blank line between command and element)
- Inline commands have no space before the styled element

**Example - Good:**
```markdown
<!--style:WarningBox-->
> **Warning:** This action cannot be undone.

This is <!--style:UIElement-->**Settings** button.
```

**Example - Wrong (blank line breaks association):**
```markdown
<!--style:CustomParagraph-->

This paragraph will NOT receive the style.
```

**Nested list styling (proper indentation):**
```markdown
<!-- style:BulletList1 -->
- Bullet 1

  <!-- style:BulletList2 -->
  - Bullet 2
```

**Example - Avoid:**
```markdown
<!--style:NormalParagraph-->
This is just regular text that doesn't need a style.
```

### Custom Aliases

**Use aliases for:**
- **All important headings** to ensure stable URL endpoints
- Stable links that survive document restructuring
- Cross-document linking
- Links to non-heading elements
- Section anchors with custom names

**Avoid aliases for:**
- Temporary content
- Internal drafts

**Keep alias values unique within each file.** The validation script checks for duplicates.

**Example - Good:**
```markdown
<!--#api-authentication-->
## Authenticating with the API

Later: See [Authentication](#api-authentication) for details.
```

**Generate aliases automatically:**
```bash
python scripts/add-aliases.py document.md --levels 1,2,3
```

### Conditions

**Use conditions for:**
- Platform-specific content (Windows/Mac/Linux)
- Output format differences (web/print/PDF)
- Audience-specific content (beginner/advanced)
- Development vs. production content
- Internal vs. external documentation

**Avoid conditions for:**
- Minor text differences (use variables instead)
- Content that should always appear
- Deeply nested conditions (hard to maintain)

**Example - Good:**
```markdown
<!--condition:windows-->
Download the `.exe` installer.
<!--/condition-->

<!--condition:mac-->
Download the `.dmg` disk image.
<!--/condition-->
```

**Example - Avoid:**
```markdown
<!--condition:windows-->
Click <!--condition:windows10-->Start<!--/condition--><!--condition:windows11-->the Windows icon<!--/condition-->...
<!--/condition-->
```

### File Includes

**Use includes for:**
- Topic map structure (top-level file includes chapters)
- Reusable content blocks
- Modular documentation structure
- Common examples or code snippets
- Boilerplate legal text

**Avoid includes for:**
- Very small content (inline it instead)
- Content that varies significantly per use
- Creating deeply nested include chains

**Example - Topic map pattern:**
```markdown
<!--include:introduction.md-->
<!--include:getting_started.md-->
<!--include:configuration.md-->
```

### Markers

**Use markers for:**
- Search keywords for Reverb output
- Document metadata (author, category)
- Content that needs special processing
- Passthrough text for output formats

**Avoid markers for:**
- Information already in document content
- Excessive keyword stuffing
- Markers that aren't processed by your output format

**Preferred format (single key-value):**
```markdown
<!--marker:Keywords="installation, setup"-->
```

**JSON format (multiple markers):**
```markdown
<!--markers:{"Keywords": "installation, setup, getting started", "Category": "User Guide"}-->
```

### Multiline Tables

**Use multiline tables for:**
- Complex data requiring lists or blockquotes in cells
- Feature comparisons with detailed descriptions
- Reference tables with examples
- Content that doesn't fit in single-line cells

**Avoid multiline tables for:**
- Simple tabular data
- Tables where standard Markdown works

**Multiline table structure:**
```markdown
<!-- multiline -->
| Name | Details                  |
|------|--------------------------|
| Bob  | Lives in Dallas.         |
|      | - Enjoys cycling         |
|      | - Loves cooking          |
|      |                          |
| Mary | Lives in El Paso.        |
|      | - Works as a teacher     |
```

- Continuation rows use empty first cell (`|      |`)
- Empty row with borders separates table rows

### Combined Commands

**Order priority:** style, multiline, marker(s), #alias

```markdown
<!-- style:ImportantHeading ; marker:Priority="high" ; #critical-section -->
## Critical Section

<!-- style:DataTable ; multiline ; #comparison-table -->
| Column | Data |
|--------|------|
```

**Avoid:** Inconsistent ordering that makes documents harder to read.

### Inline Styling for Images

**Use inline styles for:**
- Logo images requiring specific formatting
- Screenshots with consistent borders/shadows
- Icons that need size control

### Inline Styling for Links

**Use inline styles for:**
- External links that need visual distinction
- Important reference links
- UI element links

**Key rule:** Place style inside the link text brackets, not before the entire link syntax.

### Content Islands (Blockquotes)

**Use content islands for:**
- Learning boxes with multiple content types
- Warning/caution callouts with lists
- Tips with code examples
- Any "block within a block" layout

**Best practice:** Include a heading inside the blockquote for accessibility. Use custom styles when you need different types of content islands (e.g., `BQ_Learn`, `BQ_Warning`).

## Document Structure

### Recommended Organization

See the **Document Structure** section in [SKILL.md](../SKILL.md#document-structure) for the recommended document template showing how to combine markers, aliases, includes, and conditions.

### Condition Placement

**Do:** Keep conditions at natural content boundaries

```markdown
<!--condition:web-->
## Web-Only Section

Content here...
<!--/condition-->
```

**Don't:** Fragment content with many small conditions

```markdown
## Section
<!--condition:web-->Word<!--/condition--><!--condition:print-->Text<!--/condition--> here.
```

### Include Organization

Use the topic map pattern - a top-level file includes chapter-level files:

```
docs/
├── _user-guide.md       # Top-level topic map with includes
├── introduction.md      # Introduction chapter
├── getting_started.md   # Getting started chapter
├── configuration.md     # Configuration chapter
├── advanced_topics.md   # Advanced topics chapter
└── shared/
    └── code-samples.md  # Reusable code examples
```

The top-level file (`_user-guide.md`) contains the document title, markers, and includes for each chapter.

## Variable Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Product names | lowercase with underscores | `$product_name;` |
| Versions | descriptive | `$version;`, `$api_version;` |
| URLs | descriptive with suffix | `$download_url;`, `$support_url;` |
| Dates | descriptive | `$release_date;`, `$last_updated;` |
| Platform-specific | platform prefix | `$windows_path;`, `$mac_path;` |

## Condition Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Output format | format name | `web`, `print`, `pdf`, `chm` |
| Platform | platform name | `windows`, `mac`, `linux` |
| Audience | audience level | `beginner`, `advanced`, `admin` |
| Environment | environment name | `production`, `development`, `staging` |
| Feature flags | feature name | `feature_x`, `beta_feature` |

## Style Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Headings | `Heading` + context | `HeadingChapter`, `HeadingSection` |
| Notes/Callouts | Box type | `NoteBox`, `WarningBox`, `TipBox` |
| Code | `Code` + type | `CodeExample`, `CodeOutput` |
| Tables | `Table` + purpose | `TableData`, `TableComparison` |
| UI Elements | `UI` + element | `UIButton`, `UIMenu` |

## Common Mistakes to Avoid

### 1. Missing Semicolons on Variables

**Wrong:**
```markdown
Welcome to $product_name, version $version.
```

**Right:**
```markdown
Welcome to $product_name;, version $version;.
```

### 2. Blank Line After Block Style

**Wrong:**
```markdown
<!--style:CustomHeading-->

# Heading
```

**Right:**
```markdown
<!--style:CustomHeading-->
# Heading
```

### 3. Space Before Inline Style Target

**Wrong:**
```markdown
This is <!--style:Emphasis--> **bold**.
```

**Right:**
```markdown
This is <!--style:Emphasis-->**bold**.
```

### 4. Forgetting to Close Conditions

**Wrong:**
```markdown
<!--condition:web-->
Web content here...
<!-- Forgot to close! -->
```

**Right:**
```markdown
<!--condition:web-->
Web content here...
<!--/condition-->
```

### 5. Invalid JSON in Markers

**Wrong:**
```markdown
<!--markers:{Keywords: "test"}--> <!-- Missing quotes on key -->
```

**Right:**
```markdown
<!--markers:{"Keywords": "test"}-->
```

### 6. Circular Includes

**Wrong:**
```
main.md includes header.md
header.md includes main.md  <!-- Circular! -->
```

**Right:**
Ensure include chains never loop back.

## Performance Considerations

1. **Limit include depth** - Deep nesting slows processing
2. **Avoid excessive conditions** - Each adds processing overhead
3. **Keep marker JSON simple** - Complex structures slow parsing
4. **Use variables for repeated content** - Reduces document size

## Testing Your Documents

1. Run the validation script before publishing:
   ```bash
   python scripts/validate-mdpp.py document.md
   ```

2. Test with different condition combinations

3. Verify all includes resolve correctly

4. Check variable values are defined in ePublisher

5. Preview in ePublisher before final publish

## Integration with ePublisher

### Variable Sources

Variables can be defined in:
1. ePublisher project Variables window
2. Stationery defaults
3. Target-specific overrides

### Condition Configuration

Conditions are configured in:
1. ePublisher Conditions window
2. Per-target visibility settings
3. Job file condition overrides

### Style Mapping

Custom styles map to:
1. Stationery style definitions
2. Format-specific CSS/XSL
3. Output template configurations

## Advanced Patterns

### Link References

Link references are a standard Markdown feature that allow defining link targets separately from their usage. While supported, they are **generally not recommended** for most documentation because they add indirection that makes content harder to understand and maintain.

**Standard inline links (recommended):**
```markdown
See [Installation](#installation) for setup instructions.
Visit the [API Documentation](https://docs.example.com/api).
```

**Link references (advanced):**
```markdown
See [Installation][install-guide] for setup instructions.
Visit the [API Documentation][api-docs].

[install-guide]: #installation
[api-docs]: https://docs.example.com/api
```

**Why inline links are preferred:**
- Self-contained and easier to understand
- AI-assisted authoring works better with explicit links
- No need to hunt for where references are defined
- Simpler mental model for authors

**When link references may be useful:**
- Redirecting links based on document context (e.g., pointing to the latest API version)
- Conditional link targets for different output formats
- Very long URLs that clutter the text

**Example - version redirection:**
```markdown
See the [API Reference][latest-api] for endpoint details.

[latest-api]: apis/api-v2.0.md#reference
```

When a new API version is released, only the reference definition needs updating.

**Tradeoffs:**
- Adds complexity and indirection
- Makes AI-generated content more difficult
- Requires authors to look in multiple places
- Harder to validate link integrity
