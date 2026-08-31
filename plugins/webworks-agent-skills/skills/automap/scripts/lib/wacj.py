"""WebWorks AutoMap Composition Job (.wacj) grammar.

One definition of the .wacj element/attribute vocabulary, shared by the AutoMap
skill's Python tools (parse-job.py, validate-job.py, list-job-targets.py,
create-job.py) so the grammar cannot drift between them.

Grounded in the shipped product source:

    Automap/Core/CompositionJobXmlElements.cs   element + attribute names
    Automap/Core/CompositionJobReader.cs        load semantics and defaults
    Automap/Core/CompositionJobWriter.cs        what a writer emits vs. omits
    Automap/Core/CompositionJobRunner.cs        run-time diagnostics
    Publish/Core/Deployment/InlineDeploySettings.cs   inline destination policy

Grammar (2026.1)::

    <CompositionJob name="..." version="1.0">
      <Jobs target="composition-wide output target">
        <Job path="..." role="shell|parcel|infer" build="True|False" target="..."/>
      </Jobs>
      <MergeSettings title="..." discover="True|False">
        <TOC name="..." title="...">
          <Group name="..." title="..."/>
        </TOC>
        <Group name="..." title="..."/>
      </MergeSettings>
      <Destination name="...">              <!-- legacy spelling: <DeployTarget> -->
        <DeploySettings>
          <DeploySetting Name="..." Action="file|s3|...">
            <Configuration Value="..." Region="..." Distribution="..."/>
          </DeploySetting>
        </DeploySettings>
      </Destination>
    </CompositionJob>

Reader defaults that the tools must reproduce: an unrecognized ``role`` is
``infer``; ``build`` defaults to ``False`` (a hand-authored member is federated
unless it opts in); ``discover`` defaults to ``False``; a missing
``<MergeSettings>`` means Automatic mode.
"""

from pathlib import Path
from typing import Optional
from xml.etree.ElementTree import Element  # For type hints only

# File extensions
COMPOSITION_EXTENSION = '.wacj'
JOB_EXTENSION = '.waj'
PROJECT_EXTENSIONS = ('.wep', '.wrp')
MEMBER_EXTENSIONS = (JOB_EXTENSION,) + PROJECT_EXTENSIONS

# Root elements (AutoMap dispatches on these, not on the extension)
COMPOSITION_ROOT = 'CompositionJob'
JOB_ROOT = 'Job'

# Member jobs
JOBS_ELEMENT = 'Jobs'
JOB_ELEMENT = 'Job'

# Member roles. An unrecognized value loads as ROLE_INFER.
ROLE_SHELL = 'shell'
ROLE_PARCEL = 'parcel'
ROLE_INFER = 'infer'
ROLES = (ROLE_SHELL, ROLE_PARCEL, ROLE_INFER)

# Merge settings (site TOC spec) - the same inner grammar as a .waj target
MERGE_SETTINGS_ELEMENT = 'MergeSettings'
TOC_ELEMENT = 'TOC'
GROUP_ELEMENT = 'Group'
SPEC_ELEMENTS = (TOC_ELEMENT, GROUP_ELEMENT)

# Shared federated destination
DESTINATION_ELEMENT = 'Destination'
DESTINATION_LEGACY_ELEMENT = 'DeployTarget'
DEPLOY_SETTINGS_ELEMENT = 'DeploySettings'
DEPLOY_SETTING_ELEMENT = 'DeploySetting'
DEPLOY_CONFIGURATION_ELEMENT = 'Configuration'
DEPLOY_SETTING_NAME_ATTR = 'Name'
DEPLOY_ACTION_ATTR = 'Action'

# Deployment actions. Only secret-free transports may be defined inline
# (InlineDeploySettings.EnforcePolicy): folder and Amazon S3. Any other
# action is rejected at parse time.
ACTION_FOLDER = 'file'
ACTION_S3 = 's3'

# Composition modes implied by <MergeSettings> (CompositionJob.Mode), named as
# the Administrator's Merge Settings area names them:
#   Automatic        - omit <MergeSettings>; compose every parcel at the destination
#   Custom           - declared <Group>/<TOC> placements
#   Custom + include-new - discover="true" plus placements ("Also include newly
#                      published parcels not listed above")
MODE_AUTOMATIC = 'automatic'
MODE_CUSTOM = 'custom'
MODE_CUSTOM_INCLUDE_NEW = 'custom+include-new'

# How a member's output target was selected
TARGET_SOURCE_MEMBER = 'member override'
TARGET_SOURCE_COMPOSITION = 'composition target'
TARGET_SOURCE_AUTO = 'auto-detect'


def is_composition_path(path: str) -> bool:
    """True when the path names a composition job file (.wacj)."""
    return Path(path).suffix.lower() == COMPOSITION_EXTENSION


def parses_as_bool(value: Optional[str]) -> bool:
    """True when .NET Boolean.TryParse would accept the attribute value.

    The reader uses Boolean.TryParse and silently falls back to the default,
    so a value like build="yes" loads as False; tools warn instead of guessing.
    """
    if value is None:
        return False
    return value.strip().lower() in ('true', 'false')


def parse_bool(value: Optional[str], default: bool = False) -> bool:
    """Parse an attribute with .NET Boolean.TryParse semantics."""
    if not parses_as_bool(value):
        return default
    return value.strip().lower() == 'true'


def normalize_role(value: Optional[str]) -> str:
    """Map a declared role to the value the reader loads (unknown -> infer)."""
    if value is None:
        return ROLE_INFER
    lowered = value.strip().lower()
    if lowered in (ROLE_SHELL, ROLE_PARCEL):
        return lowered
    return ROLE_INFER


def role_is_recognized(value: Optional[str]) -> bool:
    """True when the declared role is one the grammar names (or is absent)."""
    if value is None or value.strip() == '':
        return True
    return value.strip().lower() in ROLES


def member_display_name(member_path: str) -> str:
    """The member name as the product logs it: the file name without extension."""
    return Path(member_path).stem if member_path else ''


def _spec_node(elem: Element) -> Optional[dict]:
    """Convert a <TOC>/<Group> element into a spec node (other tags ignored)."""
    if elem.tag == TOC_ELEMENT:
        return {
            'kind': 'container',
            'name': elem.get('name', ''),
            # A container's title falls back to its name on load.
            'title': elem.get('title', '') or elem.get('name', ''),
            'children': [node for node in (_spec_node(child) for child in elem)
                         if node is not None],
        }
    if elem.tag == GROUP_ELEMENT:
        return {
            'kind': 'group',
            'name': elem.get('name', ''),
            'title': elem.get('title', ''),
        }
    return None


def spec_group_names(nodes: list) -> list:
    """Every group (leaf) name in a spec tree, in document order."""
    names = []
    for node in nodes:
        if node['kind'] == 'container':
            names.extend(spec_group_names(node['children']))
        else:
            names.append(node['name'])
    return names


def iter_spec(nodes: list, depth: int = 0):
    """Yield (depth, node) for every node in a spec tree, depth-first."""
    for node in nodes:
        yield depth, node
        if node['kind'] == 'container':
            yield from iter_spec(node['children'], depth + 1)


def unknown_spec_children(merge_elem: Optional[Element]) -> list:
    """Tag names under <MergeSettings> the reader ignores (nested included)."""
    unknown = []

    def walk(parent: Element) -> None:
        for child in parent:
            if child.tag in SPEC_ELEMENTS:
                if child.tag == TOC_ELEMENT:
                    walk(child)
            elif isinstance(child.tag, str):
                unknown.append(child.tag)

    if merge_elem is not None:
        walk(merge_elem)
    return unknown


def find_destination(root: Element):
    """Return (element, tag) for <Destination>, falling back to <DeployTarget>.

    The current spelling wins when both are present, matching the reader.
    """
    elem = root.find(DESTINATION_ELEMENT)
    if elem is not None:
        return elem, DESTINATION_ELEMENT

    elem = root.find(DESTINATION_LEGACY_ELEMENT)
    if elem is not None:
        return elem, DESTINATION_LEGACY_ELEMENT

    return None, ''


def extract_deploy_settings(destination_elem: Optional[Element]) -> list:
    """Inline destination definitions carried by <Destination>."""
    settings = []

    if destination_elem is None:
        return settings

    settings_elem = destination_elem.find(DEPLOY_SETTINGS_ELEMENT)
    if settings_elem is None:
        return settings

    for setting_elem in settings_elem.findall(DEPLOY_SETTING_ELEMENT):
        config_elem = setting_elem.find(DEPLOY_CONFIGURATION_ELEMENT)
        settings.append({
            'name': setting_elem.get(DEPLOY_SETTING_NAME_ATTR, ''),
            'action': setting_elem.get(DEPLOY_ACTION_ATTR, ''),
            'configuration': dict(config_elem.attrib) if config_elem is not None else {},
        })

    return settings


def extract_composition_info(root: Element, job_path: str) -> dict:
    """Extract everything the .wacj grammar carries, with reader defaults applied.

    Lenient by design: malformed input (a member with no path, a missing
    destination) is reported in the returned structure rather than raised, so
    parse-job.py can describe a file that validate-job.py rejects.
    """
    job_dir = Path(job_path).parent

    info = {
        'kind': 'composition',
        'name': root.get('name', ''),
        'version': root.get('version', ''),
        'outputTarget': '',
        'hasJobsElement': False,
        'members': [],
        'mergeSettings': {
            'present': False,
            'title': '',
            'discover': False,
            'spec': [],
        },
        'mode': MODE_AUTOMATIC,
        'destination': {
            'declared': False,
            'element': '',
            'legacySpelling': False,
            'name': '',
            'deploySettingsDeclared': False,
            'deploySettings': [],
        },
    }

    # Members. Jobs/@target is the composition-wide output target pushed down to
    # every member; Job/@target is a per-member override.
    jobs_elem = root.find(JOBS_ELEMENT)
    if jobs_elem is not None:
        info['hasJobsElement'] = True
        info['outputTarget'] = jobs_elem.get('target', '')

        for member_elem in jobs_elem.findall(JOB_ELEMENT):
            member_path = member_elem.get('path', '')
            role_declared = member_elem.get('role')
            build_declared = member_elem.get('build')
            member_target = member_elem.get('target', '')

            if member_target:
                effective_target = member_target
                target_source = TARGET_SOURCE_MEMBER
            elif info['outputTarget']:
                effective_target = info['outputTarget']
                target_source = TARGET_SOURCE_COMPOSITION
            else:
                effective_target = ''
                target_source = TARGET_SOURCE_AUTO

            resolved = str(job_dir / member_path) if member_path else ''

            info['members'].append({
                'path': member_path,
                'pathResolved': resolved,
                'exists': bool(resolved) and Path(resolved).exists(),
                'displayName': member_display_name(member_path),
                'role': normalize_role(role_declared),
                'roleDeclared': role_declared or '',
                'roleRecognized': role_is_recognized(role_declared),
                'build': parse_bool(build_declared, False),
                'buildDeclared': build_declared or '',
                'buildRecognized': build_declared is None or parses_as_bool(build_declared),
                'target': member_target,
                'effectiveTarget': effective_target,
                'targetSource': target_source,
            })

    # Merge settings (site TOC spec). Absence means Automatic mode.
    merge_elem = root.find(MERGE_SETTINGS_ELEMENT)
    if merge_elem is not None:
        discover = parse_bool(merge_elem.get('discover'), False)
        info['mergeSettings'] = {
            'present': True,
            'title': merge_elem.get('title', ''),
            'discover': discover,
            'discoverDeclared': merge_elem.get('discover', ''),
            'spec': [node for node in (_spec_node(child) for child in merge_elem)
                     if node is not None],
        }
        info['mode'] = MODE_CUSTOM_INCLUDE_NEW if discover else MODE_CUSTOM

    # Shared federated destination.
    destination_elem, destination_tag = find_destination(root)
    if destination_elem is not None:
        settings_elem = destination_elem.find(DEPLOY_SETTINGS_ELEMENT)
        info['destination'] = {
            'declared': True,
            'element': destination_tag,
            'legacySpelling': destination_tag == DESTINATION_LEGACY_ELEMENT,
            'name': destination_elem.get('name', ''),
            'deploySettingsDeclared': settings_elem is not None,
            'deploySettings': extract_deploy_settings(destination_elem),
        }

    return info
