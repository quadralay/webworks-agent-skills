# Workflow: Landmark Resolution

*From SKILL.md intake item 5.*

<required_reading>
The schema contract for the lookup-table artifact lives in `references/landmark-lookup-table.md`. Read it when consuming or producing pre-built lookup-tables (`--lookup-table` source, `dump --out` artifact). For chunk-source workflows (`--from`), no additional references are needed. The resolver mirrors the behavior of `scripts/landmarks.js` in any Reverb 2.0 output; consult that runtime file only when investigating a behavior mismatch.
</required_reading>

<process>
## Step 1: Identify the Input

Reverb 2.0 publishes stable links of the form `<prefix>#/<id>`, for example:

```
https://static.webworks.com/docs/epublisher/latest/help/#/e5d3d31c42d8d1d4
```

Resolving them to a real HTML file requires reading either the `_lx.js` chunks emitted alongside the help output (one per document group) or a pre-built lookup-table artifact. The resolver supports three input shapes:

| Input | When |
|-------|------|
| Single `*_lx.js` chunk file | You only need IDs from one document group, or you are scripting against a single chunk. |
| Directory containing chunks | Default for any "resolve this URL" scenario — the resolver globs `*_lx.js` and merges every chunk into one index. |
| Committed lookup-table artifact | A skill bundles a pre-built `dump` artifact for a well-known help mirror. Avoids re-parsing chunks on every invocation and lets a skill ship without the runtime's `_lx.js` files. See `references/landmark-lookup-table.md` for the schema. |

If the help output is hosted (e.g., `static.webworks.com`), expect a local mirror or a committed lookup-table artifact. Download the help directory (or the specific `*_lx.js` chunk you need) before running the resolver, or generate a lookup-table once and ship it. Remote `_lx.js` fetching is deferred follow-up work — see the plan's "Deferred to Follow-Up Work".

### Landmark ID formats

The resolver treats the ID as an opaque string. As of Reverb 2026.1, projects may emit any of:

- 16-character hex hash (default; all releases)
- 8-character hex hash (opt-in)
- Pass-through source ID (opt-in)

Do not regex, length-check, or hex-validate IDs in callers. Use whatever appears after `#/` verbatim.

## Step 2: Run the Resolver

```bash
# Resolve a single ID against one chunk
python scripts/resolve-landmarks.py resolve <id> --from <chunk-or-dir>

# Resolve a single ID against a committed lookup-table artifact
python scripts/resolve-landmarks.py resolve <id> --lookup-table <file>

# Rewrite a full stable URL into a direct URL (--from or --lookup-table)
python scripts/resolve-landmarks.py rewrite <stable-url> --from <chunk-or-dir>
python scripts/resolve-landmarks.py rewrite <stable-url> --lookup-table <file>

# Dump every (id → path) binding as a schema'd lookup-table artifact
python scripts/resolve-landmarks.py dump --from <chunk-or-dir> \
    --out landmarks.json --source-label "Product Name X.Y.Z Help (lang)"
```

`--from` and `--lookup-table` are mutually exclusive on `resolve` and `rewrite`; passing both is a usage error (exit 2).

Modes:

| Mode | Input | Output |
|------|-------|--------|
| `resolve <id>` | A landmark ID, plus `--from <chunk-or-dir>` or `--lookup-table <file>` | Resolved relative path (`file.html` or `file.html#anchor`). Add `--json` for `{"id": ..., "path": ...}`. |
| `rewrite <url>` | A stable URL (`<prefix>#/<id>`), plus `--from` or `--lookup-table` | A direct URL: `<prefix><resolved-path>`. Add `--base-url <url>` to swap the prefix. |
| `dump` | `--from <chunk-or-dir>` | Schema'd JSON artifact (see `references/landmark-lookup-table.md`). `--out <file>` writes to disk; `--source-label <s>` overrides `source.path` for committed artifacts; `--table` emits the legacy human-readable form. |

## Step 3: Interpret the Output

The resolver returns paths exactly as the Reverb runtime's `GetPathById()` does:

- **Empty anchor** → bare file path (e.g., `Group/page.html`)
- **Non-empty anchor** → `file#anchor` (e.g., `Group/page.html#wwp100`)

If an ID appears multiple times in the chunks (typical: one page-level row at anchor index 0, one paragraph-level row at a specific anchor), the resolver applies **last-write-wins** — which usually returns the paragraph-level `file#anchor` form. This matches the runtime contract.

## Step 4: Handle "ID Not Found"

The resolver exits non-zero when an ID is not in the merged index:

| Exit code | Meaning | Common cause |
|-----------|---------|--------------|
| `0` | Success | Resolved successfully. |
| `1` | Resolution failure | ID not in index, or URL has no ID after `#/`. |
| `2` | Parse/IO failure | Source path missing, chunk malformed, or no `*_lx.js` files in directory. |

Most "ID not found" errors mean the chunk for that document group was not included in `--from`. Point the resolver at the full output directory rather than a single chunk.

If `--from` references a single chunk and the ID belongs to a different group, the lookup will miss. The fix is to use the directory containing every `*_lx.js` chunk.

## Step 5: Rewrite Stable URLs in Bulk (Optional)

To rewrite a list of stable URLs found in skill documentation or other sources:

```bash
# Dump the index once for the help output as a schema'd artifact
python scripts/resolve-landmarks.py dump \
    --from <help-mirror-dir> \
    --out landmarks.json \
    --source-label "<Product> <Version> Help (<lang>)"

# Then resolve IDs against the artifact at O(1) per query
python scripts/resolve-landmarks.py resolve <id> --lookup-table landmarks.json

# Or load landmarks.json directly in your own tooling
```

Always set `--source-label` for committed artifacts — the default `source.path` is the absolute filesystem path of `--from`, which embeds a developer-local value and defeats the determinism contract across machines.

The artifact is byte-deterministic across runs (modulo `source.captured_at`), so committing it produces a stable diff each time the source help is regenerated. See `references/landmark-lookup-table.md` for the schema, encoding, and versioning policy.

## Schema and Downstream Consumers

> **Migration note:** Earlier prereleases of `dump` emitted a flat `{id: "file#anchor"}` JSON map. Plugin 2.12.0 replaces that shape with the schema'd `{format_version, landmarks, source}` artifact described below. Any captured output from the old shape is no longer compatible; re-run `dump --out <file> --source-label <name>` to regenerate against the current schema. The `--table` output is unchanged.

The `dump` artifact follows a documented contract:

- **Schema reference:** [`../references/landmark-lookup-table.md`](../references/landmark-lookup-table.md) — top-level fields, per-entry shape, encoding, determinism, versioning.
- **Pre-built artifacts:** [`../references/lookup-tables/`](../references/lookup-tables/) — committed examples and verification fixtures.

Third-party tooling can parse the artifact JSON directly using the schema doc; reading `scripts/resolve-landmarks.py` is not required. Resolvers older than the artifact's `format_version` will reject the file with exit code 2 rather than silently producing wrong results.

## Worked Example

The ePublisher XSLT extensions doc is published at the stable URL:

```
https://static.webworks.com/docs/epublisher/latest/help/#/e5d3d31c42d8d1d4
```

Assume the help mirror is downloaded to `./help-mirror/`:

```bash
# Resolve just the ID
python scripts/resolve-landmarks.py \
    resolve e5d3d31c42d8d1d4 \
    --from ./help-mirror/

# Rewrite the full URL
python scripts/resolve-landmarks.py \
    rewrite "https://static.webworks.com/docs/epublisher/latest/help/#/e5d3d31c42d8d1d4" \
    --from ./help-mirror/
```

The `rewrite` form returns the direct URL with the resolved file path appended after the original prefix. AI consumers can then fetch that URL without executing the Reverb JavaScript runtime.
</process>

<success_criteria>
This workflow is complete when:
- [ ] Input source identified (single chunk or directory mirror)
- [ ] Resolver run with the correct mode (`resolve`, `rewrite`, or `dump`)
- [ ] Output interpreted against the runtime's anchor-formatting rules
- [ ] Any "ID not found" responses traced to the missing chunk or mistyped ID
- [ ] Stable URLs (where applicable) rewritten to direct URLs ready for JS-less consumption
</success_criteria>
