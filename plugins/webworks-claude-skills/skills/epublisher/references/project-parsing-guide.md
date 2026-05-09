# Project File Parsing Guide

Comprehensive guide to parsing ePublisher project files (`.wep`, `.wrp`, `.wxsp`) for targets, formats, and source documents.

## Table of Contents

- [Project File Structure](#project-file-structure)
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
         RuntimeVersion="2024.1"
         FormatVersion="{Current}"
         xmlns="urn:WebWorks-Publish-Project">
  <Formats>
    <!-- Target and format configurations -->
  </Formats>
  <Groups>
    <!-- Source document references -->
  </Groups>
  <FormatConfigurations>
    <!-- FormatSettings for each target -->
  </FormatConfigurations>
  <GlobalConfiguration>
    <!-- Project-wide settings -->
  </GlobalConfiguration>
</Project>
```

For per-style trait configuration inside `<GlobalConfiguration>` or `<FormatConfiguration>`, including the `{WWDefaultRule}` prototype literal and the global-vs-per-target scope distinction, see [`format-traits-guide.md`](./format-traits-guide.md).

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
- Can be absolute or relative to project file

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
- Can be relative (to project file) or absolute
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

**Relative (preferred):**
```xml
<Document Path="Source\getting-started.md" ... />
```
- Relative to project file directory
- Portable across machines
- Recommended for version control

**Absolute (less common):**
```xml
<Document Path="C:\projects\my-proj\Source\content.md" ... />
```
- Full path from drive root
- Not portable
- Use only for external references

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

**Version**: 1.0.0
**Last Updated**: 2025-11-04
**Target**: ePublisher 2024.1+ project files
