#!/bin/bash
#
# detect-installation.sh
# Detects WebWorks ePublisher AutoMap CLI installation using Windows Registry
#
# This script detects AutoMap installations via registry or filesystem search.
# Both methods initially find the Administrator executable, then normalize
# to the CLI executable path for automation purposes.
#
# Executable Types:
#   - WebWorks.Automap.Administrator.exe (UI for job scheduling)
#   - WebWorks.Automap.exe (CLI for automation) <- This is returned
#
# Usage:
#   ./detect-installation.sh [--version VERSION] [--verbose]
#
# Exit Codes:
#   0 - AutoMap CLI found
#   1 - AutoMap not found
#   2 - Invalid arguments
#
# Output:
#   Prints full path to AutoMap CLI executable on success
#

set -euo pipefail

# Script configuration
SCRIPT_NAME="$(basename "$0")"
VERBOSE=false
REQUESTED_VERSION=""
SHOW_BUILD=false

# Registry paths
REG_PATH_64BIT="HKLM\\SOFTWARE\\WebWorks\\ePublisher AutoMap"
REG_PATH_32BIT="HKLM\\SOFTWARE\\WOW6432Node\\WebWorks\\ePublisher AutoMap"

# Fallback installation paths
FALLBACK_PATHS=(
    "C:\\Program Files\\WebWorks\\ePublisher"
    "C:\\Program Files (x86)\\WebWorks\\ePublisher"
)

#
# Helper Functions
#

log_verbose() {
    if [ "$VERBOSE" = true ]; then
        echo "[VERBOSE] $*" >&2
    fi
}

log_error() {
    echo "[ERROR] $*" >&2
}

usage() {
    cat <<EOF
Usage: $SCRIPT_NAME [OPTIONS]

Detects WebWorks ePublisher AutoMap CLI installation on Windows systems.
Returns path to the CLI executable (WebWorks.Automap.exe) for automation.

OPTIONS:
    --version VERSION    Detect specific version (e.g., 2024.1)
    --show-build        Display build number along with executable path
    --verbose           Enable verbose output
    --help              Show this help message

EXIT CODES:
    0    AutoMap found
    1    AutoMap not found
    2    Invalid arguments

EXAMPLES:
    # Detect latest AutoMap installation
    $SCRIPT_NAME

    # Detect specific version
    $SCRIPT_NAME --version 2024.1

    # Show build number
    $SCRIPT_NAME --show-build

    # Verbose mode
    $SCRIPT_NAME --verbose

OUTPUT:
    On success, prints full path to AutoMap CLI executable:
    C:\\Program Files\\WebWorks\\ePublisher\\2024.1\\ePublisher AutoMap\\WebWorks.Automap.exe

    Note: The script detects the Administrator executable but returns the CLI path.

    With --show-build, also displays build number:
    C:\\Program Files\\WebWorks\\ePublisher\\2024.1\\ePublisher AutoMap\\WebWorks.Automap.exe
    Build: 4603
EOF
}

#
# Registry Query Functions
#

query_registry_versions() {
    local reg_path="$1"

    log_verbose "Querying registry path: $reg_path"

    # Query registry for subkeys (versions)
    local versions
    versions=$(reg query "$reg_path" 2>/dev/null | grep "HKEY" | sed 's/.*\\//' || true)

    if [ -n "$versions" ]; then
        log_verbose "Found versions: $versions"
        echo "$versions"
        return 0
    fi

    return 1
}

query_registry_exepath() {
    local reg_path="$1"
    local version="$2"

    local full_path="$reg_path\\$version"
    log_verbose "Querying ExePath from: $full_path"

    # Query ExePath value (without /v flag for compatibility)
    local exe_path
    exe_path=$(reg query "$full_path" 2>/dev/null | grep "ExePath" | awk '{for(i=3;i<=NF;i++) printf "%s ", $i; print ""}' | sed 's/ $//' || true)

    if [ -n "$exe_path" ]; then
        log_verbose "Found ExePath: $exe_path"
        echo "$exe_path"
        return 0
    fi

    return 1
}

query_registry_build_number() {
    local reg_path="$1"
    local version="$2"

    local full_path="$reg_path\\$version"
    log_verbose "Querying Version from: $full_path"

    # Query Version value (e.g., "24.1.4603") - without /v flag for compatibility
    local version_string
    version_string=$(reg query "$full_path" 2>/dev/null | grep "Version" | grep "REG_SZ" | awk '{for(i=3;i<=NF;i++) printf "%s ", $i; print ""}' | sed 's/ $//' || true)

    if [ -n "$version_string" ]; then
        log_verbose "Found Version: $version_string"

        # Extract build number (last fragment after final dot)
        local build_number
        build_number=$(echo "$version_string" | awk -F'.' '{print $NF}')

        if [ -n "$build_number" ]; then
            log_verbose "Extracted Build Number: $build_number"
            echo "$build_number"
            return 0
        fi
    fi

    return 1
}

validate_executable() {
    local exe_path="$1"

    # Convert Windows path to Unix-style for test
    local unix_path
    unix_path=$(cygpath "$exe_path" 2>/dev/null || echo "$exe_path")

    if [ -f "$unix_path" ]; then
        log_verbose "Validated executable exists: $exe_path"
        return 0
    fi

    log_verbose "Executable does not exist: $exe_path"
    return 1
}

#
# Normalizes AutoMap executable paths to CLI version
#
# Converts paths pointing to WebWorks.Automap.Administrator.exe to
# the corresponding CLI executable WebWorks.Automap.exe
#
# Arguments:
#   $1 - Full path to AutoMap executable (Administrator or CLI)
#
# Returns:
#   0 - CLI executable path (on success)
#   1 - Executable not found or validation failed
#
# Output:
#   Prints full path to CLI executable
#
normalize_to_cli_path() {
    local exe_path="$1"

    log_verbose "Normalizing path to CLI executable: $exe_path"

    # If path points to Administrator executable, convert to CLI executable
    if [[ "$exe_path" == *"Automap.Administrator.exe"* ]]; then
        # Remove ".Administrator" from filename
        local cli_path="${exe_path/.Administrator.exe/.exe}"
        log_verbose "Converted Administrator path to CLI path: $cli_path"

        # Validate that CLI executable exists
        if validate_executable "$cli_path"; then
            echo "$cli_path"
            return 0
        else
            log_error "CLI executable not found at: $cli_path"
            log_error "Administrator executable exists but CLI does not"
            return 1
        fi
    fi

    # Path already points to CLI executable (or some other file)
    if validate_executable "$exe_path"; then
        echo "$exe_path"
        return 0
    fi

    return 1
}

#
# Detection Functions
#

detect_via_registry() {
    local requested_version="$1"

    # Try 64-bit registry first
    log_verbose "Attempting 64-bit registry detection..."

    if versions=$(query_registry_versions "$REG_PATH_64BIT"); then
        log_verbose "Found 64-bit installations"

        if [ -n "$requested_version" ]; then
            # Check for specific version
            if echo "$versions" | grep -q "^${requested_version}$"; then
                log_verbose "Found requested version: $requested_version"

                if exe_path=$(query_registry_exepath "$REG_PATH_64BIT" "$requested_version"); then
                    if cli_path=$(normalize_to_cli_path "$exe_path"); then
                        # Query build number if requested
                        if [ "$SHOW_BUILD" = true ]; then
                            if build_number=$(query_registry_build_number "$REG_PATH_64BIT" "$requested_version"); then
                                log_verbose "Build number: $build_number"
                                echo "$cli_path|$build_number"
                            else
                                echo "$cli_path|"
                            fi
                        else
                            echo "$cli_path"
                        fi
                        return 0
                    fi
                fi
            fi
        else
            # Find latest version
            local latest_version
            latest_version=$(echo "$versions" | sort -V | tail -1)
            log_verbose "Latest version: $latest_version"

            if exe_path=$(query_registry_exepath "$REG_PATH_64BIT" "$latest_version"); then
                if cli_path=$(normalize_to_cli_path "$exe_path"); then
                    # Query build number if requested
                    if [ "$SHOW_BUILD" = true ]; then
                        if build_number=$(query_registry_build_number "$REG_PATH_64BIT" "$latest_version"); then
                            log_verbose "Build number: $build_number"
                            echo "$cli_path|$build_number"
                        else
                            echo "$cli_path|"
                        fi
                    else
                        echo "$cli_path"
                    fi
                    return 0
                fi
            fi
        fi
    fi

    # Try 32-bit registry
    log_verbose "Attempting 32-bit registry detection..."

    if versions=$(query_registry_versions "$REG_PATH_32BIT"); then
        log_verbose "Found 32-bit installations"

        if [ -n "$requested_version" ]; then
            # Check for specific version
            if echo "$versions" | grep -q "^${requested_version}$"; then
                log_verbose "Found requested version: $requested_version"

                if exe_path=$(query_registry_exepath "$REG_PATH_32BIT" "$requested_version"); then
                    if cli_path=$(normalize_to_cli_path "$exe_path"); then
                        # Query build number if requested
                        if [ "$SHOW_BUILD" = true ]; then
                            if build_number=$(query_registry_build_number "$REG_PATH_32BIT" "$requested_version"); then
                                log_verbose "Build number: $build_number"
                                echo "$cli_path|$build_number"
                            else
                                echo "$cli_path|"
                            fi
                        else
                            echo "$cli_path"
                        fi
                        return 0
                    fi
                fi
            fi
        else
            # Find latest version
            local latest_version
            latest_version=$(echo "$versions" | sort -V | tail -1)
            log_verbose "Latest version: $latest_version"

            if exe_path=$(query_registry_exepath "$REG_PATH_32BIT" "$latest_version"); then
                if cli_path=$(normalize_to_cli_path "$exe_path"); then
                    # Query build number if requested
                    if [ "$SHOW_BUILD" = true ]; then
                        if build_number=$(query_registry_build_number "$REG_PATH_32BIT" "$latest_version"); then
                            log_verbose "Build number: $build_number"
                            echo "$cli_path|$build_number"
                        else
                            echo "$cli_path|"
                        fi
                    else
                        echo "$cli_path"
                    fi
                    return 0
                fi
            fi
        fi
    fi

    return 1
}

detect_via_filesystem() {
    local requested_version="$1"

    log_verbose "Attempting filesystem detection..."

    for base_path in "${FALLBACK_PATHS[@]}"; do
        log_verbose "Checking: $base_path"

        # Convert to Unix path for find
        local unix_base
        unix_base=$(cygpath "$base_path" 2>/dev/null || echo "$base_path")

        if [ ! -d "$unix_base" ]; then
            log_verbose "Directory does not exist: $base_path"
            continue
        fi

        if [ -n "$requested_version" ]; then
            # Check specific version (look for Administrator executable)
            local exe_path="$base_path\\$requested_version\\ePublisher AutoMap\\WebWorks.Automap.Administrator.exe"

            if cli_path=$(normalize_to_cli_path "$exe_path"); then
                # Filesystem detection cannot provide build number
                if [ "$SHOW_BUILD" = true ]; then
                    echo "$cli_path|"
                else
                    echo "$cli_path"
                fi
                return 0
            fi
        else
            # Find all versions and select latest
            local versions
            versions=$(find "$unix_base" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null | grep -E '^[0-9]+\.[0-9]+' | sort -V || true)

            if [ -n "$versions" ]; then
                local latest_version
                latest_version=$(echo "$versions" | tail -1)
                log_verbose "Found version via filesystem: $latest_version"

                local exe_path="$base_path\\$latest_version\\ePublisher AutoMap\\WebWorks.Automap.Administrator.exe"

                if cli_path=$(normalize_to_cli_path "$exe_path"); then
                    # Filesystem detection cannot provide build number
                    if [ "$SHOW_BUILD" = true ]; then
                        echo "$cli_path|"
                    else
                        echo "$cli_path"
                    fi
                    return 0
                fi
            fi
        fi
    done

    return 1
}

#
# Main Detection Logic
#

detect_automap() {
    local requested_version="$1"

    # Try registry first (preferred method)
    if exe_path=$(detect_via_registry "$requested_version"); then
        log_verbose "Detection successful via registry"
        echo "$exe_path"
        return 0
    fi

    log_verbose "Registry detection failed, trying filesystem..."

    # Fallback to filesystem search
    if exe_path=$(detect_via_filesystem "$requested_version"); then
        log_verbose "Detection successful via filesystem"
        echo "$exe_path"
        return 0
    fi

    log_error "AutoMap installation not found"
    return 1
}

#
# Argument Parsing
#

while [[ $# -gt 0 ]]; do
    case $1 in
        --version)
            if [ -z "${2:-}" ]; then
                log_error "Missing VERSION argument"
                usage
                exit 2
            fi
            REQUESTED_VERSION="$2"
            shift 2
            ;;
        --show-build)
            SHOW_BUILD=true
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
        *)
            log_error "Unknown option: $1"
            usage
            exit 2
            ;;
    esac
done

#
# Execute Detection
#

log_verbose "Starting AutoMap detection..."
if [ -n "$REQUESTED_VERSION" ]; then
    log_verbose "Requested version: $REQUESTED_VERSION"
fi

if automap_result=$(detect_automap "$REQUESTED_VERSION"); then
    if [ "$SHOW_BUILD" = true ]; then
        # Parse output: path|build
        automap_path=$(echo "$automap_result" | cut -d'|' -f1)
        build_number=$(echo "$automap_result" | cut -d'|' -f2)

        echo "$automap_path"
        if [ -n "$build_number" ]; then
            echo "Build: $build_number"
        fi
    else
        echo "$automap_result"
    fi
    exit 0
else
    exit 1
fi
