# ePublisher File Resolver and Override Hierarchy Guide

## Overview

WebWorks ePublisher uses a sophisticated file resolver system that allows customization of format files (templates, stylesheets, transforms) without modifying the installation files. Understanding this hierarchy is critical for successful customizations.

## Project Structure

An ePublisher project follows this standard organization:

```
your-project/
├── your-project.wep          # Project file (.wep=Designer, .wrp=Express, .wxsp=Stationery)
├── Source/                   # Source documents (optional, can reside anywhere)
│   └── docs/
├── Targets/                  # Target-specific overrides
│   └── [TargetName]/
├── Formats/                  # Format-level overrides
│   ├── WebWorks Reverb 2.0/
│   └── WebWorks Reverb 2.0.base/  # .wrp and .wxsp projects only
└── Output/                   # Generated output
    └── [TargetName]/
```

## The Four-Level Override Hierarchy

ePublisher resolves files using a priority-based hierarchy, from highest to lowest priority:

### Level 1: Target-Specific Overrides (Highest Priority)

**Location:** `[Project]\Targets\[TargetName]\[format-structure]\`

**Purpose:** Customizations that apply to a single target only

**Use Cases:**
- Target-specific branding (logos, colors unique to one output)
- Custom deployment configurations for a single target
- Test customizations before applying format-wide

**Example:**
```
C:\projects\my-proj\Targets\WebHelp-Internal\Pages\Connect.asp
C:\projects\my-proj\Targets\WebHelp-Internal\Pages\sass\skin.scss
```

**When to Use:**
- Customization applies to only one target
- Testing changes before broader deployment
- Target-specific branding or configuration

### Level 2: Format-Level Overrides (Medium Priority)

**Location:** `[Project]\Formats\[FormatName]\[format-structure]\`

**Purpose:** Customizations that apply to all targets using this format

**Use Cases:**
- Format-wide styling changes (colors, fonts, layout)
- Custom templates shared across all targets of this format
- Common branding elements for all outputs of this type

**Example:**
```
C:\projects\my-proj\Formats\WebWorks Reverb 2.0\Pages\Connect.asp
C:\projects\my-proj\Formats\WebWorks Reverb 2.0\Pages\sass\_colors.scss
```

**When to Use:**
- Customization should apply to all targets using this format
- Shared branding or styling across multiple outputs
- Common functionality needed by all targets

### Level 3: Packaged Installation Defaults (Isolates Project from installation changes when using ePublisher Express)

**Location:** `[Project]\Formats\[FormatName].base\[format-structure]\`

**Purpose:** Default files packaged with project to isolate from installation changes 

**Use Cases:**
- Lock down all installation files to protect from ePublisher installation changes
- Reference for original file structure
- Source for copying files to project

**Example:**
```
C:\projects\my-proj\Formats\WebWorks Reverb 2.0.base\Pages\Connect.asp
C:\projects\my-proj\Formats\WebWorks Reverb 2.0.base\Pages\sass\_colors.scss
```

### Level 4: Installation Defaults (Lowest Priority / Fallback)

**Location:** `C:\Program Files\WebWorks\ePublisher\[version]\Formats\[FormatName]\[format-structure]\`

**Purpose:** System-wide default files provided by installation

**Use Cases:**
- Fallback files when no project overrides exist
- Reference for original file structure
- Source for copying files to project

**Example:**
```
C:\Program Files\WebWorks\ePublisher\2024.1\Formats\WebWorks Reverb 2.0\Pages\Page.asp
C:\Program Files\WebWorks\ePublisher\2024.1\Formats\WebWorks Reverb 2.0\Pages\sass\_sizes.scss
```

**Important Rules:**
- **NEVER modify installation files directly**
- Always copy to project for customizations
- Installation files may be overwritten during upgrades

## Resolution Process

When ePublisher needs a file (e.g., `Pages\Connect.asp`), it searches in this order:

1. Check target-specific location: `Targets\[TargetName]\Pages\Connect.asp`
2. If not found, check format-level: `Formats\[FormatName]\Pages\Connect.asp`
3. If not found, check format-base-level (Express project): `Formats\[FormatName].base\Pages\Connect.asp`
4. If still not found, use installation default: `[Install]\Formats\[FormatName]\Pages\Connect.asp`

**The first file found wins** - ePublisher stops searching once a match is found.

## Parallel Folder Structure Requirement

### Critical Rule

**File and folder names MUST exactly match the installation hierarchy.**

This is not optional - it's a strict requirement for the file resolver to work.

### Example: Connect.asp Customization

**Installation File:**
```
C:\Program Files\WebWorks\ePublisher\2024.1\
  └─ Formats\
      └─ WebWorks Reverb 2.0\
          └─ Pages\
              └─ Connect.asp
```

**Valid Target-Specific Override:**
```
C:\projects\my-proj\
  └─ Targets\
      └─ MyWebHelp\
          └─ Pages\              ← Exact folder name match
              └─ Connect.asp     ← Exact file name match
```

**Valid Format-Level Override:**
```
C:\projects\my-proj\
  └─ Formats\
      └─ WebWorks Reverb 2.0\    ← Exact format name match
          └─ Pages\              ← Exact folder name match
              └─ Connect.asp     ← Exact file name match
```

**INVALID Examples:**

```
# Wrong folder name (Pages vs pages)
C:\projects\my-proj\Formats\WebWorks Reverb 2.0\pages\Connect.asp

# Wrong file name (connect.asp vs Connect.asp)
C:\projects\my-proj\Formats\WebWorks Reverb 2.0\Pages\connect.asp

# Missing intermediate folder (no Pages directory)
C:\projects\my-proj\Formats\WebWorks Reverb 2.0\Connect.asp

# Wrong format name (missing "2.0")
C:\projects\my-proj\Formats\WebWorks Reverb\Pages\Connect.asp
```

### Why This Matters

The file resolver uses exact string matching for paths. Any deviation causes the resolver to skip your customization and fall back to the installation file, making your changes invisible in the output.

### Case Sensitivity

While Windows is case-insensitive for file system operations, **ePublisher's file resolver is case-sensitive** when matching paths. Always preserve exact casing from installation.

## Base Format Version and Customization Sources

### What is Base Format Version?

The Base Format Version determines which version of format files to use when creating customizations. Different ePublisher versions may have incompatible file structures.

### Determining Base Format Version

Extract from the `<Project>` element in `.wep` or `.wrp` or `.wxsp` files:

```xml
<Project RuntimeVersion="2024.1" FormatVersion="{Current}" ...>
```

**Logic:**
```
IF FormatVersion == "{Current}" THEN
    Base Format Version = RuntimeVersion
ELSE
    Base Format Version = FormatVersion
END IF
```

**Examples:**

1. **Current format (most common):**
   ```xml
   <Project RuntimeVersion="2024.1" FormatVersion="{Current}">
   ```
   Base Format Version = `2024.1`

2. **Locked to older format:**
   ```xml
   <Project RuntimeVersion="2024.1" FormatVersion="2020.2">
   ```
   Base Format Version = `2020.2`

### Using Base Format Version

When copying files from installation to project, always use the Base Format Version:

**Correct:**
```bash
# For project with Base Format Version = 2020.2
source="C:\Program Files\WebWorks\ePublisher\2020.2\Formats\WebWorks Reverb 2.0\Pages\Connect.asp"
destination="C:\projects\my-proj\Formats\WebWorks Reverb 2.0\Pages\Connect.asp"
```

**Incorrect:**
```bash
# Using wrong version (2024.1 when project uses 2020.2)
source="C:\Program Files\WebWorks\ePublisher\2024.1\Formats\WebWorks Reverb 2.0\Pages\Connect.asp"
destination="C:\projects\my-proj\Formats\WebWorks Reverb 2.0\Pages\Connect.asp"
```

### Why Version Matters

- File structure may differ between versions
- XSL templates may have different parameters
- SCSS variables and mixins may change
- ASP page structure may evolve

Mixing versions can cause build errors or unexpected output.

## Common Customization Workflows

### Workflow 1: Copy Single File to Format Level

**Scenario:** Customize `Connect.asp` for all targets using WebWorks Reverb 2.0

**Steps:**

1. **Determine Base Format Version:**
   ```bash
   grep -oP '<Project[^>]*RuntimeVersion="\K[^"]+' project.wep
   # Output: 2024.1
   ```

2. **Locate source file in installation:**
   ```
   C:\Program Files\WebWorks\ePublisher\2024.1\Formats\WebWorks Reverb 2.0\Pages\Connect.asp
   ```

3. **Construct destination path (format-level):**
   ```
   C:\projects\my-proj\Formats\WebWorks Reverb 2.0\Pages\Connect.asp
   ```

4. **Create directory structure:**
   ```bash
   mkdir -p "C:\projects\my-proj\Formats\WebWorks Reverb 2.0\Pages"
   ```

5. **Copy file:**
   ```bash
   cp "C:\Program Files\WebWorks\ePublisher\2024.1\Formats\WebWorks Reverb 2.0\Pages\Connect.asp" \
      "C:\projects\my-proj\Formats\WebWorks Reverb 2.0\Pages\Connect.asp"
   ```

6. **Verify structure:**
   - ✓ Format name matches: `WebWorks Reverb 2.0`
   - ✓ Folder name matches: `Pages`
   - ✓ File name matches: `Connect.asp`

### Workflow 2: Copy File to Target-Specific Location

**Scenario:** Customize `_colors.scss` for only the "Internal WebHelp" target

**Steps:**

1. **Determine target name:**
   ```bash
   grep -oP 'TargetName="\K[^"]+' project.wep
   # Find: "Internal WebHelp"
   ```

2. **Determine format name:**
   ```bash
   grep '<Format .*TargetName="Internal WebHelp"' project.wep | grep -oP 'Name="\K[^"]+'
   # Output: WebWorks Reverb 2.0
   ```

3. **Locate source:**
   ```
   C:\Program Files\WebWorks\ePublisher\2024.1\Formats\WebWorks Reverb 2.0\Pages\sass\_colors.scss
   ```

4. **Construct destination (target-specific):**
   ```
   C:\projects\my-proj\Targets\Internal WebHelp\Pages\sass\_colors.scss
   ```

5. **Create structure and copy:**
   ```bash
   mkdir -p "C:\projects\my-proj\Targets\Internal WebHelp\Pages\sass"
   cp "C:\Program Files\WebWorks\ePublisher\2024.1\Formats\WebWorks Reverb 2.0\Pages\sass\_colors.scss" \
      "C:\projects\my-proj\Targets\Internal WebHelp\Pages\sass\_colors.scss"
   ```

### Workflow 3: SCSS Override Pattern (For Structural CSS Changes)

**Scenario:** Modify CSS structure when SASS variables are insufficient

**When to Use This Approach:**

Reverb uses SASS variables to make customization easier. **Always try modifying SASS variables first:**
- **First choice:** Customize `_colors.scss`, `_sizes.scss`, `_borders.scss` (copy to project, modify variables)
- **Second choice:** Use `_custom-skin.scss` / `_custom-webworks.scss` pattern (when variables aren't enough)

**Use the override pattern when:**
- No SASS variable exists for the desired customization
- CSS structure itself needs modification (selectors, layout, positioning)
- Adding entirely new CSS rules not covered by existing variables
- Overriding third-party styles (Font Awesome, etc.)

**Why this pattern:** Easier to upgrade and maintain; clear separation of custom vs. default styles

**Two override files for two entry points:**

| Override file | Entry point | Scope |
|---------------|-------------|-------|
| `_custom-skin.scss` | `skin.scss` | Toolbar, TOC, navigation chrome (`.ww_skin_*` selectors) |
| `_custom-webworks.scss` | `webworks.scss` | Content page inside iframe (fonts, links, tables) |

**Steps (example: skin chrome override):**

1. **Copy `skin.scss` to project** (format or target level)

2. **Create `_custom-skin.scss` in same directory:**
   ```scss
   // Custom skin overrides — toolbar, TOC, navigation chrome
   // Targets .ww_skin_* selectors

   .ww_skin_search_input_container {
     width: unset;
   }

   .ww_skin_search_input {
     width: 300px;
   }
   ```

3. **Add import to end of `skin.scss`:**
   ```scss
   // ... existing skin.scss content ...

   // Custom skin overrides — keep this import last
   @import "custom-skin";
   ```

4. **For content page overrides**, repeat with `webworks.scss` and `_custom-webworks.scss`:
   ```scss
   // In copied webworks.scss — add at end:
   @import "custom-webworks";
   ```

5. **Benefits:**
   - Custom CSS separated from default styles
   - Original entry points mostly unchanged (easier to compare with installation)
   - Clear naming indicates scope (`skin` = chrome, `webworks` = content)
   - Proper CSS specificity (overrides load last)

### Workflow 4: Customizing ASP Templates with Custom Assets

**Scenario:** Restructure an ASP template (`Header.asp`, `Footer.asp`, `Connect.asp`) to add new layout containers and reference custom images or scripts — for example, splitting a single header logo into a left text-mark and a right art-mark.

Four decisions matter, in order: which override level to copy to, what to do with the existing `.ww_skin_*` class hierarchy, where to place the asset files, and where to put any new structural CSS. Skipping any one of them produces a build that succeeds but silently loses theme or breaks asset paths.

**Steps:**

1. **Copy the ASP template to the right override level.**

   Use the override-level decision from Workflows 1 and 2 — format level for changes that apply to every target using this format, target level for one target only. Copy with `copy-customization.py` so parallel structure is validated:

   ```bash
   python scripts/copy-customization.py \
       --source "C:\Program Files\WebWorks\ePublisher\2024.1\Formats\WebWorks Reverb 2.0\Pages\Header.asp" \
       --destination "C:\projects\my-proj\Formats\WebWorks Reverb 2.0\Pages\Header.asp"
   ```

2. **Wrap, do not strip, existing `.ww_skin_*` classes.**

   When adding new structural elements around a themed element, the new elements must **wrap** the existing class hierarchy, not replace it. The intermediate `.ww_skin_*` wrappers carry variable-driven rules from `skin.scss` (`$header_logo_container_padding`, `$header_logo_height`, `$header_logo_width`, and similar). Removing a wrapper to "simplify" the markup silently disables those rules — the build succeeds, the output loses its theme.

   **WRONG — strips the existing `.ww_skin_header_logo_container` wrapper:**

   ```html
   <div class="ww_skin_header_logo_left">
     <img class="ww_skin_header_logo"
          src="images/logo-text.png"
          wwpage:attribute-src="copy-relative-to-output-root" />
   </div>
   ```

   **CORRECT — new structural div wraps the existing class hierarchy:**

   ```html
   <div class="ww_skin_header_logo_left">
     <div class="ww_skin_header_logo_container">
       <img class="ww_skin_header_logo"
            src="images/logo-text.png"
            wwpage:attribute-src="copy-relative-to-output-root" />
     </div>
   </div>
   ```

   The rule generalizes beyond headers: any `.ww_skin_*` wrapper in the template that has matching rules in `skin.scss` must remain in the customized markup, with new structural elements wrapped around it rather than substituted for it.

3. **Place custom assets in the override directory next to the ASP file.**

   Assets referenced from the customized template live under the same `Pages/` override directory the template was copied to, in a subdirectory whose name matches the `src` value:

   ```
   Formats/WebWorks Reverb 2.0/Pages/
   ├── Header.asp                      ← Customized template (src="images/logo-text.png")
   └── images/                         ← Subdirectory matching the src path
       ├── logo-text.png               ← Custom asset
       └── logo-art.png                ← Custom asset
   ```

   The `wwpage:attribute-src` attribute on the `<img>` tells ePublisher to copy the file into the output and rewrite the `src` path automatically. **For the full mechanism — syntax, variant table, `Files/` contrast, file-based vs setting-based resolvers — see `### Copying Custom Assets in ASP Templates` under `## Advanced Topics`** in this file. Workflow 4 does not duplicate that content.

   Variant choice: branding images that should match the rebuild cycle use `copy-relative-to-output-root`; scripts and assets that need cache-busting use `copy-relative-to-output-root-with-generation-hash` (the base install uses the hashed variant for the script and splash-image references in `Connect.asp`, `Page.asp`, and `Splash.asp`).

4. **Add new structural CSS in `_custom-skin.scss`, not the copied `skin.scss`.**

   When the new wrappers added in Step 2 (`.ww_skin_header_logo_left`, `.ww_skin_header_logo_right`, etc.) need rules of their own — different sizing, alignment, margins — those rules belong in `_custom-skin.scss`, the partial dedicated to chrome (`.ww_skin_*`) customizations. Putting them in the copied `skin.scss` makes the file diff against the installation noisy and hard to compare during upgrades; inventing a fresh partial with a different name (e.g., `_custom.scss`) hides the rules from anyone looking in the well-known `_custom-skin.scss` / `_custom-webworks.scss` pair.

   **See `### Workflow 3: SCSS Override Pattern (For Structural CSS Changes)` above** for the partial setup steps (creating `_custom-skin.scss`, adding `@import "custom-skin";` to the copied `skin.scss`). Workflow 4 does not duplicate that content.

   Use the `$theme_` prefix for new variables — greppable across the project and consistent with the reverb2 skill's `$theme_` Naming Convention. Projects may substitute their own greppable prefix if they have one already established.

   ```scss
   // _custom-skin.scss — wrapper rules for split-logo header

   $theme_header_art_logo_height: $header_logo_height;
   $theme_header_art_logo_width:  auto;

   .ww_skin_header_logo_right {
     margin-left: auto;

     .ww_skin_header_logo_container img {
       height: $theme_header_art_logo_height;
       width:  $theme_header_art_logo_width;
     }
   }
   ```

**Common pitfalls:**

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Stripped intermediate `.ww_skin_*` wrapper | Variable-driven padding/sizing from `skin.scss` silently disappears in the output | Wrap new structural elements around the existing class hierarchy — do not replace it (Step 2) |
| Assets dropped into `Files/` | Image copied into every output group folder; relative path from chrome pages is wrong | Place assets under `Pages/<subdir>/` and reference with `wwpage:attribute-src` (Step 3) |
| New wrapper rules added to the copied `skin.scss` | Noisy diff against the installation; rules invisible to anyone searching the standard custom partials | Put new chrome rules in `_custom-skin.scss` (Step 4) |

**End-to-end example — split-logo Header.asp:**

```html
<div class="ww_skin_header" wwpage:condition="header-enabled">
  <div class="ww_skin_header_logo_container_outer">
    <div class="ww_skin_header_logo_left">
      <div class="ww_skin_header_logo_container">
        <img class="ww_skin_header_logo"
             src="images/logo-text.png"
             wwpage:attribute-src="copy-relative-to-output-root" />
      </div>
    </div>
    <div class="ww_skin_header_logo_right">
      <div class="ww_skin_header_logo_container">
        <img class="ww_skin_header_logo"
             src="images/logo-art.png"
             wwpage:attribute-src="copy-relative-to-output-root" />
      </div>
    </div>
  </div>
</div>
```

`logo-text.png` and `logo-art.png` live in `Formats/WebWorks Reverb 2.0/Pages/images/`. The wrapper rules for `.ww_skin_header_logo_left` and `.ww_skin_header_logo_right` live in `Formats/WebWorks Reverb 2.0/Pages/sass/_custom-skin.scss`. Every `.ww_skin_header_logo_container` from the base template is preserved, so variable-driven padding and sizing from `skin.scss` continue to apply.

**Note on naming:** Project-specific examples sometimes use a different SCSS partial (e.g., `_custom.scss`) or a project prefix (e.g., `$rad_*`). The skill convention is `_custom-skin.scss` for chrome selectors and `_custom-webworks.scss` for content-page styles, with the `$theme_` prefix for custom variables. Map any project-specific naming onto these conventions when working from the skill so future customizers find the same partials and prefixes.

## File Types and Locations

### ASP Templates (`.asp`)

**Purpose:** Define HTML (XSL-FO for PDF) page structure and dynamic content

**Common Files:**
- `Connect.asp` - Main page template (Reverb)
- `Page.asp` - Content page template
- `Header.asp` - Page header
- `Footer.asp` - Page footer
- `Search.asp` - Search page
- `Body.asp` - PDF body template (PDF - XSL-FO)
- `Title.asp` - PDF title page (PDF - XSL-FO)

**Location:** `Formats\[FormatName]\Pages\`

**Customization Use Cases:**
- Add company logos
- Modify toolbar layout
- Customize header/footer content
- Add custom JavaScript
- Modify page metadata

### SCSS Stylesheets (`.scss`)

**Purpose:** Control visual styling and layout

**Common Files:**
- `skin.scss` — Reverb chrome entry point (toolbar, TOC, navigation)
- `webworks.scss` — Reverb content page entry point (inside iframe)
- `_custom-skin.scss` — Custom skin CSS overrides (user-created, imported by `skin.scss`)
- `_custom-webworks.scss` — Custom content CSS overrides (user-created, imported by `webworks.scss`)
- `_colors.scss` — Color variables (300+, neo cascade)
- `_sizes.scss` — Size variables (120+, dimensions, spacing)
- `_fonts.scss` — Font variables (69, families, weights)
- `_borders.scss` — Border variables (150+, widths, styles, radii)
- `_icons.scss` — Icon variables (44, Font Awesome codepoints)

**Location:** `Formats\[FormatName]\Pages\sass\`

**Customization Use Cases:**
- Change color schemes
- Modify fonts and typography
- Adjust layout and spacing
- Customize toolbar styling
- Override default styles

**Best Practice:**
1. **First:** Modify SASS variables (`_colors.scss`, `_sizes.scss`, `_borders.scss`, `_fonts.scss`, `_icons.scss`)
2. **Second:** Use `_custom-skin.scss` / `_custom-webworks.scss` when variables aren't sufficient

### XSL Transforms (`.xsl`)

**Purpose:** Process content and generate output

**Common Files:**
- `content.xsl` - Content transformation
- `pages.xsl` - Page generation
- `pagetemplate.xsl` - Page template processing
- Various element-specific transforms

**Locations:**
- `Formats\[FormatName]\Transforms\`
- `Formats\Shared\common\pages\`
- `Formats\Shared\common\locale\`

**Customization Use Cases:**
- Modify content processing
- Add custom attributes
- Change output structure
- Customize element rendering

**Important:** ePublisher uses XSLT 1.0 (Microsoft .NET runtime) - advanced XSLT 2.0+ features are not supported.

### JavaScript Files (`.js`)

**Purpose:** Client-side functionality (Reverb runtime)

**Common Files:**
- Reverb runtime scripts
- Search functionality
- Navigation behavior

**Location:** `Formats\[FormatName]\Pages\scripts\`

**Customization Use Cases:**
- Add custom client-side behavior
- Modify search functionality
- Customize navigation

## Validation and Testing

### Pre-Customization Checklist

Before copying files:

- [ ] Determined Base Format Version
- [ ] Located source file in correct installation version
- [ ] Verified source file exists and is readable
- [ ] Identified target customization level (format vs. target)
- [ ] Constructed destination path with exact structure match
- [ ] Verified all folder and file names match exactly (including case)

### Post-Customization Checklist

After copying files:

- [ ] Verified file exists at destination
- [ ] Compared file size with source (should match)
- [ ] Checked parallel structure is maintained
- [ ] Rebuilt project with AutoMap
- [ ] Verified customization appears in output
- [ ] Checked build log for errors
- [ ] Tested in browser/viewer

### Common Validation Errors

**Error:** Customization doesn't appear in output

**Causes:**
- Wrong folder or file name (case mismatch)
- Missing intermediate directories
- Wrong format name in path
- File copied to wrong override level
- Build cache not cleared

**Solution:**
- Verify exact structure match with installation
- Rebuild with `-c` flag to clear cache
- Check build log for file resolution messages

**Error:** Build fails after customization

**Causes:**
- Syntax error in customized file (ASP, SCSS, XSL)
- Missing dependency or import
- Version incompatibility

**Solution:**
- Validate file syntax
- Compare with installation version
- Check ePublisher build log for specific error

## Advanced Topics

### Multiple Override Levels

Files can exist at multiple override levels simultaneously. ePublisher uses the highest priority match:

**Example:**
```
Installation: C:\Program Files\WebWorks\ePublisher\2024.1\Formats\WebWorks Reverb 2.0\Pages\Connect.asp
Format-level: C:\projects\my-proj\Formats\WebWorks Reverb 2.0\Pages\Connect.asp
Target-level: C:\projects\my-proj\Targets\Internal\Pages\Connect.asp
```

For "Internal" target, ePublisher uses: Target-level (highest priority)
For other targets, ePublisher uses: Format-level

### Shared Formats Directory

Some XSL files are in `Formats\Shared\` and apply across all formats:

```
C:\Program Files\WebWorks\ePublisher\2024.1\Formats\Shared\common\pages\pagetemplate.xsl
```

Override at format level:
```
C:\projects\my-proj\Formats\Shared\common\pages\pagetemplate.xsl
```

### Version Upgrade Considerations

When upgrading ePublisher:

1. Review customized files for compatibility
2. Compare with new installation files
3. Merge new features/fixes into customizations
4. Test all customizations after upgrade
5. Consider updating FormatVersion to {Current}

### Copying Custom Assets in ASP Templates

When customizing an ASP template (`Header.asp`, `Footer.asp`, `Connect.asp`, etc.), assets the template references (custom logos, scripts, stylesheets) can be placed alongside the template and tagged with the `wwpage:attribute-src` attribute. ePublisher then copies the file into the output and rewrites the `src` path automatically — no hardcoded relative paths, no misplaced files in the `Files/` directory.

**How it works:**

- ePublisher copies the referenced file into the output during publish
- ePublisher rewrites the element's `src` attribute to the correct path relative to the output location (so the reference resolves regardless of how deep the page sits in the output group hierarchy)

**Syntax:**

```html
<img src="images/my-logo.png" wwpage:attribute-src="copy-relative-to-output-root" />
<script src="scripts/custom.js" wwpage:attribute-src="copy-relative-to-output-root"></script>
```

**Variants:**

| Value | Behavior |
|-------|----------|
| `copy-relative-to-output-root` | Copies file, rewrites path relative to output root |
| `copy-relative-to-output-root-with-generation-hash` | Same, plus appends a generation hash query parameter for cache-busting on rebuild |

The `-with-generation-hash` variant is used extensively by the base install (`Connect.asp`, `Page.asp`, `Splash.asp`) for scripts and images that need cache invalidation when the project is rebuilt.

**File placement:**

Place assets in subdirectories alongside the overridden ASP template, mirroring the structure ePublisher expects under `Pages/`:

```
Formats/WebWorks Reverb 2.0/Pages/
├── Header.asp              # Template referencing the assets
├── images/
│   ├── logo-text.png       # Custom asset
│   └── logo-art.png        # Custom asset
└── sass/
    └── _custom-skin.scss
```

The `src` value in the template is relative to the ASP file itself (`src="images/logo-text.png"`); ePublisher resolves it from the override location at publish time.

**Comparison with the `Files/` directory:**

| Approach | Use case |
|----------|----------|
| `Files/` directory | Source-document-level assets (icons, CSS referenced from content). Copied into every output group folder. |
| `wwpage:attribute-src` | Template-level assets (logos in headers/footers, custom scripts loaded by `Connect.asp`). Copied once, path-corrected automatically. |

Placing template-level assets in `Files/` works incidentally but copies them into every group folder and yields incorrect relative paths from chrome pages — use `wwpage:attribute-src` for anything an ASP template references.

**Contrast with setting-based `wwpage:attribute-src` values:**

The base `Header.asp` also uses `wwpage:attribute-src="header-logo-src"` and `wwpage:attribute-src="company-logo-src"`. These are **setting-based** resolvers — they read the asset path from target configuration (the `Header Logo` / `Company Logo` settings). The `copy-relative-to-output-root` value is a **file-based** resolver that copies a specific file from the override directory. When customizing an existing template, both forms may appear in the same file; use the file-based variant when you want the asset bundled with the override, and leave the setting-based variants in place when the asset should remain configurable per target.

**Example — split-logo Header.asp:**

```html
<div class="ww_skin_header" wwpage:condition="header-enabled">
  <div class="ww_skin_header_logo_container_outer">
    <div class="ww_skin_header_logo_left">
      <div class="ww_skin_header_logo_container">
        <img class="ww_skin_header_logo" src="images/logo-text.png" wwpage:attribute-src="copy-relative-to-output-root" />
      </div>
    </div>
    <div class="ww_skin_header_logo_right">
      <div class="ww_skin_header_logo_container">
        <img class="ww_skin_header_logo" src="images/logo-art.png" wwpage:attribute-src="copy-relative-to-output-root" />
      </div>
    </div>
  </div>
</div>
```

The `.ww_skin_header_logo_container` wrappers must remain inside each new structural div — see `### Workflow 4: Customizing ASP Templates with Custom Assets` Step 2 for why. Drop `logo-text.png` and `logo-art.png` into `Formats/WebWorks Reverb 2.0/Pages/images/` (or the equivalent target-level override) and ePublisher handles the copy and path rewrite at publish time.

## Tools and Scripts

### resolve-version-root.py

Python script for deterministic installation VersionRoot detection (used for `Formats/`, `Adapters/`, and `Helpers/` lookups):

```bash
python scripts/resolve-version-root.py --project-file "C:\projects\my-proj\project.wep"
```

**Detection precedence:**
1. `AUTOMAP_EXE_PATH`
2. Designer registry (`HKLM\SOFTWARE\WebWorks\ePublisher Designer`)
3. AutoMap registry (`HKLM\SOFTWARE\WebWorks\ePublisher AutoMap`)

**Output includes:**
- `versionRoot`
- `formatsDir`, `adaptersDir`, `helpersDir`
- `hasFormats`, `hasAdapters`, `hasHelpers`

**Options:**
| Option | Description |
|--------|-------------|
| `--version` | Preferred version (e.g., 2024.1) |
| `--project-file` | Project file to extract version from |
| `--path-only` | Print only the path (for shell piping) |
| `-v, --verbose` | Enable verbose diagnostics |

**Exit Codes:**
| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | VersionRoot not found |
| 2 | Invalid arguments |

### copy-customization.py

Python script for validated file copying with parallel structure enforcement:

```bash
python scripts/copy-customization.py \
    --source "C:\Program Files\WebWorks\ePublisher\2024.1\Formats\WebWorks Reverb 2.0\Pages\Connect.asp" \
    --destination "C:\projects\my-proj\Formats\WebWorks Reverb 2.0\Pages\Connect.asp"
```

**Features:**
- Validates parallel structure automatically
- Creates directories as needed
- Checks source file exists
- Verifies successful copy
- Provides clear error messages

**Options:**
| Option | Description |
|--------|-------------|
| `-s, --source` | Source file path in installation (required) |
| `-d, --destination` | Destination file path in project (required) |
| `-f, --force` | Overwrite existing destination file |
| `--dry-run` | Simulate operation without making changes |
| `--validate-only` | Only validate paths without copying |
| `-v, --verbose` | Enable verbose output |

**Exit Codes:**
| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Invalid arguments |
| 2 | Source file not found |
| 3 | Invalid destination path |
| 4 | Copy operation failed |

### Manual Validation

Verify structure manually:

```bash
# Extract relative path from installation file
# Installation: C:\Program Files\WebWorks\ePublisher\2024.1\Formats\WebWorks Reverb 2.0\Pages\Connect.asp
# Relative: WebWorks Reverb 2.0\Pages\Connect.asp

# Verify destination ends with exact relative path
# Destination: C:\projects\my-proj\Formats\WebWorks Reverb 2.0\Pages\Connect.asp
# Suffix: WebWorks Reverb 2.0\Pages\Connect.asp ← Match!
```

## Summary

**Key Takeaways:**

1. **Four-level hierarchy:** Target → Format → Packaged (.base) → Installation (highest to lowest priority)
2. **Parallel structure is mandatory:** File and folder names must match exactly
3. **Never modify installation files:** Always copy to project for customizations
4. **Use Base Format Version:** Match installation version with project version
5. **Prefer `_custom-skin.scss` / `_custom-webworks.scss` pattern:** Easier to maintain and upgrade
6. **Test after every customization:** Rebuild and verify changes appear
7. **Document your changes:** Add comments explaining customizations

**When in doubt:**
- Use `copy-customization.py` script for validated copying
- Compare paths character-by-character with installation
- Rebuild with `-c` flag to clear cache
- Check build log for file resolution details

