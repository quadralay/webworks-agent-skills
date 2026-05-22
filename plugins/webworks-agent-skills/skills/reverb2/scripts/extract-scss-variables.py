#!/usr/bin/env python3
"""
extract-scss-variables.py

Extracts SCSS variable values from Reverb project files.
Searches through the file resolver hierarchy to find effective values.

Usage:
    python extract-scss-variables.py <project-dir> [category]

Arguments:
    project-dir - Path to ePublisher project directory
    category    - Optional: neo, colors, sizes, layout, toolbar, header, footer,
                  menu, page, search, link, all (default: neo)

Output:
    JSON object with variable names and values
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

# ANSI color codes
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
NC = '\033[0m'

DEBUG = os.environ.get('DEBUG', '0') == '1'


def debug_log(message: str) -> None:
    """Print debug message to stderr."""
    if DEBUG:
        print(f"{YELLOW}[DEBUG]{NC} {message}", file=sys.stderr)


def error_log(message: str) -> None:
    """Print error message to stderr."""
    print(f"{RED}[ERROR]{NC} {message}", file=sys.stderr)


def success_log(message: str) -> None:
    """Print success message to stderr."""
    print(f"{GREEN}[SUCCESS]{NC} {message}", file=sys.stderr)


def find_scss_file(project_dir: Path, filename: str, target_name: Optional[str] = None) -> Optional[Path]:
    """
    Find SCSS file in project directory using file resolver hierarchy.

    Search order (most specific first):
    1. Target-specific (if target specified)
    2. Format-level customization
    3. Stationery format-level
    4. Packaged defaults (.base)
    5. Stationery .base level
    """
    debug_log(f"Looking for {filename} in project: {project_dir}")

    # Search locations in priority order
    search_paths = []

    # 1. Target-specific (if target specified)
    if target_name:
        search_paths.append(
            project_dir / 'Targets' / target_name / 'Pages' / 'sass' / filename
        )

    # 2. Format-level customization
    search_paths.append(
        project_dir / 'Formats' / 'WebWorks Reverb 2.0' / 'Pages' / 'sass' / filename
    )

    # 3. Stationery format-level
    for stationery_dir in project_dir.glob('*stationery'):
        if stationery_dir.is_dir():
            search_paths.append(
                stationery_dir / 'Formats' / 'WebWorks Reverb 2.0' / 'Pages' / 'sass' / filename
            )

    # 4. Packaged defaults (.base)
    search_paths.append(
        project_dir / 'Formats' / 'WebWorks Reverb 2.0.base' / 'Pages' / 'sass' / filename
    )

    # 5. Stationery .base level
    for stationery_dir in project_dir.glob('*stationery'):
        if stationery_dir.is_dir():
            search_paths.append(
                stationery_dir / 'Formats' / 'WebWorks Reverb 2.0.base' / 'Pages' / 'sass' / filename
            )

    # Check each path
    for path in search_paths:
        if path.exists():
            debug_log(f"Found at: {path}")
            return path

    debug_log(f"File not found: {filename}")
    return None


def parse_scss_variables(content: str, pattern: str) -> dict:
    """
    Parse SCSS variables matching a pattern.

    Args:
        content: SCSS file content
        pattern: Regex pattern for variable names (e.g., r'^\\$neo_')

    Returns:
        Dictionary of variable names (without $) to values
    """
    variables = {}

    # Pattern to match SCSS variable declarations
    # $variable_name: value;  or  $variable_name: value !default;
    var_pattern = re.compile(
        r'^\s*(\$[a-z_][a-z0-9_]*):\s*(.+?)\s*(?:!default\s*)?;',
        re.MULTILINE | re.IGNORECASE
    )

    filter_pattern = re.compile(pattern) if pattern else None

    for match in var_pattern.finditer(content):
        var_name = match.group(1)  # includes $
        var_value = match.group(2).strip()

        # Apply filter if provided
        if filter_pattern and not filter_pattern.match(var_name):
            continue

        # Remove $ prefix for output
        clean_name = var_name.lstrip('$')
        variables[clean_name] = var_value

    return variables


def extract_neo_variables(content: str) -> dict:
    """Extract $neo_* variables."""
    return parse_scss_variables(content, r'^\$neo_')


def extract_layout_variables(content: str) -> dict:
    """Extract $_layout_color_* variables."""
    return parse_scss_variables(content, r'^\$_layout_color_')


def extract_component_variables(content: str, component: str) -> dict:
    """Extract variables for a specific component prefix."""
    return parse_scss_variables(content, rf'^\${component}_')


def extract_all_variables(content: str) -> dict:
    """Extract all SCSS variables."""
    return parse_scss_variables(content, r'^\$[a-z_]')


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Extract SCSS variable values from Reverb project files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Categories:
    neo      - $neo_* variables (default)
    layout   - $_layout_color_* variables
    colors   - All color variables
    sizes    - Variables from _sizes.scss
    toolbar  - $toolbar_* variables
    header   - $header_* variables
    footer   - $footer_* variables
    menu     - $menu_* variables
    page     - $page_* variables
    search   - $search_* variables
    link     - $link_* variables
    all      - All variables

Examples:
    # Extract neo color variables (default)
    %(prog)s /path/to/project

    # Extract all variables
    %(prog)s /path/to/project all

    # Extract toolbar-specific variables
    %(prog)s /path/to/project toolbar
"""
    )

    parser.add_argument('project_dir', metavar='project-dir',
                        help='Path to ePublisher project directory')
    parser.add_argument('category', nargs='?', default='neo',
                        choices=['neo', 'layout', 'colors', 'sizes', 'toolbar',
                                 'header', 'footer', 'menu', 'page', 'search', 'link', 'all'],
                        help='Variable category to extract (default: neo)')

    args = parser.parse_args()

    project_dir = Path(args.project_dir)
    category = args.category

    if not project_dir.is_dir():
        error_log(f"Project directory not found: {project_dir}")
        return 1

    # Determine which file to read based on category
    if category == 'sizes':
        filename = '_sizes.scss'
    else:
        filename = '_colors.scss'

    scss_file = find_scss_file(project_dir, filename)

    if scss_file is None:
        error_log(f"{filename} not found in project")
        return 1

    success_log(f"Reading from: {scss_file}")

    # Read file content
    try:
        content = scss_file.read_text(encoding='utf-8')
    except Exception as e:
        error_log(f"Failed to read file: {e}")
        return 1

    # Extract variables based on category
    if category == 'neo':
        variables = extract_neo_variables(content)
    elif category == 'layout':
        variables = extract_layout_variables(content)
    elif category in ('colors', 'all', 'sizes'):
        variables = extract_all_variables(content)
    else:
        # Component-specific: toolbar, header, footer, menu, page, search, link
        variables = extract_component_variables(content, category)

    # Output as JSON
    print(json.dumps(variables, indent=2))

    return 0


if __name__ == '__main__':
    sys.exit(main())
