---
date: 2026-05-20
topic: reverb-landmark-dump
---

# Reverb Landmark Resolver: `dump` Schema'd Lookup-Table Output

## Summary

Upgrade `resolve-landmarks.py dump` from a barebones `{id: file#anchor}` JSON dump into a schema'd, deterministic lookup-table artifact (`format_version`, `source`, `landmarks`) and add a matching `--lookup-table <file>` resolution path on `resolve` and `rewrite`. Other skills can then ship pre-built lookup tables for well-known help mirrors without parsing `_lx.js` chunks at resolution time.

---

## Problem Frame

The v1 resolver (issue #54) parses `_lx.js` chunks on every invocation. That cost is fine for ad-hoc resolution, but it is the wrong shape for the consumers that motivated the resolver in the first place: skills that bundle a known help mirror (e.g., the ePublisher Designer help that ships with the product) and resolve against it repeatedly.

Today such a skill has two unattractive options. Carry the full `_lx.js` chunks alongside the skill — large, opaque, and tied to whatever `_lx.js` schema Reverb happens to use — or hand-author a `id → file` map and accept that it drifts every time the help is regenerated. The v1 `dump` subcommand emits a JSON object but its schema is shallow (no `format_version`, no metadata, no determinism guarantee, no path normalization), so consumers cannot safely depend on it without each one reinventing the same wrapper.

The pain hits at the boundary between this resolver and downstream tools. Without a stable artifact contract, every prospective consumer either rewrites the dump format, runs the chunk parser at consumption time (defeating the bundled-mirror premise), or ships drift-prone hand-maintained maps.

---

## Requirements

**Dump subcommand**

- R1. `dump --from <dir>` produces a JSON object matching the schema in [Key Decisions / D1].
- R2. `dump --from <dir> --out <file>` writes the same JSON to `<file>` instead of stdout. Without `--out`, output goes to stdout.
- R3. The dump output is byte-identical across repeated runs against the same input, except for the `captured_at` timestamp. Sorting and tie-breaking rules are spelled out in [Key Decisions / D2].
- R4. Landmark IDs containing non-ASCII characters (XML NCNames, e.g., `概要`, `übersicht`) appear in the output as raw Unicode strings, not as `\uXXXX` escapes.
- R5. Source paths in the `landmarks` map are normalized to forward slashes and URL-decoded before being emitted. The raw form in `_lx.js` is not preserved.
- R6. `dump` accepts `--source-label <string>` to override the `source.path` field. Without the flag, `source.path` is the absolute path passed to `--from`.
- R7. `dump --table` (existing v1 behavior) continues to emit the human-readable table; only the JSON path changes shape.

**Lookup-table consumer path**

- R8. `resolve <id> --lookup-table <file>` resolves IDs against a dump artifact instead of `_lx.js` chunks. Each lookup is O(1) after the file is loaded.
- R9. `rewrite <url> --lookup-table <file>` accepts a lookup table the same way as `resolve`.
- R10. `--lookup-table` and `--from` are mutually exclusive on `resolve` and `rewrite`; passing both is a usage error (exit code 2).
- R11. A lookup table whose `format_version` is unknown to the resolver causes a clear error referencing the version mismatch (exit code 2).

**Documentation and verification**

- R12. The schema is documented in `plugins/webworks-claude-skills/skills/reverb2/references/landmark-lookup-table.md`. The `--help` text for `dump` references the file by path.
- R13. The skill's `workflows/landmark-resolution.md` is updated to cover the lookup-table consumer path alongside the existing `--from` path.
- R14. At least one real lookup-table artifact (e.g., ePublisher Designer 2026.1 help) is dumped and committed under `plugins/webworks-claude-skills/skills/reverb2/references/` as a verification fixture and reference example.
- R15. The verification suite (`tests/verify-landmark-resolver.py`) gains tests that cover: deterministic output across runs, Unicode ID round-trip, `--lookup-table` returning the same answer as `--from` for the same ID set, the mutual-exclusion error for `--from` + `--lookup-table`, and the `format_version` mismatch error.

---

## Acceptance Examples

- AE1. **Covers R3.** Given a fixed input directory of `_lx.js` chunks, when `dump --from <dir>` is run twice and the two outputs are compared with `captured_at` masked out, the byte streams are identical.
- AE2. **Covers R4, R5.** Given a project that emits source-id-format landmarks including `概要` and `übersicht`, when `dump` is run, the output contains those IDs as raw Unicode keys and their `file` fields use forward slashes with URL-encoded characters decoded.
- AE3. **Covers R8, R15.** Given a dump artifact from `dump --from <chunks>/`, when `resolve <id> --lookup-table <dump.json>` is run for every ID in the artifact, each returns the same path that `resolve <id> --from <chunks>/` returns.
- AE4. **Covers R10.** When `resolve <id> --from <chunks>/ --lookup-table <dump.json>` is invoked, the resolver exits 2 with a usage error explaining the mutual exclusion.
- AE5. **Covers R11.** Given a dump artifact whose `format_version` is `2`, when a v1-only resolver invokes `resolve --lookup-table <that-file>`, the resolver exits 2 with a message naming the unsupported version.

---

## Success Criteria

- A downstream skill (e.g., a future ePublisher help skill) can commit a single JSON file alongside its docs, resolve landmark IDs against it via `--lookup-table`, and survive Reverb releases that change ID format without regenerating any skill code.
- A reader of `references/landmark-lookup-table.md` can write a third-party parser of the artifact without reading `resolve-landmarks.py`.
- `ce-plan` can move directly to implementation: schema, CLI surface, determinism contract, and consumer path are all locked.

---

## Scope Boundaries

- **No remote `dump`.** This subcommand operates on a local chunk directory. Remote-fetch composed with `dump` is deferred to whatever follow-up handles remote `_lx.js` fetching.
- **No reverse-lookup output.** The `landmarks` map is `id → {file, anchor}` only. The reverse direction (`file → ids`, or the runtime's `pairToId`) is out of scope; that work belongs to #78.
- **No `--shape runtime` variant.** The runtime's `{v, f, a, ids, pairToId}` shape is interesting mainly because `pairToId` is the reverse index. Adding it here would couple this issue's schema to reverse-lookup design decisions that belong to #78. v1 ships the skill-friendly shape only.
- **No compressed or binary formats.** v1 is JSON only. Early estimate: < 200KB uncompressed for the ePublisher 2026.1 help. Compression is a follow-up if real file size pressure appears.
- **No automated snapshot refresh, publishing, or skill-side ownership decisions.** The committed fixture exists to verify the resolver behavior. Which products' help to bake in, where the artifacts live long-term, and how they refresh on each Reverb release are separate decisions handled outside this issue.
- **No new ID-format handling.** IDs remain opaque strings (per #54). This issue does not introduce hashing, validation, or format-aware logic.

---

## Key Decisions

- **D1. Schema (skill-friendly shape).** The dump artifact has exactly this top-level structure:
  ```json
  {
    "format_version": 1,
    "source": {
      "type": "local-directory",
      "path": "<absolute path or --source-label override>",
      "chunks_found": <int>,
      "captured_at": "<ISO 8601 UTC timestamp>"
    },
    "landmarks": {
      "<id>": { "file": "<normalized relative path>", "anchor": "<anchor string, possibly empty>" }
    }
  }
  ```
  Rationale: self-contained per-entry, readable, decoupled from the runtime's intern-pool layout, easy to consume from any language.

- **D2. Determinism rules.**
  - `landmarks` keys are sorted lexicographically by raw Unicode code point.
  - When the same ID appears in multiple chunk rows, the v1 resolver's "last-write-wins" semantics apply (matching `Landmarks.Advance()`). Chunk discovery order is `sorted(source.glob('*_lx.js'))`, already deterministic.
  - JSON written with `sort_keys=True`, `ensure_ascii=False`, two-space indentation, LF line endings, trailing newline.
  - `captured_at` is the only non-deterministic field. All other bytes are stable across runs.

- **D3. Path normalization in `landmarks[*].file`.** Forward slashes (`/`) and URL-decoded characters. Raw `_lx.js` paths contain Windows-style separators with URL-encoded special characters because they are designed to be inserted into JS strings that may become `href`s. Skill consumers should not each reinvent the normalization.

- **D4. Paths, not URLs.** `landmarks[*].file` holds a path relative to the help root, not an absolute URL. Hosting moves do not invalidate committed artifacts; consumers compose a base URL at read time.

- **D5. Schema versioning lives in `references/landmark-lookup-table.md`.** Provides a stable contract for downstream consumers (including third-party parsers not written by the reverb2 skill). The `--help` text references the file by path; it does not duplicate the schema.

- **D6. `--shape runtime` deferred.** The runtime's `{v, f, a, ids, pairToId}` shape will be revisited as part of #78 (reverse-lookup) where its `pairToId` index is the load-bearing piece.

- **D7. v1 stdout schema is replaced.** The v1 `dump` (stdout, no schema) has been merged for less than a day with no known consumers; replacing the stdout shape is cleaner than carrying two schemas. `--table` mode is unchanged.

- **D8. Anchor as a separate field, not folded into `file`.** Storing `{ file, anchor }` mirrors the runtime's pair storage and lets consumers pick their concatenation rule. Concatenated `file#anchor` form is recoverable in one line of consumer code; the split form is not recoverable from the concatenated form.

- **D9. `--source-label` flag.** Lets a committer name the source semantically (e.g., `"ePublisher Designer 2026.1 Help (en)"`) instead of baking a developer-specific filesystem path into a committed fixture.

---

## Dependencies / Assumptions

- The v1 resolver's chunk discovery, parser, and merge semantics (`resolve-landmarks.py`) are reused as-is. This issue adds output and consumer paths around them; it does not modify them.
- Real-help dump artifact (R14) requires access to a generated Reverb 2.0 help output. Implementer is assumed to have such an install or generated output on hand; if not, a representative multi-chunk fixture in `tests/fixtures/` can stand in for the verification fixture and the real artifact can ship in a follow-up commit.
- JSON output with `ensure_ascii=False` is consumed by tools that expect UTF-8 encoded JSON. The schema doc must state this explicitly so third-party parsers do not default to `ensure_ascii=True` round-trips that would lose information about which encoding the file is in.

---

## Outstanding Questions

### Deferred to Planning

- [Affects R6][Technical] Should `source.path` default to the absolute path of `--from`, or to a path normalized in some way (e.g., resolved through realpath, stripped of `..`)? Plan against the simplest behavior that passes determinism tests; the `--source-label` flag is the escape hatch.
- [Affects R14][Technical] Where exactly under `references/` does the committed real artifact live, and what is its filename convention? Suggested default: `references/lookup-tables/<product>-<version>-<language>.json`. Plan can confirm against the skill's existing layout conventions.
- [Affects R15][Technical] Should the verification suite parse and re-emit the committed real artifact to assert it stays in sync with the resolver, or treat it as a frozen sample? Suggested default: re-emit-and-compare, gated to skip when the underlying chunks are not available locally.
