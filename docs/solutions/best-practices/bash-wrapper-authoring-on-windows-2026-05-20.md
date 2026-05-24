---
title: Bash wrapper authoring and testing on Windows Git Bash
date: 2026-05-20
category: best-practices
module: automap-plugin/bash-wrappers
problem_type: best_practice
component: tooling
severity: medium
related_components:
  - development_workflow
  - testing_framework
applies_when:
  - "Authoring or modifying bash wrapper scripts in plugins/webworks-agent-skills/skills/automap/scripts/"
  - "Adding fixture-based CLI tests for bash helpers that diff against committed .expected files"
  - "Wrapper scripts run under set -euo pipefail and shell out to grep, wc, or other tools that exit non-zero on legitimate empty results"
  - "Log or pass-through content may contain Windows paths or other backslash sequences"
  - "Adding test fixtures whose paths would otherwise be swept up by broad .gitignore patterns or rewritten by core.autocrlf on Windows"
symptoms:
  - "Wrapper aborts silently with exit 1 when grep -c finds zero matches under set -euo pipefail"
  - "Windows paths printed via log_warning or log_error lose backslashes or gain spurious tabs and newlines from echo -e"
  - "Bash test driver cannot import wrapper helper functions without triggering the script's main flow"
  - "Test fixture .log files vanish from git status because a top-level *.log ignore pattern hides them"
  - "Test assertions that diff against expected-*.txt fixtures fail on Windows because core.autocrlf=true rewrites line endings"
tags:
  - bash
  - shell-scripting
  - set-euo-pipefail
  - printf-vs-echo
  - sourceable-scripts
  - gitignore
  - gitattributes
  - line-endings
---

# Bash wrapper authoring and testing on Windows Git Bash

## Context

Implementing AutoMap generate.log post-build scanning (issue #50) required a bash helper that runs after every successful AutoMap build, tallies `[WARN]`/`[ERROR]` lines per target, and reports them without altering exit codes. The wrapper already runs under `set -euo pipefail` on Windows Git Bash, and the test fixtures had to round-trip through git. The implementation itself was small; the lessons were in the half-dozen ways the surrounding environment fought the change.

## Guidance

### 1. `set -euo pipefail` turns `grep -c` zero-match into a fatal abort

`grep -c PATTERN file` exits 1 when there are zero matches. Under `set -e`, that one-line count expression aborts the entire wrapper before the result is even consumed — and the most common case for a clean build log is *zero* `[ERROR]` matches. `|| true` on each `grep -c` is necessary but not sufficient: a downstream `grep | while` pipeline can still trip `pipefail` on SIGPIPE. The robust pattern is to demote strict mode inside a subshell around the entire scan block and additionally `|| true`-guard each individual `grep -c`, then default the captured count with `${var:-0}`.

```bash
scan_target_log() {
  local log_file="$1"
  (
    set +e
    set +u
    set +o pipefail

    local warn_count error_count
    warn_count=$(grep -c '\[WARN\]'  "$log_file" 2>/dev/null || true)
    error_count=$(grep -c '\[ERROR\]' "$log_file" 2>/dev/null || true)
    warn_count=${warn_count:-0}
    error_count=${error_count:-0}

    printf '%s %s\n' "$warn_count" "$error_count"
  )
}
```

### 2. `echo -e` mangles backslash sequences in pass-through content

The existing `log_warning` / `log_error` helpers use `echo -e` so they can embed ANSI color escapes. That works fine for caller-controlled strings, but routing an external log line through `echo -e "${RED}[ERROR]${NC} $line"` interprets `\t`, `\n`, `\r` etc. inside `$line` — and a Windows path like `C:\path\to\output.pdf` becomes `C:\path<TAB>o\output.pdf` in the rendered output. The fix is a dedicated router that uses `printf` with separated `%b` (escapes interpreted) and `%s` (verbatim) conversions. Leave the existing helpers alone for caller-controlled strings; do not retrofit them.

```bash
# Before (corrupts backslashes inside $line)
echo -e "${RED}[ERROR]${NC} $line" >&2

# After (color expanded, line preserved byte-for-byte)
route_log_line() {
  local line="$1"
  if [[ "$line" == *"[ERROR]"* ]]; then
    printf '%b[ERROR]%b %s\n' "$RED"    "$NC" "$line" >&2
  else
    printf '%b[WARNING]%b %s\n' "$YELLOW" "$NC" "$line"
  fi
}
```

### 3. Guard the main flow so the wrapper is sourceable

A bash script that parses arguments and runs the main flow at the top level cannot be sourced by a test driver — sourcing executes the script, which blows up on the missing positional args. Wrap everything from argument parsing through the final exit in a `BASH_SOURCE`-vs-`$0` guard. When the file is executed directly the two are equal and the block runs; when a test driver sources it the block is skipped, but every helper defined above it is now available for direct invocation in isolation.

```bash
# ... helper functions defined above ...

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  # Argument parsing, main flow, exit logic.
  parse_args "$@"
  main
  exit $?
fi
```

### 4. Characterization-first bash tests with `.expected` files and `diff`

A real test framework is overkill for one wrapper, but bash CLI output is fiddly enough (ANSI codes, line ordering, header wording, stdout-vs-stderr) that ad-hoc assertions drift. The working pattern is one fixture tree per scenario plus a committed `.expected` text capture of the exact output. The driver sources the script, invokes a helper against the fixture, captures stdout and stderr together, and `diff`s against `.expected`. Write the `.expected` file *before* implementing the helper — it is the contract, not a snapshot of what the code happened to produce.

```bash
# tests/test-generate-log-scan.sh
source "$(dirname "$0")/../scripts/automap-wrapper.sh"

run_case() {
  local name="$1" fixture="$2" expected="$3"
  local actual
  actual=$(scan_generate_logs "$fixture" 2>&1)
  if ! diff -u "$expected" <(printf '%s\n' "$actual"); then
    echo "FAIL: $name" >&2
    return 1
  fi
}

run_case "single warning target" \
  tests/fixtures/single-warning-target \
  tests/fixtures/single-warning-target/expected-default.txt
```

### 5. Top-level `.gitignore` patterns silently drop test fixture log files

This repo's top-level `.gitignore` includes `*.log` and `logs/`. Fixtures like `tests/fixtures/single-warning-target/Logs/Reverb2/generate.log` match both patterns, so `git add` silently skips them — locally everything looks fine, CI sees an empty fixture tree, and the test passes vacuously or fails inscrutably. The fix is a scoped negation pattern placed *below* the broad block. Negation order matters: a later `!` overrides an earlier match. Verify with `git check-ignore -v <path>` — exit code 1 means the path is no longer ignored.

```text
# .gitignore
*.log
logs/

# Don't ignore intentional test fixtures
!plugins/webworks-agent-skills/skills/automap/tests/fixtures/**
```

```bash
git check-ignore -v plugins/webworks-agent-skills/skills/automap/tests/fixtures/single-warning-target/Logs/Reverb2/generate.log
# exit 1 = not ignored (good); exit 0 = still ignored (still broken)
```

### 6. `core.autocrlf=true` breaks byte-identical test assertions

Windows developers commonly have `core.autocrlf=true` set globally, which inserts CRLF on checkout for text files. That breaks two things at once: bash scripts checked out with `\r` line endings fail to execute on some shells, and `.expected` text files come back with CRLF endings while the wrapper at runtime emits LF — `diff` against the captured output then fails on every line. A repo-local `.gitattributes` pins `eol=lf` for the affected paths so checkout normalization is correct regardless of the contributor's global git config.

```text
# .gitattributes
*.sh                                                            eol=lf
plugins/webworks-agent-skills/skills/automap/tests/fixtures/** eol=lf
```

## Why This Matters

Bash wrappers are a recurring shape in this plugin — `automap-wrapper.sh`, `detect-installation.sh`, and future scripts that shell out to Windows tooling — and each of these six hazards will recur whenever a contributor adds a new wrapper, a new test, or a new fixture. The strict-mode and `echo -e` traps are silent: the script keeps running (or appears to), but with wrong output or an early abort. The git-side traps (`.gitignore`, CRLF) are worse because they only manifest off the author's machine. Cataloging the fix patterns here means the next wrapper starts with the sourceable main-flow guard, the `printf` router for external content, the `.expected`/`diff` test harness, and the `.gitattributes` + scoped `!`-negation already in place — rather than rediscovering each one under deadline. This is especially load-bearing for issue #73 (the PowerShell port), where the bash hazards either translate directly or have direct PowerShell equivalents (`$ErrorActionPreference`, `Write-Output` vs `Write-Host`, dot-sourcing semantics).

## When to Apply

- Writing or modifying any bash script that runs under `set -euo pipefail` and shells out to `grep`, `wc`, or other tools that exit non-zero on legitimate empty-result cases.
- Emitting log lines, command output, or file contents through a colorized print helper — switch from `echo -e` to separated-conversion `printf` whenever any segment is external content.
- Building a new CLI-style wrapper that needs unit tests — add the `BASH_SOURCE`/`$0` guard from day one so helpers can be sourced and exercised in isolation.
- Adding fixture trees that contain files matching repo-wide ignore patterns (`*.log`, `*.tmp`, `build/`, `logs/`) — pair the new fixture with a scoped `!` negation and verify with `git check-ignore`.
- Committing any text file whose contents are compared byte-for-byte at test time (`.expected` captures, golden outputs) — pin `eol=lf` for that path in `.gitattributes`.
- Onboarding a new contributor on Windows — confirm their `core.autocrlf` setting will not corrupt checked-out shell scripts or fixtures before they run the test suite.

## Examples

- Canonical scan helper with subshell strict-mode demotion and `printf`-based line router: `plugins/webworks-agent-skills/skills/automap/scripts/automap-wrapper.sh` lines 454-520.
- `BASH_SOURCE`-vs-`$0` main-flow guard that keeps the wrapper sourceable from tests: `plugins/webworks-agent-skills/skills/automap/scripts/automap-wrapper.sh` lines 559-707.
- Characterization test driver using committed `.expected` files and `diff`: `plugins/webworks-agent-skills/skills/automap/tests/test-generate-log-scan.sh`.
- Scoped `.gitignore` unignore patterns for the fixtures path: top-level `.gitignore`.
- `.gitattributes` `eol=lf` pins for `*.sh` and the fixtures path: top-level `.gitattributes`.

## Related

- GitHub issue #50 — automap: Parse generate.log for warnings and errors after build (origin of these learnings)
- GitHub issue #73 — refactor(automap): port automap-wrapper.sh and detect-installation.sh to PowerShell (consumer of these learnings on the PowerShell side)
- See also: `docs/solutions/bash-syntax-errors-in-skill-tables.md` — a separate bash-hazard family (markdown-table parsing during skill loading), unrelated root cause but same neighborhood.
- See also: `docs/solutions/best-practices/epublisher-diffable-html-output-config-2026-05-19.md` — diff-based testing rationale that motivates the `.expected` characterization-test pattern here.
