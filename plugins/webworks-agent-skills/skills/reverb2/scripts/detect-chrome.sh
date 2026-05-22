#!/bin/bash
################################################################################
# detect-chrome.sh
#
# Detects Chrome/Chromium installation on Windows for use with Puppeteer.
# Searches common installation paths and respects environment variable overrides.
#
# Usage:
#   ./detect-chrome.sh
#
# Output:
#   Prints Chrome executable path to stdout
#   Returns exit code 0 on success, 1 on failure
#
# Environment Variables:
#   CHROME_PATH - Manual override for Chrome executable path
#
################################################################################

set -euo pipefail

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m' # No Color

# Enable verbose output if DEBUG is set
DEBUG="${DEBUG:-0}"
debug_log() {
    if [[ "$DEBUG" == "1" ]]; then
        echo -e "${YELLOW}[DEBUG]${NC} $*" >&2
    fi
}

error_log() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

success_log() {
    echo -e "${GREEN}[SUCCESS]${NC} $*" >&2
}

################################################################################
# Main Chrome Detection Logic
################################################################################

detect_chrome() {
    debug_log "Starting Chrome detection..."

    # Check for manual override first
    if [[ -n "${CHROME_PATH:-}" ]]; then
        debug_log "Found CHROME_PATH environment variable: $CHROME_PATH"
        if [[ -f "$CHROME_PATH" ]]; then
            success_log "Using Chrome from CHROME_PATH: $CHROME_PATH"
            echo "$CHROME_PATH"
            return 0
        else
            error_log "CHROME_PATH is set but file does not exist: $CHROME_PATH"
            return 1
        fi
    fi

    # Common Windows Chrome installation paths
    local chrome_paths=(
        "/c/Program Files/Google/Chrome/Application/chrome.exe"
        "/c/Program Files (x86)/Google/Chrome/Application/chrome.exe"
        "$LOCALAPPDATA/Google/Chrome/Application/chrome.exe"
        "$PROGRAMFILES/Google/Chrome/Application/chrome.exe"
        # Edge Chromium (fallback)
        "/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
        "/c/Program Files/Microsoft/Edge/Application/msedge.exe"
        "$PROGRAMFILES/Microsoft/Edge/Application/msedge.exe"
    )

    # Search for Chrome in standard locations
    for path in "${chrome_paths[@]}"; do
        debug_log "Checking path: $path"
        if [[ -f "$path" ]]; then
            success_log "Found Chrome at: $path"
            echo "$path"
            return 0
        fi
    done

    # Chrome not found
    error_log "Chrome/Edge not found in any standard location"
    error_log ""
    error_log "Please install Chrome or set CHROME_PATH environment variable:"
    error_log "  export CHROME_PATH=\"/c/path/to/chrome.exe\""
    error_log ""
    error_log "Download Chrome from: https://www.google.com/chrome/"

    return 1
}

################################################################################
# Entry Point
################################################################################

main() {
    detect_chrome
}

main "$@"
