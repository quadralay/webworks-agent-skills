#!/usr/bin/env python3
"""
resolve-version-root.py

Deterministically resolve ePublisher VersionRoot with the following precedence:
1. AUTOMAP_EXE_PATH environment variable
2. Designer registry entry
3. AutoMap registry entry

VersionRoot shape:
    C:\\Program Files\\WebWorks\\ePublisher\\[version]

The script returns JSON with derived component directories and availability flags
for Formats, Adapters, and Helpers.
"""

import argparse
import json
import os
import re
import sys
import defusedxml.ElementTree as ET
from pathlib import Path
from typing import Optional

try:
    import winreg  # type: ignore[attr-defined]
except ImportError:
    winreg = None


REGISTRY_SOURCES = [
    ("designer_registry", r"SOFTWARE\WebWorks\ePublisher Designer"),
    ("designer_registry", r"SOFTWARE\WOW6432Node\WebWorks\ePublisher Designer"),
    ("automap_registry", r"SOFTWARE\WebWorks\ePublisher AutoMap"),
    ("automap_registry", r"SOFTWARE\WOW6432Node\WebWorks\ePublisher AutoMap"),
]

EXE_VALUE_CANDIDATES = ("ExePath", "InstallPath", "Path", "InstallDir")

EXIT_SUCCESS = 0
EXIT_NOT_FOUND = 1
EXIT_INVALID_ARGS = 2


RED = '\033[0;31m'
NC = '\033[0m'


def log_verbose(message: str, verbose: bool) -> None:
    if verbose:
        print(f"[VERBOSE] {message}", file=sys.stderr)


def log_error(message: str) -> None:
    print(f"{RED}[ERROR]{NC} {message}", file=sys.stderr)


def parse_version_key(version: str) -> tuple[int, ...]:
    """
    Parse dotted version fragments to numeric tuple for deterministic sorting.
    Example: "2024.1" -> (2024, 1)
    """
    return tuple(int(part) for part in re.findall(r"\d+", version))


def extract_base_format_version(project_file: Path, verbose: bool) -> Optional[str]:
    """Read Base Format Version from .wep/.wrp/.wxsp root attributes."""
    log_verbose(f"Reading project metadata from: {project_file}", verbose)

    if not project_file.is_file():
        log_error(f"Project file not found: {project_file}")
        return None

    try:
        root = ET.parse(project_file).getroot()
    except (ET.ParseError, OSError, ValueError) as exc:
        log_error(f"Failed to parse project XML: {exc}")
        return None

    runtime_version = root.get("RuntimeVersion", "").strip()
    format_version = root.get("FormatVersion", "").strip()

    if not runtime_version:
        log_error("RuntimeVersion not found in project file")
        return None

    if not format_version or format_version == "{Current}":
        return runtime_version

    return format_version


def derive_version_root_from_executable(exe_path: str, verbose: bool) -> tuple[Optional[Path], Optional[str]]:
    """
    Derive VersionRoot from an executable path by locating the "ePublisher"
    path segment and taking the next segment as version.
    """
    if not exe_path:
        return None, None

    path = Path(exe_path)
    parts = path.parts
    lower_parts = [part.lower() for part in parts]

    if "epublisher" not in lower_parts:
        log_verbose(f"Path does not include ePublisher segment: {exe_path}", verbose)
        return None, None

    idx = lower_parts.index("epublisher")
    if idx + 1 >= len(parts):
        log_verbose(f"Path missing version segment after ePublisher: {exe_path}", verbose)
        return None, None

    version = parts[idx + 1]
    version_root = Path(*parts[:idx + 2])
    return version_root, version


def get_registry_versions(registry_path: str, verbose: bool) -> list[str]:
    if winreg is None:
        return []

    versions: list[str] = []
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, registry_path) as key:
            index = 0
            while True:
                try:
                    versions.append(winreg.EnumKey(key, index))
                    index += 1
                except OSError:
                    break
    except OSError:
        log_verbose(f"Registry path not found: HKLM\\{registry_path}", verbose)
        return []

    return versions


def get_registry_exe_path(registry_path: str, version: str, verbose: bool) -> Optional[str]:
    if winreg is None:
        return None

    version_key = f"{registry_path}\\{version}"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, version_key) as key:
            for value_name in EXE_VALUE_CANDIDATES:
                try:
                    value, _ = winreg.QueryValueEx(key, value_name)
                    if isinstance(value, str) and value.strip():
                        log_verbose(f"Read {value_name} from HKLM\\{version_key}", verbose)
                        return value.strip()
                except OSError:
                    continue
    except OSError:
        log_verbose(f"Registry version key missing: HKLM\\{version_key}", verbose)
        return None

    return None


def resolve_from_registry(requested_version: Optional[str], verbose: bool) -> tuple[Optional[Path], Optional[str], Optional[str]]:
    """
    Resolve VersionRoot from registry in precedence order:
    Designer keys first, then AutoMap keys.
    """
    if winreg is None:
        log_verbose("winreg unavailable; skipping registry detection", verbose)
        return None, None, None

    for source_name, registry_path in REGISTRY_SOURCES:
        versions = get_registry_versions(registry_path, verbose)
        if not versions:
            continue

        if requested_version:
            ordered_versions = [requested_version] if requested_version in versions else []
        else:
            ordered_versions = sorted(versions, key=parse_version_key, reverse=True)

        if not ordered_versions:
            continue

        for version in ordered_versions:
            exe_path = get_registry_exe_path(registry_path, version, verbose)
            if not exe_path:
                continue

            version_root, detected_version = derive_version_root_from_executable(exe_path, verbose)
            if not version_root or not detected_version:
                continue

            # If explicit version requested, enforce exact match.
            if requested_version and detected_version != requested_version:
                log_verbose(
                    f"Skipping registry candidate due to version mismatch: requested={requested_version}, detected={detected_version}",
                    verbose,
                )
                continue

            return version_root, detected_version, source_name

    return None, None, None


def resolve_from_automap_env(verbose: bool) -> tuple[Optional[Path], Optional[str], Optional[str]]:
    automap_exe_path = os.environ.get("AUTOMAP_EXE_PATH", "").strip()
    if not automap_exe_path:
        return None, None, None

    version_root, version = derive_version_root_from_executable(automap_exe_path, verbose)
    if not version_root or not version:
        log_verbose("AUTOMAP_EXE_PATH set but not mappable to VersionRoot", verbose)
        return None, None, None

    return version_root, version, "automap_env"


def _output_result(result: dict[str, object], path_only: bool) -> None:
    if path_only:
        print(result["versionRoot"])
    else:
        print(json.dumps(result, indent=2))


def build_result(version_root: Path, version: str, source: str) -> dict[str, object]:
    formats_dir = version_root / "Formats"
    adapters_dir = version_root / "Adapters"
    helpers_dir = version_root / "Helpers"

    return {
        "versionRoot": str(version_root),
        "version": version,
        "source": source,
        "formatsDir": str(formats_dir),
        "adaptersDir": str(adapters_dir),
        "helpersDir": str(helpers_dir),
        "hasFormats": formats_dir.is_dir(),
        "hasAdapters": adapters_dir.is_dir(),
        "hasHelpers": helpers_dir.is_dir(),
    }


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
        description="Resolve ePublisher VersionRoot (deterministic precedence: AUTOMAP_EXE_PATH, Designer registry, AutoMap registry).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Resolve using default precedence
    %(prog)s

    # Resolve for specific version
    %(prog)s --version 2024.1

    # Resolve version from project metadata
    %(prog)s --project-file project.wep

    # Return only path for shell usage
    %(prog)s --path-only
""",
    )

    parser.add_argument(
        "--version",
        help="Preferred ePublisher version (e.g., 2024.1). If provided, resolver tries this version first.",
    )
    parser.add_argument(
        "--project-file",
        help="Project file (.wep/.wrp/.wxsp). Base Format Version is extracted and used as requested version.",
    )
    parser.add_argument(
        "--path-only",
        action="store_true",
        help="Print only VersionRoot path on success.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose diagnostics on stderr.",
    )

    args = parser.parse_args()

    requested_version = args.version.strip() if args.version else None

    if args.project_file:
        project_version = extract_base_format_version(Path(args.project_file), args.verbose)
        if project_version is None:
            return EXIT_INVALID_ARGS
        requested_version = project_version
        log_verbose(f"Requested version from project: {requested_version}", args.verbose)

    # 1) AUTOMAP_EXE_PATH precedence
    version_root, detected_version, source = resolve_from_automap_env(args.verbose)
    if version_root and detected_version and source:
        if not requested_version or requested_version == detected_version:
            _output_result(build_result(version_root, detected_version, source), args.path_only)
            return EXIT_SUCCESS
        log_verbose(
            f"AUTOMAP_EXE_PATH version mismatch (requested={requested_version}, detected={detected_version}); continuing",
            args.verbose,
        )

    # 2) Designer registry, 3) AutoMap registry
    version_root, detected_version, source = resolve_from_registry(requested_version, args.verbose)
    if version_root and detected_version and source:
        _output_result(build_result(version_root, detected_version, source), args.path_only)
        return EXIT_SUCCESS

    if requested_version:
        log_error(f"Unable to resolve VersionRoot for version: {requested_version}")
    else:
        log_error("Unable to resolve VersionRoot (checked AUTOMAP_EXE_PATH, Designer registry, AutoMap registry)")
    return EXIT_NOT_FOUND


if __name__ == "__main__":
    sys.exit(main())
