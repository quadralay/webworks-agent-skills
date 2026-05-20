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

Resolving them to a real HTML file requires reading the `_lx.js` chunks emitted alongside the help output. There is one `*_lx.js` chunk per document group. The resolver accepts two source modes:

| Source | When |
|--------|------|
| **Local** (`--from <path>`) | You have a downloaded mirror or are scripting against specific chunks. Fully offline. |
| **Remote** (`--remote-base-url <url>`) | You only have a published help URL; the resolver fetches and caches `_lx.js` chunks over HTTP. No download step. |

`--from` and `--remote-base-url` are mutually exclusive on every subcommand. For `rewrite`, a stable URL with an `http://` or `https://` scheme auto-infers the remote base when neither flag is set.

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
| `dump` | Source path or URL | JSON object `{id: relative_path}` (or a table with `--table`). |

Flags by category:

| Flag | Subcommands | Default | Description |
|------|-------------|---------|-------------|
| `--from <path>` | all | — | Local mirror source (mutually exclusive with `--remote-base-url`). |
| `--remote-base-url <url>` | all | — | Published help mirror source (mutually exclusive with `--from`). |
| `--no-cache` | all (remote only) | off | Skip cache; re-fetch landing page and every chunk. |
| `--cache-ttl <secs>` | all (remote only) | `86400` | Landing-page re-poll cadence. |
| `--cache-dir <path>` | all (remote only) | platform user-cache | Cache root override. |
| `--http-timeout <secs>` | all (remote only) | `10` | Per-request read timeout. |
| `--json` | `resolve` | off | Emit JSON output. |
| `--base-url <url>` | `rewrite` | — | Replace the inferred URL prefix on output. |
| `--table` | `dump` | off | Emit a human-readable table. |

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
| `1` | Resolution failure | ID not in index, URL has no ID after `#/`, malformed percent-encoding in the input URL, or no source specified. |
| `2` | Parse/IO/HTTP failure | Source path missing, chunk malformed, no `*_lx.js` files in directory, 4xx/5xx on the remote, network timeout, or DNS/TLS error. The stderr message names the failing URL. |

Most "ID not found" errors mean the chunk for that document group was not included in `--from`. Point the resolver at the full output directory (or use `--remote-base-url` for the whole mirror).

If `--from` references a single chunk and the ID belongs to a different group, the lookup will miss. The fix is to use the directory containing every `*_lx.js` chunk or switch to remote mode against the published mirror.

`HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY` are honored in remote mode without any custom configuration. Transient 5xx and read-timeout failures retry up to three times with exponential backoff before raising.

## Step 6: Rewrite Stable URLs in Bulk (Optional)

To rewrite a list of stable URLs found in skill documentation or other sources:

```bash
# Dump the index once for the help output (local or remote)
python scripts/resolve-landmarks.py dump --remote-base-url <help-mirror-url> > landmarks.json

# Then look up IDs from landmarks.json in your own script or editor
```

The `dump` JSON is small enough to commit alongside skill docs if needed; refresh it whenever the published help is regenerated (or rely on the cache's automatic invalidation).

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
- [ ] Input source identified (local `--from` directory, remote `--remote-base-url`, or `rewrite` with an HTTP URL for auto-infer)
- [ ] Resolver run with the correct mode (`resolve`, `rewrite`, or `dump`)
- [ ] Output interpreted against the runtime's anchor-formatting rules
- [ ] Any "ID not found" responses traced to the missing chunk or mistyped ID
- [ ] Any HTTP failure surfaced as exit code `2` with the failing URL in stderr — never a silent fallback
- [ ] Stable URLs (where applicable) rewritten to direct URLs ready for JS-less consumption
</success_criteria>
