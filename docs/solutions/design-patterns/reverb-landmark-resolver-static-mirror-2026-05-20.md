---
title: Ship a static mirror of a JS-runtime ID resolver by parsing the underlying data files
date: 2026-05-20
last_updated: 2026-05-20
category: design-patterns
module: reverb2
problem_type: design_pattern
component: tooling
severity: medium
applies_when:
  - A help system or SPA uses a JavaScript runtime to resolve stable opaque-ID URLs to physical file paths
  - AI consumers or other JS-less clients must read that content without executing the runtime
  - The opaque IDs may change format across releases (hex hash, pass-through source ID, etc.) and the resolver must be forward-compatible
  - A skill needs to convert stable links to direct file links for embedding in documentation
related_components:
  - reverb2
  - epublisher
  - tooling
tags:
  - reverb2
  - landmark-resolver
  - opaque-id
  - js-runtime-bypass
  - static-mirror
  - ai-consumer
  - forward-compatibility
---

# Ship a static mirror of a JS-runtime ID resolver by parsing the underlying data files

## Context

Reverb 2.0 help output publishes stable topic links of the form `<prefix>#/<id>`, for example `https://static.webworks.com/docs/epublisher/latest/help/#/e5d3d31c42d8d1d4`. Resolving them to a real HTML file requires executing the Reverb JavaScript runtime: the runtime fetches every `_lx.js` chunk in the output, merges them through `Landmarks.Advance()`, and looks the ID up in the merged index.

AI consumers fetching documentation without a JavaScript runtime cannot follow stable links. The workaround until now was to hand-maintain both a stable URL and a direct file URL in skill references (`product-foundations.md`), with a comment that the direct URL "may change if docs restructure" — fragile, drift-prone, and silent when it breaks.

Issue #54 adds a Python resolver to the `reverb2` skill (`scripts/resolve-landmarks.py`) that does what the runtime does, without the runtime. The resolver, its fixtures, and its workflow doc together encode a pattern that is reusable any time a static mirror of a JavaScript ID-resolution runtime is needed.

## Guidance

When you need a JS-less counterpart to a JS-runtime resolver, ship it as a thin tool that:

1. **Treats IDs as opaque strings.** Do not regex, length-check, or hex-validate. Match by straight string equality against whatever the runtime stores. This is what makes the tool survive ID-format changes (Reverb 2026.1 introduced 8-character hex hashes and pass-through source IDs alongside the original 16-character hex; the resolver needed no code change to handle them).

2. **Mirrors the runtime's merge semantics exactly.** Read the same data files the runtime reads. Build the same global index the runtime builds. Apply the same last-write-wins (or first-write-wins, or whatever the runtime does) for duplicate IDs. The user-visible defaults — in Reverb's case, `file#anchor` from paragraph-level rows winning over page-level rows — fall out of getting the order right, not from special-casing.

3. **Parses the data files with the lightest tool that works.** Reverb's `_lx.js` chunks are `var landmarks = {...JSON-shaped...};Landmarks.Advance(landmarks);`. A targeted regex extracts the object literal, then `json.loads` parses it. No JavaScript interpreter, no third-party parser. Document the JSON-shape assumption so the failure mode is obvious if a future release breaks it.

4. **Exposes a narrow CLI surface, with primitives that compose.** `resolve <id>`, `rewrite <url>`, `dump` is enough. Bulk workflows compose `dump` output with anything else. A wider surface (`resolve --all-bindings`, server mode, remote fetch) is deferred until there is a real second consumer.

5. **Wires into the skill's existing intake.** Add an intake option, a routing row, and a capabilities row. Write a workflow doc. Do not restructure the skill — slot the new capability into the existing scaffolding.

## Why This Matters

The fragile alternative is hand-maintained URL pairs in skill references. Each one is a small commitment to remember to update the direct-file half of the pair whenever published help is regenerated — a commitment that will be missed, and that will silently break the JS-less consumer when it is. The static mirror eliminates that commitment.

The opaque-ID rule is the load-bearing decision. A resolver that validates IDs as 16-character hex will break the moment Reverb emits a project with `landmark-id-format` set to `source-id` (a 2026.1 opt-in already visible in real format-traits XML). A resolver that only does string equality keeps working, with no release coordination, across every ID format Reverb has shipped or will ship.

The runtime-mirror rule is the second load-bearing decision. The runtime's `dset(D.ids, id, [fi, ai])` is intentionally a silent overwrite, and the order of rows in `_lx.js` (page-level row first, then paragraph-level row) is what makes that overwrite produce the user-friendly `file#anchor` default. A static mirror that picks a different policy (e.g., "return the first row" or "return both") will return *different* paths for the same input. Matching the runtime contract is a correctness property, not a stylistic choice.

## When to Apply

- Adding a JS-less resolver for any opaque-ID URL scheme whose authoritative resolution lives in a JavaScript runtime
- Documenting any product whose published links go through a runtime resolver and need to be embedded in skill references that may be consumed by JS-less agents
- Shipping any tool that has a "runtime equivalent" — the rule is to mirror the runtime's contract exactly, including its surprises

## Examples

### Forward-compatible ID lookup (the opaque-ID rule)

```python
# resolve-landmarks.py — straight string equality, no validation
id_to_pair[landmark_id] = (file_map[local_fi], anchor_map[local_ai])
# ...
pair = id_to_pair.get(landmark_id)
```

The third element of each `e[i]` tuple in `_lx.js` is whatever the project emitted. Reverb 2026.1's three formats — 16-character hex hash, 8-character hex hash, pass-through source ID — round-trip through this code with no branching.

### Runtime-mirroring merge (the runtime-mirror rule)

```python
# build_index: same scan order, same overwrite semantics as Landmarks.Advance()
for chunk_path in chunk_paths:
    chunk = parse_chunk(chunk_path)
    file_map = [intern(f, global_files, file_index) for f in chunk['f']]
    anchor_map = [intern(a, global_anchors, anchor_index) for a in chunk['a']]
    for row in chunk['e']:
        # ... defensive `continue` checks mirroring the runtime's guards ...
        id_to_pair[landmark_id] = (file_map[local_fi], anchor_map[local_ai])
        # ^ last-write-wins, just like dset(D.ids, id, [fi, ai]) in the runtime
```

### Lightest parser that works (the parser-shape rule)

```python
_LANDMARKS_RE = re.compile(
    r'var\s+landmarks\s*=\s*(\{.*?\})\s*;\s*Landmarks\.Advance\s*\(',
    re.DOTALL,
)
# match.group(1) is JSON-shaped; json.loads handles it directly.
```

The assumption — chunk files keep using JSON-compatible literals — is documented in the plan and the script docstring so that, if Reverb ever switches to ES-only syntax, the failure surface is obvious.

### Narrow CLI surface (the composition rule)

```bash
# Three primitives:
python scripts/resolve-landmarks.py resolve <id>      --from <chunk-or-dir>
python scripts/resolve-landmarks.py rewrite <url>     --from <chunk-or-dir>
python scripts/resolve-landmarks.py dump              --from <chunk-or-dir>

# Bulk rewriting composes from dump:
python scripts/resolve-landmarks.py dump --from ./help-mirror/ > landmarks.json
# ...then look IDs up in landmarks.json from your own script or editor.
```

### Skill-wiring pattern (the slot-in rule)

The SKILL.md change in this PR is three lines plus a row: intake option 5, routing row for `5, "resolve", "landmark", "hash"`, and a Capabilities row for `Landmark Resolution`. The new `workflows/landmark-resolution.md` mirrors the shape of the existing `csh-analysis.md` workflow doc. No restructuring; the new capability slots into the existing scaffolding the same way a new CSH/SCSS/report capability would.

## Related

- `docs/solutions/design-patterns/static-mirror-remote-fetch-cache-2026-05-20.md` — issue #76's v2 follow-up extends this pattern over HTTP. It adds the HTTP-fetch/cache/runtime-fidelity half (generation-hash cache key, landing-page double-duty discovery, URL-fragment `decodeURIComponent` parity) without invalidating any rule in this doc — the parser/index half here is carried into v2 unchanged.
- `plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py` — the resolver (now extended in v2 with `--remote-base-url` and the cache state machine)
- `plugins/webworks-claude-skills/skills/reverb2/workflows/landmark-resolution.md` — workflow doc (rewritten in v2 to cover both local and remote sources)
- `plugins/webworks-claude-skills/skills/reverb2/tests/verify-landmark-resolver.py` — verification scenarios (28 in v1 → 80 in v2) covering opaque IDs, multi-chunk merge, last-write-wins, and the full CLI contract
- `plugins/webworks-claude-skills/skills/reverb2/tests/fixtures/` — handcrafted `_lx.js` fixtures (single-chunk and multi-chunk)
- `docs/solutions/documentation-gaps/epublisher-format-traits-xml-schema-2026-05-09.md` — documents the `landmark-id-format` configuration option (the opt-in that introduced the non-hex ID variants the resolver must tolerate)
- `docs/solutions/architecture-patterns/format-spec-vs-integration-skill-separation-2026-05-09.md` — sibling skill-architecture guidance
- GitHub issue #54 — v1 feature request and design discussion
- GitHub issue #76 — v2 remote-fetch feature request
