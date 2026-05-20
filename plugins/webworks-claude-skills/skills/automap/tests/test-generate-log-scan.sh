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
set +u

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

# AE2 + R6, R9, R12: single-target, warnings only, summary format.
run_case "single-warning-target (default)" \
    "$FIXTURES/single-warning-target" \
    false \
    "$FIXTURES/single-warning-target/expected-default.txt"

# AE4 + R7, R10: verbose mode, header, blank-line-between [WARN]s preserved.
run_case "single-warning-target (verbose)" \
    "$FIXTURES/single-warning-target" \
    true \
    "$FIXTURES/single-warning-target/expected-verbose.txt"

# AE3 + R9, R11: multi-target aggregation, error-only target routes red.
run_case "multi-target (default)" \
    "$FIXTURES/multi-target" \
    false \
    "$FIXTURES/multi-target/expected-default.txt"

# R10 + cross-target verbose grouping.
run_case "multi-target (verbose)" \
    "$FIXTURES/multi-target" \
    true \
    "$FIXTURES/multi-target/expected-verbose.txt"

# R15: target directory name with embedded space round-trips through quoting.
run_case "space-target (default)" \
    "$FIXTURES/space-target" \
    false \
    "$FIXTURES/space-target/expected-default.txt"

run_case "space-target (verbose)" \
    "$FIXTURES/space-target" \
    true \
    "$FIXTURES/space-target/expected-verbose.txt"

# AE1 + R5: missing Logs/ directory emits nothing.
run_case "no-logs-dir (default)" \
    "$FIXTURES/no-logs-dir" \
    false \
    "$FIXTURES/no-logs-dir/expected-default.txt"

run_case "no-logs-dir (verbose)" \
    "$FIXTURES/no-logs-dir" \
    true \
    "$FIXTURES/no-logs-dir/expected-verbose.txt"

echo ""
echo "Results: $PASS passed, $FAIL failed"

if [[ $FAIL -eq 0 ]]; then
    exit 0
else
    exit 1
fi
