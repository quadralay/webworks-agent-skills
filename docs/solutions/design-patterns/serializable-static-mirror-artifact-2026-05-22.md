---
title: Ship a versioned, deterministic, provenance-stamped JSON artifact when a static-mirror tool needs to distribute its index alongside skills
date: 2026-05-22
category: design-patterns
module: reverb2
problem_type: design_pattern
component: tooling
severity: medium
applies_when:
  - A static-mirror tool (e.g., a JS-less resolver for a JS-runtime URL scheme) already exists, and a downstream consumer wants a pre-built lookup it can ship with the skill or tool instead of parsing source files at runtime
  - The consumer needs O(1) lookups, zero network access, and zero dependency on the upstream's source files being reachable
  - Multiple consumers (the original dynamic resolver, the bundled consumer, future skill authors) must produce byte-identical resolution output from the same input
  - The artifact will be reviewed in PRs and committed alongside skill code, so determinism, readability, and minimal diff churn on refresh all matter
  - The artifact's schema is likely to evolve and consumers must fail loudly rather than guess forward compatibility
related_components:
  - reverb2
  - epublisher
  - tooling
tags:
  - reverb2
  - landmark-resolver
  - static-mirror
  - serialization
  - format-versioning
  - provenance
  - determinism
  - unicode-preservation
---

# Ship a versioned, deterministic, provenance-stamped JSON artifact when a static-mirror tool needs to distribute its index alongside skills

## Context

Issue #54 added a JS-less landmark resolver (`reverb-landmark-resolver-static-mirror-2026-05-20.md`). Issue #76 extended it to fetch chunks over HTTP (`static-mirror-remote-fetch-cache-2026-05-20.md`). Both deal with *resolving* — turning a stable ID into a file path on demand. Neither answered a third agent-shaped question: "I know in advance which mirror I will resolve against. Can I ship a baked lookup table with my skill so resolution costs no chunk parsing, no HTTP, and no dependency on the upstream being reachable?"

Issue #77 added the artifact half: a `dump` subcommand that emits a structured JSON file, and a `--lookup-table <file>` source on `resolve` / `rewrite` that consumes the artifact. The committed `epublisher-designer-2026.1-help-lookup.json` (1003 landmarks, 142 KB) is the first artifact this skill ships.

The interesting design work was not "emit JSON" — the v1 `dump` subcommand already did that. It was answering five questions a flat `{id: "file#anchor"}` map cannot:

1. **Will this artifact survive a schema change?** The flat shape had no version. A consumer pinning to today's keys would silently mis-resolve the day the schema evolved.
2. **Where did this artifact come from?** A committed JSON blob with no provenance is a JSON blob nobody trusts. Reviewers cannot tell which mirror, how many chunks, when captured, or whether the file is stale.
3. **Can two consumers — the runtime, the dynamic resolver, the bundled consumer — produce *byte-identical* resolution output from the same input?** Not "equivalent". Identical, including anchor-formatting rules and Unicode encoding.
4. **Will the artifact diff cleanly on refresh?** A non-deterministic serializer (key order, whitespace, trailing newline, line endings, `\uXXXX` escapes) inflates diffs to the point of un-reviewability.
5. **What happens when the schema does change?** Auto-coerce? Best-effort? Or fail loudly?

The pattern below answers those questions in the order they bite.

## Guidance

When extending a static-mirror tool with a serializable artifact form, treat the *artifact* as an interchange contract — not as a serialization of the in-memory index.

### Rule 1 — Version the artifact, and make the version a hard gate

The first scalar in the artifact is a `format_version`. Consumers refuse to load any value they do not understand, with an explicit error message, exit code 2, and a stderr line that names the unsupported version verbatim.

```python
def load_lookup_table(path: Path) -> dict:
    # ...read, JSON-parse, type-check root...
    if 'format_version' not in data:
        raise ValueError(f"{path}: missing 'format_version'; this build understands 1")
    if data['format_version'] != 1:
        raise ValueError(
            f"unsupported format_version {data['format_version']!r}; this build understands 1"
        )
    if not isinstance(data.get('landmarks'), dict):
        raise ValueError(f"{path}: 'landmarks' is missing or not an object")
    return data
```

The hard gate is the load-bearing detail. A soft check (warn-and-coerce) defers the failure to whatever mis-resolves silently downstream — exactly the loudness the version field was added to provide. Future schema changes ride a version bump; the resolver's refusal to guess forward-compatibility is the *only* thing that earns the field its place in the artifact.

### Rule 2 — Stamp provenance into the artifact, not into a sidecar

Every artifact carries a `source` block with the four facts a reviewer needs to triage it:

| Field | Why |
|-------|-----|
| `type` | Closed-set enum (`local-directory` \| `remote-base-url`); consumers can switch on it. Open-ended strings invite fragmentation. |
| `path` or `base_url` | Verbatim CLI input. Not absolutized, not relativized. Documents what the operator typed. |
| `chunks_found` | Sanity-check signal: "I expected 7, why does this artifact say 1?" The number falls out of the build for free. |
| `captured_at` | UTC ISO-8601 with trailing `Z`, second precision. The only field that legitimately differs across deterministic re-runs. |

```python
def _build_dump_artifact(files, anchors, id_to_pair, *,
                        source_type, source_value, chunks_found, captured_at):
    source_block = {
        'type': source_type,
        'chunks_found': chunks_found,
        'captured_at': captured_at,
    }
    if source_type == SOURCE_TYPE_REMOTE:
        source_block['base_url'] = source_value
    else:
        source_block['path'] = source_value
    landmarks = {
        landmark_id: {'file': files[fi], 'anchor': anchors[ai]}
        for landmark_id, (fi, ai) in id_to_pair.items()
    }
    return {
        'format_version': 1,
        'source': source_block,
        'landmarks': landmarks,
    }
```

Keep the `source.type` values as named module constants so the producer and consumer reference one symbol, not two stringly-typed copies that can drift apart:

```python
SOURCE_TYPE_LOCAL = 'local-directory'
SOURCE_TYPE_REMOTE = 'remote-base-url'
```

A sidecar file (`landmarks.json` + `landmarks.meta.json`) is the alternative. Reject it: two-file artifacts can desynchronize; one-file artifacts cannot.

### Rule 3 — Make resolution byte-identical across the dynamic and bundled paths via a single formatter

A consumer with `--lookup-table` and a consumer with `--from` must produce the exact same string for the same input. Not "equivalent". Identical. Achieve that by routing both paths through one formatter:

```python
def _format_path(file_path: str, anchor: str) -> str:
    """`file#anchor` when `anchor` is non-empty, bare `file` otherwise.

    Single source of truth for the runtime's GetPathById formatting; shared by
    chunk-based and lookup-table-based resolution so they stay byte-identical.
    """
    return f"{file_path}#{anchor}" if anchor else file_path
```

```python
def resolve_id(landmark_id, files, anchors, id_to_pair):
    pair = id_to_pair.get(landmark_id)
    if pair is None:
        return None
    file_idx, anchor_idx = pair
    return _format_path(files[file_idx], anchors[anchor_idx])

def resolve_id_from_lookup(landmark_id, lookup):
    entry = lookup['landmarks'].get(landmark_id)
    if entry is None:
        return None
    return _format_path(entry.get('file', ''), entry.get('anchor', ''))
```

Two formatter copies will drift. The lookup version will add a defensive `str(...)` here, the chunk version will add an `or ''` there, and on some edge case the two paths will return different bytes for the same logical answer. One formatter shared by both paths makes that drift impossible by construction.

The verifier closes the loop on this rule: a round-trip test resolves every ID through both paths and asserts byte-equality, against both the unit fixtures *and* the committed real artifact.

### Rule 4 — Deterministic serialization is a property of the writer, not a comment

A committed artifact will be re-dumped every time the upstream regenerates. The diff that lands in the next PR must reflect *only* what changed upstream — not what changed about the dump tool's mood that day. That requires nailing five details together, none optional:

```python
json_text = json.dumps(artifact, ensure_ascii=False, sort_keys=True, indent=2) + '\n'
payload = json_text.encode('utf-8')
if args.out is None or args.out == '-':
    sys.stdout.buffer.write(payload)
    sys.stdout.flush()
else:
    Path(args.out).write_bytes(payload)
```

| Detail | What it controls | Failure mode if wrong |
|--------|------------------|-----------------------|
| `ensure_ascii=False` | Unicode IDs and file paths emit as raw UTF-8 | `概要` becomes `概要`; a hex viewer can't grep for the source ID; consumers must re-decode |
| `sort_keys=True` | Key order is dict-insertion-independent | Dump twice, get two different orderings — every refresh is a fake diff |
| `indent=2` | One canonical whitespace shape | Pretty-print drift across machines/versions |
| `+ '\n'` | Trailing newline | POSIX tools choke; line-ending diffs on every commit |
| `write_bytes` / `sys.stdout.buffer.write` | Bypasses Windows CRLF translation | Same source produces `\n`-encoded artifact on Linux, `\r\n`-encoded on Windows — byte-determinism broken across operating systems |

The last row is the one that bites silently. Python's text-mode writes on Windows expand `\n` to `\r\n`. A round-trip test running on the developer's Linux box passes; the same test in a Windows CI run produces a different artifact byte stream. Forcing the write through the bytes path eliminates the asymmetry.

Determinism is asserted in the verifier by dumping twice and diffing everything *except* `source.captured_at`. The captured-at field is the only legitimate source of difference across runs; the assertion proves that no other field accidentally became non-deterministic.

### Rule 5 — Unicode preservation flows from one line, but earns its own test

`ensure_ascii=False` is one line. Forgetting it costs nothing today (Reverb's default ID format is hex) and silently breaks the day someone ships a `landmark-id-format: source-id` project with non-ASCII NCNames (`概要`, `übersicht`). The runtime tolerates them; the artifact must too.

Forcing the test even when the production data is all ASCII is the load-bearing decision. The `unicode-ids_lx.js` fixture exercises a code path that no real ePublisher 2026.1 mirror exercises yet — but will, the moment a customer turns on source-id mode. The test prevents the regression that would otherwise be invisible until a customer ships a Unicode-ID project.

The verifier check is a hex assertion: open the file, look for the UTF-8 bytes `e6 a6 82 e6 a6 81` literally, fail if any `\u`-escape appears anywhere in the artifact.

### Rule 6 — Reject `--lookup-table` on `dump`; accept it on `resolve` / `rewrite`

The verb hierarchy is: `dump` produces an artifact from a source. `resolve` / `rewrite` consume a source. A lookup-table is a *consumer* source — not something you `dump` from. Reuse the same mutually-exclusive `--from` / `--remote-base-url` / `--lookup-table` argparse group across all three subcommands, but reject the combination at the subcommand handler:

```python
def cmd_dump(args):
    if getattr(args, 'lookup_table', None):
        error_log("--lookup-table is not a valid source for dump; use --from or --remote-base-url")
        return 1
    # ...
```

The argparse group handles the *exclusion* (you cannot pass two source flags at once); the handler handles the *applicability* (`dump --lookup-table` is nonsensical even when it parses). A user typing `dump --lookup-table x.json` should see an explicit "this combination isn't supported" message, not a Python traceback or silent no-op.

## Why This Matters

**Versioning is the only durable answer to "is this artifact still valid?".** A skill that ships a baked lookup is a skill that froze a representation of the upstream mirror at a point in time. Some of those freezes will outlive the schema. The `format_version` field is what lets the resolver refuse to mis-resolve when that happens — and what lets a future schema change confidently land without invalidating every shipped artifact in the wild. The hard-gate decision (refuse, don't coerce) is the only one that makes the field load-bearing rather than decorative.

**Provenance is the only durable answer to "do I trust this committed file?".** A 142 KB JSON blob with 1003 keys is exactly the kind of file a reviewer rubber-stamps because nobody can read it. The 4-line `source` block at the top of the artifact is what makes the file reviewable: type, where, how-many, when. Those four facts answer 90% of the "is this stale?" questions reviewers ask, before they have to read a single landmark entry.

**Byte-identical resolution is a correctness property, not a stylistic preference.** Two consumers can disagree about `file#anchor` versus `file` versus `file#` and never notice in CI, because each consumer's tests pass against its own formatter. The bug surfaces in production when a downstream tool string-compares two resolved URLs from two different paths and gets non-equal strings for the same logical input. One shared `_format_path` helper, exercised by both paths in the same test, is the cheapest way to make the bug impossible.

**Diff-cleanliness compounds over time.** Every refresh of a committed artifact is a PR. If each refresh produces 800 noise lines (key reordering, escape changes, line-ending churn) and 5 signal lines (an actual upstream change), reviewers stop reading carefully. The five details in Rule 4 are not five small details; they are one decision (the artifact is content-addressable modulo `captured_at`) implemented in five places.

**Failing loudly on schema mismatch is what makes the artifact a contract.** The cost of a clear stderr line and exit 2 is zero. The cost of a silent forward-coerce that mis-resolves one ID out of a thousand is a week of debugging the wrong layer.

## When to Apply

- Adding a serializable artifact form to any tool whose authoritative behavior is a runtime index built from upstream data files
- Reviewing an existing dump/export feature whose output is a flat map and whose downstream consumers cannot answer "what version", "from where", "is this fresh"
- Designing the round-trip story between an on-demand resolver and a baked artifact when both will coexist long-term
- Designing the schema for any file that will be committed to a repo, refreshed periodically, and reviewed in PRs — diff-cleanliness rules apply to every such file, regardless of domain

## Examples

### Round-trip equivalence (the byte-identical rule)

The verifier asserts that resolving every ID through `--lookup-table` returns the same string as `--from` against the source chunks. Running the resolution in-process (not via subprocess) keeps the test scalable to the 1003-ID real artifact:

```python
files, anchors, id_to_pair, _ = build_index_for_source(chunks_dir)
lookup = load_lookup_table(artifact_path)

for landmark_id, _pair in id_to_pair.items():
    via_chunks = resolve_id(landmark_id, files, anchors, id_to_pair)
    via_lookup = resolve_id_from_lookup(landmark_id, lookup)
    assert via_chunks == via_lookup, f"{landmark_id}: {via_chunks!r} != {via_lookup!r}"
```

The 1003-iteration loop runs in milliseconds because both paths are in-process. A subprocess-per-ID variant of the same test added 6 minutes to CI on the same fixture — a real performance footgun for any future verifier that scales the fixture up.

### Determinism check (the byte-deterministic rule)

```python
out_a = tmp / 'a.json'
out_b = tmp / 'b.json'

run_dump(source=chunks_dir, out=out_a)
run_dump(source=chunks_dir, out=out_b)

# Strip the one legitimately non-deterministic field, compare everything else
def _strip_ts(text):
    return re.sub(r'"captured_at": "[^"]+"', '"captured_at": "<stripped>"', text)

assert _strip_ts(out_a.read_text(encoding='utf-8')) == _strip_ts(out_b.read_text(encoding='utf-8'))
```

The test deliberately compares *text*, not parsed JSON. Parsing-then-comparing would mask whitespace, key order, or line-ending drift — the failures the test exists to catch.

### Unicode preservation (the raw-UTF-8 rule)

```python
artifact_bytes = (tmp / 'help.json').read_bytes()
assert b'\xe6\xa6\x82\xe8\xa6\x81' in artifact_bytes, "Unicode ID was escaped or lost"
assert b'\\u6982' not in artifact_bytes, "Unicode escape leaked into the artifact"
```

The first assertion proves the literal UTF-8 bytes are present; the second proves the JSON serializer did not fall back to `\u`-escaping. Both checks are cheap, both fail informatively, and together they pin down the property the rule is trying to guarantee.

### Provenance block on remote dump (the source-stamp rule)

```python
artifact = json.loads((tmp / 'help.json').read_text(encoding='utf-8'))
source = artifact['source']
assert source['type'] == 'remote-base-url'
assert source['base_url'] == 'https://example.com/help/'
assert source['chunks_found'] == 3
assert re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$', source['captured_at'])
```

The `source.type` switch tells the verifier (and human reviewers) which branch of the closed enum applies, so the test can assert on `base_url` vs `path` without coupling to which one was set.

### Version-gate failure (the hard-gate rule)

```python
artifact = {'format_version': 99, 'source': {...}, 'landmarks': {}}
artifact_path.write_text(json.dumps(artifact))

result = subprocess.run(
    [sys.executable, resolver_script, 'resolve', 'abc', '--lookup-table', str(artifact_path)],
    capture_output=True, text=True,
)
assert result.returncode == 2
assert 'unsupported format_version 99' in result.stderr
assert 'this build understands 1' in result.stderr
```

The substring checks pin the exact message format so a future refactor that silently shortens the error doesn't slip past CI.

## Related

- `docs/solutions/design-patterns/reverb-landmark-resolver-static-mirror-2026-05-20.md` — issue #54's parent pattern. Establishes opaque-ID handling, runtime-mirror merge semantics, and the narrow CLI surface this issue extends.
- `docs/solutions/design-patterns/static-mirror-remote-fetch-cache-2026-05-20.md` — issue #76's sibling pattern. Adds the HTTP-fetch/cache half; the artifact pattern here is the third piece of the static-mirror story (parser/index → HTTP/cache → serializable artifact).
- `plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py` — the resolver, now with `cmd_dump` emitting the structured artifact and `--lookup-table` consuming it. The `_format_path` helper, `_build_dump_artifact`, `load_lookup_table`, and the `SOURCE_TYPE_*` constants are the load-bearing pieces.
- `plugins/webworks-claude-skills/skills/reverb2/workflows/landmark-resolution.md` — the workflow doc. Step 1c covers the lookup-table source, Step 6 covers the bulk-rewrite recipe, the inline "Dump Artifact Schema" section is the authoritative schema reference.
- `plugins/webworks-claude-skills/skills/reverb2/tests/fixtures/epublisher-designer-2026.1-help-lookup.json` — the first real artifact this skill ships. 1003 landmarks across 7 chunks; doubles as the round-trip verifier's input and as living documentation of the schema.
- `plugins/webworks-claude-skills/skills/reverb2/tests/verify-landmark-resolver.py` — verifier. The eleven scenarios added in this issue cover determinism, structured shape, sorted-keys output, Unicode preservation, round-trip on chunk + Unicode fixtures, `format_version` validation (including the boundary case), the full source-flag mutual-exclusion matrix, `dump --lookup-table` rejection, the real-artifact smoke test, and the remote-mode `source` block.
- `docs/solutions/documentation-gaps/epublisher-format-traits-xml-schema-2026-05-09.md` — documents the `landmark-id-format: source-id` opt-in. The Unicode-preservation rule (Rule 5) exists because of this option.
- GitHub issue #77 — feature request, including the runtime-shape vs skill-friendly-shape design discussion that the brainstorm resolved in favor of the skill-friendly shape.
