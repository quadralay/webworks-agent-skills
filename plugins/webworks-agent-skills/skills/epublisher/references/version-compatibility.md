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

### ePublisher 2024.1
- New AutoMap CLI executable name
- Updated registry paths

### ePublisher 2020.2
- Legacy support baseline

## Detecting Version

Use `python parse-targets.py --version` to detect Base Format Version from project files.
