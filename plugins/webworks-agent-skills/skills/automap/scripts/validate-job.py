#!/usr/bin/env python3
"""
validate-job.py

Validate AutoMap job files (.waj) for correctness before building.

Usage:
    python validate-job.py [OPTIONS] <job-file>

Features:
    - XML well-formedness validation
    - Required elements check
    - Stationery reference validation
    - Target configuration validation
    - Optional document existence check
    - Optional format name validation against Stationery

Exit Codes:
    0 - All validations passed
    1 - File error (job file not found)
    2 - Invalid arguments
    3 - Validation failed
"""

import argparse
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
EXIT_VALIDATION_FAILED = 3

# ANSI color codes
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color


class ValidationResult:
    """Represents a validation check result."""

    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.message = ""
        self.warnings = []

    def pass_check(self, message: str = "") -> 'ValidationResult':
        self.passed = True
        self.message = message
        return self

    def fail_check(self, message: str) -> 'ValidationResult':
        self.passed = False
        self.message = message
        return self

    def add_warning(self, message: str) -> 'ValidationResult':
        self.warnings.append(message)
        return self


def log_error(message: str) -> None:
    """Print error message to stderr."""
    print(f"{RED}[ERROR]{NC} {message}", file=sys.stderr)


def print_result(result: ValidationResult) -> None:
    """Print a validation result."""
    if result.passed:
        status = f"{GREEN}[PASS]{NC}"
    else:
        status = f"{RED}[FAIL]{NC}"

    message = f" - {result.message}" if result.message else ""
    print(f"{status} {result.name}{message}")

    for warning in result.warnings:
        print(f"  {YELLOW}[WARN]{NC} {warning}")


def validate_file_exists(job_file: str) -> ValidationResult:
    """Check that the job file exists."""
    result = ValidationResult("Job file exists")
    path = Path(job_file)

    if not path.exists():
        return result.fail_check(f"File not found: {job_file}")

    if path.suffix.lower() != '.waj':
        return result.fail_check(f"Invalid extension: {path.suffix} (expected .waj)")

    return result.pass_check(path.name)


def validate_xml_wellformed(job_file: str) -> tuple[ValidationResult, Optional[Element]]:
    """Check that the XML is well-formed."""
    result = ValidationResult("XML well-formed")

    try:
        tree = ET.parse(job_file)
        root = tree.getroot()
        return result.pass_check(), root
    except ET.ParseError as e:
        return result.fail_check(str(e)), None
    except Exception as e:
        return result.fail_check(f"Failed to read: {e}"), None


def validate_root_element(root: Element) -> ValidationResult:
    """Check that the root element is Job with required attributes."""
    result = ValidationResult("Job element valid")

    if root.tag != 'Job':
        return result.fail_check(f"Expected <Job>, found <{root.tag}>")

    name = root.get('name')
    version = root.get('version')

    if not name:
        return result.fail_check("Missing 'name' attribute on Job element")

    if not version:
        result.add_warning("Missing 'version' attribute (defaulting to 1.0)")

    return result.pass_check(f"name=\"{name}\" version=\"{version or '1.0'}\"")


def validate_project_element(root: Element, job_dir: Path) -> ValidationResult:
    """Check that the Project element exists and references a valid Stationery."""
    result = ValidationResult("Stationery reference")

    project = root.find('Project')
    if project is None:
        return result.fail_check("Missing <Project> element")

    stationery_path = project.get('path')
    if not stationery_path:
        return result.fail_check("Missing 'path' attribute on Project element")

    # Try to resolve the path
    resolved = job_dir / stationery_path
    if resolved.exists():
        return result.pass_check(f"Found: {stationery_path}")
    else:
        return result.fail_check(f"Not found: {stationery_path}")


def validate_files_element(root: Element) -> ValidationResult:
    """Check that the Files element exists with at least one group."""
    result = ValidationResult("Source documents")

    files = root.find('Files')
    if files is None:
        result.add_warning("Missing <Files> element - no source documents defined")
        return result.pass_check("(empty)")

    groups = files.findall('Group')
    if not groups:
        result.add_warning("No <Group> elements found")
        return result.pass_check("(empty)")

    total_docs = 0
    for group in groups:
        group_name = group.get('name', '(unnamed)')
        if not group.get('name'):
            result.add_warning(f"Group missing 'name' attribute")

        docs = group.findall('Document')
        total_docs += len(docs)

        for doc in docs:
            if not doc.get('path'):
                result.add_warning(f"Document in '{group_name}' missing 'path' attribute")

    return result.pass_check(f"{len(groups)} groups, {total_docs} documents")


def validate_documents_exist(root: Element, job_dir: Path) -> ValidationResult:
    """Check that all referenced documents exist on disk."""
    result = ValidationResult("Document paths")

    files = root.find('Files')
    if files is None:
        return result.pass_check("(no documents)")

    missing = []
    found = 0

    for group in files.findall('Group'):
        for doc in group.findall('Document'):
            doc_path = doc.get('path', '')
            if doc_path:
                resolved = job_dir / doc_path
                if resolved.exists():
                    found += 1
                else:
                    missing.append(doc_path)

    if missing:
        for path in missing[:5]:  # Show first 5 missing
            result.add_warning(f"Not found: {path}")
        if len(missing) > 5:
            result.add_warning(f"... and {len(missing) - 5} more missing")

    if found > 0 and not missing:
        return result.pass_check(f"All {found} documents found")
    elif found > 0:
        return result.pass_check(f"{found} found, {len(missing)} missing")
    elif missing:
        return result.fail_check(f"All {len(missing)} documents missing")
    else:
        return result.pass_check("(no documents)")


def validate_targets_element(root: Element) -> ValidationResult:
    """Check that the Targets element exists with at least one target."""
    result = ValidationResult("Build targets")

    targets = root.find('Targets')
    if targets is None:
        return result.fail_check("Missing <Targets> element")

    target_list = targets.findall('Target')
    if not target_list:
        return result.fail_check("No <Target> elements found")

    enabled = sum(1 for t in target_list if t.get('build', 'True') == 'True')

    for target in target_list:
        if not target.get('name'):
            result.add_warning("Target missing 'name' attribute")
        if not target.get('format'):
            result.add_warning(f"Target '{target.get('name', '?')}' missing 'format' attribute")

    return result.pass_check(f"{len(target_list)} targets ({enabled} enabled)")


def validate_target_formats(root: Element, stationery_path: Path) -> ValidationResult:
    """Validate that target format names exist in the Stationery."""
    result = ValidationResult("Format names")

    if not stationery_path.exists():
        result.add_warning("Skipped - Stationery not found")
        return result.pass_check("(skipped)")

    # Parse stationery to get format names
    try:
        tree = ET.parse(str(stationery_path))
        stationery_root = tree.getroot()
    except Exception as e:
        result.add_warning(f"Failed to parse Stationery: {e}")
        return result.pass_check("(skipped)")

    # Get available format names
    ns = {'ep': 'urn:WebWorks-Publish-Project'}
    format_elements = stationery_root.findall('.//ep:Format', ns)
    if not format_elements:
        format_elements = list(stationery_root.iter('Format'))

    available_formats = set(f.get('Name', '') for f in format_elements)

    # Check job targets
    targets = root.find('Targets')
    if targets is None:
        return result.pass_check("(no targets)")

    invalid = []
    valid = 0

    for target in targets.findall('Target'):
        format_name = target.get('format', '')
        if format_name in available_formats:
            valid += 1
        else:
            invalid.append(format_name)

    if invalid:
        for name in invalid:
            result.add_warning(f"Format not in Stationery: {name}")
        result.add_warning(f"Available: {', '.join(available_formats)}")

    if valid > 0 and not invalid:
        return result.pass_check(f"All {valid} formats valid")
    elif valid > 0:
        return result.pass_check(f"{valid} valid, {len(invalid)} invalid")
    else:
        return result.fail_check("No valid formats")


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Validate AutoMap job files (.waj) for correctness.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exit Codes:
    0    All validations passed
    1    File error
    2    Invalid arguments
    3    Validation failed

Examples:
    # Basic validation
    %(prog)s job.waj

    # Check document existence
    %(prog)s --check-documents job.waj

    # Validate formats against Stationery
    %(prog)s --check-stationery job.waj

    # Full validation
    %(prog)s --check-documents --check-stationery job.waj
"""
    )

    parser.add_argument('job_file', metavar='job-file',
                        help='Path to .waj job file')
    parser.add_argument('-d', '--check-documents', action='store_true',
                        help='Check that referenced documents exist')
    parser.add_argument('-s', '--check-stationery', action='store_true',
                        help='Validate format names against Stationery')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Show all checks including passed ones')

    args = parser.parse_args()
    job_path = Path(args.job_file)
    job_dir = job_path.parent

    results = []
    all_passed = True

    # Check 1: File exists
    result = validate_file_exists(args.job_file)
    results.append(result)
    if not result.passed:
        print_result(result)
        return EXIT_FILE_ERROR

    # Check 2: XML well-formed
    result, root = validate_xml_wellformed(args.job_file)
    results.append(result)
    if not result.passed or root is None:
        for r in results:
            print_result(r)
        return EXIT_VALIDATION_FAILED

    # Check 3: Root element
    result = validate_root_element(root)
    results.append(result)
    if not result.passed:
        all_passed = False

    # Check 4: Project element
    result = validate_project_element(root, job_dir)
    results.append(result)
    if not result.passed:
        all_passed = False

    # Get stationery path for later checks
    project = root.find('Project')
    stationery_path = job_dir / project.get('path', '') if project is not None else Path()

    # Check 5: Files element
    result = validate_files_element(root)
    results.append(result)
    if not result.passed:
        all_passed = False

    # Check 6: Document existence (optional)
    if args.check_documents:
        result = validate_documents_exist(root, job_dir)
        results.append(result)
        if not result.passed:
            all_passed = False

    # Check 7: Targets element
    result = validate_targets_element(root)
    results.append(result)
    if not result.passed:
        all_passed = False

    # Check 8: Format validation (optional)
    if args.check_stationery:
        result = validate_target_formats(root, stationery_path)
        results.append(result)
        if not result.passed:
            all_passed = False

    # Print results
    print(f"\n{BLUE}Validation Results:{NC} {args.job_file}\n")

    for result in results:
        if args.verbose or not result.passed or result.warnings:
            print_result(result)

    # Summary
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    warnings = sum(len(r.warnings) for r in results)

    print()
    if all_passed:
        if warnings:
            print(f"{GREEN}Validation: PASSED{NC} ({passed}/{total} checks, {warnings} warnings)")
        else:
            print(f"{GREEN}Validation: PASSED{NC} ({passed}/{total} checks)")
        return EXIT_SUCCESS
    else:
        failed = total - passed
        print(f"{RED}Validation: FAILED{NC} ({failed}/{total} checks failed)")
        return EXIT_VALIDATION_FAILED


if __name__ == '__main__':
    sys.exit(main())
