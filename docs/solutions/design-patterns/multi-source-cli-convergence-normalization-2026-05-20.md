---
title: Normalize at the convergence point when a CLI supports multiple input sources
date: 2026-05-20
category: design-patterns
module: reverb2
problem_type: design_pattern
component: tooling
severity: medium
applies_when:
  - A CLI gains a second input source (e.g., parse-from-raw vs load-from-artifact) that produces the same logical output as an existing source
  - Two source paths converge on a shared in-memory data structure before reaching the resolution/rewrite/emit code
  - A round-trip contract holds (dump → consume must equal direct-consume) and is verified by a parity test
  - Output strings need normalization (path separators, URL encoding, case folding, whitespace collapsing, Unicode form) that downstream consumers must not have to redo
related_components:
  - tooling
  - reverb2
tags:
  - convergence-point-normalization
  - multi-source-cli
  - parity-tests
  - lookup-tables
  - artifact-contracts
  - importer-exporter
---

# Normalize at the convergence point when a CLI supports multiple input sources

## Context

The reverb2 landmark resolver started with one input shape: `--from <dir>`, which parses `_lx.js` chunks and builds an in-memory index. Issue #77 added a second shape: `--lookup-table <file>`, which loads a previously dumped JSON artifact. Both shapes converge on the same internal triple — `(files, anchors, id_to_pair)` — and feed the same `resolve_id` and `rewrite` code paths.

The shipped contract included path normalization: backslashes converted to forward slashes, URL-encoded characters decoded. The plan placed that normalization in `cmd_dump` at emit time. With the implementation in that shape, the AE3 parity test failed: `resolve --from <dir>` returned raw `_lx.js` paths (e.g., `Group\Topics%20overview.html`) while `resolve --lookup-table <file>` returned normalized paths (`Group/Topics overview.html`). The two source paths produced different answers for the same logical query.

The fix was to move `normalize_landmark_path` into `build_index` — the function that produces the triple from `_lx.js` chunks. `load_lookup_table` already returned the normalized form (because the artifact it loaded was emitted post-normalization). Once `build_index` normalized at index time, both source paths emitted the same triple, and the parity test passed.

## Guidance

**When a CLI's two source paths converge on a single in-memory data structure, normalize at the convergence point — not at one of the emit boundaries.**

Concretely: identify the function (or pair of functions, one per source) whose output is the shared internal representation. Apply every normalization step inside those functions, before the data is handed off to resolution, rewrite, or emit code. The boundary between "raw input" and "internal canonical form" is the convergence point. Emit functions should serialize whatever they receive — they should not also be the place where raw-form differences get smoothed out, because then the non-emit code paths see the un-smoothed form.

The rule generalizes beyond paths. Anything the user expects to be consistent across sources — case folding, whitespace collapsing, Unicode normalization (NFC/NFD), trailing-slash policy, ID canonicalization — belongs at the same boundary.

## Why This Matters

A normalization placed at the emit boundary creates a silent split-brain: downstream callers that bypass the emit path (the resolver itself, when it reads `--from`) see the raw form, while consumers of the emitted artifact see the canonical form. The two halves of the round-trip contract (`dump → consume` should equal `direct-consume`) diverge. Worse, the divergence is silent under normal use — a user invoking `resolve --from` and `resolve --lookup-table` in different terminals will get different answers and have no idea why.

Moving normalization into the convergence function (here, `build_index`) makes source-independence a structural property rather than a discipline the test suite has to enforce per-emit-path. It also makes future emit paths (a future `dump --shape runtime`, a future `dump --format csv`) automatically correct — they receive an already-canonical triple, no per-emit normalization required.

The parity test is the canary that catches the wrong placement. AE3 in this work iterates every id in the dump and compares `resolve --from` and `resolve --lookup-table` outputs char-for-char. That test only passes when both sources produce identical triples; it catches the silent divergence the moment normalization is placed too late.

## When to Apply

- Adding a second input shape to an existing CLI (importer/exporter, dynamic vs cached, raw vs preprocessed). Identify the convergence point before deciding where new transformations live.
- Designing a round-trip contract: `tool dump | tool consume` must equal `tool direct-consume`. Place every normalization step on the producer side of the contract, inside the function that builds the canonical form.
- Reviewing a multi-source CLI where two paths *should* return identical output for the same query. Parity tests against every key (not just one sampled key) catch source-dependent drift.

## Examples

### The bug shape (normalization at the emit boundary)

```python
# build_index: returns raw _lx.js path strings (backslashes, URL-encoded)
def build_index(chunk_paths):
    ...
    for f in chunk['f']:
        file_map.append(_intern(f, global_files, file_index))  # raw form
    ...

# cmd_dump: normalizes when emitting JSON
def cmd_dump(args):
    files, anchors, id_to_pair = build_index(...)
    artifact = {
        'landmarks': {
            id: {'file': normalize_path(files[fi]), 'anchor': anchors[ai]}
            for id, (fi, ai) in id_to_pair.items()
        },
        ...
    }

# load_lookup_table: returns normalized form (read from already-normalized artifact)
# resolve --from <dir>: returns raw paths (build_index output, no normalization)
# resolve --lookup-table <file>: returns normalized paths (artifact form)
# -> parity test fails. Split brain.
```

### The fix (normalization at the convergence point)

```python
# build_index: normalizes at index time. Output is already canonical.
def build_index(chunk_paths):
    ...
    file_map = [
        _intern(normalize_landmark_path(f), global_files, file_index)
        for f in chunk['f']
    ]
    ...

# cmd_dump: emits whatever build_index produced. No per-emit normalization.
# load_lookup_table: reads artifact (already canonical). Returns same triple shape.
# Both source paths converge on a canonical triple.
# resolve --from <dir> and resolve --lookup-table <file> now return identical paths.
```

### The parity test (the canary)

```python
# tests/verify-landmark-resolver.py — test_lookup_table_parity_with_from
def test_lookup_table_parity_with_from(fixtures_dir, tmp):
    artifact = tmp / "snapshot.json"
    run_cli(["dump", "--from", fixtures_dir, "--out", str(artifact)])
    dumped = json.loads(artifact.read_text(encoding="utf-8"))

    for landmark_id in dumped["landmarks"]:
        from_result = run_cli(["resolve", landmark_id, "--from", fixtures_dir]).stdout
        lt_result   = run_cli(["resolve", landmark_id, "--lookup-table", str(artifact)]).stdout
        check(
            f"parity for id {landmark_id}",
            from_result == lt_result,
            f"--from: {from_result!r}; --lookup-table: {lt_result!r}",
        )
```

Iterate every id, not a sampled one. A single-key parity test would have missed the path-normalization divergence — the keys are character-clean ASCII, and only the values differed.

## Related

- `plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py` — `build_index` (convergence point) and `load_lookup_table` (sibling source path)
- `plugins/webworks-claude-skills/skills/reverb2/tests/verify-landmark-resolver.py` — `test_lookup_table_parity_with_from` (the canary test)
- `plugins/webworks-claude-skills/skills/reverb2/references/landmark-lookup-table.md` — downstream-facing schema contract that the canonical form feeds into
- `docs/solutions/design-patterns/reverb-landmark-resolver-static-mirror-2026-05-20.md` — sibling pattern (mirroring a JS runtime's contract); this doc extends the static-mirror with the rule for *where* canonicalization lives when a second source is added
- GitHub issue #77 — feature: schema'd dump and `--lookup-table` consumer path
