#!/usr/bin/env python3
"""
resolve-landmarks.py

Resolves stable Reverb 2.0 landmark URLs (the hash-based "#/<id>" form used in
published help) into direct static file paths by parsing the _lx.js chunk files
emitted alongside every Reverb output. Lets AI consumers fetch documentation
without executing the Reverb JavaScript runtime.

Usage:
    python resolve-landmarks.py resolve <id> (--from <path> | --lookup-table <file>) [--json]
    python resolve-landmarks.py rewrite <url> (--from <path> | --lookup-table <file>) [--base-url <url>]
    python resolve-landmarks.py dump --from <path> [--out <file>] [--source-label <s>] [--table]

Arguments:
    resolve <id>           Resolve a landmark ID to a relative file path (with optional #anchor).
    rewrite <url>          Rewrite a full stable URL ("...#/<id>") into a direct file URL.
    dump                   Emit the full schema'd lookup-table artifact for the given source.
    --from <path>          Path to a single *_lx.js chunk file or a directory containing chunks.
    --lookup-table <file>  Path to a previously emitted dump artifact. Mutually exclusive
                           with --from on resolve and rewrite.
    --out <file>           For "dump": write JSON to <file> instead of stdout.
    --source-label <s>     For "dump": override source.path with a semantic label.
    --base-url <url>       For "rewrite": replace the inferred URL prefix with this base.
    --json                 For "resolve": emit a JSON object instead of the bare path.
    --table                For "dump": emit a human-readable table instead of JSON.

See references/landmark-lookup-table.md for the lookup-table artifact schema.

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
    2 - Parse failure or IO failure (file missing, malformed chunk, empty source,
        unsupported lookup-table format_version, mutually exclusive args).

Examples:
    # Resolve a single ID against one chunk
    python resolve-landmarks.py resolve e5d3d31c42d8d1d4 --from output/FAQs_lx.js

    # Resolve against every chunk in a directory
    python resolve-landmarks.py resolve abc12345 --from output/

    # Resolve against a pre-built lookup-table artifact
    python resolve-landmarks.py resolve abc12345 --lookup-table landmarks.json

    # Rewrite a published stable URL into a direct URL
    python resolve-landmarks.py rewrite \\
        https://example.com/help/#/e5d3d31c42d8d1d4 --from output/

    # Dump the full lookup-table artifact (stdout)
    python resolve-landmarks.py dump --from output/

    # Dump to a file with a semantic source label
    python resolve-landmarks.py dump --from output/ \\
        --out landmarks.json --source-label "ePublisher 2026.1 Help (en)"

    # Dump the full index as a human-readable table
    python resolve-landmarks.py dump --from output/ --table
"""

import argparse
import datetime
import json
import os
import re
import sys
import urllib.parse
from pathlib import Path
from typing import Optional

# Schema version emitted by `dump` and accepted by `--lookup-table`.
LOOKUP_TABLE_FORMAT_VERSION = 1

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


def parse_chunk(path: Path) -> dict[str, list]:
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


def _intern(value: str, global_list: list[str], index: dict[str, int]) -> int:
    """Append `value` to `global_list` on first sight; return its stable index.

    Shared by `build_index` and `load_lookup_table` so both code paths converge
    on identical `(files, anchors, id_to_pair)` triples for the same content.
    """
    if value not in index:
        index[value] = len(global_list)
        global_list.append(value)
    return index[value]


def build_index(
    chunk_paths: list[Path],
) -> tuple[list[str], list[str], dict[str, tuple[int, int]]]:
    """
    Merge every chunk into a global landmark index.

    Returns:
        (global_files, global_anchors, id_to_pair)
        where id_to_pair[id] = (global_file_index, global_anchor_index).

    File strings are normalized via `normalize_landmark_path` at index time, so
    `resolve_id`'s output matches the schema'd dump's normalized form
    regardless of source kind. Anchors are interned verbatim.

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

    for chunk_path in chunk_paths:
        chunk = parse_chunk(chunk_path)
        files = chunk['f']
        anchors = chunk['a']
        entries = chunk['e']

        file_map = [_intern(normalize_landmark_path(f), global_files, file_index) for f in files]
        anchor_map = [_intern(a, global_anchors, anchor_index) for a in anchors]

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


def normalize_landmark_path(raw: str) -> str:
    """Normalize a raw `_lx.js` file path to forward slashes and URL-decoded form.

    Raw paths in the chunk's `f` array use Windows-style backslashes with
    URL-encoded special characters (they are designed to drop into a JavaScript
    string that may become an `href`). Skill consumers should not each reinvent
    the normalization; the dump applies it once at emit time.
    """
    return urllib.parse.unquote(raw.replace('\\', '/'))


def build_dump_artifact(
    files: list[str],
    anchors: list[str],
    id_to_pair: dict[str, tuple[int, int]],
    source_path: str,
    chunks_count: int,
) -> dict:
    """Assemble the schema'd lookup-table artifact in memory.

    See references/landmark-lookup-table.md for the v1 schema. `captured_at` is
    the only non-deterministic field; everything else derives from the input.
    """
    captured_at = (
        datetime.datetime.now(datetime.timezone.utc)
        .isoformat(timespec='seconds')
        .replace('+00:00', 'Z')
    )
    landmarks: dict[str, dict[str, str]] = {}
    for landmark_id, (fi, ai) in id_to_pair.items():
        landmarks[landmark_id] = {
            'file': files[fi],
            'anchor': anchors[ai],
        }
    return {
        'format_version': LOOKUP_TABLE_FORMAT_VERSION,
        'landmarks': landmarks,
        'source': {
            'captured_at': captured_at,
            'chunks_found': chunks_count,
            'path': source_path,
            'type': 'local-directory',
        },
    }


def load_lookup_table(
    path: Path,
) -> tuple[list[str], list[str], dict[str, tuple[int, int]]]:
    """Read a dump artifact and return it in `build_index`'s triple shape.

    Returns (global_files, global_anchors, id_to_pair) so callers can reuse
    `resolve_id` without branching on the source kind. Raises ValueError on
    schema errors with a message that names the offending file.
    """
    try:
        text = path.read_text(encoding='utf-8')
    except (FileNotFoundError, OSError) as e:
        raise ValueError(f"lookup-table file unreadable ({path}): {e}") from e

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"lookup-table is not valid JSON ({path}): {e}") from e

    if not isinstance(data, dict):
        raise ValueError(f"lookup-table root must be a JSON object ({path})")

    if 'format_version' not in data:
        raise ValueError(
            f"lookup-table is missing required field 'format_version' ({path})"
        )

    version = data['format_version']
    # isinstance(x, bool) check is necessary because bool is a subclass of int
    # in Python (True == 1, False == 0). Floats like 1.0 also compare equal to
    # int 1 under `!=`, so we require a true int.
    if not isinstance(version, int) or isinstance(version, bool):
        raise ValueError(
            f"lookup-table format_version must be an integer, got "
            f"{type(version).__name__} ({path})"
        )
    if version != LOOKUP_TABLE_FORMAT_VERSION:
        raise ValueError(
            f"unsupported lookup-table format_version: {version} "
            f"(this resolver supports format_version {LOOKUP_TABLE_FORMAT_VERSION}) "
            f"({path})"
        )

    if 'landmarks' not in data:
        raise ValueError(
            f"lookup-table is missing required field 'landmarks' ({path})"
        )
    landmarks = data['landmarks']
    if not isinstance(landmarks, dict):
        raise ValueError(
            f"lookup-table field 'landmarks' must be a JSON object ({path})"
        )

    global_files: list[str] = []
    global_anchors: list[str] = []
    file_index: dict[str, int] = {}
    anchor_index: dict[str, int] = {}
    id_to_pair: dict[str, tuple[int, int]] = {}

    for landmark_id, entry in landmarks.items():
        if not isinstance(entry, dict):
            raise ValueError(
                f"lookup-table landmark {landmark_id!r} is not an object ({path})"
            )
        for field in ('file', 'anchor'):
            if field not in entry:
                raise ValueError(
                    f"lookup-table landmark {landmark_id!r} is missing "
                    f"required field {field!r} ({path})"
                )
            if not isinstance(entry[field], str):
                raise ValueError(
                    f"lookup-table landmark {landmark_id!r} field {field!r} "
                    f"is not a string ({path})"
                )
        fi = _intern(entry['file'], global_files, file_index)
        ai = _intern(entry['anchor'], global_anchors, anchor_index)
        id_to_pair[landmark_id] = (fi, ai)

    return global_files, global_anchors, id_to_pair


def _load_index(
    args: argparse.Namespace,
) -> tuple[list[str], list[str], dict[str, tuple[int, int]]]:
    """Build the resolver index from whichever source --from / --lookup-table set.

    Both args attributes are always defined because the argparse mutually
    exclusive group is registered with `required=True`; one is a path string,
    the other is None.

    Maps any source-loading exception to exit-code 2 via `error_log`.
    """
    if args.lookup_table:
        try:
            return load_lookup_table(Path(args.lookup_table))
        except ValueError as e:
            error_log(str(e))
            sys.exit(2)
    return _build_or_die(Path(args.source))


def cmd_resolve(args: argparse.Namespace) -> int:
    files, anchors, id_to_pair = _load_index(args)
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

    files, anchors, id_to_pair = _load_index(args)
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
    source_path = Path(args.source)
    try:
        chunk_paths = discover_chunks(source_path)
        debug_log(f"Discovered {len(chunk_paths)} chunk(s)")
        files, anchors, id_to_pair = build_index(chunk_paths)
    except (FileNotFoundError, ValueError, OSError) as e:
        error_log(str(e))
        return 2

    if args.table:
        # --table emits the v1 human-readable shape. Paths shown here are the
        # same normalized form the JSON artifact records (build_index applies
        # normalize_landmark_path at intern time), not the raw chunk strings.
        rows = {
            landmark_id: resolve_id(landmark_id, files, anchors, id_to_pair)
            for landmark_id in id_to_pair
        }
        if not rows:
            print("No landmarks found")
            return 0
        id_width = max(len(landmark_id) for landmark_id in rows)
        id_width = max(id_width, len("Landmark ID"))
        lines = [
            "Reverb 2.0 Landmark Index:",
            "=" * (id_width + 4 + 60),
            f"{'Landmark ID':<{id_width}}    Resolved Path",
            "-" * (id_width + 4 + 60),
        ]
        for landmark_id in sorted(rows):
            lines.append(f"{landmark_id:<{id_width}}    {rows[landmark_id]}")
        print('\n'.join(lines))
        return 0

    label = args.source_label if args.source_label else str(source_path.resolve())
    artifact = build_dump_artifact(
        files, anchors, id_to_pair, label, len(chunk_paths),
    )
    serialized = json.dumps(artifact, sort_keys=True, ensure_ascii=False, indent=2) + '\n'

    if args.out:
        try:
            Path(args.out).write_text(serialized, encoding='utf-8', newline='\n')
        except OSError as e:
            error_log(f"failed to write --out file ({args.out}): {e}")
            return 2
    else:
        # Bypass text-mode line-ending translation so Windows stdout emits LF,
        # matching the LF contract documented in references/landmark-lookup-table.md.
        sys.stdout.buffer.write(serialized.encode('utf-8'))

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Resolve Reverb 2.0 stable landmark URLs to direct file paths.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Resolve a single ID against chunks
    %(prog)s resolve e5d3d31c42d8d1d4 --from output/FAQs_lx.js

    # Resolve against a pre-built lookup-table artifact
    %(prog)s resolve abc12345 --lookup-table landmarks.json

    # Rewrite a published stable URL into a direct URL
    %(prog)s rewrite https://example.com/help/#/abc12345 --from output/

    # Dump the lookup-table artifact (stdout)
    %(prog)s dump --from output/

    # Dump to a file with a semantic source label
    %(prog)s dump --from output/ \\
        --out landmarks.json --source-label "ePublisher 2026.1 Help (en)"

See references/landmark-lookup-table.md for the lookup-table artifact schema.
"""
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    resolve_parser = subparsers.add_parser(
        'resolve',
        help='Resolve a landmark ID to a relative file path',
    )
    resolve_parser.add_argument('id', help='Landmark ID (opaque string)')
    resolve_source = resolve_parser.add_mutually_exclusive_group(required=True)
    resolve_source.add_argument(
        '--from', dest='source',
        help='Path to a *_lx.js chunk or a directory containing chunks',
    )
    resolve_source.add_argument(
        '--lookup-table', dest='lookup_table',
        help='Path to a dump artifact (see references/landmark-lookup-table.md)',
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
    rewrite_source = rewrite_parser.add_mutually_exclusive_group(required=True)
    rewrite_source.add_argument(
        '--from', dest='source',
        help='Path to a *_lx.js chunk or a directory containing chunks',
    )
    rewrite_source.add_argument(
        '--lookup-table', dest='lookup_table',
        help='Path to a dump artifact (see references/landmark-lookup-table.md)',
    )
    rewrite_parser.add_argument(
        '--base-url', dest='base_url', default=None,
        help='Replace the inferred URL prefix with this base URL',
    )

    dump_parser = subparsers.add_parser(
        'dump',
        help='Emit a schema\'d lookup-table artifact for the source',
    )
    dump_parser.add_argument(
        '--from', dest='source', required=True,
        help='Path to a *_lx.js chunk or a directory containing chunks',
    )
    dump_parser.add_argument(
        '--out', dest='out', default=None,
        help='Write JSON output to this file (default: stdout)',
    )
    dump_parser.add_argument(
        '--source-label', dest='source_label', default=None,
        help='Override the source.path field (recommended for committed artifacts)',
    )
    dump_parser.add_argument(
        '--table', action='store_true',
        help='Emit a human-readable table instead of the JSON artifact',
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
