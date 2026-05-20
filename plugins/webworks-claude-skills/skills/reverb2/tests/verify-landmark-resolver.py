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
import subprocess
import sys
import tempfile
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
SKILL_DIR = THIS_DIR.parent
SCRIPT_PATH = SKILL_DIR / 'scripts' / 'resolve-landmarks.py'
FIXTURE_DIR = THIS_DIR / 'fixtures'
SINGLE_CHUNK = FIXTURE_DIR / 'single-chunk_lx.js'
MULTI_DIR = FIXTURE_DIR  # contains both multi-chunk-a and multi-chunk-b


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
        rows = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        check("CLI dump: directory mode emits JSON", False, f"JSON decode error: {e}")
        return
    expected_ids = {
        'abc1234567890def', '12345678', 'getting-started-overview', 'page-only-id',
        'chunk_a_only', 'chunk_b_only', 'common_id',
    }
    missing = expected_ids - rows.keys()
    check(
        "CLI dump: emits union of every chunk's IDs",
        not missing,
        f"missing: {sorted(missing)}",
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

    passed = sum(1 for _, ok, _ in _results if ok)
    failed = sum(1 for _, ok, _ in _results if not ok)
    print(f"\n{YELLOW}Summary:{NC} {passed} passed, {failed} failed (of {len(_results)})")

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
