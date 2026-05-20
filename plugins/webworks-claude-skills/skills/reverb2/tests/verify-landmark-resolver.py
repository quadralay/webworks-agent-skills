#!/usr/bin/env python3
"""
verify-landmark-resolver.py

Standalone verifier for resolve-landmarks.py. Runs every U1 test scenario from
the issue #54 plan and prints PASS/FAIL lines. Exits 0 only when every scenario
passes.

Usage:
    python verify-landmark-resolver.py

Tests use fixtures in tests/fixtures/ and invoke the resolver both as a
Python module (for internal-function tests) and as a subprocess (for CLI
contract tests: exit codes, stdout JSON, error formatting).
"""

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
SKILL_DIR = THIS_DIR.parent
SCRIPT_PATH = SKILL_DIR / 'scripts' / 'resolve-landmarks.py'
FIXTURE_DIR = THIS_DIR / 'fixtures'
SINGLE_CHUNK = FIXTURE_DIR / 'single-chunk_lx.js'
MULTI_DIR = FIXTURE_DIR  # contains every *_lx.js fixture
UNICODE_CHUNK = FIXTURE_DIR / 'unicode-chunk_lx.js'
LOOKUP_TABLES_DIR = SKILL_DIR / 'references' / 'lookup-tables'


def _load_resolver_module():
    """Import resolve-landmarks.py despite the dash in its filename."""
    spec = importlib.util.spec_from_file_location('resolve_landmarks', SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


resolver = _load_resolver_module()

# Reuse ANSI color codes defined in resolve-landmarks.py so PASS/FAIL output
# stays in sync if the palette ever changes.
RED = resolver.RED
GREEN = resolver.GREEN
YELLOW = resolver.YELLOW
NC = resolver.NC

_results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = '') -> None:
    _results.append((name, condition, detail))
    if condition:
        print(f"{GREEN}PASS:{NC} {name}")
    else:
        print(f"{RED}FAIL:{NC} {name}" + (f" — {detail}" if detail else ''))


def run_cli(*cli_args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *cli_args],
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# Internal-function tests (import the resolver as a module)
# ---------------------------------------------------------------------------

def test_internal_parse_chunk() -> None:
    chunk = resolver.parse_chunk(SINGLE_CHUNK)
    check(
        "parse_chunk extracts f, a, e from single-chunk fixture",
        isinstance(chunk, dict) and set(chunk) >= {'f', 'a', 'e'},
        f"got keys: {sorted(chunk)}",
    )


def test_internal_build_index_single() -> None:
    files, anchors, id_to_pair = resolver.build_index([SINGLE_CHUNK])

    # Paragraph-level row overrides page-level for "abc1234567890def"
    fi, ai = id_to_pair['abc1234567890def']
    check(
        "paragraph-level overrides page-level (last write wins)",
        files[fi] == "Group/page.html" and anchors[ai] == "wwp100",
        f"got ({files[fi]!r}, {anchors[ai]!r})",
    )

    # Page-only ID resolves to bare file (empty anchor)
    fi, ai = id_to_pair['page-only-id']
    check(
        "page-only ID has empty anchor",
        files[fi] == "Group/page.html" and anchors[ai] == "",
        f"got ({files[fi]!r}, {anchors[ai]!r})",
    )

    # Out-of-range rows are skipped
    check(
        "out-of-range file index is skipped",
        "out-of-range-file" not in id_to_pair,
    )
    check(
        "out-of-range anchor index is skipped",
        "out-of-range-anchor" not in id_to_pair,
    )

    # Empty ID is skipped
    check(
        "empty landmark ID is skipped",
        "" not in id_to_pair,
    )


def test_internal_id_format_opacity() -> None:
    files, anchors, id_to_pair = resolver.build_index([SINGLE_CHUNK])

    # 16-char hex
    check(
        "ID format opacity: 16-char hex resolves",
        resolver.resolve_id("abc1234567890def", files, anchors, id_to_pair)
        == "Group/page.html#wwp100",
    )
    # 8-char hex
    check(
        "ID format opacity: 8-char hex resolves",
        resolver.resolve_id("12345678", files, anchors, id_to_pair)
        == "Group/page.html#wwp200",
    )
    # Pass-through source ID
    check(
        "ID format opacity: pass-through source ID resolves",
        resolver.resolve_id("getting-started-overview", files, anchors, id_to_pair)
        == "Group/other.html#wwp_anchor",
    )


def test_internal_multi_chunk_merge() -> None:
    chunks = sorted([
        FIXTURE_DIR / 'multi-chunk-a_lx.js',
        FIXTURE_DIR / 'multi-chunk-b_lx.js',
    ])
    files, anchors, id_to_pair = resolver.build_index(chunks)

    # The shared file string is interned to one global index, used by both chunks.
    fi_a, _ = id_to_pair['chunk_a_only']
    fi_b, _ = id_to_pair['chunk_b_only']
    check(
        "multi-chunk merge: shared file string interned to one global index",
        files[fi_a] == "shared/index.html" and fi_a == fi_b,
        f"chunk_a fi={fi_a}, chunk_b fi={fi_b}, file={files[fi_a]!r}",
    )

    # "common_id" appears in both chunks; chunk B is processed second, so its
    # binding wins (last write wins, mirroring the runtime).
    fi, ai = id_to_pair['common_id']
    check(
        "multi-chunk merge: last-write-wins across chunks",
        files[fi] == "groupB/page.html" and anchors[ai] == "wwp_b1",
        f"got ({files[fi]!r}, {anchors[ai]!r})",
    )


def test_internal_resolve_id_not_found() -> None:
    files, anchors, id_to_pair = resolver.build_index([SINGLE_CHUNK])
    check(
        "resolve_id returns None for unknown ID",
        resolver.resolve_id("nonexistent", files, anchors, id_to_pair) is None,
    )


def test_internal_empty_e_array(tmp_path: Path) -> None:
    fixture = tmp_path / 'empty_lx.js'
    fixture.write_text(
        'var landmarks = {"f": [], "a": [], "e": []};Landmarks.Advance(landmarks);',
        encoding='utf-8',
    )
    files, anchors, id_to_pair = resolver.build_index([fixture])
    check(
        "empty e array parses with no IDs",
        files == [] and anchors == [] and id_to_pair == {},
    )


def test_internal_malformed_chunk(tmp_path: Path) -> None:
    fixture = tmp_path / 'malformed_lx.js'
    fixture.write_text('this is not a landmarks file', encoding='utf-8')
    try:
        resolver.parse_chunk(fixture)
        check("malformed chunk raises ValueError", False, "parse_chunk returned without raising")
    except ValueError as e:
        check(
            "malformed chunk raises ValueError mentioning file path",
            str(fixture) in str(e),
            f"error: {e}",
        )


def test_internal_discover_chunks_single_file() -> None:
    result = resolver.discover_chunks(SINGLE_CHUNK)
    check(
        "discover_chunks returns [path] for a single .js file",
        result == [SINGLE_CHUNK],
    )


def test_internal_discover_chunks_directory() -> None:
    result = resolver.discover_chunks(FIXTURE_DIR)
    check(
        "discover_chunks returns sorted *_lx.js files from a directory",
        len(result) >= 3 and all(p.name.endswith('_lx.js') for p in result),
        f"found: {[p.name for p in result]}",
    )


# ---------------------------------------------------------------------------
# CLI contract tests (subprocess)
# ---------------------------------------------------------------------------

def test_cli_resolve_happy_single() -> None:
    result = run_cli('resolve', 'abc1234567890def', '--from', str(SINGLE_CHUNK))
    check(
        "CLI resolve: 16-char hex exits 0 with correct path",
        result.returncode == 0 and result.stdout.strip() == "Group/page.html#wwp100",
        f"rc={result.returncode}, stdout={result.stdout!r}",
    )


def test_cli_resolve_page_level_no_anchor() -> None:
    result = run_cli('resolve', 'page-only-id', '--from', str(SINGLE_CHUNK))
    check(
        "CLI resolve: page-level emits bare path with no trailing '#'",
        result.returncode == 0 and result.stdout.strip() == "Group/page.html",
        f"rc={result.returncode}, stdout={result.stdout!r}",
    )


def test_cli_resolve_directory_mode() -> None:
    result = run_cli('resolve', 'chunk_a_only', '--from', str(MULTI_DIR))
    check(
        "CLI resolve: directory mode globs *_lx.js chunks",
        result.returncode == 0 and result.stdout.strip() == "shared/index.html",
        f"rc={result.returncode}, stdout={result.stdout!r}",
    )


def test_cli_resolve_not_found() -> None:
    result = run_cli('resolve', 'no-such-id', '--from', str(SINGLE_CHUNK))
    check(
        "CLI resolve: unknown ID exits 1",
        result.returncode == 1,
        f"rc={result.returncode}, stderr={result.stderr!r}",
    )


def test_cli_resolve_not_found_json() -> None:
    result = run_cli('resolve', 'no-such-id', '--from', str(SINGLE_CHUNK), '--json')
    payload = None
    if result.stdout.strip():
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            payload = None
    check(
        "CLI resolve: --json on miss emits {error, id} to stdout, exits 1",
        result.returncode == 1
        and isinstance(payload, dict)
        and payload.get('error') == 'ID not found'
        and payload.get('id') == 'no-such-id',
        f"rc={result.returncode}, stdout={result.stdout!r}",
    )


def test_cli_dump_directory() -> None:
    result = run_cli('dump', '--from', str(MULTI_DIR))
    if result.returncode != 0:
        check("CLI dump: directory mode emits JSON", False, f"rc={result.returncode}, stderr={result.stderr!r}")
        return
    try:
        artifact = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        check("CLI dump: directory mode emits JSON", False, f"JSON decode error: {e}")
        return
    check(
        "CLI dump: artifact has schema'd top-level keys",
        isinstance(artifact, dict)
        and set(artifact) >= {'format_version', 'landmarks', 'source'}
        and artifact.get('format_version') == resolver.LOOKUP_TABLE_FORMAT_VERSION,
        f"got keys: {sorted(artifact) if isinstance(artifact, dict) else type(artifact).__name__}",
    )
    source = artifact.get('source', {})
    check(
        "CLI dump: source object has required fields",
        isinstance(source, dict)
        and set(source) >= {'type', 'path', 'chunks_found', 'captured_at'}
        and source.get('type') == 'local-directory',
        f"source: {source!r}",
    )
    landmarks = artifact.get('landmarks', {})
    expected_ids = {
        'abc1234567890def', '12345678', 'getting-started-overview', 'page-only-id',
        'chunk_a_only', 'chunk_b_only', 'common_id',
    }
    missing = expected_ids - landmarks.keys()
    check(
        "CLI dump: landmarks contain union of every chunk's IDs",
        not missing,
        f"missing: {sorted(missing)}",
    )
    sample = landmarks.get('abc1234567890def')
    check(
        "CLI dump: each landmark entry has {file, anchor}",
        isinstance(sample, dict) and set(sample) == {'file', 'anchor'},
        f"got: {sample!r}",
    )


def test_cli_dump_table() -> None:
    result = run_cli('dump', '--from', str(MULTI_DIR), '--table')
    check(
        "CLI dump --table: emits human-readable table",
        result.returncode == 0
        and 'Landmark ID' in result.stdout
        and 'common_id' in result.stdout,
        f"rc={result.returncode}, stdout (first 200 chars)={result.stdout[:200]!r}",
    )


def test_cli_malformed_exits_2() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        bad = Path(tmp) / 'bad_lx.js'
        bad.write_text('var landmarks = oops', encoding='utf-8')
        result = run_cli('resolve', 'anything', '--from', str(bad))
        check(
            "CLI: malformed chunk exits 2",
            result.returncode == 2,
            f"rc={result.returncode}, stderr={result.stderr!r}",
        )


def test_cli_missing_source_exits_2() -> None:
    result = run_cli('resolve', 'anything', '--from', '/nonexistent/path')
    check(
        "CLI: missing --from path exits 2",
        result.returncode == 2,
        f"rc={result.returncode}, stderr={result.stderr!r}",
    )


def test_cli_rewrite_full_stable_url() -> None:
    url = 'https://static.webworks.com/docs/epublisher/latest/help/#/abc1234567890def'
    result = run_cli('rewrite', url, '--from', str(SINGLE_CHUNK))
    expected = 'https://static.webworks.com/docs/epublisher/latest/help/Group/page.html#wwp100'
    check(
        "CLI rewrite: full stable URL → direct URL",
        result.returncode == 0 and result.stdout.strip() == expected,
        f"rc={result.returncode}, stdout={result.stdout!r}",
    )


def test_cli_rewrite_with_base_url() -> None:
    url = 'https://example.com/help/#/abc1234567890def'
    result = run_cli(
        'rewrite', url,
        '--from', str(SINGLE_CHUNK),
        '--base-url', 'https://other.example/docs/',
    )
    expected = 'https://other.example/docs/Group/page.html#wwp100'
    check(
        "CLI rewrite: --base-url replaces inferred prefix",
        result.returncode == 0 and result.stdout.strip() == expected,
        f"rc={result.returncode}, stdout={result.stdout!r}",
    )


def test_cli_rewrite_no_id_after_hash() -> None:
    result = run_cli('rewrite', 'https://example.com/help/#/', '--from', str(SINGLE_CHUNK))
    check(
        "CLI rewrite: stable URL with no ID after '#/' exits 1",
        result.returncode == 1,
        f"rc={result.returncode}, stderr={result.stderr!r}",
    )


# ---------------------------------------------------------------------------
# Dump-artifact and lookup-table consumer tests (issue #77)
# ---------------------------------------------------------------------------

_CAPTURED_AT_RE = re.compile(r'"captured_at"\s*:\s*"[^"]*"')


def _mask_captured_at(text: str) -> str:
    """Replace the `captured_at` value so two runs can be compared byte-for-byte."""
    return _CAPTURED_AT_RE.sub('"captured_at": "<MASKED>"', text)


def test_dump_deterministic(tmp_path: Path) -> None:
    out_a = tmp_path / 'a.json'
    out_b = tmp_path / 'b.json'
    r1 = run_cli(
        'dump', '--from', str(MULTI_DIR),
        '--out', str(out_a),
        '--source-label', 'fixture-determinism',
    )
    r2 = run_cli(
        'dump', '--from', str(MULTI_DIR),
        '--out', str(out_b),
        '--source-label', 'fixture-determinism',
    )
    text_a = out_a.read_text(encoding='utf-8') if r1.returncode == 0 else ''
    text_b = out_b.read_text(encoding='utf-8') if r2.returncode == 0 else ''
    check(
        "AE1: two dump runs are byte-identical modulo captured_at",
        r1.returncode == 0
        and r2.returncode == 0
        and _mask_captured_at(text_a) == _mask_captured_at(text_b),
        f"r1={r1.returncode}, r2={r2.returncode}, len_a={len(text_a)}, len_b={len(text_b)}",
    )


def test_dump_unicode_round_trip(tmp_path: Path) -> None:
    if not UNICODE_CHUNK.exists():
        check("AE2: Unicode round-trip", False, f"missing fixture {UNICODE_CHUNK}")
        return
    out = tmp_path / 'unicode.json'
    result = run_cli(
        'dump', '--from', str(UNICODE_CHUNK),
        '--out', str(out),
        '--source-label', 'unicode-test',
    )
    if result.returncode != 0:
        check("AE2: Unicode round-trip", False, f"rc={result.returncode}, stderr={result.stderr!r}")
        return

    raw_bytes = out.read_bytes()
    has_raw_japanese = '概要'.encode('utf-8') in raw_bytes
    has_raw_german = 'übersicht'.encode('utf-8') in raw_bytes
    has_no_escape = '\\u6982\\u8981'.encode('ascii') not in raw_bytes
    check(
        "AE2: Unicode IDs serialize as raw UTF-8, not \\uXXXX",
        has_raw_japanese and has_raw_german and has_no_escape,
        f"raw_jp={has_raw_japanese}, raw_de={has_raw_german}, no_escape={has_no_escape}",
    )

    parsed = json.loads(raw_bytes.decode('utf-8'))
    landmarks = parsed.get('landmarks', {})
    check(
        "AE2: Unicode IDs survive JSON round-trip with raw key form",
        '概要' in landmarks and 'übersicht' in landmarks and 'ascii-control' in landmarks,
        f"keys: {sorted(landmarks)!r}",
    )


def test_dump_path_normalization(tmp_path: Path) -> None:
    if not UNICODE_CHUNK.exists():
        check("R5: dump normalizes paths", False, f"missing fixture {UNICODE_CHUNK}")
        return
    out = tmp_path / 'normalize.json'
    result = run_cli(
        'dump', '--from', str(UNICODE_CHUNK),
        '--out', str(out), '--source-label', 'normalize',
    )
    if result.returncode != 0:
        check("R5: dump normalizes paths", False, f"rc={result.returncode}, stderr={result.stderr!r}")
        return
    parsed = json.loads(out.read_text(encoding='utf-8'))
    overview_file = parsed['landmarks']['概要']['file']
    decoded_file = parsed['landmarks']['ascii-control']['file']
    check(
        "R5: backslashes replaced with forward slashes",
        '\\' not in overview_file and overview_file == 'Topics/overview.html',
        f"got: {overview_file!r}",
    )
    check(
        "R5: URL-encoded characters decoded",
        decoded_file == 'Topics/getting started.html',
        f"got: {decoded_file!r}",
    )


def test_lookup_table_parity_with_from(tmp_path: Path) -> None:
    snapshot = tmp_path / 'parity.json'
    dump_result = run_cli(
        'dump', '--from', str(MULTI_DIR),
        '--out', str(snapshot),
        '--source-label', 'parity-fixture',
    )
    if dump_result.returncode != 0:
        check("AE3: parity dump emits", False, f"rc={dump_result.returncode}")
        return

    parsed = json.loads(snapshot.read_text(encoding='utf-8'))
    landmark_ids = list(parsed['landmarks'])
    mismatches: list[tuple[str, str, str]] = []
    for landmark_id in landmark_ids:
        from_result = run_cli('resolve', landmark_id, '--from', str(MULTI_DIR))
        lt_result = run_cli('resolve', landmark_id, '--lookup-table', str(snapshot))
        if from_result.returncode != 0 or lt_result.returncode != 0:
            mismatches.append((landmark_id, '<error>', '<error>'))
            continue
        if from_result.stdout != lt_result.stdout:
            mismatches.append((landmark_id, from_result.stdout, lt_result.stdout))
    check(
        f"AE3: --lookup-table parity with --from across {len(landmark_ids)} IDs",
        not mismatches,
        f"mismatches: {mismatches[:3]!r}",
    )


def test_cli_rewrite_lookup_table(tmp_path: Path) -> None:
    snapshot = tmp_path / 'rewrite.json'
    dump_result = run_cli(
        'dump', '--from', str(SINGLE_CHUNK),
        '--out', str(snapshot),
        '--source-label', 'rewrite-fixture',
    )
    if dump_result.returncode != 0:
        check("R9: rewrite via lookup-table", False, f"dump rc={dump_result.returncode}")
        return
    url = 'https://example.com/help/#/abc1234567890def'
    from_result = run_cli('rewrite', url, '--from', str(SINGLE_CHUNK))
    lt_result = run_cli('rewrite', url, '--lookup-table', str(snapshot))
    check(
        "R9: rewrite via --lookup-table matches --from",
        from_result.returncode == 0
        and lt_result.returncode == 0
        and from_result.stdout == lt_result.stdout,
        f"from={from_result.stdout!r}, lt={lt_result.stdout!r}",
    )


def test_cli_mutex_resolve(tmp_path: Path) -> None:
    snapshot = tmp_path / 'mutex.json'
    run_cli(
        'dump', '--from', str(SINGLE_CHUNK),
        '--out', str(snapshot), '--source-label', 'mutex',
    )
    result = run_cli(
        'resolve', 'abc1234567890def',
        '--from', str(SINGLE_CHUNK),
        '--lookup-table', str(snapshot),
    )
    check(
        "AE4: resolve --from + --lookup-table exits 2 with mutex error",
        result.returncode == 2 and 'not allowed' in result.stderr,
        f"rc={result.returncode}, stderr={result.stderr!r}",
    )


def test_cli_mutex_rewrite(tmp_path: Path) -> None:
    snapshot = tmp_path / 'mutex-rewrite.json'
    run_cli(
        'dump', '--from', str(SINGLE_CHUNK),
        '--out', str(snapshot), '--source-label', 'mutex-rewrite',
    )
    result = run_cli(
        'rewrite', 'https://example.com/help/#/abc1234567890def',
        '--from', str(SINGLE_CHUNK),
        '--lookup-table', str(snapshot),
    )
    check(
        "AE4: rewrite --from + --lookup-table exits 2 with mutex error",
        result.returncode == 2 and 'not allowed' in result.stderr,
        f"rc={result.returncode}, stderr={result.stderr!r}",
    )


def test_cli_source_required(tmp_path: Path) -> None:
    result = run_cli('resolve', 'anything')
    check(
        "Resolve without --from or --lookup-table exits 2",
        result.returncode == 2 and ('--from' in result.stderr or '--lookup-table' in result.stderr),
        f"rc={result.returncode}, stderr={result.stderr!r}",
    )


def test_cli_unsupported_format_version(tmp_path: Path) -> None:
    artifact = tmp_path / 'v99.json'
    artifact.write_text(
        json.dumps({"format_version": 99, "landmarks": {}, "source": {}}),
        encoding='utf-8',
    )
    result = run_cli('resolve', 'anything', '--lookup-table', str(artifact))
    check(
        "AE5: format_version 99 exits 2 with version named in message",
        result.returncode == 2 and '99' in result.stderr and 'format_version' in result.stderr,
        f"rc={result.returncode}, stderr={result.stderr!r}",
    )


def test_cli_missing_format_version(tmp_path: Path) -> None:
    artifact = tmp_path / 'no-version.json'
    artifact.write_text(json.dumps({"landmarks": {}}), encoding='utf-8')
    result = run_cli('resolve', 'anything', '--lookup-table', str(artifact))
    check(
        "R11: missing format_version field exits 2 with field named",
        result.returncode == 2 and 'format_version' in result.stderr,
        f"rc={result.returncode}, stderr={result.stderr!r}",
    )


def test_cli_lookup_table_malformed_json(tmp_path: Path) -> None:
    artifact = tmp_path / 'bad.json'
    artifact.write_text('not json at all', encoding='utf-8')
    result = run_cli('resolve', 'anything', '--lookup-table', str(artifact))
    check(
        "Lookup-table that is not valid JSON exits 2 with file path in message",
        result.returncode == 2 and str(artifact) in result.stderr,
        f"rc={result.returncode}, stderr={result.stderr!r}",
    )


def test_cli_lookup_table_missing_landmarks(tmp_path: Path) -> None:
    artifact = tmp_path / 'no-landmarks.json'
    artifact.write_text(json.dumps({"format_version": 1}), encoding='utf-8')
    result = run_cli('resolve', 'anything', '--lookup-table', str(artifact))
    check(
        "Lookup-table missing 'landmarks' field exits 2 with field named",
        result.returncode == 2 and 'landmarks' in result.stderr,
        f"rc={result.returncode}, stderr={result.stderr!r}",
    )


def test_cli_lookup_table_unknown_id(tmp_path: Path) -> None:
    snapshot = tmp_path / 'unknown.json'
    run_cli(
        'dump', '--from', str(SINGLE_CHUNK),
        '--out', str(snapshot), '--source-label', 'unknown',
    )
    result = run_cli('resolve', 'no-such-id', '--lookup-table', str(snapshot))
    check(
        "Unknown ID via --lookup-table exits 1 (same as --from)",
        result.returncode == 1,
        f"rc={result.returncode}, stderr={result.stderr!r}",
    )


def test_dump_out_file_matches_stdout(tmp_path: Path) -> None:
    out = tmp_path / 'out.json'
    file_result = run_cli(
        'dump', '--from', str(SINGLE_CHUNK),
        '--out', str(out), '--source-label', 'stdout-parity',
    )
    stdout_result = run_cli(
        'dump', '--from', str(SINGLE_CHUNK), '--source-label', 'stdout-parity',
    )
    if file_result.returncode != 0 or stdout_result.returncode != 0:
        check("R2: --out matches stdout", False, f"rc1={file_result.returncode}, rc2={stdout_result.returncode}")
        return
    file_bytes = out.read_bytes()
    stdout_bytes = stdout_result.stdout.encode('utf-8')
    check(
        "R2: --out file content matches stdout content (modulo captured_at)",
        _mask_captured_at(file_bytes.decode('utf-8'))
        == _mask_captured_at(stdout_bytes.decode('utf-8')),
        f"file={len(file_bytes)} bytes, stdout={len(stdout_bytes)} bytes",
    )
    check(
        "R2: --out file uses LF line endings",
        b'\r\n' not in file_bytes,
        f"contains CRLF: {b'\r\n' in file_bytes}",
    )
    check(
        "R2: --out file ends with exactly one trailing newline",
        file_bytes.endswith(b'\n') and not file_bytes.endswith(b'\n\n'),
        f"last 4 bytes: {file_bytes[-4:]!r}",
    )


def test_committed_artifact_freshness() -> None:
    """Re-emit each committed lookup-table and compare to the file on disk.

    Skips cleanly when the underlying source chunks are unreachable. For the
    stand-in artifact, the source is the in-tree fixtures dir; for any real
    artifact, set REVERB_HELP_MIRROR=<chunks-dir> to point at a help install.
    """
    if not LOOKUP_TABLES_DIR.exists():
        check(
            "Committed-artifact freshness drift check",
            False,
            f"missing directory: {LOOKUP_TABLES_DIR}",
        )
        return

    artifacts = sorted(LOOKUP_TABLES_DIR.glob('*.json'))
    if not artifacts:
        check(
            "Committed-artifact freshness drift check",
            False,
            f"no committed artifacts found in {LOOKUP_TABLES_DIR}",
        )
        return

    env_help_mirror = os.environ.get('REVERB_HELP_MIRROR')

    for artifact_path in artifacts:
        try:
            committed = json.loads(artifact_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as e:
            check(f"freshness({artifact_path.name})", False, f"unreadable: {e}")
            continue

        committed_label = committed.get('source', {}).get('path', '')
        source_dir: Path | None = None
        if 'tests-fixtures-stand-in' in artifact_path.name:
            source_dir = MULTI_DIR
        elif env_help_mirror:
            source_dir = Path(env_help_mirror)

        if source_dir is None or not source_dir.exists():
            print(f"{YELLOW}SKIP:{NC} freshness({artifact_path.name}) "
                  f"— source unreachable (label={committed_label!r})")
            continue

        with tempfile.TemporaryDirectory() as tmp:
            re_emit = Path(tmp) / 'fresh.json'
            result = run_cli(
                'dump', '--from', str(source_dir),
                '--out', str(re_emit),
                '--source-label', committed_label,
            )
            if result.returncode != 0:
                check(
                    f"freshness({artifact_path.name})",
                    False,
                    f"re-emit failed rc={result.returncode}, stderr={result.stderr!r}",
                )
                continue
            fresh_text = re_emit.read_text(encoding='utf-8')
            committed_text = artifact_path.read_text(encoding='utf-8')
            check(
                f"freshness({artifact_path.name}): re-emit matches committed (modulo captured_at)",
                _mask_captured_at(fresh_text) == _mask_captured_at(committed_text),
                f"committed_label={committed_label!r}",
            )


def main() -> int:
    if not SCRIPT_PATH.exists():
        print(f"{RED}FAIL:{NC} resolver script not found at {SCRIPT_PATH}", file=sys.stderr)
        return 2
    if not SINGLE_CHUNK.exists():
        print(f"{RED}FAIL:{NC} single-chunk fixture missing at {SINGLE_CHUNK}", file=sys.stderr)
        return 2

    print(f"{YELLOW}Running landmark-resolver verification...{NC}\n")

    test_internal_parse_chunk()
    test_internal_build_index_single()
    test_internal_id_format_opacity()
    test_internal_multi_chunk_merge()
    test_internal_resolve_id_not_found()
    test_internal_discover_chunks_single_file()
    test_internal_discover_chunks_directory()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        test_internal_empty_e_array(tmp_path)
        test_internal_malformed_chunk(tmp_path)

    test_cli_resolve_happy_single()
    test_cli_resolve_page_level_no_anchor()
    test_cli_resolve_directory_mode()
    test_cli_resolve_not_found()
    test_cli_resolve_not_found_json()
    test_cli_dump_directory()
    test_cli_dump_table()
    test_cli_malformed_exits_2()
    test_cli_missing_source_exits_2()
    test_cli_rewrite_full_stable_url()
    test_cli_rewrite_with_base_url()
    test_cli_rewrite_no_id_after_hash()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        test_dump_deterministic(tmp_path)
        test_dump_unicode_round_trip(tmp_path)
        test_dump_path_normalization(tmp_path)
        test_lookup_table_parity_with_from(tmp_path)
        test_cli_rewrite_lookup_table(tmp_path)
        test_cli_mutex_resolve(tmp_path)
        test_cli_mutex_rewrite(tmp_path)
        test_cli_source_required(tmp_path)
        test_cli_unsupported_format_version(tmp_path)
        test_cli_missing_format_version(tmp_path)
        test_cli_lookup_table_malformed_json(tmp_path)
        test_cli_lookup_table_missing_landmarks(tmp_path)
        test_cli_lookup_table_unknown_id(tmp_path)
        test_dump_out_file_matches_stdout(tmp_path)

    test_committed_artifact_freshness()

    passed = sum(1 for _, ok, _ in _results if ok)
    failed = sum(1 for _, ok, _ in _results if not ok)
    print(f"\n{YELLOW}Summary:{NC} {passed} passed, {failed} failed (of {len(_results)})")

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
