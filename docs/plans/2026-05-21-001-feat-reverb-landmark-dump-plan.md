---
title: "feat: Structured Reverb landmark dump artifact and --lookup-table consumer path"
type: feat
status: completed
created: 2026-05-21
issue: 77
origin: docs/brainstorms/2026-05-21-issue-77-reverb-landmark-dump-requirements.md
depth: medium
---

# feat: Structured Reverb Landmark `dump` Artifact and `--lookup-table` Consumer Path

## Summary

Evolve the existing `dump` subcommand of `plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py` so it emits a structured, versioned, deterministic JSON lookup table with embedded source provenance — replacing the current flat `{id: "file#anchor"}` shape. Add a matching `--lookup-table <file>` source mode on `resolve` and `rewrite` that loads the artifact and serves queries in O(1) without parsing `_lx.js` chunks. Commit one real verification artifact generated from the ePublisher Designer 2026.1 help that ships with the product (the artifact doubles as round-trip test input and as a live reference for readers of the workflow doc). Extend the standalone verifier with determinism, round-trip, Unicode-preservation, and `format_version` validation scenarios. Update `workflows/landmark-resolution.md` to document the new source mode and the structured dump schema inline. Bump the plugin minor version per repo convention (new feature surface area).

## Problem Frame

Two consumer shapes for Reverb landmark resolution coexist today: dynamic resolution (the v1 resolver + the v2 remote-fetch mode added in #76) and bundled lookup (a skill that ships pre-built artifacts for a well-known Reverb mirror, then resolves against the artifact at runtime). The dynamic path is already well-served. The bundled-lookup path has three concrete gaps the current flat-shape `dump` output cannot close:

1. **No format versioning.** A consumer pinning to today's `{id: "file#anchor"}` shape silently breaks the first time the schema evolves. The artifact has no `format_version` field to gate on.
2. **No source provenance.** A committed artifact answers neither "which mirror did this come from?" nor "how many chunks contributed?" nor "when was it captured?" — the questions a reviewer or refresh tool asks first.
3. **No structured `(file, anchor)` separation.** Consumers must re-split on `#` to extract the anchor, duplicating string-handling rules the runtime already encodes (`GetPathById`).

A fourth gap is on the consumer side: even a perfect artifact requires every downstream skill to write its own JSON loader and lookup helper, because the resolver itself does not consume the dump.

Full problem framing, including the Unicode-NCName preservation requirement and the runtime-shape interop tradeoffs, is in the origin brainstorm (`docs/brainstorms/2026-05-21-issue-77-reverb-landmark-dump-requirements.md`).

## Requirements Traceability

Origin requirements R1–R13 and acceptance examples AE1–AE7 are addressed across the implementation units below:

- **R1, R2** — evolve `dump` in place, add `--out <file>`, treat the shape change as breaking → U1
- **R3** — structured JSON shape (`format_version`, `source`, sorted `landmarks`) → U1 (covers AE1)
- **R4** — byte-deterministic output across runs, excluding `captured_at` → U1, U4 (AE2)
- **R5** — raw Unicode IDs preserved in artifact, round-trip transparent → U1, U4 (AE3)
- **R6** — remote-mode dump (`source.type == "remote-base-url"`) → U1
- **R7, R8, R9** — `--lookup-table <file>` consumer path on `resolve` and `rewrite`, mutually exclusive with other sources, hard-gate on `format_version`, byte-identical resolved output → U2 (AE4, AE5)
- **R10** — commit a real ePublisher Designer 2026.1 fixture artifact → U3 (AE6 input)
- **R11** — verifier scenarios for determinism, round-trip, Unicode, format-version validation → U4 (AE6)
- **R12, R13** — workflow doc updated to cover lookup-table source mode and structured schema documented inline → U5 (AE7)
- **Plugin version bump** (project convention from `CLAUDE.md`) → U6

## Key Technical Decisions

Decisions inherited from the brainstorm (see `Key Decisions` section there for rationale): evolve `dump` in place rather than add a sibling subcommand; treat the shape change as breaking; ship a single skill-friendly shape for v1 (no `--shape runtime`); include the `source` provenance block; `format_version` is a hard gate; emit Unicode raw (`ensure_ascii=False`); preserve runtime "last-write-wins" semantics already encoded in `_merge_chunks`; do not re-normalize paths; `source.path` is the verbatim `--from` string.

Decisions resolved at planning time (closing the brainstorm's "Resolvable at planning time" open list):

- **Real-artifact fixture, not synthetic.** Verified at planning time that `C:\Program Files\WebWorks\ePublisher\2026.1\ePublisher Designer\Help\en\` exists on the build machine and contains exactly seven `*_lx.js` chunks (matching the issue body's expected `chunks_found: 7`). U3 generates and commits the real artifact under `plugins/webworks-claude-skills/skills/reverb2/tests/fixtures/epublisher-designer-2026.1-help-lookup.json`. The artifact's `source.path` is normalized to a forward-slash, repo-portable representation so the committed bytes do not embed a host-specific absolute path (see U3 Approach). The verifier's round-trip scenario (U4) uses an in-tree synthetic fixture generated on the fly from `tests/fixtures/multi-chunk-*_lx.js` so the test does not depend on the ePublisher install being present.
- **Schema documented inline in the workflow doc, not a new reference file.** Per brainstorm R13 default. Section length estimate is ~25-35 lines (JSON example + field reference table + the `format_version: 1` rule). Below the 40-line split-out threshold. The `dump` subcommand's `--help` text gets a one-line cross-reference.
- **`source.type` is closed-set for v1.** Allowed values: `"local-directory"` (from `--from`) and `"remote-base-url"` (from `--remote-base-url`). The verifier exercises both producers and asserts the field is one of these two. Future producers (e.g., a runtime-localStorage export) ride a future `format_version` bump.
- **`--out -` as explicit stdout alias is supported.** Adding it costs one branch in `cmd_dump` (`if args.out == '-' or args.out is None: write to stdout`). It buys script-style parity with common Unix conventions and makes the test scenarios slightly clearer (the round-trip determinism scenario can `dump --out -` twice without temp-file plumbing).

Additional decisions specific to the consumer-path design:

- **`--lookup-table` joins the existing mutually-exclusive source group.** It extends `_add_source_flags` so the same flag mechanism applies on `resolve` and `rewrite`. `dump` deliberately does not accept `--lookup-table` (dumping a dump would be a no-op with provenance erasure; preventing it at the CLI level keeps the surface honest).
- **Lookup-table source is in-memory `dict[str, dict]`, not a re-projection into the index tuple shape.** Adding a fourth code path in `_load_index` that returns a dict directly is cleaner than synthesizing fake `files`/`anchors` lists. `resolve_id` and `_format_remote_rewrite_url` operate on the resolved string; introduce a thin `resolve_id_from_lookup(landmark_id, lookup) -> Optional[str]` helper that mirrors `resolve_id`'s contract and is called from `cmd_resolve` and `cmd_rewrite` when `args.lookup_table` is set. Keeps the change additive — `resolve_id`'s existing call sites are untouched.
- **`captured_at` format is RFC 3339 / ISO 8601 in UTC with second precision and a trailing `Z`** (e.g. `2026-05-20T15:00:00Z`). Match the issue body example verbatim. Implementation: `datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')`. The verifier strips this exact field before byte comparison.
- **`chunks_found` is the number of chunks the source resolver actually merged**, which equals `len(discover_chunks(...))` in local mode and `len(remote_chunk_texts(...))` in remote mode. No new counting logic — both functions already return ordered lists.

## Assumptions

- No out-of-tree consumer of the flat-shape `dump` output exists. Repo-internal grep at planning time (`rg 'resolve-landmarks.*dump'` across `plugins/`, `docs/`, `scripts/`) returns only the workflow doc's recipe and the script's own `--help` text. The decision in R2 to treat the shape change as breaking depends on this assumption holding for downstream skills. If a vendored copy or external integration surfaces after merge, a follow-up issue can add a `--legacy-flat` flag without breaking the new default.
- The ePublisher Designer 2026.1 help directory layout on the build machine is representative of what shipped with the product. The seven `*_lx.js` chunks listed in the file scan (one per top-level document group) are the canonical set; no hidden chunks live in subdirectories. Verified by `glob('*_lx.js')` from the help root returning exactly 7 paths.
- Real ePublisher chunks do not contain Windows-style path separators in their `f` entries. The brainstorm flags this as an open assumption ("a counterexample would force a path-normalization step in R3"); U3 verifies it explicitly during artifact generation and raises a planning escalation if the assumption fails. (See U3 Verification.)
- `json.dumps(..., ensure_ascii=False, sort_keys=True, indent=2)` plus a trailing `"\n"` produces line endings that are stable across Windows, macOS, and Linux when Python's `print()` is bypassed by writing bytes directly. The implementation writes via `Path.write_text(content, encoding='utf-8', newline='\n')` (or the binary equivalent) to neutralize Windows CRLF translation. The verifier asserts byte equality on the file contents, not on a `print()` of them.
- The runtime's "last-write-wins" merge order is fully determined by `discover_chunks`'s `sorted(source.glob('*_lx.js'))` for local mode and by the discovery order in `remote_chunk_texts` for remote mode. Both are already stable. No new sort key is needed for determinism within a single `dump` invocation.
- The standalone verifier (`tests/verify-landmark-resolver.py`) remains the canonical test harness. No pytest infrastructure exists in the repo; new scenarios extend the existing `check(name, condition, detail)` pattern.

## Output Structure

```
plugins/webworks-claude-skills/skills/reverb2/
  scripts/
    resolve-landmarks.py                    (modified — U1, U2)
  tests/
    verify-landmark-resolver.py             (modified — U4)
    fixtures/
      epublisher-designer-2026.1-help-lookup.json   (new — U3)
  workflows/
    landmark-resolution.md                  (modified — U5)

plugins/webworks-claude-skills/.claude-plugin/
  plugin.json                               (modified — U6)

.claude-plugin/
  marketplace.json                          (modified — U6)
```

No new directories, no new sibling scripts. The deliverable is concentrated on the resolver, its verifier, its workflow doc, one new fixture file, and the manifest version fields.

## Implementation Units

### U1. Evolve `dump` to emit the structured JSON artifact

**Goal:** Replace the flat `{id: "file#anchor"}` JSON output with the structured, versioned, deterministic shape from R3, add the `--out <file>` flag (with `-` and omission both meaning stdout), and add the matching remote-mode `source` block from R6.

**Requirements:** R1, R2, R3, R4, R5, R6 (covers AE1, AE2, AE3)

**Dependencies:** none

**Files:**
- `plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py` — modify `cmd_dump` and `_add_source_flags`-adjacent argument-builder for `dump_parser` in `main()`; add a small helper `_build_dump_artifact(args, files, anchors, id_to_pair) -> dict` so the structure is testable in isolation and reusable by the verifier scenarios.

**Approach:**

- Add a new argparse argument to `dump_parser` in `main()` (right after `--table` is registered): `dump_parser.add_argument('--out', dest='out', default=None, help='Write JSON output to <file>. Use "-" or omit for stdout.')`. The `--table` flag remains untouched — it is the human-readable alternative and is unaffected by this issue.
- In `cmd_dump`, after `_load_index(args)` returns, branch on `args.table` (existing) and otherwise call a new helper `_build_dump_artifact(args, files, anchors, id_to_pair)` that returns the structured dict. Serialize via `json.dumps(artifact, ensure_ascii=False, sort_keys=True, indent=2) + '\n'`.
- `_build_dump_artifact` constructs the dict shape from R3:
  - `format_version`: integer literal `1`.
  - `source`: dict.
    - When `args.source` is set (local mode): `{"type": "local-directory", "path": args.source, "chunks_found": <count>, "captured_at": <iso utc>}`. `chunks_found` comes from `len(discover_chunks(Path(args.source)))` — call it once and cache the count locally (avoid double-discovery side effects: discovery raises on a missing directory, so the count is best derived during the `_load_index` flow; the simplest fix is to capture it inside `_build_or_die` and stash on `args` as `args._chunks_found`, or to re-discover at dump time — re-discovery is cheap and avoids cross-cutting coupling, so the implementation re-globs once for the count).
    - When `args.remote_base_url` is set (remote mode): `{"type": "remote-base-url", "base_url": args.remote_base_url, "chunks_found": <count>, "captured_at": <iso utc>}`. `chunks_found` here is the chunk count returned by `remote_chunk_texts`; capture it on a closure variable inside `_load_index`'s remote branch and stash it on `args` (e.g. `args._chunks_found = len(chunks)` before `build_index_from_texts(chunks)`). The remote branch is the cleaner place to capture because the count is already in hand.
  - `landmarks`: dict comprehension `{landmark_id: {"file": files[fi], "anchor": anchors[ai]} for landmark_id, (fi, ai) in id_to_pair.items()}`. `sort_keys=True` on `json.dumps` handles ordering for the top-level keys and for the nested `{file, anchor}` keys.
- For the `captured_at` value, add a module-level seam `_now_iso_utc = lambda: datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')` next to the existing `_now` and `_sleep` seams. The verifier monkey-patches it to a fixed value to exercise byte-identical output paths. Import `from datetime import datetime, timezone` at the top of the file.
- Writing the output: if `args.out is None` or `args.out == '-'`, `sys.stdout.write(json_text)` (already UTF-8 in modern Python on every platform the repo supports; the file's `# -*- coding -*-` is irrelevant since Python 3 uses UTF-8 source by default, but the stdout encoding on Windows defaults to the console code page — the implementation uses `sys.stdout.buffer.write(json_text.encode('utf-8'))` to bypass Windows code-page translation, then flushes). If `args.out` is a path, `Path(args.out).write_bytes(json_text.encode('utf-8'))` for the same reason (avoids Windows CRLF translation that `write_text` would apply).
- Update the `__doc__` block at the top of the file: under `Usage:`, change the `dump` line to include `[--out <file>]`; under `Other flags:`, add `--out <file>     For "dump": write structured JSON to <file> (default stdout).`. Update the `Examples:` section's `dump` examples to show `--out path/to/dump.json` once.
- Update the `main()` epilog's `dump` example to match.

**Patterns to follow:**

- The existing `cmd_dump` already separates the table and JSON output paths — preserve that separation, only change the JSON branch.
- `_merge_chunks` already implements last-write-wins by always overwriting `id_to_pair[landmark_id]` per row. No change needed; the ordering inherits from `discover_chunks`'s sort and from `_lx.js` row order.
- The existing remote-mode `write_cache_atomic` uses `json.dumps(manifest, sort_keys=True, indent=2)` — adopt the same call shape (plus `ensure_ascii=False` and a trailing newline) for consistency.

**Test scenarios:**

The verifier (U4) covers these end-to-end. For implementation-time spot-checks the developer runs by hand:

- Run `python resolve-landmarks.py dump --from tests/fixtures/ --out /tmp/dump.json` → file exists, valid JSON, has the three top-level keys, `landmarks` has expected IDs.
- Run the same twice and `diff` the files after stripping `captured_at` — should be empty diff.
- Run against `tests/fixtures/unicode-ids_lx.js` only — the file should contain raw `概要` bytes (`hexdump -C /tmp/dump.json | grep -i 'e6 a6'`).
- Run `python resolve-landmarks.py dump --remote-base-url <fake>` with the verifier's stub fetcher pattern — `source.type == "remote-base-url"`, `source.base_url == <fake>`.

**Verification:**

- `cmd_dump` covers both local and remote source modes without duplicating chunk-discovery logic (verify by reading the diff).
- `_build_dump_artifact` is small enough (under ~30 lines) to read in one screen and is testable without invoking the CLI.
- The JSON output for a single-chunk fixture is structurally what AE1 specifies (sorted top-level keys, sorted landmark IDs, nested `{file, anchor}`).
- Output bytes are LF-only on Windows (no CRLF), confirmed by inspecting the file as binary.

---

### U2. Add `--lookup-table <file>` consumer path on `resolve` and `rewrite`

**Goal:** Let consumers point `resolve` or `rewrite` at a `dump` artifact instead of `_lx.js` chunks. The flag is mutually exclusive with `--from` and `--remote-base-url`, validates `format_version == 1` (exit 2 otherwise), and serves queries in O(1) from the in-memory landmarks dict. Resolved output is byte-identical to direct-chunk resolution.

**Requirements:** R7, R8, R9 (covers AE4, AE5)

**Dependencies:** U1 (a structured artifact must exist before there is anything to consume).

**Files:**
- `plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py` — extend `_add_source_flags` with a third group member, add `load_lookup_table(path) -> dict` helper, add `resolve_id_from_lookup(landmark_id, lookup) -> Optional[str]` helper, branch `cmd_resolve` and `cmd_rewrite` on `args.lookup_table` before falling through to the existing `_load_index` path.

**Approach:**

- In `_add_source_flags`, add a third option to the mutually-exclusive group:
  ```python
  group.add_argument(
      '--lookup-table', dest='lookup_table', default=None,
      help='Path to a pre-built dump artifact (mutually exclusive with --from/--remote-base-url)',
  )
  ```
  Pass the new flag through both `resolve` and `rewrite` parsers (already wired via `_add_source_flags`). Do **not** add it to `dump_parser` — see Key Technical Decisions.
- Add `load_lookup_table(path: Path) -> dict` near the existing `parse_chunk` helper:
  - Read the file (`path.read_text(encoding='utf-8')`).
  - `json.loads`. On `json.JSONDecodeError` or `OSError`, raise `ValueError` with a message naming the file.
  - Check `isinstance(data, dict)` and presence of `format_version`. If `data.get('format_version') != 1`, raise `ValueError(f"unsupported format_version {data.get('format_version')!r}; this build understands 1")` — message wording matches AE5's exit-2 message contract.
  - Check `isinstance(data.get('landmarks'), dict)`. If not, raise `ValueError(f"{path}: 'landmarks' is missing or not an object")`.
  - Return the parsed dict.
- Add `resolve_id_from_lookup(landmark_id: str, lookup: dict) -> Optional[str]`:
  ```python
  entry = lookup['landmarks'].get(landmark_id)
  if entry is None:
      return None
  file_path = entry.get('file', '')
  anchor = entry.get('anchor', '')
  return f"{file_path}#{anchor}" if anchor else file_path
  ```
  This mirrors `resolve_id`'s formatting contract exactly so AE4's byte-identical guarantee holds.
- In `cmd_resolve`, before the existing `_load_index(args)` call:
  ```python
  if args.lookup_table:
      try:
          lookup = load_lookup_table(Path(args.lookup_table))
      except (ValueError, OSError) as e:
          error_log(str(e))
          sys.exit(2)
      path = resolve_id_from_lookup(args.id, lookup)
      # ... same not-found / JSON / plain output branches as the existing path
      return 0 | 1
  ```
  Keep the existing branch unchanged for the chunk-based path. The lookup-table branch fully short-circuits `_load_index` and chunk discovery — no `_lx.js` access at all.
- In `cmd_rewrite`, apply the same pattern but call `resolve_id_from_lookup(landmark_id, lookup)` after the URL parsing and percent-decoding logic completes. The lookup-table mode is incompatible with the URL auto-infer behavior — when both `--lookup-table` is set and an HTTP URL is passed, the auto-infer block (lines 904-910 of the current `cmd_rewrite`) is skipped because `args.lookup_table` is truthy. The output-formatting branches (`args.base_url`, remote-mode percent-quoting, prefix preservation) remain identical and apply to the `path` returned from `resolve_id_from_lookup`. Specifically: when `--lookup-table` is set with a `--base-url` flag, that base wins (existing behavior); when `--lookup-table` is set without `--base-url`, the URL's own prefix is used; the remote-mode percent-quoting branch (lines 924-926) is skipped because `args.remote_base_url` is None in this mode.
- Update `_require_source` to recognize `args.lookup_table` as a satisfied source. Add `args.lookup_table` to the truthy check alongside `args.source` and `args.remote_base_url`:
  ```python
  if args.source is None and not getattr(args, 'remote_base_url', None) and not getattr(args, 'lookup_table', None):
      ...
  ```
  Adjust the error messages in both branches of `_require_source` to mention `--lookup-table` as an option.
- Update the module `__doc__` block and the `main()` epilog: add a line under `Sources (mutually exclusive):` introducing `--lookup-table`, add an example demonstrating dump-then-resolve, and add the flag to the per-subcommand sections.

**Patterns to follow:**

- The existing mutually-exclusive group already handles the `--from`/`--remote-base-url` collision via argparse; adding a third member uses the same mechanism without writing new validation code.
- `error_log` + `sys.exit(2)` is the established pattern for parse/IO/validation failures (used by `_build_or_die` and the remote-mode error paths in `_load_index`).
- The `dispatch in `_load_index` based on which source is set` style is mirrored at the subcommand level here rather than in `_load_index` itself, because the lookup-table path returns a different in-memory shape (`dict[str, dict]`) than the chunk path's `(files, anchors, id_to_pair)` tuple. Mixing the two in `_load_index` would force a sum-type return.

**Test scenarios:**

End-to-end coverage is in U4. Implementation-time spot-checks:

- `python resolve-landmarks.py resolve <id> --lookup-table /tmp/dump.json` returns the same path as `--from tests/fixtures/`.
- `python resolve-landmarks.py resolve <id> --from tests/fixtures/ --lookup-table /tmp/dump.json` → argparse error (mutual-exclusion).
- A JSON file with `{"format_version": 99, "source": {...}, "landmarks": {}}` → exit 2, stderr names the unsupported version.
- A non-JSON file (e.g. `echo "not json" > /tmp/bad.json`) → exit 2, stderr names the file.

**Verification:**

- Read the `cmd_resolve` and `cmd_rewrite` diffs side-by-side: both gain the same short branch (~6-8 lines) and call `resolve_id_from_lookup`. No copy-pasted lookup logic between them.
- `_require_source`, `_add_source_flags`, the module docstring, the `main()` epilog, and the `dump_parser` definition all reflect the new flag consistently — no stale text mentioning only the two original source options.
- `args.lookup_table` is never reachable from `cmd_dump`; either argparse rejects it (preferred) or the implementation simply does not register it on `dump_parser`. The latter is the chosen path (dump_parser does not call `_add_source_flags`'s third option — clarification: `_add_source_flags` registers the lookup-table flag on all subparsers including dump, which would let a user dump from a lookup table. To prevent the no-op-with-provenance-erasure issue noted in Key Decisions, add a post-parse check at the top of `cmd_dump`: `if args.lookup_table: error_log("--lookup-table is not a valid source for dump; use --from or --remote-base-url"); sys.exit(1)`).

---

### U3. Generate and commit the ePublisher Designer 2026.1 fixture artifact

**Goal:** Produce a real-world lookup-table artifact from the ePublisher Designer 2026.1 help that ships with the product, and commit it under `tests/fixtures/` as the canonical reference exemplar and as input data for the verifier's round-trip scenarios.

**Requirements:** R10 (covers AE6 input)

**Dependencies:** U1 (the dump command must emit the structured shape before the artifact is generated).

**Files:**
- `plugins/webworks-claude-skills/skills/reverb2/tests/fixtures/epublisher-designer-2026.1-help-lookup.json` — new file, generated by running the U1 dump command against the ePublisher help directory and post-processing the `source.path` field for portability.

**Approach:**

- Run the dump command against the ePublisher 2026.1 help directory:
  ```bash
  python plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py \
      dump \
      --from "C:/Program Files/WebWorks/ePublisher/2026.1/ePublisher Designer/Help/en" \
      --out plugins/webworks-claude-skills/skills/reverb2/tests/fixtures/epublisher-designer-2026.1-help-lookup.json
  ```
- The raw output's `source.path` will be the absolute Windows path passed via `--from`, which is machine-specific. Post-process the committed file's `source.path` to a stable, repo-portable representation:
  ```
  "path": "<ePublisher 2026.1 install root>/ePublisher Designer/Help/en/"
  ```
  Trailing slash included so the value is self-evidently a directory. Document the replacement in a one-line comment on the same commit ("source.path normalized from absolute Windows path to portable placeholder so the committed artifact diffs cleanly across build machines"). The verifier does **not** parse this string — it is provenance metadata only.
- Inspect the generated JSON for two things before committing:
  1. **Path normalization sanity check.** Open the file, grep `\\` (backslash) inside any `"file"` field. None should appear. If any do, the brainstorm's assumption is violated and U1 needs a normalization step (replace `\\` with `/` in `_build_dump_artifact` for `landmarks[*].file` values); update U1's Approach to add this step and regenerate.
  2. **Unicode preservation check.** If the artifact happens to contain Unicode IDs (none expected from ePublisher Designer's stock content, but the check is cheap), confirm they appear raw, not as `\uXXXX`.
- Reset `source.captured_at` in the committed file to a fixed value (`"2026-05-21T00:00:00Z"` — the planning date — clearly stamped as a snapshot-time placeholder so future refreshes get an obvious diff). This keeps the committed artifact diff-clean against re-runs of the verifier, which monkey-patches `_now_iso_utc` to a fixed value as well.
- Verify the file size is well under the 200KB estimate (early estimate from the issue body). If it exceeds 500KB, escalate to a planning revision — compression was explicitly deferred in scope, but a >500KB file would warrant revisiting that decision.

**Patterns to follow:**

- Other large fixtures in `tests/fixtures/` (e.g. `landing-with-hash.html`) are committed verbatim with no post-processing. This artifact's only post-processing is the `source.path` and `source.captured_at` substitutions, both of which are non-load-bearing metadata fields — the `format_version`, `source.type`, `source.chunks_found`, and `landmarks` map are bit-for-bit what the dump produced.

**Test scenarios:**

- The verifier (U4) loads this artifact and asserts: `format_version == 1`, `source.type == "local-directory"`, `source.chunks_found == 7`, `landmarks` non-empty.
- Manually open the file in an editor; the `source` block is human-readable and self-documenting.

**Verification:**

- File exists, parses as JSON, has the three top-level keys.
- `chunks_found` is exactly `7` (matches the issue body's expected value and the planning-time count).
- File size is under 200KB (commit log notes the actual size).
- No backslash characters appear in any `landmarks.*.file` value (path normalization assumption holds; if not, U1 gets the normalization step).
- The `source.path` value does not contain `C:` or any absolute-path prefix (post-processing was applied).

---

### U4. Extend the verifier with dump and lookup-table scenarios

**Goal:** Add PASS/FAIL scenarios to `tests/verify-landmark-resolver.py` that prove determinism, round-trip equivalence, Unicode preservation, and `format_version` validation, plus coverage for the new `--lookup-table` source mode on both `resolve` and `rewrite`.

**Requirements:** R11 (covers AE6)

**Dependencies:** U1, U2, U3.

**Files:**
- `plugins/webworks-claude-skills/skills/reverb2/tests/verify-landmark-resolver.py` — modify; add a new section near the end (before the `_summary()` invocation) for the dump/lookup-table scenarios, following the existing `check(name, condition, detail)` and `run_cli(...)` patterns.

**Approach:**

Add these scenarios as a new section commented `# --- dump artifact + lookup-table consumer path (issue #77) ---`:

1. **Determinism (AE2).** Monkey-patch `resolver._now_iso_utc` to return a fixed timestamp. Run `cmd_dump` twice against `MULTI_DIR` (or `run_cli('dump', '--from', str(MULTI_DIR), '--out', tmp1)` and again with `tmp2`). Read both files as bytes. Assert byte-equal. `check('dump is byte-deterministic across runs', bytes_equal, ...)`.

2. **Structured shape (AE1).** Run `dump --from MULTI_DIR --out tmp.json`. `json.load` the file. Assert top-level keys are exactly `{"format_version", "source", "landmarks"}`, `format_version == 1`, `source.type == "local-directory"`, `source.path == str(MULTI_DIR)`, `source.chunks_found == 3` (single-chunk + multi-chunk-a + multi-chunk-b + unicode-ids — actually 4; verify at implementation time and assert the actual count). The `landmarks` dict has sorted keys and `{file, anchor}` nested entries.

3. **Sorted-keys output.** Read the raw file bytes (not just the parsed dict). Confirm the top-level keys appear in sorted order (`format_version` < `landmarks` < `source` alphabetically — wait, that's wrong, alphabetical is `format_version` < `landmarks` < `source`, so `format_version` comes first, `landmarks` second, `source` third). Then confirm the `landmarks` keys appear in sorted order in the file text. Use a simple `text.index('"id_a"') < text.index('"id_b"')` for two known-adjacent IDs from the multi-chunk fixtures.

4. **Unicode preservation (AE3).** Run `dump --from UNICODE_CHUNK --out tmp.json`. Read the file as bytes. Assert `b'\xe6\xa6\x82\xe8\xa6\x81'` (UTF-8 for `概要`) appears literally in the file. Assert no `b'\\u'` byte sequence appears inside any `landmarks` key (a stricter check: search for `b'"\\u'` to catch escaped JSON-string keys specifically).

5. **Round-trip equivalence (AE4, covers AE6).** For every ID in `MULTI_DIR`'s merged index, assert `run_cli('resolve', landmark_id, '--lookup-table', tmp.json).stdout == run_cli('resolve', landmark_id, '--from', str(MULTI_DIR)).stdout`. Single `check` reporting "round-trip equivalence: N IDs match" with N counted at run time. Per-ID failures appear in the `detail` string.

6. **Round-trip equivalence — Unicode.** Same as scenario 5 but using `UNICODE_CHUNK`. Special-case because the `概要` ID exercises the percent-decoded path in `cmd_rewrite` as well; add a second `check` that runs `rewrite "http://example.com/help/#/%E6%A6%82%E8%A6%81" --lookup-table tmp.json` and asserts the resolved URL matches `--from UNICODE_CHUNK`'s output.

7. **`format_version` validation (AE5).** Write a synthetic JSON file `{"format_version": 99, "source": {"type": "local-directory", "path": "/x", "chunks_found": 0, "captured_at": "2026-05-21T00:00:00Z"}, "landmarks": {}}` to a tmp file. Run `resolve some_id --lookup-table tmp.json`. Assert returncode == 2 and stderr contains `unsupported format_version` and `99`. Repeat with `format_version: 0` (boundary), and with a missing `format_version` field (should also exit 2 with a clear message).

8. **Mutual exclusion (AE4 implicit).** Run `resolve some_id --from MULTI_DIR --lookup-table tmp.json`. Assert returncode != 0 (argparse exits 2). Repeat the matrix: `--from + --remote-base-url`, `--from + --lookup-table`, `--remote-base-url + --lookup-table`.

9. **`dump --lookup-table` rejection.** Run `dump --lookup-table tmp.json`. Assert returncode == 1 and stderr contains `not a valid source for dump`.

10. **Real-artifact smoke (U3 cross-reference).** Load `FIXTURE_DIR / 'epublisher-designer-2026.1-help-lookup.json'`. Assert `format_version == 1`, `source.type == "local-directory"`, `source.chunks_found == 7`, `landmarks` is non-empty. Pick one known ID from the artifact (the verifier reads it dynamically from the fixture's keys — take the lexicographically smallest one) and run `resolve <id> --lookup-table <artifact>`; assert exit code 0 and stdout has the expected `file#anchor` or `file` shape.

11. **Remote-mode dump source block (R6 spot-check).** Reuse the verifier's existing stub-fetcher pattern from the v2 scenarios. Run `dump --remote-base-url https://example.com/help/ --out tmp.json` with the stub registered. Assert `source.type == "remote-base-url"`, `source.base_url == "https://example.com/help/"`, `source.chunks_found > 0`. (Read the existing remote-mode test helpers in the verifier; reuse the same fetcher stub fixtures.)

**Patterns to follow:**

- Existing `run_cli(...)` and `check(...)` helpers (lines 63-80) — use them verbatim.
- The verifier's tempfile pattern (`tempfile.TemporaryDirectory()` or `tempfile.NamedTemporaryFile()`) — match what the v2 scenarios do for remote-mode test isolation.
- Monkey-patch via `resolver._now_iso_utc = lambda: "2026-05-21T00:00:00Z"` — mirrors the existing `resolver._sleep` and `resolver._now` patching pattern in the v2 remote-mode scenarios.

**Test scenarios:**

The verifier's own scenarios are the test scenarios. Manual verification:

- `python plugins/webworks-claude-skills/skills/reverb2/tests/verify-landmark-resolver.py` exits 0. Every new scenario reports PASS.
- Comment out a load-bearing line of U1 (e.g. drop `ensure_ascii=False`); rerun the verifier; the Unicode scenario reports FAIL. Restore and confirm PASS. (Sanity check that the new scenarios actually exercise the new code.)

**Verification:**

- All scenarios in the new section follow the existing `check(...)` format — no new assertion infrastructure introduced.
- Scenarios are independent: each constructs its own tmp file or uses the committed fixture; no shared mutable state between scenarios.
- The verifier still exits 0 against the existing codebase after U1, U2, U3 land — no pre-existing scenario was broken by the changes.

---

### U5. Update `workflows/landmark-resolution.md` to cover the lookup-table source mode and document the dump schema inline

**Goal:** Surface the new source mode and the structured dump shape in the user-facing workflow doc so consumers can discover and use both without reading the script's `--help`.

**Requirements:** R12, R13 (covers AE7)

**Dependencies:** U1, U2 (the surfaces being documented must exist).

**Files:**
- `plugins/webworks-claude-skills/skills/reverb2/workflows/landmark-resolution.md` — modify several sections (Step 1 source table, Step 2 subcommand flag table, Step 6, new "Dump Artifact Schema" section after Step 6).

**Approach:**

- **Step 1 source table.** Add a third row to the "Source" table (line 20-23):
  ```markdown
  | **Lookup table** (`--lookup-table <file>`) | You have a pre-built dump artifact for a known mirror (e.g., the ePublisher Designer 2026.1 help fixture this repo ships). Fully offline, O(1) per query, no chunk parsing. |
  ```
  Update the surrounding sentence ("`--from` and `--remote-base-url` are mutually exclusive on every subcommand") to "`--from`, `--remote-base-url`, and `--lookup-table` are mutually exclusive on every subcommand. For `rewrite`, a stable URL with an `http://` or `https://` scheme auto-infers the remote base when no source flag is set."
- **Step 1c (new).** Add a new subsection "Step 1c: Lookup table (pre-built artifact)" after Step 1b:
  ```markdown
  ### Step 1c: Lookup table (pre-built artifact)

  Point `--lookup-table` at a JSON file produced by `dump`:

  ```bash
  python scripts/resolve-landmarks.py resolve <id>  --lookup-table <path/to/dump.json>
  python scripts/resolve-landmarks.py rewrite <url> --lookup-table <path/to/dump.json>
  ```

  Use this when you know in advance which mirror you are resolving against and want to ship the lookup data alongside the skill or tool — no chunk parsing at runtime, no network access, no dependency on the chunks being reachable. The resolver loads the JSON once and serves every query from an in-memory dict. The artifact is `format_version: 1` and the resolver refuses any other version with exit code 2.
  ```
- **Step 2 flag table.** Add `--lookup-table <file>` rows. Update the "Mode" table (line 73-77) to add an `dump --out <file>` mention. Update the flag table (line 81-91) to add `--lookup-table <file>` (subcommands: `resolve`, `rewrite`) and `--out <file>` (subcommands: `dump`).
- **Step 6 rewrite.** The current Step 6 text (lines 138-149) points at the flat-shape dump output. Rewrite to describe the structured shape and point at U5's new schema section:
  ```markdown
  ## Step 6: Rewrite Stable URLs in Bulk (Optional)

  To rewrite a list of stable URLs found in skill documentation or other sources, dump the index once and consume the artifact in a script or via `--lookup-table`:

  ```bash
  # Dump the index once
  python scripts/resolve-landmarks.py dump --remote-base-url <help-mirror-url> --out landmarks.json

  # Option A: feed it back into the resolver in O(1) per query
  python scripts/resolve-landmarks.py rewrite "<stable-url>" --lookup-table landmarks.json

  # Option B: parse the JSON in your own tooling — see "Dump Artifact Schema" below
  ```

  The artifact is structured, versioned (`format_version: 1`), and deterministic — running `dump` twice against the same source produces byte-identical output excluding `source.captured_at`. Commit the artifact alongside skill docs if it is small enough to be diff-friendly; refresh it whenever the published help is regenerated.
  ```
- **New section: Dump Artifact Schema** (between Step 6 and the Worked Examples). Add ~25-35 lines covering:
  - The full JSON example from R3.
  - A field reference table: `format_version` (integer, currently `1`, hard-gated), `source.type` (`"local-directory" | "remote-base-url"`), `source.path` (verbatim `--from` value, local mode only), `source.base_url` (remote mode only), `source.chunks_found` (count), `source.captured_at` (UTC ISO 8601, second precision, trailing `Z`), `landmarks` (sorted map of `id → {file, anchor}` where `anchor` may be empty).
  - One sentence on resolution semantics: "`file#anchor` when `anchor` is non-empty, bare `file` otherwise — matches the runtime's `GetPathById` formatting."
  - One sentence on Unicode: "Landmark IDs are emitted as raw UTF-8 (`ensure_ascii=False`). A `概要` source ID appears literally in the file, not as `\uXXXX`."
  - One sentence on schema evolution: "`format_version` is a hard gate. Future schema changes ride a version bump; the resolver refuses unknown versions with exit code 2."
- **Step 5 exit codes.** Add a row or amend the existing rows: exit code 2 also covers "unsupported `format_version` in `--lookup-table` artifact" and "malformed `--lookup-table` JSON". A single sentence appended to the "exit code 2" row's "Common causes" cell is sufficient — no new row.

**Patterns to follow:**

- The existing workflow doc uses Markdown tables for flag/mode references; preserve the same column shape.
- The existing "Worked Example" sections show end-to-end commands with expected output; if space allows, add a brief Worked Example for the lookup-table path (dump-then-resolve against the committed `epublisher-designer-2026.1-help-lookup.json` fixture, with one real ID from that artifact and its expected resolved path).

**Test scenarios:**

Test expectation: none — this is a documentation change.

Manual verification:

- Read Step 1's source table; confirm three rows in mutual-exclusion language.
- Read Step 6; the structured `dump` output is described and the inline schema section is the next thing on the page.
- The schema section is self-contained (a reader who jumps directly to it understands the shape without flipping back to other sections).

**Verification:**

- Markdown renders without breakage (tables are valid, code blocks balance).
- AE7's reader-test passes: a developer reading the doc for the first time sees three rows in the source table; Step 6 directs them at the structured dump schema.

---

### U6. Bump plugin minor version

**Goal:** Apply the project's required version bump so the new feature ships under a new version, per `CLAUDE.md` ("minor: new skills, new features, enhancements").

**Requirements:** Project convention (not an origin requirement, but mandated by repo `CLAUDE.md`).

**Dependencies:** U1, U2, U3, U4, U5 (the version bump ships the work, so it goes last).

**Files:**
- `plugins/webworks-claude-skills/.claude-plugin/plugin.json` — version field
- `.claude-plugin/marketplace.json` — version field

**Approach:**

- Run `scripts/bump-version.sh minor` from the repo root. The script reads `plugin.json`, increments minor (2.12.3 → 2.13.0), zeros the patch, and writes the same version back into both `plugin.json` and `marketplace.json`.
- The new subcommand evolution + new flag + new fixture is an additive feature, not a breaking change to the *plugin's* public surface. The breaking change to `dump`'s JSON output shape (R2) is internal to the resolver script's contract; the plugin's user-facing surface (skill descriptions, slash commands, workflow docs) grows monotonically.
- Do not hand-edit the JSON files.

**Patterns to follow:**

- `scripts/bump-version.sh` — the canonical bump path. Recent commits show the same pattern when introducing features (e.g., commit `cdb25d7` bumped to 2.11.1 for an enhancement).

**Test scenarios:**

Test expectation: none — this is a metadata bump.

- *Manual verification.* After running the script, both manifest files show `"version": "2.13.0"`. The script's own output reports the same new version.

**Verification:**

- `jq -r '.version' plugins/webworks-claude-skills/.claude-plugin/plugin.json` returns `2.13.0`.
- `jq -r '.version' .claude-plugin/marketplace.json` returns `2.13.0`.
- `git diff --stat` shows changes only to those two files plus the files touched by U1–U5.

---

## Scope Boundaries

### In scope

- Evolving `dump`'s default JSON output shape to the structured, versioned form.
- `--out <file>` flag (with `-` as explicit stdout alias).
- `--lookup-table <file>` source mode on `resolve` and `rewrite`.
- Hard-gating on `format_version == 1` in the consumer path.
- A committed real-ePublisher fixture artifact under `tests/fixtures/`.
- Verifier scenarios for determinism, round-trip, Unicode, and version validation.
- Inline schema documentation in `workflows/landmark-resolution.md`.
- Minor version bump.

### Out of scope

- **Automatic snapshot refresh, publishing, or CI plumbing for baked artifacts.** Deciding when and how baked artifacts get refreshed on each Reverb release is downstream. (Origin scope boundary.)
- **Compressed or binary dump output.** v1 is uncompressed JSON; the ePublisher 2026.1 estimate is well under 200KB. (Origin scope boundary.)
- **Reverse-lookup output (file → ids).** Issue #78 owns that direction. The runtime's `pairToId` is not mirrored here. (Origin scope boundary.)
- **Python-API surface for in-process consumers.** The script remains CLI-only. Skills that want programmatic resolution shell out or load the JSON directly with `json.load`. (Origin scope boundary.)
- **`--shape runtime` for runtime-localStorage interop.** Single skill-friendly shape only for v1; a `--shape` flag can be added under a future `format_version` if a consumer surfaces a real need. (Origin Key Decision.)
- **Backwards-compatible `--legacy-flat` flag on `dump`.** The flat shape is removed cleanly. The workflow doc updates in lockstep (U5). Repo grep at planning time finds no other consumers. (Origin Key Decision + assumption.)
- **A new top-level reference file for the schema.** R13 favored inline documentation; planning's section-length estimate (~25-35 lines) stays under the 40-line split-out threshold. (Origin Outstanding Question, resolved.)
- **`--shape` flag, `--legacy` flag, or any other `dump` output toggle beyond `--table` and `--out`.** The surface stays minimal.

### Deferred to Follow-Up Work

- **Reverse-lookup output (file → ids).** Issue #78.
- **Automated artifact refresh on Reverb release.** Open question — could be a small CI job, a `scripts/` helper, or a manual checklist; the right answer depends on how often Reverb ships and who curates the artifacts.
- **Dumping additional product help mirrors as committed fixtures** (e.g., ePublisher Help Center, other WebWorks products). The first artifact is the proof; broader rollout is a curation decision.

---

## Risks

- **Risk: a real ePublisher chunk contains a Windows-style path separator in its `f` entry, violating the brainstorm's "no normalization for v1" assumption.** Likelihood: low (chunks are emitted by the Reverb runtime, which uses forward-slash URLs internally). Impact: medium (forces a normalization step in U1 and an artifact regeneration in U3). Mitigation: U3's path-normalization sanity check catches it before commit; the U1 fix is a single `value.replace('\\', '/')` call in the `landmarks` dict comprehension.
- **Risk: an out-of-tree consumer of the flat-shape `dump` output exists and silently breaks on upgrade.** Likelihood: low (repo grep is clean; the resolver script's surface is documented only in the workflow doc, which updates in lockstep). Impact: medium (a downstream skill that vendored the flat shape would parse the new shape as garbage). Mitigation: the change ships under a clear feature commit and a minor version bump; if a consumer surfaces, a `--legacy-flat` flag can be added in a patch release without rebreaking compatibility (the new shape stays the default).
- **Risk: the committed artifact's `source.captured_at` placeholder gets refreshed on every regeneration, polluting `git blame`.** Likelihood: medium (any artifact refresh will change the timestamp). Impact: low (the line is metadata; the noise is one line per refresh). Mitigation: the fixed placeholder (`"2026-05-21T00:00:00Z"`) is documented in U3's Approach so refreshes update it consistently; a future automation could pin the value to a release-tied constant.
- **Risk: Windows line-ending translation produces non-deterministic output between platforms.** Likelihood: low (the implementation writes bytes, not text). Impact: high if it occurred (every determinism check fails on Windows). Mitigation: U1's Approach explicitly writes `.encode('utf-8')` via `write_bytes` or `sys.stdout.buffer.write`, bypassing Python's newline translation. The verifier's determinism scenario catches any regression at test time.
- **Risk: the verifier's monkey-patch on `_now_iso_utc` accidentally leaks between scenarios, producing fake timestamps in unrelated tests.** Likelihood: low. Impact: low (other scenarios do not inspect `captured_at`). Mitigation: each scenario that monkey-patches restores the original via `try`/`finally`, matching the existing v2 pattern for `_sleep` and `_now` patches.

## Final Checks

Before commit:

- [ ] `cmd_dump` produces the structured shape and writes deterministic UTF-8 bytes regardless of platform.
- [ ] `--lookup-table` is registered on both `resolve` and `rewrite`, hard-gates on `format_version == 1`, and is rejected on `dump`.
- [ ] `tests/fixtures/epublisher-designer-2026.1-help-lookup.json` exists, has `chunks_found: 7`, has a portable `source.path`, and a fixed `source.captured_at` placeholder.
- [ ] `python tests/verify-landmark-resolver.py` exits 0 with every new scenario reporting PASS.
- [ ] `workflows/landmark-resolution.md` shows three source rows, an inline schema section, and a Step 6 that points at the structured shape.
- [ ] `plugin.json` and `marketplace.json` both report `2.13.0`.
- [ ] No unrelated files changed.
- [ ] Commit messages use conventional commit format (`feat:` for the resolver + workflow + fixture changes, `chore:` for the version bump).
