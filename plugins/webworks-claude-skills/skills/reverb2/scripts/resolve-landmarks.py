#!/usr/bin/env python3
"""
resolve-landmarks.py

Resolves stable Reverb 2.0 landmark URLs (the hash-based "#/<id>" form used in
published help) into direct static file paths by parsing the _lx.js chunk files
emitted alongside every Reverb output. Lets AI consumers fetch documentation
without executing the Reverb JavaScript runtime.

Usage:
    python resolve-landmarks.py resolve <id> --from <path> [--json]
    python resolve-landmarks.py rewrite <url> --from <path> [--base-url <url>]
    python resolve-landmarks.py dump --from <path> [--table]

Arguments:
    resolve <id>       Resolve a landmark ID to a relative file path (with optional #anchor).
    rewrite <url>      Rewrite a full stable URL ("...#/<id>") into a direct file URL.
    dump               Emit the full {id: relative_path} map for the given source.
    --from <path>      Path to a single *_lx.js chunk file or a directory containing chunks.
    --base-url <url>   For "rewrite": replace the inferred URL prefix with this base.
    --json             For "resolve": emit a JSON object instead of the bare path.
    --table            For "dump": emit a human-readable table instead of JSON.

Landmark ID formats (treated as opaque strings):
    - 16-character hex hash (default; all Reverb 2.0 releases)
    - 8-character hex hash (new in 2026.1, opt-in)
    - Pass-through source ID (new in 2026.1, opt-in)

The resolver does not regex, length-check, or hex-validate IDs; it does a
straight string-equality lookup against the third element of each e[i] tuple in
the _lx.js data.

Exit codes:
    0 - Success.
    1 - Resolution failure (ID not found, or URL has no ID after "#/").
    2 - Parse failure or IO failure (file missing, malformed chunk, empty source).

Examples:
    # Resolve a single ID against one chunk
    python resolve-landmarks.py resolve e5d3d31c42d8d1d4 --from output/FAQs_lx.js

    # Resolve against every chunk in a directory
    python resolve-landmarks.py resolve abc12345 --from output/

    # Rewrite a published stable URL into a direct URL
    python resolve-landmarks.py rewrite \\
        https://example.com/help/#/e5d3d31c42d8d1d4 --from output/

    # Dump the full index as JSON
    python resolve-landmarks.py dump --from output/

    # Dump the full index as a human-readable table
    python resolve-landmarks.py dump --from output/ --table
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

# Matches "var landmarks = { ... };Landmarks.Advance(landmarks);" tolerating
# whitespace, CRLF, and trailing semicolons. The inner object literal must be
# JSON-compatible; the parser fails loudly when it isn't.
_LANDMARKS_RE = re.compile(
    r'var\s+landmarks\s*=\s*(\{.*?\})\s*;\s*Landmarks\.Advance\s*\(',
    re.DOTALL,
)

# Matches a stable URL fragment "<prefix>#/<id>" with at least one character
# after "#/". The id is captured as an opaque string up to the next "?", "&",
# or end of input.
_STABLE_URL_RE = re.compile(r'^(?P<prefix>.*?)#/(?P<id>[^?&]+)(?P<rest>[?&].*)?$')


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


def parse_chunk(path: Path) -> dict:
    """
    Read a _lx.js chunk and return its landmarks object as a dict.

    The chunk file shape is:
        var landmarks = { "f": [...], "a": [...], "e": [[fi,ai,id], ...] };
        Landmarks.Advance(landmarks);

    Raises ValueError on shape mismatch; the message names the offending file.
    """
    debug_log(f"Parsing chunk: {path}")

    text = path.read_text(encoding='utf-8')
    match = _LANDMARKS_RE.search(text)
    if not match:
        raise ValueError(
            f"{path}: not a recognizable _lx.js chunk "
            "(missing 'var landmarks = {...};Landmarks.Advance(...)')"
        )

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError as e:
        raise ValueError(f"{path}: landmarks object is not JSON-parseable: {e}") from e

    for key in ('f', 'a', 'e'):
        if key not in data:
            raise ValueError(f"{path}: landmarks object is missing required key '{key}'")
        if not isinstance(data[key], list):
            raise ValueError(f"{path}: landmarks key '{key}' is not a list")

    return data


def build_index(
    chunk_paths: list[Path],
) -> tuple[list[str], list[str], dict[str, tuple[int, int]]]:
    """
    Merge every chunk into a global landmark index.

    Returns:
        (global_files, global_anchors, id_to_pair)
        where id_to_pair[id] = (global_file_index, global_anchor_index).

    Mirrors the runtime's "last write wins" semantics from Landmarks.Advance()
    in scripts/landmarks.js: when an ID appears multiple times, the most
    recent (file, anchor) pair wins. The paragraph-level row is written after
    the page-level row in real _lx.js chunks, so this returns file#anchor
    whenever a paragraph anchor exists.
    """
    global_files: list[str] = []
    global_anchors: list[str] = []
    file_index: dict[str, int] = {}
    anchor_index: dict[str, int] = {}
    id_to_pair: dict[str, tuple[int, int]] = {}

    def intern(value: str, global_list: list[str], index: dict[str, int]) -> int:
        if value not in index:
            index[value] = len(global_list)
            global_list.append(value)
        return index[value]

    for chunk_path in chunk_paths:
        chunk = parse_chunk(chunk_path)
        files = chunk['f']
        anchors = chunk['a']
        entries = chunk['e']

        file_map = [intern(f, global_files, file_index) for f in files]
        anchor_map = [intern(a, global_anchors, anchor_index) for a in anchors]

        for row in entries:
            # Runtime's defensive `continue`:
            # if (fi === undefined || ai === undefined || !id) continue;
            if not isinstance(row, list) or len(row) < 3:
                continue
            local_fi, local_ai, landmark_id = row[0], row[1], row[2]
            if not landmark_id:
                continue
            if not isinstance(local_fi, int) or not isinstance(local_ai, int):
                continue
            if local_fi < 0 or local_fi >= len(file_map):
                continue
            if local_ai < 0 or local_ai >= len(anchor_map):
                continue
            id_to_pair[landmark_id] = (file_map[local_fi], anchor_map[local_ai])

    return global_files, global_anchors, id_to_pair


def resolve_id(
    landmark_id: str,
    files: list[str],
    anchors: list[str],
    id_to_pair: dict[str, tuple[int, int]],
) -> Optional[str]:
    """
    Look up a landmark ID and return the resolved relative path.

    Returns "file#anchor" when the anchor string is non-empty, otherwise the
    bare "file". Returns None when the ID is not in the index. Matches the
    runtime's GetPathById formatting in scripts/landmarks.js.
    """
    pair = id_to_pair.get(landmark_id)
    if pair is None:
        return None
    file_idx, anchor_idx = pair
    file_path = files[file_idx]
    anchor = anchors[anchor_idx]
    return f"{file_path}#{anchor}" if anchor else file_path


def discover_chunks(source: Path) -> list[Path]:
    """
    Resolve a --from argument to a sorted list of chunk files.

    A single .js file returns [source]. A directory returns every *_lx.js
    file beneath it, sorted by name. An empty directory raises FileNotFoundError
    with a message that names the searched path.
    """
    if not source.exists():
        raise FileNotFoundError(f"source path does not exist: {source}")

    if source.is_file():
        return [source]

    chunks = sorted(source.glob('*_lx.js'))
    if not chunks:
        raise FileNotFoundError(f"no *_lx.js chunks found in: {source}")
    return chunks


def _build_or_die(source: Path) -> tuple[list[str], list[str], dict[str, tuple[int, int]]]:
    """Run discover_chunks + build_index, mapping exceptions to exit-code 2."""
    try:
        chunk_paths = discover_chunks(source)
        debug_log(f"Discovered {len(chunk_paths)} chunk(s)")
        return build_index(chunk_paths)
    except (FileNotFoundError, ValueError, OSError) as e:
        error_log(str(e))
        sys.exit(2)


def cmd_resolve(args: argparse.Namespace) -> int:
    files, anchors, id_to_pair = _build_or_die(Path(args.source))
    path = resolve_id(args.id, files, anchors, id_to_pair)
    if path is None:
        if args.json:
            print(json.dumps({"error": "ID not found", "id": args.id}))
        else:
            error_log(f"ID not found: {args.id}")
        return 1
    if args.json:
        print(json.dumps({"id": args.id, "path": path}))
    else:
        print(path)
    return 0


def cmd_rewrite(args: argparse.Namespace) -> int:
    match = _STABLE_URL_RE.match(args.url)
    if not match:
        error_log(f"URL does not contain a '#/<id>' fragment: {args.url}")
        return 1
    landmark_id = match.group('id')

    files, anchors, id_to_pair = _build_or_die(Path(args.source))
    path = resolve_id(landmark_id, files, anchors, id_to_pair)
    if path is None:
        error_log(f"ID not found: {landmark_id}")
        return 1

    prefix = args.base_url if args.base_url else match.group('prefix')
    if prefix and not prefix.endswith('/'):
        prefix = prefix + '/'
    print(prefix + path)
    return 0


def cmd_dump(args: argparse.Namespace) -> int:
    files, anchors, id_to_pair = _build_or_die(Path(args.source))
    rows = {
        landmark_id: (
            f"{files[fi]}#{anchors[ai]}" if anchors[ai] else files[fi]
        )
        for landmark_id, (fi, ai) in id_to_pair.items()
    }

    if args.table:
        if not rows:
            print("No landmarks found")
            return 0
        id_width = max(len(landmark_id) for landmark_id in rows)
        id_width = max(id_width, len("Landmark ID"))
        lines = [
            "Reverb 2.0 Landmark Index:",
            "━" * (id_width + 4 + 60),
            f"{'Landmark ID':<{id_width}}    Resolved Path",
            "─" * (id_width + 4 + 60),
        ]
        for landmark_id in sorted(rows):
            lines.append(f"{landmark_id:<{id_width}}    {rows[landmark_id]}")
        print('\n'.join(lines))
    else:
        print(json.dumps(rows, indent=2, sort_keys=True))

    success_log(f"Indexed {len(rows)} landmark(s)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Resolve Reverb 2.0 stable landmark URLs to direct file paths.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Resolve a single ID
    %(prog)s resolve e5d3d31c42d8d1d4 --from output/FAQs_lx.js

    # Rewrite a published stable URL into a direct URL
    %(prog)s rewrite https://example.com/help/#/abc12345 --from output/

    # Dump the entire index as JSON
    %(prog)s dump --from output/
"""
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    resolve_parser = subparsers.add_parser(
        'resolve',
        help='Resolve a landmark ID to a relative file path',
    )
    resolve_parser.add_argument('id', help='Landmark ID (opaque string)')
    resolve_parser.add_argument(
        '--from', dest='source', required=True,
        help='Path to a *_lx.js chunk or a directory containing chunks',
    )
    resolve_parser.add_argument(
        '--json', action='store_true',
        help='Emit a JSON object instead of the bare path',
    )

    rewrite_parser = subparsers.add_parser(
        'rewrite',
        help='Rewrite a stable URL into a direct file URL',
    )
    rewrite_parser.add_argument('url', help='Stable URL of the form "<prefix>#/<id>"')
    rewrite_parser.add_argument(
        '--from', dest='source', required=True,
        help='Path to a *_lx.js chunk or a directory containing chunks',
    )
    rewrite_parser.add_argument(
        '--base-url', dest='base_url', default=None,
        help='Replace the inferred URL prefix with this base URL',
    )

    dump_parser = subparsers.add_parser(
        'dump',
        help='Emit the full {id: relative_path} map',
    )
    dump_parser.add_argument(
        '--from', dest='source', required=True,
        help='Path to a *_lx.js chunk or a directory containing chunks',
    )
    dump_parser.add_argument(
        '--table', action='store_true',
        help='Emit a human-readable table instead of JSON',
    )

    args = parser.parse_args()

    if args.command == 'resolve':
        return cmd_resolve(args)
    if args.command == 'rewrite':
        return cmd_rewrite(args)
    if args.command == 'dump':
        return cmd_dump(args)

    parser.print_help()
    return 2


if __name__ == '__main__':
    sys.exit(main())
