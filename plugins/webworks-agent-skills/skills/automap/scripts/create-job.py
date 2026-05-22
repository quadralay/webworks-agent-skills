#!/usr/bin/env python3
"""
create-job.py

Create AutoMap job files (.waj) interactively or from a configuration file.

Usage:
    # Interactive mode (prompts for all input)
    python create-job.py --stationery path/to/stationery.wxsp

    # Config file mode (reads from JSON)
    python create-job.py --config job-config.json --output job.waj

    # Generate config template
    python create-job.py --template --stationery path/to/stationery.wxsp

Features:
    - Interactive workflow for job creation
    - Config file mode for scripted creation
    - Validates against Stationery formats
    - Generates valid AutoMap job XML
    - Preview before writing

Exit Codes:
    0 - Success
    1 - File error (stationery/config not found)
    2 - Invalid arguments
    3 - Validation error
    4 - User cancelled
"""

import argparse
import json
import sys
# Use defusedxml to prevent XXE attacks (CWE-611)
import defusedxml.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement, tostring  # For creating XML
from pathlib import Path
from typing import Optional
from xml.dom import minidom

# Exit codes
EXIT_SUCCESS = 0
EXIT_FILE_ERROR = 1
EXIT_ARG_ERROR = 2
EXIT_VALIDATION_ERROR = 3
EXIT_CANCELLED = 4

# ANSI color codes
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
RED = '\033[0;31m'
NC = '\033[0m'  # No Color


def log_error(message: str) -> None:
    """Print error message to stderr."""
    print(f"{RED}[ERROR]{NC} {message}", file=sys.stderr)


def log_info(message: str) -> None:
    """Print info message."""
    print(f"{BLUE}[INFO]{NC} {message}")


def log_success(message: str) -> None:
    """Print success message."""
    print(f"{GREEN}[SUCCESS]{NC} {message}")


def prompt(message: str, default: str = "") -> str:
    """Prompt user for input with optional default."""
    if default:
        result = input(f"{message} [{default}]: ").strip()
        return result if result else default
    return input(f"{message}: ").strip()


def confirm(message: str, default: bool = True) -> bool:
    """Ask user for yes/no confirmation."""
    suffix = "[Y/n]" if default else "[y/N]"
    response = input(f"{message} {suffix}: ").strip().lower()
    if not response:
        return default
    return response in ('y', 'yes')


def sanitize_filename(name: str) -> str:
    """Sanitize filename to prevent path traversal and invalid characters."""
    import re
    # Remove path separators and special characters
    name = re.sub(r'[^\w\-.]', '_', name)
    # Remove leading dots and dashes
    name = name.lstrip('.-')
    # Ensure not empty
    return name if name else "job"


def validate_safe_path(base_dir: Path, user_path: str) -> Path:
    """Validate path doesn't escape base directory."""
    full_path = (base_dir / user_path).resolve()
    try:
        full_path.relative_to(base_dir.resolve())
    except ValueError:
        raise ValueError(f"Path traversal attempt detected: {user_path}")
    return full_path


def validate_config(config: dict) -> list[str]:
    """Validate configuration before XML generation."""
    errors = []

    # Validate job name
    if not config.get('name', '').strip():
        errors.append("Job name cannot be empty")

    # Validate stationery
    if not config.get('stationery', '').strip():
        errors.append("Stationery path cannot be empty")

    # Validate targets
    if not config.get('targets'):
        errors.append("At least one target is required")

    for i, target in enumerate(config.get('targets', [])):
        if not target.get('name', '').strip():
            errors.append(f"Target {i+1} name cannot be empty")
        if not target.get('format', '').strip():
            errors.append(f"Target {i+1} format cannot be empty")

    # Validate groups (if present)
    for i, group in enumerate(config.get('groups', [])):
        if not group.get('name', '').strip():
            errors.append(f"Group {i+1} name cannot be empty")

    return errors


def write_file_atomic(path: str, content: str, encoding: str = 'utf-8') -> None:
    """Write file atomically using temp file + rename."""
    import tempfile
    import os
    path_obj = Path(path)
    dir_path = path_obj.parent

    # Create temp file in same directory for atomic rename
    fd, temp_path = tempfile.mkstemp(
        dir=dir_path,
        prefix=f'.{path_obj.name}.tmp',
        suffix='.tmp'
    )

    try:
        with os.fdopen(fd, 'w', encoding=encoding) as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, str(path_obj))  # Atomic on most systems
    except:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def parse_stationery(stationery_path: str) -> Optional[dict]:
    """Parse stationery file to extract formats and settings."""
    path = Path(stationery_path)
    if not path.exists():
        log_error(f"Stationery file not found: {stationery_path}")
        return None

    try:
        tree = ET.parse(stationery_path)
        root = tree.getroot()
    except ET.ParseError as e:
        log_error(f"Failed to parse stationery XML: {e}")
        return None

    # Handle namespace
    ns = {'ep': 'urn:WebWorks-Publish-Project'}

    # Extract runtime version
    runtime_version = root.get('RuntimeVersion', '')

    # Extract formats
    formats = []
    format_elements = root.findall('.//ep:Format', ns)
    if not format_elements:
        format_elements = list(root.iter('Format'))

    # Build settings map
    settings_map = {}
    for config in root.findall('.//ep:FormatConfiguration', ns) or list(root.iter('FormatConfiguration')):
        target_id = config.get('TargetID', '')
        settings = []
        format_settings = config.find('ep:FormatSettings', ns)
        if format_settings is None:
            format_settings = config.find('FormatSettings')
        if format_settings is not None:
            for setting in format_settings.findall('ep:FormatSetting', ns) or format_settings.findall('FormatSetting'):
                settings.append({
                    'name': setting.get('Name', ''),
                    'defaultValue': setting.get('Value', '')
                })
        if target_id:
            settings_map[target_id] = settings

    for fmt in format_elements:
        target_id = fmt.get('TargetID', '')
        formats.append({
            'name': fmt.get('Name', ''),
            'targetName': fmt.get('TargetName', ''),
            'type': fmt.get('Type', ''),
            'targetId': target_id,
            'settings': settings_map.get(target_id, [])
        })

    # Extract file mappings
    mappings = []
    for mapping in root.findall('.//ep:FileMapping', ns) or list(root.iter('FileMapping')):
        mappings.append({
            'extension': mapping.get('extension', ''),
            'adapter': mapping.get('adapter', '')
        })

    return {
        'path': str(path.resolve()),
        'runtimeVersion': runtime_version,
        'formats': formats,
        'fileMappings': mappings
    }


def generate_job_xml(config: dict) -> str:
    """Generate job file XML from configuration."""
    # Create root element (using xml.etree.ElementTree for creation)
    job = Element('Job')
    job.set('name', config.get('name', 'untitled'))
    job.set('version', '1.0')

    # Add Project reference
    project = SubElement(job, 'Project')
    project.set('path', config.get('stationery', ''))

    # Add Files section
    files = SubElement(job, 'Files')
    for group_config in config.get('groups', []):
        group = SubElement(files, 'Group')
        group.set('name', group_config.get('name', ''))
        for doc_path in group_config.get('documents', []):
            doc = SubElement(group, 'Document')
            doc.set('path', doc_path)

    # Add Targets section
    targets = SubElement(job, 'Targets')
    for target_config in config.get('targets', []):
        target = SubElement(targets, 'Target')
        target.set('name', target_config.get('name', ''))
        target.set('format', target_config.get('format', ''))
        target.set('formatType', target_config.get('formatType', 'Application'))
        target.set('build', 'True' if target_config.get('build', True) else 'False')
        target.set('deployTarget', target_config.get('deployTarget', ''))
        target.set('cleanOutput', 'True' if target_config.get('cleanOutput', False) else 'False')

        # Add Conditions if present
        conditions = target_config.get('conditions', [])
        if conditions:
            conditions_elem = SubElement(target, 'Conditions')
            conditions_elem.set('Expression', '')
            conditions_elem.set('UseClassicConditions', 'False')
            conditions_elem.set('UseDocumentExpression', 'True')
            for cond in conditions:
                cond_elem = SubElement(conditions_elem, 'Condition')
                cond_elem.set('name', cond.get('name', ''))
                cond_elem.set('value', cond.get('value', 'True'))
                cond_elem.set('Passthrough', 'False')
                cond_elem.set('UseDocumentValue', 'False')

        # Add Variables if present
        variables = target_config.get('variables', [])
        if variables:
            variables_elem = SubElement(target, 'Variables')
            for var in variables:
                var_elem = SubElement(variables_elem, 'Variable')
                var_elem.set('name', var.get('name', ''))
                var_elem.set('value', var.get('value', ''))
                var_elem.set('UseDocumentValue', 'False')

        # Add Settings if present
        settings = target_config.get('settings', [])
        if settings:
            settings_elem = SubElement(target, 'Settings')
            for setting in settings:
                setting_elem = SubElement(settings_elem, 'Setting')
                setting_elem.set('name', setting.get('name', ''))
                setting_elem.set('value', setting.get('value', ''))

    # Convert to string with pretty printing
    xml_str = tostring(job, encoding='unicode')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent='  ', encoding=None)

    # Remove extra blank lines and fix declaration
    lines = pretty_xml.split('\n')
    # Replace first line with proper declaration
    lines[0] = '<?xml version="1.0" encoding="utf-8"?>'
    # Remove empty lines
    lines = [line for line in lines if line.strip()]

    return '\n'.join(lines)


def interactive_collect_groups() -> list[dict]:
    """Interactively collect document groups from user."""
    groups = []

    print(f"\n{CYAN}=== Source Documents ==={NC}")
    print("Organize your documents into groups (e.g., 'Getting Started', 'Reference').")
    print()

    while True:
        group_name = prompt("Group name (blank to finish)")
        if not group_name:
            if not groups:
                print(f"{YELLOW}Warning: No groups added. At least one group is recommended.{NC}")
                if not confirm("Continue without groups?", default=False):
                    continue
            break

        documents = []
        print(f"\n  Adding documents to '{group_name}'")
        print("  Enter document paths relative to job file location.")
        print("  (Blank line to finish this group)")

        while True:
            doc_path = prompt("    Document path")
            if not doc_path:
                break
            documents.append(doc_path)

        if documents:
            groups.append({'name': group_name, 'documents': documents})
            print(f"\n  {GREEN}Added group '{group_name}' with {len(documents)} documents{NC}")
        else:
            print(f"  {YELLOW}Skipped empty group '{group_name}'{NC}")

        print()
        if not confirm("Add another group?"):
            break

    return groups


def interactive_collect_targets(stationery_data: dict) -> list[dict]:
    """Interactively collect target configuration from user."""
    targets = []
    available_formats = stationery_data.get('formats', [])

    print(f"\n{CYAN}=== Build Targets ==={NC}")
    print("\nAvailable formats from Stationery:")
    for i, fmt in enumerate(available_formats, 1):
        print(f"  {i}. {fmt['name']} ({fmt['type']})")

    while True:
        print()
        choice = prompt("Select format (number or name, blank to finish)")
        if not choice:
            if not targets:
                log_error("At least one target is required.")
                continue
            break

        # Find the selected format
        selected_format = None
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(available_formats):
                selected_format = available_formats[idx]
        else:
            for fmt in available_formats:
                if fmt['name'].lower() == choice.lower():
                    selected_format = fmt
                    break

        if not selected_format:
            log_error(f"Format not found: {choice}")
            continue

        print(f"\n  Configuring target: {GREEN}{selected_format['name']}{NC}")

        target = {
            'name': selected_format['targetName'],
            'format': selected_format['name'],
            'formatType': selected_format['type'],
            'build': confirm("  Build this target by default?"),
            'cleanOutput': confirm("  Clean output before build?", default=False),
            'deployTarget': prompt("  Deploy target name (blank for none)", ""),
            'conditions': [],
            'variables': [],
            'settings': []
        }

        # Ask about overrides
        print("\n  Configure overrides?")
        print("    c = conditions, v = variables, s = settings, n = none")
        override_choice = prompt("  Override type", "n").lower()

        if 'c' in override_choice:
            print("\n  Adding conditions (name=value format, blank to finish):")
            while True:
                cond_input = prompt("    Condition (e.g., OnlineOnly=True)")
                if not cond_input:
                    break
                if '=' in cond_input:
                    name, value = cond_input.split('=', 1)
                    target['conditions'].append({'name': name.strip(), 'value': value.strip()})

        if 'v' in override_choice:
            print("\n  Adding variables (name=value format, blank to finish):")
            while True:
                var_input = prompt("    Variable (e.g., ProductVersion=2025.1)")
                if not var_input:
                    break
                if '=' in var_input:
                    name, value = var_input.split('=', 1)
                    target['variables'].append({'name': name.strip(), 'value': value.strip()})

        if 's' in override_choice:
            print("\n  Available settings:")
            for setting in selected_format.get('settings', []):
                print(f"    - {setting['name']} (default: \"{setting['defaultValue']}\")")
            print("\n  Adding settings (name=value format, blank to finish):")
            while True:
                setting_input = prompt("    Setting")
                if not setting_input:
                    break
                if '=' in setting_input:
                    name, value = setting_input.split('=', 1)
                    target['settings'].append({'name': name.strip(), 'value': value.strip()})

        targets.append(target)
        print(f"\n  {GREEN}Added target: {target['name']}{NC}")

        if not confirm("\nAdd another target?", default=False):
            break

    return targets


def interactive_mode(stationery_path: str) -> Optional[dict]:
    """Run interactive job creation workflow."""
    print(f"\n{CYAN}{'='*60}{NC}")
    print(f"{CYAN}  AutoMap Job File Creator - Interactive Mode{NC}")
    print(f"{CYAN}{'='*60}{NC}")

    # Parse stationery
    print(f"\nParsing Stationery: {stationery_path}")
    stationery_data = parse_stationery(stationery_path)
    if not stationery_data:
        return None

    print(f"{GREEN}Found {len(stationery_data['formats'])} format(s){NC}")

    # Get job name
    print(f"\n{CYAN}=== Job Configuration ==={NC}")
    job_name = prompt("Job name (e.g., 'en' for English locale)", "job")
    job_name = sanitize_filename(job_name)

    # Calculate relative stationery path
    stationery_rel = prompt(
        "Stationery path (relative to job file)",
        stationery_path
    )

    # Collect groups
    groups = interactive_collect_groups()

    # Collect targets
    targets = interactive_collect_targets(stationery_data)

    # Build config
    config = {
        'name': job_name,
        'stationery': stationery_rel,
        'groups': groups,
        'targets': targets
    }

    return config


def print_summary(config: dict) -> None:
    """Print a human-readable summary of the job configuration."""
    print(f"\n{'='*60}")
    print(f"Job: {config['name']} (version 1.0)")
    print(f"Stationery: {config['stationery']}")
    print('='*60)

    groups = config.get('groups', [])
    total_docs = sum(len(g.get('documents', [])) for g in groups)
    print(f"\nSource Documents ({len(groups)} groups, {total_docs} documents):")
    for group in groups:
        print(f"\n  {group['name']}/")
        for doc in group.get('documents', []):
            print(f"    - {doc}")

    targets = config.get('targets', [])
    print(f"\nTargets ({len(targets)}):")
    for target in targets:
        status = "[BUILD]" if target.get('build', True) else "[SKIP]"
        print(f"\n  {status} {target['name']}")
        if target.get('deployTarget'):
            print(f"         Deploy: {target['deployTarget']}")
        if target.get('conditions'):
            conds = ', '.join(f"{c['name']}={c['value']}" for c in target['conditions'])
            print(f"         Conditions: {conds}")
        if target.get('variables'):
            vars_str = ', '.join(f"{v['name']}={v['value']}" for v in target['variables'])
            print(f"         Variables: {vars_str}")
        if target.get('settings'):
            sets = ', '.join(f"{s['name']}=\"{s['value']}\"" for s in target['settings'])
            print(f"         Settings: {sets}")

    print('\n' + '='*60)


def generate_template(stationery_data: dict, stationery_path: str) -> dict:
    """Generate a template configuration from stationery."""
    formats = stationery_data.get('formats', [])

    config = {
        'name': 'my-job',
        'stationery': stationery_path,
        'groups': [
            {
                'name': 'Main',
                'documents': [
                    'Source\\document1.md',
                    'Source\\document2.md'
                ]
            }
        ],
        'targets': []
    }

    # Add a target for each format
    for fmt in formats:
        target = {
            'name': fmt['targetName'],
            'format': fmt['name'],
            'formatType': fmt['type'],
            'build': True,
            'cleanOutput': False,
            'deployTarget': '',
            'conditions': [],
            'variables': [],
            'settings': []
        }
        config['targets'].append(target)

    return config


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Create AutoMap job files (.waj) interactively or from configuration.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exit Codes:
    0    Success
    1    File error
    2    Invalid arguments
    3    Validation error
    4    User cancelled

Examples:
    # Interactive mode
    %(prog)s --stationery path/to/stationery.wxsp

    # Config file mode
    %(prog)s --config job-config.json --output job.waj

    # Generate config template
    %(prog)s --template --stationery path/to/stationery.wxsp > template.json
"""
    )

    parser.add_argument('-s', '--stationery', metavar='FILE',
                        help='Path to Stationery file (.wxsp) for interactive mode or template')
    parser.add_argument('-c', '--config', metavar='FILE',
                        help='Path to job configuration JSON file')
    parser.add_argument('-o', '--output', metavar='FILE',
                        help='Output path for job file (default: <name>.waj)')
    parser.add_argument('-t', '--template', action='store_true',
                        help='Generate a config template from Stationery (output to stdout)')
    parser.add_argument('--no-preview', action='store_true',
                        help='Skip XML preview (config mode only)')
    parser.add_argument('-y', '--yes', action='store_true',
                        help='Auto-confirm file generation')

    args = parser.parse_args()

    # Template mode
    if args.template:
        if not args.stationery:
            log_error("--stationery is required with --template")
            return EXIT_ARG_ERROR

        stationery_data = parse_stationery(args.stationery)
        if not stationery_data:
            return EXIT_FILE_ERROR

        template = generate_template(stationery_data, args.stationery)
        print(json.dumps(template, indent=2))
        return EXIT_SUCCESS

    # Config file mode
    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            log_error(f"Config file not found: {args.config}")
            return EXIT_FILE_ERROR

        try:
            with open(config_path) as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            log_error(f"Invalid JSON in config file: {e}")
            return EXIT_FILE_ERROR

        # Validate config
        errors = validate_config(config)
        if errors:
            for error in errors:
                log_error(error)
            return EXIT_VALIDATION_ERROR

        # Generate XML
        xml_content = generate_job_xml(config)

        # Preview unless skipped
        if not args.no_preview and not args.yes:
            print(f"\n{CYAN}Generated XML:{NC}\n")
            print(xml_content)
            print()
            if not confirm("Generate job file?"):
                print("Cancelled.")
                return EXIT_CANCELLED

        # Determine output path
        output_path = args.output if args.output else f"{config.get('name', 'job')}.waj"

        # Validate output path to prevent directory traversal
        try:
            validate_safe_path(Path.cwd(), output_path)
        except ValueError as e:
            log_error(str(e))
            return EXIT_VALIDATION_ERROR

        # Write file
        write_file_atomic(output_path, xml_content)

        log_success(f"Created: {output_path}")
        return EXIT_SUCCESS

    # Interactive mode
    if args.stationery:
        stationery_path = Path(args.stationery)
        if not stationery_path.exists():
            log_error(f"Stationery file not found: {args.stationery}")
            return EXIT_FILE_ERROR

        config = interactive_mode(str(stationery_path))
        if not config:
            return EXIT_FILE_ERROR

        # Validate config
        errors = validate_config(config)
        if errors:
            for error in errors:
                log_error(error)
            return EXIT_VALIDATION_ERROR

        # Show summary
        print_summary(config)

        # Preview XML
        if confirm("\nPreview XML?"):
            xml_content = generate_job_xml(config)
            print(f"\n{xml_content}")

        # Confirm generation
        print()
        choice = prompt("Generate file? (y=generate, e=export config, c=cancel)", "y").lower()

        if choice == 'c':
            print("Cancelled.")
            return EXIT_CANCELLED

        if choice == 'e':
            config_output = f"{sanitize_filename(config['name'])}-config.json"

            # Validate config output path to prevent directory traversal
            try:
                validate_safe_path(Path.cwd(), config_output)
            except ValueError as e:
                log_error(str(e))
                return EXIT_VALIDATION_ERROR

            write_file_atomic(config_output, json.dumps(config, indent=2))
            log_success(f"Exported config: {config_output}")
            return EXIT_SUCCESS

        # Generate job file
        xml_content = generate_job_xml(config)
        output_path = args.output if args.output else f"{config['name']}.waj"

        # Validate output path to prevent directory traversal
        try:
            validate_safe_path(Path.cwd(), output_path)
        except ValueError as e:
            log_error(str(e))
            return EXIT_VALIDATION_ERROR

        write_file_atomic(output_path, xml_content)

        log_success(f"Created: {output_path}")

        print(f"\n{CYAN}Next steps:{NC}")
        print(f"  - Validate: python validate-job.py {output_path}")
        print(f"  - Build: ./automap-wrapper.sh {output_path}")

        return EXIT_SUCCESS

    # No valid mode specified
    parser.print_help()
    return EXIT_ARG_ERROR


if __name__ == '__main__':
    sys.exit(main())
