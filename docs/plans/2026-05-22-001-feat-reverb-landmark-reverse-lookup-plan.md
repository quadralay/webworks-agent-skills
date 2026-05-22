---
title: "feat: Reverse-lookup subcommand for Reverb landmark resolver"
type: feat
status: active
created: 2026-05-22
issue: 78
origin: docs/brainstorms/2026-05-22-issue-78-reverb-landmark-reverse-lookup-requirements.md
depth: lightweight
---

# feat: Reverse-Lookup Subcommand for the Reverb Landmark Resolver

## Summary

Extend `plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py` with a new `reverse <path>` subcommand that answers the inverse of the existing forward question: given a file path (raw or percent-encoded), return the landmark ID(s) bound to it. The subcommand reuses the same `(files, anchors, id_to_pair)` index the existing `resolve` / `rewrite` / `dump` subcommands consume, so it composes with every source mode the resolver already supports — `--from` (local chunks), `--remote-base-url` (HTTP mirror), and `--lookup-table` (pre-built dump artifact). Extend the resolver's standalone verifier with reverse-lookup scenarios and update the resolver's workflow doc to cover the new subcommand. Bump the plugin version for the additive feature.

## Problem Frame

The resolver currently answers `id → file[#anchor]` (forward). The brainstorm captures three workflow families that need the opposite direction — stable-URL minting, link audits, and anchor citations — and notes that the underlying chunk data already binds `(file_index, anchor_index) → id` in the same `e` rows the forward map walks. No CLI surface exposes this direction today; callers must `dump` the index and grep its value side, which neither composes cleanly nor matches the runtime contract (`GetIdByPath` in `scripts/landmarks.js`). See origin: `docs/brainstorms/2026-05-22-issue-78-reverb-landmark-reverse-lookup-requirements.md`.

## Requirements Traceability

Origin requirements R1–R17 and acceptance examples AE1–AE8 are addressed across the implementation units below:

- **R9, R10** — extend `_merge_chunks` to produce a reverse map in the same pass → U1
- **R1, R2, R6, R7, R8** — `reverse <path>` subcommand, default multi-binding output, percent-decode input → U2
- **R3, R4, R5** — `--anchor`, `--first`, and `--json` flags with mutual-exclusion handling → U2
- **R11, R12** — lookup-table consumer path for `reverse` (in-memory inversion on load) → U3
- **R13** — verifier scenarios for happy paths, edge cases, and mutual exclusion (AE1–AE5) → U4
- **R14** — forward-then-reverse round-trip scenario across the merged fixture index (AE7) → U4
- **R15** — lookup-table parity scenarios re-running every reverse scenario against the dump artifact (AE6) → U4
- **R16, R17** — `workflows/landmark-resolution.md` updates: Step 2 table row, new Step 7 with worked examples (AE8) → U5
- **Plugin version bump** (per repo `CLAUDE.md`) → U6

## Key Technical Decisions

The brainstorm flagged four planning-resolvable questions. Decisions:

- **Default bare-output shape is one ID per line** (Q: stdout format for the default, non-`--first`, non-`--anchor`, non-`--json` case). Resolves the brainstorm's R2/R5 outstanding question (a) vs (b). Bare line-oriented output composes with `xargs`, `sort -u`, and pipe-chained tooling that the link-audit workflow uses; the anchor metadata is still reachable via `--json`. Adding `<anchor>\t<id>` to the bare form would split the "default" shape unnecessarily — the JSON shape from R5 is the canonical structured output.
- **`--anchor ""` is rejected by argparse with a "use --first" message** (Q: semantics of empty-string `--anchor`). Picks option (b) from the brainstorm. The page-level binding has a dedicated flag (`--first`); accepting `--anchor ""` would create two ways to ask the same question and force callers to remember which one the resolver canonicalizes in error messages. Reject with `error: --anchor cannot be empty; use --first to retrieve the page-level binding`.
- **`path_to_bindings` is built eagerly inside `_merge_chunks`** (Q: eager vs lazy reverse-map construction). The brainstorm's threshold ("if eager construction adds < 5 ms on a 5000-ID artifact, do it eagerly") favors eager; per-row work is a single `setdefault(...).append(...)` over rows the merge loop already touches, dominated by parse cost. Eager construction keeps the forward and reverse maps consistent by construction (no second code path), and the memory cost is bounded by `len(id_to_pair)`.
- **Workflow section heading: `## Step 7: Reverse Lookup — Find IDs That Target a Path`** (Q: section heading wording). Parallels the verb-leading shape of "Step 6: Rewrite Stable URLs in Bulk" and is the most-discoverable form for the audit workflow described in R17. URL-minting is exercised by a worked example inside the section.

Additional planning-time decisions:

- **Multi-binding default order: empty-anchor first, then ascending anchor index, then a final stable tiebreaker by landmark ID.** R9 specifies "anchor index ascending, empty-anchor first." Two rows with the same `(file_index, anchor_index)` cannot coexist (last-write-wins collapses them), so ties on `anchor_index` cannot happen across the merged index — but in case the runtime ever rebinds the same `(fi, ai)` to two IDs (e.g., a regenerated chunk overwriting a stale one in remote mode), the planner sorts the final pair list by `(anchor_index, landmark_id)` so output is deterministic regardless of dict insertion order.
- **Lookup-table inversion is computed exactly once per process, on first `reverse` query.** R11 says "subsequent queries are O(1) per path." Building the inversion lazily inside `cmd_reverse` (rather than inside `load_lookup_table`) keeps the existing `load_lookup_table` shape unchanged and avoids paying the cost on `resolve` / `rewrite` queries that go through the same loader. The inverted map is local to the `cmd_reverse` call, so process exit cleans it up — no module-level cache to invalidate.
- **`reverse` rejects `--base-url` (rewrite's flag) at argparse.** The flag has no meaning for path-to-id; not adding it to `reverse`'s subparser is the implementation of this decision — no extra plumbing needed.
- **Argparse `--first` and `--anchor` mutual exclusion uses `add_mutually_exclusive_group(required=False)`.** Matches how `--from` / `--remote-base-url` / `--lookup-table` are wired today.

## Assumptions

- The `_merge_chunks` extension does not affect `resolve` / `rewrite` / `dump` output. Verified at planning time by reading the function: those subcommands ignore the new third return value when callers don't request it. The plan adds a fourth element to `_merge_chunks`'s return tuple (rather than a fifth output variable) and threads it only into the `reverse` path; `build_index` and `build_index_from_texts` extend their return types accordingly.
- The standalone verifier (`tests/verify-landmark-resolver.py`) is the single test entry point. New scenarios go in as `check(...)` calls in the same shape as the existing 80+ scenarios. No new dependency, no pytest infrastructure introduction.
- The committed lookup-table fixture `tests/fixtures/epublisher-designer-2026.1-help-lookup.json` is the realistic artifact used in R17's worked example. Verified by directory listing at planning time.
- R8's "file component only" requirement is automatically satisfied: the index keys reverse bindings by file index, and an input path that contains a `#` will simply fail to match (the chunk's `f` array stores files without anchors). The plan does not introduce a `splitPath` on the input — that would invite the "anchor on path argument" interpretation, which R3's `--anchor` flag already handles cleanly.

## Output Structure

```
plugins/webworks-claude-skills/skills/reverb2/
  scripts/resolve-landmarks.py            # extend _merge_chunks, add cmd_reverse, argparse wiring
  tests/verify-landmark-resolver.py       # add reverse scenarios incl. round-trip and lookup-table parity
  workflows/landmark-resolution.md        # add Step 2 row, new Step 7, flag-table rows

plugins/webworks-claude-skills/.claude-plugin/plugin.json     # version bump
.claude-plugin/marketplace.json                                # version bump
```

No new files. Every change is additive to existing files except the version bump.

## Implementation Units

### U1. Extend `_merge_chunks` with a reverse map

**Goal:** Produce the `path_to_bindings: dict[int, list[tuple[int, str]]]` reverse map in the same chunk pass as the forward `id_to_pair`, so every source mode (local, remote, lookup-table-converted-to-chunk-equivalent) shares one construction site. Pre-sort each value list by `(anchor_index, landmark_id)` before returning.

**Requirements:** R9, R10.

**Dependencies:** none.

**Files:**

- `plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py` — modify `_merge_chunks`; update `build_index` and `build_index_from_texts` return types accordingly.

**Approach:**

- Add a fourth accumulator dict `path_to_bindings: dict[int, list[tuple[int, str]]]` inside `_merge_chunks`. In the same loop that writes `id_to_pair[landmark_id] = (file_map[local_fi], anchor_map[local_ai])`, append `(file_map[local_fi], anchor_map[local_ai], landmark_id)` semantics into the reverse structure: `path_to_bindings.setdefault(file_map[local_fi], []).append((anchor_map[local_ai], landmark_id))`.
- After the loop, sort each value list by `(anchor_index, landmark_id)` so the empty-anchor binding (anchor index `0` when interned first, which it is for every fixture and is the runtime's documented convention) sorts first. Sorting by `(anchor_index, landmark_id)` is stable regardless of intern order: if the empty string `""` is interned at some index other than `0` in a future chunk shape, the page-level binding's anchor string is still the empty string and downstream consumers test on that, not on the index.
- Implementation nuance: a single ID can be rebound to a different `(file_index, anchor_index)` across chunks (last-write-wins). The forward map's `dict.__setitem__` handles this automatically. For the reverse map, the same row visiting order will append both stale and final bindings to `path_to_bindings`. The plan resolves this by tracking *which `(file_index, anchor_index)` is currently authoritative* via a small `pair_to_id: dict[tuple[int, int], str]` accumulator built alongside `id_to_pair`; at end of merge, derive `path_to_bindings` from `pair_to_id` by inverting it once. This mirrors how the runtime's `Landmarks.Advance` builds `pairToId` (see brainstorm's runtime notes from #77) and guarantees no stale rows leak into the reverse map.
- Return tuple becomes `(global_files, global_anchors, id_to_pair, path_to_bindings)` from `_merge_chunks`. Both `build_index` and `build_index_from_texts` propagate the new field. Update their docstring "Returns:" sections and the planner-level `_load_index` to thread the fourth element through to the subcommand handlers that need it.
- Update `_load_index`'s return type from `(files, anchors, id_to_pair, chunks_found)` to `(files, anchors, id_to_pair, path_to_bindings, chunks_found)`. Callers that only need the first four (forward path) destructure with an underscore for `path_to_bindings`.

**Patterns to follow:**

- The merge loop's existing guards (skip `not isinstance(row, list)`, `len(row) < 3`, etc.) are reused — the reverse map is populated only when the forward map is, so the guard sequence is unchanged.
- The "shared interner" pattern (`intern(value, global_list, index)`) already produces the indices the reverse map needs — no new intern step.

**Test scenarios:**

- *Internal.* Add a `test_internal_build_index_reverse_map` scenario that builds the index from `single-chunk_lx.js` and asserts: (a) `path_to_bindings` contains an entry for the file index of `Group/page.html`; (b) that entry's value list is sorted by `(anchor_index, landmark_id)`; (c) the page-level binding (anchor `""`) appears first; (d) `out-of-range-file` and `out-of-range-anchor` rows are not present (they fail the existing guards before `path_to_bindings` is touched).
- *Internal.* Add a `test_internal_reverse_map_last_write_wins` scenario over `multi-chunk-a_lx.js` + `multi-chunk-b_lx.js` and assert that `common_id` appears in `path_to_bindings` only under `groupB/page.html` (the last write), not under `groupA/page.html`. This is the runtime-parity check.

**Verification:**

- Running the verifier (`python plugins/webworks-claude-skills/skills/reverb2/tests/verify-landmark-resolver.py`) prints `PASS` for both new internal scenarios.
- No existing scenario flips from PASS to FAIL (the fourth tuple element is additive).

---

### U2. Add `reverse` subcommand handler and argparse wiring

**Goal:** Expose the new subcommand with positional `path`, default multi-binding output, `--first`, `--anchor`, `--json`, and the shared `--from` / `--remote-base-url` / `--lookup-table` source flags.

**Requirements:** R1, R2, R3, R4, R5, R6, R7, R8.

**Dependencies:** U1 (needs the reverse map).

**Files:**

- `plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py` — add `cmd_reverse`, add subparser block in `main()`, extend `_load_index` consumer.

**Approach:**

- Add a new subparser `reverse` in `main()` mirroring the `resolve` subparser's structure (positional argument, source flags via `_add_source_flags(required=True)`). Place it after `dump`. Subparser-level flags:
  - `--anchor <id>`: optional, dest `anchor`. Reject empty string with `parser.error("--anchor cannot be empty; use --first to retrieve the page-level binding")` early in `cmd_reverse` (argparse does not have a built-in "non-empty string" type; do this in the handler before any work).
  - `--first`: optional, `action='store_true'`, dest `first`. Wire into a mutually-exclusive group with `--anchor`: `group = subparser.add_mutually_exclusive_group(); group.add_argument('--anchor', ...); group.add_argument('--first', ...)`. Argparse handles the mutual-exclusion exit (code `2`) on its own. **Covers AE3's exclusion clause.**
  - `--json`: optional, `action='store_true'`, dest `json`. Same dest name as `resolve --json` for consistency.
- Implement `cmd_reverse(args)`:
  1. Validate `--anchor` non-empty (parser error path described above).
  2. Decode the input path: `decoded_path = urllib.parse.unquote(args.path, errors='strict')`. On `UnicodeDecodeError` / `ValueError`, exit `1` with `error_log(f"Malformed percent-encoded path: {args.path} ({e})")` (mirrors `rewrite`'s ID-side decode error path). **Covers R6.**
  3. Branch on source:
     - **Lookup-table path:** call a new helper `_invert_lookup_for_reverse(lookup)` (added in U3) that returns `dict[str, list[tuple[str, id]]]` keyed by file string. Look up `decoded_path` in it.
     - **Chunk path (local or remote):** call `_load_index(args)`, find the file index for `decoded_path` via `files.index(decoded_path)` wrapped in `try/except ValueError`. If not present, treat as miss. If present, fetch `path_to_bindings[file_idx]` (a list of `(anchor_idx, id)` pairs); resolve anchor strings via `anchors[ai]` for the output.
  4. Apply filters in order: `--anchor` keeps only entries whose anchor string equals `args.anchor`; `--first` keeps only entries whose anchor string equals `""`. If the filter leaves the result empty (and the path itself was found), exit `1` with a flag-specific stderr message:
     - `--anchor <X>` and no match → `f"path found but no anchor binding matches: {decoded_path} (--anchor {args.anchor})"`
     - `--first` and no page-level row → `f"path found but no page-level binding; re-run without --first to see anchor-level bindings: {decoded_path}"`
     - Bare query and path not in index → `f"path not in index: {decoded_path}"`
  5. On success, print results:
     - Bare output: one ID per line, sort order already established by U1 (`(anchor_index, id)`).
     - `--json` output: `{"path": decoded_path, "matches": [{"id": ..., "anchor": ...}, ...]}`. On failure paths (`1`), JSON shape is `{"path": decoded_path, "matches": [], "error": "<reason>"}`. The `error` string is the same as the bare-mode stderr message above. **Covers R5.**
  6. Exit `0` on at least one match, `1` on no match.
- Hook `cmd_reverse` into the `if args.command == ...` dispatch in `main()`.
- **R7 path-normalization stance:** the handler does not normalize separators or strip `./` or resolve `..`. Document the contract in the subparser's `help=` string ("exact-match after percent-decoding") so it surfaces in `--help` output.
- **R8 file-component contract:** the handler does not pre-split on `#`. If the caller passes `Group/page.html#wwp100` as the path, the lookup against the `f` array misses (because the chunk stored the file without the anchor); the bare-mode error is the usual "path not in index" message, and the caller can re-run with `--anchor wwp100` and the bare path. Document this in the subparser help.

**Patterns to follow:**

- `cmd_resolve` is the closest existing analog for the source-flag + `--json` shape — see `resolve-landmarks.py:961-974`.
- The percent-decoding logic in `cmd_rewrite:983-988` is the canonical pattern; reuse `urllib.parse.unquote(..., errors='strict')` and the same error message shape.
- `_require_source(args, allow_autoinfer=False)` already gates the "no source" path with the right error message; reuse it.

**Test scenarios:**

- *CLI.* `test_cli_reverse_multi_binding_default_order` over the multi-chunk fixture: `reverse "groupA/page.html" --from tests/fixtures/` → stdout lists every ID in `(anchor_index, id)` order, exit `0`. **Covers AE1.**
- *CLI.* `test_cli_reverse_anchor_filter` over the multi-chunk fixture: `reverse "groupA/page.html" --anchor "wwp_a1" --from tests/fixtures/` → stdout is `common_id`, exit `0`. **Covers AE2.**
- *CLI.* `test_cli_reverse_first_flag` over `single-chunk_lx.js`: `reverse "Group/page.html" --first --from <fixture>` → stdout is the page-level ID (`page-only-id`), exit `0`. **Covers AE3 happy path.**
- *CLI.* `test_cli_reverse_first_flag_no_page_level` against a path that has only anchor-level bindings: `reverse "Group/other.html" --first --from <fixture>` → exit `1`, stderr names the path and explains the empty-anchor row is missing. **Covers AE3 failure path.**
- *CLI.* `test_cli_reverse_json_default` and `test_cli_reverse_json_no_match` exercising both the `matches` and the `matches: []` + `error` shapes. **Covers AE4.**
- *CLI.* `test_cli_reverse_unicode_path_raw_and_encoded` over `unicode-ids_lx.js`: both `reverse "Advanced Customizations/_xslt-extensions.04.1.html" --from <fixture>` and `reverse "Advanced%20Customizations/_xslt-extensions.04.1.html" --from <fixture>` return the same ID set including `概要`. **Covers AE5.**
- *CLI.* `test_cli_reverse_first_and_anchor_mutex` — argparse exits `2` when both flags are passed. **Covers R4's mutex clause and AE3's mutual-exclusion mention.**
- *CLI.* `test_cli_reverse_anchor_empty_rejected` — argparse-level `parser.error` exits `2` with the "use --first" guidance string.
- *CLI.* `test_cli_reverse_malformed_percent_exits_1` — input path `Bad%ZZName.html` exits `1` with the malformed-percent error message.
- *CLI.* `test_cli_reverse_path_not_in_index` — `reverse "doesnotexist.html" --from <fixture>` exits `1` with the bare-mode error message; the JSON variant has `matches: []` and the same `error` string.

**Verification:**

- All new scenarios PASS. No existing scenario regresses.
- `python plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py reverse --help` shows the new subcommand, the source-flag block (`--from`, `--remote-base-url`, `--lookup-table`), and the three reverse-specific flags (`--first`, `--anchor`, `--json`).

---

### U3. Lookup-table consumer path for `reverse`

**Goal:** Allow `reverse` to read a pre-built `format_version: 1` dump artifact without a schema change. Build the inverted `path → [(anchor, id), ...]` map in-memory on first lookup; the resulting query path is O(1) per path.

**Requirements:** R11, R12.

**Dependencies:** U2 (the `reverse` handler is where the inversion is invoked).

**Files:**

- `plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py` — add `_invert_lookup_for_reverse(lookup)` helper near `resolve_id_from_lookup`.

**Approach:**

- Add `_invert_lookup_for_reverse(lookup: dict) -> dict[str, list[tuple[str, str]]]`. Walks `lookup['landmarks']` once: for each `(id, {file, anchor})`, append `(anchor, id)` to `result.setdefault(file, [])`. After the walk, sort each value list by `(anchor, id)` so the empty-anchor entry sorts first and ties on `anchor` resolve deterministically. Total cost: one walk of the artifact's `landmarks` dict, equivalent to `len(landmarks)` appends + one sort per file.
- Why no schema change: R11's outcome is identical to what U1 produces from chunks, just derived from the already-loaded forward map. Bumping `format_version` to bundle a precomputed reverse map would (a) double the artifact size, (b) break every existing committed lookup-table (including `tests/fixtures/epublisher-designer-2026.1-help-lookup.json`), and (c) pay for an optimization no measured workload has demanded — the load-time inversion is one pass over a dict that's already in memory.
- Why not memoize across queries: `cmd_reverse` is invoked once per process. Memoization across `subprocess` invocations would require a disk cache, which is overkill for a load-time inversion that scales linearly with the artifact size already in memory.

**Patterns to follow:**

- `resolve_id_from_lookup(landmark_id, lookup)` (`resolve-landmarks.py:261-266`) is the existing single-purpose lookup-table accessor. The new helper sits next to it and follows the same "operate on the loaded dict" contract.

**Test scenarios:**

- *Internal.* `test_internal_invert_lookup_for_reverse` builds an inversion from the committed `epublisher-designer-2026.1-help-lookup.json` artifact and asserts: (a) every file appearing in `landmarks[].file` is a key in the inverted map; (b) every `(file, anchor)` pair in the forward map has a corresponding `(anchor, id)` entry in the inverted map's value list; (c) value lists are sorted.
- *CLI parity (lookup-table vs chunks).* Added in U4's parity block — see R15. Listed here for traceability: every reverse scenario from U2's CLI block re-runs with `--lookup-table <dumped.json>` and produces byte-identical output.

**Verification:**

- The internal-test scenario PASSes.
- U4's parity block (below) PASSes.

---

### U4. Verifier scenarios: reverse-lookup coverage, round-trip, lookup-table parity

**Goal:** Add the test coverage the brainstorm calls for: per-flag coverage (R13), forward-then-reverse round-trip (R14), and lookup-table parity (R15).

**Requirements:** R13, R14, R15 (covers AE1–AE7).

**Dependencies:** U2 (subcommand) and U3 (lookup-table inversion).

**Files:**

- `plugins/webworks-claude-skills/skills/reverb2/tests/verify-landmark-resolver.py` — append new test functions; register them in `main()`.

**Approach:**

- Add the per-scenario tests enumerated in U2's "Test scenarios" block (the implementer writes them as `check(...)` calls in the existing pattern).
- Add `test_cli_reverse_forward_round_trip` (R14, AE7):
  - Build the merged fixture index once via `subprocess` (`dump --from tests/fixtures/ --out tmp.json`).
  - Load the dumped JSON; for each `(id, {file, anchor})`, run the CLI `resolve <id> --from tests/fixtures/` to get the resolved path `P`. Split `P` on the first `#` to get the file portion `F`. Run `reverse <F> --from tests/fixtures/` and assert `id` is in the resulting line set.
  - On any failure, the verifier `FAIL`s with the offending `id`, `path`, and `reverse`-output as the detail string.
  - Performance note: for the 4-fixture set (~10 IDs), this is well under one second. The implementer can keep the loop inside one `tempfile.TemporaryDirectory()` block.
- Add the lookup-table parity block (R15, AE6):
  - `test_cli_reverse_lookup_parity` dumps the multi-chunk + unicode fixtures to a temp artifact, then re-runs each reverse scenario from U2 with `--lookup-table <dumped.json>` and compares stdout to the chunk-source variant.
  - Because the per-scenario tests in U2 read fixtures directly, the parity test re-issues each CLI call with both source modes and asserts `stdout_chunks == stdout_lookup`. Implementation: small helper `_assert_reverse_parity(temp_dump_path, args_excluding_source, expected_stdout)` keeps the per-scenario boilerplate tight.
- Register each new test function in `main()` (the `# CLI: reverse subcommand` section, added after the existing `# CLI: dump artifact + --lookup-table consumer path` block).

**Patterns to follow:**

- `test_cli_resolve_*` — see the existing functions in `verify-landmark-resolver.py` lines 600-800 (approximate) — for the `run_cli(...)` invocation and the `check("...", proc.returncode == 0, ...)` pattern.
- `test_cli_round_trip_equivalence_*` (already present in the verifier) — for `tempfile.TemporaryDirectory()` usage and the per-fixture comparison pattern.

**Test scenarios:**

Test expectation: every new scenario should PASS on first run after U1, U2, U3 are merged.

**Verification:**

- `python plugins/webworks-claude-skills/skills/reverb2/tests/verify-landmark-resolver.py` prints zero `FAIL`s and exits `0`.
- The `Summary:` line shows the new total count (existing count + every scenario added above).

---

### U5. Update `workflows/landmark-resolution.md`

**Goal:** Cover the `reverse` subcommand in the workflow document so first-time users see all four subcommands on one page.

**Requirements:** R16, R17 (covers AE8).

**Dependencies:** U2, U3 (the surface must exist for the doc to describe it).

**Files:**

- `plugins/webworks-claude-skills/skills/reverb2/workflows/landmark-resolution.md` — add Step 2 table row, new Step 7 section, two worked examples.

**Approach:**

- **Step 2 subcommand table** — add a `reverse <path>` row between `dump` and the flag-category table. Body: "A file path (raw or percent-encoded) → landmark ID(s) bound to that path, one per line. Add `--first` for the page-level binding only (runtime `GetIdByPath` shape), `--anchor <id>` to target a specific anchor, `--json` for `{path, matches}` output."
- **Step 2 flag table** — add rows for `--first` (subcommand: `reverse`, default: off, description: "Return only the page-level (empty-anchor) ID — runtime `GetIdByPath` shape"), `--anchor <id>` (subcommand: `reverse`, default: —, description: "Return only the binding for this specific anchor"), and `--json` for `reverse` (note that `--json` already has a row for `resolve`; extend the "Subcommands" column to `resolve, reverse`).
- **New Step 7: Reverse Lookup — Find IDs That Target a Path** — modeled on Step 6 structure. Sections:
  - Two-sentence intro framing the URL-minting and link-audit workflows.
  - Bare invocation example: `python scripts/resolve-landmarks.py reverse "Group/page.html" --from ./help-mirror/` with expected output (the multi-binding line listing).
  - `--first` and `--anchor` examples (one each) showing the runtime-parity shape and the targeted-anchor shape.
  - `--json` shape example.
  - Multi-binding ordering note: "Output is sorted by `(anchor_index, landmark_id)`. The empty-anchor (page-level) binding, when present, is emitted first."
  - Unicode note: "The input path is `urllib.parse.unquote`'d once. Raw and percent-encoded forms of the same path return the same IDs."
  - Anchor-collision footnote: "Anchor strings are not globally unique. `reverse <path> --anchor <id>` and `reverse <other-path> --anchor <id>` can resolve to different landmark IDs — anchors are scoped to their file." (Addresses the brainstorm's R3 second open question.)
- **Worked example: minting a stable URL from a known file path** (R17 first half). The link-audit example (R17 second half) shows a one-liner that iterates `reverse` over a small path list against `--lookup-table tests/fixtures/epublisher-designer-2026.1-help-lookup.json`, demonstrating the O(1)-per-query composition.
- **Step 5 exit-code table** — add a parenthetical note to the `1` row: "Also: `reverse` path not in index, `--anchor` not bound on the path, `--first` and no page-level binding."
- **Success criteria block** — add a checkbox: `[ ] If reverse-looking up a path, the chosen output mode (default, --first, --anchor) matches the workflow (audit vs. URL-mint).`

**Patterns to follow:**

- Step 6 structure (the same file, lines 152-166) — sentence intro + fenced bash blocks + commentary line — is the model for Step 7.
- The Step 2 flag table already mixes "all" / "all (remote only)" / specific subcommands in its "Subcommands" column; the `reverse`-specific flags follow the same convention.

**Test scenarios:**

Test expectation: none — this is documentation. Verification is by reading the file against the requirements.

**Verification:**

- The new Step 7 exists and contains: (a) the URL-mint worked example with a known file path → stable URL, (b) the link-audit worked example with `--lookup-table`, (c) the multi-binding ordering note, (d) the Unicode note, (e) the anchor-collision footnote.
- Step 2's subcommand table has a `reverse <path>` row.
- Step 2's flag table covers `--first`, `--anchor`, and `--json` (for `reverse`).
- Step 5's exit-code table mentions the `reverse`-specific failure modes under exit `1`.

---

### U6. Bump plugin version

**Goal:** Apply the repo-mandated version bump for an additive feature.

**Requirements:** Project convention (per `CLAUDE.md`: "minor: new skills, new features").

**Dependencies:** U1–U5 (the feature must exist before it ships).

**Files:**

- `plugins/webworks-claude-skills/.claude-plugin/plugin.json` — version field.
- `.claude-plugin/marketplace.json` — version field.

**Approach:**

- Run `scripts/bump-version.sh minor`. The script reads `plugin.json`, increments minor (2.13.0 → 2.14.0), zeros the patch, and writes the same version back into both `plugin.json` and `marketplace.json`. This is the documented workflow.
- Do not hand-edit the JSON files.

**Patterns to follow:**

- `scripts/bump-version.sh minor` is the canonical bump path used by recent feature commits in `git log`.

**Test scenarios:**

Test expectation: none — metadata bump. Verification is by diff.

**Verification:**

- Both manifest files report `"version": "2.14.0"`.
- `git diff --stat` shows changes only to the two manifest files (plus the U1–U5 files).

---

## Scope Boundaries

### In scope

- New `reverse <path>` subcommand with `--first`, `--anchor`, `--json` flags.
- Reverse map built in `_merge_chunks` for both `--from` and `--remote-base-url` source modes.
- Lookup-table inversion on first query for the `--lookup-table` source mode.
- Verifier coverage for all flag combinations, the forward-then-reverse round-trip, and lookup-table parity.
- Workflow documentation: Step 2 table row, new Step 7 section, two worked examples.
- Minor version bump.

### Out of scope

- **Fuzzy, substring, or glob path matching.** Reverse lookup is exact-string equality after percent-decoding. (Origin scope boundary; reaffirmed at planning time.)
- **Modifying the Reverb runtime.** `landmarks.js` is unchanged. (Origin scope boundary.)
- **Enriching reverse-lookup output with anchor heading text.** Anchor labels live in rendered HTML; joining them in would require fetching and parsing every output HTML file. (Origin scope boundary.)
- **`format_version: 2` dump artifact with a precomputed reverse map.** U3 inverts the existing v1 artifact on load. (Origin scope boundary; planning-time decision in "Key Technical Decisions".)
- **Programmatic Python API.** The surface is CLI-only, matching the rest of `resolve-landmarks.py`. (Origin scope boundary.)
- **`dump --reverse` or alternate-shape dump.** Reverse queries go through `reverse <path>`. (Origin scope boundary.)
- **Path-separator normalization (`/` vs `\`), leading `./` stripping, `..` resolution.** R7 explicitly rejects these. (Origin scope boundary.)
- **Applying the skill to other repos' help mirrors in this PR.** That's downstream usage, not part of the feature.

### Deferred to Follow-Up Work

- **`--normalize-separators` flag.** If a real Reverb output surfaces mixed `/` and `\` paths in `f`, a follow-up issue adds the flag (off by default). The Open Question in the brainstorm's "Genuinely uncertain" block tracks this.
- **Anchor-text legibility join.** If a concrete consumer needs human-readable anchor labels in `reverse` output, a follow-up issue scopes the HTML-side join (likely via `_lx-search.js` companions where present).
- **Memoized cross-process lookup-table inversion.** If reverse-lookup workloads against a 50k-ID artifact become hot, a future issue can ship a disk-cached inverted map keyed by the artifact's content hash. Not needed for any current workload.

## Risks

- **Risk: `_merge_chunks` signature change breaks downstream callers.** The function is module-private (leading underscore) and called only from `build_index` / `build_index_from_texts`, both of which are updated in U1. Verified by `Grep` at planning time — no other callers exist in the repo. Low likelihood, low impact.
- **Risk: forward-then-reverse round-trip in U4 is slow on the committed lookup-table fixture.** The fixture is the ePublisher Designer 2026.1 help artifact, which has hundreds-to-low-thousands of IDs. If iterating `subprocess.run` per ID becomes painful, the round-trip is restricted to the small in-tree `*_lx.js` fixtures (which the brainstorm's R14 explicitly references) and the lookup-table parity scenarios (R15) cover the larger artifact at the bulk-comparison level. Medium likelihood (size unverified at planning), low impact (the mitigation is part of the U4 plan).
- **Risk: the brainstorm's "anchor index 0 == empty anchor" assumption fails on some real chunk.** Mitigated by U1's `(anchor_index, landmark_id)` sort key, which is stable regardless of the empty-string intern index, plus U2 filters `--first` on the empty *string* (not the index). Low likelihood, low impact — the workflow doc's "empty-anchor binding first" wording is anchor-string-based, not intern-index-based.
- **Risk: `--anchor` semantics surprise callers who expected `--anchor ""` to be page-level.** Mitigated by the argparse-time rejection with a "use --first" message (Key Technical Decisions). Low likelihood, low impact — the error message itself is the affordance.

## Final Checks

Before commit:

- [ ] `python plugins/webworks-claude-skills/skills/reverb2/tests/verify-landmark-resolver.py` exits `0` and reports zero `FAIL`s.
- [ ] `python plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py reverse --help` shows the new subcommand and all three reverse-specific flags.
- [ ] `python plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py --help` lists `reverse` alongside `resolve`, `rewrite`, `dump`.
- [ ] Workflow doc renders cleanly: Step 2 table includes `reverse`, Step 7 exists, both worked examples are present, exit-code table covers reverse-specific failure modes.
- [ ] `plugin.json` and `marketplace.json` both report `"version": "2.14.0"`.
- [ ] No unrelated files changed.
- [ ] Commit uses conventional commit format (`feat:`) per repo `CLAUDE.md`.
