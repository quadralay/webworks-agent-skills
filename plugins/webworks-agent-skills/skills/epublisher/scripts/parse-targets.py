#!/usr/bin/env python3
"""
parse-targets.py

Parse ePublisher project files to extract target and format information.

Usage:
    python parse-targets.py [OPTIONS] <project-file>

Features:
    - Extract target names (for AutoMap -t parameter)
    - Extract format names (for customization paths)
    - Extract Base Format Version (for customization file sources)
    - List all targets with details
    - Validate specific target names
    - JSON output option for programmatic use

Exit Codes:
    0 - Success
    1 - Project file not found or invalid
    2 - Invalid arguments
    3 - No targets found in project
"""

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

# Exit codes
EXIT_SUCCESS = 0
EXIT_FILE_ERROR = 1
EXIT_ARG_ERROR = 2
EXIT_NO_TARGETS = 3

# ANSI color codes
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color


def log_verbose(message: str, verbose: bool) -> None:
    """Print verbose message to stderr."""
    if verbose:
        print(f"[VERBOSE] {message}", file=sys.stderr)


def log_error(message: str) -> None:
    """Print error message to stderr."""
    print(f"[ERROR] {message}", file=sys.stderr)


def validate_project_file(project_file: str) -> bool:
    """Validate that the project file exists and has a valid extension."""
    path = Path(project_file)

    if not path.exists():
        log_error(f"Project file not found: {project_file}")
        return False

    valid_extensions = {'.wep', '.wrp', '.wxsp'}
    if path.suffix.lower() not in valid_extensions:
        log_error(f"Invalid project file extension: {project_file}")
        log_error("Expected: .wep or .wrp or .wxsp")
        return False

    return True


def parse_project_xml(project_file: str) -> Optional[ET.Element]:
    """Parse the project XML file and return the root element."""
    try:
        tree = ET.parse(project_file)
        return tree.getroot()
    except ET.ParseError as e:
        log_error(f"Failed to parse XML: {e}")
        return None
    except Exception as e:
        log_error(f"Failed to read file: {e}")
        return None


def extract_targets(root: ET.Element) -> list[dict]:
    """Extract all target information from Format elements."""
    targets = []

    # Handle namespace - ePublisher project files use this namespace
    ns = {'ep': 'urn:WebWorks-Publish-Project'}

    # Try with namespace first, then without (for older project files)
    format_elements = root.findall('.//ep:Format', ns)
    if not format_elements:
        format_elements = list(root.iter('Format'))

    for format_elem in format_elements:
        target = {
            'targetName': format_elem.get('TargetName', 'Unknown'),
            'formatName': format_elem.get('Name', 'Unknown'),
            'type': format_elem.get('Type', 'Unknown'),
            'targetId': format_elem.get('TargetID', 'Unknown'),
            'outputDirectory': ''
        }

        # Look for OutputDirectory child element (with and without namespace)
        output_dir_elem = format_elem.find('ep:OutputDirectory', ns)
        if output_dir_elem is None:
            output_dir_elem = format_elem.find('OutputDirectory')
        if output_dir_elem is not None and output_dir_elem.text:
            target['outputDirectory'] = output_dir_elem.text
        else:
            # Default output directory
            target['outputDirectory'] = f"Output\\{target['targetName']}"

        targets.append(target)

    return targets


def extract_base_format_version(root: ET.Element) -> Optional[str]:
    """Extract the Base Format Version from the Project element."""
    # The root element should be Project
    runtime_version = root.get('RuntimeVersion', '')
    format_version = root.get('FormatVersion', '')

    if not runtime_version:
        log_error("RuntimeVersion not found in project file")
        return None

    # Determine Base Format Version
    if format_version == '{Current}' or not format_version:
        return runtime_version
    else:
        return format_version


def output_target_names(targets: list[dict]) -> None:
    """Output just the target names (default mode)."""
    for target in targets:
        print(target['targetName'])


def output_format_names(targets: list[dict]) -> None:
    """Output just the format names."""
    for target in targets:
        print(target['formatName'])


def output_targets_detailed(targets: list[dict]) -> None:
    """Output detailed target information."""
    for i, target in enumerate(targets, 1):
        print(f"{GREEN}Target {i}:{NC} {target['targetName']}")
        print(f"  Format: {target['formatName']}")
        print(f"  Type: {target['type']}")
        print(f"  ID: {target['targetId']}")
        print(f"  Output: {target['outputDirectory']}")
        print()


def output_targets_json(targets: list[dict]) -> None:
    """Output targets in JSON format."""
    print(json.dumps(targets, indent=2))


def validate_target(targets: list[dict], target_name: str) -> bool:
    """Validate that a specific target exists."""
    target_names = [t['targetName'] for t in targets]

    if target_name in target_names:
        print(f"{GREEN}\u2713{NC} Target found: {target_name}")
        return True
    else:
        print(f"{YELLOW}\u2717{NC} Target not found: {target_name}")
        print()
        print("Available targets:")
        for name in target_names:
            print(f"  - {name}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Parse ePublisher project files (.wep, .wrp) to extract target and format information.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exit Codes:
    0    Success
    1    Project file not found or invalid
    2    Invalid arguments
    3    No targets found in project

Examples:
    # List all target names (simple)
    %(prog)s project.wep

    # List all targets with details
    %(prog)s --list project.wep

    # Show format names for customization paths
    %(prog)s --format-names project.wep

    # Show Base Format Version
    %(prog)s --version project.wep

    # Validate target exists
    %(prog)s --validate "WebWorks Reverb 2.0" project.wep

    # JSON output for scripts
    %(prog)s --json project.wep
"""
    )

    parser.add_argument('project_file', metavar='project-file',
                        help='Path to .wep or .wrp project file')
    parser.add_argument('-l', '--list', action='store_true',
                        help='List all targets with details')
    parser.add_argument('-f', '--format-names', action='store_true',
                        help='Show format names (used for customization paths)')
    parser.add_argument('--version', action='store_true', dest='show_version',
                        help='Show Base Format Version for customizations')
    parser.add_argument('-v', '--validate', metavar='TARGET',
                        help='Validate that specific target exists')
    parser.add_argument('-j', '--json', action='store_true',
                        help='Output in JSON format')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose output')

    args = parser.parse_args()

    # Validate project file
    if not validate_project_file(args.project_file):
        return EXIT_FILE_ERROR

    log_verbose(f"Parsing project file: {args.project_file}", args.verbose)

    # Parse XML
    root = parse_project_xml(args.project_file)
    if root is None:
        return EXIT_FILE_ERROR

    # Handle --version (Base Format Version)
    if args.show_version:
        version = extract_base_format_version(root)
        if version:
            print(version)
            return EXIT_SUCCESS
        return EXIT_NO_TARGETS

    # Extract targets
    targets = extract_targets(root)

    if not targets:
        log_error("No targets found in project file")
        return EXIT_NO_TARGETS

    log_verbose(f"Found {len(targets)} targets", args.verbose)

    # Handle --validate
    if args.validate:
        log_verbose(f"Validating target: {args.validate}", args.verbose)
        if validate_target(targets, args.validate):
            return EXIT_SUCCESS
        return EXIT_FILE_ERROR

    # Handle --json
    if args.json:
        output_targets_json(targets)
        return EXIT_SUCCESS

    # Handle --list (detailed)
    if args.list:
        output_targets_detailed(targets)
        return EXIT_SUCCESS

    # Handle --format-names
    if args.format_names:
        output_format_names(targets)
        return EXIT_SUCCESS

    # Default: target names only
    output_target_names(targets)
    return EXIT_SUCCESS


if __name__ == '__main__':
    sys.exit(main())
