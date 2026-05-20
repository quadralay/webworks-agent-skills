#!/bin/bash
#
# test-generate-log-scan.sh
# Test driver for scan_generate_logs in automap-wrapper.sh.
#
# Sources the wrapper (its main-flow guard prevents arg parsing from running),
# invokes scan_generate_logs against each fixture with VERBOSE=false and
# VERBOSE=true, captures combined stdout+stderr, strips ANSI color codes, and
# diffs against per-fixture .expected reference files.
#
# Usage: bash test-generate-log-scan.sh
# Exit code: 0 if all assertions pass, 1 otherwise.
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WRAPPER="$SCRIPT_DIR/../scripts/automap-wrapper.sh"
FIXTURES="$SCRIPT_DIR/fixtures"

# Source the wrapper to import scan_generate_logs and its helpers.
# shellcheck source=../scripts/automap-wrapper.sh
source "$WRAPPER"

# Loosen strict mode the wrapper enabled so an individual assertion failure
# does not abort the entire driver.
set +e

PASS=0
FAIL=0

strip_ansi() {
    # Strip ANSI CSI sequences so .expected files stay readable plain text.
    sed -E $'s/\x1B\\[[0-9;]*[a-zA-Z]//g'
}

run_scan() {
    local fixture="$1"
    local verbose="$2"
    VERBOSE="$verbose"
    scan_generate_logs "$fixture" 2>&1 | strip_ansi
}

assert_equal() {
    local name="$1"
    local expected="$2"
    local actual="$3"

    if [[ "$expected" == "$actual" ]]; then
        PASS=$((PASS + 1))
        echo "PASS: $name"
    else
        FAIL=$((FAIL + 1))
        echo "FAIL: $name"
        echo "--- expected ---"
        printf '%s\n' "$expected"
        echo "--- actual ---"
        printf '%s\n' "$actual"
        echo "----------------"
    fi
}

run_case() {
    local name="$1"
    local fixture_dir="$2"
    local verbose="$3"
    local expected_file="$4"

    local expected actual
    expected=$(cat "$expected_file" 2>/dev/null)
    actual=$(run_scan "$fixture_dir" "$verbose")
    assert_equal "$name" "$expected" "$actual"
}

# --- Tests ---

# Single-target, warnings only: summary format.
run_case "single-warning-target (default)" \
    "$FIXTURES/single-warning-target" \
    false \
    "$FIXTURES/single-warning-target/expected-default.txt"

# Verbose mode: per-target header, original line spacing preserved.
run_case "single-warning-target (verbose)" \
    "$FIXTURES/single-warning-target" \
    true \
    "$FIXTURES/single-warning-target/expected-verbose.txt"

# Multi-target aggregation: error-only target routes red, clean target emits nothing.
run_case "multi-target (default)" \
    "$FIXTURES/multi-target" \
    false \
    "$FIXTURES/multi-target/expected-default.txt"

# Verbose mode: per-target grouping across multiple targets.
run_case "multi-target (verbose)" \
    "$FIXTURES/multi-target" \
    true \
    "$FIXTURES/multi-target/expected-verbose.txt"

# Target directory name with embedded space round-trips through quoting.
run_case "space-target (default)" \
    "$FIXTURES/space-target" \
    false \
    "$FIXTURES/space-target/expected-default.txt"

run_case "space-target (verbose)" \
    "$FIXTURES/space-target" \
    true \
    "$FIXTURES/space-target/expected-verbose.txt"

# Single target with both [WARN] and [ERROR] in one log: summary routes red,
# verbose lines route per-line based on which marker is present.
run_case "mixed-target (default)" \
    "$FIXTURES/mixed-target" \
    false \
    "$FIXTURES/mixed-target/expected-default.txt"

run_case "mixed-target (verbose)" \
    "$FIXTURES/mixed-target" \
    true \
    "$FIXTURES/mixed-target/expected-verbose.txt"

# Missing Logs/ directory emits nothing.
run_case "no-logs-dir (default)" \
    "$FIXTURES/no-logs-dir" \
    false \
    "$FIXTURES/no-logs-dir/expected-default.txt"

run_case "no-logs-dir (verbose)" \
    "$FIXTURES/no-logs-dir" \
    true \
    "$FIXTURES/no-logs-dir/expected-verbose.txt"

# Logs/ directory exists but contains no generate.log file: emits nothing.
# Exercises the literal-pattern-iterated-once branch of the glob expansion.
run_case "empty-logs-dir (default)" \
    "$FIXTURES/empty-logs-dir" \
    false \
    "$FIXTURES/empty-logs-dir/expected-default.txt"

run_case "empty-logs-dir (verbose)" \
    "$FIXTURES/empty-logs-dir" \
    true \
    "$FIXTURES/empty-logs-dir/expected-verbose.txt"

echo ""
echo "Results: $PASS passed, $FAIL failed"

if [[ $FAIL -eq 0 ]]; then
    exit 0
else
    exit 1
fi
