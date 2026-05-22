#!/usr/bin/env python3
"""
parse-stationery.py

Parse ePublisher Stationery files (.wxsp) to extract available formats,
settings, and file mappings for job file creation.

Usage:
    python parse-stationery.py [OPTIONS] <stationery-file>

Features:
    - Extract available format/target names
    - Extract format settings with default values
    - Extract supported file type mappings
    - Show runtime version for compatibility
    - JSON output option for programmatic use

Exit Codes:
    0 - Success
    1 - Stationery file not found or invalid
    2 - Invalid arguments
    3 - No formats found in stationery
"""

import argparse
import json
import sys
# Use defusedxml to prevent XXE attacks (CWE-611)
import defusedxml.ElementTree as ET
from xml.etree.ElementTree import Element  # For type hints only
from pathlib import Path
from typing import Optional

# Exit codes
EXIT_SUCCESS = 0
EXIT_FILE_ERROR = 1
EXIT_ARG_ERROR = 2
EXIT_NO_FORMATS = 3

# ANSI color codes
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
NC = '\033[0m'  # No Color


def log_verbose(message: str, verbose: bool) -> None:
    """Print verbose message to stderr."""
    if verbose:
        print(f"[VERBOSE] {message}", file=sys.stderr)


def log_error(message: str) -> None:
    """Print error message to stderr."""
    print(f"[ERROR] {message}", file=sys.stderr)


def validate_stationery_file(stationery_file: str) -> bool:
    """Validate that the stationery file exists and has a valid extension."""
    path = Path(stationery_file)

    if not path.exists():
        log_error(f"Stationery file not found: {stationery_file}")
        return False

    if path.suffix.lower() != '.wxsp':
        log_error(f"Invalid stationery file extension: {stationery_file}")
        log_error("Expected: .wxsp")
        return False

    return True


def parse_stationery_xml(stationery_file: str) -> Optional[Element]:
    """Parse the stationery XML file and return the root element."""
    try:
        tree = ET.parse(stationery_file)
        return tree.getroot()
    except ET.ParseError as e:
        log_error(f"Failed to parse XML: {e}")
        return None
    except Exception as e:
        log_error(f"Failed to read file: {e}")
        return None


def extract_runtime_version(root: Element) -> str:
    """Extract the runtime version from the Project element."""
    runtime_version = root.get('RuntimeVersion', '')
    format_version = root.get('FormatVersion', '')

    if format_version == '{Current}' or not format_version:
        return runtime_version
    return format_version


def extract_formats(root: Element, verbose: bool = False) -> list[dict]:
    """Extract all format information from the stationery."""
    formats = []

    # Handle namespace - ePublisher uses this namespace
    ns = {'ep': 'urn:WebWorks-Publish-Project'}

    # Try with namespace first, then without
    format_elements = root.findall('.//ep:Format', ns)
    if not format_elements:
        format_elements = list(root.iter('Format'))

    log_verbose(f"Found {len(format_elements)} format elements", verbose)

    # Build a map of TargetID to FormatSettings
    settings_map = {}
    format_configs = root.findall('.//ep:FormatConfiguration', ns)
    if not format_configs:
        format_configs = list(root.iter('FormatConfiguration'))

    for config in format_configs:
        target_id = config.get('TargetID', '')
        settings = []

        # Find FormatSettings
        format_settings = config.find('ep:FormatSettings', ns)
        if format_settings is None:
            format_settings = config.find('FormatSettings')

        if format_settings is not None:
            setting_elements = format_settings.findall('ep:FormatSetting', ns)
            if not setting_elements:
                setting_elements = format_settings.findall('FormatSetting')

            for setting in setting_elements:
                settings.append({
                    'name': setting.get('Name', ''),
                    'defaultValue': setting.get('Value', '')
                })

        if target_id:
            settings_map[target_id] = settings

    # Extract format information
    for format_elem in format_elements:
        target_id = format_elem.get('TargetID', '')

        fmt = {
            'name': format_elem.get('Name', 'Unknown'),
            'targetName': format_elem.get('TargetName', 'Unknown'),
            'type': format_elem.get('Type', 'Unknown'),
            'targetId': target_id,
            'outputDirectory': '',
            'settings': settings_map.get(target_id, [])
        }

        # Look for OutputDirectory child element
        output_dir_elem = format_elem.find('ep:OutputDirectory', ns)
        if output_dir_elem is None:
            output_dir_elem = format_elem.find('OutputDirectory')
        if output_dir_elem is not None and output_dir_elem.text:
            fmt['outputDirectory'] = output_dir_elem.text
        else:
            fmt['outputDirectory'] = f"Output\\{fmt['targetName']}"

        formats.append(fmt)

    return formats


def extract_file_mappings(root: Element) -> list[dict]:
    """Extract file type mappings from the stationery."""
    mappings = []

    # Handle namespace
    ns = {'ep': 'urn:WebWorks-Publish-Project'}

    mapping_elements = root.findall('.//ep:FileMapping', ns)
    if not mapping_elements:
        mapping_elements = list(root.iter('FileMapping'))

    for mapping in mapping_elements:
        mappings.append({
            'extension': mapping.get('extension', ''),
            'adapter': mapping.get('adapter', '')
        })

    return mappings


def output_human_readable(stationery_path: str, runtime_version: str,
                          formats: list[dict], mappings: list[dict]) -> None:
    """Output stationery information in human-readable format."""
    print(f"\n{GREEN}Stationery:{NC} {Path(stationery_path).name}")
    print(f"{BLUE}Runtime Version:{NC} {runtime_version}")
    print()

    # Formats table
    print(f"{CYAN}Available Formats:{NC}")
    print("-" * 70)
    print(f"{'Format Name':<30} {'Type':<15} {'Target Name':<25}")
    print("-" * 70)

    for fmt in formats:
        print(f"{fmt['name']:<30} {fmt['type']:<15} {fmt['targetName']:<25}")

    print()

    # Settings per format
    for fmt in formats:
        if fmt['settings']:
            print(f"{YELLOW}Settings for {fmt['name']}:{NC}")
            for setting in fmt['settings']:
                print(f"  - {setting['name']} (default: \"{setting['defaultValue']}\")")
            print()

    # File mappings
    if mappings:
        print(f"{CYAN}Supported File Types:{NC}")
        extensions = [m['extension'] for m in mappings]
        print(f"  {', '.join(extensions)}")
        print()


def output_json(stationery_path: str, runtime_version: str,
                formats: list[dict], mappings: list[dict]) -> None:
    """Output stationery information in JSON format."""
    data = {
        'path': str(Path(stationery_path).resolve()),
        'runtimeVersion': runtime_version,
        'formats': formats,
        'fileMappings': mappings
    }
    print(json.dumps(data, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Parse ePublisher Stationery files (.wxsp) to extract formats, settings, and file mappings.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exit Codes:
    0    Success
    1    Stationery file not found or invalid
    2    Invalid arguments
    3    No formats found in stationery

Examples:
    # Show available formats and settings
    %(prog)s stationery.wxsp

    # JSON output for programmatic use
    %(prog)s --json stationery.wxsp

    # Verbose mode for debugging
    %(prog)s -v stationery.wxsp
"""
    )

    parser.add_argument('stationery_file', metavar='stationery-file',
                        help='Path to .wxsp stationery file')
    parser.add_argument('-j', '--json', action='store_true',
                        help='Output in JSON format')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output')

    args = parser.parse_args()

    # Validate stationery file
    if not validate_stationery_file(args.stationery_file):
        return EXIT_FILE_ERROR

    log_verbose(f"Parsing stationery file: {args.stationery_file}", args.verbose)

    # Parse XML
    root = parse_stationery_xml(args.stationery_file)
    if root is None:
        return EXIT_FILE_ERROR

    # Extract information
    runtime_version = extract_runtime_version(root)
    log_verbose(f"Runtime version: {runtime_version}", args.verbose)

    formats = extract_formats(root, args.verbose)
    if not formats:
        log_error("No formats found in stationery file")
        return EXIT_NO_FORMATS

    log_verbose(f"Found {len(formats)} formats", args.verbose)

    mappings = extract_file_mappings(root)
    log_verbose(f"Found {len(mappings)} file mappings", args.verbose)

    # Output results
    if args.json:
        output_json(args.stationery_file, runtime_version, formats, mappings)
    else:
        output_human_readable(args.stationery_file, runtime_version, formats, mappings)

    return EXIT_SUCCESS


if __name__ == '__main__':
    sys.exit(main())
