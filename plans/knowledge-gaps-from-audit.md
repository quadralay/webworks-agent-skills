# Knowledge Gaps Discovered During Audit

Gaps identified during a Q&A session testing Claude's ability to work effectively as an ePublisher developer. Each item notes where the knowledge should live.

## Cross-Cutting Concern

### 0. Do not rely on built-in/training knowledge for ePublisher or Reverb
- **Applies to**: ALL WCS skills and repo CLAUDE.md
- **Gap**: No explicit warning against using built-in knowledge. ePublisher is a proprietary tool — training data is likely inaccurate or outdated. Reverb is a WebWorks-specific web framework unlike traditional websites, with its own JavaScript, CSS, and HTML conventions.
- **Breadcrumb needed**:
  - All skills must strongly prefer authoritative sources: WCS skill references, published help docs (`static.webworks.com`), `.fti` files, format source files, and adapter source files
  - Never assume general web development patterns apply to Reverb — always consult the format's `Pages/scripts/*.js`, `Pages/*.asp`, and `Pages/sass/*.scss` files
  - Never assume standard XSLT patterns — ePublisher uses `XslCompiledTransform` (XSLT 1.0 only) with custom extension functions
  - When in doubt, read the source code or docs rather than guessing from training data

## WCS Plugin Gaps — epublisher skill

### 1. Format entry point: `format.wwfmt`
- **Gap**: No mention of `format.wwfmt` or its role
- **Breadcrumb needed**: Each output format lives in `Formats/<format name>/` and has a `format.wwfmt` file that defines the format and references `.xsl` transform files. This is the starting point for diagnosing any format issue.

### 2. Publish pipeline architecture: pipelines and stages
- **Gap**: No description of how the publish engine executes
- **Breadcrumb needed**:
  - `format.wwfmt` controls everything — it defines pipelines that execute when their dependent pipelines are fulfilled
  - Each pipeline calls stages in order with input/output parameters
  - Output parameters often create XML files in the Data (temp) directory alongside the WIF
  - Outputs from one stage become inputs to the next; parameters with value `engine:wif` reference the adapter-generated WIF file
  - Execution continues until all pipelines complete
  - `%TEMP%/WebWorks/ePublisher/<project hash>/Data/<target guid>/files.info` tracks all generated files, dependencies, which files show in the UI, and which can be deployed

### 3. Format Trait Info (`.fti`) files define settings, properties, and options
- **Gap**: No mention of `.fti` files or how target settings/style properties are defined
- **Breadcrumb needed**: At runtime, ePublisher loads `format.wwfmt`, traverses the referenced `.xsl` files, and uses their folder paths to locate corresponding `.fti` (Format Trait Info) files. These define all available settings (FormatSettings), properties, and options. Important gotcha: the internal names in `.fti` files and project files (`.wep/.wrp/.wxsp/.waj`) do **not** match the UI display names users see in Designer/Express — the display name mapping is in the product source code, not in the format files.

### 4. Format trait name lookup reference
- **Gap**: Users refer to settings/properties by UI display name, but `.fti` files use internal names. The `.resx` mapping only exists in the product source code, not in installations. No way for WCS to resolve UI name → internal name.
- **Solution (option 3 — curated table + search fallback)**:
  - Create a curated reference file (`references/format-trait-names.md` or `.json`) mapping the most commonly customized traits (styles, fonts, colors, page layout, TOC, search settings) from UI display name → internal `.fti` name
  - Add a search workflow that scans `.fti` files by keyword/pattern for edge cases not in the table. For installed products, `.fti` files are at `C:\Program Files\WebWorks\ePublisher\<version>\Formats\`
  - The table should be generated from `FormatTraitInfoStrings.resx` in the ePublisher repo, making it easy to regenerate when traits change
- **Action**: Generate initial table from `dev/source/windows/dotnet/WebWorks/Publish/Core/Resources/FormatTraitInfoStrings.resx`

### 5. XSLT Extensions
- **Gap**: No mention of ePublisher XSLT extensions — custom extension functions available in `.xsl` transforms beyond standard XSLT
- **Breadcrumb needed**: ePublisher provides custom XSLT extension functions callable from format `.xsl` files. Published documentation is available at `https://static.webworks.com/docs/epublisher/latest/help/Advanced%20Customizations_%20Overrides_%20and%20Extensions/_xslt-extensions.04.1.html`

### 6. XSLT libraries used by ePublisher
- **Gap**: No mention of which XSLT processor/library ePublisher uses
- **Breadcrumb needed**:
  - **Output generation and adapter inputs**: Uses .NET `XslCompiledTransform` (XSLT 1.0 only). All format `.xsl` files must be XSLT 1.0 compatible.
  - **DITA preprocessing**: Uses transforms from the DITA Open Toolkit (DITA-OT), supporting both XSLT 1.0 and 2.0. These are located at `Adapters/xml/scripts/dita/ant/xsl/`. The DITA-OT version is selected via ANT template files in `Adapters/xml/scripts/dita/ant/` (e.g., `webworks-4.1.xml` corresponds to `dita-ot-4.1`).

### 7. Adapter architecture: four core adapters
- **Gap**: No mention of which adapters exist or how they're organized
- **Breadcrumb needed**: There are four core adapters (in `Adapters/`):
  - **XML** (`xml/`) — handles XML and DITA input (DITA is a subset of the XML adapter)
  - **helper** (`helper/`) — handles Markdown++ input (`helper/markdown/`)
  - **Word** — handles Microsoft Word input
  - **FrameMaker** — handles Adobe FrameMaker input
- Each adapter has an `adapter.fti` for configurations (except helper/Markdown++ currently)

### 8. Adapter configurations via `adapter.fti`
- **Gap**: No mention of adapter settings or where they're defined
- **Breadcrumb needed**: Adapter configurations (called `AdapterConfigurations` in project files) are defined in `Adapters/<input format name>/adapter.fti`. These handle edge cases with different input formats (Word, FrameMaker, DITA). The `helper` (Markdown++) adapter has no configurations currently. Adapter trait display names are also covered by the trait lookup table (item 4).

### 9. WIF (WebWorks Intermediate Format)
- **Gap**: No mention of WIF — the central intermediate format that all adapters produce and all output formats consume
- **Breadcrumb needed**:
  - All input adapters convert source documents into WIF (`.wif`), and all output format transforms start from the WIF file
  - No formal schema — WIF is designed to evolve easily
  - The adapter creates a copy of the source file as `<source name>.<md|fm|docx|ditamap>wif`, then generates the final `<source name>.wif`
  - WIF files are generated in a temp directory with GUID-based hierarchy: `%TEMP%/WebWorks/ePublisher/<project name-guid-hash>/<format target guid><group guid>/<document guid>/<source name>.wif`
  - **Practical tip**: Use the Designer/Express UI menu **View > Data Directory** to open the temp folder for the current project — this is the easiest way to locate WIF files for debugging, since the GUID hierarchy is not human-navigable
  - **Algorithm for workspace directory name** (from `WorkspaceManager.cs`):
    1. Concatenate `"{projectPath}:{projectID}"` (projectID is a GUID stored in the `.wep` file)
    2. UTF-8 encode, then SHA1 hash (20 bytes)
    3. XOR-fold to 10 bytes: `xorBytes[i] = hash[i*2] ^ hash[i*2+1]`
    4. Base64 encode, then replace `/`→`_`, `+`→`-`, remove `=`
  - Full data directory path: `%TEMP%/WebWorks/ePublisher/<workspace-hash>/Data/<target-guid>/`
  - This enables programmatic lookup of WIF files and intermediate outputs without the UI.

### 10. `.wez` files are installer artifacts, not format sources
- **Gap**: Skills might direct users to examine `.wez` files when diagnosing format issues
- **Breadcrumb needed**: `.wez` files are zip archives used only for installer packaging. They are not the source of truth for format contents. Always work with the extracted format directory (`Formats/<format name>/`), not the `.wez` file.

### 11. Available output formats and format lifecycle
- **Gap**: No list of current output formats or explanation of format versioning/lifecycle
- **Breadcrumb needed**:
  - **Current formats (2025.1)**: Dynamic HTML, Eclipse Help, Markdown++, Microsoft HTML Help 1.x, Oracle Help, PDF - XSL-FO, PDF, Sun JavaHelp 2.0, WebWorks Help 5.0, WebWorks Reverb, WebWorks Reverb 2.0, eBook - ePUB 2.0 (XML+XSL removed in 2025.1)
  - **Format availability**: Last 2-3 years of formats ship with Designer/AutoMap installers. Older formats available via "Legacy Formats Installer" (uncommon).
  - **Format versioning**: When a format is removed from a version, users must downgrade the format version to see it in the UI. After changing a format version, users must close and reopen their project because `.fti` files are only scanned once at project load.
  - `Shared` is common resources used across formats, not an output format itself.

### 12. Output localization strings: `locales.xml`
- **Gap**: No mention of where generated output localization strings live
- **Breadcrumb needed**: Locale strings for generated output (e.g., "Table of Contents", "Search", "Index") are stored in `Formats/Shared/common/locale/locales.xml`. This is distinct from the .NET application `.resx` files — those are for the UI applications, not generated output. Customers commonly customize or add locale strings here.

### 13. Testing workflow for format/adapter changes
- **Gap**: No testing methodology documented
- **Breadcrumb needed**:
  - Generate output, manually modify to produce desired result, rename `Output` folder to `Output.golden` (the gold standard)
  - Optionally generate and rename to `Output.baseline` (the before state)
  - Modify XSL files and/or adapters/DLLs, regenerate, compare `Output` to `.baseline` or `.golden` to determine success
  - Future opportunity: automated output format development by processing XSL outside ePublisher's engine (e.g., small C# runtimes)

### 14. Debugging transforms
- **Gap**: No debugging guidance for XSLT issues
- **Breadcrumb needed**:
  - **Logging**: Use `wwlog:Message(...)` extension functions in XSL files — output appears in `generate.log` (always written after generation; AutoMap skill currently ignores log output to save context but the file is always available)
  - **Data directory inspection**: Examine intermediate XML files in the Data directory — these are defined in `format.wwfmt` stage parameters
  - **Visual Studio**: Attach debugger to step through transforms — not ideal except for extreme development cases
  - **Future**: Potential for automated XSL processing outside the engine using small C# runtimes

### 15. Technical support process
- **Gap**: No mention of how customers/partners file support cases
- **Breadcrumb needed**: Support cases are filed at https://www.webworks.com/Support/. Users must have an active Contract ID (GUID format: `XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX`) to submit a case. The Contract ID can be found in the product UI via Help > License Keys... > "Register" button.

## WCS Plugin Gaps — reverb2 skill

### 16. Reverb 2.0 runtime architecture: Pages directory
- **Gap**: No description of the runtime file structure within a format
- **Breadcrumb needed**: The runtime output of Reverb 2.0 is built from three source types in `<format name>/Pages/`:
  - `scripts/*.js` — JavaScript behavior (keyboard shortcuts, search, navigation, etc.)
  - `*.asp` — HTML templates (become `.html`/`.htm` in published output)
  - `sass/*.scss` — styles (become `.css` in published output); `_*.scss` files are configurable variable collections
- This is the starting point for diagnosing any runtime issue in Reverb 2.0 output.

### 17. SCSS theming: `Pages/sass/_*.scss` variables
- **Gap**: The scss-theming workflow may reference `.weplugin` files which are deprecated; needs to point to the SCSS source directly
- **Breadcrumb needed**: To customize Reverb 2.0 appearance (e.g., toolbar background color), look in `<format name>/Pages/sass/`. Files named `_*.scss` are collections of configurable variables. This is the preferred approach — `.weplugin` skin packages are deprecated (prepackaged SCSS overrides to the default Neo skin) and will be removed in Reverb 3.0.

## ePublisher Repo (`CLAUDE.md`) Gaps

See separate plan file: `C:\Repo\ePublisher_debug\trunk\plans\knowledge-gaps-from-audit.md`
