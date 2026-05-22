# Workflow: Landmark Resolution

*From SKILL.md intake item 5.*

<required_reading>
**No additional references needed** - all information is in this file. The resolver mirrors the behavior of `scripts/landmarks.js` in any Reverb 2.0 output; consult that runtime file only when investigating a behavior mismatch.
</required_reading>

<process>
## Step 1: Identify the Input

Reverb 2.0 publishes stable links of the form `<prefix>#/<id>`, for example:

```
https://static.webworks.com/docs/epublisher/latest/help/#/e5d3d31c42d8d1d4
```

Resolving them to a real HTML file requires reading the `_lx.js` chunks emitted alongside the help output. There is one `*_lx.js` chunk per document group. The resolver accepts three source modes:

| Source | When |
|--------|------|
| **Local** (`--from <path>`) | You have a downloaded mirror or are scripting against specific chunks. Fully offline. |
| **Remote** (`--remote-base-url <url>`) | You only have a published help URL; the resolver fetches and caches `_lx.js` chunks over HTTP. No download step. |
| **Lookup table** (`--lookup-table <file>`) | You have a pre-built dump artifact for a known mirror (e.g., the ePublisher Designer 2026.1 help fixture this skill ships). Fully offline, O(1) per query, no chunk parsing. |

`--from`, `--remote-base-url`, and `--lookup-table` are mutually exclusive on every subcommand. For `rewrite`, a stable URL with an `http://` or `https://` scheme auto-infers the remote base when no source flag is set.

### Step 1a: Local mirror

Point `--from` at a single `*_lx.js` chunk or a directory containing chunks:

```bash
python scripts/resolve-landmarks.py resolve <id>      --from <chunk-or-dir>
python scripts/resolve-landmarks.py rewrite <url>     --from <chunk-or-dir>
python scripts/resolve-landmarks.py dump              --from <chunk-or-dir>
```

The directory mode globs `*_lx.js` and merges every chunk into one index.

### Step 1b: Remote mirror

Point `--remote-base-url` at the help mirror root (the URL the runtime resolves stable links against):

```bash
python scripts/resolve-landmarks.py resolve <id>  --remote-base-url <url>
python scripts/resolve-landmarks.py rewrite <url> --remote-base-url <url>
python scripts/resolve-landmarks.py dump          --remote-base-url <url>
```

For `rewrite` you can also just pass the stable URL — the base is inferred:

```bash
# Equivalent to: rewrite ... --remote-base-url https://static.webworks.com/docs/epublisher/latest/help/
python scripts/resolve-landmarks.py rewrite \
    "https://static.webworks.com/docs/epublisher/latest/help/#/e5d3d31c42d8d1d4"
```

### Step 1c: Lookup table (pre-built artifact)

Point `--lookup-table` at a JSON file produced by `dump`:

```bash
python scripts/resolve-landmarks.py resolve <id>  --lookup-table <path/to/dump.json>
python scripts/resolve-landmarks.py rewrite <url> --lookup-table <path/to/dump.json>
```

Use this when you know in advance which mirror you are resolving against and want to ship the lookup data alongside the skill or tool — no chunk parsing at runtime, no network access, no dependency on the chunks being reachable. The resolver loads the JSON once and serves every query from an in-memory dict. The artifact is `format_version: 1` and the resolver refuses any other version with exit code 2.

### Landmark ID formats

The resolver treats the ID as an opaque string. As of Reverb 2026.1, projects may emit any of:

- 16-character hex hash (default; all releases)
- 8-character hex hash (opt-in)
- Pass-through source ID (opt-in)

Do not regex, length-check, or hex-validate IDs in callers. Use whatever appears after `#/` verbatim.

Percent-encoded fragments (e.g., `#/%E6%A6%82%E8%A6%81` for `概要`) are URL-decoded before lookup — matching how the browser runtime's `decodeURIComponent` step resolves them. The decoded ID flows into the index lookup unchanged.

## Step 2: Run the Resolver

Subcommands:

| Mode | Input | Output |
|------|-------|--------|
| `resolve <id>` | A landmark ID | Resolved relative path (`file.html` or `file.html#anchor`). Add `--json` for `{"id": ..., "path": ...}`. |
| `rewrite <url>` | A stable URL (`<prefix>#/<id>`) | A direct URL: `<prefix><resolved-path>`. Add `--base-url <url>` to swap the prefix. |
| `dump` | Source path or URL | Structured JSON `{format_version, source, landmarks}` on stdout (or a table with `--table`, or a file with `--out <file>`). See [Dump Artifact Schema](#dump-artifact-schema). |
| `reverse <path>` | A file path (raw or percent-encoded) | Landmark IDs bound to the path, one per line. Add `--first` for the page-level binding only (runtime `GetIdByPath` shape), `--anchor <id>` to target a specific anchor, or `--json` for `{path, matches:[{id, anchor},...]}`. See [Step 7](#step-7-reverse-lookup--find-ids-that-target-a-path). |

Flags by category:

| Flag | Subcommands | Default | Description |
|------|-------------|---------|-------------|
| `--from <path>` | all | — | Local mirror source (mutually exclusive with `--remote-base-url` and `--lookup-table`). |
| `--remote-base-url <url>` | all | — | Published help mirror source (mutually exclusive with `--from` and `--lookup-table`). |
| `--lookup-table <file>` | `resolve`, `rewrite`, `reverse` | — | Pre-built dump artifact (mutually exclusive with `--from` and `--remote-base-url`). |
| `--no-cache` | all (remote only) | off | Skip cache; re-fetch landing page and every chunk. |
| `--cache-ttl <secs>` | all (remote only) | `86400` | Landing-page re-poll cadence. |
| `--cache-dir <path>` | all (remote only) | platform user-cache | Cache root override. |
| `--http-timeout <secs>` | all (remote only) | `10` | Per-request read timeout. |
| `--json` | `resolve`, `reverse` | off | Emit JSON output. |
| `--base-url <url>` | `rewrite` | — | Replace the inferred URL prefix on output. |
| `--out <file>` | `dump` | stdout | Write structured JSON to `<file>`. `-` is an explicit stdout alias. |
| `--table` | `dump` | off | Emit a human-readable table instead of structured JSON. |
| `--first` | `reverse` | off | Return only the page-level (empty-anchor) binding — runtime `GetIdByPath` shape. |
| `--anchor <id>` | `reverse` | — | Return only the binding for this specific anchor (mutually exclusive with `--first`). |

## Step 3: Interpret the Output

The resolver returns paths exactly as the Reverb runtime's `GetPathById()` does:

- **Empty anchor** → bare file path (e.g., `Group/page.html`)
- **Non-empty anchor** → `file#anchor` (e.g., `Group/page.html#wwp100`)

In remote mode, `rewrite` percent-quotes the path portion of the output URL so it is paste-ready for HTTP fetch tools. Spaces become `%20`; path separators (`/`) stay as `/`. The fragment portion (`#anchor`) is left as-is — runtime anchors are already URL-safe.

If an ID appears multiple times in the chunks (typical: one page-level row at anchor index 0, one paragraph-level row at a specific anchor), the resolver applies **last-write-wins** — which usually returns the paragraph-level `file#anchor` form. This matches the runtime contract.

## Step 4: Cache Behavior (remote mode)

Remote mode caches discovered `_lx.js` chunks under a per-base subdirectory of the user cache root:

| Platform | Cache root |
|----------|------------|
| Windows | `%LOCALAPPDATA%\webworks\reverb-landmarks\` |
| macOS | `~/Library/Caches/webworks/reverb-landmarks/` |
| Linux | `$XDG_CACHE_HOME/webworks/reverb-landmarks/` (falls back to `~/.cache/webworks/reverb-landmarks/`) |

Within that root, each base URL gets its own directory keyed by `<host>/<percent-encoded-path>/`. Two base URLs that differ only in trailing slash get distinct caches.

**Invalidation:** Reverb 2.0 emits a `GLOBAL_GENERATION_HASH` constant into each build's landing page. The resolver caches that hash alongside the chunks; when the mirror rebuilds, the next remote invocation after `--cache-ttl` seconds sees a new hash and re-fetches every chunk atomically. Within the TTL window, the resolver uses cached chunks without any network access.

If a mirror ships without `GLOBAL_GENERATION_HASH`, the resolver falls back to TTL-only invalidation and prints a one-line warning to stderr.

**Force a refresh:** pass `--no-cache` to skip every cache check for that invocation.

**Manual clear:** delete the per-base directory or the entire cache root. The cache is per-user scratch — nothing else depends on it.

## Step 5: Handle "ID Not Found" and Failures

| Exit code | Meaning | Common causes |
|-----------|---------|---------------|
| `0` | Success | Resolved successfully. |
| `1` | Resolution failure | ID not in index, URL has no ID after `#/`, malformed percent-encoding in the input URL or path, or no source specified. Also: `reverse` path not in index, `--anchor <id>` not bound on the path, or `--first` with no page-level binding. |
| `2` | Parse/IO/HTTP failure | Source path missing, chunk malformed, no `*_lx.js` files in directory, 4xx/5xx on the remote, network timeout, or DNS/TLS error. The stderr message names the failing URL. Also: malformed `--lookup-table` JSON, an unsupported `format_version` in the artifact, or `reverse --anchor ""` (use `--first` instead). |

Most "ID not found" errors mean the chunk for that document group was not included in `--from`. Point the resolver at the full output directory (or use `--remote-base-url` for the whole mirror).

If `--from` references a single chunk and the ID belongs to a different group, the lookup will miss. The fix is to use the directory containing every `*_lx.js` chunk or switch to remote mode against the published mirror.

`HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY` are honored in remote mode without any custom configuration. Transient 5xx and read-timeout failures retry up to three times with exponential backoff before raising.

## Step 6: Rewrite Stable URLs in Bulk (Optional)

To rewrite a list of stable URLs found in skill documentation or other sources, dump the index once and consume the artifact in a script or via `--lookup-table`:

```bash
# Dump the index once (local or remote source) into a structured JSON artifact
python scripts/resolve-landmarks.py dump --remote-base-url <help-mirror-url> --out landmarks.json

# Option A: feed the artifact back into the resolver — O(1) per query, no chunk parsing
python scripts/resolve-landmarks.py rewrite "<stable-url>" --lookup-table landmarks.json

# Option B: parse the JSON in your own tooling — see "Dump Artifact Schema" below
```

The artifact is structured, versioned (`format_version: 1`), and deterministic — running `dump` twice against the same source produces byte-identical output excluding `source.captured_at`. Commit the artifact alongside skill docs if it is small enough to be diff-friendly; refresh it whenever the published help is regenerated.

## Step 7: Reverse Lookup — Find IDs That Target a Path

The `reverse` subcommand answers the inverse of `resolve`: given a file path, return the landmark IDs that resolve to it. Two workflows drive this:

- **Stable-URL minting** — you have a file path (from a search hit, a sitemap, or a direct browse) and need the stable ID to build a `<prefix>#/<id>` URL that survives future help reorganizations.
- **Link audits** — you want every stable ID that points at a given page, so you can find references in skill docs or customer-facing material that would break if the page is restructured or removed.

```bash
# Bare output: every binding for the path, one ID per line, with the page-level
# (empty-anchor) binding emitted first.
python scripts/resolve-landmarks.py reverse "Group/page.html" --from ./help-mirror/
# page-only-id
# abc1234567890def
# 12345678
```

Filter to a single binding with `--first` (matches the runtime's `GetIdByPath` shape) or `--anchor <id>` (a specific anchor):

```bash
# Only the page-level binding (no anchor) — paste-ready for "this whole page"
# stable URLs.
python scripts/resolve-landmarks.py reverse "Group/page.html" --first --from ./help-mirror/
# page-only-id

# Only the binding bound to anchor "wwp100" — paste-ready for "this paragraph"
# stable URLs.
python scripts/resolve-landmarks.py reverse "Group/page.html" --anchor wwp100 --from ./help-mirror/
# abc1234567890def
```

For programmatic consumers, `--json` emits a structured payload:

```bash
python scripts/resolve-landmarks.py reverse "Group/page.html" --json --from ./help-mirror/
# {"path": "Group/page.html",
#  "matches": [{"id": "page-only-id", "anchor": ""},
#              {"id": "abc1234567890def", "anchor": "wwp100"},
#              {"id": "12345678", "anchor": "wwp200"}]}
```

On a miss (path not in index, `--anchor` not bound, `--first` with no empty-anchor row) `reverse` exits `1` and writes a flag-specific message to stderr. With `--json`, the same payload shape is preserved: `{"path": ..., "matches": [], "error": "<reason>"}` on stdout.

**Multi-binding ordering.** Output is sorted by `(anchor, landmark_id)`. The empty-anchor (page-level) binding sorts first.

**Unicode and percent-encoding.** The input path is `urllib.parse.unquote`'d once before lookup; raw and percent-encoded forms of the same path return the same IDs. Landmark IDs in the output may be raw Unicode strings (e.g., `概要`) when the source emits source-ID format. Pass paths exactly as they appear in the `_lx.js` `f` array — `reverse` does not normalize separators, strip `./`, or resolve `..`.

**Don't include `#anchor` in the path.** The lookup keys files only, so `Group/page.html#wwp100` will miss. Use `--anchor wwp100` and the bare path instead.

**Anchor strings are not globally unique.** `reverse <path> --anchor <id>` and `reverse <other-path> --anchor <id>` can resolve to different landmark IDs — anchors are scoped to their file.

### Worked Example: Mint a Stable URL from a Known Path

You browsed the published help and found that the topic you want to link to is rendered at `Advanced Customizations/_xslt-extensions.04.1.html`. Mint the page-level stable URL:

```bash
ID=$(python scripts/resolve-landmarks.py reverse \
    "Advanced Customizations/_xslt-extensions.04.1.html" \
    --first \
    --remote-base-url https://static.webworks.com/docs/epublisher/latest/help/)
echo "https://static.webworks.com/docs/epublisher/latest/help/#/$ID"
```

The minted URL is what to drop into skill docs or customer-facing material — it survives future help reorganizations because the runtime resolves it back through `landmarks.js`.

### Worked Example: Link Audit Against a Lookup Table

You have a list of paths (perhaps from a sitemap dump) and want to find every stable ID that targets any of them. Use the pre-built lookup-table artifact so the query is O(1) per path with no chunk parsing:

```bash
# tests/fixtures/epublisher-designer-2026.1-help-lookup.json is committed in
# this skill. Substitute your own dump.json for a different mirror.
while read -r path; do
    python scripts/resolve-landmarks.py reverse "$path" \
        --lookup-table tests/fixtures/epublisher-designer-2026.1-help-lookup.json \
        --json
done < paths-to-audit.txt
```

Each line is a self-contained JSON object — pipe through `jq` to filter, count, or join against your own data.

## Dump Artifact Schema

`dump` emits a structured JSON document. Consumers (including `--lookup-table`) read this shape:

```json
{
  "format_version": 1,
  "source": {
    "type": "local-directory",
    "path": "C:/Program Files/WebWorks/ePublisher/2026.1/ePublisher Designer/Help/en",
    "chunks_found": 7,
    "captured_at": "2026-05-21T00:00:00Z"
  },
  "landmarks": {
    "e5d3d31c42d8d1d4": {
      "file": "Advanced Customizations_ Overrides_ and Extensions/_xslt-extensions.04.1.html",
      "anchor": ""
    }
  }
}
```

| Field | Type | Notes |
|-------|------|-------|
| `format_version` | integer | Currently `1`. The resolver refuses unknown versions with exit code 2 — hard gate, no auto-coerce. |
| `source.type` | string | Closed set: `"local-directory"` (from `--from`) or `"remote-base-url"` (from `--remote-base-url`). |
| `source.path` | string | Verbatim `--from` value. Present only when `source.type == "local-directory"`. |
| `source.base_url` | string | Verbatim `--remote-base-url` value. Present only when `source.type == "remote-base-url"`. |
| `source.chunks_found` | integer | Number of `_lx.js` chunks merged into the artifact. |
| `source.captured_at` | string | UTC, ISO 8601, second precision, trailing `Z` (e.g., `2026-05-21T00:00:00Z`). The only field that differs across deterministic re-runs. |
| `landmarks` | object | Sorted map of `id → {file, anchor}`. `anchor` may be empty. |

Resolution: `file#anchor` when `anchor` is non-empty, bare `file` otherwise — matches the runtime's `GetPathById` formatting.

Unicode: landmark IDs are emitted as raw UTF-8 (`ensure_ascii=False`). A `概要` source ID appears literally in the file, not as `\uXXXX`.

Schema evolution: `format_version` is a hard gate. Future schema changes ride a version bump; the resolver refuses unknown versions with exit code 2.

## Worked Example: Remote Mirror

The ePublisher XSLT extensions doc is published at the stable URL:

```
https://static.webworks.com/docs/epublisher/latest/help/#/e5d3d31c42d8d1d4
```

With no local mirror:

```bash
# Auto-inferred base URL (rewrite mode reads the URL itself):
python scripts/resolve-landmarks.py \
    rewrite "https://static.webworks.com/docs/epublisher/latest/help/#/e5d3d31c42d8d1d4"
```

Expected output:

```
https://static.webworks.com/docs/epublisher/latest/help/Advanced%20Customizations/_xslt-extensions.04.1.html
```

Notes:
- First invocation fetches the landing page, reads `GLOBAL_GENERATION_HASH`, fetches every discovered `_lx.js` chunk, and caches them under `%LOCALAPPDATA%\webworks\reverb-landmarks\static.webworks.com\docs%2Fepublisher%2Flatest%2Fhelp%2F\` (Windows) or the equivalent macOS/Linux path.
- Subsequent invocations within 24 hours use the cache directly — no network access.
- Spaces in the resolved path are percent-quoted in the output URL (`Advanced Customizations` → `Advanced%20Customizations`) so the URL is paste-ready for `curl`, `wget`, or any HTTP fetch tool.

## Worked Example: Local Mirror

The same query, against a downloaded mirror:

```bash
# Resolve just the ID
python scripts/resolve-landmarks.py \
    resolve e5d3d31c42d8d1d4 \
    --from ./help-mirror/

# Rewrite the full URL (no percent-quoting in local mode)
python scripts/resolve-landmarks.py \
    rewrite "https://static.webworks.com/docs/epublisher/latest/help/#/e5d3d31c42d8d1d4" \
    --from ./help-mirror/
```

The `rewrite` form returns the direct URL with the resolved file path appended after the original prefix. AI consumers can then fetch that URL without executing the Reverb JavaScript runtime.
</process>

<success_criteria>
This workflow is complete when:
- [ ] Input source identified (local `--from` directory, remote `--remote-base-url`, pre-built `--lookup-table` artifact, or `rewrite` with an HTTP URL for auto-infer)
- [ ] Resolver run with the correct mode (`resolve`, `rewrite`, `dump`, or `reverse`)
- [ ] Output interpreted against the runtime's anchor-formatting rules
- [ ] Any "ID not found" responses traced to the missing chunk or mistyped ID
- [ ] Any HTTP failure surfaced as exit code `2` with the failing URL in stderr — never a silent fallback
- [ ] Stable URLs (where applicable) rewritten to direct URLs ready for JS-less consumption
- [ ] If reverse-looking up a path, the chosen output mode (default, `--first`, `--anchor`) matches the workflow (audit vs. URL-mint)
</success_criteria>
