---
name: markdown-plus-plus
description: Authoritative reference for Markdown++ syntax including styles, conditions, variables, includes, markers, and aliases. Use when editing, fixing, migrating, auditing, or validating Markdown++ documents.
---

<objective>

# markdown-plus-plus

Read and write Markdown++ documents - an extended Markdown format with variables, conditions, custom styles, file includes, and markers.
</objective>

<overview>

## Overview

Markdown++ extends CommonMark with HTML comment-based extensions. All extensions (except variables) use HTML comments for backward compatibility with standard Markdown renderers.

### Quick Reference

- **Variables**: `$variable_name;` — Inline, reusable content
- **Styles**: `<!--style:Name-->` — Block (above) or Inline (before)
- **Aliases**: `<!--#alias-name-->` — Anchor for `[text](#alias-name)` links
- **Conditions**: `<!--condition:name-->...<!--/condition-->` — Show/hide content by format
- **Includes**: `<!--include:path/to/file.md-->` — Insert file contents
- **Markers**: `<!--markers:{"Key": "val"}-->` — Metadata for search/processing
- **Multiline Tables**: `<!-- multiline -->` — Enable block content in cells

</overview>

<syntax_examples>

## Syntax Examples

### Variables

Variables store reusable values across documents. They use `$name;` syntax (dollar sign, name, semicolon).

```markdown
Welcome to $product_name;, version $version;.
The **$product_name;** application supports...
```

**Rules:**
- Alphanumeric characters, hyphens, underscores only
- Must end with semicolon
- No spaces in variable names
- Case-sensitive: `$Product;` differs from `$product;`

**Valid:** `$product_name;`, `$version-2;`, `$my_var;`
**Invalid:** `$product name;` (space), `$product` (no semicolon)

### Custom Styles

Styles override default formatting for elements. Placement depends on element type.

**Block-level** (place on line directly above element, no blank line):
```markdown
<!--style:CustomHeading-->
# My Heading

<!--style:NoteBlock-->
> This is a styled blockquote.
```

**IMPORTANT:** Block commands must be attached to the element (no blank line between). Comment tags must be associated with a paragraph - they cannot float alone separated by whitespace.

```markdown
<!-- WRONG - blank line breaks the association -->
<!--style:CustomParagraph-->

This paragraph will NOT receive the style.

<!-- CORRECT - command directly above element -->
<!--style:CustomParagraph-->
This paragraph receives the style.
```

**Inline** (place immediately before the element, no space):
```markdown
This is <!--style:Emphasis-->**important text**.
Use <!--style:ProductName-->*$product_name;* for branding.
```

**Nested lists** (use proper indentation for nested styles):
```markdown
<!-- style:BulletList1 -->
- Bullet 1

  <!-- style:BulletList2 -->
  - Bullet 2
```

**CRITICAL:** Indented style comments require matching indentation on the following content line. Mismatched indentation causes the style to render as visible text.

```markdown
<!-- WRONG - style indented but content is not -->
1. Step content...

   <!-- style:NoteIndent -->
**Note:** This will NOT receive the style.

<!-- CORRECT - both at same indentation -->
1. Step content...

   <!-- style:NoteIndent -->
   **Note:** This correctly receives the style.
```

**Tables** (place style comment above table):
```markdown
<!--style:DataTable-->
[table rows follow immediately below]
```

### Custom Aliases

Aliases create stable internal link anchors. Use them for all important headings to ensure stable URL endpoints.

```markdown
<!--#getting-started-->
## Getting Started

<!--#installation-steps-->
### Installation

Later in the document:
See [Getting Started](#getting-started) for an introduction.
Jump to [Installation](#installation-steps) for setup instructions.
```

**Cross-document links:**
```markdown
See [API Reference](api.md#authentication) for auth details.
```

**Rules:**
- Alphanumeric, hyphens, underscores only
- No spaces (alias ends at first space)
- Must start with `#` inside the comment
- **Keep alias values unique within each file**

Use `scripts/add-aliases.py` to auto-generate aliases for headings.

### Conditions

Conditions show or hide content based on output format. Content between opening and closing tags is conditional.

**Basic usage:**
```markdown
<!--condition:web-->
Visit our [website](https://example.com) for updates.
<!--/condition-->

<!--condition:print-->
See Appendix A for additional resources.
<!--/condition-->
```

**Operators:**

- **Space** (AND): `a b` - all must be visible. Example: `<!--condition:web production-->`
- **Comma** (OR): `a,b` - any can be visible. Example: `<!--condition:web,print-->`
- **Exclamation** (NOT): `!a` - visible when condition is hidden. Example: `<!--condition:!internal-->`

**Precedence:** NOT (tightest) > AND (space) > OR (comma)

**Complex examples:**
```markdown
<!--condition:!internal-->
This appears when "internal" condition is hidden.
<!--/condition-->

<!--condition:web,print-->
This appears in web OR print output.
<!--/condition-->

<!--condition:web production-->
This appears only when BOTH web AND production are visible.
<!--/condition-->

<!--condition:!draft,web production-->
Means: (!draft) OR (web AND production)
<!--/condition-->
```

**Inline conditions:**
```markdown
Contact us at <!--condition:web-->[support@example.com](mailto:support@example.com)<!--/condition--><!--condition:print-->the address on the back cover<!--/condition-->.
```

### File Includes

Includes insert content from other Markdown++ files.

```markdown
<!--include:shared/header.md-->

# Main Content

<!--include:../common/footer.md-->
```

**Rules:**
- Paths are relative to the containing file
- Recursive includes are supported
- Circular includes are detected and prevented
- Include must be alone on its line

**With conditions:**
```markdown
<!--condition:web-->
<!--include:web-only-content.md-->
<!--/condition-->
```

### Markers (Metadata)

Markers attach metadata to document elements for search, processing, or custom behavior.

**Preferred format (single key-value):**
```markdown
<!--marker:Keywords="api, documentation"-->
```

**JSON format (multiple keys):**
```markdown
<!--markers:{"Keywords": "api, documentation", "Description": "API reference guide"}-->
```

Use `marker:key="value"` for single markers, JSON format for multiple.

**Common marker keys:**

- **Keywords** — Maps to HTML meta keywords tag
- **Description** — Maps to HTML meta description tag
- **IndexMarker** — Creates index entries for generated output

**Index markers:**

Index markers create entries in generated indexes (back-of-book style).

```markdown
<!--marker:IndexMarker="creating projects"-->
## Creating Projects
```

**Multiple entries** (comma-separated):
```markdown
<!--marker:IndexMarker="projects:creating,output:generating,targets"-->
## Creating Projects
```

**Sub-entries** (colon for nesting):
```markdown
<!--marker:IndexMarker="source documents:opening,documents:opening from Manager"-->
## Opening Source Documents
```

**Format rules:**
- `primary` — Top-level index entry
- `primary:secondary` — Nested entry under primary
- Comma separates multiple entries

### Multiline Tables

Multiline tables allow block content (lists, blockquotes, styled elements) inside cells. Each row continues on subsequent lines using empty first cells, and rows are separated by an empty row.

```markdown
<!-- multiline -->
Name   Details
-----  --------------------------
Bob    Lives in Dallas.
       - Enjoys cycling
       - Loves cooking
       [empty row separates records]
Mary   Lives in El Paso.
       - Works as a teacher
```

Note: In actual syntax, use standard markdown table pipes. Empty first cell continues previous row; empty row separates records.

**Rules:**
- Add `<!-- multiline -->` on line above table
- First content row starts the data
- Continuation rows have empty first cell (continues previous row)
- Empty row with cell borders separates records
- Cells can contain lists, blockquotes, custom styles, and other Markdown++ commands
- Standard alignment syntax applies (`:---`, `---:`, `:---:`)

**With custom style:**
```markdown
<!-- style:DataTable ; multiline -->
Feature  Description
-------  --------------------------
API      REST endpoints.
         - GET /users
         - POST /users
         [empty row]
Auth     OAuth 2.0 support.
```

Note: Use standard markdown table syntax with pipes in actual documents.

### Combined Commands

Multiple commands can appear in a single comment, separated by semicolons.

**Order priority:** style, multiline, marker(s), #alias

```markdown
<!-- style:CustomHeading ; marker:Keywords="intro" ; #introduction -->
# Introduction

<!-- style:DataTable ; multiline ; #feature-table -->
[table with Feature and Description columns follows]

<!-- style:NoteBlock ; marker:Priority="high" ; #important-note -->
> This blockquote has style, marker, and alias combined.
```

Whitespace around semicolons is optional.

### Inline Styling for Images and Links

Apply custom styles to images and links using inline style comments.

**Images:**
```markdown
<!--style:CustomImage-->![Logo](images/logo.png "Company Logo")

<!--style:ScreenshotStyle-->![Settings Screen](images/settings.png)
```

**Links (style inside link text):**
```markdown
[<!--style:CustomLink-->*Link text*](topics/file.md#anchor "Title")

See the [<!--style:ImportantLink-->**API Reference**](api.md#auth).
```

### Content Islands (Blockquotes)

Blockquotes are an effective way to create "content islands" - grouped content blocks useful for callouts, notes, or enhanced layouts. Custom styles make them more configurable for different types of content islands.

**Basic content island (no custom style):**
```markdown
> ## Learning Section
>
> This blockquote contains multiple elements:
>
> - Bullet point 1
> - Bullet point 2
>
> ```python
> def example():
>     return "Code inside blockquote"
> ```
>
> Final paragraph in the content island.
```

**Styled content islands (recommended for multiple island types):**
```markdown
<!--style:BQ_Learn-->
> ## Learning Section
>
> This blockquote groups related learning content together.

<!--style:BQ_Warning-->
> **Warning:** This is a styled warning block.
>
> Take note of the following:
> 1. First consideration
> 2. Second consideration
```

### Nested Lists with Styling

Apply custom styles to list containers:

```markdown
<!--style:ProcedureList-->
1. First step
   - Sub-item A
   - Sub-item B
2. Second step
   1. Nested numbered item
   2. Another nested item
3. Third step
```

### Document Structure

**Topic map pattern** - A top-level file includes chapter-level files:

```markdown
<!--markers:{"Keywords": "user guide, documentation", "Description": "Complete user guide for the application"} ; #user-guide-->
# User Guide

<!--include:introduction.md-->

<!--include:getting_started.md-->

<!--include:configuration.md-->

<!--condition:advanced-->
<!--include:advanced_topics.md-->
<!--/condition-->
```

**Key points:**
- Markers and alias are combined in one comment attached to the title heading
- `Keywords` and `Description` map to HTML meta tags
- Includes pull in chapter-level content files
- Conditions wrap audience-specific sections

</syntax_examples>

<validation>

## Validation

Use the validation script to check Markdown++ syntax:

```bash
python scripts/validate-mdpp.py document.md
```

**Options:**
- `--verbose` - Show detailed output
- `--json` - Output errors as JSON
- `--strict` - Treat warnings as errors

**Common errors detected:**
- Unclosed condition blocks
- Invalid variable names
- Malformed marker JSON
- Circular file includes
- Duplicate alias values within a file

## Alias Generation

Generate unique aliases for headings:

```bash
python scripts/add-aliases.py document.md --levels 1,2,3
```

**Options:**
- `--levels` - Comma-separated heading levels to process (e.g., `1,2,3`)
- `--dry-run` - Preview changes without modifying file
- `--prefix` - Add prefix to generated aliases

See `references/syntax-reference.md` for complete syntax rules.

</validation>

<references>

## Reference Files

- `references/syntax-reference.md` - Detailed syntax rules, edge cases, and validation codes
- `references/examples.md` - Real-world document examples
- `references/best-practices.md` - Usage guidance, naming conventions, and common mistakes

</references>

<related_skills>

## Related Skills

- **epublisher** — Understand project structure containing Markdown++ sources
- **automap** — Build ePublisher projects with Markdown++ source documents
- **reverb** — Test output generated from Markdown++ sources

</related_skills>

<success_criteria>

## Success Criteria

- Markdown++ document uses correct syntax for all extensions
- Variables use valid names (alphanumeric, hyphens, underscores)
- Conditions have matching opening and closing tags
- File includes use valid relative paths
- Markers contain valid JSON (for `markers:` format)
- No circular includes detected
</success_criteria>
