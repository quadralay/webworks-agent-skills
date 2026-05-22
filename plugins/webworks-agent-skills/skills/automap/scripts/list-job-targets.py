#!/usr/bin/env python3
"""
list-job-targets.py

List targets from AutoMap job files (.waj) with build status and configuration.

Usage:
    python list-job-targets.py [OPTIONS] <job-file>

Features:
    - List all targets with build status
    - Filter by enabled/disabled status
    - Show detailed configuration
    - JSON output option

Exit Codes:
    0 - Success
    1 - Job file not found or invalid
    2 - Invalid arguments
    3 - No targets found
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
EXIT_NO_TARGETS = 3

# ANSI color codes
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
NC = '\033[0m'  # No Color


def log_error(message: str) -> None:
    """Print error message to stderr."""
    print(f"[ERROR] {message}", file=sys.stderr)


def validate_job_file(job_file: str) -> bool:
    """Validate that the job file exists and has a valid extension."""
    path = Path(job_file)

    if not path.exists():
        log_error(f"Job file not found: {job_file}")
        return False

    if path.suffix.lower() != '.waj':
        log_error(f"Invalid job file extension: {job_file}")
        return False

    return True


def parse_job_xml(job_file: str) -> Optional[Element]:
    """Parse the job XML file and return the root element."""
    try:
        tree = ET.parse(job_file)
        return tree.getroot()
    except ET.ParseError as e:
        log_error(f"Failed to parse XML: {e}")
        return None
    except Exception as e:
        log_error(f"Failed to read file: {e}")
        return None


def extract_targets(root: Element) -> list[dict]:
    """Extract target information from the job file."""
    targets = []

    targets_elem = root.find('Targets')
    if targets_elem is None:
        return targets

    for target_elem in targets_elem.findall('Target'):
        target = {
            'name': target_elem.get('name', ''),
            'format': target_elem.get('format', ''),
            'formatType': target_elem.get('formatType', 'Application'),
            'build': target_elem.get('build', 'True') == 'True',
            'cleanOutput': target_elem.get('cleanOutput', 'False') == 'True',
            'deployTarget': target_elem.get('deployTarget', ''),
            'conditionsCount': 0,
            'variablesCount': 0,
            'settingsCount': 0,
            'conditions': [],
            'variables': [],
            'settings': []
        }

        # Count and extract conditions
        conditions_elem = target_elem.find('Conditions')
        if conditions_elem is not None:
            conds = conditions_elem.findall('Condition')
            target['conditionsCount'] = len(conds)
            for cond in conds:
                target['conditions'].append({
                    'name': cond.get('name', ''),
                    'value': cond.get('value', '')
                })

        # Count and extract variables
        variables_elem = target_elem.find('Variables')
        if variables_elem is not None:
            vars_list = variables_elem.findall('Variable')
            target['variablesCount'] = len(vars_list)
            for var in vars_list:
                target['variables'].append({
                    'name': var.get('name', ''),
                    'value': var.get('value', '')
                })

        # Count and extract settings
        settings_elem = target_elem.find('Settings')
        if settings_elem is not None:
            sets = settings_elem.findall('Setting')
            target['settingsCount'] = len(sets)
            for setting in sets:
                target['settings'].append({
                    'name': setting.get('name', ''),
                    'value': setting.get('value', '')
                })

        targets.append(target)

    return targets


def output_simple(targets: list[dict]) -> None:
    """Output just target names with build status."""
    for target in targets:
        status = "[BUILD]" if target['build'] else "[SKIP]"
        print(f"{status} {target['name']}")


def output_table(job_name: str, stationery: str, targets: list[dict]) -> None:
    """Output targets in a table format."""
    print(f"\n{CYAN}Job:{NC} {job_name}")
    print(f"{BLUE}Stationery:{NC} {stationery}")

    enabled = sum(1 for t in targets if t['build'])
    print(f"\n{CYAN}Targets ({len(targets)} total, {enabled} enabled):{NC}\n")

    for target in targets:
        if target['build']:
            status = f"{GREEN}[BUILD]{NC}"
        else:
            status = f"{YELLOW}[SKIP]{NC}"

        print(f"  {status} {target['name']}")
        print(f"          Format: {target['format']}")

        if target['deployTarget']:
            print(f"          Deploy: {target['deployTarget']}")

        if target['cleanOutput']:
            print(f"          Clean: Yes")

        overrides = []
        if target['conditionsCount'] > 0:
            overrides.append(f"Conditions: {target['conditionsCount']}")
        if target['variablesCount'] > 0:
            overrides.append(f"Variables: {target['variablesCount']}")
        if target['settingsCount'] > 0:
            overrides.append(f"Settings: {target['settingsCount']}")

        if overrides:
            print(f"          {', '.join(overrides)}")

        print()


def output_detailed(job_name: str, stationery: str, targets: list[dict]) -> None:
    """Output targets with full configuration details."""
    print(f"\n{CYAN}Job:{NC} {job_name}")
    print(f"{BLUE}Stationery:{NC} {stationery}")

    enabled = sum(1 for t in targets if t['build'])
    print(f"\n{CYAN}Targets ({len(targets)} total, {enabled} enabled):{NC}\n")

    for target in targets:
        if target['build']:
            status = f"{GREEN}[BUILD]{NC}"
        else:
            status = f"{YELLOW}[SKIP]{NC}"

        print(f"  {status} {target['name']}")
        print(f"          Format: {target['format']}")
        print(f"          Type: {target['formatType']}")

        if target['deployTarget']:
            print(f"          Deploy: {target['deployTarget']}")

        print(f"          Clean: {'Yes' if target['cleanOutput'] else 'No'}")

        if target['conditions']:
            print(f"          Conditions:")
            for cond in target['conditions']:
                print(f"            - {cond['name']} = {cond['value']}")

        if target['variables']:
            print(f"          Variables:")
            for var in target['variables']:
                print(f"            - {var['name']} = {var['value']}")

        if target['settings']:
            print(f"          Settings:")
            for setting in target['settings']:
                print(f"            - {setting['name']} = \"{setting['value']}\"")

        print()


def output_json(targets: list[dict]) -> None:
    """Output targets in JSON format."""
    print(json.dumps(targets, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(
        description='List targets from AutoMap job files (.waj).',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exit Codes:
    0    Success
    1    Job file not found or invalid
    2    Invalid arguments
    3    No targets found

Examples:
    # List all targets
    %(prog)s job.waj

    # Show only enabled targets
    %(prog)s --enabled job.waj

    # Show only disabled targets
    %(prog)s --disabled job.waj

    # Show detailed configuration
    %(prog)s --detailed job.waj

    # JSON output
    %(prog)s --json job.waj

    # Simple output (names only)
    %(prog)s --simple job.waj
"""
    )

    parser.add_argument('job_file', metavar='job-file',
                        help='Path to .waj job file')
    parser.add_argument('-e', '--enabled', action='store_true',
                        help='Show only enabled targets (build="True")')
    parser.add_argument('-d', '--disabled', action='store_true',
                        help='Show only disabled targets (build="False")')
    parser.add_argument('--detailed', action='store_true',
                        help='Show detailed configuration for each target')
    parser.add_argument('-s', '--simple', action='store_true',
                        help='Simple output (target names with status only)')
    parser.add_argument('-j', '--json', action='store_true',
                        help='Output in JSON format')

    args = parser.parse_args()

    # Validate job file
    if not validate_job_file(args.job_file):
        return EXIT_FILE_ERROR

    # Parse XML
    root = parse_job_xml(args.job_file)
    if root is None:
        return EXIT_FILE_ERROR

    # Get job info
    job_name = root.get('name', 'Unknown')
    project = root.find('Project')
    stationery = project.get('path', '') if project is not None else ''

    # Extract targets
    targets = extract_targets(root)

    if not targets:
        log_error("No targets found in job file")
        return EXIT_NO_TARGETS

    # Filter if requested
    if args.enabled:
        targets = [t for t in targets if t['build']]
    elif args.disabled:
        targets = [t for t in targets if not t['build']]

    if not targets:
        print("No targets match the filter criteria")
        return EXIT_SUCCESS

    # Output results
    if args.json:
        output_json(targets)
    elif args.simple:
        output_simple(targets)
    elif args.detailed:
        output_detailed(job_name, stationery, targets)
    else:
        output_table(job_name, stationery, targets)

    return EXIT_SUCCESS


if __name__ == '__main__':
    sys.exit(main())
