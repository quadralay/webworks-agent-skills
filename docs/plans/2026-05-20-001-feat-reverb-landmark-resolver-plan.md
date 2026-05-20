---
title: "feat: Add Reverb landmark resolver"
type: feat
status: active
created: 2026-05-20
issue: 54
depth: standard
---

# feat: Reverb Landmark Resolver

## Summary

Add a Python resolver to the `reverb2` skill that converts stable Reverb 2.0 landmark URLs (the hash-based `#/<id>` form used in published help) into direct static file paths by parsing the `_lx.js` chunk files emitted alongside every Reverb output. The resolver lets AI consumers fetch documentation without executing the Reverb JavaScript runtime, and it lets the `epublisher` and `reverb2` skills automatically rewrite stable links in their own reference material into direct file links.

## Problem Frame

Reverb 2.0 output uses stable hash-based URLs for topic linking (`https://static.webworks.com/docs/epublisher/latest/help/#/e5d3d31c42d8d1d4`). Resolving these URLs to a real HTML file requires executing the Reverb JavaScript runtime — the runtime fetches every `_lx.js` chunk, merges them through `Landmarks.Advance()`, and looks the ID up in the merged index.

AI systems fetching documentation without a JS runtime cannot resolve stable links and must fall back to direct file URLs that may change when source documents are restructured. Today, `plugins/webworks-claude-skills/skills/epublisher/references/product-foundations.md` documents both link forms by hand with a comment that the stable form needs JavaScript. A resolver eliminates that hand-maintained mapping for any Reverb output we can read on disk or fetch over HTTP.

## Requirements Traceability

This plan addresses every behavior the issue describes. There is no upstream brainstorm document, so the issue body itself is the requirements source.

- **Parse `_lx.js` and rebuild the runtime index** → U1
- **Resolve any landmark ID (16-char hex, 8-char hex, or pass-through source ID — treated as opaque)** → U1
- **Return file path with optional `#anchor`, matching runtime `GetPathById` semantics** → U1
- **Handle local Reverb output (one directory containing many `_lx.js` chunks)** → U1
- **Handle a single `_lx.js` file** → U1
- **Provide fixture-backed verification of parsing, merging, and resolution** → U2
- **Document when and how to use the resolver from the skill** → U3, U4
- **Replace the hand-maintained "stable + direct link" pattern in `product-foundations.md` with a pointer to the resolver** → U5
- **Ship the change under a new plugin version** → U6 (project convention from `CLAUDE.md`)

The "remote Reverb output (fetch `_lx.js` from `static.webworks.com`)" and "pre-built lookup-table generation" usage scenarios from the issue are deferred — see Scope Boundaries.

## Key Technical Decisions

- **Single Python script under `scripts/`, matching the existing reverb2 pattern.** `parse-url-maps.py` is the closest analog (read a structured artifact in the Reverb output, return JSON or a table). A Python script keeps tool selection consistent across the skill and reuses the same arg/log/error conventions. Resolves issue implementation option 1 vs 2 vs 3.
- **Treat the landmark ID as an opaque string.** Per the issue, the 2026.1 release introduces 8-char and pass-through ID formats with no in-band format indicator. The resolver does not regex, length-check, or hex-validate IDs — it does a straight string-equality lookup against the third element of each `e[i]` tuple. This makes the resolver forward-compatible with future ID schemes.
- **Match the runtime's "last write wins" semantics for duplicate ID rows.** Real `_lx.js` chunks contain multiple `e` rows per ID (typically one page-level row with `anchorIndex=0` and one paragraph-level row with a specific anchor). Sometimes the same ID appears against several `(file, anchor)` pairs across chunks. The reference runtime (`/scripts/landmarks.js` in any Reverb 2.0 output) uses `dset(D.ids, id, [fi, ai])`, which silently overwrites. The Python resolver mirrors that contract so its output matches what the runtime would return for the same input. The paragraph-level row is written after the page-level row, so by "last write wins" the resolver returns `file#anchor` (not bare `file`) whenever a paragraph anchor exists — which is the user-friendly default.
- **Inter chunk file/anchor indices, then resolve.** Each `_lx.js` chunk's `e` tuples reference local indices into that chunk's `f` and `a` arrays. The resolver merges chunks the same way `Landmarks.Advance()` does: build a global `f`/`a` table with a `(string → global index)` interning dict, remap each chunk's `e` rows through `(local fileIdx → global fileIdx, local anchorIdx → global anchorIdx)`, then write into a single `{id: (globalFileIdx, globalAnchorIdx)}` map. This matches the runtime's merge semantics exactly.
- **JS parsing strategy: regex-extract the JSON-shaped object literal, then `json.loads`.** The chunk file is always `var landmarks = { ... };Landmarks.Advance(landmarks);` with the inner object using JSON-compatible syntax (double-quoted keys, double-quoted strings, integer indices, arrays). A targeted regex extracts the substring between `landmarks =` and `};Landmarks.Advance`, then standard `json.loads` parses it. No JavaScript runtime, no third-party JS parser. Rejected: full Esprima-via-py since the input is already JSON-shaped; rejected: line-based scanning since chunk files have no guaranteed line breaks.
- **Match the runtime's anchor formatting: empty anchor → bare file path; non-empty anchor → `file#anchor`.** This matches `GetPathById` in `scripts/landmarks.js` exactly.
- **Two CLI modes:** `resolve <id> [--from <path>]` returns the resolved relative path (and JSON metadata with `--json`); `rewrite <url> [--from <path>] [--base-url <url>]` rewrites a full stable URL into a direct URL. `--from` accepts either a single `_lx.js` file or a directory; the resolver discovers all `*_lx.js` files when given a directory. A `dump --from <path>` mode emits the complete `{id: relative_path}` map as JSON for downstream tooling. Three modes keep the surface narrow; broader tooling (pre-built lookup tables, remote fetching) goes through these primitives.
- **Local file system only in v1.** Remote `_lx.js` fetching (the "static.webworks.com" scenario from the issue) is deferred; v1 supports any directory the user can resolve locally, which covers the AI consumer case via a downloaded mirror.
- **No additional Python dependencies.** Standard library only (`argparse`, `json`, `re`, `pathlib`, `sys`, `os`). The existing reverb2 scripts already follow this convention; adding a dependency just for this script would be out of proportion.

## Assumptions

- The `_lx.js` JS object literal will remain JSON-compatible in shape (double-quoted keys, JSON-legal value types). This has held since Reverb 2.0 shipped and the regex-then-`json.loads` strategy assumes it. If future Reverb releases switch to ES-only syntax (single quotes, trailing commas, comments), the parser will need to escalate. Documenting this as an assumption so the failure mode is obvious if it ever fires.
- The full set of `*_lx.js` files in a Reverb output directory is the complete landmark dataset. The runtime relies on `Parcels.landmarks` to enumerate them; v1 of the resolver relies on directory globbing, which produces the same set in every Reverb output observed today.
- One landmark ID may appear in multiple `_lx.js` chunks (cross-group references in dual-group output) and across multiple `(file, anchor)` rows within a chunk. "Last write wins" returns one canonical resolution per ID — typically the paragraph-level form `file#anchor`. If a future requirement needs every binding, U1's `dump` mode is the place to add a `--all-bindings` flag; not in v1.
- Issue #52 (the blocker named in the issue body) is merged on `main` and not gating this work. Recent commit `cbc1c64` confirms the merge.

## High-Level Technical Design

This sketch illustrates the intended approach and is directional guidance for review, not implementation specification.

```
parse a single _lx.js chunk
  → read text → regex-strip `var landmarks = ` prefix and `};Landmarks.Advance(landmarks);` suffix
  → json.loads → {"f": [...], "a": [...], "e": [[fi,ai,id], ...]}

merge N chunks into one global index
  → global_files = []                  # global f
  → global_anchors = []                # global a
  → file_index = {}                    # string → global f index
  → anchor_index = {}                  # string → global a index
  → id_to_pair = {}                    # id → (global_fi, global_ai)
  → for each chunk:
      build local→global maps for that chunk's f and a
      for each [local_fi, local_ai, id] in chunk.e:
          id_to_pair[id] = (file_map[local_fi], anchor_map[local_ai])   # last-write wins

resolve(id)
  → pair = id_to_pair.get(id)        — None if unknown
  → file = global_files[pair[0]]
  → anchor = global_anchors[pair[1]]
  → return f"{file}#{anchor}" if anchor else file

rewrite(stable_url, base_url=None)
  → split into <prefix>#/<id>[?query|#extra-ignored]
  → resolved = resolve(id)
  → return (base_url or inferred prefix) + resolved
```

## Output Structure

```
plugins/webworks-claude-skills/skills/reverb2/
  scripts/
    resolve-landmarks.py          (new — U1)
  tests/
    fixtures/
      single-chunk_lx.js          (new — U2)
      multi-chunk-a_lx.js         (new — U2)
      multi-chunk-b_lx.js         (new — U2)
    verify-landmark-resolver.py   (new — U2)
  workflows/
    landmark-resolution.md        (new — U3)
  SKILL.md                        (modified — U4)
```

Plus:

```
plugins/webworks-claude-skills/skills/epublisher/references/
  product-foundations.md          (modified — U5)

plugins/webworks-claude-skills/.claude-plugin/plugin.json   (modified — U6)
.claude-plugin/marketplace.json                              (modified — U6)
```

## Implementation Units

### U1. Build `resolve-landmarks.py`

**Goal:** Implement the core resolver as a single Python script: parse one or many `_lx.js` files, build the merged landmark index, and expose `resolve`, `dump`, and `rewrite` modes via a CLI that matches the conventions of the existing reverb2 scripts.

**Requirements:** parsing, merging, opaque-ID lookup, anchor formatting, three usage modes (see Requirements Traceability above).

**Dependencies:** none.

**Files:**
- `plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py` — new file.

**Approach:**

- Mirror the structure of `plugins/webworks-claude-skills/skills/reverb2/scripts/parse-url-maps.py`:
  - Shebang `#!/usr/bin/env python3`, module docstring with usage examples.
  - ANSI color constants, `DEBUG` env var, `debug_log`/`error_log`/`success_log` helpers.
  - `argparse` with subcommands (`resolve`, `rewrite`, `dump`); print JSON to stdout by default; `--table` for human-readable in `dump` mode.
  - Non-zero exit code on resolution failure or parse failure so the script composes cleanly in `bash &&` pipelines.
- Build three internal functions:
  - `parse_chunk(path) -> dict` — read file, regex-extract the object literal, `json.loads`, return `{"f": [...], "a": [...], "e": [[fi,ai,id], ...]}`. Tolerate trailing whitespace and CRLF; reject anything that does not match the expected shape with a clear error mentioning the file path.
  - `build_index(chunk_paths) -> (list[str], list[str], dict[str, tuple[int,int]])` — iterate chunks, intern file/anchor strings into global lists, remap each chunk's `e` rows, populate the id→(fi,ai) dict using "last write wins". Skip rows where `id` is empty or indices are out of range, matching the runtime's defensive `continue`.
  - `resolve_id(id, files, anchors, id_to_pair) -> Optional[str]` — return `f"{files[fi]}#{anchors[ai]}"` when `anchors[ai]` is non-empty, otherwise the bare `files[fi]`; return `None` if the ID is not in the index.
- Add a `discover_chunks(source) -> list[Path]` helper:
  - If `source` is a `.js` file, return `[source]`.
  - If `source` is a directory, return `sorted(source.glob("*_lx.js"))`.
  - Empty result → clear error referencing the input path so the user can see what was searched.
- `rewrite` mode parses an input URL of the form `<prefix>#/<id>` (any non-empty string after `#/` is the ID); strips an optional `?` or `&` suffix; returns `<prefix> + resolved_path`. When `--base-url` is supplied it replaces the inferred prefix.
- Exit codes: `0` on successful resolution; `1` on resolution failure (ID not found); `2` on parse/IO failure. Document these in the module docstring.

**Patterns to follow:**

- Argparse + subcommand shape, log helpers, JSON-first output, `Path(...).exists()` guards, exception → `error_log` → return error — see `plugins/webworks-claude-skills/skills/reverb2/scripts/parse-url-maps.py` lines 1-178.
- Module docstring shape (usage examples, output description) — same file.
- Reference implementation for `build_index` semantics — `Landmarks.Advance()` in any Reverb 2.0 output's `scripts/landmarks.js`. The `dset(D.ids, id, [fi, ai])` overwrite is the contract to preserve.

**Test scenarios:**

- *Happy: single-chunk resolve.* Given a chunk where the `e` array contains `[0, 1, "abc123"]` and `f[0]="Group/page.html"`, `a[1]="wwp200"`, `resolve abc123 --from single-chunk_lx.js` returns `Group/page.html#wwp200`.
- *Happy: page-level resolution.* Given a chunk row `[0, 0, "abc"]` and `a[0]=""`, `resolve abc` returns `Group/page.html` with no trailing `#`. This is the runtime's anchor-formatting contract.
- *Happy: paragraph-level overrides page-level (last write wins).* Given both `[0, 0, "id1"]` and `[0, 2, "id1"]` in the same chunk (with `a[0]=""`, `a[2]="wwp100"`), `resolve id1` returns `page.html#wwp100`. Asserts that the order of `e` rows produces the paragraph anchor, matching the runtime's overwrite semantics.
- *Happy: multi-chunk merge.* Given two chunks A and B with overlapping file strings (e.g. both list `"shared/index.html"` as their first `f` entry), a `resolve` of an ID from chunk B returns the correct path. Asserts that local→global index remapping is correct.
- *Happy: ID format opacity.* Resolve a 16-char hex ID, an 8-char hex ID (`"abcdef12"`), and a pass-through source ID (`"getting-started-overview"`). All three resolve successfully. No code path checks ID length or character class.
- *Happy: directory mode.* Point `--from` at a directory containing three `*_lx.js` chunks; `dump` returns the union of every chunk's IDs as JSON.
- *Edge: ID not found.* `resolve nonexistent --from <chunk>` exits non-zero with a JSON `{"error": "ID not found", "id": "nonexistent"}` to stdout (or stderr in `--quiet` mode).
- *Edge: empty `e` array.* A chunk with `"e": []` parses without error and contributes no IDs to the index.
- *Edge: malformed `_lx.js`.* A file missing the `var landmarks =` prefix or the trailing `};Landmarks.Advance(...)` exits with code 2 and an error pointing at the file path. Asserts that the parser fails loudly rather than producing an empty index.
- *Edge: out-of-range index in `e`.* A row `[99, 0, "id"]` against an `f` array of length 2 is skipped (matching the runtime's `if (fi === undefined || ai === undefined || !id) continue;`).
- *Edge: stable URL with no ID.* `rewrite "https://example/help/#/" ` exits non-zero with a clear error; the regex requires at least one character after `#/`.
- *Rewrite: full stable URL.* `rewrite "https://static.webworks.com/docs/epublisher/latest/help/#/e5d3d31c42d8d1d4" --from <dir>` returns the corresponding `https://static.webworks.com/docs/epublisher/latest/help/<path>` direct URL. The prefix before `#/` is preserved.
- *Rewrite: with `--base-url` override.* Same input with `--base-url https://other.example/help/` returns the direct URL under the override prefix.
- *Integration: real fixture.* Run `resolve` against a fixture extracted from `Help/en/FAQs_lx.js` for a known ID; the output matches what `GetPathById` would have returned (verified by hand against the chunk's `f` and `a` arrays).

**Verification:**

- `python plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py resolve <id> --from <fixture-dir>` prints the expected file path (with or without anchor) and exits 0.
- `--help` text lists all three subcommands and their flags.
- Module docstring shows the same three exit codes documented in Approach above.

---

### U2. Add fixtures and a verification script

**Goal:** Ship a small, self-contained test surface so the resolver's behavior can be confirmed without a full Reverb output checkout. The reverb2 skill does not have a formal `pytest` setup today (see Patterns), so this follows the existing skill convention: sample fixtures plus a runnable verification script that exercises every test scenario from U1.

**Requirements:** verification of every U1 test scenario.

**Dependencies:** U1 (the script must exist).

**Files:**
- `plugins/webworks-claude-skills/skills/reverb2/tests/fixtures/single-chunk_lx.js` — new, minimal handcrafted chunk with known IDs covering page-level and paragraph-level rows, opaque ID variants (16-char, 8-char, pass-through), and one row whose index is intentionally out of range.
- `plugins/webworks-claude-skills/skills/reverb2/tests/fixtures/multi-chunk-a_lx.js` — new, first chunk of a two-chunk pair sharing one file string with chunk B.
- `plugins/webworks-claude-skills/skills/reverb2/tests/fixtures/multi-chunk-b_lx.js` — new, second chunk of the pair, with at least one ID that only exists in this chunk.
- `plugins/webworks-claude-skills/skills/reverb2/tests/verify-landmark-resolver.py` — new, standalone Python script that imports `resolve-landmarks.py` (or invokes it as a subprocess), runs each U1 test scenario, and prints a `PASS`/`FAIL` summary with non-zero exit on any failure.

**Approach:**

- Fixtures are tiny by design — three to five `f` entries, four to six `a` entries (including `""` at index 0 to match the real format), and a handful of `e` rows that exercise the cases above. Keep them small enough that a reader can hand-resolve any ID to verify the assertions.
- `verify-landmark-resolver.py` uses only the standard library. It is not pytest; it is a runnable verifier so the conventions match the existing reverb2 scripts and so a CI step can be a single `python` invocation. Each scenario is a function that calls into the resolver and prints `PASS:` / `FAIL:` lines. The script exits 0 only when every scenario passes.
- Prefer invoking the resolver via `subprocess.run` for the CLI surface tests (exit codes, JSON output to stdout, error messages to stderr). For internal-function tests (`build_index`, `resolve_id`, parsing), import the resolver as a module. Cover both — the script's CLI is part of the contract.
- Do not add `pytest` or any third-party test runner. The "skill plugin" repo intentionally has no Python test harness today; introducing one for this PR is out of scope (see Scope Boundaries).

**Patterns to follow:**

- Sample-fixture-in-tests pattern — see `plugins/webworks-claude-skills/skills/automap/tests/sample.waj` and `sample.wxsp`.
- Standalone-Python-script + ANSI color status output — see the existing reverb2 scripts.

**Test scenarios:**

Test expectation: none (this unit is itself the test layer). Verification is by running `verify-landmark-resolver.py` and observing that every U1 test scenario emits `PASS:` and the script exits 0.

**Verification:**

- `python plugins/webworks-claude-skills/skills/reverb2/tests/verify-landmark-resolver.py` exits 0 with every scenario reporting `PASS:`.
- Each fixture file parses successfully with `node -e "$(cat fixture.js); console.log(landmarks)"` (sanity check that the fixtures match real Reverb output's JavaScript shape — not a required CI step, but a one-time confirmation while authoring the fixtures).

---

### U3. Add `workflows/landmark-resolution.md`

**Goal:** Document the resolver from the skill's perspective: when to use it, what inputs it expects, what output it produces, and which CLI mode fits which scenario. Mirror the shape of `workflows/csh-analysis.md` so the resolver is discoverable through the normal SKILL.md intake → routing flow.

**Requirements:** discoverability of the new capability from inside the skill.

**Dependencies:** U1 (the script being documented).

**Files:**
- `plugins/webworks-claude-skills/skills/reverb2/workflows/landmark-resolution.md` — new file.

**Approach:**

- Open with `*From SKILL.md intake item 5.*` (the new intake option introduced in U4).
- Sections mirror `workflows/csh-analysis.md`:
  - `<required_reading>` — point readers at `references/` only when needed; this workflow needs no extra reference reading.
  - `<process>` — five steps: (1) identify input (local dir, single chunk, or a stable URL), (2) run `resolve-landmarks.py` in the matching mode, (3) interpret the output, (4) handle "ID not found", (5) optionally rewrite a list of stable URLs in bulk.
  - `<success_criteria>` — checklist mirroring the csh-analysis pattern.
- Include a concrete worked example: a stable URL from `product-foundations.md` rewritten via the resolver to a direct URL, with the command line shown.
- Explicitly note the v1 limitation: requires local access to `_lx.js` chunks. For URLs hosted on `static.webworks.com`, the user must download the help mirror first (or wait for the deferred remote-fetch capability — see Scope Boundaries).

**Patterns to follow:**

- `plugins/webworks-claude-skills/skills/reverb2/workflows/csh-analysis.md` — section layout, `<process>` / `<success_criteria>` tag pairing, table styling.

**Test scenarios:**

Test expectation: none — this is a workflow document (prose, no executable code). Verification is by reading the file against the intent above.

**Verification:**

- File exists at the path above and parses as valid markdown.
- The worked example's CLI invocation matches U1's actual CLI flags (verified by running the example end-to-end during authoring).
- All file paths in the document are repo-relative.

---

### U4. Wire the workflow into `reverb2/SKILL.md`

**Goal:** Make the new capability reachable through the skill's standard intake/routing flow so an agent invoked on "resolve this Reverb hash URL" loads the right workflow.

**Requirements:** discoverability + intake parity with the other four workflows already wired into SKILL.md.

**Dependencies:** U3 (workflow doc to point at).

**Files:**
- `plugins/webworks-claude-skills/skills/reverb2/SKILL.md` — modify.

**Approach:**

- Add intake option 5: "Resolve a stable Reverb landmark URL (or hash) to a direct file path" under the existing `<intake>` block.
- Add a row to the `<routing>` table mapping `5`, `"resolve"`, `"landmark"`, or `"hash"` to `workflows/landmark-resolution.md`.
- Add a row to the `<capabilities>` table with feature `Landmark Resolution`, script `resolve-landmarks.py`, description `Resolve Reverb stable URLs (#/<id>) to direct file paths using _lx.js chunks`.
- No other edits to SKILL.md. The change is additive; the existing four intake items stay in place.

**Patterns to follow:**

- `<intake>`, `<routing>`, and `<capabilities>` sections of `plugins/webworks-claude-skills/skills/reverb2/SKILL.md` (lines 48-83). Match the table column widths and the trigger-word style of the existing routing rows.

**Test scenarios:**

Test expectation: none — this is SKILL.md content (prose tables, no executable code). Verification is by reading the diff against the patterns above.

Manual verification scenarios:

- An agent invoked with "I have a Reverb hash URL like `#/e5d3d31c42d8d1d4`, what file does it point to?" routes to `workflows/landmark-resolution.md` via the new routing row.
- The capabilities table now lists five capabilities, in the same column shape as the existing four.

**Verification:**

- `git diff plugins/webworks-claude-skills/skills/reverb2/SKILL.md` shows additions only — no edits to existing rows in `<intake>`, `<routing>`, or `<capabilities>`.
- The intake item count matches the routing row count and the capabilities row count.

---

### U5. Point `product-foundations.md` at the resolver

**Goal:** Replace the hand-maintained "stable link + direct link" footnote in `product-foundations.md` with a one-line pointer to the resolver, so the dual-link maintenance burden disappears and future stable-URL references in skill docs no longer need a hand-curated direct fallback.

**Requirements:** "Convert stable links in skill documentation to direct file URLs for AI consumption" (issue body, Usage scenarios).

**Dependencies:** U1 (the resolver must exist), U3 (the workflow doc to point at).

**Files:**
- `plugins/webworks-claude-skills/skills/epublisher/references/product-foundations.md` — modify lines 9-11 (the XSLT extensions stable+direct link pair).

**Approach:**

- Keep the stable URL — it is the authoritative published location. Drop the parenthetical "(requires JavaScript)" caveat, since the resolver now removes that constraint.
- Drop the second bullet (the direct link), since maintaining a hand-mirrored direct URL is exactly what the resolver replaces. Replace with one sentence pointing to the resolver and its workflow doc: *"To resolve any `#/<id>` URL to a direct file path without a JavaScript runtime, use the `reverb2` skill's landmark-resolution workflow (see `plugins/webworks-claude-skills/skills/reverb2/workflows/landmark-resolution.md`)."*
- Do not add new stable-URL references to other docs as part of this PR. The product-foundations entry is the only existing hand-maintained dual link; widening the scope to scan every skill doc for similar patterns is deferred.

**Patterns to follow:**

- The existing bullet-list shape inside `## Platform and Runtime` — see `plugins/webworks-claude-skills/skills/epublisher/references/product-foundations.md` lines 7-12. The replacement keeps the same indentation and the same bullet sibling-set.

**Test scenarios:**

Test expectation: none — this is a documentation edit. Verification is by reading the diff.

Manual verification:

- After the edit, an agent reading `product-foundations.md` and encountering the stable URL has a one-hop pointer to the resolver workflow.
- The published stable URL still appears in the file (so the file remains useful as a published-doc reference), but the direct-URL fallback is gone.

**Verification:**

- `git diff plugins/webworks-claude-skills/skills/epublisher/references/product-foundations.md` shows the replacement is contained to the two existing bullets and the immediately surrounding lines; no other section is touched.
- The pointer to `workflows/landmark-resolution.md` uses a repo-relative path.

---

### U6. Bump plugin version 2.10.0 → 2.11.0

**Goal:** Apply the project's required version bump so the new resolver ships under a new minor version, per `CLAUDE.md` ("minor: new skills, new features"). A new script and a new workflow inside an existing skill is an additive feature, so this is a minor bump, not a patch.

**Requirements:** Project convention (not an origin issue requirement, but mandated by repo `CLAUDE.md`).

**Dependencies:** U1, U2, U3, U4, U5 (all the shipping work must exist before the version that ships it is committed).

**Files:**
- `plugins/webworks-claude-skills/.claude-plugin/plugin.json` — `version` field.
- `.claude-plugin/marketplace.json` — `version` field.

**Approach:**

- Run `scripts/bump-version.sh minor`. The script reads `plugin.json`, increments the minor (2.10.0 → 2.11.0), zeros the patch, and writes the same version into both manifests. Same workflow used by U2 of the most recent merged PR (see `2026-05-19-002-feat-claude-md-audit-skill-plan.md` U2).
- Do not hand-edit the JSON files — using the script is the documented workflow in `CLAUDE.md`.

**Patterns to follow:**

- `scripts/bump-version.sh` — the canonical bump path.

**Test scenarios:**

Test expectation: none — this is a metadata bump. Verification is by reading the diff.

**Verification:**

- Both manifests show `"version": "2.11.0"`.
- `git diff --stat` shows changes only to the two manifest files in this unit (other units contribute their own files).

---

## Scope Boundaries

### In scope

- Python resolver script with `resolve`, `dump`, and `rewrite` modes.
- Local file system input only (single `_lx.js` file or a directory containing chunks).
- Fixtures + standalone Python verification script.
- Workflow doc + SKILL.md wiring.
- One-line update to `product-foundations.md` replacing the hand-maintained direct-link fallback.
- Minor version bump.

### Out of scope

- **Not generating new landmark IDs.** This is read-only client tooling; ID generation lives in the Reverb output pipeline, not in this skill.
- **Not modifying the Reverb runtime (`scripts/landmarks.js`).** The resolver mirrors the runtime's existing behavior; it does not change it. In particular, the runtime's hard-coded 16-char regex in `ExtractLandmark` is left alone — that is Reverb format work, not skill work.
- **Not adding `pytest` (or any third-party test framework) to the plugin.** The skill plugin has no Python test harness today; the standalone verification script keeps tooling consistent with the rest of the repo.
- **Not scanning the entire skill-docs tree for additional stable-URL references to rewrite.** U5 updates the one existing instance (in `product-foundations.md`); auditing every reference doc for additional dual-link patterns is a separate, follow-up task.

### Deferred to Follow-Up Work

- **Remote `_lx.js` fetching** (the "static.webworks.com" usage scenario from the issue). A `--remote-base-url` flag that downloads chunks over HTTP, optionally caching them, is a natural follow-on. Out of v1 because it adds HTTP retries, caching, and proxy handling that are not load-bearing for the AI-consumer case where the help mirror can be downloaded once.
- **Pre-built lookup table** (the "implementation option 3" from the issue). Once the resolver exists, a one-time `dump --from <dir>` against the published ePublisher help can produce a static JSON map that other skills could ship with. Out of v1; design depends on which products' help to bake in and how to keep the snapshots fresh.
- **Reverse lookup** (`path → id`). The runtime has `GetIdByPath`; the resolver's `build_index` already populates the data to support this. Not added until a concrete user surfaces.
- **Tightening Reverb's `ExtractLandmark` regex to accept the new 2026.1 ID formats** (8-char hex, pass-through source IDs). The runtime currently requires `[A-Za-z0-9]{16}`; the regex would need to be loosened (or replaced with a non-greedy capture) for the 2026.1 opt-in formats to round-trip through the JavaScript runtime. This is Reverb format work, not skill work, and would need to be filed against the Reverb 2.0 format source rather than this plugin.

## Risks and Mitigations

- **Risk: JS object literal drifts from JSON-compatible shape in a future Reverb release.** Mitigation: the parser fails loudly (exit code 2) on shape mismatch rather than producing wrong answers; the "Assumptions" section documents this so a future regression is easy to spot. If/when Reverb starts emitting ES-only syntax, the parser would need to escalate to a real JS parser, but that change is out of v1.
- **Risk: a future Reverb release adds chunk-file naming we do not glob.** Mitigation: the `discover_chunks` helper's glob (`*_lx.js`) matches the naming used by every Reverb 2.0 output observed today and by the Reverb 2026.1 output sampled while planning. If a future release changes the suffix, the directory mode falls back to "no chunks found" with a clear error, and the single-file mode still works for any explicit file path.
- **Risk: misuse — calling the resolver against a chunk subset and getting partial results.** Mitigation: directory mode globs all `*_lx.js` chunks by default; the workflow doc calls out that resolving against a single chunk only covers IDs in that group. The script's `dump` output makes the input scope explicit.
- **Risk: "last write wins" semantics surprise a caller who expects every binding.** Mitigation: the chosen behavior matches the runtime exactly, which is the contract callers should expect. The `--all-bindings` extension is noted as a clean follow-on in Scope Boundaries.

## System-Wide Impact

- **`reverb2` skill** — gains a new script, workflow, and SKILL.md entry. No removal of existing capabilities.
- **`epublisher` skill** — one paragraph in `product-foundations.md` changes shape (stable link + direct link → stable link + resolver pointer). Behavior remains the same; maintenance burden decreases.
- **Plugin manifests** — minor version bump.
- **No changes to** `automap`, `markdown-integration`, `claude-md-audit` skills, the AutoMap CLI, or any Reverb format source.
