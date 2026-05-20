# Reverb 2.0 Landmark Lookup-Table Schema (v1)

*Reference contract for the JSON artifact emitted by `scripts/resolve-landmarks.py dump`.*

## Purpose

A landmark lookup-table is a static JSON snapshot of every `id → (file, anchor)` binding for one Reverb 2.0 help mirror. It lets a skill that bundles a known help output resolve landmark IDs without parsing the runtime's `_lx.js` chunks at consumption time. The resolver produces an artifact (`dump`) and consumes one (`resolve --lookup-table` / `rewrite --lookup-table`). Third-party tools may parse the JSON directly using this document as the contract; reading the resolver source is not required.

## File Location and Naming Convention

Lookup-tables committed alongside the reverb2 skill live under:

```
plugins/webworks-claude-skills/skills/reverb2/references/lookup-tables/<product>-<version>-<language>.json
```

Examples:

- `epublisher-designer-2026.1-en.json`
- `tests-fixtures-stand-in.json` (verification stand-in only)

Downstream skills that bundle their own lookup-tables may use their own layout. The schema is the contract; the path is not.

## Schema (version 1)

```json
{
  "format_version": 1,
  "landmarks": {
    "<id>": { "anchor": "<string>", "file": "<string>" }
  },
  "source": {
    "captured_at": "<ISO 8601 UTC timestamp>",
    "chunks_found": <int>,
    "path": "<string>",
    "type": "local-directory"
  }
}
```

### Top-level fields

| Field | Type | Presence | Description |
|---|---|---|---|
| `format_version` | integer | required | Schema version. v1 is the only value currently defined. A consumer that does not recognize the value must reject the file (see Versioning Policy below). |
| `landmarks` | object | required | Map of landmark ID to `{file, anchor}` entry. Keys are raw Unicode strings (XML NCNames). |
| `source` | object | required | Provenance metadata describing what was dumped. |

### `source` object

| Field | Type | Presence | Description |
|---|---|---|---|
| `captured_at` | string | required | UTC timestamp of the dump, formatted `YYYY-MM-DDTHH:MM:SSZ`. The only non-deterministic field in the file. |
| `chunks_found` | integer | required | Number of `*_lx.js` chunks merged into this artifact. |
| `path` | string | required | Either the absolute path passed to `--from` (default) or the semantic label passed to `--source-label`. Committed artifacts should always use `--source-label` to avoid baking in a developer-local filesystem string. |
| `type` | string | required | Always `"local-directory"` in v1. Reserved for future source kinds (for example, a remote-fetch source). |

### `landmarks` entries

| Field | Type | Presence | Description |
|---|---|---|---|
| `file` | string | required | Relative path from the help root, forward-slash normalized, URL-decoded. May be the empty string for malformed sources but is otherwise non-empty. |
| `anchor` | string | required | Anchor identifier within the file (for example, `wwp100`). Empty string when the landmark refers to the page as a whole. The empty string is the same signal `Reverb`'s runtime uses in `GetPathById`. |

Per-entry keys are alphabetic in the emitted output (`anchor` precedes `file`). Top-level keys land in `format_version, landmarks, source` order for the same reason. JSON itself does not constrain key order, so consumers that parse into language-native maps must not depend on the in-file order.

### Worked example

```json
{
  "format_version": 1,
  "landmarks": {
    "12345678": { "anchor": "wwp200", "file": "Group/page.html" },
    "abc1234567890def": { "anchor": "wwp100", "file": "Group/page.html" },
    "getting-started-overview": { "anchor": "wwp_anchor", "file": "Group/other.html" },
    "page-only-id": { "anchor": "", "file": "Group/page.html" },
    "übersicht": { "anchor": "", "file": "Topics/uebersicht.html" },
    "概要": { "anchor": "wwp_overview", "file": "Topics/overview.html" }
  },
  "source": {
    "captured_at": "2026-05-20T15:00:00Z",
    "chunks_found": 2,
    "path": "ePublisher Designer 2026.1 Help (en)",
    "type": "local-directory"
  }
}
```

The example mixes the cases that consumers should expect: a page-only landmark (empty anchor), a paragraph-level landmark (non-empty anchor), a pass-through source ID (`getting-started-overview`), and Unicode source IDs in raw form. A reader who hand-types this into a file can point the resolver at it via `--lookup-table` and resolve any of the listed IDs.

## Encoding

- UTF-8, no BOM.
- LF line endings (`\n`). The resolver writes LF on every platform, including Windows.
- A single trailing newline at end of file.
- Files contain raw Unicode characters. The resolver emits `\u`-escape sequences only for control characters JSON requires to be escaped; everything else is the raw code point. Consumers must read as UTF-8.

## Determinism Contract

Two runs of `dump --from <dir>` against the same input produce byte-identical output except for `source.captured_at`. The rules that make this hold:

- `landmarks` keys are sorted lexicographically by raw Unicode code point.
- Chunk discovery uses `sorted(source.glob('*_lx.js'))`, already deterministic.
- When the same ID is bound by multiple chunks, the v1 resolver's "last write wins" semantics apply — matching `Landmarks.Advance()` at runtime.
- JSON is emitted with `sort_keys=True`, `ensure_ascii=False`, two-space indentation.
- `source.path` is stable for any single run, but varies across machines unless `--source-label` is used. Committed artifacts should always set `--source-label` so the value is a semantic name (for example, `"ePublisher Designer 2026.1 Help (en)"`) instead of an absolute filesystem path.

## Path Normalization

The raw `_lx.js` `f` array contains paths in Windows-style form with URL-encoded special characters (because they were generated for insertion into JavaScript strings that may become `href`s). The dump normalizes once at emit time:

- Backslashes (`\`) become forward slashes (`/`).
- URL-encoded characters (`%20`, `%2F`, and so on) are decoded.

Consumers should not re-normalize. Reading `landmarks[*].file` yields a path ready to be appended to a help-root base URL.

Anchors are emitted verbatim. The runtime does not URL-encode anchors at generation time, so no decoding is required.

## Versioning Policy

`format_version` is an integer. Consumers must reject any file whose `format_version` they do not recognize. v1 of the resolver rejects with exit code 2 and a message naming the unsupported version. Missing `format_version` is the same exit code with a message naming the field.

A bump to `format_version` is a breaking change to the schema and is the signal for downstream consumers to update. The schema may add optional fields at v1 without bumping, but no field is currently optional in v1.

## Cross-References

- `scripts/resolve-landmarks.py` — the resolver that produces and consumes the artifact.
- `workflows/landmark-resolution.md` — task-level workflow that covers both `--from` and `--lookup-table` consumer paths.
- `tests/verify-landmark-resolver.py` — runs the determinism, Unicode round-trip, parity, mutex, and version-mismatch coverage that protects this contract.
