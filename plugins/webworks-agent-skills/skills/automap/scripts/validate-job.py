#!/usr/bin/env python3
"""
validate-job.py

Validate AutoMap job files (.waj) and composition job files (.wacj) for
correctness before building.

Usage:
    python validate-job.py [OPTIONS] <job-file>

Features:
    - XML well-formedness validation
    - Required elements check
    - Stationery reference validation
    - Target configuration validation
    - Optional document existence check
    - Optional format name validation against Stationery
    - Composition jobs (.wacj): member/role/build grammar, output target
      selection, MergeSettings spec, destination and inline destination
      definitions, plus an optional cross-check of .waj members

Exit Codes:
    0 - All validations passed
    1 - File error (job file not found)
    2 - Invalid arguments
    3 - Validation failed
"""

import argparse
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
    ACTION_WEBDAV, COMPOSITION_EXTENSION, COMPOSITION_ROOT, JOB_EXTENSION,
    JOB_ROOT, MEMBER_EXTENSIONS, MERGE_SETTINGS_ELEMENT, MODE_DISCOVERY,
    ROLE_SHELL, TARGET_SOURCE_AUTO, TARGET_SOURCE_COMPOSITION,
    TARGET_SOURCE_MEMBER, extract_composition_info, is_composition_path,
    iter_spec, spec_group_names, unknown_spec_children,
)

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


def print_report(results: list, job_file: str, verbose: bool) -> int:
    """Print the validation report and return the process exit code."""
    print(f"\n{BLUE}Validation Results:{NC} {job_file}\n")

    for result in results:
        if verbose or not result.passed or result.warnings:
            print_result(result)

    passed = sum(1 for r in results if r.passed)
    total = len(results)
    warnings = sum(len(r.warnings) for r in results)

    print()
    if passed == total:
        if warnings:
            print(f"{GREEN}Validation: PASSED{NC} ({passed}/{total} checks, {warnings} warnings)")
        else:
            print(f"{GREEN}Validation: PASSED{NC} ({passed}/{total} checks)")
        return EXIT_SUCCESS

    print(f"{RED}Validation: FAILED{NC} ({total - passed}/{total} checks failed)")
    return EXIT_VALIDATION_FAILED


def validate_file_exists(job_file: str) -> ValidationResult:
    """Check that the job file exists."""
    result = ValidationResult("Job file exists")
    path = Path(job_file)

    if not path.exists():
        return result.fail_check(f"File not found: {job_file}")

    if path.suffix.lower() not in (JOB_EXTENSION, COMPOSITION_EXTENSION):
        return result.fail_check(
            f"Invalid extension: {path.suffix} "
            f"(expected {JOB_EXTENSION} or {COMPOSITION_EXTENSION})")

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

    if root.tag == COMPOSITION_ROOT:
        return result.fail_check(
            f"This is a composition job (<{COMPOSITION_ROOT}>) in a "
            f"{JOB_EXTENSION} file; rename it to {COMPOSITION_EXTENSION}")

    if root.tag != JOB_ROOT:
        return result.fail_check(f"Expected <{JOB_ROOT}>, found <{root.tag}>")

    name = root.get('name')
    version = root.get('version')

    if not name:
        return result.fail_check("Missing 'name' attribute on Job element")

    if not version:
        result.add_warning("Missing 'version' attribute (defaulting to 1.0)")

    return result.pass_check(f"name=\"{name}\" version=\"{version or '1.0'}\"")


def validate_project_element(root: Element, job_dir: Path) -> ValidationResult:
    """Check that the Project element exists and references a valid origin.

    The origin may be a Stationery (.wxsp) or a Designer/Express project
    (.wep/.wrp). A .wep/.wrp origin with useAsStationery="True" is staged as a
    stationery; without it, the project builds in place. All are valid.
    """
    result = ValidationResult("Project/Stationery reference")

    project = root.find('Project')
    if project is None:
        return result.fail_check("Missing <Project> element")

    origin_path = project.get('path')
    if not origin_path:
        return result.fail_check("Missing 'path' attribute on Project element")

    use_as_stationery = project.get('useAsStationery', 'False') == 'True'
    suffix = Path(origin_path).suffix.lower()
    is_project_origin = suffix in ('.wep', '.wrp')
    is_stationery_origin = suffix in ('.wxsp',)

    # Resolve the origin mode for the report message
    if is_project_origin and use_as_stationery:
        mode = "project as stationery"
    elif is_project_origin:
        mode = "project built in place"
    elif is_stationery_origin:
        mode = "Stationery"
    else:
        mode = "origin"
        result.add_warning(
            f"Unrecognized origin extension '{suffix or '(none)'}' "
            "(expected .wxsp or .wep/.wrp)"
        )

    # useAsStationery is only meaningful for a .wep/.wrp origin
    if use_as_stationery and not is_project_origin:
        result.add_warning(
            f"useAsStationery=\"True\" is ignored for a '{suffix or '(none)'}' "
            "origin (applies only to .wep/.wrp projects)"
        )

    # Try to resolve the path
    resolved = job_dir / origin_path
    if resolved.exists():
        return result.pass_check(f"Found ({mode}): {origin_path}")
    else:
        return result.fail_check(f"Not found: {origin_path}")


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


def validate_composition_root(root: Element) -> ValidationResult:
    """Check the <CompositionJob> root element and its attributes."""
    result = ValidationResult("CompositionJob element valid")

    if root.tag == JOB_ROOT:
        return result.fail_check(
            f"This is a publishing job (<{JOB_ROOT}>) in a "
            f"{COMPOSITION_EXTENSION} file; rename it to {JOB_EXTENSION}")

    if root.tag != COMPOSITION_ROOT:
        return result.fail_check(f"Expected <{COMPOSITION_ROOT}>, found <{root.tag}>")

    name = root.get('name')
    version = root.get('version')

    # The name drives the composition log file name (<name>-log.txt beside the
    # .wacj), so an unnamed composition logs to "-log.txt".
    if not name:
        return result.fail_check(
            f"Missing 'name' attribute on {COMPOSITION_ROOT} element "
            "(it names the composition log file)")

    if not version:
        result.add_warning("Missing 'version' attribute (writers emit 1.0)")

    return result.pass_check(f"name=\"{name}\" version=\"{version or '1.0'}\"")


def validate_composition_members(info: dict) -> ValidationResult:
    """Check <Jobs>/<Job> member references and their attributes."""
    result = ValidationResult("Member jobs")

    if not info['hasJobsElement']:
        return result.fail_check(
            "Missing <Jobs> element - a composition with no members cannot "
            "resolve the shell format")

    members = info['members']
    if not members:
        return result.fail_check("No <Job> elements found under <Jobs>")

    missing_path = 0
    seen_paths = {}

    for index, member in enumerate(members, start=1):
        label = member['displayName'] or f"member {index}"

        if not member['path']:
            missing_path += 1
            result.add_warning(f"Member {index} is missing its 'path' attribute")
            continue

        key = member['path'].lower()
        if key in seen_paths:
            result.add_warning(
                f"Duplicate member path: {member['path']} "
                f"(also member {seen_paths[key]})")
        else:
            seen_paths[key] = index

        suffix = Path(member['path']).suffix.lower()
        if suffix not in MEMBER_EXTENSIONS:
            result.add_warning(
                f"Member '{label}' has an unexpected extension "
                f"'{suffix or '(none)'}' (expected {', '.join(MEMBER_EXTENSIONS)})")

        if not member['roleRecognized']:
            result.add_warning(
                f"Member '{label}' has an unrecognized role "
                f"\"{member['roleDeclared']}\" - it loads as \"infer\" "
                "(expected shell, parcel or infer)")

        if not member['buildRecognized']:
            result.add_warning(
                f"Member '{label}' has a non-boolean build "
                f"\"{member['buildDeclared']}\" - it loads as False "
                "(expected True or False)")

    shells = [m for m in members if m['role'] == ROLE_SHELL]
    if not shells:
        result.add_warning(
            "No member declares role=\"shell\" - the first member is used to "
            "resolve the shell format")
    elif len(shells) > 1:
        result.add_warning(
            f"{len(shells)} members declare role=\"shell\" - the first one is "
            "used to resolve the shell format")

    if missing_path:
        return result.fail_check(
            f"{missing_path} of {len(members)} members are missing 'path'")

    built = sum(1 for m in members if m['build'])
    return result.pass_check(
        f"{len(members)} members ({built} built by this composition)")


def validate_composition_member_paths(info: dict) -> ValidationResult:
    """Check that every member job/project file exists on disk."""
    result = ValidationResult("Member paths")

    members = [m for m in info['members'] if m['path']]
    if not members:
        return result.pass_check("(no members)")

    missing = [m['path'] for m in members if not m['exists']]
    found = len(members) - len(missing)

    for path in missing[:5]:
        result.add_warning(f"Not found: {path}")
    if len(missing) > 5:
        result.add_warning(f"... and {len(missing) - 5} more missing")

    if not missing:
        return result.pass_check(f"All {found} members found")
    if found:
        return result.pass_check(f"{found} found, {len(missing)} missing")
    return result.fail_check(f"All {len(missing)} members missing")


def validate_composition_target_selection(info: dict) -> ValidationResult:
    """Report how each member's output target is selected."""
    result = ValidationResult("Output target selection")

    members = info['members']
    if not members:
        return result.pass_check("(no members)")

    counts = {
        TARGET_SOURCE_MEMBER: 0,
        TARGET_SOURCE_COMPOSITION: 0,
        TARGET_SOURCE_AUTO: 0,
    }
    for member in members:
        counts[member['targetSource']] += 1

    parts = [f"{count} {source}" for source, count in counts.items() if count]

    composition_target = info['outputTarget'] or '(none)'
    return result.pass_check(
        f"Jobs/@target={composition_target}; " + ", ".join(parts))


def validate_composition_merge_settings(info: dict, root: Element) -> ValidationResult:
    """Check <MergeSettings> - the composition's site TOC spec."""
    result = ValidationResult("Site TOC (MergeSettings)")

    merge = info['mergeSettings']
    if not merge['present']:
        # Absence IS discovery mode, not an omission.
        return result.pass_check(f"{MODE_DISCOVERY} mode (no <MergeSettings>)")

    if merge['title']:
        result.add_warning(
            f"MergeSettings title '{merge['title']}' is accepted for grammar "
            "parity but is not used by composition (the composed site's title "
            "comes from the shell project's build)")

    if merge.get('discoverDeclared') and not merge['discover'] \
            and merge['discoverDeclared'].strip().lower() != 'false':
        result.add_warning(
            f"Non-boolean discover \"{merge['discoverDeclared']}\" - it loads "
            "as False (expected True or False)")

    for tag in sorted(set(unknown_spec_children(root.find(MERGE_SETTINGS_ELEMENT)))):
        result.add_warning(
            f"<{tag}> under <MergeSettings> is ignored (expected <TOC> or <Group>)")

    unnamed = 0
    names = []
    for _, node in iter_spec(merge['spec']):
        if not node['name']:
            unnamed += 1
        elif node['kind'] == 'group':
            names.append(node['name'])

    if unnamed:
        result.add_warning(f"{unnamed} <TOC>/<Group> node(s) missing 'name'")

    duplicates = sorted({name for name in names if names.count(name) > 1})
    for name in duplicates:
        result.add_warning(
            f"Group '{name}' is declared more than once - the compose treats "
            "duplicate group names as one")

    group_count = len(spec_group_names(merge['spec']))
    return result.pass_check(f"{info['mode']} mode, {group_count} groups declared")


def validate_composition_destination(info: dict) -> ValidationResult:
    """Check <Destination> and any inline destination definitions."""
    result = ValidationResult("Destination")

    destination = info['destination']
    if not destination['declared']:
        return result.fail_check(
            "Missing <Destination name=\"...\"/> - the composition cannot "
            "resolve the shared federated destination")

    if destination['legacySpelling']:
        result.add_warning(
            "<DeployTarget> is the pre-release spelling of <Destination>, read "
            "for one release; saving the job writes <Destination>")

    if not destination['name']:
        return result.fail_check(
            f"<{destination['element']}> is missing its 'name' attribute")

    seen = {}
    for setting in destination['deploySettings']:
        name = setting['name']
        if not name:
            return result.fail_check(
                "An inline destination definition is missing its Name attribute")

        if name in seen:
            return result.fail_check(f"Duplicate inline destination definition '{name}'")
        seen[name] = True

        if setting['action'] == ACTION_WEBDAV:
            return result.fail_check(
                f"Inline destination definition '{name}' uses the WebDAV "
                "('http') action; WebDAV definitions embed credentials and "
                "cannot be stored in job files - define it in deploy.prefs")

        if not setting['action']:
            result.add_warning(
                f"Inline destination definition '{name}' has no Action "
                "attribute (it loads as a custom action)")

    if destination['deploySettings'] and destination['name'] not in seen:
        result.add_warning(
            f"Inline definitions are present but none is named "
            f"'{destination['name']}' - that name must resolve from the "
            "--deploysettings overlay or deploy.prefs")

    inline = f", {len(destination['deploySettings'])} inline definition(s)" \
        if destination['deploySettings'] else ""
    return result.pass_check(f"{destination['name']}{inline}")


def validate_composition_member_jobs(info: dict) -> ValidationResult:
    """Cross-check .waj members against the composition's selections.

    Mirrors two run-time checks statically: the selected output target must be
    one the member's job declares (CompositionTargetSelector.ResolveExplicit),
    and an unbuilt member's own job should deploy that target to the
    composition's destination (CompositionJobRunner.WarnOnMemberDestinationMismatch).
    """
    result = ValidationResult("Member job cross-check")

    destination_name = info['destination']['name']
    checked = 0
    mismatched_targets = []

    for member in info['members']:
        if not member['path'] or not member['exists']:
            continue
        if Path(member['path']).suffix.lower() != JOB_EXTENSION:
            # A .wep/.wrp member's target universe is the project's targets,
            # which needs the format installation to resolve.
            continue

        try:
            member_root = ET.parse(member['pathResolved']).getroot()
        except Exception as exp:
            result.add_warning(f"Member '{member['displayName']}': unreadable ({exp})")
            continue

        if member_root.tag != JOB_ROOT:
            result.add_warning(
                f"Member '{member['displayName']}': expected <{JOB_ROOT}>, "
                f"found <{member_root.tag}>")
            continue

        checked += 1

        targets_elem = member_root.find('Targets')
        target_elems = targets_elem.findall('Target') if targets_elem is not None else []
        declared = [t.get('name', '') for t in target_elems]

        selected = member['effectiveTarget']
        if selected and declared and selected not in declared:
            mismatched_targets.append(member['displayName'])
            result.add_warning(
                f"Member '{member['displayName']}' has no output target named "
                f"'{selected}' (from {member['targetSource']}). Its job "
                f"declares: {', '.join(declared) or '(none)'}")
            continue

        if not selected:
            continue

        # A built member deploys to the composition's destination regardless,
        # so only unbuilt members are cross-checked.
        if member['build']:
            continue

        selected_elem = next((t for t in target_elems if t.get('name', '') == selected), None)
        if selected_elem is None:
            continue

        member_destination = (selected_elem.get('destination')
                              or selected_elem.get('deployTarget') or '')

        if not member_destination:
            result.add_warning(
                f"Member '{member['displayName']}': its job declares no "
                f"destination for output target '{selected}', so its output "
                "does not deploy anywhere this composition can read")
        elif destination_name and member_destination.lower() != destination_name.lower():
            result.add_warning(
                f"Member '{member['displayName']}': its job deploys output "
                f"target '{selected}' to destination '{member_destination}', "
                f"not to this composition's destination '{destination_name}'")

    if mismatched_targets:
        return result.fail_check(
            f"{len(mismatched_targets)} member(s) do not declare the selected "
            "output target")

    if not checked:
        return result.pass_check("(no .waj members to cross-check)")

    return result.pass_check(f"{checked} .waj members cross-checked")


def run_composition_checks(root: Element, job_file: str,
                           check_members: bool) -> list:
    """Run every .wacj check and return the results in report order."""
    results = []

    result = validate_composition_root(root)
    results.append(result)
    if not result.passed:
        return results

    info = extract_composition_info(root, job_file)

    results.append(validate_composition_members(info))
    if check_members:
        results.append(validate_composition_member_paths(info))
    results.append(validate_composition_target_selection(info))
    results.append(validate_composition_merge_settings(info, root))
    results.append(validate_composition_destination(info))
    if check_members:
        results.append(validate_composition_member_jobs(info))

    return results


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
        description='Validate AutoMap job (.waj) and composition job (.wacj) files.',
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

    # Composition job grammar only
    %(prog)s composition.wacj

    # Composition job plus member existence and .waj cross-check
    %(prog)s --check-members composition.wacj
"""
    )

    parser.add_argument('job_file', metavar='job-file',
                        help='Path to .waj job file or .wacj composition job file')
    parser.add_argument('-d', '--check-documents', action='store_true',
                        help='Check that referenced documents exist (.waj)')
    parser.add_argument('-s', '--check-stationery', action='store_true',
                        help='Validate format names against Stationery (.waj)')
    parser.add_argument('-m', '--check-members', action='store_true',
                        help='Check member jobs exist and cross-check their '
                             'output target and destination (.wacj)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Show all checks including passed ones')

    args = parser.parse_args()
    job_path = Path(args.job_file)
    job_dir = job_path.parent

    results = []

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

    # Composition jobs (.wacj) reference member jobs instead of documents and
    # targets, so they run their own check sequence.
    if is_composition_path(args.job_file):
        # --check-documents is the .waj spelling of the same intent, so it also
        # turns on the member checks.
        check_members = args.check_members or args.check_documents
        results.extend(run_composition_checks(root, args.job_file, check_members))
        return print_report(results, args.job_file, args.verbose)

    # Check 3: Root element
    results.append(validate_root_element(root))

    # Check 4: Project element
    results.append(validate_project_element(root, job_dir))

    # Get stationery path for later checks
    project = root.find('Project')
    stationery_path = job_dir / project.get('path', '') if project is not None else Path()

    # Check 5: Files element
    results.append(validate_files_element(root))

    # Check 6: Document existence (optional)
    if args.check_documents:
        results.append(validate_documents_exist(root, job_dir))

    # Check 7: Targets element
    results.append(validate_targets_element(root))

    # Check 8: Format validation (optional)
    if args.check_stationery:
        results.append(validate_target_formats(root, stationery_path))

    # Print results
    return print_report(results, args.job_file, args.verbose)


if __name__ == '__main__':
    sys.exit(main())
