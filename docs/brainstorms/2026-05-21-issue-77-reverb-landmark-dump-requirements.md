---
date: 2026-05-21
topic: reverb-landmark-dump
issue: 77
---

# Reverb Landmark Resolver — Static Lookup-Table `dump` Output and `--lookup-table` Consumer Path

## Summary

Evolve the existing `dump` subcommand in `plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py` so it emits a structured, versioned, deterministic JSON lookup table (with embedded source metadata) suitable for pre-building and distributing alongside skills that resolve against well-known Reverb mirrors. Add a matching `--lookup-table <file>` resolution path on `resolve` and `rewrite` that consumes the dumped artifact instead of `_lx.js` chunks. Commit one real artifact (ePublisher Designer 2026.1 help) as a verification fixture and reference. Update `workflows/landmark-resolution.md` to cover the lookup-table consumer path.

---

## Problem Frame

Two distinct consumer shapes for Reverb landmark resolution exist today:

1. **Dynamic resolution** — `resolve-landmarks.py` parses `_lx.js` chunks on demand (`--from`) or fetches them over HTTP (`--remote-base-url`, added in #76). Right for ad-hoc or one-off queries.
2. **Bundled lookup** — a skill or tool that knows ahead of time it will resolve against a specific Reverb mirror (the help that ships with ePublisher Designer, for example) benefits from a pre-built JSON map: no chunk parsing at runtime, no dependency on the chunks being reachable, smaller distribution surface.

The resolver script's current `dump` subcommand already emits JSON, but its shape is a flat `{id: "file#anchor"}` map — minimum viable, not durable. Three concrete gaps:

1. **No format versioning.** A skill that pins to today's flat shape will silently break the day the schema evolves. There is no `format_version` field to gate on.
2. **No source provenance.** A committed artifact gives no answer to "which mirror did this come from?", "how many chunks contributed?", or "when was it captured?" — the questions a downstream reviewer or refresh tool needs.
3. **No structured `(file, anchor)` separation.** Consumers must re-split on `#` to extract anchors, duplicating string-handling rules the runtime already encodes (`GetPathById` formatting).

A fourth gap is on the consumer side: even with a perfect artifact, the resolver has no flag to consume it. A skill that wants to ship a baked lookup table still has to write its own JSON loader and lookup helper.

The issue body and the 2026-05-20 runtime verification notes also surface two design questions that this brainstorm should engage rather than defer:

- **Unicode source IDs.** Reverb 2026.1 emits source IDs that may be Unicode NCNames (`概要`, `übersicht`). The artifact must preserve them raw, not escape to `\uXXXX` or lossy-transcode.
- **Runtime-shape interop.** The runtime persists its in-memory state to `localStorage` in a normalized form (`v`, `f`, `a`, `ids`, `pairToId`). Mirroring that shape would let an artifact be loaded via DevTools to seed a session, but diverges from skill-friendly readability. The issue body recommends supporting both behind `--shape`.

---

## Requirements

**Dump subcommand surface**

- R1. Evolve the existing `dump` subcommand on `resolve-landmarks.py`. Add `--out <file>` so the artifact can be written to disk; when `--out` is omitted, continue writing to stdout (preserves current scripting use). Keep `--table` as the human-readable alternative; it is unaffected by this issue.
- R2. The default JSON output shape changes from the current flat `{id: "file#anchor"}` map to the structured, versioned shape documented in R3. Treat this as a breaking change to the `dump` JSON contract — the script's only published consumer is `workflows/landmark-resolution.md` (Step 6, optional bulk-rewrite recipe), which the implementation updates in the same change.
- R3. The structured JSON shape matches the schema below verbatim, with sorted `landmarks` keys and stable runtime "last-write-wins" binding for IDs that appear in multiple chunks:

   ```json
   {
     "format_version": 1,
     "source": {
       "type": "local-directory",
       "path": "<absolute or repo-relative path passed to --from>",
       "chunks_found": 7,
       "captured_at": "2026-05-20T15:00:00Z"
     },
     "landmarks": {
       "e5d3d31c42d8d1d4": {
         "file": "Advanced Customizations/_xslt-extensions.04.1.html",
         "anchor": ""
       }
     }
   }
   ```

- R4. **Determinism.** Two invocations of `dump` against the same input directory produce byte-identical output excluding `source.captured_at`. Sort `landmarks` keys; sort the in-memory `id_to_pair` traversal by stable rule that reproduces the runtime's last-write-wins semantics; do not pretty-print with platform-dependent line endings (use `"\n"` regardless of OS).
- R5. **Unicode preservation.** Emit Unicode landmark IDs and file/anchor strings as raw UTF-8 (`json.dumps(..., ensure_ascii=False)`). A landmark with the source ID `概要` appears literally as `"概要": {...}` in the artifact, not `"概要"`. Round-trip resolution against the artifact must return the same `file#anchor` the dynamic resolver would.
- R6. **Remote-mode dump.** Allow `dump --remote-base-url <url> --out <file>`. The `source` block becomes `{"type": "remote-base-url", "base_url": "<url>", "chunks_found": N, "captured_at": "..."}`. The existing remote cache layer (from #76) provides the chunks; no new HTTP code is needed.

**Consumer path on `resolve` and `rewrite`**

- R7. Add `--lookup-table <file>` to both `resolve` and `rewrite`. The flag is mutually exclusive with `--from` and `--remote-base-url` (extend the existing `_add_source_flags` mutually-exclusive group).
- R8. When `--lookup-table` is supplied, the resolver loads the JSON, validates `format_version == 1` (exit 2 with a clear message otherwise), and serves `resolve`/`rewrite` queries from the in-memory `landmarks` dict. Resolution is O(1) per query — no chunk parsing, no HTTP.
- R9. The `--lookup-table` path produces byte-identical resolved output to direct-chunk resolution. Specifically: anchor formatting (`file#anchor` when anchor is non-empty, bare `file` otherwise) and the `rewrite` percent-encoding rules for remote-mode prefixes are unchanged.

**Verification fixture**

- R10. Commit at least one real artifact under `plugins/webworks-claude-skills/skills/reverb2/tests/fixtures/` (e.g. `epublisher-designer-2026.1-help-lookup.json`) generated from the ePublisher Designer 2026.1 help that ships with the product. The artifact serves two purposes: (1) verification fixture for the resolver's round-trip test, (2) live reference for consumers reading the brainstorm/plan to see what a dumped artifact actually looks like. If the help is not reachable from the build environment, fall back to a fixture generated from the existing `multi-chunk-*_lx.js` test fixtures and clearly label it as synthetic in the artifact's `source` block (`"path": "tests/fixtures/"`).
- R11. The standalone verifier (`tests/verify-landmark-resolver.py`) gains scenarios that cover: (a) determinism (dump twice, compare bytes excluding `captured_at`); (b) round-trip equivalence (dump-then-resolve matches direct-chunk resolve, every ID in the fixture); (c) Unicode preservation (`unicode-ids_lx.js` fixture dumps the raw `概要` key and the `--lookup-table` path resolves it identically to `--from`); (d) `format_version` validation (a fixture with `format_version: 99` exits 2).

**Workflow documentation**

- R12. Update `plugins/webworks-claude-skills/skills/reverb2/workflows/landmark-resolution.md` to document the lookup-table consumer path. Add a new column or row to the "Source" table covering `--lookup-table`; revise Step 6 ("Rewrite Stable URLs in Bulk") to point at the structured `dump` output rather than the flat shape; add a short "Step 2b: Lookup-table consumer" paragraph that explains when to use a pre-built artifact versus on-demand `_lx.js` resolution.
- R13. Document the schema in one authoritative place. Default: an inline section in `workflows/landmark-resolution.md` immediately after Step 6 (no new file). The `dump` subcommand's `--help` text gets a one-line cross-reference to that section.

---

## Acceptance Examples

- AE1. **Covers R1, R3.** Given `python resolve-landmarks.py dump --from tests/fixtures/ --out /tmp/help.json`, when the command exits 0, then `/tmp/help.json` parses as JSON, has top-level keys `format_version`, `source`, `landmarks`, and the `landmarks` value is a sorted-key map of `id → {file, anchor}` entries with no `"file#anchor"` flat strings.
- AE2. **Covers R4.** Given the same `dump` invocation run twice, when both outputs are loaded and `source.captured_at` is stripped from each, then the remaining JSON is byte-identical (same key order, same whitespace, same Unicode encoding).
- AE3. **Covers R5.** Given `dump --from tests/fixtures/ --out /tmp/help.json` against a fixture set that includes `unicode-ids_lx.js`, when `/tmp/help.json` is opened in a hex viewer, then the bytes `e6 a6 82 e6 a6 81` (UTF-8 for `概要`) appear literally in the file; no `概要` escape appears anywhere.
- AE4. **Covers R7, R8, R9.** Given a freshly produced artifact at `/tmp/help.json`, when the user runs `python resolve-landmarks.py resolve <id> --lookup-table /tmp/help.json` for every ID in the artifact, then each invocation returns the same resolved path as `python resolve-landmarks.py resolve <id> --from tests/fixtures/` and exits 0.
- AE5. **Covers R8.** Given a JSON file with `{"format_version": 99, "source": {...}, "landmarks": {}}` passed via `--lookup-table`, when the resolver runs, then it exits 2 and the stderr message names the unsupported version explicitly (e.g., "unsupported format_version 99; this build understands 1").
- AE6. **Covers R10, R11.** Given the committed fixture artifact and the standalone verifier, when `python tests/verify-landmark-resolver.py` runs, then the determinism, round-trip, Unicode, and format-version scenarios all report PASS and the verifier exits 0.
- AE7. **Covers R12, R13.** Given a developer reading `workflows/landmark-resolution.md` for the first time, when they reach the "Source" table, then they see three rows (`--from`, `--remote-base-url`, `--lookup-table`) with a one-sentence "When" column; when they reach Step 6, then the section directs them at the structured `dump` schema, not the flat shape.

---

## Success Criteria

- A skill author who wants to ship a baked lookup table for a well-known Reverb mirror can produce, commit, and consume the artifact end-to-end without writing any new JSON-parsing or lookup code — `dump` produces it, `--lookup-table` consumes it.
- The committed fixture artifact serves as both verification input and documentation: a reader can open it in an editor, read the `source` block, and immediately understand what was dumped, from where, and when.
- The artifact format is durable: future schema changes ride a `format_version` bump, and the resolver refuses to silently mis-resolve against a version it does not understand.
- The dump output is reproducible byte-for-byte across machines and operating systems modulo `captured_at`, so committed artifacts are review-friendly and diff cleanly when refreshed.
- Unicode source IDs round-trip transparently — a project that uses `概要` as a landmark ID neither has to escape it nor lose it.

---

## Scope Boundaries

- **Not automating snapshot refresh, publishing, or CI plumbing.** This issue adds the local `dump` command and the `--lookup-table` consumer path. Deciding when and how baked artifacts get refreshed on each Reverb release is downstream.
- **Not compressing or producing binary output.** v1 is uncompressed JSON. Early estimate for the ePublisher 2026.1 help is well under 200KB uncompressed; compression can be revisited only if file size becomes a real constraint.
- **Not adding a reverse-lookup output (file → ids).** Issue #78 owns that direction. The runtime's `pairToId` is referenced in the design questions only to evaluate whether mirroring the runtime shape is worth the complexity now (see Outstanding Questions).
- **Not exposing `dump` as a Python API for in-process consumers.** The script's surface remains CLI-only. Skills that want programmatic resolution either shell out or load the JSON artifact directly with `json.load`.
- **Not back-porting the structured format to an alternate flat-output flag (`--shape flat`, `--legacy`).** R2 treats the flat shape as removed. The bulk-rewrite recipe in Step 6 of the workflow is updated in lockstep; no other consumers exist (verified by grepping the repo for callers of `dump`).
- **Not bumping the plugin version in the brainstorm artifact.** Version bump happens at PR time per `CLAUDE.md` instructions.
- **Not documenting the schema in a new top-level reference file.** R13 favors an inline section in the existing workflow document; a dedicated `references/landmark-dump-schema.md` is overkill for a single small schema (see Outstanding Questions for the alternate option).

---

## Key Decisions

- **Evolve the existing `dump` subcommand rather than add a new one.** The issue body says "New subcommand `dump --from <dir> --out <file>`", but `dump` already exists in `resolve-landmarks.py`. Adding a sibling (`dump-table`, `bake`) duplicates the source-discovery and indexing machinery and confuses the workflow doc, which already names `dump`. Evolving in place keeps the script's verb count flat and matches the issue's underlying intent.
- **Treat the format change as breaking.** The existing flat-`dump` output is only referenced by the workflow doc's optional bulk-rewrite recipe (verified by repo grep). No external skill consumes it. A backwards-compatible flag would carry the flat shape forward forever with no real beneficiary. R2 + R12 update both surfaces together.
- **Single shape, not `--shape runtime` vs `--shape skill`.** The 2026-05-20 verification note proposed both shapes. This brainstorm picks the skill-friendly shape only for v1 because: (1) the runtime localStorage shape is private to the runtime — coupling the artifact to it locks the artifact to runtime versioning forever; (2) reverse-lookup is explicitly out of scope (#78 owns it); (3) interop "load via DevTools" is a developer-debugging convenience, not a consumer use case the issue body or any caller has requested; (4) `--shape` doubles the test surface and the documentation surface for an unproven need. If a future consumer surfaces, a `--shape runtime` flag can be added without breaking v1 because `format_version` gates compatibility.
- **Include `source` block, not just `landmarks`.** Provenance is the difference between a debuggable committed artifact and a JSON blob nobody trusts. The `chunks_found` and `captured_at` fields explicitly support "where did this come from / is it stale" questions reviewers will ask.
- **`format_version` is a hard gate, not a hint.** The resolver refuses unknown versions (exit 2 with an explicit message) rather than guessing forward compatibility. This is the only way the version field earns its place.
- **Use `ensure_ascii=False` for JSON serialization.** Default `json.dumps` escapes non-ASCII to `\uXXXX`. The runtime supports raw Unicode NCNames; the artifact must preserve them. UTF-8 is the only practical interchange encoding for these files.
- **Sort `landmarks` keys, not just rely on `sort_keys=True`.** The current code already uses `sort_keys=True` for the flat output. Reaffirm it for the new shape and verify in the determinism test that nested keys (`file`, `anchor`) also sort deterministically (they do — only two keys, both stable).
- **Path normalization is a real concern but the runtime already does the work.** The runtime emits `f` entries as forward-slash relative paths to the help root (verified in `tests/fixtures/single-chunk_lx.js` and friends). The dump output passes them through unchanged. No re-normalization is needed for v1; if a chunk ever surfaces a Windows-style separator, the integration test will catch it.
- **`source.path` is the verbatim string passed to `--from`.** Not resolved to absolute, not relativized to the repo root. Documenting the literal CLI input is the most-honest provenance; consumers who care about absolute paths can capture `realpath` separately.
- **Commit a real ePublisher artifact when reachable, fall back to a synthetic fixture otherwise.** The verification fixture's primary job is to make the round-trip test repeatable; a synthetic fixture from `tests/fixtures/multi-chunk-*_lx.js` accomplishes that. A real artifact additionally serves as documentation — but committing it depends on having the ePublisher 2026.1 help on the build machine, which is environment-specific. Planning decides which path the implementation takes (see Outstanding Questions).

---

## Dependencies / Assumptions

- The resolver from #54 is merged and the `dump` subcommand exists in `plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py`. Verified by reading the script. The script's `cmd_dump` function currently produces flat-shape JSON or a `--table` rendering.
- The remote-fetching work from #76 is merged. Verified via `git log --oneline` showing `6311966 Merge pull request #81 from quadralay/claude/issue-76`. The remote-mode source path (`--remote-base-url`) and its cache layer are reused unchanged by R6.
- The `blocked-by: #49` directive is satisfied. Verified via `git log --oneline` showing `ce728c2 Merge pull request #90 from quadralay/claude/issue-49`. Per the re-dispatch note, this serializes #77 behind all Chain A work; nothing further blocks implementation.
- The fixture suite under `tests/fixtures/` already contains `unicode-ids_lx.js` covering the Unicode-NCName scenario. R11's Unicode test consumes this fixture directly — no new fixture authoring is required for the round-trip Unicode coverage.
- The standalone verifier (`tests/verify-landmark-resolver.py`) is the canonical test harness for this script. No pytest infrastructure exists; new scenarios go into the same verifier as PASS/FAIL `check(...)` calls.
- The workflow doc at `plugins/webworks-claude-skills/skills/reverb2/workflows/landmark-resolution.md` is the user-facing documentation for the resolver. R12 updates it; no other documentation entry-point exists for resolver users.
- The runtime's last-write-wins semantics from `Landmarks.Advance()` are already preserved by the script's `_merge_chunks` function. Determinism for multi-binding IDs requires no new logic — only verifying that chunk ordering is stable (the script already sorts `*_lx.js` via `discover_chunks`).

---

## Outstanding Questions

### Resolvable at planning time

- [Affects R10] [Environment] Decide whether the committed verification artifact is generated from real ePublisher 2026.1 help or from the existing synthetic `multi-chunk-*_lx.js` fixtures. Real artifact is more compelling documentation; synthetic artifact is reproducible on any build machine. Planning checks whether the build environment has access to `C:\Program Files\WebWorks\ePublisher\2026.1\ePublisher Designer\Help\en\` (or equivalent) and either: (a) generates and commits the real artifact, (b) commits the synthetic fixture with an explicit note that the real-artifact path is deferred to a follow-up, or (c) commits both — synthetic for tests, real as a reference exemplar.
- [Affects R13] [Technical] Decide whether the schema documentation lives inline in `workflows/landmark-resolution.md` (this brainstorm's default) or in a new `plugins/webworks-claude-skills/skills/reverb2/references/landmark-dump-schema.md`. Inline keeps the artifact's documentation close to its primary consumer flow; a reference file is more discoverable for someone arriving from a tool-integration angle. Planning weighs by the section length once written (if it exceeds ~40 lines, split it out).
- [Affects R3, R6] [Technical] Decide whether `source.type` is closed-set (`"local-directory" | "remote-base-url"`) or open-ended (allow future producers like `"runtime-localstorage-export"`). Closed-set is safer for v1 (consumers can switch on it); open-ended defers the decision but risks fragmentation. Planning picks closed-set unless it surfaces a reason during implementation.
- [Affects R1] [Editorial] Decide whether `--out -` is supported as an explicit "write to stdout" alias, in addition to omitting `--out`. Some users prefer the explicit dash convention for scriptability. Cheap to add; planning decides based on whether the test scenarios benefit from it.

### Genuinely uncertain — record as assumption

- [Affects R10] [Open] Whether the ePublisher Designer 2026.1 help, when dumped, contains any IDs that would surface a path-normalization bug. The brainstorm's Key Decision says "no re-normalization for v1" based on the test fixtures. The first real-artifact dump will either confirm that decision or surface a counterexample. Recorded as an assumption: if a real artifact reveals Windows-style paths in `f` entries, planning revisits R3's "file" field semantics and adds a normalization step.
- [Affects R2] [Open] Whether any out-of-tree caller of `resolve-landmarks.py dump` exists beyond the workflow doc's recipe. Repo-internal grep is clean, but downstream skills or scripts that vendored or shelled out to the resolver during the #54 → #76 window may consume the flat shape. The decision to treat the change as breaking assumes no such consumer; a planning-time check for vendored copies or external references is cheap insurance.
