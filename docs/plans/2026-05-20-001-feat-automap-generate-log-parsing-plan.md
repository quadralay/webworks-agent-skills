---
title: "feat: AutoMap wrapper parses generate.log for post-build warnings and errors"
type: feat
status: active
date: 2026-05-20
origin: docs/brainstorms/2026-05-20-issue-50-automap-generate-log-parsing-requirements.md
---

# AutoMap Wrapper Parses `generate.log` for Post-Build Warnings and Errors

## Summary

After a successful AutoMap build (exit 0), the wrapper scans every `Logs/<TargetName>/generate.log` under the project directory, counts `[WARN]` and `[ERROR]` lines per target, and emits a yellow/red summary line per target that has non-zero counts. `--verbose` additionally echoes the extracted lines grouped under a per-target header. The wrapper's exit code remains unchanged.

---

## Problem Frame

`plugins/webworks-claude-skills/skills/automap/scripts/automap-wrapper.sh` currently treats AutoMap's exit code as the sole signal of build health, so builds that succeed (exit 0) but record `[WARN]`/`[ERROR]` lines in `Logs/<TargetName>/generate.log` (e.g., PDF generation skipped, legacy format warnings) go silent. The fix is observational: scan what AutoMap already wrote and surface it before the wrapper exits.

See origin: [docs/brainstorms/2026-05-20-issue-50-automap-generate-log-parsing-requirements.md](../brainstorms/2026-05-20-issue-50-automap-generate-log-parsing-requirements.md).

---

## Requirements

Carried from origin verbatim (R-IDs map 1:1 with the brainstorm). Origin actors/flows/acceptance-examples sub-trace omitted — origin is feature-shape with R/AE IDs only.

- R1. The log scan runs only on AutoMap exit code 0.
- R2. The scan runs after `[SUCCESS] Build completed in Ns` and before the wrapper itself exits 0.
- R3. The log root is derived from `dirname` of the project file argument: `<project_dir>/Logs/`.
- R4. The scan discovers logs by globbing `<project_dir>/Logs/*/generate.log`; it does not re-enumerate targets from `-t`, `--target=`, `--all-targets`, or job-file `build="True"` attributes.
- R5. If `<project_dir>/Logs/` is missing or contains no `generate.log` files, no summary line is emitted and the wrapper still exits 0.
- R6. Line detection extracts literal `[WARN]` and `[ERROR]` substrings, case-sensitive.
- R7. Multiple consecutive `[WARN]` lines (including blank lines between them) are all captured.
- R8. No parsing, categorization, deduplication, or filtering beyond extraction.
- R9. **Default mode:** one summary line per target with non-zero counts: `[WARN] <N> warning(s), <M> error(s) in Logs/<TargetName>/generate.log`. Targets with all zeros emit nothing.
- R10. **Verbose mode (`--verbose`):** in addition to R9 summaries, echo every extracted line, grouped by target, with a target header.
- R11. Summary lines route through `log_warning` (yellow) when warnings dominate or stand alone, `log_error` (red) when the target has any errors. (Resolved during planning — see Open Questions below.)
- R12. The log path printed in the summary is relative to the project directory (e.g., `Logs/Reverb2/generate.log`).
- R13. The wrapper's exit code is unchanged by the scan. Exit 0 stays exit 0.
- R14. Scan failures (permission denied, read errors, encoding issues) are swallowed; the wrapper still exits 0.
- R15. Target names containing spaces and non-ASCII characters are handled (proper quoting on glob iteration).

**Origin acceptance examples:** AE1 (covers R1, R2, R5, R13), AE2 (covers R3, R4, R6, R9, R11, R12), AE3 (covers R4, R9), AE4 (covers R7, R10), AE5 (covers R13), AE6 (covers R14).

---

## Scope Boundaries

- Not promoting warnings to non-zero exit codes (no `--fail-on-warning` in this change).
- Not filtering, deduplicating, or interpreting `[WARN]`/`[ERROR]` content — surface verbatim.
- Not parsing the log for `Total time:` or any timing reconciliation against the wrapper's own timing.
- Not scanning logs on AutoMap exit ≠ 0 (the existing `parse_automap_output` covers that path).
- Not enumerating targets from project/job files for the scan (filesystem-driven discovery only).
- Not adding a Python helper — wrapper stays bash.
- Not modifying any other script (`detect-installation.sh`, `parse-job.py`, etc.) except as required to keep the scan localized to `automap-wrapper.sh`.
- Not bumping the plugin version in the same change as the plan artifact (handled at PR time per project `CLAUDE.md`).

### Deferred to Follow-Up Work

- Opt-in `--fail-on-warning` / `--fail-on-error` flag for CI/CD callers that want gating: separate issue once this lands and we see real-world warning volume.
- Handling of alternative log paths (e.g., `Output/<TargetName>/Logs/`, top-level `automap.log`) if a future AutoMap version writes elsewhere: extend the discovery glob then.

---

## Context & Research

### Relevant Code and Patterns

- `plugins/webworks-claude-skills/skills/automap/scripts/automap-wrapper.sh` — single file under change. Key existing surfaces this plan integrates with:
  - `log_info` / `log_success` / `log_warning` / `log_error` / `log_verbose` helpers (lines 60-82) — color routing and stdout vs. stderr policy.
  - `parse_automap_output` (lines 412-448) — precedent for line-by-line classification and helper routing; the scan's verbose-mode line iteration follows the same pattern (route to `log_warning` or `log_error` based on the marker present).
  - `validate_project_file` (lines 301-320) — precedent for `cygpath`-then-unix-path handling. The scan reuses the same pattern to derive `<project_dir>`.
  - `execute_automap` (lines 450-481) — the call site where the scan hooks in after `log_success "Build completed in ${duration}s"`.
- `set -euo pipefail` is in effect (line 31). `grep -c` returns exit 1 when zero matches, so count expressions must be guarded (`|| true` or `(( count = $(grep -c …) || true ))` style).

### Institutional Learnings

- No `docs/solutions/` entry covers wrapper output parsing or log scanning. The closest related fix (`docs/plans/2026-03-02-fix-automap-script-path-resolution.md`) shifted the wrapper away from `grep -oP` for locale portability — keep using `grep -E` (BRE/ERE) with literal markers, not Perl-compatible patterns.

### External References

- AutoMap log format examples are documented in the issue body and brainstorm; no external lookup needed.

---

## Key Technical Decisions

- **Use two `grep -c` passes per log for counts, plus one `grep -E` pass for verbose-mode line extraction.** Resolves brainstorm Q1. Simpler than a single-pass-with-bash-counters approach; the log files are tens of KB at worst so the cost is negligible. Each count expression must be `|| true`-guarded to coexist with `set -euo pipefail`.
- **Verbose-mode per-target header style:** emit a single bracketed header line via `log_warning` (`[WARN] Warnings/errors in Logs/<Target>/generate.log:`), then iterate the extracted lines and route each to `log_warning` or `log_error` based on which marker (`[WARN]` or `[ERROR]`) the line contains. Resolves brainstorm Q2. This mirrors the existing `parse_automap_output` pattern (line-by-line classification with per-line helper routing) so output coloring stays consistent and a reader scanning yellow/red lines can still tell warnings from errors at a glance.
- **Summary-line helper choice:** route the summary through `log_error` (red, stderr) when the target's error count > 0; otherwise through `log_warning` (yellow, stdout). A target with `1 warning(s), 1 error(s)` is red. Reasoning: errors are the louder signal; if a CI script is grepping for `[ERROR]` on stderr, the summary line should appear there. Refines R11.
- **Filesystem discovery via bash glob with `nullglob`-equivalent guard.** Use `for log_file in "$project_dir/Logs"/*/generate.log; do [ -f "$log_file" ] || continue; ...; done`. Avoids `find`'s subprocess overhead, handles target names with spaces natively, and degrades gracefully when the glob matches nothing (the literal pattern is iterated once and skipped by the `-f` guard).
- **Project directory derivation:** mirror `validate_project_file`'s pattern — `project_dir=$(dirname "$(cygpath "$PROJECT_FILE" 2>/dev/null || echo "$PROJECT_FILE")")`. Keeps cygpath-fallback behavior consistent with the rest of the wrapper.
- **Scan function is pure-input/pure-output:** `scan_generate_logs <project_dir>` accepts the project directory as an explicit argument rather than reading the global `$PROJECT_FILE`. This makes the function unit-testable in isolation against a fixture tree without spinning up AutoMap.
- **Add a bash-level test script for the scan.** Resolves brainstorm Q4 — adding a fixture-bearing tests directory plus a tiny driver script gives R15 (space-bearing target names) real verification rather than relying on quoting review alone. Driver lives at `plugins/webworks-claude-skills/skills/automap/tests/test-generate-log-scan.sh`; it sources the function from `automap-wrapper.sh` (or re-implements the invocation pattern) and asserts expected output against captured fixtures.
- **Robustness via local `set +e` scope.** The scan helper wraps its body in `set +e` / explicit success exit, with `2>/dev/null` redirection on file reads, so any failure (permission denied, encoding hiccup, vanished log) cannot abort the wrapper under `set -euo pipefail`. Satisfies R14.
- **Relative-path display via parameter expansion.** Strip `$project_dir/` from the absolute log path: `relative_log="${log_file#"$project_dir"/}"`. Satisfies R12 without re-walking the path.

---

## Open Questions

### Resolved During Planning

- **Q1 (grep strategy) — resolved.** Two `grep -c` count passes plus one `grep -E` verbose-mode pass. See Key Technical Decisions.
- **Q2 (verbose header format) — resolved.** Single bracketed `log_warning` header per target, then per-line `log_warning`/`log_error` routing based on the marker the line contains. See Key Technical Decisions.
- **Q3 (project_dir derivation on Git Bash) — resolved.** `dirname` of the cygpath-converted path. Wrapper already uses this pattern at `validate_project_file`; reusing it keeps behavior consistent.
- **Q4 (space-bearing target fixture) — resolved.** Adding a fixture under `plugins/webworks-claude-skills/skills/automap/tests/fixtures/` and a driver script under `tests/` is the right level for a bash-only change. Quoting review alone is too weak for R15.
- **R11 ambiguity (which helper for summary lines) — resolved.** `log_error` when errors > 0, `log_warning` otherwise. Lifted into Key Technical Decisions for visibility.

### Deferred to Implementation

- Exact wording of the verbose-mode target header (e.g., `Warnings/errors in Logs/<Target>/generate.log:` vs. `[Logs/<Target>/generate.log]`). Implementer picks based on what reads cleanest alongside the routed yellow/red lines; both satisfy R10.
- Whether to surface the absolute log path in verbose mode alongside the relative one when the user is likely running outside the project directory. Defer — start with relative-only (matches R12) and revisit only if a user reports they couldn't find the file.
- Whether `grep -E '\[WARN\]|\[ERROR\]'` preserves the original line order from the log under all GNU/BSD grep variants on Git Bash. Defer to the test script — the fixture-based test asserts ordering directly.

---

## Implementation Units

### U1. Add `scan_generate_logs` helper and supporting line-router to `automap-wrapper.sh`

**Goal:** Introduce the log-scanning function and a per-line router used in verbose mode. Function is pure-input/pure-output (takes project directory as argument) and self-contained so it can be invoked from a test harness in U3.

**Requirements:** R3, R4, R5, R6, R7, R8, R9, R10, R11, R12, R14, R15.

**Dependencies:** None.

**Files:**
- Modify: `plugins/webworks-claude-skills/skills/automap/scripts/automap-wrapper.sh`

**Approach:**
- Define `scan_generate_logs()` as a new helper, placed alongside the other helpers (after `parse_automap_output`, before `execute_automap`).
- Signature: `scan_generate_logs <project_dir>`. Returns 0 unconditionally.
- Body outline (directional):
  - Resolve `logs_root="$1/Logs"`; if `[ ! -d "$logs_root" ]`, return 0.
  - Locally `set +e` (or wrap in a subshell) so glob/read failures cannot abort the wrapper.
  - Iterate `for log_file in "$logs_root"/*/generate.log; do [ -f "$log_file" ] || continue; ...; done`.
  - For each `log_file`: derive `target=$(basename "$(dirname "$log_file")")` and `relative_log="${log_file#"$1"/}"`.
  - Counts: `warn_count=$(grep -c '\[WARN\]' "$log_file" 2>/dev/null || true)` and `error_count=$(grep -c '\[ERROR\]' "$log_file" 2>/dev/null || true)`. Guard for empty string (treat as 0).
  - Skip emission when `warn_count -eq 0 && error_count -eq 0`.
  - Compose summary line: `summary="$warn_count warning(s), $error_count error(s) in $relative_log"`.
  - If `error_count -gt 0`: `log_error "$summary"`; else `log_warning "$summary"`.
  - In verbose mode: emit a single per-target header (`log_warning "Warnings/errors in $relative_log:"`), then `grep -E '\[WARN\]|\[ERROR\]' "$log_file" 2>/dev/null | while IFS= read -r line; do route_log_line "$line"; done`.
- Define `route_log_line()` helper (or inline in the while loop): if line contains `[ERROR]`, call `log_error "$line"`; else call `log_warning "$line"`.

**Patterns to follow:**
- Helper placement and style: see existing `parse_automap_output` (lines 412-448).
- `cygpath`-then-`dirname` pattern: see `validate_project_file` (lines 301-320).
- `while IFS= read -r line; do ...; done` pipe pattern: see `execute_automap` verbose branch (lines 462-464).

**Test scenarios:**
- *Happy path.* Single-target fixture with a `generate.log` containing 3 `[WARN]` lines and 0 `[ERROR]` lines produces one yellow line: `[WARN] 3 warning(s), 0 error(s) in Logs/Reverb2/generate.log`. Covers AE2.
- *Happy path.* Multi-target fixture: `Logs/Reverb2/generate.log` has 2 warnings; `Logs/PDF/generate.log` has 0 warnings and 1 error; `Logs/Clean/generate.log` has 0 of each. Output contains exactly one yellow line for Reverb2 and one red line for PDF, no line for Clean. Covers AE3.
- *Happy path (verbose).* Fixture with 3 consecutive `[WARN]` lines including a blank line between the second and third. With `VERBOSE=true`, output contains a single per-target header followed by all 3 yellow lines in original order. Covers AE4 + R7.
- *Edge case.* `Logs/` does not exist under the project dir — function returns silently, exit 0, no output. Covers AE1 + R5.
- *Edge case.* `Logs/` exists but contains no `generate.log` files (e.g., only an empty subdirectory) — function returns silently, no output. Covers R5.
- *Edge case.* Target directory name contains a space (`Logs/My Target/generate.log`) — summary line is emitted correctly: `[WARN] 1 warning(s), 0 error(s) in Logs/My Target/generate.log`. Covers R15.
- *Edge case.* Log file contains only one line, which is `[WARN]` — `warn_count=1`, `error_count=0`, summary line emitted. Verifies `grep -c` guard for single-line files.
- *Error path.* Log file is present but unreadable (e.g., empty file, or simulated by removing read permission where possible). Function continues to next target, does not abort, exits 0. Covers AE6 + R14.
- *Integration.* `grep -E '\[WARN\]|\[ERROR\]'` preserves the original line order from the log file (assert by comparing extracted lines to manually-ordered expectations in a fixture with interleaved markers).
- *Integration.* When called immediately after `log_success "Build completed in ${duration}s"`, the summary lines appear after the success line in the output stream.

**Verification:**
- New helper exists in the file with the signature `scan_generate_logs <project_dir>`.
- `bash -n plugins/webworks-claude-skills/skills/automap/scripts/automap-wrapper.sh` reports no syntax errors.
- `shellcheck plugins/webworks-claude-skills/skills/automap/scripts/automap-wrapper.sh` reports no new warnings (or pre-existing ones only).

---

### U2. Invoke `scan_generate_logs` from the main success path

**Goal:** Wire the new helper into the wrapper so a successful build triggers the scan before the wrapper exits 0. Failed builds are unchanged.

**Requirements:** R1, R2, R13.

**Dependencies:** U1.

**Files:**
- Modify: `plugins/webworks-claude-skills/skills/automap/scripts/automap-wrapper.sh`

**Approach:**
- Inside the main-execution block at the bottom of the file, modify the `if execute_automap "$automap_cmd"; then ... exit 0` branch:
  - Before `exit 0`, derive `project_dir` from `$PROJECT_FILE` using the same `cygpath`-then-`dirname` pattern as `validate_project_file`.
  - Call `scan_generate_logs "$project_dir"`.
  - Then `exit 0` unchanged.
- Do not call the scan in the else (failure) branch — the existing `log_error "Build failed ..."` and `parse_automap_output`-driven diagnostics cover that path.
- Do not change the exit code based on scan output. The wrapper's exit-code contract is fixed by AutoMap's exit code only.

**Patterns to follow:**
- Project-dir derivation: mirror `validate_project_file` (lines 301-320) for `cygpath` plus `dirname`.

**Test scenarios:**
- *Happy path.* Mock `execute_automap` to return 0 against a fixture project dir with one warning-bearing log; assert wrapper exits 0 and prints the expected summary after `[SUCCESS]`. Covers AE2 + R2 + R13.
- *Happy path.* Mock `execute_automap` to return 0 against a fixture with no `Logs/` directory; assert wrapper exits 0 with no extra output beyond `[SUCCESS]`. Covers AE1 + R5.
- *Error path.* Mock `execute_automap` to return non-zero; assert `scan_generate_logs` is NOT invoked (no summary line, no log scan messages). Covers R1.
- *Integration.* End-to-end against the existing `sample.waj` fixture is not feasible without invoking AutoMap; rely on the U3 test script to drive `scan_generate_logs` directly against fixtures.

**Verification:**
- The success branch calls `scan_generate_logs` exactly once with the project directory as argument.
- The failure branch does not call `scan_generate_logs`.
- Exit codes are unchanged (still 0 on AutoMap exit 0, still 1 on AutoMap exit non-zero).

---

### U3. Add log-scan fixtures and a bash test driver

**Goal:** Add fixture `generate.log` files and a tiny driver script that exercises `scan_generate_logs` in isolation. The driver makes R15 (space-bearing targets), R7 (multi-line warnings), R5 (missing-Logs), R9/R10 (default vs. verbose output), R12 (relative path), and R14 (read failures) verifiable without running AutoMap.

**Requirements:** R5, R7, R9, R10, R12, R14, R15.

**Dependencies:** U1.

**Files:**
- Create: `plugins/webworks-claude-skills/skills/automap/tests/fixtures/single-warning-target/Logs/Reverb2/generate.log`
- Create: `plugins/webworks-claude-skills/skills/automap/tests/fixtures/multi-target/Logs/Reverb2/generate.log`
- Create: `plugins/webworks-claude-skills/skills/automap/tests/fixtures/multi-target/Logs/PDF/generate.log`
- Create: `plugins/webworks-claude-skills/skills/automap/tests/fixtures/multi-target/Logs/Clean/generate.log`
- Create: `plugins/webworks-claude-skills/skills/automap/tests/fixtures/space-target/Logs/My Target/generate.log`
- Create: `plugins/webworks-claude-skills/skills/automap/tests/fixtures/no-logs-dir/.gitkeep` (project dir without a Logs/ subdirectory)
- Create: `plugins/webworks-claude-skills/skills/automap/tests/test-generate-log-scan.sh`

**Approach:**
- Fixtures hand-rolled to mirror the issue body's sample format: timestamps, `[WARN]` lines with the same wording, plus `[ERROR]` lines for the multi-target case. Include the blank-line-between-`[WARN]`s pattern in at least one fixture (R7).
- Test driver is a thin bash script that:
  - Sources `automap-wrapper.sh` in a mode that defines the helpers without running the main flow. Options:
    - **Option A (preferred):** wrap the main-execution block in `if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then ... fi` so sourcing the file does not run the main flow. This is the conventional bash idiom and keeps the test driver simple. Costs one small edit to `automap-wrapper.sh` (counted under U1 to keep U3 fixture-and-test-only).
    - **Option B (fallback):** if the wrap-main-in-if-sourced idiom is rejected at review, copy `scan_generate_logs` into the test driver. Lossier but works.
  - For each fixture, call `scan_generate_logs <fixture_dir>`, capture stdout+stderr, and diff against a `.expected` reference file.
  - Run each fixture twice: once with `VERBOSE=false`, once with `VERBOSE=true`.
  - Exits non-zero on any diff failure.
- The driver does NOT exercise the full wrapper (U2's call site). U2 verification is via code inspection plus the U1 unit-level fixture tests.

**Execution note:** Write the fixtures and at least the first assertion before implementing U1's helper, so the helper has concrete expected output to satisfy. Characterization-first for this unit, since the output format is the contract.

**Patterns to follow:**
- Bash `if sourced` idiom: standard `[[ "${BASH_SOURCE[0]}" == "${0}" ]]` guard.
- Diff-based assertions: simpler than a test framework and consistent with the bash-only constraint.

**Test scenarios:**
- *Happy path.* Driver run against the `single-warning-target` fixture (no verbose) produces exactly: `[WARN] 3 warning(s), 0 error(s) in Logs/Reverb2/generate.log`. Covers AE2.
- *Happy path.* Driver run against `multi-target` (no verbose) produces one yellow line for Reverb2 (`2 warning(s), 0 error(s)`) and one red line for PDF (`0 warning(s), 1 error(s)`), with no line for `Clean`. Covers AE3.
- *Happy path (verbose).* Driver run against `single-warning-target` (verbose) produces the summary line followed by a per-target header and all 3 `[WARN]` lines (including the one preceded by a blank line) in original order. Covers AE4 + R7.
- *Edge case.* Driver run against `space-target` (no verbose) produces `[WARN] 1 warning(s), 0 error(s) in Logs/My Target/generate.log`. Covers R15.
- *Edge case.* Driver run against `no-logs-dir` produces no output and exits 0. Covers AE1 + R5.
- *Error path.* Manually chmod-removing read permission on one fixture log (or simulating by overwriting with a directory) — driver still exits 0 with whatever output the other logs produced. Covers AE6 + R14. (Note: chmod behavior on Git Bash/Windows is partial; if the chmod path can't be exercised reliably on Windows, the driver skips this assertion with a note rather than failing.)

**Verification:**
- `bash plugins/webworks-claude-skills/skills/automap/tests/test-generate-log-scan.sh` exits 0 on a fresh worktree.
- Each fixture has a matching `.expected` reference file (default and verbose variants where applicable).
- Driver script is executable (`chmod +x` or invoked via `bash ...`).

---

### U4. Document the post-build log scan in `SKILL.md`

**Goal:** Add a short user-facing note to the automap skill so callers know to expect post-build warning summaries and where the log lives.

**Requirements:** Supports R9 and R12 (the user needs to know what the summary line means and where to look).

**Dependencies:** U1, U2.

**Files:**
- Modify: `plugins/webworks-claude-skills/skills/automap/SKILL.md`

**Approach:**
- Add a brief subsection (3-6 lines) under the existing wrapper-output discussion explaining:
  - The wrapper scans `Logs/<TargetName>/generate.log` after a successful build.
  - Targets with non-zero `[WARN]`/`[ERROR]` counts get a yellow or red summary line.
  - `--verbose` echoes the actual lines.
  - Exit codes are unchanged — the scan is observational.
- Where exactly to add this is an editorial judgment; reasonable home is alongside the existing exit-code / output discussion. Implementer picks based on the current section structure.

**Patterns to follow:**
- Existing tone and section style in `SKILL.md`.

**Test scenarios:**
- Test expectation: none — documentation update with no behavioral change.

**Verification:**
- New subsection exists in `SKILL.md`.
- No code blocks contradict U1/U2 behavior.
- Markdown renders cleanly (no broken headings or fences).

---

## System-Wide Impact

- **Interaction graph:** Only `automap-wrapper.sh` and its `tests/` siblings change. No other scripts or skills consume `generate.log` today, so there is no downstream coupling to update.
- **Error propagation:** Scan failures are intentionally swallowed (R14). The wrapper's exit code remains 100% controlled by AutoMap's exit code. CI callers grepping for `[ERROR]` on stderr will newly see the per-target summary line when errors are present — that is the intended observable change.
- **State lifecycle risks:** None. The scan only reads files AutoMap already wrote; nothing is created, modified, or deleted by the wrapper as a result of the scan.
- **API surface parity:** The wrapper is the single execution interface (per `SKILL.md`). No parallel surface needs the same change.
- **Integration coverage:** U3's fixture-and-driver harness covers the cross-layer scenarios that matter (helper × verbose flag × space-bearing targets × multi-target aggregation × missing-Logs). Full end-to-end through AutoMap is not in scope — AutoMap itself is the externalized dependency and is exercised in vendor regression.
- **Unchanged invariants:**
  - Wrapper exit-code contract (0/1/2/3/4) is unchanged.
  - `log_info` / `log_success` / `log_warning` / `log_error` / `log_verbose` helpers are unchanged.
  - `extract_targets`, `select_targets`, `validate_project_file`, `detect_automap_executable`, `build_automap_command`, `parse_automap_output`, `execute_automap` are unchanged except for the single call-site edit in `execute_automap`'s success branch (U2).
  - Existing argument parsing and CLI flags are unchanged. No new flags in this change.

---

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| `grep -c` returning exit 1 on zero matches aborts the wrapper under `set -euo pipefail`. | Every count expression uses `\|\| true` (and parses the result as 0 when empty). Verified by U3 fixture for the zero-match case. |
| `dirname` on a cygpath-converted Windows path returns the wrong directory on some Git Bash builds. | Mirror the exact `cygpath`-then-`dirname` pattern already used by `validate_project_file`; if that pattern is broken anywhere it is broken everywhere, so the wrapper's existing behavior catches it. |
| `grep -E '\[WARN\]\|\[ERROR\]'` reorders lines on some grep variants. | U3 fixture explicitly asserts ordering against an interleaved log. If a future grep variant reorders, the driver fails immediately. |
| `nullglob` is not enabled by default — when `Logs/*/generate.log` matches nothing, the literal pattern iterates once. | `[ -f "$log_file" ] \|\| continue` guard inside the loop handles the literal-pattern case explicitly, no `shopt` change needed. |
| `generate.log` written in UTF-16 (older Windows installs) confuses `grep`. | R14's swallow-and-continue covers this. Marker pattern returns zero matches; no false reporting, no abort. If users report this, follow-up work can add `iconv` detection. |
| Log files growing very large (multi-MB) make the double `grep -c` pass costly. | Brainstorm acceptance criteria note "tens of KB" expected size. If real-world logs grow beyond ~10 MB this becomes worth revisiting; not a launch blocker. |
| Adding fixtures with a space-bearing path name on Windows requires the worktree filesystem to preserve the space. | NTFS preserves spaces in directory names natively. The fixture-creation step in U3 verifies this on the developer's machine before commit. |

---

## Documentation / Operational Notes

- `SKILL.md` updated under U4 — the only doc impact.
- No `docs/solutions/` entry needed at plan time. If real-world warning surfacing exposes a recurring pattern (e.g., "PDF not created" warnings always trace to the same misconfiguration), capture that as a follow-up `docs/solutions/` learning rather than embedding it in the wrapper.
- Plugin version bump (`scripts/bump-version.sh patch`) happens at PR time per project `CLAUDE.md` — not part of this plan's implementation units.
- No rollout, migration, or monitoring concerns. The change is local to the wrapper and observable immediately on next build.

---

## Sources & References

- **Origin document:** [docs/brainstorms/2026-05-20-issue-50-automap-generate-log-parsing-requirements.md](../brainstorms/2026-05-20-issue-50-automap-generate-log-parsing-requirements.md)
- **Issue:** #50
- **Related prior fix:** `docs/plans/2026-03-02-fix-automap-script-path-resolution.md` (locale-portable grep precedent)
- **Wrapper source:** `plugins/webworks-claude-skills/skills/automap/scripts/automap-wrapper.sh`
- **Skill reference:** `plugins/webworks-claude-skills/skills/automap/SKILL.md`
