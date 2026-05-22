#!/usr/bin/env python3
"""
generate-report.py

Generates a comprehensive human-readable report from Reverb analysis results.
Combines project info, CSH data, and browser test results into formatted output.

Usage:
    python generate-report.py <project-file> <project-info-json> <csh-data-json> <test-results-json>

Arguments:
    project-file       - Path to .wep project file
    project-info-json  - JSON with project/target information
    csh-data-json      - JSON array of CSH links
    test-results-json  - JSON with browser test results
"""

import argparse
import io
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Ensure stdout uses UTF-8 encoding for box-drawing characters on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ANSI color codes
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
BOLD = '\033[1m'
NC = '\033[0m'


def safe_get(data: dict, *keys: str, default: Any = None) -> Any:
    """Safely get nested dictionary values."""
    result = data
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key, default)
        else:
            return default
    return result if result is not None else default


def print_header(project_file: str, target_name: str) -> None:
    """Print the report header."""
    print()
    print(f"{BOLD}\u2554{'═' * 70}\u2557{NC}")
    print(f"{BOLD}\u2551          Reverb Output Analysis Report{' ' * 30}\u2551{NC}")
    print(f"{BOLD}\u255a{'═' * 70}\u255d{NC}")
    print()
    print(f"{BLUE}Project:{NC} {Path(project_file).name}")
    print(f"{BLUE}Target:{NC} {target_name}")
    print(f"{BLUE}Generated:{NC} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()


def print_browser_test_results(test_results: dict) -> None:
    """Print browser test results section."""
    print()
    print(f"{BOLD}{'═' * 75}{NC}")
    print(f"{BOLD} Browser Test Results{NC}")
    print(f"{BOLD}{'═' * 75}{NC}")
    print()

    reverb_loaded = safe_get(test_results, 'reverbLoaded', default=False)
    load_time = safe_get(test_results, 'loadTime', default=0)
    error_count = safe_get(test_results, 'errorCount', default=0)
    warning_count = safe_get(test_results, 'warningCount', default=0)

    if reverb_loaded:
        print(f"{GREEN}\u2705 Reverb Runtime{NC}")
        print(f"   \u2022 Loaded successfully")
        print(f"   \u2022 Load time: {load_time}ms")
    else:
        print(f"{RED}\u274c Reverb Runtime{NC}")
        print(f"   \u2022 Failed to load")

    print()

    if error_count == 0:
        print(f"{GREEN}\u2705 JavaScript Errors{NC}")
        print(f"   \u2022 No errors detected")
    else:
        print(f"{RED}\u274c JavaScript Errors{NC}")
        print(f"   \u2022 {error_count} errors found")
        print()
        # Extract and display errors
        errors = safe_get(test_results, 'errors', default=[])
        for error in errors[:10]:  # Show first 10 errors
            message = safe_get(error, 'message', default='Unknown error')
            print(f"   {RED}\u2022{NC} {message}")

    print()

    if warning_count == 0:
        print(f"{GREEN}\u2705 Console Warnings{NC}")
        print(f"   \u2022 No warnings detected")
    else:
        print(f"{YELLOW}\u26a0 Console Warnings{NC}")
        print(f"   \u2022 {warning_count} warnings found")


def print_csh_results(csh_data: list) -> None:
    """Print CSH results section."""
    print()
    print(f"{BOLD}{'═' * 75}{NC}")
    print(f"{BOLD} Context Sensitive Help (CSH){NC}")
    print(f"{BOLD}{'═' * 75}{NC}")
    print()

    if not csh_data:
        print(f"{BLUE}\u2139 No CSH Links Configured{NC}")
        print(f"   \u2022 url_maps.xml has empty TopicMap")
        return

    csh_count = len(csh_data)
    print(f"{GREEN}\u2705 CSH Links: {csh_count} configured{NC}")
    print()

    # Display CSH table
    print(f"{BOLD}{'ID':<8} {'URL':<40} Title{NC}")
    print('\u2500' * 75)

    for entry in csh_data:
        topic_id = entry.get('id', entry.get('topic_id', ''))
        url = entry.get('url', '')
        title = entry.get('title', '')
        print(f"{topic_id:<8} {url:<40} {title}")


def print_component_analysis(test_results: dict) -> None:
    """Print component analysis section."""
    print()
    print(f"{BOLD}{'═' * 75}{NC}")
    print(f"{BOLD} Component Analysis{NC}")
    print(f"{BOLD}{'═' * 75}{NC}")
    print()

    components = safe_get(test_results, 'components', default={})

    # Toolbar
    toolbar = safe_get(components, 'toolbar', default={})
    toolbar_present = safe_get(toolbar, 'present', default=False)

    if toolbar_present:
        print(f"{GREEN}\u2705 Toolbar{NC} (#toolbar_div)")
        toolbar_logo = safe_get(toolbar, 'logo', default='none')
        if toolbar_logo and toolbar_logo not in ('none', 'null', None):
            print(f"   \u2022 Logo: {toolbar_logo}")
        else:
            print(f"   \u2022 Logo: none")

        toolbar_search = safe_get(toolbar, 'searchPresent', default=False)
        if toolbar_search:
            print(f"   \u2022 Search: enabled")
        else:
            print(f"   \u2022 Search: disabled")
    else:
        print(f"{BLUE}\u25cb Toolbar{NC} (not configured)")

    # Header
    header = safe_get(components, 'header', default={})
    header_present = safe_get(header, 'present', default=False)

    if header_present:
        print(f"{GREEN}\u2705 Header{NC} (#header_div)")
        header_logo = safe_get(header, 'logo', default='none')
        if header_logo and header_logo not in ('none', 'null', None):
            print(f"   \u2022 Logo: {header_logo}")
        else:
            print(f"   \u2022 Logo: none")
    else:
        print(f"{BLUE}\u25cb Header{NC} (not configured)")

    # Footer
    footer = safe_get(components, 'footer', default={})
    footer_present = safe_get(footer, 'present', default=False)

    if footer_present:
        footer_type = safe_get(footer, 'type', default='unknown')
        print(f"{GREEN}\u2705 Footer{NC} (#footer_div, type: {footer_type})")
        footer_logo = safe_get(footer, 'logo', default='none')
        if footer_logo and footer_logo not in ('none', 'null', None):
            print(f"   \u2022 Logo: {footer_logo}")
        else:
            print(f"   \u2022 Logo: none")
    else:
        print(f"{BLUE}\u25cb Footer{NC} (not configured)")

    # TOC Menu
    toc = safe_get(components, 'toc', default={})
    toc_present = safe_get(toc, 'present', default=False)

    if toc_present:
        print(f"{GREEN}\u2705 TOC Menu{NC} (#toc)")
        toc_expanded = safe_get(toc, 'expanded', default=False)
        if toc_expanded:
            print(f"   \u2022 Initial state: expanded")
        else:
            print(f"   \u2022 Initial state: collapsed")
        toc_items = safe_get(toc, 'itemCount', default=0)
        print(f"   \u2022 Items: {toc_items}")
    else:
        print(f"{BLUE}\u25cb TOC Menu{NC} (not configured)")

    # Content Area
    content = safe_get(components, 'content', default={})
    content_present = safe_get(content, 'present', default=False)

    if content_present:
        print(f"{GREEN}\u2705 Content Area{NC} (#page_div)")
        has_iframe = safe_get(content, 'hasIframe', default=False)
        if has_iframe:
            print(f"   \u2022 Content iframe: loaded")
    else:
        print(f"{RED}\u274c Content Area{NC} (MISSING - this is required)")


def print_summary(test_results: dict) -> None:
    """Print summary section."""
    print()
    print(f"{BOLD}{'═' * 75}{NC}")
    print(f"{BOLD} Summary{NC}")
    print(f"{BOLD}{'═' * 75}{NC}")
    print()

    error_count = safe_get(test_results, 'errorCount', default=0)
    warning_count = safe_get(test_results, 'warningCount', default=0)

    if error_count == 0:
        print(f"{GREEN}\u2705 Status: PASS{NC}")
    else:
        print(f"{RED}\u274c Status: FAIL{NC}")

    print(f"   \u2022 Errors: {error_count}")
    print(f"   \u2022 Warnings: {warning_count}")

    # Count active components
    components = safe_get(test_results, 'components', default={})
    components_active = 0

    for comp_name in ['toolbar', 'header', 'footer', 'toc', 'content']:
        comp = safe_get(components, comp_name, default={})
        if safe_get(comp, 'present', default=False):
            components_active += 1

    print(f"   \u2022 Active components: {components_active}")
    print()


def parse_json_arg(arg: str) -> Any:
    """Parse a JSON argument, handling both strings and file paths."""
    # First try to parse as JSON string
    try:
        return json.loads(arg)
    except json.JSONDecodeError:
        pass

    # Try to read as file
    if Path(arg).exists():
        try:
            with open(arg) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"{RED}[ERROR]{NC} Failed to read JSON file: {e}", file=sys.stderr)
            return None

    # Invalid JSON
    print(f"{RED}[ERROR]{NC} Invalid JSON: {arg[:100]}...", file=sys.stderr)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Generate human-readable report from Reverb analysis results.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Arguments can be either JSON strings or paths to JSON files.

Examples:
    # Using JSON strings
    %(prog)s project.wep '{"target_name":"Reverb"}' '[]' '{"reverbLoaded":true}'

    # Using JSON files
    %(prog)s project.wep project-info.json csh-data.json test-results.json
"""
    )

    parser.add_argument('project_file', metavar='project-file',
                        help='Path to .wep project file')
    parser.add_argument('project_info', metavar='project-info-json',
                        help='JSON with project/target information')
    parser.add_argument('csh_data', metavar='csh-data-json',
                        help='JSON array of CSH links')
    parser.add_argument('test_results', metavar='test-results-json',
                        help='JSON with browser test results')

    args = parser.parse_args()

    # Parse JSON arguments
    project_info = parse_json_arg(args.project_info)
    csh_data = parse_json_arg(args.csh_data)
    test_results = parse_json_arg(args.test_results)

    if project_info is None or csh_data is None or test_results is None:
        return 1

    # Extract target name from project info
    target_name = safe_get(project_info, 'target_name', default='Unknown')

    # Print report sections
    print_header(args.project_file, target_name)
    print_browser_test_results(test_results)
    print_csh_results(csh_data)
    print_component_analysis(test_results)
    print_summary(test_results)

    return 0


if __name__ == '__main__':
    sys.exit(main())
