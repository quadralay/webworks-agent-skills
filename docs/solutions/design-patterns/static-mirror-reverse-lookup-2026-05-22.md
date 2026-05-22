---
title: Derive the reverse-lookup index from the persisted forward map when adding an inverse-direction query to a static-mirror tool
date: 2026-05-22
category: design-patterns
module: reverb2
problem_type: design_pattern
component: tooling
severity: medium
applies_when:
  - A static-mirror tool already answers a forward `id -> value` lookup and is being extended with an inverse `value -> id(s)` lookup
  - The tool exposes more than one source mode (local chunks, remote HTTP, pre-built artifact) and the inverse query must agree byte-for-byte across all of them
  - The underlying data is a sequence of write events with last-write-wins semantics, so naive accumulators can desync from the merged forward map
  - The forward map's persisted shape is the existing dump-artifact contract and you do not want to bump its schema for the new direction
  - Multiple bindings can target the same value (one page-level binding plus per-anchor bindings) and the CLI must pick a deterministic, documented output order
related_components:
  - reverb2
  - epublisher
  - tooling
tags:
  - reverb2
  - landmark-resolver
  - static-mirror
  - reverse-lookup
  - last-write-wins
  - round-trip
  - cli-design
---

# Derive the reverse-lookup index from the persisted forward map when adding an inverse-direction query to a static-mirror tool

## Context

Issue #54 shipped the Reverb landmark resolver: a static-mirror tool that answers the forward question `id -> file[#anchor]` by parsing `_lx.js` chunks the way the in-browser runtime does. Issue #76 extended it to remote HTTP sources. Issue #77 added a serializable dump artifact with a `--lookup-table` consumer path, so the resolver now had three source modes (local `--from`, remote `--remote-base-url`, pre-built `--lookup-table`) all feeding one forward index.

Issue #78 added the inverse direction: `reverse <path> -> [id, ...]`. The brainstorm captured three workflows that need this direction — stable-URL minting, link audits, and anchor citations — and noted that the underlying chunk data already binds `(file_index, anchor_index) -> id` in the same `e` rows the forward map walks. The runtime persists this as `pairToId` keyed by `"fileIndex|anchorIndex"`; the static mirror could mirror that.

The interesting design work was not "add an inverse map" — `dict.items()` does that. It was answering four questions a naive implementation gets wrong:

1. **Which existing structure is authoritative when last-write-wins rebinds an ID across chunks?** The merge loop builds two maps at once; the wrong choice silently desyncs them.
2. **Can `reverse` against `--from`, `--remote-base-url`, and `--lookup-table` produce byte-identical output?** The three source modes go through different code paths; the reverse direction has to converge.
3. **What is the default output when a path has multiple bindings — runtime parity (only the page-level binding, matching `GetIdByPath`), or "all bindings"?** Both are defensible; one is strictly more general.
4. **Where do you draw the line on path normalization?** The runtime does straight string equality after `splitPath`. Anything more is the static mirror inventing a contract the runtime does not have.

The autofix commit that landed in this issue (`abe0bc7`) is the cautionary tale for question 1: the initial implementation answered it wrong, the chunk-side and lookup-table-side reverse maps disagreed for any "orphaned" ID, and the acceptance-criterion forward-then-reverse round-trip failed silently against multi-chunk inputs. The rules below answer the four questions in the order they bite.

## Guidance

When extending a static-mirror tool with an inverse-direction lookup, treat the *inverse projection* as a function of the persisted forward map — not as a parallel accumulator that the merge loop maintains.

### Rule 1 — Derive the inverse map from the same forward map that the dump artifact persists

The forward map is the authoritative state. The reverse map is one projection of it. Build the projection at the end of the merge — never alongside it.

```python
# resolve-landmarks.py — inside _merge_chunks, after the merge loop completes
path_to_bindings: dict[int, list[tuple[int, str]]] = {}
for landmark_id, (fi, ai) in id_to_pair.items():
    path_to_bindings.setdefault(fi, []).append((ai, landmark_id))
for fi in path_to_bindings:
    path_to_bindings[fi].sort(key=lambda pair: (global_anchors[pair[0]], pair[1]))
```

The wrong-shape version of the same code is the one this issue's autofix removed. It maintained a `pair_to_id: dict[(int, int), str]` accumulator inside the merge loop, then inverted *that* into `path_to_bindings`:

```python
# wrong — maintains a parallel reverse accumulator inside the merge
pair_to_id: dict[tuple[int, int], str] = {}
# ...inside the loop...
previous_pair = id_to_pair.get(landmark_id)
if previous_pair is not None and previous_pair != pair and pair_to_id.get(previous_pair) == landmark_id:
    del pair_to_id[previous_pair]
id_to_pair[landmark_id] = pair
pair_to_id[pair] = landmark_id
# ...after the loop...
for (fi, ai), landmark_id in pair_to_id.items():
    path_to_bindings.setdefault(fi, []).append((ai, landmark_id))
```

That version desyncs the moment an ID `X` rebinds from `(fi_1, ai_1)` to `(fi_2, ai_2)` in a later chunk *while a different ID `Y` is still bound to `(fi_1, ai_1)`*. The forward map keeps both: `id_to_pair[X] = (fi_2, ai_2)` and `id_to_pair[Y] = (fi_1, ai_1)`. The naive `pair_to_id` overwrites the `(fi_1, ai_1)` row with `X` and then deletes it, dropping `Y` from the reverse map entirely.

The `--lookup-table` source has no merge loop at all — it inverts the persisted forward map at load time, identically to the rule's prescription. Whichever path the static mirror's tool exposes, the inversion-from-forward path is the contract; the other path is the bug.

### Rule 2 — Round-trip equivalence is the primary correctness test, and it must exercise the merge

For every ID `X` in the merged index, the test resolves `X` to path `P`, splits `P` on the first `#` to recover the file portion `F`, then asserts that `X` is in `reverse(F)`. This is the *only* test that catches the Rule 1 desync without naming it.

```python
def test_cli_reverse_forward_round_trip():
    for fixture_label, source in [("single", SINGLE_FIXTURE), ("multi", MULTI_DIR), ("unicode", UNICODE_FIXTURE)]:
        files, anchors, id_to_pair, _ = build_index_for_source(source)
        for landmark_id in id_to_pair:
            forward = run_cli(['resolve', landmark_id, '--from', str(source)])
            assert forward.returncode == 0
            path = forward.stdout.strip()
            file_part = path.split('#', 1)[0]
            reverse_out = run_cli(['reverse', file_part, '--from', str(source)])
            assert reverse_out.returncode == 0, f"{fixture_label}/{landmark_id}: reverse failed for {file_part}"
            ids_in_reverse = reverse_out.stdout.strip().splitlines()
            assert landmark_id in ids_in_reverse, (
                f"{fixture_label}/{landmark_id} forward-resolved to {path} but reverse({file_part}) "
                f"returned {ids_in_reverse}"
            )
```

The first version of this test in the issue only exercised single-chunk fixtures. Single-chunk fixtures cannot trigger last-write-wins — there is no "later chunk" to rebind anything. The autofix made the test multi-chunk-aware by adding the `MULTI_DIR` pass, which was what caught the desync. The rule generalizes: a round-trip test that only walks the smallest fixtures will silently miss every bug that requires multi-input merging.

### Rule 3 — Reverse against `--lookup-table`, `--from`, and `--remote-base-url` must produce byte-identical output

Three source modes, one reverse direction. The verifier asserts the chunk source and the lookup-table source return the same lines for the same input — across single-binding, multi-binding, `--first`, `--anchor`, and `--json` cases.

```python
def test_cli_reverse_lookup_parity(tmp):
    artifact = tmp / 'dump.json'
    run_cli(['dump', '--from', str(MULTI_DIR), '--out', str(artifact)])
    cases = [
        ['shared/index.html'],                        # default: all bindings
        ['shared/index.html', '--first'],             # filtered: page-level only
        ['shared/index.html', '--json'],              # structured output
        ['groupA/page.html', '--anchor', 'wwp_a1'],   # anchor filter
    ]
    for args in cases:
        via_chunks = run_cli(['reverse', *args, '--from', str(MULTI_DIR)])
        via_lookup = run_cli(['reverse', *args, '--lookup-table', str(artifact)])
        assert via_chunks.stdout == via_lookup.stdout, f"reverse mismatch: {args}"
        assert via_chunks.returncode == via_lookup.returncode
```

The case selection matters. The autofix added `shared/index.html` specifically — a path that exists in chunk A as `(chunk_a_only, "")` and in chunk B as `(chunk_b_only, "")`. Chunk B overwrites the `(fi, ai)` slot; the persisted forward map keeps both IDs (each with their own resolved `(fi, ai)`); the reverse map for `shared/index.html` must include both. The pre-autofix code returned only `chunk_b_only` from the chunk source and both IDs from the lookup-table source. A parity test that only queried single-binding paths would have passed.

The cheaper version of this test — checking that `_invert_lookup_for_reverse(load_dump_artifact(...))` equals the chunk-side `path_to_bindings` — is what the verifier actually does in-process for the bulk comparison, then uses the subprocess form above for a small representative case set. The asymmetry is intentional: byte-identical CLI output is the contract surface; in-process equality is the load-bearing implementation detail that produces it.

### Rule 4 — Default to "all bindings"; `--first` opts into runtime parity

The runtime's `GetIdByPath` returns only the page-level (empty-anchor) binding. That is a side effect of `localStorage`'s persisted shape, not an intentional API design. Mirroring it as the CLI default would silently drop information callers are asking for in the link-audit and anchor-citation workflows.

| Caller's question | Right output |
|-------------------|--------------|
| "What stable URL minted from this page?" | `--first` (page-level only) |
| "Every ID that targets this page" | bare (all bindings) |
| "The ID for this specific anchor" | `--anchor <id>` |
| Runtime-compatible "id-by-path" | `--first` |

Sort multi-binding output by `(anchor_string, landmark_id)`. The empty-anchor binding sorts first because the empty string is the smallest sort key — no special-casing needed. Sorting by *anchor string* (not anchor index) means the order is independent of the intern order in any particular chunk, which makes the output portable across local, remote, and lookup-table sources without coordination.

`--first` and `--anchor` are mutually exclusive (argparse-level mutex group). The combination is degenerate either way you interpret it: "the page-level row, but only if its anchor matches" simplifies to checking against `""`; "the binding at this anchor, but only when it's first" is true for exactly one anchor per file. Argparse rejection at exit `2` is the simplest signal.

`--anchor ""` is rejected by the handler (not by argparse), with a stderr message that points the caller at `--first`. Exit `1` (CLI usage error), not exit `2` (argparse parse error), because the empty string is a value-level mistake — argparse accepted the parse, the semantic check rejects the value. The autofix moved this from exit `2` to exit `1` to align with the module-level contract that exit `1` covers all resolution failures including value-level usage errors.

### Rule 5 — Percent-decode input once; do nothing else

The input path can arrive in either raw form (the form chunks store) or percent-encoded form (the form browsers display). `urllib.parse.unquote(args.path, errors='strict')` is the single normalization step, mirroring what `cmd_rewrite` does on the ID side of stable URLs. Malformed percent-encoding exits `1` with a stderr message that names the offending input.

Beyond percent-decoding, do *nothing*. No separator canonicalization (`/` vs `\`). No leading `./` stripping. No `..` resolution. No fragment splitting on `#`. The runtime's `GetIdByPath` is straight equality against the keys in the chunk's `f` array; any normalization beyond what the runtime does turns the static mirror into a *similar but different* contract.

A caller who passes `Group/page.html#wwp100` as the path will get "path not in index" and the workflow doc explains why: use `--anchor wwp100` and the bare path instead. The error is informative, the contract is intact, and the static mirror does not silently accept inputs the runtime would reject.

### Rule 6 — Inverse projection composes with the existing artifact schema; do not bump `format_version`

The v1 dump artifact persists `{id -> {file, anchor}}`. The inverse projection is one walk of that dict. Bumping `format_version` to `2` to bundle a precomputed reverse map would:

- Double the artifact size (the forward map and the inverted map have similar entropy, but gzip would deduplicate less than naive counting suggests — the strings on both sides are the same)
- Break every existing committed artifact that consumers `--lookup-table` against today
- Pay for an optimization no measured workload has demanded (the inversion is one pass over a dict already in memory; the cost is bounded by `len(landmarks)`)

`_invert_lookup_for_reverse(lookup)` is a single 8-line helper. It runs on first `reverse` query against a `--lookup-table` source. The result is local to the `cmd_reverse` call; no module-level cache, no disk persistence, no schema change.

```python
def _invert_lookup_for_reverse(lookup: dict) -> dict[str, list[tuple[str, str]]]:
    result: dict[str, list[tuple[str, str]]] = {}
    for landmark_id, entry in lookup['landmarks'].items():
        if not isinstance(entry, dict):
            continue
        file_path = entry.get('file', '')
        anchor = entry.get('anchor', '')
        result.setdefault(file_path, []).append((anchor, landmark_id))
    for file_path in result:
        result[file_path].sort()
    return result
```

The `result[file_path].sort()` call sorts each value list — the `(anchor, id)` tuples sort lexicographically, so the empty-anchor entry sorts first and ties on `anchor` resolve deterministically. Matches the chunk-side `path_to_bindings` sort key by construction (Rule 4).

## Why This Matters

**Inverse projections that maintain themselves desync.** The temptation to keep a `pair_to_id` accumulator alongside `id_to_pair` is real — the merge loop is already walking the rows, the inverse is just an `else` branch away, and the eager construction "saves a pass". The cost the saving hides is that two structures now have to stay consistent across every edge case the merge loop touches, including last-write-wins rebinds where one side overwrites and the other side needs to keep the orphaned entry. One source of truth, projected once at the end, eliminates the consistency burden.

**The persisted forward map is the contract; everything else is a projection.** The dump artifact persists `{id -> {file, anchor}}`. Two consumers — the chunk-loading path and the artifact-loading path — both materialize the same forward map. The reverse direction must be a function of that map alone. If chunk-side reverse lookup and lookup-table-side reverse lookup ever disagree, the bug is in whichever side built the reverse map from anything *other than* the forward map. This is the same principle as Rule 3 of the dump-artifact doc (`_format_path` is shared): one source of truth, exercised by all paths in the same test, makes drift impossible by construction.

**Round-trip equivalence catches the bug; isolated tests do not.** A test that resolves `X -> P` then checks `reverse(P).contains(X)` is the only test that exercises both directions through the same merge. Per-direction unit tests with hand-picked fixtures pass on the wrong implementation because the test author chose fixtures where the desync does not trigger. The autofix made the round-trip multi-chunk-aware; before that, single-chunk-only coverage gave a false-PASS on a real correctness bug. The general rule: a round-trip test on the smallest fixture is the same as no round-trip test.

**Defaulting to "all bindings" matches what the inverse-direction workflows ask for.** The runtime's `GetIdByPath` returning only the page-level binding is a localStorage shape artifact. The CLI defaulting to the same shape would silently truncate the link-audit and anchor-citation workflows that motivate this direction in the first place. `--first` is the cheap downgrade for callers who *want* runtime parity; the default cannot be reversed without breaking the workflows the feature was added for.

**Schema stability over micro-optimization.** The forward map walked once at load time is a load-bearing optimization for the in-memory case (no chunk re-parse) but a no-op for the on-disk case (the inversion is bounded by artifact size, which the consumer already has to parse). Spending a `format_version: 2` bump on a precomputed reverse map breaks every committed artifact in the wild for a workload no one has measured. The right move is "v1 artifact + on-load inversion"; the wrong move is "v2 artifact with both maps". Future workloads can revisit; current workloads do not pay the cost.

## When to Apply

- Adding any inverse-direction lookup to a static-mirror tool whose forward direction is already shipped through more than one source mode
- Extending an existing merge function to produce a second projection alongside the original — verify the projection is end-of-merge, not maintained-in-loop
- Reviewing any CLI extension where the new direction must produce byte-identical output across the tool's source modes
- Designing the default output shape for a new lookup primitive — check whether the runtime's persisted shape is an *artifact* of its storage layer (and thus a bad default) or an *intentional* API choice (and thus a good default)
- Considering a `format_version` bump for an additive read-side feature — first verify the feature cannot ride the existing schema with a load-time projection

## Examples

### Round-trip across the merge (the desync-catching rule)

```python
files_a, anchors_a, id_to_pair_a, _ = build_index([CHUNK_A])           # single-chunk
files_m, anchors_m, id_to_pair_m, _ = build_index([CHUNK_A, CHUNK_B])  # merged

# Single-chunk fixtures never trigger last-write-wins; the round-trip
# always passes here regardless of how `path_to_bindings` is built.
for landmark_id, (fi, ai) in id_to_pair_a.items():
    assert landmark_id in reverse_via_cli(files_a[fi], source=DIR_A)

# The merge fixture is what catches a reverse map built from a
# maintained-in-loop accumulator. Without this pass, the autofix bug
# would have shipped.
for landmark_id, (fi, ai) in id_to_pair_m.items():
    assert landmark_id in reverse_via_cli(files_m[fi], source=DIR_AB)
```

The two halves are intentionally separate. The single-chunk half catches "the projection is wrong even in the simple case"; the multi-chunk half catches "the projection is correct in the simple case but desyncs on merge". A test suite with only the first half is the failure mode the autofix corrected.

### Orphan-ID assertion (the maintained-accumulator gotcha)

```python
files, anchors, id_to_pair, path_to_bindings = build_index([CHUNK_A, CHUNK_B])
# CHUNK_A:  shared_id  -> shared/index.html
# CHUNK_B:  shared_id  -> shared/index.html  (rebind to same path, no-op)
#           chunk_b_only -> shared/index.html (different ID, same path)
# CHUNK_A:  chunk_a_only -> shared/index.html (different ID, same path)
file_idx = files.index('shared/index.html')
ids_at_path = [id for _, id in path_to_bindings[file_idx]]
assert sorted(ids_at_path) == ['chunk_a_only', 'chunk_b_only', 'shared_id']
```

The maintained-`pair_to_id` version of `_merge_chunks` returned only `['chunk_b_only']` for this assertion — `shared_id` and `chunk_a_only` both got their `(fi, ai)` slots overwritten in the `pair_to_id` accumulator, even though `id_to_pair` correctly kept all three. The end-of-merge inversion from `id_to_pair` keeps all three by construction.

### Three-source parity (the byte-identical rule)

```python
# Chunk-source reverse
chunk_out = run_cli(['reverse', 'shared/index.html', '--from', str(MULTI_DIR)])

# Dump the same source to an artifact, then reverse against the artifact
artifact = tmp / 'dump.json'
run_cli(['dump', '--from', str(MULTI_DIR), '--out', str(artifact)])
lookup_out = run_cli(['reverse', 'shared/index.html', '--lookup-table', str(artifact)])

# Both must produce the same bytes
assert chunk_out.stdout == lookup_out.stdout
assert chunk_out.returncode == lookup_out.returncode
```

Whatever the test fixture is, *include a case where last-write-wins crosses chunk boundaries*. If the chosen fixture's paths each appear in only one chunk, parity is trivially satisfied and the test misses every interesting bug.

### `--anchor ""` rejection (the value-level error rule)

```python
result = run_cli(['reverse', 'Group/page.html', '--anchor', '', '--from', str(FIXTURE)])
assert result.returncode == 1  # CLI usage error, not argparse parse error
assert 'use --first to retrieve the page-level binding' in result.stderr
```

The exit code is `1` (the module-level "resolution failure" exit) because argparse accepted the parse — the value-level rejection happens inside `cmd_reverse`. The earlier exit-`2` version aligned with argparse-rejected cases but mis-classified the error: argparse exit `2` means "the parse itself failed"; this parse succeeded and the handler rejected the value.

### Percent-decode round-trip (the do-nothing-else rule)

```python
encoded = 'Advanced%20Customizations/_xslt-extensions.04.1.html'
raw = 'Advanced Customizations/_xslt-extensions.04.1.html'

encoded_out = run_cli(['reverse', encoded, '--from', str(UNICODE_FIXTURE)])
raw_out = run_cli(['reverse', raw, '--from', str(UNICODE_FIXTURE)])
assert encoded_out.stdout == raw_out.stdout
```

The single `urllib.parse.unquote(..., errors='strict')` call makes both forms equivalent. No separator normalization is needed — both forms agree on `/`. No leading `./` stripping is needed — neither form has it. The minimum decoding step that makes the test pass is the maximum the tool should do.

## Related

- `docs/solutions/design-patterns/reverb-landmark-resolver-static-mirror-2026-05-20.md` — issue #54's parent pattern. Establishes the opaque-ID rule, the runtime-mirror merge rule, and the narrow CLI surface this issue extends with a fourth verb (`reverse`).
- `docs/solutions/design-patterns/static-mirror-remote-fetch-cache-2026-05-20.md` — issue #76's sibling pattern. The remote source mode that `reverse` composes with for free, because the merge function is shared.
- `docs/solutions/design-patterns/serializable-static-mirror-artifact-2026-05-22.md` — issue #77's sibling pattern. Defines the v1 artifact schema this issue projects through without bumping (Rule 6). The "byte-identical resolution across consumers" principle (Rule 3 of that doc) generalizes to the byte-identical-reverse principle (Rule 3 of this doc).
- `plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py` — the resolver, now with `cmd_reverse`, the `_invert_lookup_for_reverse` helper, and the end-of-merge `path_to_bindings` construction. The `_merge_chunks` function is the load-bearing one for Rule 1.
- `plugins/webworks-claude-skills/skills/reverb2/workflows/landmark-resolution.md` — the workflow doc. Step 7 covers the `reverse` subcommand with two worked examples (URL mint and link audit).
- `plugins/webworks-claude-skills/skills/reverb2/tests/verify-landmark-resolver.py` — the verifier. The forward-then-reverse round-trip scenario (multi-chunk pass added by the autofix) is the load-bearing one for Rule 2; the chunk-vs-lookup parity scenarios (`shared/index.html` cases added by the autofix) are the load-bearing ones for Rule 3.
- GitHub issue #78 — feature request, including the four open design questions the brainstorm and plan resolved before implementation.
- The autofix commit `abe0bc7` ("make reverse-lookup chunk/lookup-table sources agree") — the literal Rule 1 fix. The commit message names the maintained-`pair_to_id` desync explicitly and reads as a reference example of the failure mode this doc exists to prevent.
