#!/bin/bash
################################################################################
# setup-dependencies.sh
#
# Installs Node.js dependencies for the Reverb analyzer skill.
# Verifies Node.js is installed and runs npm install.
#
# Usage:
#   ./setup-dependencies.sh
#
# Exit Codes:
#   0 - Dependencies installed successfully
#   1 - Node.js not found or npm install failed
#
################################################################################

set -euo pipefail

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SKILL_DIR="$(dirname "$SCRIPT_DIR")"

info_log() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

success_log() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

error_log() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

################################################################################
# Dependency Checks
################################################################################

check_node() {
    info_log "Checking for Node.js..."

    if ! command -v node &> /dev/null; then
        error_log "Node.js not found!"
        error_log ""
        error_log "Please install Node.js 18+ from:"
        error_log "  https://nodejs.org/"
        error_log ""
        return 1
    fi

    local node_version
    node_version=$(node --version)
    success_log "Found Node.js: $node_version"

    # Check minimum version (18.0.0) - matches package.json requirement
    local major_version
    major_version=$(echo "$node_version" | sed 's/v//' | cut -d. -f1)

    if [[ "$major_version" -lt 18 ]]; then
        error_log "Node.js version 18+ required, found: $node_version"
        error_log "See package.json engines requirement"
        return 1
    fi

    return 0
}

check_npm() {
    info_log "Checking for npm..."

    if ! command -v npm &> /dev/null; then
        error_log "npm not found (should be installed with Node.js)"
        return 1
    fi

    local npm_version
    npm_version=$(npm --version)
    success_log "Found npm: $npm_version"

    return 0
}

################################################################################
# Installation
################################################################################

install_dependencies() {
    info_log "Installing Node.js dependencies..."

    cd "$SKILL_DIR" || {
        error_log "Failed to change to skill directory: $SKILL_DIR"
        return 1
    }

    # Check if package.json exists
    if [[ ! -f "package.json" ]]; then
        error_log "package.json not found in: $SKILL_DIR"
        return 1
    fi

    # Check if node_modules already exists
    if [[ -d "node_modules" ]]; then
        info_log "node_modules directory already exists"
        info_log "Run 'npm install' manually if you need to update dependencies"
        return 0
    fi

    # Run npm install
    if npm install --loglevel=error; then
        success_log "Dependencies installed successfully"
        return 0
    else
        error_log "npm install failed"
        return 1
    fi
}

################################################################################
# Main Logic
################################################################################

main() {
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Reverb Analyzer Skill - Dependency Setup"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # Check prerequisites
    if ! check_node; then
        exit 1
    fi

    if ! check_npm; then
        exit 1
    fi

    # Install dependencies
    if ! install_dependencies; then
        exit 1
    fi

    echo ""
    success_log "Setup complete!"
    echo ""
}

main "$@"
