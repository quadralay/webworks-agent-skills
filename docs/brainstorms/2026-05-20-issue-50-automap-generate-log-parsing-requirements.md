---
date: 2026-05-20
topic: automap-generate-log-parsing
issue: 50
---

# AutoMap Wrapper — Parse `generate.log` for Warnings and Errors After Build

## Summary

Extend `plugins/webworks-claude-skills/skills/automap/scripts/automap-wrapper.sh` so that after a build returns exit code 0, the wrapper scans each target's `Logs/<TargetName>/generate.log` for `[WARN]` and `[ERROR]` lines and reports them. Today, AutoMap can exit successfully while the log records real problems (PDF generation failures, legacy-format warnings, unsupported methods), and the wrapper silently passes that through. The enhancement surfaces those signals at the end of the build so they are not missed.

---

## Problem Frame

`automap-wrapper.sh` treats AutoMap's exit code as the sole signal of build health: exit 0 prints `[SUCCESS] Build completed in Ns` and the wrapper exits 0. That is incomplete. AutoMap writes a structured log to `Logs/<TargetName>/generate.log` (relative to the project file's directory) for each target it builds, and that log can contain `[WARN]` and `[ERROR]` lines that the CLI does not promote to a non-zero exit. The Radware Case 00024362 build (referenced in the issue) is the recorded example: exit 0, but PDF output never created and warnings buried in the log.

This matters because:

1. **Silent partial failures.** A "successful" build can be missing outputs (PDFs not created, formats falling back to defaults). The user only finds out by manually opening the log file.
2. **Convention drift goes unflagged.** AutoMap warns when a project is pinned to a legacy format version (`'2024.1'`), when methods are unsupported, or when conversion falls back. These are the kinds of accumulating warnings a wrapper should surface.
3. **The information is already on disk.** No new instrumentation is needed — only reading what AutoMap already wrote.

The wrapper is the right home for this. It is the only layer that runs after every build, in both interactive and CI/CD modes, regardless of whether the user invoked AutoMap on a `.wep`, `.wrp`, `.waj`, or `.wxsp`. Adding the scan downstream of the wrapper would require every caller to remember to do it.

---

## Requirements

**Trigger and timing**

- R1. The log scan runs only when the AutoMap invocation returns exit code 0. Failed builds (exit ≠ 0) already surface diagnostics through the wrapper's existing `parse_automap_output`; the scan is for the "succeeded but issues" case described in the issue.
- R2. The scan runs after `[SUCCESS] Build completed in Ns` is emitted, before the wrapper itself exits 0. The summary line for warnings is part of the same end-of-build report.

**Log discovery**

- R3. The project directory is derived from the project file argument passed to the wrapper (the same path the wrapper already validates in `validate_project_file`). The log root is `<project_dir>/Logs/`.
- R4. The wrapper scans every subdirectory of `<project_dir>/Logs/` that contains a `generate.log`. Discovery is filesystem-driven, not derived from `-t`, `--target=`, `--all-targets`, or job-file `build="True"` attributes. This works for single-target, multi-target, and `.waj` builds without the wrapper having to enumerate targets a second time.
- R5. If `<project_dir>/Logs/` does not exist, or contains no `generate.log` files, the wrapper emits no summary line and exits 0. The absence of logs is not itself an error — older AutoMap versions and certain target types may not produce them.

**Line detection**

- R6. The scan extracts any line matching `[WARN]` or `[ERROR]` (literal substrings, case-sensitive — this matches AutoMap's own log format). Lines are extracted per-log; counts are tracked per-target and aggregated.
- R7. The scan handles multiple consecutive `[WARN]` lines correctly (the issue notes that PDF warnings sometimes have a blank line between them). Line-based extraction handles this natively.
- R8. The scan does not attempt to parse, categorize, deduplicate, or filter the warnings beyond extracting the lines. The user sees what AutoMap wrote.

**Reporting**

- R9. **Default (non-verbose) mode.** Emit one summary line per target that has at least one warning or error: `[WARN] <N> warning(s), <M> error(s) in Logs/<TargetName>/generate.log`. Targets with zero warnings and zero errors produce no line. If all scanned targets are clean, emit nothing (the existing `[SUCCESS]` line is sufficient).
- R10. **Verbose mode (`--verbose`).** In addition to the summary line(s) from R9, echo every extracted `[WARN]`/`[ERROR]` line to stdout, grouped by target, with the target name as a header. Use the existing `log_warning` / `log_error` helpers so coloring stays consistent.
- R11. The summary uses the existing `log_warning` and `log_error` helpers (not `log_info`) so that warnings appear in yellow and errors in red and route through the same output channel as other diagnostics.
- R12. The log path printed in the summary is relative to the project directory (e.g., `Logs/Reverb2/generate.log`), not absolute and not a converted Windows path. This keeps the message copy-pasteable for users browsing the project directory.

**Exit code behavior**

- R13. The wrapper's exit code is unchanged by the log scan. A build that AutoMap reports as exit 0 still exits 0, even if the log contains `[WARN]` or `[ERROR]` lines. The wrapper's job is to surface the signal, not to override AutoMap's verdict.

**Robustness**

- R14. The scan must not fail the wrapper. Any error while reading logs (permission denied, malformed path, log truncated, encoding issue) is swallowed; the build still exits 0 with whatever summary lines the scan was able to produce. The scan is observability, not a gate.
- R15. The wrapper handles target names containing spaces or non-ASCII characters in the path. Use proper quoting on file iteration; do not assume `find` / `for` works on the unquoted result.

---

## Acceptance Examples

- AE1. **Covers R1, R2, R5, R13.** Given a project where `Logs/` does not yet exist, when the wrapper runs a successful build that does not create `Logs/`, then the output ends with `[SUCCESS] Build completed in Ns`, no warning summary appears, and the exit code is 0.
- AE2. **Covers R3, R4, R6, R9, R11, R12.** Given a project file at `/path/to/proj.wep` that, on build, produces `/path/to/Logs/Reverb2/generate.log` containing three `[WARN]` lines and zero `[ERROR]` lines, when the wrapper finishes without `--verbose`, then a single yellow summary line appears: `[WARN] 3 warning(s), 0 error(s) in Logs/Reverb2/generate.log`.
- AE3. **Covers R4, R9.** Given a multi-target build that produces `Logs/Reverb2/generate.log` (2 warnings) and `Logs/PDF/generate.log` (0 warnings, 1 error), when the wrapper finishes without `--verbose`, then two summary lines appear — one yellow for Reverb2 ("2 warning(s), 0 error(s)") and one red for PDF ("0 warning(s), 1 error(s)") — and no summary line appears for any third target whose log is clean.
- AE4. **Covers R7, R10.** Given a `generate.log` containing three consecutive `[WARN]` lines (with a blank line between two of them, as in the issue's PDF example), when the wrapper runs with `--verbose`, then all three warning lines appear in the output, prefixed by a header indicating the target name.
- AE5. **Covers R13.** Given a build whose `generate.log` contains an `[ERROR]` line but AutoMap returned exit code 0, when the wrapper finishes, then the summary line indicates the error, the wrapper's exit code is 0 (matching AutoMap), and the CI script invoking the wrapper sees success.
- AE6. **Covers R14.** Given a `Logs/<Target>/generate.log` that cannot be read (permission denied, missing during the scan), when the wrapper runs, then the scan continues to the next log, no traceback or stack appears, and the wrapper still exits 0.

---

## Success Criteria

- A user running a build with warning-producing content (e.g., the Radware/Case 00024362 scenario) sees the warning count immediately in the terminal, without needing to open `generate.log` manually.
- CI/CD scripts that grep wrapper output for `[WARN]` or `[ERROR]` now see warnings even when AutoMap exited 0.
- The wrapper's exit-code contract is unchanged; existing automation continues to treat exit 0 as success.
- The scan adds negligible overhead (typical log files are tens of KB; even a multi-target Stationery build has fewer than a dozen logs).

---

## Scope Boundaries

- **Not changing exit codes based on warning content.** Treating warnings as failures is a policy decision callers should make themselves by inspecting wrapper output, not a default the wrapper imposes. A future opt-in flag (`--fail-on-warning`) could be considered separately.
- **Not filtering, deduplicating, or interpreting warnings.** The wrapper surfaces what AutoMap wrote, verbatim. Pattern recognition ("PDF not created" → suggest configuration X) belongs in skill troubleshooting docs, not in the wrapper.
- **Not parsing the log for timing.** The issue floats showing `Total time:` from the log alongside the wrapper's own timing. Deferred — the wrapper's timing already exists and the log-derived timing adds clutter without solving the headline problem.
- **Not parsing the log for failed builds.** When AutoMap returns non-zero, the wrapper's existing `parse_automap_output` already surfaces the error stream. Adding a second scan would duplicate signal. The new scan is gated on exit 0.
- **Not enumerating targets from the project / job file.** The wrapper already has target extraction logic for the interactive prompt, but the log scan deliberately uses filesystem discovery (Requirement R4) so it works for `.waj` builds, `--all-targets`, and partial-target invocations without coupling to that code path.
- **Not adding a Python helper.** The wrapper is bash and stays bash. The scan is grep-able line extraction; a separate `parse-log.py` would be over-engineered for the requirement.
- **Not modifying any other script** (`detect-installation.sh`, `parse-job.py`, etc.). The change is localized to `automap-wrapper.sh` and (if warranted) the skill's documentation files.
- **Not bumping the plugin version in the same change as this brainstorm artifact.** Version bump happens at PR time per the project's `CLAUDE.md`.

---

## Key Decisions

- **Filesystem-driven log discovery, not target-list-driven.** The wrapper already supports several ways to specify what to build (single `-t`, multi `--target=`, `--all-targets`, `.waj` `build="True"` attributes). Mirroring that complexity in the log scan is fragile and duplicative. Scanning `Logs/*/generate.log` after the build asks the filesystem "what got built?" — which is what we actually want to know.
- **Exit code unchanged.** The wrapper is a thin pass-through over AutoMap's verdict. Promoting warnings to failures would change the contract that callers rely on and would surprise CI scripts that already exit 0 on exit 0. Surfacing is the goal; gating is a separate (future, opt-in) decision.
- **Bash, not Python.** The wrapper is bash; the scan is line extraction and counting. Reaching for `lib/` Python here would add a process boundary, an import, and version coupling for what is essentially `grep -c '\[WARN\]'`.
- **Default mode emits one summary line per target with non-zero counts.** Quieter than echoing every warning line by default, but louder than emitting nothing — the user always knows there is something to look at and where the file is.
- **Verbose mode echoes the lines.** Users who pass `--verbose` already opted in to noisy output; showing the actual warning text is consistent with that intent.
- **Log path is relative to the project directory.** Absolute paths and Windows-converted paths are harder to read at a glance and longer than necessary. Relative paths match how the issue itself describes the location (`Logs/Reverb2/generate.log`).
- **Skip the optional `Total time:` extraction.** The wrapper already times the build (`Build completed in Ns`). The issue describes the log's own timing as a "could optionally" — keeping the change focused on the headline problem (unreported warnings) avoids feature creep.

---

## Dependencies / Assumptions

- The `blocked-by: #54` directive in the issue refers to PR #54 (Reverb landmark resolver). Verified merged on 2026-05-20 (commit `fbe86f6`, "Merge pull request #75 from quadralay/claude/issue-54"). No work in this brainstorm depends on landmark-resolver code, so the blocker was procedural sequencing rather than a code dependency.
- AutoMap writes logs to `<project_dir>/Logs/<TargetName>/generate.log` for the supported versions (2024.1+ per the skill's `SKILL.md` Requirements section). Older versions may use different paths or omit logs; the scan-and-skip-if-absent behavior in R5 covers that case.
- AutoMap uses literal `[WARN]` and `[ERROR]` markers (uppercase, in square brackets, no severity sub-levels). This matches the sample log in the issue body. If a future AutoMap version changes the markers, the scan returns zero matches rather than crashing.
- `generate.log` is plain text in the system's default encoding (UTF-8 on modern Windows installs, possibly UTF-16 on older ones). The scan reads via standard bash tooling; encoding edge cases fall under R14 (swallow and continue).
- The wrapper script's working directory at the time it runs is unspecified — callers may invoke it from anywhere. The scan derives the log root from the project file path, not from `$PWD`.
- Target names in `Logs/` subdirectories may contain spaces. The bash quoting must handle that; tests should include at least one space-bearing target to verify.

---

## Outstanding Questions

### Resolvable at planning time

- [Affects R6, R10] [Technical] Decide whether the scan uses `grep -E '\[WARN\]|\[ERROR\]'` once per log, or two passes (`grep -c '\[WARN\]'` then `grep -c '\[ERROR\]'`). Either works; planning picks the simpler implementation and notes whether the per-line output in verbose mode preserves original order.
- [Affects R10] [Editorial] Decide the exact format of the verbose-mode per-target header. Options: `[WARN] Warnings/errors in Logs/<Target>/generate.log:` (yellow), or a neutral header followed by individually-colored lines. Planning picks based on how the existing `parse_automap_output` styles multi-line groupings.
- [Affects R3] [Verification] Confirm by reading the wrapper's `validate_project_file` and the path-handling around `cygpath` that the derived `<project_dir>` is suitable for filesystem iteration on Git Bash. The `dirname` of the (possibly cygpath-converted) project file is the candidate; planning verifies.
- [Affects R15] [Verification] Confirm by adding a test fixture (or extending `tests/sample.waj`) that target names with spaces produce correctly-quoted log paths. The current `tests/` directory has `sample.waj` and `sample.wxsp` — planning decides whether to add a fixture with a space-bearing target or to rely on quoting review alone.

### Genuinely uncertain — record as assumption

- [Affects R5, R14] [Open] Whether any current AutoMap version emits warnings to a path other than `Logs/<TargetName>/generate.log` (e.g., `Output/<TargetName>/Logs/`, or a top-level `automap.log`). The issue body and `tests/` fixtures suggest the documented path is canonical, but the skill's references do not list every variant. Planning treats `Logs/<TargetName>/generate.log` as the only path; if a later report surfaces another location, the scan extends to cover both.
- [Affects R14] [Open] Whether `generate.log` is ever written with a different encoding (UTF-16LE with BOM, for example) on older Windows installs. The scan assumes plain text; if encoding turns out to be an issue, R14's "swallow and continue" keeps the wrapper working while we add an explicit handler.
