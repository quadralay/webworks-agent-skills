# Version Compatibility

## Supported Versions

| Component | Minimum | Recommended | Notes |
|-----------|---------|-------------|-------|
| ePublisher | 2020.2 | 2026.1 | Primary development target |
| AutoMap | 2020.2 | 2026.1 | Required for automation |
| Designer for `.wrp` projects | 2026.1 | 2026.1 | Before 2026.1, opening a `.wrp` requires ePublisher Express |
| `.wep`-origin (`.base`-less) projects | 2026.1 | 2026.1 | Origin and a compatible installed format library must stay reachable |
| Reverb Format | 2.0 | 2.0 | Only Reverb 2.0 supported |
| Chrome | 90+ | Latest | For browser testing |
| Node.js | 16+ | 18+ | For Puppeteer scripts |
| Platform | Windows | Windows 10/11 | ePublisher is Windows-only |

## Breaking Changes by Version

### ePublisher 2026.1 (new in 2026.1 — features below do NOT exist in earlier versions)
- `useAsStationery="True"` on a job's `<Project>` element (a live `.wep`/`.wrp` as stationery)
- Federated parcel composition (Reverb 2.0): `.wacj` composition jobs, per-target deploy scope (Everything / Groups / Shell; `deployScope` attribute, `--deployscope`), `wwcomposition*` output descriptors
- Amazon S3 + CloudFront deploy destinations (named profile/role credentials, deploy-time invalidation, dry run; global `--dryrun`)
- Inline destination definitions in `.waj`/`.wacj` (`<DeploySettings>`) and the `--deploysettings` overlay file
- A failed deploy is an error (reaches the exit status); earlier versions warned and exited 0
- Designer opens, builds, synchronizes, and deploys Express `.wrp` projects, presenting the Express window experience (Document Manager, synchronization prompt, no Style Designer, no Preview). Its Open dialog offers `.wep` and `.wrp` under one **ePublisher Project Files** entry. Double-clicking a `.wrp` opens Express when installed, Designer otherwise
- Designer **File > New Project from Stationery...** — creates a `.wrp` from a `.wxsp` *or* a `.wep`
- Designer **File > Save as Express Project...** — creates a `.wrp` linked to the current `.wep` via `<Origin>`, for a master/satellite arrangement; the "Include source documents, groups, and Merge Settings" option is off by default
- Opening a standalone `.wxsp` (double-click, command line, File > Open) starts New Project from Stationery with it pre-selected, in both products. Earlier versions raise an unhandled error
- Style Designer supports multi-select (Ctrl/Shift-click) for bulk style edits; values disagreeing across the selection display blank, and `[Prototype]` is excluded from a multiple selection
- PDF - XSL-FO compiles with Apache FOP 2.11 (2022.1–2025.1 use FOP 2.8), and a FOP failure or missing output PDF is now a build error — earlier versions report success while the PDF is silently absent, with the full stderr transcript (including routine INFO lines) logged as Warnings; see the pdf-xslfo skill's `references/fop-engine.md`
- See the automap skill's `references/composition-jobs.md` before recommending any of the AutoMap and deploy items, and this skill's `project-parsing-guide.md` ("Origin and Synchronization") for the Designer/Express items — never suggest them to users on 2025.1 or earlier

### ePublisher 2024.1
- New AutoMap CLI executable name
- Updated registry paths

### ePublisher 2020.2
- Legacy support baseline

## Detecting Version

Use `python parse-targets.py --version` to detect Base Format Version from project files.
