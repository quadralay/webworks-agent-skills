#!/usr/bin/env python3
"""
parse-job.py

Parse AutoMap job files (.waj) and composition job files (.wacj) to extract
configuration information.

Usage:
    python parse-job.py [OPTIONS] <job-file>

Features:
    - Extract job name and version
    - Extract Stationery reference path
    - List all document groups and documents
    - List all targets with configuration
    - Composition jobs (.wacj): members, roles, output target selection,
      site-TOC spec (MergeSettings) and the shared destination
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
import os
import sys
# Use defusedxml to prevent XXE attacks (CWE-611)
import defusedxml.ElementTree as ET
from xml.etree.ElementTree import Element  # For type hints only
from pathlib import Path
from typing import Optional

# The .wacj grammar lives beside this script in lib/wacj.py so every AutoMap
# tool shares one definition of the composition element vocabulary.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.wacj import (  # noqa: E402
    COMPOSITION_EXTENSION, COMPOSITION_ROOT, JOB_EXTENSION, JOB_ROOT,
    MODE_DISCOVERY, MODE_HYBRID, TARGET_SOURCE_AUTO,
    extract_composition_info, is_composition_path, iter_spec,
)

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

    if path.suffix.lower() not in (JOB_EXTENSION, COMPOSITION_EXTENSION):
        log_error(f"Invalid job file extension: {job_file}")
        log_error(f"Expected: {JOB_EXTENSION} or {COMPOSITION_EXTENSION}")
        return False

    return True


def check_root_matches_extension(root: Element, job_file: str) -> bool:
    """Confirm the root element matches the file extension.

    AutoMap dispatches on the root element (<Job> vs <CompositionJob>), so a
    mismatch is worth naming rather than parsing the wrong grammar.
    """
    composition_path = is_composition_path(job_file)

    if composition_path and root.tag != COMPOSITION_ROOT:
        log_error(f"Expected <{COMPOSITION_ROOT}> in a {COMPOSITION_EXTENSION} "
                  f"file, found <{root.tag}>")
        return False

    if not composition_path and root.tag != JOB_ROOT:
        if root.tag == COMPOSITION_ROOT:
            log_error(f"This is a composition job (<{COMPOSITION_ROOT}>) in a "
                      f"{JOB_EXTENSION} file; rename it to {COMPOSITION_EXTENSION}")
        else:
            log_error(f"Expected <{JOB_ROOT}> in a {JOB_EXTENSION} file, "
                      f"found <{root.tag}>")
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
        # Discriminates a publishing job from a composition job (.wacj) for
        # consumers that accept either shape.
        'kind': 'job',
        'name': root.get('name', 'Unknown'),
        'version': root.get('version', '1.0'),
        'stationery': '',
        'stationeryResolved': '',
        'stationeryExists': False,
        'useAsStationery': False,
        'groups': [],
        'targets': []
    }

    # Extract the job origin reference (Stationery .wxsp, or .wep/.wrp project)
    project_elem = root.find('Project')
    if project_elem is not None:
        stationery_path = project_elem.get('path', '')
        job_info['stationery'] = stationery_path
        # useAsStationery="True" opts a .wep/.wrp origin into project-as-stationery mode
        job_info['useAsStationery'] = project_elem.get('useAsStationery', 'False') == 'True'

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
                'destination': target_elem.get('destination') or target_elem.get('deployTarget', ''),
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

    # Origin info (Stationery .wxsp, or .wep/.wrp project)
    origin_status = f"{GREEN}exists{NC}" if job_info['stationeryExists'] else f"{YELLOW}not found{NC}"
    if job_info['useAsStationery']:
        origin_label = "Origin (project as stationery)"
    else:
        origin_label = "Stationery"
    print(f"{BLUE}{origin_label}:{NC} {job_info['stationery']} [{origin_status}]")

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

        if target['destination']:
            print(f"         Deploy: {target['destination']}")

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


def output_composition_human(info: dict) -> None:
    """Output composition job (.wacj) information in human-readable format."""
    version = info['version'] or '1.0'
    print(f"\n{GREEN}Composition Job:{NC} {info['name'] or '(unnamed)'} (version {version})")

    mode_note = {
        MODE_DISCOVERY: 'parcel set discovered from the mirror',
        MODE_HYBRID: 'declared spec plus discovered extras',
    }.get(info['mode'], 'parcel set is exactly the declared spec')
    print(f"{BLUE}Mode:{NC} {info['mode']} ({mode_note})")

    output_target = info['outputTarget'] or '(auto-detect per member)'
    print(f"{BLUE}Output target:{NC} {output_target}")

    # Members
    members = info['members']
    built = sum(1 for m in members if m['build'])
    print(f"\n{CYAN}Members ({len(members)} total, {built} built by this composition):{NC}")

    for member in members:
        status = f"{GREEN}[BUILD]{NC}" if member['build'] else f"{YELLOW}[READ]{NC}"
        exists = f"{GREEN}exists{NC}" if member['exists'] else f"{YELLOW}not found{NC}"
        print(f"\n  {status} {member['path'] or '(no path)'} [{exists}]")
        print(f"         Role: {member['role']}"
              + ("" if member['roleRecognized']
                 else f" (declared \"{member['roleDeclared']}\", unrecognized)"))
        if member['targetSource'] == TARGET_SOURCE_AUTO:
            print(f"         Target: (auto-detect)")
        else:
            print(f"         Target: {member['effectiveTarget']} ({member['targetSource']})")

    # Site TOC spec
    merge = info['mergeSettings']
    print(f"\n{CYAN}Site TOC (MergeSettings):{NC}")
    if not merge['present']:
        print("  (none - discovery mode)")
    else:
        if merge['title']:
            print(f"  Title: {merge['title']} (accepted for grammar parity; not used by composition)")
        if merge['discover']:
            print("  Discover: True (declared spec plus discovered extras)")
        if not merge['spec']:
            print("  (empty spec)")
        for depth, node in iter_spec(merge['spec']):
            indent = '  ' + ('  ' * (depth + 1))
            if node['kind'] == 'container':
                print(f"{indent}{node['name'] or '(unnamed)'}/")
            else:
                title = f" ({node['title']})" if node['title'] else ''
                print(f"{indent}- {node['name'] or '(unnamed)'}{title}")

    # Destination
    destination = info['destination']
    print(f"\n{CYAN}Destination:{NC}")
    if not destination['declared']:
        print(f"  {YELLOW}(none declared){NC}")
    else:
        legacy = ' (legacy <DeployTarget> spelling)' if destination['legacySpelling'] else ''
        print(f"  {destination['name'] or '(unnamed)'}{legacy}")
        for setting in destination['deploySettings']:
            action = setting['action'] or '(no action)'
            print(f"    Inline definition: {setting['name'] or '(unnamed)'} [{action}]")
            for key, value in setting['configuration'].items():
                print(f"      {key}: {value}")

    print()


def output_json(job_info: dict) -> None:
    """Output job information in JSON format."""
    print(json.dumps(job_info, indent=2))


def output_config(job_info: dict) -> None:
    """Output in create-job.py compatible config format."""
    config = {
        'name': job_info['name'],
        'stationery': job_info['stationery'],
        'useAsStationery': job_info['useAsStationery'],
        'groups': job_info['groups'],
        'targets': job_info['targets']
    }
    print(json.dumps(config, indent=2))


def output_composition_config(info: dict) -> None:
    """Output a composition in create-job.py compatible config format."""
    config = {
        'kind': 'composition',
        'name': info['name'],
        'outputTarget': info['outputTarget'],
        'members': [
            {
                'path': member['path'],
                'role': member['role'],
                'build': member['build'],
                'target': member['target'],
            }
            for member in info['members']
        ],
        'destination': {
            'name': info['destination']['name'],
            'deploySettings': info['destination']['deploySettings'],
        },
    }

    # MergeSettings is omitted entirely in discovery mode - its absence is the
    # mode, so a round-trip must not invent an empty element.
    if info['mergeSettings']['present']:
        config['mergeSettings'] = {
            'title': info['mergeSettings']['title'],
            'discover': info['mergeSettings']['discover'],
            'spec': info['mergeSettings']['spec'],
        }

    print(json.dumps(config, indent=2))


def ensure_utf8() -> None:
    """Make this tool Unicode-safe regardless of the caller's environment.

    UTF-8 mode is read at interpreter startup, so the setdefault only
    affects Python children spawned later; the reconfigure handles this
    process's own stdio on locale-codepage consoles (Windows cp1252).
    See CONTRIBUTING.md "New Python Tools".
    """
    os.environ.setdefault('PYTHONUTF8', '1')
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass


def main() -> int:
    ensure_utf8()
    parser = argparse.ArgumentParser(
        description='Parse AutoMap job (.waj) and composition job (.wacj) files.',
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

    # Show composition members, site TOC spec and destination
    %(prog)s composition.wacj

    # JSON output
    %(prog)s --json job.waj

    # Export config for create-job.py
    %(prog)s --config job.waj > job-config.json

    # Verbose mode
    %(prog)s -v job.waj
"""
    )

    parser.add_argument('job_file', metavar='job-file',
                        help='Path to .waj job file or .wacj composition job file')
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

    if not check_root_matches_extension(root, args.job_file):
        return EXIT_PARSE_ERROR

    # Composition job (.wacj): a distinct artifact that references .waj/.wep
    # members, so it carries a different grammar than a publishing job.
    if is_composition_path(args.job_file):
        composition = extract_composition_info(root, args.job_file)

        log_verbose(f"Composition name: {composition['name']}", args.verbose)
        log_verbose(f"Found {len(composition['members'])} members", args.verbose)
        log_verbose(f"Composition mode: {composition['mode']}", args.verbose)

        if args.config:
            output_composition_config(composition)
        elif args.json:
            output_json(composition)
        else:
            output_composition_human(composition)

        return EXIT_SUCCESS

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
