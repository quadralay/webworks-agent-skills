---
title: "feat: Reverb landmark dump — schema'd lookup-table artifact"
type: feat
status: active
created: 2026-05-20
issue: 77
origin: docs/brainstorms/2026-05-20-issue-77-reverb-landmark-dump-requirements.md
depth: standard
---

# feat: Reverb Landmark Dump — Schema'd Lookup-Table Artifact

## Summary

Upgrade `resolve-landmarks.py dump` from a barebones `{id: file#anchor}` JSON dump into a schema'd, deterministic lookup-table artifact (`format_version`, `source`, `landmarks`) and add a matching `--lookup-table <file>` resolution path on `resolve` and `rewrite`. Ship the schema as a versioned reference doc, refresh the workflow doc to cover the consumer path, and extend the verifier with determinism, Unicode round-trip, parity, and mutual-exclusion coverage. Land at least one committed lookup-table artifact under the skill's `references/lookup-tables/` directory.

The schema, determinism rules, path normalization, paths-not-URLs choice, and the deferral of the runtime `{v, f, a, ids, pairToId}` shape are all locked by the origin brainstorm (see origin: `docs/brainstorms/2026-05-20-issue-77-reverb-landmark-dump-requirements.md`). This plan is implementation-only.

---

## Problem Frame

The v1 resolver (issue #54) parses `_lx.js` chunks on every invocation. That cost is fine for ad-hoc resolution, but it is the wrong shape for the consumers that motivated the resolver in the first place: skills that bundle a known help mirror (for example, the ePublisher Designer help that ships with the product) and resolve against it repeatedly. The v1 `dump` subcommand emits a shallow JSON object — no `format_version`, no source metadata, no documented determinism, no path normalization — so consumers either reinvent a wrapper schema, re-parse chunks at consumption time (defeating the bundled-mirror premise), or ship hand-maintained `id -> file` maps that silently drift.

This plan locks the artifact contract, adds a matching consumer path on `resolve` / `rewrite`, and commits a real artifact so downstream skills have something concrete to depend on.

---

## Requirements Traceability

Origin requirements R1-R15 and acceptance examples AE1-AE5 map to implementation units as follows:

- **R1, R2, R3, R5, R6, R7** — schema'd dump output, `--out`, `--source-label`, normalization, `--table` preservation -> U2
- **R4** — raw Unicode IDs in output -> U2 (encoding contract) and U5 (test coverage)
- **R8, R9, R10, R11** — `--lookup-table` consumer path with mutual-exclusion and version-mismatch errors -> U3
- **R12** — schema doc under `references/landmark-lookup-table.md` -> U1
- **R13** — workflow doc update -> U6
- **R14** — committed real artifact under `references/lookup-tables/` -> U4
- **R15** — verifier coverage (determinism, Unicode, parity, mutex, version mismatch, fixture freshness) -> U5
- **AE1** -> U5 (determinism test)
- **AE2** -> U4 (Unicode fixture) and U5 (Unicode round-trip)
- **AE3** -> U5 (parity test against `--from`)
- **AE4** -> U5 (mutual-exclusion test)
- **AE5** -> U5 (`format_version` mismatch test)
- Plugin version bump (project convention from repo `CLAUDE.md`) -> U7

---

## Key Technical Decisions

These all carry over from the origin brainstorm. They are restated here so the plan stands alone for the implementer.

- **D1. Schema (skill-friendly shape, locked).** Top-level: `format_version` (int, `1`), `source` (object), `landmarks` (object of `id -> {file, anchor}`). See origin Key Decision D1 for the canonical shape.
- **D2. Determinism, locked.** `landmarks` keys sorted lexicographically by raw Unicode code point. Multi-chunk merge keeps the v1 resolver's last-write-wins semantics with `sorted(source.glob('*_lx.js'))` discovery order. JSON written with `sort_keys=True`, `ensure_ascii=False`, two-space indentation, LF line endings, single trailing newline. `captured_at` is the only non-deterministic field.
- **D3. Path normalization, locked.** `landmarks[*].file` uses forward slashes and URL-decoded characters. Normalization happens once in the resolver so downstream consumers do not reinvent it.
- **D4. Paths, not URLs, locked.** `landmarks[*].file` is relative to the help root. Consumers compose a base URL at read time.
- **D5. Schema versioning lives in `references/landmark-lookup-table.md`, locked.** The schema doc is the contract for third-party parsers. `--help` references the file by path; it does not duplicate the schema.
- **D6. `--shape runtime` deferred to #78.** v1 ships only the skill-friendly shape. The runtime's `{v, f, a, ids, pairToId}` shape's value comes mainly from `pairToId` (reverse index), which belongs to the reverse-lookup follow-up.
- **D7. v1 stdout schema is replaced, not duplicated.** The barebones v1 `dump` shape has been merged for less than a day with no known consumers. Replacing the stdout shape is cleaner than supporting both. `--table` mode is unchanged.
- **D8. Anchor stored as a separate field.** `{file, anchor}` mirrors the runtime's pair storage. The concatenated `file#anchor` form is recoverable from the split; the reverse is not.
- **D9. `--source-label` overrides `source.path`.** Lets committed fixtures use a semantic source label (for example, `"ePublisher Designer 2026.1 Help (en)"`) instead of a developer-specific filesystem path.

### Decisions resolved at planning time

These three were marked "Deferred to Planning" in the origin doc. The plan locks them as follows:

- **D10. `source.path` default is `Path(--from).resolve()`.** `Path.resolve()` returns an absolute, normalized path with `..` resolved and symlinks expanded. Simplest behavior that produces a stable string and survives the determinism contract for any single run; `--source-label` is the override for committed artifacts.
- **D11. Committed real artifacts live at `plugins/webworks-claude-skills/skills/reverb2/references/lookup-tables/<product>-<version>-<language>.json`.** Filename pattern keeps multiple artifacts side by side without colliding. The brainstorm's suggested layout. The directory is created in this plan.
- **D12. Verifier compares the committed artifact against a freshly re-emitted dump.** The check parses the committed JSON, re-runs `dump` against the underlying chunks, and asserts byte-equivalence modulo `captured_at`. When the chunks are not available locally (because the implementer or CI does not have the help install), the test logs a `SKIP` and exits without failure. This catches drift between the artifact and the resolver without forcing everyone running the verifier to have the source help on disk.

### Implementation-specific decisions

- **D13. Lookup-table loader reconstructs the resolver's internal index shape.** `load_lookup_table(path) -> (files, anchors, id_to_pair)` reads the JSON artifact, interns unique file strings and anchor strings into ordered lists, and returns the same `(files, anchors, id_to_pair)` triple `build_index` returns. This means `resolve_id` and the URL-rewriting code path work without change. The cost is small (one pass over the `landmarks` map at load time) and avoids forking the resolver internals across two source shapes.
- **D14. Mutual exclusion uses argparse's `add_mutually_exclusive_group(required=True)`.** Both `--from` and `--lookup-table` become alternatives within one required group on `resolve` and `rewrite`. argparse handles the exit-code-2 usage error and the message text. `dump` keeps `--from` as a plain required argument; it does not consume lookup-table artifacts.
- **D15. `format_version` mismatch is a deliberate exit-2 error with a version-named message.** Format example: `"unsupported lookup-table format_version: 2 (this resolver supports format_version 1)"`. Missing field is also exit 2 with `"lookup-table is missing required field 'format_version'"`. Both errors route through the existing `error_log` / `sys.exit(2)` pattern in the resolver.

---

## Output Structure

```
plugins/webworks-claude-skills/skills/reverb2/
  references/
    landmark-lookup-table.md           # new: schema contract (R12)
    lookup-tables/                     # new directory
      <product>-<version>-<language>.json  # new: committed artifact (R14)
  scripts/
    resolve-landmarks.py               # modified: dump rewritten, --lookup-table added
  tests/
    fixtures/
      unicode-chunk_lx.js              # new: Unicode-ID fixture (R4, AE2)
    verify-landmark-resolver.py        # modified: new test scenarios (R15)
  workflows/
    landmark-resolution.md             # modified: lookup-table consumer path (R13)
```

---

## High-Level Technical Design

*This illustrates the intended shape and is directional guidance for review, not implementation specification.*

### CLI surface after this plan

```
# dump — produces the schema'd artifact
python resolve-landmarks.py dump --from <dir> [--out <file>] [--source-label <string>] [--table]

# resolve — accepts either source
python resolve-landmarks.py resolve <id> --from <dir>
python resolve-landmarks.py resolve <id> --lookup-table <file>    # mutually exclusive with --from
                                                                  # (argparse usage error if both given)

# rewrite — accepts either source
python resolve-landmarks.py rewrite <url> --from <dir>            [--base-url <url>]
python resolve-landmarks.py rewrite <url> --lookup-table <file>   [--base-url <url>]
```

### Dump artifact shape (canonical, sort_keys=True at emit)

```json
{
  "format_version": 1,
  "landmarks": {
    "12345678": { "anchor": "wwp200", "file": "Group/page.html" },
    "page-only-id": { "anchor": "", "file": "Group/page.html" },
    "概要": { "anchor": "wwp_overview", "file": "Topics/overview.html" }
  },
  "source": {
    "captured_at": "2026-05-20T15:00:00Z",
    "chunks_found": 7,
    "path": "ePublisher Designer 2026.1 Help (en)",
    "type": "local-directory"
  }
}
```

Top-level keys land in `format_version, landmarks, source` order because `sort_keys=True` is alphabetic at every level. Per-entry keys land as `anchor, file`. The brainstorm sample showed `format_version, source, landmarks` for narrative reasons — that ordering is illustrative; the emitted ordering is alphabetic.

### Internal data-flow seam

```
                       --from <dir>
                            |
                            v
                    discover_chunks() ----> build_index() ----+
                                                              |
                                                              v
                                                  (files, anchors, id_to_pair)
                                                              ^
                                                              |
                       --lookup-table <file>                  |
                            |                                 |
                            v                                 |
                     load_lookup_table() ---------------------+
                                                              |
                                                              v
                                                   resolve_id() / rewrite()
                                                              |
                                                              v
                                          cmd_dump emits schema'd JSON above
```

Both source paths converge on `(files, anchors, id_to_pair)`; downstream code is unchanged.

---

## Implementation Units

### U1. Add schema reference doc `references/landmark-lookup-table.md`

**Goal:** Land the public contract for the dump artifact so downstream consumers (other skills, third-party parsers) can depend on the shape without reading `resolve-landmarks.py`.

**Requirements:** R12

**Dependencies:** none — this is the contract everything else implements.

**Files:**
- `plugins/webworks-claude-skills/skills/reverb2/references/landmark-lookup-table.md` — new file

**Approach:**

- YAML frontmatter matches the existing `references/scss-architecture.md` style (title, date, module: reverb2). No special metadata required.
- Sections to include, in this order:
  1. **Purpose.** What the artifact is and what consumes it. One paragraph.
  2. **File location and naming convention.** State `references/lookup-tables/<product>-<version>-<language>.json` as the convention for in-skill artifacts; note that downstream skills may follow their own conventions.
  3. **Schema (version 1).** Spell out every field with type, presence (required/optional), and example. Include the canonical alphabetic key order at every level, with a note that JSON spec does not require key order so consumers parsing into language-native maps should not depend on the in-file order.
  4. **Encoding.** UTF-8, no BOM, LF line endings, single trailing newline. Files contain raw Unicode (not `\uXXXX` escapes). Consumers must read as UTF-8.
  5. **Determinism contract.** What is stable across runs (everything except `captured_at`), under what sort key (raw Unicode code point), and what merge policy (`sorted(source.glob('*_lx.js'))` discovery, last-write-wins per id).
  6. **Path normalization.** Forward slashes, URL-decoded; emitted by the resolver, consumers do not need to re-normalize.
  7. **Versioning policy.** A consumer reading a file with `format_version` it does not know must fail loudly (no silent fallback). Bumping `format_version` is a breaking change to the schema and is the trigger for downstream skills to update.
  8. **Worked example.** A complete (but small) example file with a few entries spanning the typical cases: page-level (empty anchor), paragraph-level (non-empty anchor), Unicode source ID. Reuse values from the test fixtures so the example doubles as live documentation.
- The doc is prose + code blocks only — no Python imports, no internal function names. Aim for a third-party parser author being able to write a reader from this doc alone.

**Patterns to follow:**
- `plugins/webworks-claude-skills/skills/reverb2/references/scss-architecture.md` — neighbor reference doc shape (frontmatter, section structure, cross-references).
- `plugins/webworks-claude-skills/skills/reverb2/workflows/landmark-resolution.md` — tone and section weights for reverb2 docs (concise prose with tables/code blocks where they pull weight).

**Test scenarios:**

Test expectation: none — this is a reference document. Verification is by reading the file against the requirements traceability above.

Manual verification scenarios for the implementer:

- *Covers R12.* The doc exists at the documented path and is referenced by name from `resolve-landmarks.py`'s `--help` epilogue (added in U2).
- *Worked example round-trip.* A reader who hand-types the worked example into a file, points the resolver at it via `--lookup-table`, and runs `resolve <id>` against an ID in the example gets the expected file path back. (Implementer manually verifies during U3.)

**Verification:**
- File exists, frontmatter parses, sections present in the order above.
- Schema section documents every field that U2 emits (cross-check against the canonical sample in this plan's High-Level Technical Design section).

---

### U2. Rewrite `cmd_dump` to emit the schema'd artifact

**Goal:** Replace the v1 stdout shape with the schema'd artifact defined by U1. Add `--out` (file destination) and `--source-label` (semantic source override). Preserve `--table` mode unchanged.

**Requirements:** R1, R2, R3, R5, R6, R7, R4 (raw Unicode encoding)

**Dependencies:** U1 (schema doc must exist so `--help` can reference it).

**Files:**
- `plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py` — modify `cmd_dump`, add helper for normalization and artifact assembly, update `dump_parser` argparse setup, update module docstring and `--help` epilogue to reference `references/landmark-lookup-table.md` by path.

**Approach:**

- Add a new helper `normalize_landmark_path(raw: str) -> str` that converts Windows-style backslashes to forward slashes and URL-decodes percent-encoded characters. Apply it to every file string at dump time. Anchors are stored verbatim (no normalization needed).
- Add a new helper `build_dump_artifact(files, anchors, id_to_pair, source_path, chunks_count) -> dict` that assembles the schema'd dict in memory. `captured_at` is `datetime.datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')` — produces `2026-05-20T15:00:00Z` form, deterministic per-run, only field that changes across runs.
- `cmd_dump` flow:
  1. `_build_or_die(Path(args.source))` -> `(files, anchors, id_to_pair)` (reuses existing code).
  2. Build the dict. `source.path` is `args.source_label` when set, otherwise `str(Path(args.source).resolve())`.
  3. Branch on `--table` (unchanged path; uses the v1 table formatting) vs JSON. JSON path serializes with `json.dumps(artifact, sort_keys=True, ensure_ascii=False, indent=2)` then appends a single `'\n'`.
  4. Branch on `--out`: when set, write to that file using `pathlib.Path(args.out).write_text(serialized, encoding='utf-8', newline='\n')` to force LF endings on Windows. When unset, `print` to stdout (Python's default `print` appends `\n` and writes through the encoded stream).
- Add the `--out` and `--source-label` arguments to `dump_parser` in `main()`. Keep `--table` and `--from`.
- Update the module docstring and the `argparse` epilogue. The `--help` epilogue should add: `See references/landmark-lookup-table.md for the artifact schema.`
- The runtime-mirror semantics from #54 (last-write-wins, discovery sort, defensive `continue` for malformed rows) are reused via the existing `build_index` call — no behavior change there.

**Patterns to follow:**
- `parse_chunk`, `build_index`, `_build_or_die` in the existing resolver — reuse as-is.
- `cmd_dump`'s existing `--table` branch — keep, do not refactor.
- Error path: route any failures (write errors, path resolution errors) through `error_log` + `sys.exit(2)` to match the rest of the script.

**Test scenarios:**

- *Happy path.* `dump --from tests/fixtures/` writes a JSON object to stdout with `format_version: 1`, `source` containing `type`, `path`, `chunks_found`, `captured_at`, and `landmarks` containing every fixture ID. Parsed JSON's keys match the schema doc.
- *Covers R2.* `dump --from <dir> --out <file>` writes the same content to `<file>` and produces no stdout output. `<file>` ends with a single `\n`, has LF line endings even on Windows, and is valid JSON.
- *Covers R3 (determinism).* Two runs of `dump --from <dir>` produce byte-identical output when `captured_at` lines are masked out.
- *Covers R5 (normalization).* Given a chunk whose `f` array contains `"Foo\\bar%20baz.html"` (backslash + URL-encoded space), the dump's `landmarks[*].file` reads `"Foo/bar baz.html"`.
- *Covers R6.* `dump --from <dir> --source-label "ePublisher Designer 2026.1 Help (en)"` emits `source.path == "ePublisher Designer 2026.1 Help (en)"`; without `--source-label`, `source.path` is the absolute resolved path of `<dir>`.
- *Covers R7.* `dump --from <dir> --table` emits the v1 table format unchanged. Adding a `--table` snapshot regression in U5 guards against accidental changes.
- *Covers R4 (encoding, partial — full round-trip in U5).* A chunk containing `"概要"` in its `e` array emits a `landmarks` key spelled `概要` in raw Unicode, not `概要`.
- *Edge: empty source.* `dump --from <empty-dir>` exits 2 (the existing `discover_chunks` error). Verified by reusing the existing CLI test that covers that path; no new test required.

**Verification:**
- `python resolve-landmarks.py dump --from tests/fixtures/` JSON parses cleanly and matches the schema doc.
- `--help` epilogue mentions `references/landmark-lookup-table.md`.
- Existing `--table` CLI test still passes (covered by U5's re-run, but no behavior change expected).

---

### U3. Add `--lookup-table` consumer path to `resolve` and `rewrite`

**Goal:** Let `resolve` and `rewrite` consume a dump artifact directly, with O(1) per-query lookups and clear errors for the two failure modes (mutual exclusion, version mismatch).

**Requirements:** R8, R9, R10, R11

**Dependencies:** U1 (schema), U2 (artifact existence in the wild).

**Files:**
- `plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py` — add `load_lookup_table()`, modify `resolve_parser` and `rewrite_parser` argparse setup, modify `cmd_resolve` and `cmd_rewrite` to dispatch on which flag was set.

**Approach:**

- Add a new helper `load_lookup_table(path: Path) -> tuple[list[str], list[str], dict[str, tuple[int, int]]]` that:
  1. Reads the file as UTF-8 (`Path(path).read_text(encoding='utf-8')`).
  2. Parses JSON via `json.loads`. Wraps any `JSONDecodeError` in a `ValueError` with the path in the message.
  3. Checks `format_version`. Missing field -> `ValueError("lookup-table is missing required field 'format_version': <path>")`. Unknown version -> `ValueError(f"unsupported lookup-table format_version: {v} (this resolver supports format_version 1)")`. Both surface as exit 2 via `_build_or_die`-style routing.
  4. Walks `landmarks` (which must be a dict; otherwise `ValueError`). For each `id -> {file, anchor}`, interns the file string into `global_files`/`file_index` and the anchor string into `global_anchors`/`anchor_index`, then records `id_to_pair[id] = (fi, ai)`.
  5. Returns `(global_files, global_anchors, id_to_pair)` — same triple shape `build_index` returns, so `resolve_id` and rewrite's URL-prefix logic work without change.
- Refactor argparse on `resolve` and `rewrite`:
  - Replace `--from <path>` (required) with `add_mutually_exclusive_group(required=True)` containing `--from` and `--lookup-table`.
  - argparse handles the mutual-exclusion error automatically. The default error exits 2 with a usage message — confirms R10 without custom code.
- Refactor `cmd_resolve` and `cmd_rewrite`: build the index from whichever source was set, then run the existing resolution path:
  ```python
  if args.lookup_table:
      try:
          files, anchors, id_to_pair = load_lookup_table(Path(args.lookup_table))
      except (FileNotFoundError, ValueError, OSError) as e:
          error_log(str(e))
          sys.exit(2)
  else:
      files, anchors, id_to_pair = _build_or_die(Path(args.source))
  ```
- Consider extracting that branch into a small `_load_index(args)` helper to avoid duplication between `cmd_resolve` and `cmd_rewrite`. Keep it inside the script.
- Update the module docstring and `argparse` epilogue to show both source forms on `resolve` and `rewrite`. Cross-reference `references/landmark-lookup-table.md`.
- `dump` is intentionally untouched — it always reads from `--from <dir>`. Round-trip use cases (dump then re-dump a dump) are not in scope.

**Patterns to follow:**
- `_build_or_die` — wraps the existing chunk-source path with exit-2 error handling. The new `load_lookup_table` failure path follows the same shape.
- `parse_chunk`'s `ValueError` raising pattern with the file path in the message — reuse that style in `load_lookup_table`'s error messages so failure surface is consistent.

**Test scenarios:**

- *Covers R8 (happy path).* Dump artifact `tests/fixtures/snapshot.json` (created on the fly in the verifier from the multi-chunk fixtures). `resolve <id> --lookup-table tests/fixtures/snapshot.json` returns the same path for every id that `resolve <id> --from tests/fixtures/` returns. Iterate over every id in the dump (not just one) — this is also the AE3 parity test.
- *Covers R9.* `rewrite https://example.com/help/#/<id> --lookup-table tests/fixtures/snapshot.json` returns the same direct URL the `--from` form returns.
- *Covers R10 (mutual exclusion).* `resolve <id> --from <dir> --lookup-table <file>` exits 2 and stderr contains "not allowed with" or similar argparse phrasing. Same for `rewrite`.
- *Covers R11, AE5 (version mismatch).* Hand-craft a JSON file with `format_version: 2` (or `99`); invoke `resolve <id> --lookup-table <that-file>`. Resolver exits 2 with a message naming the unsupported version. Repeat with `format_version` absent entirely — exits 2 with the "missing required field" message.
- *Edge: malformed lookup-table.* File is not valid JSON -> exit 2 with the file path in the message.
- *Edge: lookup-table missing `landmarks`.* JSON is valid, `format_version` is 1, but `landmarks` key is absent. Exit 2 with a message naming the missing field.
- *Edge: id not in lookup-table.* `resolve unknown-id --lookup-table <file>` exits 1, same as the `--from` form's not-found path. `--json` mode emits the same `{error, id}` shape.

**Verification:**
- All existing `--from` CLI tests still pass (regression check).
- Mutex error format is argparse's stock error; no custom string required.
- `load_lookup_table` on a freshly written U2 dump returns a triple whose `id_to_pair` has the same keys and resolves to the same paths as the corresponding `build_index` call.

---

### U4. Add Unicode-ID fixture and commit a real lookup-table artifact

**Goal:** Land the two artifacts the tests and consumers need: a Unicode-ID fixture (for AE2 round-trip coverage) and a real committed lookup-table that demonstrates the schema in production form.

**Requirements:** R4 (encoding), R14 (committed real artifact)

**Dependencies:** U2 (need working `dump` to produce the real artifact).

**Files:**
- `plugins/webworks-claude-skills/skills/reverb2/tests/fixtures/unicode-chunk_lx.js` — new fixture
- `plugins/webworks-claude-skills/skills/reverb2/references/lookup-tables/<product>-<version>-<language>.json` — new committed artifact
- `plugins/webworks-claude-skills/skills/reverb2/references/lookup-tables/README.md` — short index describing what each artifact is and how it was generated (optional but recommended, see Approach)

**Approach:**

- *Unicode fixture.* Add a small `_lx.js` chunk that emits at least three Unicode source IDs spanning the cases the runtime supports (per the brainstorm's runtime-verification note): a Japanese ID (`概要`), a German ID with diacritic (`übersicht`), and an ASCII pass-through ID for control. Shape mirrors the existing `single-chunk_lx.js` fixture so the file is recognized by `discover_chunks` (`*_lx.js`). Anchors can be empty or page-level to keep the fixture small.
- *Committed real artifact.* Preferred path: generate the ePublisher Designer 2026.1 Help (en) output, point `dump --from <that-output-dir> --source-label "ePublisher Designer 2026.1 Help (en)"` at it, and commit the result under `references/lookup-tables/epublisher-designer-2026.1-en.json`. The brainstorm acknowledges the implementer may not have the source help on disk; if not, generate a stand-in from the test fixtures and name it `tests-fixtures-stand-in.json` with `--source-label "test fixtures stand-in"`, and note in `references/lookup-tables/README.md` that the real artifact will land in a follow-up commit. Either path satisfies R14 in the sense that the verifier has something committed to assert against; the in-the-wild value is higher with the real artifact.
- *Optional README.* If two artifacts coexist (real + stand-in), drop a one-page `references/lookup-tables/README.md` describing the filename convention (`<product>-<version>-<language>.json` from D11), which artifact is the real one, and how to regenerate them. Skip the README when only one artifact ships.

**Patterns to follow:**
- Existing fixtures in `tests/fixtures/` for shape and tone — keep the Unicode fixture small (under 20 lines).
- `references/scss-architecture.md` as the neighbor when shaping the optional `references/lookup-tables/README.md`.

**Test scenarios:**

Test expectation: none for the fixtures themselves — they are data, not code. Test coverage that *exercises* them lives in U5.

Manual verification:
- *Covers R4 (encoding).* Reading `unicode-chunk_lx.js` with `utf-8-sig` or `utf-8` yields a chunk parseable by `parse_chunk`, and `build_index` returns `id_to_pair` with keys `概要`, `übersicht`, and the ASCII control. Verified through U5's AE2 test.
- *Covers R14.* `references/lookup-tables/<file>.json` exists, parses as valid JSON, has `format_version: 1`, and `source.path` is either the real semantic label or the documented stand-in label.

**Verification:**
- Fixture file is valid `_lx.js` (`Landmarks.Advance(landmarks);` suffix, JSON-shaped object literal).
- Committed artifact passes the verifier's drift check (U5's freshness scenario) when chunks are present, and is `SKIP`-ed cleanly when they are not.
- File encoding is UTF-8 without BOM, LF line endings.

---

### U5. Extend the verifier with new test scenarios

**Goal:** Land the test coverage R15 specifies plus the committed-artifact freshness check. The verifier remains a single-file standalone runner with no third-party deps.

**Requirements:** R15 (full list); covers AE1, AE2, AE3, AE4, AE5

**Dependencies:** U2, U3, U4.

**Files:**
- `plugins/webworks-claude-skills/skills/reverb2/tests/verify-landmark-resolver.py` — extend with new scenarios; do not break existing scenarios.

**Approach:**

- Add new tests adjacent to the existing CLI-contract section. Reuse `run_cli`, `check`, and the `_results` accumulator already in the file. Keep the PASS/FAIL output format.
- *AE1 / R3 determinism.* New helper `_mask_captured_at(json_text: str) -> str` strips or replaces the `captured_at` line. Test: run `dump --from <multi-fixture-dir>` twice into temp files; assert masked outputs are byte-equal.
- *AE2 / R4 / R5 Unicode + normalization round-trip.* Build an index from `unicode-chunk_lx.js`; assert `id_to_pair` has raw Unicode keys (not escaped). Run `dump --from tests/fixtures/unicode-chunk_lx.js --out <tmp>`; parse `<tmp>` with `json.loads` and assert the Unicode keys are still raw Unicode in the parsed dict. Sample a path with URL-encoded characters and assert the dump emits the decoded form.
- *AE3 / R8 parity test.* Run `dump --from <fixtures-dir>` into a temp file; load the file with `load_lookup_table` (or via CLI), then for every id in the dump, assert `resolve <id> --lookup-table <file>` returns the same path as `resolve <id> --from <fixtures-dir>`. Iterate over every id, not just one.
- *AE4 / R10 mutual exclusion.* Run `resolve <id> --from <dir> --lookup-table <file>`; assert exit code 2 and that stderr contains argparse's mutex phrasing. Same test for `rewrite`.
- *AE5 / R11 version mismatch.* Hand-write two artifacts in a tempdir: one with `format_version: 99`, one missing the field. Run `resolve <id> --lookup-table <each>`; assert exit code 2 and the message names the unsupported version (or the missing field).
- *Drift check (D12).* Locate `references/lookup-tables/<the-real-artifact>.json`. Parse its `source.path`. If it matches a path the implementer / CI can access (heuristic: look for an env var `REVERB_HELP_MIRROR` pointing at a chunks dir, or accept that we cannot reach the real path and `SKIP`), re-run `dump --from <that-dir> --source-label <committed-label>` and assert the result matches the committed artifact byte-for-byte (modulo `captured_at`). When the chunks are not reachable, log `SKIP` with a clear message and do not fail.
- *`--out` snapshot.* Smoke test that `dump --from <dir> --out <tmp>` writes the same content to `<tmp>` as the stdout path emits, with LF line endings and a single trailing newline.
- *`--table` regression.* The existing `test_cli_dump_table` covers basic invariants (`'Landmark ID'` header, sample id present). Keep it. Optionally extend with a snapshot of the exact table for the multi-chunk fixtures so future accidental changes to `--table` formatting are caught.
- Register every new test in `main()` so they actually run.

**Patterns to follow:**
- `test_cli_dump_directory`, `test_cli_resolve_directory_mode` — CLI subprocess pattern, JSON parsing, `check(name, condition, detail)` shape.
- `test_internal_*` functions for tests that load the resolver as a module.
- `tempfile.TemporaryDirectory()` already used in `test_internal_empty_e_array`; mirror it.

**Test scenarios (within this unit, i.e., what tests U5 adds — the implementer should not need to invent these):**

- *Covers AE1.* `test_dump_deterministic`: two runs, masked compare, expect equal.
- *Covers AE2.* `test_dump_unicode_round_trip`: dump the Unicode fixture, parse output, assert raw Unicode keys survive.
- *Covers R5.* `test_dump_path_normalization`: chunk with backslashes + URL-encoding emits forward-slash + decoded paths.
- *Covers AE3.* `test_lookup_table_parity_with_from`: for every id, both sources return identical resolved paths.
- *Covers AE4.* `test_cli_mutex_from_and_lookup_table`: both `resolve` and `rewrite` exit 2 when both flags are present.
- *Covers AE5.* `test_cli_unsupported_format_version`: artifact with `format_version: 99` -> exit 2 with version named. Variant: missing field -> exit 2 with field named.
- *Covers D12.* `test_committed_artifact_freshness`: re-emit and compare; `SKIP` when source chunks unreachable.
- *Covers R2.* `test_dump_out_file_matches_stdout`: same content, LF endings, one trailing newline.

**Verification:**
- Verifier passes (`PASS` for every new scenario, `SKIP` for the drift check when chunks unavailable).
- Exit code is 0 when every non-skipped scenario passes.
- Existing 28-scenario coverage from #54 still passes (regression check).

---

### U6. Update `workflows/landmark-resolution.md` and `--help`

**Goal:** Surface the lookup-table consumer path in the documentation a user will read first (workflow doc, `--help`). The schema doc U1 produced is the deep contract; this unit makes sure users discover it through the normal entry points.

**Requirements:** R13

**Dependencies:** U1 (must cross-link to it), U2 / U3 (CLI surface must be locked).

**Files:**
- `plugins/webworks-claude-skills/skills/reverb2/workflows/landmark-resolution.md` — modify
- `plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py` — module docstring + `argparse` epilogue (mostly already done in U2/U3; verify the workflow doc references are correct here)

**Approach:**

- Workflow doc updates:
  - In **Step 1: Identify the Input**, add a third row to the input shapes table: `Committed lookup-table artifact` row, for when a skill ships a pre-built artifact alongside its docs.
  - In **Step 2: Run the Resolver**, add a fourth code block showing the `--lookup-table` form on `resolve` and `rewrite`. Note that `--from` and `--lookup-table` are mutually exclusive.
  - Update the modes table to add a row or note for the lookup-table source. Keep the table from sprawling — add a separate `### Lookup-table mode` subsection if the table becomes hard to read.
  - In **Step 5: Rewrite Stable URLs in Bulk**, refresh the `dump` example to use the new schema'd output. Show `--out <file>` and `--source-label <string>`. Mention that the artifact is committable and stable across runs.
  - Add a final subsection `### Schema and downstream consumers` that links to `references/landmark-lookup-table.md` (relative path from the workflow doc: `../references/landmark-lookup-table.md`).
- Resolver `--help` epilogue (mostly handled in U2/U3): confirm the epilogue mentions both source forms and `references/landmark-lookup-table.md` by path.
- The `<required_reading>` block at the top of the workflow doc currently says "No additional references needed." Update it to point at `references/landmark-lookup-table.md` when consumers care about the artifact schema. Keep the wording light — most use cases still do not need the schema doc.

**Patterns to follow:**
- The existing workflow doc structure (`<required_reading>`, `<process>`, numbered Steps, `<success_criteria>`). Do not restructure.
- Sibling workflow `workflows/csh-analysis.md` for cross-reference style if needed.

**Test scenarios:**

Test expectation: none — these are documentation changes. Verification is by reading the diff against R13.

Manual verification:
- *Covers R13.* The workflow doc shows three input shapes (single chunk, directory, lookup-table artifact). The CLI examples cover both `--from` and `--lookup-table` source forms. The doc cross-links to `references/landmark-lookup-table.md` at least once.

**Verification:**
- Workflow doc parses as valid markdown.
- Cross-references resolve (the schema doc path exists from U1).
- `--help` text actually mentions the schema doc path (verified by spot-running `python resolve-landmarks.py dump --help`).

---

### U7. Bump plugin version to 2.12.0

**Goal:** Apply the project's required version bump so the new dump schema and consumer path ship under a new version, per `CLAUDE.md` ("minor: new skills, new features").

**Requirements:** Project convention (not an origin requirement, but mandated by the repo `CLAUDE.md`).

**Dependencies:** U1 through U6 (the version bump ships everything together).

**Files:**
- `plugins/webworks-claude-skills/.claude-plugin/plugin.json` — version field
- `.claude-plugin/marketplace.json` — version field

**Approach:**

- Run `scripts/bump-version.sh minor`. The script increments minor (2.11.0 -> 2.12.0), zeros the patch, and writes both manifests in lockstep. Do not hand-edit.

**Patterns to follow:**
- `scripts/bump-version.sh` — the canonical bump path. Recent commits in `git log` follow this same pattern.

**Test scenarios:**

Test expectation: none — metadata bump. Verification is by reading the diff.

**Verification:**
- Both `plugin.json` and `marketplace.json` report `"version": "2.12.0"`.
- `git diff --stat` shows changes only to those two files (plus the files from U1-U6).

---

## Scope Boundaries

### In scope

- Schema'd `dump` output with `--out`, `--source-label`, deterministic emit.
- Path normalization (forward slashes, URL-decoded) in dump output.
- `--lookup-table` consumer path on `resolve` and `rewrite`, with mutex against `--from` and version-mismatch errors.
- Schema reference doc (`references/landmark-lookup-table.md`).
- Unicode-ID fixture + at least one committed lookup-table artifact.
- Verifier extensions covering determinism, Unicode round-trip, parity, mutex, version mismatch, and committed-artifact freshness drift check.
- Workflow doc update plus `--help` cross-references.
- Plugin minor-version bump.

### Out of scope

- **No remote `dump`.** This subcommand operates on a local chunk directory. Remote-fetch composition is deferred to whatever follow-up handles remote `_lx.js` fetching. (Origin scope boundary.)
- **No reverse-lookup output.** `landmarks` is `id -> {file, anchor}` only. Reverse direction (`file -> ids`, runtime's `pairToId`) is out of scope; belongs to #78. (Origin scope boundary.)
- **No `--shape runtime` variant.** Runtime's `{v, f, a, ids, pairToId}` shape is interesting mainly because of `pairToId`. Adding it here would couple this issue's schema to reverse-lookup design decisions that belong to #78. (Origin scope boundary.)
- **No compressed or binary formats.** v1 is JSON only. Compression deferred until real file-size pressure appears. (Origin scope boundary.)
- **No automated snapshot refresh, publishing, or skill-side ownership decisions.** The committed fixture is a verification artifact, not the start of a maintained product index. Which products' help to bake in, where artifacts live long-term, and how they refresh on each Reverb release are separate decisions. (Origin scope boundary.)
- **No new ID-format handling.** IDs remain opaque strings. No hashing, validation, or format-aware logic. (Origin scope boundary.)
- **No refactor of `parse_chunk`, `build_index`, or `_build_or_die`.** These are reused as-is. (Origin Dependency.)

### Deferred to Follow-Up Work

- **A real ePublisher Designer 2026.1 Help (en) committed artifact.** If the implementer does not have the source help on disk, U4 ships a fixture-derived stand-in plus a `README.md` noting the follow-up. The real artifact lands when generated.
- **`--shape runtime` and reverse-lookup direction** — handled by #78.
- **Remote-fetch + dump composition** — handled by the remote-fetch issue.

---

## Risks

- **Risk: Determinism contract breaks silently across Python versions.** `json.dumps(sort_keys=True, ensure_ascii=False, indent=2)` is stable across Python 3.x, but the timestamp format and `Path.resolve()` semantics can vary subtly (Windows short-path resolution, junction handling). Mitigation: `--source-label` is the escape hatch for committed artifacts — committers should always set it so `source.path` does not bake in a developer-specific filesystem string. The drift check in U5 also catches accidental output changes. Low likelihood, moderate impact.
- **Risk: `--lookup-table` consumer drift from `--from` consumer over time.** The two paths converge on the same `(files, anchors, id_to_pair)` triple, but a future change to `build_index` (for example, adding a fourth field) could leave `load_lookup_table` behind. Mitigation: the parity test in U5 iterates over every id and compares paths — any divergence fails the test. Low likelihood, low impact.
- **Risk: Unicode encoding subtle on Windows.** Python's default open-for-write on Windows can produce CRLF and CP1252. U2 explicitly passes `encoding='utf-8'` and `newline='\n'` to `write_text`, and the existing tests run on macOS / Linux CI. Mitigation: U5's determinism test will fail on a CRLF leak; U2's per-call encoding kwargs are the structural fix. Low likelihood, moderate impact.
- **Risk: The committed real artifact is generated from a developer's specific help install and embeds developer-local paths.** Mitigation: `--source-label` is *mandatory* in the U4 workflow for committed artifacts. The README in U4 documents this. The drift check in U5 fails if a committed artifact's `source.path` looks filesystem-shaped. Low likelihood (the workflow gates it), high impact if it leaks (commits a developer's home directory path).

---

## Final Checks

Before commit:

- [ ] `references/landmark-lookup-table.md` exists, frontmatter valid, sections present per U1.
- [ ] `scripts/resolve-landmarks.py` `dump` emits schema'd JSON; `--out`, `--source-label`, `--table` all work.
- [ ] `scripts/resolve-landmarks.py` `resolve` and `rewrite` accept both `--from` and `--lookup-table`, with argparse-enforced mutex and clear version-mismatch errors.
- [ ] `tests/fixtures/unicode-chunk_lx.js` exists; index built from it contains raw Unicode keys.
- [ ] At least one artifact under `references/lookup-tables/` is committed; its `source.path` is a semantic label (set via `--source-label`), not a developer-local filesystem path.
- [ ] `tests/verify-landmark-resolver.py` passes every scenario (or `SKIP`-s the drift check cleanly).
- [ ] `workflows/landmark-resolution.md` documents the lookup-table consumer path and cross-links the schema doc.
- [ ] `plugin.json` and `marketplace.json` both report `2.12.0`.
- [ ] No unrelated files changed.
- [ ] Commit uses conventional commit format (`feat:`) per repo `CLAUDE.md`.
