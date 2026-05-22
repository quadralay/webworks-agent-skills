#!/bin/bash
################################################################################
# detect-entry-point.sh
#
# Detects Reverb output directory and entry point from WebWorks project file.
# Extracts FormatSettings and determines where Reverb output was generated.
#
# Usage:
#   ./detect-entry-point.sh <project-file> [target-name]
#
# Arguments:
#   project-file  - Path to .wep project file
#   target-name   - Optional target name (default: first Reverb target found)
#
# Output:
#   JSON with output_dir, entry_point, and format_settings
#
################################################################################

set -euo pipefail

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m'

DEBUG="${DEBUG:-0}"

debug_log() {
    if [[ "$DEBUG" == "1" ]]; then
        echo -e "${YELLOW}[DEBUG]${NC} $*" >&2
    fi
}

error_log() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

################################################################################
# XML Parsing Helpers
################################################################################

# Extract attribute value from XML element
extract_attribute() {
    local xml="$1"
    local element="$2"
    local attribute="$3"

    echo "$xml" | grep -oP "(?<=<$element[^>]*$attribute=\")[^\"]*" || true
}

# Extract FormatSetting value by name
extract_format_setting() {
    local project_file="$1"
    local target_id="$2"
    local setting_name="$3"
    local default_value="${4:-}"

    debug_log "Extracting FormatSetting: $setting_name for target: $target_id"

    # Find FormatSetting within the target's FormatConfiguration
    local value
    value=$(grep -A 1000 "TargetID=\"$target_id\"" "$project_file" | \
            grep -oP "(?<=<FormatSetting Name=\"$setting_name\" Value=\")[^\"]*" | \
            head -n 1 || echo "$default_value")

    echo "${value:-$default_value}"
}

# Extract all FormatSettings for a target as JSON
extract_all_format_settings() {
    local project_file="$1"
    local target_id="$2"

    debug_log "Extracting all FormatSettings for target: $target_id"

    # Extract FormatSettings section for this target
    local settings_xml
    settings_xml=$(grep -A 1000 "TargetID=\"$target_id\"" "$project_file" | \
                   grep '<FormatSetting' | head -n 100 || true)

    if [[ -z "$settings_xml" ]]; then
        echo "{}"
        return
    fi

    # Convert to JSON using awk
    echo "$settings_xml" | awk '
    BEGIN {
        printf "{"
        first = 1
    }
    {
        if (match($0, /Name="([^"]+)" Value="([^"]+)"/, arr)) {
            if (!first) printf ","
            printf "\"%s\":\"%s\"", arr[1], arr[2]
            first = 0
        }
    }
    END {
        printf "}"
    }'
}

################################################################################
# Project File Analysis
################################################################################

validate_reverb_version() {
    local project_file="$1"
    local target_id="$2"

    debug_log "Validating Reverb version for target: $target_id"

    # Extract format Name for this target from Format element
    local format_name
    format_name=$(grep "<Format" "$project_file" | \
                  grep "TargetID=\"$target_id\"" | \
                  sed -n 's/.*Name="\([^"]*\)".*/\1/p' | head -n 1 || true)

    debug_log "Detected format: $format_name"

    if [[ "$format_name" == "WebWorks Reverb 2.0" ]]; then
        debug_log "✓ Verified Reverb 2.0 format"
        return 0
    elif [[ "$format_name" == "WebWorks Reverb" ]]; then
        error_log "Legacy WebWorks Reverb (version 1.x) detected"
        error_log ""
        error_log "This skill only supports WebWorks Reverb 2.0"
        error_log "Your project uses: $format_name"
        error_log ""
        error_log "Please upgrade your project to Reverb 2.0 or use legacy analysis tools."
        return 1
    else
        error_log "Unknown or unsupported Reverb format: $format_name"
        error_log "This skill requires: WebWorks Reverb 2.0"
        return 1
    fi
}

find_reverb_target() {
    local project_file="$1"
    local target_name="${2:-}"

    debug_log "Looking for Reverb targets in project file..."

    # If target name specified, find its ID
    if [[ -n "$target_name" ]]; then
        local target_id
        target_id=$(grep "<Format" "$project_file" | grep "TargetName=\"$target_name\"" | \
                    sed -n 's/.*TargetID="\([^"]*\)".*/\1/p' | head -n 1 || true)

        if [[ -z "$target_id" ]]; then
            error_log "Target '$target_name' not found in project file"
            return 1
        fi

        echo "$target_id"
        return 0
    fi

    # Find first Reverb target (look for Format with Name="WebWorks Reverb")
    local target_id
    target_id=$(grep "<Format" "$project_file" | \
                grep 'Name="WebWorks Reverb' | \
                sed -n 's/.*TargetID="\([^"]*\)".*/\1/p' | head -n 1 || true)

    if [[ -z "$target_id" ]]; then
        error_log "No Reverb targets found in project file"
        return 1
    fi

    echo "$target_id"
}

get_target_name() {
    local project_file="$1"
    local target_id="$2"

    grep "<Format" "$project_file" | grep "TargetID=\"$target_id\"" | \
        sed -n 's/.*TargetName="\([^"]*\)".*/\1/p' | head -n 1 || echo "Unknown"
}

get_output_directory() {
    local project_file="$1"
    local target_id="$2"

    debug_log "Finding output directory for target: $target_id"

    # Look for OutputDirectory element within the Format element for this target
    local output_path
    output_path=$(grep -A 5 "TargetID=\"$target_id\"" "$project_file" | \
                  grep "<OutputDirectory>" | \
                  sed -n 's/.*<OutputDirectory>\(.*\)<\/OutputDirectory>.*/\1/p' | head -n 1 || true)

    if [[ -z "$output_path" ]]; then
        error_log "Output directory not found for target"
        return 1
    fi

    # Convert to absolute path if relative
    local project_dir
    project_dir=$(dirname "$(realpath "$project_file")")

    if [[ "$output_path" =~ ^[A-Za-z]:\\ ]] || [[ "$output_path" =~ ^/ ]]; then
        # Already absolute
        echo "$output_path"
    else
        # Relative to project file
        echo "$project_dir/$output_path"
    fi
}

################################################################################
# Main Logic
################################################################################

main() {
    if [[ $# -lt 1 ]]; then
        error_log "Usage: $0 <project-file> [target-name]"
        exit 1
    fi

    local project_file="$1"
    local target_name="${2:-}"

    # Validate project file exists
    if [[ ! -f "$project_file" ]]; then
        error_log "Project file not found: $project_file"
        exit 1
    fi

    debug_log "Analyzing project file: $project_file"

    # Find target
    local target_id
    target_id=$(find_reverb_target "$project_file" "$target_name")

    if [[ -z "$target_id" ]]; then
        exit 1
    fi

    # Get target details
    local target_display_name
    target_display_name=$(get_target_name "$project_file" "$target_id")

    debug_log "Found target: $target_display_name (ID: $target_id)"

    # Validate Reverb version
    if ! validate_reverb_version "$project_file" "$target_id"; then
        exit 1
    fi

    # Get output directory
    local output_dir
    output_dir=$(get_output_directory "$project_file" "$target_id")

    # Extract entry point setting
    local entry_point
    entry_point=$(extract_format_setting "$project_file" "$target_id" "connect-entry" "index.html")

    # Extract all FormatSettings
    local format_settings
    format_settings=$(extract_all_format_settings "$project_file" "$target_id")

    # Build result JSON
    cat <<EOF
{
  "target_id": "$target_id",
  "target_name": "$target_display_name",
  "output_dir": "$output_dir",
  "entry_point": "$entry_point",
  "entry_url": "file://$output_dir/$entry_point",
  "format_settings": $format_settings
}
EOF
}

main "$@"
