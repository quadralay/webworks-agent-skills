# Version Compatibility

## Supported Versions

| Component | Minimum | Recommended | Notes |
|-----------|---------|-------------|-------|
| ePublisher | 2020.2 | 2024.1+ | Primary development target |
| AutoMap | 2020.2 | 2024.1+ | Required for automation |
| Reverb Format | 2.0 | 2.0 | Only Reverb 2.0 supported |
| Chrome | 90+ | Latest | For browser testing |
| Node.js | 16+ | 18+ | For Puppeteer scripts |
| Platform | Windows | Windows 10/11 | ePublisher is Windows-only |

## Breaking Changes by Version

### ePublisher 2026.1 (new in 2026.1 — features below do NOT exist in earlier versions)
- `useAsStationery="True"` on a job's `<Project>` element (a live `.wep`/`.wrp` as stationery)
- Federated parcel composition (Reverb 2.0): `.wacj` composition jobs, per-target deploy scope (Everything / Groups / Shell; `deployScope` attribute, `--deployscope`), `wwcomposition*` output descriptors
- Amazon S3 + CloudFront deploy destinations (named profile/role credentials, deploy-time invalidation, dry run; global `--dryrun`)
- Inline deploy-target definitions in `.waj`/`.wacj` (`<DeploySettings>`) and the `--deploysettings` overlay file
- A failed deploy is an error (reaches the exit status); earlier versions warned and exited 0
- See the automap skill's `references/composition-jobs.md` before recommending any of these — never suggest them to users on 2025.1 or earlier

### ePublisher 2024.1
- New AutoMap CLI executable name
- Updated registry paths

### ePublisher 2020.2
- Legacy support baseline

## Detecting Version

Use `python parse-targets.py --version` to detect Base Format Version from project files.
