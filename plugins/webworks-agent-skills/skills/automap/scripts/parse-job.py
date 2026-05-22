#!/usr/bin/env python3
"""
parse-job.py

Parse AutoMap job files (.waj) to extract configuration information.

Usage:
    python parse-job.py [OPTIONS] <job-file>

Features:
    - Extract job name and version
    - Extract Stationery reference path
    - List all document groups and documents
    - List all targets with configuration
    - JSON output option for programmatic use
    - Export config for use with create-job.py

Exit Codes:
    0 - Success
    1 - Job file not found or invalid
    2 - Invalid arguments
    3 - Parse error
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
EXIT_PARSE_ERROR = 3

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


def validate_job_file(job_file: str) -> bool:
    """Validate that the job file exists and has a valid extension."""
    path = Path(job_file)

    if not path.exists():
        log_error(f"Job file not found: {job_file}")
        return False

    if path.suffix.lower() != '.waj':
        log_error(f"Invalid job file extension: {job_file}")
        log_error("Expected: .waj")
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


def extract_job_info(root: Element, job_path: str) -> dict:
    """Extract all job information from the XML."""
    job_dir = Path(job_path).parent

    # Basic job info
    job_info = {
        'name': root.get('name', 'Unknown'),
        'version': root.get('version', '1.0'),
        'stationery': '',
        'stationeryResolved': '',
        'stationeryExists': False,
        'groups': [],
        'targets': []
    }

    # Extract Stationery reference
    project_elem = root.find('Project')
    if project_elem is not None:
        stationery_path = project_elem.get('path', '')
        job_info['stationery'] = stationery_path

        # Try to resolve the path
        if stationery_path:
            resolved = job_dir / stationery_path
            job_info['stationeryResolved'] = str(resolved)
            job_info['stationeryExists'] = resolved.exists()

    # Extract document groups
    files_elem = root.find('Files')
    if files_elem is not None:
        for group_elem in files_elem.findall('Group'):
            group = {
                'name': group_elem.get('name', ''),
                'documents': []
            }
            for doc_elem in group_elem.findall('Document'):
                group['documents'].append(doc_elem.get('path', ''))
            job_info['groups'].append(group)

    # Extract targets
    targets_elem = root.find('Targets')
    if targets_elem is not None:
        for target_elem in targets_elem.findall('Target'):
            target = {
                'name': target_elem.get('name', ''),
                'format': target_elem.get('format', ''),
                'formatType': target_elem.get('formatType', 'Application'),
                'build': target_elem.get('build', 'True') == 'True',
                'cleanOutput': target_elem.get('cleanOutput', 'False') == 'True',
                'deployTarget': target_elem.get('deployTarget', ''),
                'conditions': [],
                'variables': [],
                'settings': []
            }

            # Extract conditions
            conditions_elem = target_elem.find('Conditions')
            if conditions_elem is not None:
                for cond_elem in conditions_elem.findall('Condition'):
                    target['conditions'].append({
                        'name': cond_elem.get('name', ''),
                        'value': cond_elem.get('value', '')
                    })

            # Extract variables
            variables_elem = target_elem.find('Variables')
            if variables_elem is not None:
                for var_elem in variables_elem.findall('Variable'):
                    target['variables'].append({
                        'name': var_elem.get('name', ''),
                        'value': var_elem.get('value', '')
                    })

            # Extract settings
            settings_elem = target_elem.find('Settings')
            if settings_elem is not None:
                for setting_elem in settings_elem.findall('Setting'):
                    target['settings'].append({
                        'name': setting_elem.get('name', ''),
                        'value': setting_elem.get('value', '')
                    })

            job_info['targets'].append(target)

    return job_info


def output_human_readable(job_info: dict) -> None:
    """Output job information in human-readable format."""
    print(f"\n{GREEN}Job:{NC} {job_info['name']} (version {job_info['version']})")

    # Stationery info
    stationery_status = f"{GREEN}exists{NC}" if job_info['stationeryExists'] else f"{YELLOW}not found{NC}"
    print(f"{BLUE}Stationery:{NC} {job_info['stationery']} [{stationery_status}]")

    # Groups and documents
    total_docs = sum(len(g['documents']) for g in job_info['groups'])
    print(f"\n{CYAN}Source Documents ({len(job_info['groups'])} groups, {total_docs} documents):{NC}")

    for group in job_info['groups']:
        print(f"\n  {group['name']}/")
        for doc in group['documents']:
            print(f"    - {doc}")

    # Targets
    print(f"\n{CYAN}Targets ({len(job_info['targets'])}):{NC}")

    for target in job_info['targets']:
        status = f"{GREEN}[BUILD]{NC}" if target['build'] else f"{YELLOW}[SKIP]{NC}"
        print(f"\n  {status} {target['name']}")
        print(f"         Format: {target['format']}")
        print(f"         Type: {target['formatType']}")

        if target['deployTarget']:
            print(f"         Deploy: {target['deployTarget']}")

        if target['cleanOutput']:
            print(f"         Clean: Yes")

        if target['conditions']:
            conds = ', '.join(f"{c['name']}={c['value']}" for c in target['conditions'])
            print(f"         Conditions: {conds}")

        if target['variables']:
            vars_str = ', '.join(f"{v['name']}={v['value']}" for v in target['variables'])
            print(f"         Variables: {vars_str}")

        if target['settings']:
            sets = ', '.join(f"{s['name']}=\"{s['value']}\"" for s in target['settings'])
            print(f"         Settings: {sets}")

    print()


def output_json(job_info: dict) -> None:
    """Output job information in JSON format."""
    print(json.dumps(job_info, indent=2))


def output_config(job_info: dict) -> None:
    """Output in create-job.py compatible config format."""
    config = {
        'name': job_info['name'],
        'stationery': job_info['stationery'],
        'groups': job_info['groups'],
        'targets': job_info['targets']
    }
    print(json.dumps(config, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Parse AutoMap job files (.waj) to extract configuration.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exit Codes:
    0    Success
    1    Job file not found or invalid
    2    Invalid arguments
    3    Parse error

Examples:
    # Show job configuration
    %(prog)s job.waj

    # JSON output
    %(prog)s --json job.waj

    # Export config for create-job.py
    %(prog)s --config job.waj > job-config.json

    # Verbose mode
    %(prog)s -v job.waj
"""
    )

    parser.add_argument('job_file', metavar='job-file',
                        help='Path to .waj job file')
    parser.add_argument('-j', '--json', action='store_true',
                        help='Output in JSON format (includes metadata)')
    parser.add_argument('-c', '--config', action='store_true',
                        help='Output in create-job.py compatible config format')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output')

    args = parser.parse_args()

    # Validate job file
    if not validate_job_file(args.job_file):
        return EXIT_FILE_ERROR

    log_verbose(f"Parsing job file: {args.job_file}", args.verbose)

    # Parse XML
    root = parse_job_xml(args.job_file)
    if root is None:
        return EXIT_PARSE_ERROR

    # Extract job info
    job_info = extract_job_info(root, args.job_file)

    log_verbose(f"Job name: {job_info['name']}", args.verbose)
    log_verbose(f"Found {len(job_info['groups'])} groups", args.verbose)
    log_verbose(f"Found {len(job_info['targets'])} targets", args.verbose)

    # Output results
    if args.config:
        output_config(job_info)
    elif args.json:
        output_json(job_info)
    else:
        output_human_readable(job_info)

    return EXIT_SUCCESS


if __name__ == '__main__':
    sys.exit(main())
