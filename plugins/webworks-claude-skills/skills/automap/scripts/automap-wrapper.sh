#!/bin/bash
#
# automap-wrapper.sh
# Wrapper script for WebWorks ePublisher AutoMap CLI
#
# This wrapper automatically detects the AutoMap CLI installation and executes
# builds with proper argument handling, output parsing, and error detection.
#
# Note: The detection script finds the AutoMap Administrator executable via
# registry or filesystem, then normalizes to the CLI executable for headless
# automation.
#
# Usage:
#   ./automap-wrapper.sh [OPTIONS] <project-file>
#
# Features:
#   - Automatic AutoMap CLI detection (via registry or filesystem)
#   - Proper argument handling and quoting
#   - Output parsing and error detection
#   - Exit code reporting
#   - Progress monitoring
#
# Exit Codes:
#   0   - Build succeeded
#   1   - Build failed
#   2   - Invalid arguments
#   3   - AutoMap not found
#   4   - Project file not found
#

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_NAME="$(basename "$0")"
DETECT_SCRIPT="$SCRIPT_DIR/detect-installation.sh"

# Default options (safe defaults: clean, no-deploy, skip-reports enabled)
CLEAN_BUILD=true
CLEAN_DEPLOY=false
NO_DEPLOY=true
SKIP_REPORTS=true
TARGET=""
TARGET_MULTI=""
ALL_TARGETS=false
DEPLOY_FOLDER=""
VERBOSE=false

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

#
# Helper Functions
#

log_info() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}[INFO]${NC} $*"
    fi
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

log_verbose() {
    if [ "$VERBOSE" = true ]; then
        echo "[VERBOSE] $*" >&2
    fi
}

#
# Target Selection Functions
#

extract_targets() {
    local project_file="$1"

    # Convert to Unix path for reading
    local unix_path
    unix_path=$(cygpath "$project_file" 2>/dev/null || echo "$project_file")

    # Determine file type and extract targets
    case "$project_file" in
        *.waj)
            # Job files: <Target name="...">
            grep -oP '<Target[^>]*\sname="[^"]*"' "$unix_path" 2>/dev/null | \
                grep -oP 'name="[^"]*"' | sed 's/name="//;s/"$//'
            ;;
        *.wep|*.wrp|*.wxsp)
            # Project files: <Format TargetName="...">
            grep -oP 'TargetName="[^"]*"' "$unix_path" 2>/dev/null | \
                sed 's/TargetName="//;s/"$//'
            ;;
    esac
}

parse_selection() {
    local input="$1"
    local max="$2"

    # Handle 'a' or 'all' for all targets
    if [[ "$input" =~ ^[aA](ll)?$ ]]; then
        seq 1 "$max"
        return 0
    fi

    # Split by comma and process each part
    IFS=',' read -ra parts <<< "$input"
    for part in "${parts[@]}"; do
        part=$(echo "$part" | tr -d ' ')  # Remove spaces

        if [[ "$part" =~ ^([0-9]+)-([0-9]+)$ ]]; then
            # Range: 1-3
            local start="${BASH_REMATCH[1]}"
            local end="${BASH_REMATCH[2]}"
            if [[ $start -ge 1 && $end -le $max && $start -le $end ]]; then
                seq "$start" "$end"
            else
                return 1  # Invalid range
            fi
        elif [[ "$part" =~ ^[0-9]+$ ]]; then
            # Single number
            if [[ $part -ge 1 && $part -le $max ]]; then
                echo "$part"
            else
                return 1  # Out of range
            fi
        else
            return 1  # Invalid format
        fi
    done | sort -nu  # Sort and deduplicate

    return 0
}

select_targets() {
    local project_file="$1"
    local -a targets
    local attempts=0
    local max_attempts=3

    # Extract available targets
    mapfile -t targets < <(extract_targets "$project_file")

    if [[ ${#targets[@]} -eq 0 ]]; then
        log_error "No targets found in project file"
        return 1
    fi

    # Single target optimization: auto-select without prompting (works in both modes)
    if [[ ${#targets[@]} -eq 1 ]]; then
        TARGET="${targets[0]}"
        log_info "Single target found, auto-selecting: $TARGET"
        return 0
    fi

    # Multi-target + Non-interactive mode: require explicit --all-targets
    if [[ ! -t 0 ]]; then
        log_error "No target specified in non-interactive mode."
        log_error "Use -t TARGET, --target=TARGETS, or --all-targets"
        log_error ""
        log_error "Available targets:"
        for i in "${!targets[@]}"; do
            log_error "  - ${targets[$i]}"
        done
        return 1
    fi

    log_warning "No target specified. Available targets:"
    echo ""
    for i in "${!targets[@]}"; do
        printf "  %d) %s\n" "$((i + 1))" "${targets[$i]}"
    done
    printf "  a) All targets\n"
    echo ""

    while [[ $attempts -lt $max_attempts ]]; do
        read -r -p "Select target(s) [1-${#targets[@]}, comma-separated, ranges like 1-3, or 'a' for all]: " selection

        # Empty input = cancel
        if [[ -z "$selection" ]]; then
            log_info "Build cancelled."
            return 1
        fi

        # Parse selection
        local -a selected_indices
        if mapfile -t selected_indices < <(parse_selection "$selection" "${#targets[@]}"); then
            if [[ ${#selected_indices[@]} -gt 0 ]]; then
                # Build the target list
                local -a selected_targets=()
                for idx in "${selected_indices[@]}"; do
                    selected_targets+=("${targets[$((idx - 1))]}")
                done

                # Set TARGET_MULTI for multiple targets, TARGET for single
                if [[ ${#selected_targets[@]} -eq 1 ]]; then
                    TARGET="${selected_targets[0]}"
                elif [[ ${#selected_targets[@]} -eq ${#targets[@]} ]]; then
                    ALL_TARGETS=true
                else
                    # Join with comma for --target= syntax
                    TARGET_MULTI=$(IFS=','; echo "${selected_targets[*]}")
                fi

                log_info "Selected: ${selected_targets[*]}"
                return 0
            fi
        fi

        ((attempts++))
        if [[ $attempts -lt $max_attempts ]]; then
            log_warning "Invalid selection. Please try again. ($((max_attempts - attempts)) attempts remaining)"
        fi
    done

    log_error "Too many invalid attempts. Build cancelled."
    return 1
}

usage() {
    cat <<EOF
Usage: $SCRIPT_NAME [OPTIONS] <project-file>

Wrapper script for WebWorks ePublisher AutoMap CLI with automatic detection
and safe defaults for development workflows.

REQUIRED:
    <project-file>          Path to .wep, .wrp, .waj, or .wxsp project/job file

TARGET SELECTION:
    -t TARGET              Build single target only
    --target=T1,T2,...     Build multiple specific targets
    --all-targets          Build all targets (bypasses interactive selection)

    If no target is specified:
    - Single-target projects: auto-selects the only target
    - Multi-target projects: prompts for selection (interactive mode)
    - Non-interactive mode: requires -t, --target=, or --all-targets

BUILD OPTIONS (safe defaults - opt out as needed):
    -c, --clean            Clean build [DEFAULT: enabled]
    --no-clean             Disable clean build (incremental)
    -n, --nodeploy         Do not deploy output [DEFAULT: enabled]
    --deploy               Enable deployment to output location
    --skip-reports         Skip report pipelines [DEFAULT: enabled, 2025.1+]
    --with-reports         Generate reports
    -l, --cleandeploy      Clean deployment location before copying

OTHER OPTIONS:
    -d, --deployfolder=PATH  Override deployment destination (implies --deploy)
    --verbose                Show all build output (default: minimal)
    --help                   Show this help message

ENVIRONMENT:
    AUTOMAP_EXE_PATH       Path to AutoMap executable (bypasses auto-detection)
                           Use for dev builds: export AUTOMAP_EXE_PATH="/path/to/debug/WebWorks.Automap.exe"
                           Or cache detected path: export AUTOMAP_EXE_PATH=\$(./scripts/detect-installation.sh)

EXIT CODES:
    0    Build succeeded
    1    Build failed
    2    Invalid arguments / user cancelled
    3    AutoMap not found
    4    Project file not found

EXAMPLES:
    # Build single target (safe defaults applied: clean, no-deploy, skip-reports)
    $SCRIPT_NAME -t "WebWorks Reverb 2.0" project.wep

    # Build multiple targets
    $SCRIPT_NAME --target="WebWorks Reverb 2.0","PDF - XSL-FO" project.wep

    # CI/CD: Build all targets explicitly
    $SCRIPT_NAME --all-targets project.wep

    # Production release: deploy with reports
    $SCRIPT_NAME --deploy --with-reports -t "WebWorks Reverb 2.0" project.wep

    # Incremental build during development
    $SCRIPT_NAME --no-clean -t "WebWorks Reverb 2.0" project.wep

    # Interactive mode: no target specified, prompts for selection
    $SCRIPT_NAME project.wep
EOF
}

validate_project_file() {
    local project_file="$1"

    # Convert to Unix path for test
    local unix_path
    unix_path=$(cygpath "$project_file" 2>/dev/null || echo "$project_file")

    if [ ! -f "$unix_path" ]; then
        log_error "Project file not found: $project_file"
        return 1
    fi

    # Check file extension
    if [[ ! "$project_file" =~ \.(wep|wrp|waj|wxsp)$ ]]; then
        log_warning "Project file has unexpected extension: $project_file"
        log_warning "Expected: .wep, .wrp, .waj, or .wxsp"
    fi

    return 0
}

detect_automap_executable() {
    log_verbose "Detecting AutoMap installation..."

    # Check for executable path override (supports both dev builds and caching)
    if [[ -n "${AUTOMAP_EXE_PATH:-}" ]]; then
        log_verbose "Found AUTOMAP_EXE_PATH environment variable: $AUTOMAP_EXE_PATH"
        local unix_path
        unix_path=$(cygpath "$AUTOMAP_EXE_PATH" 2>/dev/null || echo "$AUTOMAP_EXE_PATH")

        if [[ -f "$unix_path" && -x "$unix_path" ]]; then
            log_verbose "Using AutoMap executable from AUTOMAP_EXE_PATH"
            echo "$AUTOMAP_EXE_PATH"
            return 0
        else
            if [[ ! -f "$unix_path" ]]; then
                log_error "AUTOMAP_EXE_PATH is set but file not found: $AUTOMAP_EXE_PATH"
            else
                log_error "AUTOMAP_EXE_PATH is set but file is not executable: $AUTOMAP_EXE_PATH"
            fi
            log_error "Unset AUTOMAP_EXE_PATH or set it to a valid executable path"
            return 1
        fi
    fi

    if [ ! -x "$DETECT_SCRIPT" ]; then
        log_error "Detection script not found or not executable: $DETECT_SCRIPT"
        return 1
    fi

    local detect_args=()
    if [ "$VERBOSE" = true ]; then
        detect_args+=(--verbose)
    fi

    local automap_path
    if ! automap_path=$("$DETECT_SCRIPT" "${detect_args[@]}"); then
        log_error "AutoMap installation not found"
        return 1
    fi

    echo "$automap_path"
    return 0
}

build_automap_command() {
    local automap_path="$1"
    local project_file="$2"

    # Start with quoted executable path
    local cmd="\"$automap_path\""

    # Add clean flags
    if [ "$CLEAN_BUILD" = true ]; then
        cmd="$cmd -c"
    fi

    if [ "$CLEAN_DEPLOY" = true ]; then
        cmd="$cmd -l"
    fi

    # Add no deploy flags
    if [ "$NO_DEPLOY" = true ]; then
        cmd="$cmd -n"
    fi

    # Add target if specified (single or multiple)
    if [ -n "$TARGET_MULTI" ]; then
        # Multiple targets via --target=
        cmd="$cmd --target=\"$TARGET_MULTI\""
    elif [ -n "$TARGET" ]; then
        # Single target via -t
        cmd="$cmd -t \"$TARGET\""
    fi

    # Add deploy folder if specified
    if [ -n "$DEPLOY_FOLDER" ]; then
        cmd="$cmd --deployfolder=\"$DEPLOY_FOLDER\""
    fi

    # Add skip reports flag (2025.1+)
    if [ "$SKIP_REPORTS" = true ]; then
        cmd="$cmd --skip-reports"
    fi

    # Add project file (always last)
    cmd="$cmd \"$project_file\""

    echo "$cmd"
}

parse_automap_output() {
    local output_line="$1"

    # Check for success indicators
    if echo "$output_line" | grep -qi "generation completed successfully"; then
        log_success "$output_line"
        return 0
    fi

    if echo "$output_line" | grep -qi "output deployed to"; then
        log_success "$output_line"
        return 0
    fi

    # Check for error patterns
    if echo "$output_line" | grep -qiE "(^Error:|Failed to|Unable to|Exception)"; then
        log_error "$output_line"
        return 0
    fi

    # Check for warning patterns
    if echo "$output_line" | grep -qiE "(^Warning:|Could not find)"; then
        log_warning "$output_line"
        return 0
    fi

    # Check for progress indicators
    if echo "$output_line" | grep -qiE "(Processing|Generating|Transforming|Building)"; then
        log_info "$output_line"
        return 0
    fi

    # Default: echo the line in verbose mode
    if [ "$VERBOSE" = true ]; then
        echo "$output_line"
    fi
}

execute_automap() {
    local cmd="$1"
    local exit_code=0
    local start_time end_time duration

    start_time=$(date +%s)

    if [ "$VERBOSE" = true ]; then
        # Verbose mode: parse and display all output
        log_info "Executing AutoMap..."
        log_verbose "Command: $cmd"

        eval "$cmd" 2>&1 | while IFS= read -r line; do
            parse_automap_output "$line"
        done || exit_code=$?
    else
        # Default: minimal output, suppress stdout, stderr passes through
        eval "$cmd" > /dev/null
        exit_code=$?
    fi

    end_time=$(date +%s)
    duration=$((end_time - start_time))

    if [ $exit_code -eq 0 ]; then
        log_success "Build completed in ${duration}s"
    else
        log_error "Build failed with exit code $exit_code after ${duration}s"
    fi

    return $exit_code
}

#
# Argument Parsing
#

PROJECT_FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--clean)
            CLEAN_BUILD=true
            shift
            ;;
        -n|--nodeploy)
            NO_DEPLOY=true
            shift
            ;;
        -l|--cleandeploy)
            CLEAN_DEPLOY=true
            shift
            ;;
        -t)
            if [ -z "${2:-}" ]; then
                log_error "Missing TARGET argument"
                usage
                exit 2
            fi
            TARGET="$2"
            shift 2
            ;;
        --target=*)
            TARGET_MULTI="${1#--target=}"
            shift
            ;;
        -d)
            if [ -z "${2:-}" ]; then
                log_error "Missing PATH argument for -d"
                usage
                exit 2
            fi
            DEPLOY_FOLDER="$2"
            NO_DEPLOY=false  # Deployfolder implies deployment enabled
            shift 2
            ;;
        --deployfolder=*)
            DEPLOY_FOLDER="${1#--deployfolder=}"
            NO_DEPLOY=false  # Deployfolder implies deployment enabled
            shift
            ;;
        --skip-reports)
            SKIP_REPORTS=true
            shift
            ;;
        --with-reports)
            SKIP_REPORTS=false
            shift
            ;;
        --no-clean)
            CLEAN_BUILD=false
            shift
            ;;
        --deploy)
            NO_DEPLOY=false
            shift
            ;;
        --all-targets)
            ALL_TARGETS=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        -*)
            log_error "Unknown option: $1"
            usage
            exit 2
            ;;
        *)
            if [ -n "$PROJECT_FILE" ]; then
                log_error "Multiple project files specified"
                usage
                exit 2
            fi
            PROJECT_FILE="$1"
            shift
            ;;
    esac
done

#
# Validation
#

if [ -z "$PROJECT_FILE" ]; then
    log_error "Project file required"
    usage
    exit 2
fi

if ! validate_project_file "$PROJECT_FILE"; then
    exit 4
fi

# Check for conflicting flags
if [[ -n "$TARGET" || -n "$TARGET_MULTI" ]] && [[ "$ALL_TARGETS" = true ]]; then
    log_error "Cannot specify both -t/--target= and --all-targets"
    exit 2
fi

# Interactive target selection when no target specified
if [[ -z "$TARGET" && -z "$TARGET_MULTI" && "$ALL_TARGETS" != true ]]; then
    if ! select_targets "$PROJECT_FILE"; then
        exit 2
    fi
fi

#
# Main Execution
#

log_verbose "Starting AutoMap wrapper..."
log_verbose "Project file: $PROJECT_FILE"

# Detect AutoMap installation
if ! automap_path=$(detect_automap_executable); then
    exit 3
fi

log_info "Using AutoMap: $automap_path"

# Build command
automap_cmd=$(build_automap_command "$automap_path" "$PROJECT_FILE")

# Execute AutoMap
if execute_automap "$automap_cmd"; then
    exit 0
else
    exit 1
fi
