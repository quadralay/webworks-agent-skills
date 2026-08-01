# Project File Parsing Guide

Comprehensive guide to parsing ePublisher project files (`.wep`, `.wrp`, `.wxsp`) for targets, formats, and source documents.

## Table of Contents

- [Project File Structure](#project-file-structure)
- [Origin and Synchronization](#origin-and-synchronization)
- [Parsing Targets and Formats](#parsing-targets-and-formats)
- [Managing Source Documents](#managing-source-documents)
- [Common Parsing Operations](#common-parsing-operations)
- [Helper Scripts](#helper-scripts)

## Project File Structure

ePublisher project files are XML documents with this high-level structure:

```xml
<?xml version="1.0" encoding="utf-8"?>
<Project Version="1.1.2.0"
         ProjectID="..."
         ChangeID="..."
         RuntimeVersion="2024.1"
         FormatVersion="{Current}"
         xmlns="urn:WebWorks-Publish-Project">
  <Origin>
    <!-- Only in a project linked to a Stationery or to another project -->
  </Origin>
  <Formats>
    <!-- Target and format configurations -->
  </Formats>
  <Groups>
    <!-- Source document references -->
  </Groups>
  <GlobalConfiguration>
    <!-- Project-wide settings -->
  </GlobalConfiguration>
  <FormatConfigurations>
    <!-- FormatSettings for each target -->
  </FormatConfigurations>
</Project>
```

`<Origin>` is serialized first, ahead of `<Formats>` — see [Origin and Synchronization](#origin-and-synchronization).

Saving as Stationery strips `ChangeID`, `<Origin>`, and `<Groups>` (along with the `ProjectID` and the project settings). That strip is what makes a design project usable as a stationery.

For per-style trait configuration inside `<GlobalConfiguration>` or `<FormatConfiguration>`, including the `{WWDefaultRule}` prototype literal and the global-vs-per-target scope distinction, see [`format-traits-guide.md`](./format-traits-guide.md).

## Origin and Synchronization

A project created from a Stationery — or, as of ePublisher 2026.1, from another project — records where it came from in an `<Origin>` element. A design project authored directly in Designer has no `<Origin>`. The distinction between the two project types is **origin, not product**: `.wep` and `.wrp` use the same file format, and as of 2026.1 Designer opens both.

### The `<Origin>` element

```xml
<Origin>
  <Path Checksum="9f2a1c4e7b8d05364af1e2b9c7d84a05"
        LastModified="2026-07-14T18:22:31Z">..\Stationery\Corporate.wxsp</Path>
</Origin>
```

| Part | Meaning |
|------|---------|
| `<Path>` text | Path to the origin file, persisted relative to the project file. Absolute paths are accepted; a root-relative path (`\Stationery\Corporate.wxsp`) resolves against the project's own drive. |
| `Checksum` | MD5 of the origin file as it stood when the project was last created from or synchronized with it |
| `LastModified` | UTC last-write time of the origin at that same moment |

The origin may be a `.wxsp`, a `.wep`, or a `.wrp`. The element shape and the comparison below are identical in all three cases.

### When the synchronization prompt appears

A linked project is treated as out of date when any of these is true:

1. No origin is recorded
2. The recorded origin file no longer exists
3. The origin's last-write time is more than four hours away from the recorded `LastModified`, **or** its MD5 no longer matches `Checksum` (both must agree for the project to count as current)
4. The origin's `stationery.manifest` differs from the copy cached in the project directory

The check runs when a `.wrp` window opens — in Express, and in Designer as of 2026.1 — and before an AutoMap build. `.wep` design-project windows never run it: synchronization is a property of the project, not of the product it is opened in.

Synchronizing copies from the origin: output formats, output targets and their settings, styles, conditions, variables, and cross-reference definitions. It **overwrites** target-setting customizations made locally in the linked project.

**Not synchronized** — these are local to the project and survive every synchronization:

- Merge Settings
- Document Manager contents (groups and source documents)
- Preferences

Manual synchronization is **File > Synchronize with Stationery**. Its browse dialog accepts a `.wep` or `.wrp` as well as a `.wxsp`, so a linked project can be repointed at a different origin.

### Choosing an origin type

| Origin | `.base` snapshots in the linked project | Trade-off |
|--------|------------------------------------------|-----------|
| `.wxsp` Stationery | Yes | Self-contained. Building never needs the origin, and the project tolerates a differing installed format library. Use when the design must be *distributed* — to another site, a customer, or anyone who will not have the design project on hand. |
| `.wep` / `.wrp` project | No | The origin must stay reachable to synchronize, and transforms resolve from the installation (resolver level 4), so origin and linked project need compatible installed format libraries. In exchange the linked project tracks the live design instead of a redistributed snapshot. |

See `file-resolver-guide.md` for the resolver levels themselves.

### Save as Express Project

**File > Save as Express Project...** (Designer, 2026.1) creates a `.wrp` whose `<Origin>` points at the current `.wep`, without publishing Stationery. Designer saves the design project first, so an unsaved edit is not read as a change to synchronize the first time the new project opens. The new project gets its own directory: `<location>\<name>\<name>.wrp`.

The command sits directly below **Save as Stationery** and applies to design projects only — it is disabled (not hidden) in an Express project window, including a `.wrp` hosted in Designer.

This produces a master/satellite topology: one seat owns the master `.wep` and is the only seat that needs Style Designer; every other seat works in a linked satellite `.wrp` with its own source documents and output, picking up design changes through the ordinary synchronization prompt. Satellites can be opened in either product. There is no reverse sync — satellite changes never flow back.

The satellite receives the design: output formats, output targets and their settings, styles, conditions, variables, cross-reference definitions, and the user, output-format, and format-target override files. It does not receive the design project's identity, so it is a project in its own right rather than a copy.

**Include source documents, groups, and Merge Settings** (checkbox, cleared by default):

| State | Result |
|-------|--------|
| Cleared (default) | Hollow shell — the satellite starts with no groups or documents, and the recipient adds their own |
| Selected | Groups, documents, and Merge Settings are carried over |

When it is selected:

- **Group identities are preserved**, so Merge Settings that place those groups keep resolving in the satellite.
- **Documents get fresh identities.** Do not expect `DocumentID` values to match between master and satellite.
- **Document paths are re-relativized** to the satellite's directory — documents are copied holding the master's resolved absolute paths, then persisted relative to the new project location.
- **Deprecated document-level style overrides are never carried**, in either state. Designer reports when it dropped some.

Because the origin is a live project rather than a published artifact, satellites synchronize against whatever state was last *saved*. Keep the master on a shared path and treat saves as releases; **Save as Stationery** remains the formal publish gate.

## Parsing Targets and Formats

### Format Element Structure

```xml
<Format TargetName="WebWorks Reverb 2.0"
        Name="WebWorks Reverb 2.0"
        Type="Application"
        TargetID="RrzaU8EqDdU">
  <OutputDirectory>Output\WebWorks Reverb 2.0</OutputDirectory>
</Format>
```

### Key Attributes

**`TargetName`** (MOST IMPORTANT for builds)
- The target name used in AutoMap `-t` parameter
- Must match exactly when executing builds
- Case-sensitive
- Examples: `"WebWorks Reverb 2.0"`, `"PDF - XSL-FO"`, `"Target 1"`

**`Name`** (IMPORTANT for customizations)
- The format name used for customization paths
- Determines which format files to use from installation
- Examples: `"WebWorks Reverb 2.0"`, `"PDF - XSL-FO"`

**`Type`**
- Format type, typically `"Application"`
- Other values: `"Static"`, `"Dynamic"` (less common)

**`TargetID`**
- Unique identifier for this target within the project
- Used to link FormatConfiguration elements
- Auto-generated, typically alphanumeric string

### OutputDirectory Element

**When present:**
```xml
<Format TargetName="PDF - XSL-FO" ...>
  <OutputDirectory>C:\CustomOutput\PDF</OutputDirectory>
</Format>
```
- Output generated to specified directory
- Can be absolute or relative to project file — prefer relative, including parent-relative `..\`, per [Relative vs Absolute Paths](#relative-vs-absolute-paths)

**When absent:**
```xml
<Format TargetName="WebWorks Reverb 2.0" ...>
</Format>
```
- Output defaults to `Output\[TargetName]\` within project directory
- Example: `Output\WebWorks Reverb 2.0\`

### Extracting Target Information

**List all target names:**
```bash
grep -oP 'TargetName="\K[^"]+' project.wep
```

**List all format names:**
```bash
grep -oP '<Format[^>]*Name="\K[^"]+' project.wep | sort -u
```

**Get full Format elements:**
```bash
grep '<Format ' project.wep
```

**Extract target with output directory:**
```bash
# Find Format element
grep -A 2 'TargetName="WebWorks Reverb 2.0"' project.wep

# Output:
# <Format TargetName="WebWorks Reverb 2.0" ...>
#   <OutputDirectory>Output\WebWorks Reverb 2.0</OutputDirectory>
# </Format>
```

**Get TargetID for specific target:**
```bash
grep 'TargetName="WebWorks Reverb 2.0"' project.wep | \
  sed -n 's/.*TargetID="\([^"]*\)".*/\1/p'
```

### Example Target Configurations

**Basic Reverb Target:**
```xml
<Format TargetName="WebWorks Reverb 2.0"
        Name="WebWorks Reverb 2.0"
        Type="Application"
        TargetID="RrzaU8EqDdU">
</Format>
```
Output location: `Output\WebWorks Reverb 2.0\`

**PDF Target with Custom Output:**
```xml
<Format TargetName="PDF - XSL-FO"
        Name="PDF - XSL-FO"
        Type="Application"
        TargetID="MUI33r6_1kU">
  <OutputDirectory>C:\PDFOutput</OutputDirectory>
</Format>
```
Output location: `C:\PDFOutput\`

**Multiple Reverb Targets:**
```xml
<Format TargetName="Target 1"
        Name="WebWorks Reverb 2.0"
        Type="Application"
        TargetID="RrzaU8EqDdU">
  <OutputDirectory>Output\Target 1</OutputDirectory>
</Format>

<Format TargetName="Target 2"
        Name="WebWorks Reverb 2.0"
        Type="Application"
        TargetID="AbcaU8EqDdU">
  <OutputDirectory>Output\Target 2</OutputDirectory>
</Format>
```
Both use Reverb format but have different output locations.

### Use Cases for Target Parsing

**1. List Available Targets**
Parse project file to show user all configured targets:
```bash
python scripts/parse-targets.py project.wep
```

**2. Validate Target Name**
Before executing AutoMap, confirm target exists:
```bash
target_name="WebWorks Reverb 2.0"
if grep -q "TargetName=\"$target_name\"" project.wep; then
    echo "Target exists"
else
    echo "Target not found"
fi
```

**3. Determine Format for Customization**
Use `Name` attribute to construct customization paths:
```bash
format_name=$(grep 'TargetName="Target 1"' project.wep | \
              sed -n 's/.*Name="\([^"]*\)".*/\1/p')
# Result: "WebWorks Reverb 2.0"
# Customization path: Formats/WebWorks Reverb 2.0/...
```

**4. Find Generated Output**
Check for `<OutputDirectory>` to locate build output:
```bash
output_dir=$(grep -A 2 'TargetName="Target 1"' project.wep | \
             grep '<OutputDirectory>' | \
             sed -n 's/.*<OutputDirectory>\(.*\)<\/OutputDirectory>.*/\1/p')
```

**5. Batch Processing**
Extract all target names for sequential builds:
```bash
for target in $(grep -oP 'TargetName="\K[^"]+' project.wep); do
    echo "Building: $target"
    "[AutoMap-Path]" -c -n -t "$target" project.wep
done
```

## Managing Source Documents

### Source Document Structure

```xml
<Groups>
  <Group Name="Group1" Type="normal" Included="true" GroupID="w3KcSrHh-HI">
    <Document Path="Source\content-seed.md"
              Type="normal"
              Included="true"
              DocumentID="abc123xyz" />
    <Document Path="Source\getting-started.md"
              Type="normal"
              Included="true"
              DocumentID="def456uvw" />
  </Group>
  <Group Name="Reference" Type="normal" Included="true" GroupID="xYz987aBc">
    <Document Path="Source\api-reference.md"
              Type="normal"
              Included="true"
              DocumentID="ghi789rst" />
  </Group>
</Groups>
```

### FrameMaker Book Structure

```xml
<Groups>
  <Group Name="Exploring ePublisher" Type="normal" Included="true" GroupID="dohcaj00OHA">
    <Book Type="book"
          Included="true"
          DocumentID="9CK1vFTe-0A"
          Path="Source Docs\Adobe FrameMaker\Exploring ePublisher.book">
      <Document Type="normal"
                Included="true"
                DocumentID="PNwbOCS_JSw"
                Path="Source Docs\Adobe FrameMaker\Understanding ePublisher.fm" />
    </Book>
  </Group>
</Groups>
```

### Element Attributes

#### Group Element

**`Name`**
- Display name for the group
- Shows in table of contents
- Example: `"Getting Started"`, `"API Reference"`

**`Type`**
- Group type, typically `"normal"`
- Other values rarely used

**`Included`**
- Boolean: `"true"` or `"false"`
- Controls whether group is processed
- `false` = skip entire group and all documents

**`GroupID`**
- Unique identifier (required)
- Auto-generated alphanumeric string
- Example: `"w3KcSrHh-HI"`, `"xYz987aBc"`

#### Document Element

**`Path`** (MOST IMPORTANT)
- Path to source file
- Can be relative (to project file) or absolute — prefer relative, including parent-relative `..\`, per [Relative vs Absolute Paths](#relative-vs-absolute-paths)
- Use backslashes for Windows: `"Source\file.md"`
- Example: `"Source\getting-started.md"`, `"C:\Docs\manual.md"`

**`Type`**
- Document type, typically `"normal"`
- Special values: `"book"` for FrameMaker books

**`Included`**
- Boolean: `"true"` or `"false"`
- Controls whether document is processed
- Allows temporary exclusion without deletion

**`DocumentID`**
- Unique identifier (required)
- Auto-generated alphanumeric string
- Example: `"abc123xyz"`, `"def456uvw"`

#### Book Element

**`Path`** (MOST IMPORTANT)
- Path to FrameMaker book file (`.book`, `.bk`)
- Example: `"Source\manual.book"`

**`Type`**
- Must be `"book"` for FrameMaker books

**`Included`**
- Boolean: `"true"` or `"false"`
- Controls whether book is processed

**`DocumentID`**
- Unique identifier (required)
- Auto-generated alphanumeric string

**Child Documents:**
- FrameMaker books can contain child `<Document>` elements
- Each represents a chapter/file in the book
- Child documents also need `DocumentID` and `Path`

### Document Type Reference

Common document and book types:

| Source Format | Type Value | Extension | Notes |
|---------------|-----------|-----------|-------|
| Markdown | `normal` | `.md` | Plain text markup |
| DITA | `normal` | `.ditamap`, `.dita`, `.xml` | XML-based |
| Microsoft Word | `normal` | `.docx` | Binary format |
| FrameMaker Document | `normal` | `.fm` | Single chapter |
| FrameMaker Book | `book` | `.book`, `.bk` | Multi-chapter |

### Extracting Source Information

**List all source file paths:**
```bash
grep -oP '(Document|Book) Path="\K[^"]+' project.wep
```

**List documents with inclusion status:**
```bash
grep '<Document ' project.wep | \
  grep -oP 'Path="\K[^"]+|Included="\K[^"]+'
```

**Find excluded documents:**
```bash
grep '<Document ' project.wep | grep 'Included="false"' | \
  grep -oP 'Path="\K[^"]+'
```

**Count total documents:**
```bash
grep -c '<Document ' project.wep
```

**List all groups:**
```bash
grep -oP '<Group Name="\K[^"]+' project.wep
```

## Common Parsing Operations

### 1. List All Source Files

**Simple list:**
```bash
grep -oP 'Document Path="\K[^"]+' project.wep
```

**With group context:**
```bash
awk '/<Group Name=/{group=$0} /<Document Path=/{print group; print $0}' project.wep
```

**With inclusion status:**
```bash
grep '<Document ' project.wep | \
  sed -n 's/.*Path="\([^"]*\)".*Included="\([^"]*\)".*/\2: \1/p'
```

### 2. Check If Document Included

**Specific document:**
```bash
# Check if content-seed.md is included
grep 'Path="Source\\content-seed.md"' project.wep | \
  grep -oP 'Included="\K[^"]+'
```

**Result:** `true` or `false`

### 3. Validate Source Paths Exist

**Check all documents:**
```bash
for doc in $(grep -oP 'Document Path="\K[^"]+' project.wep); do
    # Convert Windows path to Unix
    unix_path=$(echo "$doc" | sed 's|\\|/|g')
    if [ -f "$unix_path" ]; then
        echo "✓ $doc"
    else
        echo "✗ $doc (NOT FOUND)"
    fi
done
```

### 4. Add New Document

**Steps:**
1. Generate unique DocumentID (11-char alphanumeric)
2. Insert `<Document>` element inside existing `<Group>`
3. Ensure proper XML structure

**Example:**
```xml
<!-- Before -->
<Group Name="Group1" Type="normal" Included="true" GroupID="w3KcSrHh-HI">
  <Document Path="Source\file1.md" Type="normal" Included="true" DocumentID="abc123xyz" />
</Group>

<!-- After adding new document -->
<Group Name="Group1" Type="normal" Included="true" GroupID="w3KcSrHh-HI">
  <Document Path="Source\file1.md" Type="normal" Included="true" DocumentID="abc123xyz" />
  <Document Path="Source\file2.md" Type="normal" Included="true" DocumentID="newDoc2025" />
</Group>
```

**Using Edit tool:**
```bash
# Find insertion point (after last document in group)
# Generate ID: newDoc2025
# Insert new line with proper indentation
```

### 5. Remove Document

**Using Edit tool:**
```bash
# Find exact <Document> element line
# Use Edit tool to remove the entire line
```

**Warning:** Ensure no orphaned formatting or unclosed tags.

### 6. Toggle Document Inclusion

**Change true → false:**
```bash
# Find line
# Use Edit tool to change Included="true" to Included="false"
```

**Example:**
```xml
<!-- Exclude temporarily -->
<Document Path="Source\old-content.md" Type="normal" Included="false" DocumentID="abc123xyz" />
```

### 7. Add New Group

**Steps:**
1. Generate unique GroupID (11-char alphanumeric)
2. Create `<Group>` element with attributes
3. Add one or more `<Document>` child elements

**Example:**
```xml
<Group Name="New Content" Type="normal" Included="true" GroupID="newGrp2025">
  <Document Path="Source\new-page.md" Type="normal" Included="true" DocumentID="newDoc001" />
</Group>
```

### 8. Add FrameMaker Book

**Steps:**
1. Generate unique DocumentID
2. Add `<Book>` element with `Type="book"`
3. Optionally add child `<Document>` elements for chapters

**Example:**
```xml
<Group Name="User Guide" Type="normal" Included="true" GroupID="ugGrp12345">
  <Book Type="book"
        Included="true"
        DocumentID="bookMain01"
        Path="Source\UserGuide.book">
    <Document Type="normal"
              Included="true"
              DocumentID="ch1Doc0001"
              Path="Source\Chapter1.fm" />
    <Document Type="normal"
              Included="true"
              DocumentID="ch2Doc0002"
              Path="Source\Chapter2.fm" />
  </Book>
</Group>
```

## ID Generation Guidelines

### Format

**GroupID:**
- Alphanumeric string, typically 11 characters
- Mix of letters (case-sensitive) and numbers
- May include hyphens or underscores
- Examples: `w3KcSrHh-HI`, `xYz987aBc`, `newGrp2025`

**DocumentID:**
- Alphanumeric string, 9-12 characters
- Similar format to GroupID
- Examples: `abc123xyz`, `def456uvw`, `PNwbOCS_JSw`

### Generation Strategy

**Simple approach:**
```bash
# Generate random alphanumeric ID
generate_id() {
    local length=${1:-11}
    cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w $length | head -n 1
}

# Usage
new_group_id=$(generate_id 11)
new_doc_id=$(generate_id 10)
```

**With prefix (for clarity):**
```bash
# Generate with meaningful prefix
generate_id_with_prefix() {
    local prefix="$1"
    local random=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 8 | head -n 1)
    echo "${prefix}${random}"
}

# Usage
new_group_id=$(generate_id_with_prefix "grp")  # grpAb3Xy9Zm
new_doc_id=$(generate_id_with_prefix "doc")     # docK4Rt8Wq
```

## Path Handling

### Windows Path Format

**In XML, always use backslashes:**
```xml
<Document Path="Source\content.md" ... />
```

**NOT forward slashes:**
```xml
<!-- INCORRECT -->
<Document Path="Source/content.md" ... />
```

### Relative vs Absolute Paths

**Prefer relative paths in all cases** — including parent-relative (`..\`) traversal for sources that live outside the project folder. Relative paths stay portable across machines and play well with version control.

**Child-relative** (source inside the project tree):
```xml
<Document Path="Source\getting-started.md" ... />
```
- Relative to the project file's directory

**Parent-relative** (source outside the project folder — verified to resolve and build correctly):
```xml
<Document Path="..\Source\Word\Overview.docx" ... />
```
- `..\` walks up to a shared ancestor, then back down to the source
- Still portable, as long as the project and source move together

**Reach for an absolute path only when** a relative one is impossible or impractical:

1. The source is on a **different drive** than the project file (no shared path root exists)
2. The source is on a **different network share**
3. The project file and the source share **only the drive letter or share root** as a common ancestor — a relative path technically works but is long and unmaintainable (e.g. `..\..\..\..\Other\Tree\file.docx`), so absolute is preferable

```xml
<Document Path="C:\projects\my-proj\Source\content.md" ... />
```
- Full path from drive root; not portable across machines

### Path Validation

**Before adding document:**
```bash
source_path="Source/new-file.md"

# Check file exists
if [ -f "$source_path" ]; then
    echo "File exists, safe to add"
else
    echo "File not found: $source_path"
    echo "Create file first or check path"
fi
```

## Helper Scripts

### parse-targets.py

Parse project files to extract target and format information.

**Usage:**
```bash
# List all targets
python scripts/parse-targets.py project.wep

# Detailed info
python scripts/parse-targets.py --list project.wep

# JSON output
python scripts/parse-targets.py --json project.wep

# Base Format Version
python scripts/parse-targets.py --version project.wep
```

**Output examples:**
```
$ python scripts/parse-targets.py project.wep
WebWorks Reverb 2.0
PDF - XSL-FO

$ python scripts/parse-targets.py --version project.wep
Base Format Version: 2024.1
```

### manage-sources.sh

Manage source documents in project files.

**Usage:**
```bash
# List all sources
bash scripts/manage-sources.sh --list project.wep

# Validate paths exist
bash scripts/manage-sources.sh --validate project.wep

# Toggle inclusion
bash scripts/manage-sources.sh --toggle "Source\file.md" project.wep

# Show group hierarchy
bash scripts/manage-sources.sh --groups project.wep
```

**Output examples:**
```
$ bash scripts/manage-sources.sh --list project.wep
Group: Getting Started
  ✓ Source\content-seed.md (included)
  ✓ Source\getting-started.md (included)

Group: Reference
  ✓ Source\api-reference.md (included)
  ✗ Source\old-content.md (excluded)

$ bash scripts/manage-sources.sh --validate project.wep
✓ Source\content-seed.md exists
✓ Source\getting-started.md exists
✗ Source\missing-file.md NOT FOUND
```

## Related Documentation

- [../SKILL.md](../SKILL.md) - Main skill documentation
- [file-resolver-guide.md](./file-resolver-guide.md) - File override hierarchy

---

**Version**: 1.1.0
**Last Updated**: 2026-08-01
**Target**: ePublisher 2024.1+ project files (Origin and Synchronization covers 2026.1 behavior)
