#!/bin/bash
#
# manage-sources.sh
# Manage source files in ePublisher project files
#
# Usage:
#   ./manage-sources.sh [OPTIONS] <project-file>
#
# Features:
#   - List all source documents with paths and inclusion status
#   - Add documents to existing groups
#   - Remove documents from project
#   - Toggle document inclusion status
#   - Validate source file paths
#   - Generate unique IDs for new documents
#
# Exit Codes:
#   0 - Success
#   1 - Project file not found or invalid
#   2 - Invalid arguments
#   3 - No documents found in project
#   4 - Source file not found
#

set -euo pipefail

# Script configuration
SCRIPT_NAME="$(basename "$0")"
ACTION=""
PROJECT_FILE=""
DOCUMENT_PATH=""
GROUP_NAME=""
DOCUMENT_TYPE="fm-maker"
VERBOSE=false

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

#
# Helper Functions
#

log_verbose() {
    if [ "$VERBOSE" = true ]; then
        echo "[VERBOSE] $*" >&2
    fi
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

usage() {
    cat <<EOF
Usage: $SCRIPT_NAME [OPTIONS] <project-file>

Manage source documents and books in ePublisher project files (.wep, .wrp, .wxsp).

REQUIRED:
    <project-file>          Path to .wep, .wrp, or .wxsp project file

ACTIONS:
    -l, --list              List all source documents and books with status
    -a, --add PATH          Add document to project (requires --group)
    -r, --remove PATH       Remove document from project
    -t, --toggle PATH       Toggle document/book inclusion status
    -v, --validate          Validate all source file paths exist

OPTIONS:
    -g, --group NAME        Group name for adding documents
    --type TYPE             Document type (default: fm-maker)
                            Options: fm-maker, fm-html, fm-dita, fm-word
    --json                  Output in JSON format (list only)
    --verbose               Enable verbose output
    --help                  Show this help message

EXIT CODES:
    0    Success
    1    Project file not found or invalid
    2    Invalid arguments
    3    No documents found in project
    4    Source file not found

EXAMPLES:
    # List all source documents
    $SCRIPT_NAME --list project.wep

    # Add new Markdown document to existing group
    $SCRIPT_NAME --add "Source\\new-chapter.md" --group "Group1" project.wep

    # Remove document from project
    $SCRIPT_NAME --remove "Source\\old-content.md" project.wep

    # Toggle document inclusion
    $SCRIPT_NAME --toggle "Source\\draft.md" project.wep

    # Validate all source paths
    $SCRIPT_NAME --validate project.wep

    # List in JSON format
    $SCRIPT_NAME --list --json project.wep
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
    if [[ ! "$project_file" =~ \.(wep|wrp|wxsp)$ ]]; then
        log_error "Invalid project file extension: $project_file"
        log_error "Expected: .wep or .wrp or .wxsp"
        return 1
    fi

    return 0
}

generate_id() {
    local length="${1:-11}"
    # Generate random alphanumeric ID
    cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w "$length" | head -n 1
}

list_documents() {
    local project_file="$1"
    local json_output="${2:-false}"

    log_verbose "Extracting document and book information from: $project_file"

    # Extract all Document and Book elements
    local doc_lines
    doc_lines=$(grep -E '<(Document|Book) ' "$project_file" || true)

    if [ -z "$doc_lines" ]; then
        log_error "No Document or Book elements found in project file"
        return 3
    fi

    if [ "$json_output" = "true" ]; then
        echo "["
        local first=true
        while IFS= read -r line; do
            local path included doc_type doc_id

            # Extract attributes (can appear in any order)
            path=$(echo "$line" | grep -oP '\sPath="\K[^"]+' || echo "Unknown")
            included=$(echo "$line" | grep -oP '\sIncluded="\K[^"]+' || echo "true")
            doc_type=$(echo "$line" | grep -oP '\sType="\K[^"]+' || echo "Unknown")
            doc_id=$(echo "$line" | grep -oP '\sDocumentID="\K[^"]+' || echo "Unknown")

            if [ "$first" = true ]; then
                first=false
            else
                echo ","
            fi

            cat <<JSON_ENTRY
  {
    "path": "$path",
    "included": $included,
    "type": "$doc_type",
    "documentId": "$doc_id"
  }
JSON_ENTRY
        done <<< "$doc_lines"
        echo ""
        echo "]"
    else
        echo -e "${BLUE}Source Documents and Books:${NC}"
        echo ""
        local count=1
        while IFS= read -r line; do
            local path included doc_type

            # Extract attributes (can appear in any order)
            path=$(echo "$line" | grep -oP '\sPath="\K[^"]+' || echo "Unknown")
            included=$(echo "$line" | grep -oP '\sIncluded="\K[^"]+' || echo "true")
            doc_type=$(echo "$line" | grep -oP '\sType="\K[^"]+' || echo "Unknown")

            local status_color
            if [ "$included" = "true" ]; then
                status_color="${GREEN}"
            else
                status_color="${YELLOW}"
            fi

            printf "%d. ${status_color}[%s]${NC} %s\n" "$count" "$included" "$path"
            echo "   Type: $doc_type"
            echo ""

            ((count++))
        done <<< "$doc_lines"
    fi
}

validate_sources() {
    local project_file="$1"
    local project_dir
    project_dir=$(dirname "$project_file")

    log_info "Validating source file paths..."

    local doc_lines
    doc_lines=$(grep -E '<(Document|Book) ' "$project_file" || true)

    if [ -z "$doc_lines" ]; then
        log_error "No Document or Book elements found in project file"
        return 3
    fi

    local valid_count=0
    local invalid_count=0
    local invalid_paths=()

    while IFS= read -r line; do
        local path included

        # Extract attributes (can appear in any order)
        path=$(echo "$line" | grep -oP '\sPath="\K[^"]+' || echo "")
        included=$(echo "$line" | grep -oP '\sIncluded="\K[^"]+' || echo "true")

        if [ -z "$path" ]; then
            continue
        fi

        # Convert backslashes to forward slashes for bash
        local unix_path="${path//\\//}"

        # Build absolute path
        local full_path
        if [[ "$unix_path" =~ ^[A-Za-z]: ]]; then
            # Absolute path
            full_path=$(cygpath "$unix_path" 2>/dev/null || echo "$unix_path")
        else
            # Relative path
            full_path="$project_dir/$unix_path"
        fi

        if [ -f "$full_path" ]; then
            valid_count=$((valid_count + 1))
            printf "${GREEN}✓${NC} %s\n" "$path"
        else
            invalid_count=$((invalid_count + 1))
            invalid_paths+=("$path")
            printf "${RED}✗${NC} %s (not found)\n" "$path"
        fi
    done <<< "$doc_lines"

    echo ""
    if [ "$invalid_count" -eq 0 ]; then
        log_success "All $valid_count source files validated successfully"
        return 0
    else
        log_error "$invalid_count source file(s) not found"
        return 4
    fi
}

add_document() {
    local project_file="$1"
    local doc_path="$2"
    local group_name="$3"
    local doc_type="$4"

    log_verbose "Adding document: $doc_path to group: $group_name"

    # Verify source file exists
    local project_dir
    project_dir=$(dirname "$project_file")

    local unix_path="${doc_path//\\//}"
    local full_path
    if [[ "$unix_path" =~ ^[A-Za-z]: ]]; then
        full_path=$(cygpath "$unix_path" 2>/dev/null || echo "$unix_path")
    else
        full_path="$project_dir/$unix_path"
    fi

    if [ ! -f "$full_path" ]; then
        log_error "Source file not found: $full_path"
        return 4
    fi

    # Check if group exists
    if ! grep -q "Group Name=\"$group_name\"" "$project_file"; then
        log_error "Group not found: $group_name"
        log_info "Available groups:"
        grep -oP 'Group Name="\K[^"]+' "$project_file" | sed 's/^/  - /'
        return 2
    fi

    # Check if document already exists
    if grep -q "Path=\"$doc_path\"" "$project_file"; then
        log_error "Document already exists in project: $doc_path"
        return 2
    fi

    # Generate unique document ID
    local doc_id
    doc_id=$(generate_id 9)

    # Create document element
    local new_doc="    <Document Path=\"$doc_path\" Type=\"$doc_type\" Included=\"true\" DocumentID=\"$doc_id\" />"

    # Find the closing tag of the group and add before it
    # This is a complex operation - inform user to manually add for now
    log_error "Adding documents requires XML manipulation."
    log_info "Please use the Edit tool to add the following line inside the <Group Name=\"$group_name\"> element:"
    echo ""
    echo "$new_doc"
    echo ""
    return 2
}

remove_document() {
    local project_file="$1"
    local doc_path="$2"

    log_verbose "Removing document: $doc_path"

    # Check if document exists
    if ! grep -q "Path=\"$doc_path\"" "$project_file"; then
        log_error "Document not found in project: $doc_path"
        return 2
    fi

    log_error "Removing documents requires XML manipulation."
    log_info "Please use the Edit tool to remove the <Document> element with Path=\"$doc_path\""
    return 2
}

toggle_inclusion() {
    local project_file="$1"
    local doc_path="$2"

    log_verbose "Toggling inclusion for: $doc_path"

    # Check if document exists
    local doc_line
    doc_line=$(grep "Path=\"$doc_path\"" "$project_file" || true)

    if [ -z "$doc_line" ]; then
        log_error "Document not found in project: $doc_path"
        return 2
    fi

    # Get current inclusion status
    local current_status
    current_status=$(echo "$doc_line" | grep -oP 'Included="\K[^"]+' || echo "true")

    local new_status
    if [ "$current_status" = "true" ]; then
        new_status="false"
    else
        new_status="true"
    fi

    log_info "Current status: Included=\"$current_status\""
    log_info "New status: Included=\"$new_status\""
    log_info ""
    log_info "Please use the Edit tool to change:"
    echo "  Old: Included=\"$current_status\""
    echo "  New: Included=\"$new_status\""
    echo "  In line: $doc_line"

    return 0
}

#
# Argument Parsing
#

JSON_OUTPUT=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -l|--list)
            ACTION="list"
            shift
            ;;
        -a|--add)
            ACTION="add"
            if [ -z "${2:-}" ]; then
                log_error "Missing PATH argument"
                usage
                exit 2
            fi
            DOCUMENT_PATH="$2"
            shift 2
            ;;
        -r|--remove)
            ACTION="remove"
            if [ -z "${2:-}" ]; then
                log_error "Missing PATH argument"
                usage
                exit 2
            fi
            DOCUMENT_PATH="$2"
            shift 2
            ;;
        -t|--toggle)
            ACTION="toggle"
            if [ -z "${2:-}" ]; then
                log_error "Missing PATH argument"
                usage
                exit 2
            fi
            DOCUMENT_PATH="$2"
            shift 2
            ;;
        -v|--validate)
            ACTION="validate"
            shift
            ;;
        -g|--group)
            if [ -z "${2:-}" ]; then
                log_error "Missing GROUP argument"
                usage
                exit 2
            fi
            GROUP_NAME="$2"
            shift 2
            ;;
        --type)
            if [ -z "${2:-}" ]; then
                log_error "Missing TYPE argument"
                usage
                exit 2
            fi
            DOCUMENT_TYPE="$2"
            shift 2
            ;;
        --json)
            JSON_OUTPUT=true
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

if [ -z "$ACTION" ]; then
    log_error "No action specified"
    usage
    exit 2
fi

if [ -z "$PROJECT_FILE" ]; then
    log_error "Project file required"
    usage
    exit 2
fi

if ! validate_project_file "$PROJECT_FILE"; then
    exit 1
fi

# Action-specific validation
if [ "$ACTION" = "add" ] && [ -z "$GROUP_NAME" ]; then
    log_error "Group name required for adding documents (use --group)"
    exit 2
fi

#
# Main Execution
#

log_verbose "Performing action: $ACTION"
log_verbose "Project file: $PROJECT_FILE"

case "$ACTION" in
    list)
        list_documents "$PROJECT_FILE" "$JSON_OUTPUT"
        ;;
    validate)
        validate_sources "$PROJECT_FILE"
        ;;
    add)
        add_document "$PROJECT_FILE" "$DOCUMENT_PATH" "$GROUP_NAME" "$DOCUMENT_TYPE"
        ;;
    remove)
        remove_document "$PROJECT_FILE" "$DOCUMENT_PATH"
        ;;
    toggle)
        toggle_inclusion "$PROJECT_FILE" "$DOCUMENT_PATH"
        ;;
    *)
        log_error "Unknown action: $ACTION"
        exit 2
        ;;
esac

exit $?
