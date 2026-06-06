#!/usr/bin/env python3
"""
audit-overrides.py

Audit the advanced customizations (overrides) in a WebWorks ePublisher project
against an installed format build, and surface UPSTREAM DRIFT so customizations
can be reconciled on upgrade.

Three subcommands:

    enumerate   List every override and classify it (forked-copy vs net-new).
    discover    "Sub-audit": fingerprint each forked-copy override against ALL
                installed ePublisher versions to find the most likely fork-point
                baseline, corroborated across companion files. Promotes an
                unknown-baseline (Mode B) project toward a known one (Mode A).
    audit       Full pass: lock state, classification, and per-file drift summary
                using the resolved-or-discovered baseline.

Key concepts (see issue quadralay/webworks-agent-skills#105):

  Lock state (FormatVersion):
    {Current}        -> project tracks ePublisher's version; auto-upgrade-safe
                        only when no advanced customizations are present.
    <specific ver>   -> project is LOCKED to that base format; no auto-upgrade.

  Reference-version availability:
    Mode A (3-way)   -> the fork-point base build is on disk; drift and
                        customization separate cleanly.
    Mode B (2-way)   -> fork-point base is gone (improper earlier upgrade, or a
                        patched/early-release build). Classification is inferred.

  Annotation test (primary disambiguator):
    An annotated divergence (e.g. EPUB#### / WEBWORKS marker) is an intentional
    customization. An UNANNOTATED divergence is probable drift -- positive
    (baseline added it, override lacks it) or negative (baseline removed it,
    override still carries it). Because users often fail to annotate their
    intentions, the `discover` sub-audit recovers the true fork-point so the
    override-vs-fork-point diff reveals those intentions regardless of markers.

This is a Phase-1 (report-only) prototype. It makes no writes to the project.
"""

import argparse
import difflib
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

try:
    import defusedxml.ElementTree as ET
except ImportError:  # pragma: no cover - fallback for minimal environments
    import xml.etree.ElementTree as ET  # type: ignore

DEFAULT_INSTALL_ROOT = Path(r"C:\Program Files\WebWorks\ePublisher")

# Default annotation markers. Projects annotate customizations differently;
# override/extend with --annotation-pattern. These two cover the design.wep
# fixture (a ticket-style marker and a house keyword).
DEFAULT_ANNOTATION_PATTERNS = [r"\bEPUB\d+\b", r"\bWEBWORKS\b"]

# Folders inside a project that hold overrides.
OVERRIDE_CONTAINERS = ("Formats", "Targets")

# SCSS/text extensions we treat as text for diffing/fingerprinting.
TEXT_SUFFIXES = {
    ".asp", ".xsl", ".scss", ".css", ".js", ".fti", ".xml", ".html",
    ".htm", ".json", ".txt", ".config", ".aspx", ".master",
}

EXIT_SUCCESS = 0
EXIT_NOT_FOUND = 1
EXIT_INVALID_ARGS = 2


# --------------------------------------------------------------------------- #
# Small helpers (intentionally inlined; factor into a shared lib/ when the
# skill graduates from prototype -- see issue #105 anatomy note).
# --------------------------------------------------------------------------- #
def version_key(version: str) -> tuple[int, ...]:
    """'2024.1' -> (2024, 1) for deterministic version sorting."""
    return tuple(int(part) for part in re.findall(r"\d+", version))


def local_name(tag: str) -> str:
    """Strip an XML namespace: '{urn:...}Format' -> 'Format'."""
    return tag.rsplit("}", 1)[-1]


def is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES


def read_lines(path: Path) -> list[str]:
    """Read a text file, normalizing line endings (CRLF/CR -> LF) so a pure
    line-ending difference does not read as a 100% change."""
    data = path.read_bytes()
    text = data.decode("utf-8", errors="replace")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.split("\n")


def similarity(a_lines: list[str], b_lines: list[str]) -> float:
    """Line-level similarity ratio in [0,1] (1.0 == identical)."""
    sm = difflib.SequenceMatcher(a=a_lines, b=b_lines, autojunk=False)
    return sm.ratio()


def diff_counts(base_lines: list[str], ovr_lines: list[str]) -> tuple[int, int]:
    """Return (added_in_override, removed_from_base) line counts."""
    added = removed = 0
    for line in difflib.unified_diff(base_lines, ovr_lines, n=0, lineterm=""):
        if line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            removed += 1
    return added, removed


# --------------------------------------------------------------------------- #
# Project model
# --------------------------------------------------------------------------- #
@dataclass
class ProjectInfo:
    path: Path
    runtime_version: str
    format_version: str          # raw attribute, e.g. "{Current}" or "2025.1"
    lock_state: str              # "tracking" | "locked"
    base_format_version: str     # effective version: RuntimeVersion if tracking
    target_to_format: dict[str, str] = field(default_factory=dict)
    format_names: list[str] = field(default_factory=list)


def parse_project(project_path: Path) -> ProjectInfo:
    root = ET.parse(str(project_path)).getroot()
    runtime = (root.get("RuntimeVersion") or "").strip()
    fmt = (root.get("FormatVersion") or "").strip()

    if not fmt or fmt == "{Current}":
        lock_state = "tracking"
        base = runtime
    else:
        lock_state = "locked"
        base = fmt

    target_to_format: dict[str, str] = {}
    format_names: list[str] = []
    for el in root.iter():
        if local_name(el.tag) != "Format":
            continue
        target_name = (el.get("TargetName") or "").strip()
        format_name = (el.get("Name") or "").strip()
        if target_name and format_name:
            target_to_format[target_name] = format_name
        if format_name and format_name not in format_names:
            format_names.append(format_name)

    return ProjectInfo(
        path=project_path,
        runtime_version=runtime,
        format_version=fmt or "{Current}",
        lock_state=lock_state,
        base_format_version=base,
        target_to_format=target_to_format,
        format_names=format_names,
    )


# --------------------------------------------------------------------------- #
# Override enumeration + classification
# --------------------------------------------------------------------------- #
@dataclass
class Override:
    abs_path: Path
    level: str          # "format" | "target"
    scope_name: str     # format name or target name
    format_name: str    # resolved format (== scope_name for level=format)
    rel_path: str       # path under the format structure, POSIX style
    is_text: bool
    classification: str = "unknown"   # "forked-copy" | "net-new"
    baseline_path: Optional[Path] = None


def enumerate_overrides(project: ProjectInfo) -> list[Override]:
    project_dir = project.path.parent
    overrides: list[Override] = []

    for container in OVERRIDE_CONTAINERS:
        base_dir = project_dir / container
        if not base_dir.is_dir():
            continue
        for scope_dir in sorted(base_dir.iterdir()):
            if not scope_dir.is_dir():
                continue
            scope_name = scope_dir.name
            # .base folders are packaged defaults (level 3), not customizations.
            if scope_name.endswith(".base"):
                continue
            if container == "Formats":
                level = "format"
                format_name = scope_name
            else:
                level = "target"
                format_name = project.target_to_format.get(scope_name, "")
            for f in sorted(scope_dir.rglob("*")):
                if not f.is_file():
                    continue
                rel = f.relative_to(scope_dir).as_posix()
                overrides.append(
                    Override(
                        abs_path=f,
                        level=level,
                        scope_name=scope_name,
                        format_name=format_name,
                        rel_path=rel,
                        is_text=is_text_file(f),
                    )
                )
    return overrides


def baseline_file_for(ov: Override, install_version_dir: Path) -> Optional[Path]:
    """Where this override's counterpart lives in an installed version."""
    if not ov.format_name:
        return None
    candidate = install_version_dir / "Formats" / ov.format_name / ov.rel_path
    return candidate


def classify_overrides(overrides: list[Override], baseline_root: Path) -> None:
    for ov in overrides:
        base = baseline_file_for(ov, baseline_root)
        if base and base.is_file():
            ov.classification = "forked-copy"
            ov.baseline_path = base
        else:
            ov.classification = "net-new"


# --------------------------------------------------------------------------- #
# Installed-version discovery
# --------------------------------------------------------------------------- #
def list_installed_versions(install_root: Path) -> list[str]:
    if not install_root.is_dir():
        return []
    versions = []
    for child in install_root.iterdir():
        if child.is_dir() and re.fullmatch(r"\d+(\.\d+)+", child.name):
            versions.append(child.name)
    return sorted(versions, key=version_key)


# --------------------------------------------------------------------------- #
# Sub-audit: fork-point fingerprinting
# --------------------------------------------------------------------------- #
@dataclass
class FileFingerprint:
    rel_path: str
    format_name: str
    override_lines: int
    per_version: dict[str, float]      # version -> similarity ratio
    best_version: Optional[str]
    best_ratio: float
    runner_up: Optional[str]
    runner_up_ratio: float


def fingerprint_file(ov: Override, install_root: Path, versions: list[str]) -> Optional[FileFingerprint]:
    if not ov.is_text:
        return None
    try:
        ovr_lines = read_lines(ov.abs_path)
    except OSError:
        return None

    per_version: dict[str, float] = {}
    for ver in versions:
        base_path = baseline_file_for(ov, install_root / ver)
        if not base_path or not base_path.is_file():
            continue
        try:
            base_lines = read_lines(base_path)
        except OSError:
            continue
        per_version[ver] = round(similarity(base_lines, ovr_lines), 6)

    if not per_version:
        return None

    ranked = sorted(per_version.items(), key=lambda kv: kv[1], reverse=True)
    best_version, best_ratio = ranked[0]
    runner_up, runner_up_ratio = (ranked[1] if len(ranked) > 1 else (None, 0.0))

    return FileFingerprint(
        rel_path=ov.rel_path,
        format_name=ov.format_name,
        override_lines=len(ovr_lines),
        per_version=per_version,
        best_version=best_version,
        best_ratio=round(best_ratio, 4),
        runner_up=runner_up,
        runner_up_ratio=round(runner_up_ratio, 4),
    )


def weighted_aggregate(fingerprints: list[FileFingerprint]) -> dict[str, float]:
    """Size-weighted similarity per version: sum(ratio*lines)/sum(lines)."""
    num: dict[str, float] = {}
    den: dict[str, float] = {}
    for fp in fingerprints:
        for ver, ratio in fp.per_version.items():
            num[ver] = num.get(ver, 0.0) + ratio * fp.override_lines
            den[ver] = den.get(ver, 0.0) + fp.override_lines
    return {ver: round(num[ver] / den[ver], 6) for ver in num if den.get(ver)}


def confidence_for(agreement: float, margin: float) -> str:
    if margin < 0.005:
        return "low"          # plateau: many versions tie -> indeterminate
    if agreement >= 0.75 and margin >= 0.02:
        return "high"
    if agreement >= 0.5 or margin >= 0.01:
        return "medium"
    return "low"


def releases_between(versions_sorted: list[str], lo: str, hi: str) -> int:
    """Count installed releases strictly after `lo` and up to/including `hi`."""
    klo, khi = version_key(lo), version_key(hi)
    return sum(1 for v in versions_sorted if klo < version_key(v) <= khi)


@dataclass
class FormatDiscovery:
    format_name: str
    retired: bool
    file_count: int
    best_version: Optional[str]
    best_score: float
    runner_up: Optional[str]
    runner_up_score: float
    margin: float
    agreement: float
    confidence: str
    locked_version: str
    staleness_releases: Optional[int]
    note: str


@dataclass
class DiscoveryResult:
    versions_considered: list[str]
    locked_version: str
    per_format: list[FormatDiscovery]
    overall_best: Optional[str]
    overall_score: float
    per_file: list[FileFingerprint]


def _discover_one(fingerprints: list[FileFingerprint], format_name: str,
                  retired: bool, locked: str, versions: list[str]) -> FormatDiscovery:
    agg = weighted_aggregate(fingerprints)
    ranked = sorted(agg.items(), key=lambda kv: kv[1], reverse=True)
    best, best_s = (ranked[0] if ranked else (None, 0.0))
    ru, ru_s = (ranked[1] if len(ranked) > 1 else (None, 0.0))
    margin = round(best_s - ru_s, 6)
    votes: dict[str, int] = {}
    for fp in fingerprints:
        if fp.best_version:
            votes[fp.best_version] = votes.get(fp.best_version, 0) + 1
    agreement = round(votes.get(best, 0) / len(fingerprints), 3) if fingerprints else 0.0
    confidence = confidence_for(agreement, margin)

    staleness: Optional[int] = None
    if retired:
        note = "retired format -> remove wholesale (see `cleanup`); fork-point not meaningful"
    elif best and locked:
        if version_key(best) < version_key(locked):
            staleness = releases_between(versions, best, locked)
            note = (f"fork-point {best} is {staleness} release(s) behind the project lock {locked} "
                    f"-> overrides were never re-synced to their own baseline")
        elif version_key(best) > version_key(locked):
            staleness = 0
            note = f"fork-point {best} is NEWER than the lock {locked} (heavy customization may skew this)"
        else:
            staleness = 0
            note = f"fork-point {best} matches the lock {locked} (current)"
        if confidence == "low":
            note += "  [low confidence: files match several versions near-equally]"
    else:
        note = "indeterminate"

    return FormatDiscovery(
        format_name=format_name, retired=retired, file_count=len(fingerprints),
        best_version=best, best_score=round(best_s, 4),
        runner_up=ru, runner_up_score=round(ru_s, 4), margin=round(margin, 4),
        agreement=agreement, confidence=confidence,
        locked_version=locked, staleness_releases=staleness, note=note)


def discover_baseline(overrides: list[Override], install_root: Path,
                      versions: list[str], project: ProjectInfo) -> DiscoveryResult:
    forked_text = [ov for ov in overrides
                   if ov.classification == "forked-copy" and ov.is_text]

    fingerprints: list[FileFingerprint] = []
    for ov in forked_text:
        fp = fingerprint_file(ov, install_root, versions)
        if fp is not None:
            fingerprints.append(fp)

    by_fmt: dict[str, list[FileFingerprint]] = {}
    for fp in fingerprints:
        by_fmt.setdefault(fp.format_name, []).append(fp)

    locked = project.base_format_version
    per_format = [
        _discover_one(items, fmt, is_retired_format(fmt), locked, versions)
        for fmt, items in sorted(by_fmt.items())
    ]

    overall = weighted_aggregate(fingerprints)
    ranked = sorted(overall.items(), key=lambda kv: kv[1], reverse=True)
    overall_best, overall_score = (ranked[0] if ranked else (None, 0.0))

    return DiscoveryResult(
        versions_considered=versions,
        locked_version=locked,
        per_format=per_format,
        overall_best=overall_best,
        overall_score=round(overall_score, 4),
        per_file=fingerprints,
    )


# --------------------------------------------------------------------------- #
# Annotation + drift (basic, uses a single baseline)
# --------------------------------------------------------------------------- #
def compile_annotation_patterns(patterns: list[str]) -> list[re.Pattern]:
    return [re.compile(p) for p in patterns]


def annotation_hits(lines: list[str], patterns: list[re.Pattern]) -> int:
    count = 0
    for line in lines:
        if any(p.search(line) for p in patterns):
            count += 1
    return count


@dataclass
class FileAudit:
    rel_path: str
    classification: str
    baseline_version: Optional[str]
    added_in_override: int
    removed_from_base: int
    annotated_override_lines: int
    note: str = ""


def audit_file(ov: Override, baseline_path: Optional[Path],
               baseline_version: Optional[str],
               ann_patterns: list[re.Pattern]) -> FileAudit:
    if ov.classification == "net-new" or baseline_path is None or not baseline_path.is_file():
        ovr_lines = read_lines(ov.abs_path) if ov.is_text else []
        return FileAudit(
            rel_path=ov.rel_path,
            classification=ov.classification,
            baseline_version=None,
            added_in_override=len(ovr_lines),
            removed_from_base=0,
            annotated_override_lines=annotation_hits(ovr_lines, ann_patterns) if ov.is_text else 0,
            note="net-new (no baseline counterpart); verify referenced hooks still exist",
        )

    base_lines = read_lines(baseline_path)
    ovr_lines = read_lines(ov.abs_path)
    added, removed = diff_counts(base_lines, ovr_lines)
    ann = annotation_hits(ovr_lines, ann_patterns)
    notes = []
    if removed >= 25 and removed > added:
        notes.append("baseline has many lines absent from override -> POSITIVE DRIFT suspect "
                     "(base added since fork, or override deleted); confirm via discover + 3-way")
    if added and ann == 0:
        notes.append("override-only changes are UNANNOTATED -> run `discover` and diff vs fork-point to recover intent")
    note = "; ".join(notes)
    return FileAudit(
        rel_path=ov.rel_path,
        classification=ov.classification,
        baseline_version=baseline_version,
        added_in_override=added,
        removed_from_base=removed,
        annotated_override_lines=ann,
        note=note,
    )


# --------------------------------------------------------------------------- #
# Static checks (issue #105 "C"): SCSS variables + prefix convention,
# custom-partial wiring, dangling references (negative drift).
# --------------------------------------------------------------------------- #
SCSS_VAR_DEF = re.compile(r"^\s*(\$[A-Za-z0-9_-]+)\s*:\s*(.*?)\s*(?:!default\s*)?;", re.MULTILINE)
SCSS_IMPORT = re.compile(r'@(?:import|use)\s+["\']([^"\']+)["\']')
SCSS_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
SCSS_LINE_COMMENT = re.compile(r"//[^\n]*")
# Reverb setting/trait reference inside an ASP/HTML/XSL template.
WWPAGE_ATTR_REF = re.compile(r'wwpage:attribute-[A-Za-z0-9-]+="([^"]+)"')
FTI_NAME_DEF = re.compile(r'name="([^"]+)"')

# Canonical custom-variable prefix (reverb2 skill). Projects substitute their
# own company abbreviation (e.g. webworks_, dicad_); we auto-detect it rather
# than assume. This is only the default seed for reporting.
CANONICAL_PREFIX = "theme"


def parse_scss_vars(path: Path) -> dict[str, str]:
    """Map $name -> value-string for top-level variable definitions."""
    try:
        text = "\n".join(read_lines(path))
    except OSError:
        return {}
    out: dict[str, str] = {}
    for m in SCSS_VAR_DEF.finditer(text):
        out[m.group(1)] = m.group(2).split("//")[0].strip()
    return out


def prefix_of(var_name: str) -> str:
    """'$theme_primary' -> 'theme'; '$foo' -> 'foo'."""
    stem = var_name.lstrip("$")
    return stem.split("_", 1)[0] if "_" in stem else stem


def strip_scss_comments(text: str) -> str:
    """Drop /* */ and // comments so commented-out code (e.g. an @import in a
    file header that documents the wiring step) is not mistaken for real code."""
    text = SCSS_BLOCK_COMMENT.sub("", text)
    text = SCSS_LINE_COMMENT.sub("", text)
    return text


@dataclass
class ScssAnalysis:
    rel_path: str
    baseline_present: bool
    missing_vars: list[str]          # in baseline, absent from override -> build-break risk
    added_vars: list[str]            # in override, absent from baseline -> customization
    changed_vars: list[str]          # same name, different value -> customization
    added_prefixes: dict[str, int]   # prefix histogram of added vars
    annotation_hits: int


def analyze_scss(ov: Override, baseline_path: Optional[Path],
                 ann_patterns: list[re.Pattern]) -> ScssAnalysis:
    ovr_vars = parse_scss_vars(ov.abs_path)
    base_vars = parse_scss_vars(baseline_path) if (baseline_path and baseline_path.is_file()) else {}
    base_present = bool(base_vars)

    missing = sorted(set(base_vars) - set(ovr_vars))
    added = sorted(set(ovr_vars) - set(base_vars))
    changed = sorted(n for n in (set(ovr_vars) & set(base_vars)) if ovr_vars[n] != base_vars[n])

    hist: dict[str, int] = {}
    for name in added:
        p = prefix_of(name)
        hist[p] = hist.get(p, 0) + 1

    return ScssAnalysis(
        rel_path=ov.rel_path,
        baseline_present=base_present,
        missing_vars=missing,
        added_vars=added,
        changed_vars=changed,
        added_prefixes=hist,
        annotation_hits=annotation_hits(read_lines(ov.abs_path), ann_patterns),
    )


def detect_project_prefix(analyses: list[ScssAnalysis],
                          declared: Optional[list[str]]) -> tuple[Optional[str], dict[str, int]]:
    """Aggregate added-var prefixes across all SCSS overrides to find the
    project's de-facto custom-variable convention. Standard Reverb variables
    are never in the added set, so the dominant prefix here is the real one."""
    agg: dict[str, int] = {}
    for a in analyses:
        for p, n in a.added_prefixes.items():
            agg[p] = agg.get(p, 0) + n
    if declared:
        # Honor an explicitly-declared prefix if it appears at all.
        for d in declared:
            d = d.rstrip("_")
            if d in agg:
                return d, agg
        return declared[0].rstrip("_"), agg
    if not agg:
        return None, agg
    best = max(agg.items(), key=lambda kv: kv[1])
    return best[0], agg


@dataclass
class WiringFinding:
    partial: str            # e.g. "_custom-webworks.scss"
    import_name: str        # e.g. "custom-webworks"
    wired: bool
    imported_by: Optional[str]
    reason: str


# Conventional entry point for the two skill-template partials.
PARTIAL_ENTRY_POINT = {
    "custom-skin": "skin.scss",
    "custom-webworks": "webworks.scss",
}


def check_partial_wiring(overrides: list[Override]) -> list[WiringFinding]:
    """Net-new SCSS partials take effect only if an OVERRIDE entry point
    @imports them (the base entry points can't know about a net-new partial)."""
    sass_overrides = [o for o in overrides if o.rel_path.endswith(".scss")]
    overridden_files = {Path(o.rel_path).name for o in sass_overrides}

    # Collect every partial imported by an override .scss file (ignoring
    # comments, and ignoring a file that "imports" itself).
    imported: dict[str, str] = {}     # import_name -> importing file
    for o in sass_overrides:
        text = strip_scss_comments("\n".join(read_lines(o.abs_path)))
        importer = Path(o.rel_path).name
        self_name = importer[1:-5] if importer.startswith("_") and importer.endswith(".scss") else None
        for m in SCSS_IMPORT.finditer(text):
            name = Path(m.group(1)).name.lstrip("_")
            if name.endswith(".scss"):
                name = name[:-5]
            if name == self_name:
                continue
            imported[name] = importer

    findings: list[WiringFinding] = []
    for o in sass_overrides:
        fname = Path(o.rel_path).name
        if not fname.startswith("_"):
            continue
        if o.classification != "net-new":
            continue  # standard partials are imported by base entry points
        import_name = fname[1:-5] if fname.endswith(".scss") else fname[1:]
        if import_name in imported:
            findings.append(WiringFinding(fname, import_name, True, imported[import_name], "imported by an override entry point"))
        else:
            entry = PARTIAL_ENTRY_POINT.get(import_name)
            if entry and entry not in overridden_files:
                reason = (f"no override imports it; its conventional entry point '{entry}' "
                          f"is not in the override set -> INCOMPLETE TEMPLATE (takes no effect)")
            else:
                reason = "no override @import found -> dead partial (takes no effect)"
            findings.append(WiringFinding(fname, import_name, False, None, reason))
    return findings


@dataclass
class DanglingFinding:
    setting: str
    referenced_in: list[str]
    annotated: bool
    verdict: str            # "negative-drift" | "undefined-custom"


def build_baseline_corpus(baseline_root: Optional[Path], format_name: str,
                          overrides: list[Override]) -> str:
    parts: list[str] = []
    if baseline_root and format_name:
        fmt_dir = baseline_root / "Formats" / format_name
        if fmt_dir.is_dir():
            for f in fmt_dir.rglob("*"):
                if f.is_file() and is_text_file(f):
                    try:
                        parts.append(f.read_text(encoding="utf-8", errors="replace"))
                    except OSError:
                        continue
    # Include override-defined traits (e.g. a custom pages.fti option).
    for o in overrides:
        if o.rel_path.endswith(".fti"):
            parts.append("\n".join(read_lines(o.abs_path)))
    return "\n".join(parts)


def check_dangling_references(overrides: list[Override], baseline_root: Optional[Path],
                              format_name: str, ann_patterns: list[re.Pattern]) -> list[DanglingFinding]:
    corpus = build_baseline_corpus(baseline_root, format_name, overrides)
    refs: dict[str, list[str]] = {}
    ref_annotated: dict[str, bool] = {}
    for o in overrides:
        if Path(o.rel_path).suffix.lower() not in (".asp", ".html", ".htm", ".xsl"):
            continue
        lines = read_lines(o.abs_path)
        for line in lines:
            for m in WWPAGE_ATTR_REF.finditer(line):
                val = m.group(1)
                refs.setdefault(val, [])
                if o.rel_path not in refs[val]:
                    refs[val].append(o.rel_path)
                if any(p.search(line) for p in ann_patterns):
                    ref_annotated[val] = True

    findings: list[DanglingFinding] = []
    for val, where in sorted(refs.items()):
        # Defined or used anywhere in the baseline (covers built-in resolvers
        # and standard settings) or in an override-defined trait? Then fine.
        if val in corpus:
            continue
        annotated = ref_annotated.get(val, False)
        verdict = "undefined-custom" if annotated else "negative-drift"
        findings.append(DanglingFinding(val, where, annotated, verdict))
    return findings


# --------------------------------------------------------------------------- #
# Removal recommendations (issue #105): retired formats, orphaned overrides,
# and cruft/duplicate files. Aggressive by design -- migration step 1 is a
# baseline commit/copy, so the original state is always recoverable.
# --------------------------------------------------------------------------- #
# Formats no longer supported. Their overrides should be removed wholesale;
# computing drift for them is not useful. (Maintained list.)
RETIRED_FORMATS = {
    "WebWorks Help 5.0",
    "WebWorks Help",
    "WebWorks Reverb",        # Reverb 1.x (Reverb 2.0 is current)
    "WebWorks Help 4.0",
    "WebWorks Help 3.0",
}

# Format versions older than this are End-Of-Life (installable via the optional
# EOL installer, but users are encouraged to move forward). Bumps to 2023.1
# when 2026.1 ships.
EOL_BEFORE_VERSION = "2022.1"

# Filename signals of a backup/experiment/duplicate copy.
CRUFT_NAME_PATTERNS = [
    re.compile(r"orig", re.I),
    re.compile(r"_old\b|_old[._]", re.I),
    re.compile(r"_original", re.I),
    re.compile(r"backup|bak\b", re.I),
    re.compile(r"\bcopy\b|_copy", re.I),
    re.compile(r"with_version", re.I),
    re.compile(r"\bgood[_A-Z]", re.I),
    re.compile(r"blurry", re.I),
    re.compile(r"_x{1,2}\.|_xx\b", re.I),
    re.compile(r"\d{4,}"),          # date-stamped: 0728, 071618, 10_31_18
    re.compile(r"\bNG[A-Z]"),       # NGPage.asp -> "next-gen" experiment
]

# Filenames an override might reference (assets/sources to protect from cruft).
REF_FILE = re.compile(r'''["'\(]([^"'\)\s]+\.(?:gif|jpe?g|png|svg|ico|js|css|scss|asp|html?|xml|json))["'\)]''', re.I)


def is_retired_format(format_name: str) -> bool:
    return format_name in RETIRED_FORMATS


def build_reference_set(overrides: list[Override], project: ProjectInfo) -> set[str]:
    """Basenames + SCSS import names referenced by any override template/style,
    PLUS asset filenames referenced in the project file's settings (logo/splash
    paths live there, not in templates). A file appearing here is intentional
    source, never cruft."""
    refs: set[str] = set()

    def harvest(text: str, scss: bool = False) -> None:
        for m in REF_FILE.finditer(text):
            refs.add(Path(m.group(1)).name.lower())
        if scss:
            for m in SCSS_IMPORT.finditer(strip_scss_comments(text)):
                base = Path(m.group(1)).name.lstrip("_")
                base_noext = base[:-5] if base.endswith(".scss") else base
                refs.add(base.lower())
                refs.add(f"_{base_noext}.scss".lower())
                refs.add(f"{base_noext}.scss".lower())

    for o in overrides:
        suf = Path(o.rel_path).suffix.lower()
        if suf not in (".asp", ".html", ".htm", ".xsl", ".scss", ".css", ".js"):
            continue
        harvest("\n".join(read_lines(o.abs_path)), scss=(suf == ".scss"))

    # Project file: logo/splash/asset paths configured in FormatSettings.
    try:
        harvest(project.path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        pass
    return refs


def _stem(name: str) -> str:
    return Path(name).stem.lstrip("_").lower()


CRUFT_PREFIX_AFFIXES = ("orig_", "good_", "old_", "backup_", "copy_", "ng")
CRUFT_SUFFIX_AFFIXES = ("_orig", "_original", "_old", "_copy", "_backup", "_with_version", "_x", "_xx")


def _strip_cruft_affixes(stem: str) -> set[str]:
    """Yield plausible 'real' stems by removing backup/experiment decoration."""
    cands = {stem,
             re.sub(r"[_-]?\d+$", "", stem),   # trailing date/number: page071618 -> page
             re.sub(r"\d+", "", stem)}         # embedded digits: 071618page -> page
    for c in list(cands):
        for p in CRUFT_PREFIX_AFFIXES:
            if c.startswith(p) and len(c) > len(p):
                cands.add(c[len(p):])
        for s in CRUFT_SUFFIX_AFFIXES:
            if c.endswith(s) and len(c) > len(s):
                cands.add(c[:-len(s)])
    cands.discard(stem)
    return {c for c in cands if c}


def looks_like_variant(name: str, sibling_names: list[str]) -> Optional[str]:
    """If `name` is a decorated variant of a sibling override, return that
    sibling. Uses affix-stripping (precise) then prefix+separator (catches
    dated variants like splash_Cohu2019.gif of splash.gif). Avoids loose
    substring matches that would treat CohuStandardColorLogo as 'logo'."""
    s = _stem(name)
    sib_stems = {sib: _stem(sib) for sib in sibling_names if sib != name and _stem(sib)}
    # 1) affix-stripped equality with an existing sibling
    stripped_forms = _strip_cruft_affixes(s)
    for sib, ss in sib_stems.items():
        if ss != s and ss in stripped_forms:
            return sib
    # 2) prefix + separator (decorated longer form of a shorter sibling)
    for sib, ss in sib_stems.items():
        if len(ss) >= 4 and s != ss and s.startswith(ss) and len(s) > len(ss) and s[len(ss)] in "_-.0123456789":
            return sib
    return None


@dataclass
class RemovalFinding:
    kind: str               # "scope" | "file"
    target: str             # scope dir or file rel path
    category: str           # "retired-format" | "orphan-target" | "orphan-format" | "duplicate-backup"
    reason: str
    confidence: str         # "high" | "medium"
    file_count: int = 1


def detect_removals(overrides: list[Override], project: ProjectInfo) -> list[RemovalFinding]:
    findings: list[RemovalFinding] = []
    ref_set = build_reference_set(overrides, project)

    # Group overrides by (level, scope) for scope-level findings + sibling lists.
    by_scope: dict[tuple[str, str], list[Override]] = {}
    for o in overrides:
        by_scope.setdefault((o.level, o.scope_name), []).append(o)

    retired_scopes: set[tuple[str, str]] = set()
    orphan_scopes: set[tuple[str, str]] = set()

    for (level, scope), items in by_scope.items():
        fmt = items[0].format_name
        # Retired format (format-level dir, or any target bound to a retired format).
        if is_retired_format(scope if level == "format" else fmt):
            retired_scopes.add((level, scope))
            findings.append(RemovalFinding(
                kind="scope", target=f"{level.capitalize()}s/{scope}",
                category="retired-format",
                reason=f"format '{fmt or scope}' is retired -> remove overrides wholesale (no drift analysis)",
                confidence="high", file_count=len(items)))
            continue
        # Orphaned target (no matching target in the project).
        if level == "target" and scope not in project.target_to_format:
            orphan_scopes.add((level, scope))
            findings.append(RemovalFinding(
                kind="scope", target=f"Targets/{scope}", category="orphan-target",
                reason="no target with this name exists in the project -> orphaned override",
                confidence="high", file_count=len(items)))
            continue
        # Orphaned format-level dir (format used by no target; 'Shared' is special).
        if level == "format" and scope != "Shared" and scope not in project.format_names:
            orphan_scopes.add((level, scope))
            findings.append(RemovalFinding(
                kind="scope", target=f"Formats/{scope}", category="orphan-format",
                reason="no target uses this format -> orphaned override",
                confidence="high", file_count=len(items)))

    # Cruft/duplicate files (skip scopes already slated for wholesale removal).
    for (level, scope), items in by_scope.items():
        if (level, scope) in retired_scopes or (level, scope) in orphan_scopes:
            continue
        # Sibling basenames per directory within this scope.
        dir_files: dict[str, list[str]] = {}
        for o in items:
            d = str(Path(o.rel_path).parent)
            dir_files.setdefault(d, []).append(Path(o.rel_path).name)
        for o in items:
            if o.classification != "net-new":
                continue
            name = Path(o.rel_path).name
            if name.lower() in ref_set:
                continue  # referenced source -> protect
            siblings = dir_files.get(str(Path(o.rel_path).parent), [])
            variant_of = looks_like_variant(name, siblings)
            name_cruft = any(p.search(name) for p in CRUFT_NAME_PATTERNS)
            if variant_of and name_cruft:
                conf, why = "high", f"backup/experiment name and duplicates existing override '{variant_of}'"
            elif variant_of:
                conf, why = "high", f"duplicates existing override '{variant_of}' (unreferenced)"
            elif name_cruft:
                conf, why = "medium", "backup/experiment filename, unreferenced by any override"
            else:
                continue
            findings.append(RemovalFinding(
                kind="file", target=f"{level.capitalize()}s/{scope}/{o.rel_path}",
                category="duplicate-backup", reason=why, confidence=conf))

    # Redundant overrides: a forked-copy identical to its baseline. Often a local
    # patch that has since been fixed upstream -> the override no longer does
    # anything but add maintenance noise.
    for (level, scope), items in by_scope.items():
        if (level, scope) in retired_scopes or (level, scope) in orphan_scopes:
            continue
        for o in items:
            if o.classification != "forked-copy" or not o.baseline_path or not o.baseline_path.is_file():
                continue
            try:
                if o.is_text:
                    same = read_lines(o.abs_path) == read_lines(o.baseline_path)
                else:
                    same = o.abs_path.read_bytes() == o.baseline_path.read_bytes()
            except OSError:
                continue
            if same:
                findings.append(RemovalFinding(
                    kind="file", target=f"{level.capitalize()}s/{scope}/{o.rel_path}",
                    category="redundant-override",
                    reason="identical to the baseline (local patch now fixed upstream, or never changed) -> remove to reduce noise",
                    confidence="high"))
    return findings


# --------------------------------------------------------------------------- #
# 3-way drift classifier (issue #105 "A"): base-old (fork-point / locked
# version) -> base-new (upgrade target) -> override. Separates the user's
# customizations from upstream drift and flags merge conflicts.
# --------------------------------------------------------------------------- #
@dataclass
class ThreeWayResult:
    location: str            # Targets/<name>/... or Formats/<name>/... (disambiguates)
    rel_path: str
    format_name: str
    upstream_change: int     # lines changed base_old -> base_new (the drift)
    customization: int       # lines changed base_old -> override (user intent)
    conflict_regions: int    # customized regions that upstream also changed
    verdict: str
    note: str = ""


def _changed_intervals(a: list[str], b: list[str]) -> list[tuple[int, int]]:
    """Intervals in `a`'s index space that differ in `b`."""
    ivs: list[tuple[int, int]] = []
    for tag, i1, i2, _j1, _j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        ivs.append((i1, i2) if i2 > i1 else (i1, i1 + 1))  # widen pure inserts
    return ivs


def _changed_size(a: list[str], b: list[str]) -> int:
    n = 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag != "equal":
            n += (i2 - i1) + (j2 - j1)
    return n


def _overlap_count(a_ivs: list[tuple[int, int]], b_ivs: list[tuple[int, int]]) -> int:
    count = 0
    for a1, a2 in a_ivs:
        if any(a1 < b2 and b1 < a2 for b1, b2 in b_ivs):
            count += 1
    return count


def analyze_3way(location: str, rel_path: str, format_name: str,
                 base_old: list[str], base_new: list[str], ovr: list[str]) -> ThreeWayResult:
    upstream = _changed_size(base_old, base_new)
    custom = _changed_size(base_old, ovr)
    cust_ivs = _changed_intervals(base_old, ovr)
    up_ivs = _changed_intervals(base_old, base_new)
    conflicts = _overlap_count(cust_ivs, up_ivs)

    if upstream == 0 and custom == 0:
        verdict, note = "redundant", "identical to baseline (no upstream change, no customization); safe to remove"
    elif upstream == 0:
        verdict, note = "in-sync", "no upstream change between the two versions; customizations carry forward as-is"
    elif custom == 0:
        verdict, note = "fast-forward", "override is an unmodified copy; adopt the new baseline (or drop the override)"
    elif conflicts == 0:
        verdict, note = "auto-mergeable", "customizations and upstream changes touch disjoint regions"
    else:
        verdict, note = "manual-merge", f"{conflicts} customized region(s) also changed upstream -> review"
    return ThreeWayResult(location, rel_path, format_name, upstream, custom, conflicts, verdict, note)


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #
def emit_json(obj) -> None:
    def default(o):
        if isinstance(o, Path):
            return str(o)
        if hasattr(o, "__dataclass_fields__"):
            return asdict(o)
        raise TypeError(repr(o))
    print(json.dumps(obj, indent=2, default=default))


# --------------------------------------------------------------------------- #
# Subcommands
# --------------------------------------------------------------------------- #
def resolve_baseline_root(project: ProjectInfo, install_root: Path,
                          override_version: Optional[str]) -> tuple[Optional[Path], Optional[str]]:
    ver = override_version or project.base_format_version
    root = install_root / ver
    if root.is_dir():
        return root, ver
    return None, ver


def cmd_enumerate(args) -> int:
    project = parse_project(Path(args.project))
    install_root = Path(args.install_root)
    baseline_root, baseline_ver = resolve_baseline_root(project, install_root, args.baseline_version)
    overrides = enumerate_overrides(project)
    if baseline_root:
        classify_overrides(overrides, baseline_root)

    if args.format == "json":
        emit_json({
            "project": project,
            "baselineVersion": baseline_ver,
            "baselineAvailable": baseline_root is not None,
            "overrides": overrides,
        })
        return EXIT_SUCCESS

    forked = [o for o in overrides if o.classification == "forked-copy"]
    netnew = [o for o in overrides if o.classification == "net-new"]
    unknown = [o for o in overrides if o.classification == "unknown"]
    print(f"Project: {project.path.name}")
    print(f"  Lock state : {project.lock_state}  (RuntimeVersion={project.runtime_version}, FormatVersion={project.format_version})")
    print(f"  Base format: {project.base_format_version}")
    print(f"  Baseline   : {baseline_ver} ({'available' if baseline_root else 'NOT on disk -> Mode B'})")
    print(f"  Overrides  : {len(overrides)} total | {len(forked)} forked-copy | {len(netnew)} net-new"
          + (f" | {len(unknown)} unclassified" if unknown else ""))
    print()
    print(f"  {'CLASS':<12} {'LEVEL':<7} {'REL PATH'}")
    print(f"  {'-'*12} {'-'*7} {'-'*40}")
    for o in overrides:
        print(f"  {o.classification:<12} {o.level:<7} {o.format_name}/{o.rel_path}")
    return EXIT_SUCCESS


def cmd_discover(args) -> int:
    project = parse_project(Path(args.project))
    install_root = Path(args.install_root)
    versions = list_installed_versions(install_root)
    if not versions:
        print(f"No installed versions found under {install_root}", file=sys.stderr)
        return EXIT_NOT_FOUND

    # classify against the newest installed version so we know which files are
    # forked-copies worth fingerprinting.
    newest = install_root / versions[-1]
    overrides = enumerate_overrides(project)
    classify_overrides(overrides, newest)

    result = discover_baseline(overrides, install_root, versions, project)

    if args.format == "json":
        emit_json(result)
        return EXIT_SUCCESS

    print(f"Fork-point discovery for {project.path.name}   (project lock: {result.locked_version})")
    print(f"  {len(result.versions_considered)} installed versions considered "
          f"({result.versions_considered[0]} .. {result.versions_considered[-1]})")
    print(f"  Overall project fork-point: {result.overall_best} (score={result.overall_score})")
    print()
    print("  Per-format fork-point + staleness vs the project lock:")
    print(f"    {'FORK-POINT':<11} {'SCORE':<7} {'CONF':<7} {'FILES':>5}  {'FORMAT'}")
    print(f"    {'-'*11} {'-'*7} {'-'*7} {'-'*5}  {'-'*30}")
    for fd in sorted(result.per_format, key=lambda f: f.format_name):
        fp_disp = "RETIRED" if fd.retired else str(fd.best_version)
        score = "-" if fd.retired else f"{fd.best_score}"
        print(f"    {fp_disp:<11} {score:<7} {fd.confidence:<7} {fd.file_count:>5}  {fd.format_name}")
        print(f"        -> {fd.note}")
    print()
    print("  Lowest per-file ratios (most customized or most drifted):")
    print(f"    {'BEST':<8} {'RATIO':<7}  {'FILE'}")
    print(f"    {'-'*8} {'-'*7}  {'-'*40}")
    for fp in sorted(result.per_file, key=lambda f: f.best_ratio)[:12]:
        print(f"    {str(fp.best_version):<8} {fp.best_ratio:<7}  {fp.format_name}/{fp.rel_path}")
    return EXIT_SUCCESS


def cmd_audit(args) -> int:
    project = parse_project(Path(args.project))
    install_root = Path(args.install_root)
    baseline_root, baseline_ver = resolve_baseline_root(project, install_root, args.baseline_version)
    overrides = enumerate_overrides(project)
    if not baseline_root:
        print(f"Baseline {baseline_ver} not on disk; classifying against newest installed.", file=sys.stderr)
        versions = list_installed_versions(install_root)
        if versions:
            baseline_root = install_root / versions[-1]
            baseline_ver = versions[-1]
    if baseline_root:
        classify_overrides(overrides, baseline_root)

    ann_patterns = compile_annotation_patterns(args.annotation_pattern or DEFAULT_ANNOTATION_PATTERNS)
    audits = [
        audit_file(ov, ov.baseline_path, baseline_ver if ov.classification == "forked-copy" else None, ann_patterns)
        for ov in overrides
    ]

    # --- Static checks (C) ---
    format_name = next((o.format_name for o in overrides if o.format_name), "")
    scss_overrides = [o for o in overrides if o.rel_path.endswith(".scss")]
    scss_analyses = [analyze_scss(o, o.baseline_path, ann_patterns) for o in scss_overrides]
    project_prefix, prefix_hist = detect_project_prefix(
        scss_analyses, [p.rstrip("_") for p in (args.theme_prefix or [])] or None)
    wiring = check_partial_wiring(overrides)
    dangling = check_dangling_references(overrides, baseline_root, format_name, ann_patterns)

    # Pair each SCSS analysis with its override for prefix-coverage reporting.
    scss_by_path = {o.rel_path: a for o, a in zip(scss_overrides, scss_analyses)}

    if args.format == "json":
        emit_json({
            "project": project,
            "baselineVersion": baseline_ver,
            "modeNote": "2-way vs installed baseline; run `discover` for fork-point (Mode B promotion)",
            "files": audits,
            "scss": {
                "detectedProjectPrefix": project_prefix,
                "addedPrefixHistogram": prefix_hist,
                "perFile": scss_analyses,
            },
            "partialWiring": wiring,
            "danglingReferences": dangling,
        })
        return EXIT_SUCCESS

    print(f"Audit: {project.path.name}  (lock={project.lock_state}, baseline={baseline_ver})")
    print()
    print(f"  {'CLASS':<12} {'+OVR':>5} {'-BASE':>6} {'ANNOT':>6}  {'FILE'}")
    print(f"  {'-'*12} {'-'*5} {'-'*6} {'-'*6}  {'-'*40}")
    for a in audits:
        print(f"  {a.classification:<12} {a.added_in_override:>5} {a.removed_from_base:>6} "
              f"{a.annotated_override_lines:>6}  {a.rel_path}")
        if a.note:
            print(f"               -> {a.note}")

    # --- SCSS variables + prefix convention ---
    print()
    print("SCSS variables & custom-prefix convention")
    if project_prefix:
        canon = " (canonical)" if project_prefix == CANONICAL_PREFIX else " (project-specific)"
        print(f"  Detected custom-variable prefix: ${project_prefix}_*{canon}   "
              f"[added-var prefixes: " + ", ".join(f"{p}:{n}" for p, n in sorted(prefix_hist.items(), key=lambda kv: -kv[1])) + "]")
        print(f"  -> grep '\\${project_prefix}_' finds every custom variable without relying on comments")
    else:
        print("  No custom variables added by any SCSS override (variable-value overrides only).")
    print()
    print(f"  {'+VARS':>6} {'~VALS':>6} {'!MISSING':>8} {'OFF-PREFIX':>10}  {'FILE'}")
    print(f"  {'-'*6} {'-'*6} {'-'*8} {'-'*10}  {'-'*32}")
    for a in scss_analyses:
        off = [v for v in a.added_vars if prefix_of(v) != project_prefix] if project_prefix else []
        print(f"  {len(a.added_vars):>6} {len(a.changed_vars):>6} {len(a.missing_vars):>8} {len(off):>10}  {a.rel_path}")
        if a.missing_vars:
            shown = ", ".join(a.missing_vars[:6]) + (" ..." if len(a.missing_vars) > 6 else "")
            print(f"      !! BUILD-BREAK RISK -- baseline vars absent from override: {shown}")
        if off:
            shown = ", ".join(off[:6]) + (" ..." if len(off) > 6 else "")
            print(f"      ~  custom vars outside ${project_prefix}_ (less greppable): {shown}")

    # --- Custom-partial wiring ---
    print()
    print("Custom-partial wiring (net-new SCSS partials)")
    if not wiring:
        print("  No net-new SCSS partials.")
    for w in wiring:
        mark = "OK " if w.wired else "XX "
        print(f"  {mark} {w.partial}: {w.reason}" + (f" [{w.imported_by}]" if w.imported_by else ""))

    # --- Dangling references (negative drift) ---
    print()
    print("Dangling references (negative-drift / undefined-custom detector)")
    if not dangling:
        print("  None -- every wwpage:attribute binding resolves against the baseline or an override trait.")
    for d in dangling:
        tag = "NEGATIVE DRIFT" if d.verdict == "negative-drift" else "UNDEFINED CUSTOM"
        print(f"  [{tag}] '{d.setting}' referenced in {', '.join(d.referenced_in)} "
              f"but defined nowhere in baseline/override"
              + ("" if d.annotated else "  (unannotated -> likely obsolete code removed upstream)"))
    return EXIT_SUCCESS


def cmd_cleanup(args) -> int:
    project = parse_project(Path(args.project))
    install_root = Path(args.install_root)
    baseline_root, baseline_ver = resolve_baseline_root(project, install_root, args.baseline_version)
    overrides = enumerate_overrides(project)
    classify_root = baseline_root
    if not classify_root:
        versions = list_installed_versions(install_root)
        classify_root = (install_root / versions[-1]) if versions else None
    if classify_root:
        classify_overrides(overrides, classify_root)

    findings = detect_removals(overrides, project)
    total_files = len(overrides)
    removable_files = sum(f.file_count for f in findings)

    if args.format == "json":
        emit_json({
            "project": project,
            "baselineVersion": baseline_ver,
            "overrideFileCount": total_files,
            "removableFileCount": removable_files,
            "findings": findings,
        })
        return EXIT_SUCCESS

    cats = {
        "retired-format": "Retired formats (remove wholesale)",
        "orphan-target": "Orphaned targets (no matching target in project)",
        "orphan-format": "Orphaned formats (used by no target)",
        "duplicate-backup": "Duplicate / backup / experiment files",
        "redundant-override": "Redundant overrides (identical to baseline)",
    }
    print(f"Cleanup recommendations: {project.path.name}  (lock={project.lock_state}, base={baseline_ver})")
    print(f"  {removable_files} of {total_files} override files recommended for removal.")
    print("  (Safe to be aggressive: migration step 1 is a baseline commit/copy.)")
    for cat, title in cats.items():
        group = [f for f in findings if f.category == cat]
        if not group:
            continue
        n = sum(f.file_count for f in group)
        print()
        print(f"  {title}  [{n} file(s)]")
        for f in group:
            scope = " (whole dir)" if f.kind == "scope" else ""
            print(f"    - {f.target}{scope}  [{f.confidence}]")
            print(f"        {f.reason}")
    if not findings:
        print("  Nothing to remove -- override tree is clean.")
    return EXIT_SUCCESS


def cmd_drift(args) -> int:
    project = parse_project(Path(args.project))
    install_root = Path(args.install_root)
    from_ver = args.from_version or project.base_format_version
    to_ver = args.to_version
    from_root = install_root / from_ver
    to_root = install_root / to_ver
    if not from_root.is_dir():
        print(f"[ERROR] from-version baseline not installed: {from_root}", file=sys.stderr)
        return EXIT_NOT_FOUND
    if not to_root.is_dir():
        print(f"[ERROR] to-version baseline not installed: {to_root}", file=sys.stderr)
        return EXIT_NOT_FOUND

    overrides = enumerate_overrides(project)
    classify_overrides(overrides, from_root)

    results: list[ThreeWayResult] = []
    skipped_retired = 0
    dropped_upstream: list[str] = []
    for ov in overrides:
        if not ov.is_text or ov.classification != "forked-copy":
            continue
        if is_retired_format(ov.format_name):
            skipped_retired += 1
            continue
        base_old_file = baseline_file_for(ov, from_root)
        base_new_file = baseline_file_for(ov, to_root)
        if not base_old_file or not base_old_file.is_file():
            continue
        if not base_new_file or not base_new_file.is_file():
            dropped_upstream.append(f"{ov.format_name}/{ov.rel_path}")
            continue
        location = f"{ov.level.capitalize()}s/{ov.scope_name}/{ov.rel_path}"
        results.append(analyze_3way(
            location, ov.rel_path, ov.format_name,
            read_lines(base_old_file), read_lines(base_new_file), read_lines(ov.abs_path)))

    if args.format == "json":
        emit_json({
            "project": project, "fromVersion": from_ver, "toVersion": to_ver,
            "skippedRetired": skipped_retired, "droppedUpstream": dropped_upstream,
            "results": results,
        })
        return EXIT_SUCCESS

    order = {"manual-merge": 0, "auto-mergeable": 1, "fast-forward": 2, "redundant": 3, "in-sync": 4}
    results.sort(key=lambda r: (order.get(r.verdict, 9), -r.conflict_regions, -r.customization))
    print(f"3-way drift: {project.path.name}   {from_ver} -> {to_ver}")
    counts: dict[str, int] = {}
    for r in results:
        counts[r.verdict] = counts.get(r.verdict, 0) + 1
    print("  " + " | ".join(f"{v}: {counts.get(v,0)}" for v in order))
    if skipped_retired:
        print(f"  ({skipped_retired} forked files in retired formats skipped -> see `cleanup`)")
    print()
    print(f"  {'VERDICT':<14} {'UPSTREAM':>8} {'CUSTOM':>7} {'CONFL':>6}  {'OVERRIDE'}")
    print(f"  {'-'*14} {'-'*8} {'-'*7} {'-'*6}  {'-'*44}")
    for r in results:
        print(f"  {r.verdict:<14} {r.upstream_change:>8} {r.customization:>7} {r.conflict_regions:>6}  {r.location}")
        if r.verdict in ("manual-merge", "redundant"):
            print(f"        -> {r.note}")
    if dropped_upstream:
        print()
        print(f"  Dropped upstream (file/format gone in {to_ver}) -- verify still needed:")
        for d in dropped_upstream:
            print(f"    - {d}")
    return EXIT_SUCCESS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit ePublisher advanced customizations (overrides) for upstream drift.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p):
        p.add_argument("--project", required=True, help="Path to .wep/.wrp/.wxsp project file.")
        p.add_argument("--install-root", default=str(DEFAULT_INSTALL_ROOT),
                       help=f"ePublisher install root (default: {DEFAULT_INSTALL_ROOT}).")
        p.add_argument("--format", choices=["text", "json"], default="text", help="Output format.")

    p_enum = sub.add_parser("enumerate", help="List and classify overrides.")
    add_common(p_enum)
    p_enum.add_argument("--baseline-version", help="Force a baseline version (default: derived from project).")
    p_enum.set_defaults(func=cmd_enumerate)

    p_disc = sub.add_parser("discover", help="Fingerprint overrides to find the fork-point baseline.")
    add_common(p_disc)
    p_disc.set_defaults(func=cmd_discover)

    p_clean = sub.add_parser("cleanup", help="Recommend removals: retired formats, orphans, cruft/duplicates.")
    add_common(p_clean)
    p_clean.add_argument("--baseline-version", help="Force a baseline version (default: derived from project).")
    p_clean.set_defaults(func=cmd_cleanup)

    p_drift = sub.add_parser("drift", help="3-way drift classification (from-version -> to-version).")
    add_common(p_drift)
    p_drift.add_argument("--to-version", required=True, help="Upgrade-target format version (e.g. 2025.1).")
    p_drift.add_argument("--from-version", help="Fork-point/base version (default: project's locked FormatVersion).")
    p_drift.set_defaults(func=cmd_drift)

    p_aud = sub.add_parser("audit", help="Full audit pass (classification + drift summary).")
    add_common(p_aud)
    p_aud.add_argument("--baseline-version", help="Force a baseline version (default: derived from project).")
    p_aud.add_argument("--annotation-pattern", action="append",
                       help="Regex marking an intentional customization (repeatable). "
                            f"Default: {DEFAULT_ANNOTATION_PATTERNS}")
    p_aud.add_argument("--theme-prefix", action="append",
                       help="Custom SCSS variable prefix signalling a customization, e.g. 'theme' "
                            "or a company abbreviation like 'webworks' (repeatable). "
                            "If omitted, the prefix is auto-detected from override-added variables.")
    p_aud.set_defaults(func=cmd_audit)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.func(args)
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return EXIT_NOT_FOUND


if __name__ == "__main__":
    sys.exit(main())
