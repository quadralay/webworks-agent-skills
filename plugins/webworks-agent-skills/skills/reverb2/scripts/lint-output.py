#!/usr/bin/env python3
"""
lint-output.py

Static linter for a built or assembled WebWorks Reverb 2.0 output directory.
Catches structural breakages that kill the runtime *silently* — the page hangs
on the spinner with no console error — and that are detectable without a
browser, so they can run in CI or a pre-deploy gate.

Reverb 2.0 is a single-page application whose shell (`index.html`) loads content
"parcels" at runtime via `scripts/connect.js`. Several breakage classes are
visible purely in the emitted files:

Checks
------
1. self-closed-element  (error)
   A non-void HTML element written in XML self-closing form — `<script/>`,
   `<iframe/>`, `<div/>`, `<span/>`, `<a/>`, `<ul/>`, `<li/>`, … In `text/html`
   the `/` is ignored, so `<script/>` parses as an *open* `<script>` that
   swallows the rest of the document as script text. The first page never
   renders and there is **no** console error. (ePublisher Trac #2792.) Void
   elements (`<meta/>`, `<link/>`, `<br/>`, …) and elements inside foreign
   content (`<svg>`, `<math>`) are exempt — self-closing is legal there.

2. manifest-parcel-groupid  (error)
   `connect.js` binds each parcel to the `#parcels` manifest **by GroupID**:
   it reads each manifest anchor `<a id="<ctx>:<GID>" href="<Name>.html">`,
   takes `id.split(':')[1]` as the GroupID, fetches `<Name>.html`, and looks up
   `toc:<GID>`, `data:<GID>`, `breadcrumbs:<GID>`, and `page:<GID>:first/last`
   inside it. If the parcel's own GroupID (its `<body id="id:<GID>">` and those
   divs) disagrees with the manifest's — which happens when output is assembled
   from multiple builds that each minted their own GroupIDs, e.g. the
   Reverb-on-S3 deploy-set model — every lookup returns null, the parcel never
   attaches, and the spinner hangs silently.

3. parcel-deploy-unit  (error)
   Each manifest parcel `<Name>` is published as a deploy unit: `<Name>.html`
   (the manifest href target), the `<Name>/` content directory, and the runtime
   chunks `<Name>_ix.html` / `<Name>_lx.js` / `<Name>_sx.js`. Which chunks are
   required is version/feature dependent — older builds omit the `_lx.js`
   landmark chunk, search-disabled builds omit `_sx.js` — so the required chunk
   set is read from the build's own `scripts/connect.js` (it pushes
   `parcel_directory_url + '<suffix>'` for each chunk it fetches). A missing
   member means a broken parcel.

4. reference-integrity  (warn)
   Local `scripts/` and `css/` assets referenced by `index.html`
   (`<script src>`, `<link href>`) exist on disk. Remote (`http(s)://`,
   protocol-relative `//`) and `data:` references are skipped.

The check set is extensible — new known-breakage checks get added here as they
are discovered.

Usage
-----
    python lint-output.py <output-dir> [--json] [--strict] [--no-color]

Arguments
---------
    output-dir   Root of a built/assembled Reverb 2.0 output (the directory
                 containing index.html).

Flags
-----
    --json       Emit a structured JSON report instead of human-readable text.
    --strict     Treat warnings as failures (affects the exit code only).
    --no-color   Disable ANSI color in text output (auto-disabled when stdout
                 is not a TTY).

Exit codes (CI-friendly)
------------------------
    0 - Clean: no error-severity findings (and no warnings under --strict).
    1 - At least one error-severity finding (or, under --strict, any warning).
    2 - The linter could not run: <output-dir> missing or not a directory,
        or an unreadable file. Distinct from "found problems".

Examples
--------
    # Lint a debug build
    python lint-output.py "Output/WebWorks Reverb 2.0"

    # CI gate — fail on warnings too, machine-readable
    python lint-output.py ./site --strict --json

Relationship to the browser test
--------------------------------
This linter is the *static* pre-flight (cheap, no browser). `browser-test.js`
is the *runtime* confirmation (the `preload` load signal; needs Chrome). A good
flow runs the linter first, then the browser test.
"""

import argparse
import json
import os
import sys
import urllib.parse
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional

# ANSI color codes (matched to the other reverb2 scripts).
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
NC = '\033[0m'

DEBUG = os.environ.get('DEBUG', '0') == '1'

# Void elements per the HTML spec: legal to write self-closed, the `/` is
# simply ignored. Self-closing these is harmless, so they are never flagged.
VOID_ELEMENTS = frozenset({
    'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
    'link', 'meta', 'param', 'source', 'track', 'wbr',
})

# Roots of foreign content where XML self-closing syntax is valid HTML5. Any
# self-closed tag inside an <svg> or <math> subtree (`<path/>`, `<rect/>`,
# `<circle/>`, …) is legitimate and must not be flagged.
FOREIGN_ROOTS = frozenset({'svg', 'math'})

# Element-id prefixes whose value is *always* the parcel's GroupID, used to read
# the parcel's own GroupID and compare it to what the manifest binds:
#   body  -> id:<GID>          (single, on <body>)
#   toc   -> toc:<GID>         (single container)
#   data  -> data:<GID>        (single container)
#   page  -> page:<GID>:<first|last|N>   (GroupID-keyed; trailing :<suffix>)
# `breadcrumbs:` is deliberately excluded: it carries one `breadcrumbs:<GID>`
# container *and* several `breadcrumbs:<pageLandmarkId>` per-result fragments, so
# its values are not all GroupIDs and must not be compared.
GID_SIMPLE_PREFIXES = ('id', 'toc', 'data')
GID_PAGE_PREFIX = 'page'

# Per-parcel runtime chunk suffixes. Which of these a build emits is version- and
# feature-dependent, so the *required* subset is read from the build's own
# connect.js rather than assumed (see expected_chunk_suffixes).
CHUNK_SUFFIXES = ('_ix.html', '_lx.js', '_sx.js')

# Root-level shell HTML pages scanned for self-closed elements in addition to
# index.html and the per-parcel pages. Only those that exist are scanned.
SHELL_HTML_FILES = ('index.html', 'search.html', 'splash.html', 'not-found.html')

# Finding severities.
SEVERITY_ERROR = 'error'
SEVERITY_WARN = 'warn'


def debug_log(message: str) -> None:
    """Print a debug message to stderr (only when DEBUG=1)."""
    if DEBUG:
        print(f"{YELLOW}[DEBUG]{NC} {message}", file=sys.stderr)


def error_log(message: str) -> None:
    """Print an error message to stderr."""
    print(f"{RED}[ERROR]{NC} {message}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Finding model
# ---------------------------------------------------------------------------


class Finding:
    """A single lint result.

    `file` is relative to the output directory (for readable, stable output).
    `line`/`col` are 1-based and optional (None for whole-file findings). For
    minified output every line is 1, so `snippet` carries the local context.
    """

    def __init__(
        self,
        check: str,
        severity: str,
        message: str,
        file: Optional[str] = None,
        line: Optional[int] = None,
        col: Optional[int] = None,
        snippet: Optional[str] = None,
    ):
        self.check = check
        self.severity = severity
        self.message = message
        self.file = file
        self.line = line
        self.col = col
        self.snippet = snippet

    def to_dict(self) -> dict:
        out: dict = {'check': self.check, 'severity': self.severity}
        if self.file is not None:
            out['file'] = self.file
        if self.line is not None:
            out['line'] = self.line
        if self.col is not None:
            out['col'] = self.col
        out['message'] = self.message
        if self.snippet is not None:
            out['snippet'] = self.snippet
        return out


# ---------------------------------------------------------------------------
# HTML parsing helpers
# ---------------------------------------------------------------------------


class SelfClosedScanner(HTMLParser):
    """Collect self-closed non-void elements that are not inside foreign content.

    HTMLParser dispatches XML-style `<tag .../>` to handle_startendtag, and
    treats <script>/<style> bodies as raw CDATA, so a `<div/>` written *inside*
    a script string literal is never mistaken for a real tag. Foreign-content
    depth (<svg>/<math>) is tracked so legal self-closing there is exempt.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.findings: list[tuple[int, int, str, str]] = []
        self.foreign_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in FOREIGN_ROOTS:
            self.foreign_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in FOREIGN_ROOTS and self.foreign_depth > 0:
            self.foreign_depth -= 1

    def handle_startendtag(self, tag: str, attrs) -> None:
        # An empty foreign root (`<svg/>`) or any self-closed tag within foreign
        # content is valid HTML5 — never flag it.
        if tag in FOREIGN_ROOTS or self.foreign_depth > 0:
            return
        if tag in VOID_ELEMENTS:
            return
        line, offset = self.getpos()
        raw = self.get_starttag_text() or f"<{tag}/>"
        self.findings.append((line, offset + 1, tag, raw))


def find_self_closed(html_text: str) -> list[tuple[int, int, str, str]]:
    """Return (line, col, tag, raw) for each self-closed non-void element.

    `col` is 1-based. Parsing is lenient: HTMLParser does not raise on the kind
    of malformed markup that triggers this very check.
    """
    scanner = SelfClosedScanner()
    scanner.feed(html_text)
    scanner.close()
    return scanner.findings


class ElementIdCollector(HTMLParser):
    """Collect (tag, id) for every element that carries an `id` attribute."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[tuple[str, str]] = []

    def _record(self, tag: str, attrs) -> None:
        for name, value in attrs:
            if name == 'id' and value:
                self.ids.append((tag, value))

    def handle_starttag(self, tag: str, attrs) -> None:
        self._record(tag, attrs)

    def handle_startendtag(self, tag: str, attrs) -> None:
        self._record(tag, attrs)


def collect_element_ids(html_text: str) -> list[tuple[str, str]]:
    """Return (tag, id_value) for every element with an id, in document order."""
    collector = ElementIdCollector()
    collector.feed(html_text)
    collector.close()
    return collector.ids


class ParcelEntry:
    """One `#parcels` manifest entry.

    `gid_anchor` is the GroupID connect.js binds on: `anchor_id.split(':')[1]`.
    `gid_li` is the GroupID on the wrapping `<li id="group:<GID>">` (used by
    connect.js for TOC hierarchy). They normally agree; a disagreement is itself
    a manifest-internal breakage.
    """

    def __init__(
        self,
        gid_li: Optional[str],
        name: Optional[str],
        anchor_id: Optional[str],
        href: Optional[str],
    ):
        self.gid_li = gid_li
        self.name = name
        self.anchor_id = anchor_id
        self.href = href

    @property
    def gid_anchor(self) -> Optional[str]:
        if not self.anchor_id:
            return None
        parts = self.anchor_id.split(':')
        return parts[1] if len(parts) >= 2 and parts[0] != '' else None


class ManifestParser(HTMLParser):
    """Extract `#parcels` manifest entries from index.html.

    Tracks entry/exit of `<div id="parcels">` by counting nested <div> tags, so
    only anchors inside the manifest are collected (not TOC or chrome anchors
    elsewhere in the shell). Within each `<li id="group:<GID>">` it records the
    GroupID, the `data-group-title`, and the first `<a id=… href=…>` anchor.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[ParcelEntry] = []
        self._in_parcels = False
        self._div_depth = 0
        self._current: Optional[ParcelEntry] = None

    def handle_starttag(self, tag: str, attrs) -> None:
        attr = dict(attrs)
        if tag == 'div':
            if not self._in_parcels:
                if attr.get('id') == 'parcels':
                    self._in_parcels = True
                    self._div_depth = 0
                return
            # Already inside #parcels — count nested divs to find the close.
            self._div_depth += 1
            return
        if not self._in_parcels:
            return
        if tag == 'li':
            gid_li = None
            lid = attr.get('id', '')
            if lid.startswith('group:'):
                gid_li = lid[len('group:'):]
            self._current = ParcelEntry(
                gid_li=gid_li,
                name=attr.get('data-group-title'),
                anchor_id=None,
                href=None,
            )
        elif tag == 'a' and self._current is not None and self._current.href is None:
            if attr.get('id') and attr.get('href'):
                self._current.anchor_id = attr['id']
                self._current.href = attr['href']

    def handle_endtag(self, tag: str) -> None:
        if not self._in_parcels:
            return
        if tag == 'div':
            if self._div_depth == 0:
                # This </div> closes #parcels itself.
                self._in_parcels = False
            else:
                self._div_depth -= 1
        elif tag == 'li' and self._current is not None:
            self.entries.append(self._current)
            self._current = None


def parse_manifest(index_html_text: str) -> list[ParcelEntry]:
    """Return the `#parcels` manifest entries from index.html, in document order."""
    parser = ManifestParser()
    parser.feed(index_html_text)
    parser.close()
    return parser.entries


def classify_gid_id(id_value: str) -> Optional[str]:
    """Return the GroupID a parcel element id encodes, or None if it encodes none.

    `page:<GID>:<suffix>` yields GID (middle segment); `id:`/`toc:`/`data:`
    yield the segment after the colon. GroupIDs never contain a colon (connect.js
    builds these ids by string concatenation around `:`), so the split is
    unambiguous. `breadcrumbs:` is intentionally not classified here.
    """
    if id_value.startswith(GID_PAGE_PREFIX + ':'):
        gid = id_value[len(GID_PAGE_PREFIX) + 1:].split(':', 1)[0]
        return gid or None
    for prefix in GID_SIMPLE_PREFIXES:
        if id_value.startswith(prefix + ':'):
            gid = id_value[len(prefix) + 1:]
            return gid if gid and ':' not in gid else None
    return None


def extract_parcel_gids(parcel_html_text: str) -> tuple[Optional[str], set]:
    """Return (body_gid, {gid,...}) for a parcel page.

    `body_gid` is the GroupID on the `<body id="id:<GID>">` element (the parcel's
    own GroupID marker), or None if absent. The set is every GroupID that appears
    under the always-GroupID prefixes (`id:`/`toc:`/`data:`/`page:`) — for a
    well-formed parcel it is exactly the parcel's single GroupID.
    """
    body_gid: Optional[str] = None
    gids: set = set()
    for tag, id_value in collect_element_ids(parcel_html_text):
        gid = classify_gid_id(id_value)
        if gid is None:
            continue
        gids.add(gid)
        if tag == 'body' and id_value.startswith('id:'):
            body_gid = gid
    return body_gid, gids


class AssetRefCollector(HTMLParser):
    """Collect local asset references from index.html: <script src>, <link href>."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.refs: list[tuple[str, str]] = []  # (kind, raw_ref)

    def _add(self, kind: str, ref: Optional[str]) -> None:
        if ref:
            self.refs.append((kind, ref))

    def handle_starttag(self, tag: str, attrs) -> None:
        attr = dict(attrs)
        if tag == 'script':
            self._add('script src', attr.get('src'))
        elif tag == 'link':
            self._add('link href', attr.get('href'))

    def handle_startendtag(self, tag: str, attrs) -> None:
        self.handle_starttag(tag, attrs)


def extract_local_assets(index_html_text: str) -> list[tuple[str, str]]:
    """Return (kind, ref) for each *local* asset referenced by index.html.

    Remote (`http(s)://`, protocol-relative `//`) and `data:` refs are dropped —
    only on-disk assets are checkable. The `?v=<hash>` cache-buster query and any
    fragment are stripped, and the path is percent-decoded for filesystem lookup.
    """
    collector = AssetRefCollector()
    collector.feed(index_html_text)
    collector.close()

    local: list[tuple[str, str]] = []
    for kind, ref in collector.refs:
        stripped = ref.strip()
        lowered = stripped.lower()
        if lowered.startswith(('http://', 'https://', '//', 'data:', 'mailto:', '#')):
            continue
        path = stripped.split('?', 1)[0].split('#', 1)[0]
        if not path:
            continue
        local.append((kind, urllib.parse.unquote(path)))
    return local


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def _read_text(path: Path) -> str:
    """Read a file as UTF-8, tolerating stray bytes (output is generated UTF-8)."""
    return path.read_text(encoding='utf-8', errors='replace')


def expected_chunk_suffixes(output_dir: Path) -> list[str]:
    """Return the parcel-chunk suffixes this build's connect.js actually fetches.

    The required deploy-unit chunks are version/feature dependent: every build
    fetches `_ix.html`, newer builds also fetch the `_lx.js` landmark chunk, and
    `_sx.js` is present when search is enabled. connect.js is the source of truth
    — it pushes `parcel_directory_url + '<suffix>'` for each chunk it loads — so a
    suffix is required iff it appears there. If connect.js cannot be read, only
    the always-present deploy-unit members (`<Name>.html`, `<Name>/`) are
    required; the missing connect.js itself surfaces via reference-integrity.
    """
    connect = output_dir / 'scripts' / 'connect.js'
    try:
        text = connect.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return []
    return [suffix for suffix in CHUNK_SUFFIXES if suffix in text]


def check_self_closed(
    output_dir: Path,
    rel_files: list[str],
    findings: list[Finding],
) -> int:
    """Flag self-closed non-void elements in each scanned HTML file.

    Returns the number of files actually scanned (existing + readable).
    """
    scanned = 0
    for rel in rel_files:
        path = output_dir / rel
        if not path.is_file():
            continue
        try:
            text = _read_text(path)
        except OSError as e:
            findings.append(Finding(
                'self-closed-element', SEVERITY_ERROR,
                f"could not read file: {e}", file=rel,
            ))
            continue
        scanned += 1
        for line, col, tag, raw in find_self_closed(text):
            findings.append(Finding(
                'self-closed-element', SEVERITY_ERROR,
                f"<{tag}> is self-closed; in text/html the '/' is ignored and the "
                f"element swallows following markup - kills the Reverb runtime "
                f"silently (Trac #2792)",
                file=rel, line=line, col=col, snippet=raw.strip(),
            ))
    return scanned


def check_manifest_and_parcels(
    output_dir: Path,
    entries: list[ParcelEntry],
    chunk_suffixes: list[str],
    findings: list[Finding],
) -> None:
    """Run the GroupID-consistency and deploy-unit-completeness checks per parcel."""
    for entry in entries:
        if not entry.href:
            findings.append(Finding(
                'manifest-parcel-groupid', SEVERITY_ERROR,
                f"manifest parcel '{entry.name or entry.gid_li or '?'}' has no "
                f"<a href> - cannot bind a parcel page",
                file='index.html',
            ))
            continue

        href_path = urllib.parse.unquote(entry.href.split('?', 1)[0].split('#', 1)[0])
        stem = href_path[:-5] if href_path.lower().endswith('.html') else href_path
        gid_manifest = entry.gid_anchor

        # Manifest-internal: the anchor GID and the wrapping <li group:> GID
        # should match. connect.js binds on the anchor; the <li> drives TOC
        # hierarchy. A split here breaks one or the other.
        if gid_manifest is None:
            findings.append(Finding(
                'manifest-parcel-groupid', SEVERITY_ERROR,
                f"manifest anchor id={entry.anchor_id!r} is not of the form "
                f"'<ctx>:<GroupID>'; connect.js reads the GroupID as "
                f"id.split(':')[1] and will bind nothing",
                file='index.html',
            ))
        elif entry.gid_li is not None and entry.gid_li != gid_manifest:
            findings.append(Finding(
                'manifest-parcel-groupid', SEVERITY_ERROR,
                f"manifest GroupID mismatch for '{href_path}': anchor binds "
                f"'{gid_manifest}' but the wrapping <li> is 'group:{entry.gid_li}'",
                file='index.html',
            ))

        _check_deploy_unit(output_dir, stem, href_path, chunk_suffixes, findings)
        _check_parcel_groupid(output_dir, href_path, gid_manifest, findings)


def _check_deploy_unit(
    output_dir: Path,
    stem: str,
    href_path: str,
    chunk_suffixes: list[str],
    findings: list[Finding],
) -> None:
    """Verify the parcel's deploy unit exists on disk.

    `<Name>.html` (the manifest href) and the `<Name>/` content directory are
    always required; the chunk files (`chunk_suffixes`) are those this build's
    connect.js actually fetches.
    """
    required_files = [f"{stem}.html"] + [f"{stem}{suffix}" for suffix in chunk_suffixes]
    for rel in required_files:
        if not (output_dir / rel).is_file():
            findings.append(Finding(
                'parcel-deploy-unit', SEVERITY_ERROR,
                f"missing parcel deploy-unit file for '{href_path}'",
                file=rel,
            ))
    if not (output_dir / stem).is_dir():
        findings.append(Finding(
            'parcel-deploy-unit', SEVERITY_ERROR,
            f"missing parcel content directory for '{href_path}'",
            file=f"{stem}/",
        ))


def _check_parcel_groupid(
    output_dir: Path,
    href_path: str,
    gid_manifest: Optional[str],
    findings: list[Finding],
) -> None:
    """Verify the parcel page's own GroupID matches what the manifest binds."""
    if gid_manifest is None:
        return  # already reported as a manifest-anchor error
    parcel_file = output_dir / href_path
    if not parcel_file.is_file():
        return  # the missing file is reported by the deploy-unit check
    try:
        text = _read_text(parcel_file)
    except OSError as e:
        findings.append(Finding(
            'manifest-parcel-groupid', SEVERITY_ERROR,
            f"could not read parcel page: {e}", file=href_path,
        ))
        return

    body_gid, parcel_gids = extract_parcel_gids(text)

    if not parcel_gids and body_gid is None:
        findings.append(Finding(
            'manifest-parcel-groupid', SEVERITY_ERROR,
            f"parcel page carries no GroupID landmarks (id:/toc:/data:/page:) - "
            f"the manifest binds GroupID '{gid_manifest}' but this is not a "
            f"recognizable Reverb parcel page",
            file=href_path,
        ))
        return

    if gid_manifest not in parcel_gids:
        # The manifest GroupID appears on none of the parcel's landmarks — the
        # whole parcel was built under a different GroupID (the classic deploy-set
        # mismatch). connect.js binds toc:/data:/page: by the manifest GroupID,
        # so every getElementById returns null and the parcel never attaches.
        observed = sorted(parcel_gids)
        observed_str = observed[0] if len(observed) == 1 else str(observed)
        findings.append(Finding(
            'manifest-parcel-groupid', SEVERITY_ERROR,
            f"GroupID mismatch: the manifest binds parcel '{href_path}' to "
            f"GroupID '{gid_manifest}', but the parcel's landmarks use "
            f"'{observed_str}'. connect.js binds toc:/data:/page: by the manifest "
            f"GroupID, so this parcel never attaches and the spinner hangs with "
            f"no console error",
            file=href_path,
        ))
    else:
        # Manifest GroupID is present, but the parcel also carries landmarks under
        # a different GroupID — a partial / mixed-GroupID page.
        extra = sorted(g for g in parcel_gids if g != gid_manifest)
        if extra:
            findings.append(Finding(
                'manifest-parcel-groupid', SEVERITY_ERROR,
                f"parcel '{href_path}' mixes GroupIDs: the manifest binds "
                f"'{gid_manifest}' but some landmarks use {extra}; those elements "
                f"will not bind",
                file=href_path,
            ))


def check_reference_integrity(
    output_dir: Path,
    index_html_text: str,
    findings: list[Finding],
) -> None:
    """Warn on local scripts/css referenced by index.html that are missing on disk."""
    for kind, ref in extract_local_assets(index_html_text):
        if not (output_dir / ref).is_file():
            findings.append(Finding(
                'reference-integrity', SEVERITY_WARN,
                f"index.html references a local asset that is missing on disk "
                f"({kind})",
                file=ref,
            ))


def lint(output_dir: Path) -> list[Finding]:
    """Run every check against `output_dir` and return all findings.

    The output directory is assumed to exist (the caller validates it). A
    missing index.html is itself reported as an error finding; the manifest- and
    reference-dependent checks are then skipped.
    """
    findings: list[Finding] = []

    index_path = output_dir / 'index.html'
    if not index_path.is_file():
        findings.append(Finding(
            'self-closed-element', SEVERITY_ERROR,
            "index.html not found - not a Reverb 2.0 output directory, or the "
            "shell entry point is missing",
            file='index.html',
        ))
        # Still scan any parcel-less shell pages that happen to exist.
        check_self_closed(output_dir, list(SHELL_HTML_FILES), findings)
        return findings

    index_text = _read_text(index_path)
    entries = parse_manifest(index_text)
    debug_log(f"parsed {len(entries)} manifest parcel(s)")

    # Files scanned for self-closed elements: the shell pages plus, per parcel,
    # the entry page and its index chunk.
    html_files = [f for f in SHELL_HTML_FILES]
    for entry in entries:
        if not entry.href:
            continue
        href_path = urllib.parse.unquote(entry.href.split('?', 1)[0].split('#', 1)[0])
        stem = href_path[:-5] if href_path.lower().endswith('.html') else href_path
        for rel in (href_path, f"{stem}_ix.html"):
            if rel not in html_files:
                html_files.append(rel)

    chunk_suffixes = expected_chunk_suffixes(output_dir)
    debug_log(f"connect.js fetches chunk suffixes: {chunk_suffixes}")

    check_self_closed(output_dir, html_files, findings)
    check_manifest_and_parcels(output_dir, entries, chunk_suffixes, findings)
    check_reference_integrity(output_dir, index_text, findings)
    return findings


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _counts(findings: list[Finding]) -> tuple[int, int]:
    errors = sum(1 for f in findings if f.severity == SEVERITY_ERROR)
    warnings = sum(1 for f in findings if f.severity == SEVERITY_WARN)
    return errors, warnings


def render_text(
    output_dir: Path,
    findings: list[Finding],
    use_color: bool,
) -> str:
    """Render findings as grouped, human-readable text."""
    def c(code: str, text: str) -> str:
        return f"{code}{text}{NC}" if use_color else text

    errors, warnings = _counts(findings)
    lines: list[str] = [f"Reverb 2.0 output lint: {output_dir}"]

    if not findings:
        lines.append(c(GREEN, "  OK - no issues found"))
        return '\n'.join(lines)

    # Stable grouping by check name, errors before warnings within each.
    order = {SEVERITY_ERROR: 0, SEVERITY_WARN: 1}
    for finding in sorted(
        findings, key=lambda f: (f.check, order.get(f.severity, 9), f.file or '', f.line or 0)
    ):
        if finding.severity == SEVERITY_ERROR:
            tag = c(RED, 'ERROR')
        else:
            tag = c(YELLOW, ' WARN')
        loc = finding.file or '(output)'
        if finding.line is not None:
            loc += f":{finding.line}"
            if finding.col is not None:
                loc += f":{finding.col}"
        lines.append(f"{tag}  [{finding.check}]  {loc}")
        lines.append(f"       {finding.message}")
        if finding.snippet:
            lines.append(f"       > {finding.snippet}")

    summary = f"{errors} error(s), {warnings} warning(s)"
    lines.append('')
    lines.append(c(RED if errors else YELLOW, summary))
    return '\n'.join(lines)


def render_json(output_dir: Path, findings: list[Finding], success: bool) -> str:
    """Render findings as a structured JSON report."""
    errors, warnings = _counts(findings)
    report = {
        'tool': 'lint-output',
        'output_dir': str(output_dir),
        'success': success,
        'summary': {'errors': errors, 'warnings': warnings, 'total': len(findings)},
        'findings': [f.to_dict() for f in findings],
    }
    return json.dumps(report, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


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
        description='Static linter for WebWorks Reverb 2.0 output directories.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exit codes:
    0  Clean (no errors; no warnings under --strict)
    1  Error-severity findings (or any warning under --strict)
    2  Could not run (output dir missing / unreadable)

Examples:
    %(prog)s "Output/WebWorks Reverb 2.0"
    %(prog)s ./site --strict --json
""",
    )
    parser.add_argument('output_dir', help='Reverb 2.0 output directory (contains index.html)')
    parser.add_argument('--json', action='store_true', help='Emit a structured JSON report')
    parser.add_argument(
        '--strict', action='store_true',
        help='Treat warnings as failures (exit code only)',
    )
    parser.add_argument('--no-color', action='store_true', help='Disable ANSI color in text output')
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    if not output_dir.is_dir():
        error_log(f"not a directory: {output_dir}")
        return 2

    try:
        findings = lint(output_dir)
    except OSError as e:
        error_log(f"could not lint {output_dir}: {e}")
        return 2

    errors, warnings = _counts(findings)
    success = errors == 0 and (warnings == 0 if args.strict else True)

    if args.json:
        print(render_json(output_dir, findings, success))
    else:
        use_color = not args.no_color and sys.stdout.isatty()
        print(render_text(output_dir, findings, use_color))

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
