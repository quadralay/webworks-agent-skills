---
date: 2026-05-22
topic: reverb-landmark-reverse-lookup
issue: 78
---

# Reverb Landmark Resolver — Reverse Lookup (`path → id`)

## Summary

Extend `plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py` with a `reverse <path>` subcommand that returns the landmark ID(s) bound to a given file path, optionally narrowed to a specific anchor. The new subcommand reads the same `(files, anchors, id_to_pair)` index the existing `resolve` / `rewrite` / `dump` subcommands consume, so it composes with every source mode the resolver already supports — local chunks (`--from`), remote mirror (`--remote-base-url`), and pre-built lookup table (`--lookup-table`). Update `workflows/landmark-resolution.md` to cover the new subcommand and its multi-binding semantics.

---

## Problem Frame

`scripts/resolve-landmarks.py` today answers the forward question: **"given a stable landmark ID, what file (and anchor) does it resolve to?"** That direction handles the "agent receives a stable URL, needs the direct file URL" workflow that motivated issue #54 and was extended to remote sources in #76 and to pre-built artifacts in #77.

A second family of workflows asks the **inverse** question and currently has no tool support:

1. **Stable-URL minting.** An agent or skill has produced or located a specific file path — from a sitemap, a search result, a citation, or a manual browse — and wants to share a stable `<prefix>#/<id>` URL that survives future help reorganizations. Without reverse lookup, the agent has to dump the whole index and grep the value side, which neither composes cleanly nor uses the contract the runtime already implements.
2. **Link audits.** When checking whether a documentation restructure will break references in skill docs or customer-facing material, the question "which stable IDs currently point at this page?" needs a direct answer. Today the only way is to dump the index and post-process it.
3. **Anchor citations.** Given a heading on a page, the agent wants the specific stable ID that targets that anchor so it can be embedded as a citation or quote anchor. Forward resolution does not surface this; the data is present in the `e` arrays but is unreachable through the CLI.

The underlying data already supports the inverse direction: the resolver's `build_index` (and the runtime's `Landmarks.Advance`) walks the same `e` rows that bind `(file_index, anchor_index) → id`. The runtime persists this as `pairToId` keyed by `"fileIndex|anchorIndex"` (see issue #77's notes from runtime verification). The forward map is just one projection of the same data; the reverse map can be built from the same chunk pass at zero additional parse cost.

Three concrete gaps in the current resolver:

1. **No `reverse` (or equivalent) CLI surface.** `resolve`, `rewrite`, and `dump` cover the forward and bulk-export cases. None of them answers "given a path, what IDs target it?" without an out-of-band post-processing step.
2. **No `--anchor` disambiguator.** A single page can host multiple landmarks (one page-level binding plus one per anchor). The reverse-lookup primitive needs a way to ask for "the ID for this specific anchor on this page" without filtering the full result set in calling code.
3. **No defined multi-binding output contract.** When a path has multiple IDs bound to it (the typical case: page-level row plus one or more anchor rows), the tool must agree with itself on ordering and grouping. The runtime's `GetIdByPath` returns only the page-level (empty-anchor) binding; richer multi-binding output is a CLI design decision this brainstorm makes.

The 2026-05-20 runtime verification notes embedded in the issue body also surface Unicode handling on both sides of the lookup: source IDs can be raw Unicode NCNames (`概要`, `übersicht`) and file paths can contain non-ASCII characters that get URL-encoded for browser navigation. Reverse lookup must accept both raw and percent-encoded input paths and yield the same result.

---

## Requirements

**Reverse-lookup subcommand surface**

- R1. Add a new subcommand `reverse <path>` to `plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py` alongside `resolve`, `rewrite`, and `dump`. The subcommand takes a positional `path` argument and the same mutually-exclusive `--from` / `--remote-base-url` / `--lookup-table` source flags as the other subcommands (including the existing remote-mode flags `--no-cache`, `--cache-ttl`, `--cache-dir`, `--http-timeout`).
- R2. `reverse <path>` defaults to returning **all** landmark IDs bound to that path, in stable order (anchor index ascending, with the empty-anchor / page-level binding emitted first). One ID per line on stdout. Exit code `0` on at least one match; exit code `1` on no match.
- R3. Add `--anchor <anchor-id>` to filter the result set to the single binding whose anchor (in the chunk's `a` array) matches the supplied string. When the path-and-anchor combination resolves, exit `0` and print the single ID. When the path resolves but the specific anchor is not bound on it, exit `1` with a stderr message that names the path and the anchor.
- R4. Add `--first` to return only the page-level (empty-anchor) ID for the path — matching the runtime's `GetIdByPath` shape. When the page-level binding exists, exit `0` and print the single ID. When the path exists in the index but has no page-level (`anchor == ""`) binding, exit `1` with a stderr message that explains the path has only anchor-level bindings and the caller can re-run without `--first` to see them. `--first` and `--anchor` are mutually exclusive (argparse-level error).
- R5. Add `--json` to `reverse` mirroring `resolve --json`. The JSON shape is `{"path": "<input>", "matches": [{"id": "<id>", "anchor": "<anchor>"}, ...]}` — `matches` is always a list (even with `--first` or `--anchor`, where it has at most one element), so consumers do not have to branch on shape. On exit `1` (no match), the JSON is `{"path": "<input>", "matches": [], "error": "<reason>"}`.

**Input path normalization**

- R6. Accept the path argument in either raw form (the form that appears verbatim in the chunk's `f` array) or percent-encoded form (the form that appears in browser URLs, e.g. `Advanced%20Customizations/_xslt-extensions.04.1.html`). The resolver applies `urllib.parse.unquote(..., errors='strict')` to the input before lookup, mirroring the same Unicode-decoding step `rewrite` already performs on the ID side of stable URLs. Malformed percent-encoding exits `1` with a clear stderr message.
- R7. Do **not** attempt further path normalization. Specifically: do not canonicalize separators (`/` vs `\`), do not strip leading `./`, do not resolve `..`. The runtime's `GetIdByPath` does straight equality matching against the keys in `f`; the resolver matches the runtime contract. Any normalization beyond percent-decoding belongs in calling code, not in the tool.
- R8. The path is matched against the **file** component only — the portion before any `#` in the chunk's stored form (the runtime's `splitPath` separates `file` from `anchor` at the first `#`). The resolver's index already stores file and anchor as separate strings, so this falls out of the lookup; the requirement names the contract so the workflow doc and the JSON shape are unambiguous.

**Index construction**

- R9. Extend `_merge_chunks` (or add a thin sibling) so that, in addition to the existing `id_to_pair: dict[str, tuple[int, int]]`, the merge produces a `path_to_bindings: dict[int, list[tuple[int, str]]]` keyed by `file_index` whose values are lists of `(anchor_index, landmark_id)` pairs. The list is sorted by `anchor_index` ascending (so the empty-anchor binding, anchor index `0` when present, comes first). Last-write-wins for duplicate `(file_index, anchor_index)` pairs, matching the runtime's `Landmarks.Advance` semantics already documented in the forward direction.
- R10. The reverse map is built in the same pass as the forward map — no extra chunk parse, no second discovery of chunk files. Building it costs one extra append per `e` row processed; total memory cost is proportional to the number of entries already in `id_to_pair`.

**Lookup-table integration**

- R11. The `--lookup-table` consumer path supports `reverse` without changing the `format_version: 1` artifact schema. When a `reverse` query lands against a lookup table, the resolver inverts the `landmarks` map on load: it walks the `{id: {file, anchor}}` entries once and builds an in-memory `path_to_bindings: dict[str, list[tuple[str, str]]]` keyed by `file` whose values are `(anchor, id)` pairs sorted by anchor (empty anchor first, then by Unicode codepoint order). Subsequent queries are O(1) per path.
- R12. The lookup-table source for `reverse` produces byte-identical output to the equivalent `--from` or `--remote-base-url` source query, given the same underlying chunks. Coverage is in the verifier (see R15).

**Verification**

- R13. Extend `plugins/webworks-claude-skills/skills/reverb2/tests/verify-landmark-resolver.py` with scenarios covering: (a) page-level binding only (`--first` and default both return the same single ID); (b) multi-binding (page-level plus two anchor-level bindings — default returns three IDs in stable order, `--anchor` filters to one, `--first` returns just the page-level); (c) path not in index (exit `1` with appropriate stderr); (d) `--anchor` for an anchor not bound on the path (exit `1` with anchor-specific stderr); (e) Unicode path round-trip (raw and percent-encoded inputs return the same IDs, and at least one of the IDs returned is itself a Unicode NCName from the `unicode-ids_lx.js` fixture); (f) `--first` + `--anchor` mutual exclusion (argparse exits `2`).
- R14. Add a forward-then-reverse round-trip scenario: for every ID `X` in the merged fixture index, `resolve X` returns a path `P` (possibly with `#anchor`); then `reverse <file portion of P>` returns a set that includes `X`. The scenario splits `file#anchor` on the first `#` (mirroring the runtime's `splitPath`) before feeding the file portion to `reverse`.
- R15. Add a lookup-table parity scenario: dump the `multi-chunk-*_lx.js` and `unicode-ids_lx.js` fixtures to a JSON artifact, then run every `reverse` scenario from R13 and R14 against both the chunk source and the lookup-table source; outputs must match line-for-line.

**Workflow documentation**

- R16. Update `plugins/webworks-claude-skills/skills/reverb2/workflows/landmark-resolution.md` to cover the `reverse` subcommand: add a row to the Step 2 subcommand table; add a new Step 7 ("Reverse Lookup: Find IDs That Target a Path") modeled on the existing Step 6 structure; document the `--first` / `--anchor` / `--json` flag semantics in the flag table; add a worked example that mints a stable URL from a known file path.
- R17. Add at least one worked example to the new Step 7 that exercises the link-audit workflow: dump the index once, then iterate `reverse` over a small list of paths to surface every ID that currently targets each page. The example uses `--lookup-table` for the iteration to demonstrate the O(1)-per-query composition.

---

## Acceptance Examples

- AE1. **Covers R1, R2.** Given the multi-chunk fixture set (`multi-chunk-a_lx.js`, `multi-chunk-b_lx.js`), when the user runs `python resolve-landmarks.py reverse "groupA/page.html" --from tests/fixtures/`, then stdout lists every landmark ID bound to `groupA/page.html` in anchor-index-ascending order (page-level binding first when present), exit code is `0`, and stderr is empty.
- AE2. **Covers R3.** Given the same fixture, when the user runs `... reverse "groupA/page.html" --anchor "wwp_a1" --from tests/fixtures/`, then stdout prints the single ID `common_id` (the row `[1, 1, "common_id"]` in `multi-chunk-a_lx.js`), and exit code is `0`.
- AE3. **Covers R4.** Given a page with both a page-level binding and an anchor-level binding (e.g., `Group/page.html` in `single-chunk_lx.js`), when the user runs `... reverse "Group/page.html" --first --from tests/fixtures/`, then stdout prints the single page-level ID and exit code is `0`. When the user runs the same against a path that exists in the index but has no anchor-`""` row, then exit code is `1` and stderr names the path and explains the empty-anchor binding is missing.
- AE4. **Covers R5.** Given any of the above scenarios with `--json` appended, when the command runs, then stdout is a JSON object with keys `path` and `matches` (a list of `{id, anchor}` objects), and the exit code is unchanged from the non-`--json` form.
- AE5. **Covers R6, R7, R8.** Given the `unicode-ids_lx.js` fixture with `"f": ["Advanced Customizations/_xslt-extensions.04.1.html"]`, when the user runs `... reverse "Advanced%20Customizations/_xslt-extensions.04.1.html" --from tests/fixtures/` (percent-encoded) and `... reverse "Advanced Customizations/_xslt-extensions.04.1.html" --from tests/fixtures/` (raw), then both invocations return the same ID set including `概要`.
- AE6. **Covers R11, R12, R15.** Given a lookup-table artifact dumped from the multi-chunk and unicode fixtures, when every reverse-lookup scenario is run twice — once with `--from tests/fixtures/` and once with `--lookup-table <dumped.json>` — then the two output sets are byte-identical (modulo `captured_at` differences inside any subsequent dumps).
- AE7. **Covers R14.** Given the merged fixture index, when the verifier runs the forward-then-reverse round-trip across every ID, then for each ID `X` resolved to path `P` (possibly `file#anchor`), `reverse <file portion of P>` returns a set that includes `X`; if any ID is missing from its reverse-lookup set, the verifier FAILs with the offending ID and path.
- AE8. **Covers R16, R17.** Given a developer landing on `workflows/landmark-resolution.md` looking for "how do I find the stable ID for a page I already have," when they scan the subcommand table in Step 2, then they find a `reverse <path>` row that points at Step 7; when they read Step 7, then they find a worked example that mints a stable URL from a known file path and a second example that audits a list of paths via `--lookup-table`.

---

## Success Criteria

- A skill author or agent with a known file path can mint the stable URL for that page (or for a specific anchor on it) in a single resolver invocation, without dumping the index and post-processing it.
- The reverse-lookup primitive composes with every source mode the forward resolver already supports — local, remote, and lookup-table — without any source-mode-specific code paths in calling tools.
- Multi-binding paths produce a deterministic, documented output order, so callers writing scripts against `reverse` do not have to invent ordering rules.
- The forward and reverse directions agree: any ID returned by the existing `resolve` subcommand for a given input is reachable in the opposite direction by passing the file portion of `resolve`'s output to `reverse`.
- Unicode handling is uniform across both directions: a path with non-ASCII characters round-trips raw and percent-encoded; an ID with raw Unicode (`概要`) surfaces in `reverse` output without escaping.
- The `--lookup-table` consumer path serves `reverse` queries with no schema change to the v1 dump artifact, so existing committed lookup tables continue to work after this change merges.
- The workflow doc gives a first-time reader a single page that covers all four subcommands (`resolve`, `rewrite`, `dump`, `reverse`) and explains when to use each — no separate reference file required.

---

## Scope Boundaries

- **Not adding fuzzy, substring, or glob path matching.** Reverse lookup is exact string equality after percent-decoding. Substring matching, `did you mean`-style suggestions, and glob support are downstream concerns.
- **Not modifying the Reverb runtime.** The runtime's `GetIdByPath` is unchanged. This issue extends the JS-less mirror only.
- **Not enriching reverse-lookup output with anchor heading text.** The anchor labels (the human-readable headings that anchor IDs correspond to) live in the rendered HTML, not in `_lx.js`. Joining them in would require pulling and parsing every output HTML file — a much larger scope. The reverse-lookup output emits raw anchor IDs (`wwp100015` etc.); a future enhancement could resolve them against the published HTML if a concrete consumer surfaces.
- **Not changing the v1 lookup-table artifact schema.** R11 inverts the existing `landmarks` map on load. No `format_version: 2` is needed; no `pairToId` field is added. If reverse-lookup workloads become large enough that the load-time inversion is a real cost, a future schema-bumped artifact can ship a precomputed reverse map — but the v1 cost is one walk of an already-loaded dict, which is bounded by the artifact size.
- **Not exposing reverse-lookup as a Python API for in-process consumers.** Like the rest of `resolve-landmarks.py`, the surface is CLI-only. Programmatic consumers shell out or load the JSON artifact directly with `json.load`.
- **Not bumping the plugin version in the brainstorm artifact.** Version bump happens at PR time per `CLAUDE.md` instructions.
- **Not adding a `dump --reverse` or alternate-shape dump.** `dump` continues to emit the forward `{id: {file, anchor}}` map. Reverse-lookup queries either go through `reverse <path>` directly or are derived in calling code by inverting the existing dump output. A `--shape reverse` flag is overkill for a single primitive and would re-introduce the `--shape` design pressure the issue-77 brainstorm explicitly deferred.
- **Not exporting the in-memory `path_to_bindings` map.** It is an implementation detail of the `reverse` subcommand. Callers that need a full reverse map invert the existing `dump` output themselves (one Python `dict` comprehension).

---

## Key Decisions

- **Pick subcommand `reverse <path>` over `resolve --reverse <path>`.** The issue body lists both options. The subcommand form keeps each verb single-purpose — `resolve` answers `id → path`, `reverse` answers `path → id` — and parallels the existing `rewrite` and `dump` subcommands, both of which are dedicated verbs rather than flags on `resolve`. The flag form (`resolve --reverse`) would couple two opposite-direction lookups under one subcommand, expand `resolve`'s argument matrix, and make the `--from` / `--remote-base-url` / `--lookup-table` source flags do double duty with conflicting semantics depending on `--reverse`. The single-purpose subcommand is the same trade-off the resolver made in issue #54 when it picked `rewrite <url>` over `resolve --url <url>`.
- **Default behavior is "all bindings"; `--first` opts into runtime parity.** The issue's open design question proposes either "all" or "first" as the default. `reverse <path>` defaulting to all bindings is the strictly more general answer — link-audit and anchor-citation workflows need every binding, and `--first` cheaply downgrades to the runtime's `GetIdByPath` shape for callers who want only that. The runtime's `GetIdByPath` returning only the page-level ID is a side effect of `localStorage`'s persisted shape; mirroring it as the CLI default would silently drop information the user is asking for.
- **`--first` and `--anchor` are mutually exclusive.** Combining them either means "the page-level binding, but only if its anchor matches" (degenerate — the page-level binding's anchor is always `""`) or "the binding at this anchor, but only when it's first in the order" (degenerate — every anchor is at a unique position). Argparse rejection is the simplest signal that the combination is meaningless.
- **Sort multi-binding output by anchor index (chunk-array order), empty anchor first.** The runtime's `Landmarks.Advance` writes the page-level row first and anchor-level rows in subsequent order; chunk authoring tools emit anchors in declaration order, so anchor index `0` (empty) plus the natural authoring order yields the most-predictable output for human readers. Sorting by anchor *string* would surface alphabetic order, which is less faithful to how anchors are presented in the source documents.
- **Invert the lookup-table on load rather than bump the artifact schema.** v1 lookup-table artifacts already encode the bindings as `{id: {file, anchor}}`. A single pass over the artifact's `landmarks` dict produces the reverse map in O(n) time and O(n) memory. Bumping to `format_version: 2` to add a precomputed reverse map would double the artifact size (the runtime's `pairToId` is similar in size to `ids`), break every existing committed artifact, and pay for an optimization no measured workload has demanded. Load-time inversion is the right v1 trade.
- **Percent-decode input paths once, identically to how `rewrite` decodes IDs.** The forward path already calls `urllib.parse.unquote(..., errors='strict')` on the ID side of stable URLs to handle Unicode IDs. Mirroring the same single-step decode on the path side gives the same surface — callers can paste the path in whichever form they have it (browser URL, raw chunk-store form) and get the same answer.
- **Do not chase anchor-text legibility in v1.** Joining anchor IDs to their heading text requires fetching and parsing the rendered HTML (or `_lx-search.js` companions, where present), which is a separate tool's scope. Raw anchor IDs are still useful — they round-trip with `resolve --anchor`-style workflows and they match the IDs the runtime emits — and adding legibility later does not require a schema change.
- **No `dump --reverse` flag.** `dump` emits the canonical artifact; reverse queries go through `reverse`. Adding a second dump shape would re-open the `--shape` design pressure the issue-77 brainstorm explicitly deferred, for an output that a single-line `dict` comprehension can derive from the existing dump.

---

## Dependencies / Assumptions

- The resolver from #54, the remote-mode work from #76, and the structured-`dump` / `--lookup-table` work from #77 are all merged. Verified via `git log --oneline` showing `8bda19b Merge pull request #91 from quadralay/claude/issue-77`. The `blocked-by: #77` directive in the issue body is satisfied; nothing further blocks implementation.
- The resolver's `_merge_chunks` function is the single point of index construction for both `--from` and `--remote-base-url` source modes. Verified by reading `plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py` (`build_index` and `build_index_from_texts` both delegate to `_merge_chunks`). Extending it to also produce the reverse map covers both source modes in one change.
- The runtime's `Landmarks.Advance` last-write-wins semantics are already mirrored in `_merge_chunks` for the forward direction. The reverse direction inherits the same correctness property by walking the same rows in the same order — no separate runtime-parity verification is required beyond R14's forward-then-reverse round-trip.
- The fixture suite under `tests/fixtures/` (`single-chunk_lx.js`, `multi-chunk-a_lx.js`, `multi-chunk-b_lx.js`, `unicode-ids_lx.js`) covers the binding shapes the reverse subcommand needs to verify: page-level only, page-level plus anchor-level, multi-anchor, and Unicode IDs. Verified by reading the fixtures. No new fixture authoring is required for R13's core scenarios; R17's worked example may pull from the committed ePublisher Designer 2026.1 lookup-table fixture for realism.
- The standalone verifier (`tests/verify-landmark-resolver.py`) is the canonical test harness. No pytest infrastructure exists; new scenarios go in as PASS/FAIL `check(...)` calls in the same shape as the existing 80+ scenarios.
- The workflow doc at `plugins/webworks-claude-skills/skills/reverb2/workflows/landmark-resolution.md` is the user-facing documentation for the resolver. R16 updates it; no other documentation entry-point exists for resolver users.

---

## Outstanding Questions

### Resolvable at planning time

- [Affects R2, R5] [Technical] Decide the stdout format for the default (multi-binding, no `--first` / `--anchor`) case. Two options: (a) one ID per line, bare — composes cleanly with `xargs` and other line-oriented tools; (b) one row per line as `<anchor>\t<id>` — preserves the anchor metadata in non-JSON output. This brainstorm's default is (a) for consistency with `resolve`'s bare-path output; if planning decides (b) is materially more useful for the link-audit workflow, the JSON shape in R5 stays unchanged and only the bare output changes.
- [Affects R3] [Technical] Decide the semantics of `--anchor ""`. Three options: (a) treat empty-string `--anchor` as equivalent to `--first` (return only the page-level binding); (b) reject it at argparse (use `--first` instead); (c) accept it literally and return the binding whose anchor equals the empty string (which is option (a) by another name). Planning picks the option that produces the clearest stderr message when callers get it wrong.
- [Affects R9, R11] [Technical] Decide whether `path_to_bindings` is built eagerly in `_merge_chunks` (paying the cost on every invocation, even `resolve` which does not use it) or lazily on first `reverse` call (one branch in `_merge_chunks` keyed by the active subcommand). Eager is simpler; lazy avoids the extra dict for the dominant forward-resolution case. Planning weighs by the measured cost on a 5000-ID artifact — if eager construction adds < 5 ms to a forward `resolve`, do it eagerly for code simplicity.
- [Affects R16, R17] [Editorial] Decide the section heading for the new workflow step. Options: `## Step 7: Reverse Lookup — Find IDs That Target a Path`; `## Step 7: Path → ID Lookup`; `## Step 7: Mint Stable URLs from File Paths`. The first is most-discoverable for the audit workflow; the third is most-discoverable for the URL-minting workflow. Planning picks the form that scans best alongside the existing Step 6 heading.

### Genuinely uncertain — record as assumption

- [Affects R7] [Open] Whether any real Reverb output emits paths in the `f` array that contain characters needing normalization beyond percent-decoding — for example, mixed `/` and `\` separators on Windows builds, or paths containing a literal `#` character (which the runtime's `splitPath` would mis-segment). The brainstorm's Key Decision says "no normalization beyond percent-decoding" based on the existing fixtures. The first real-help dump run against `reverse` will either confirm that decision or surface a counterexample. If a path with mixed separators surfaces, planning revisits R7 and adds a `--normalize-separators` flag (off by default) rather than changing the runtime-mirror contract.
- [Affects R3] [Open] Whether any real Reverb output binds a single anchor string to multiple files (i.e., the same anchor name `wwp100` appearing on two different pages, each with its own landmark ID). The runtime's `pairToId` is keyed by `(file_index, anchor_index)`, so anchor collisions across pages are not a correctness issue — they are isolated by the file index. The reverse-lookup primitive inherits the same isolation: `reverse <path1> --anchor wwp100` and `reverse <path2> --anchor wwp100` resolve to different IDs. This is expected, but the workflow doc should call it out so callers do not assume anchors are globally unique.
