#!/usr/bin/env python3
"""
verify-landmark-resolver.py

Standalone verifier for resolve-landmarks.py. Runs every test scenario and
prints PASS/FAIL lines. Exits 0 only when every scenario passes.

Usage:
    python verify-landmark-resolver.py

Tests use fixtures in tests/fixtures/ and invoke the resolver both as a
Python module (for internal-function tests, including stub-fetcher state-
machine tests) and as a subprocess (for CLI contract tests: exit codes,
stdout JSON, error formatting). No network access is required.
"""

import importlib.util
import json
import os
import socket
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

THIS_DIR = Path(__file__).resolve().parent
SKILL_DIR = THIS_DIR.parent
SCRIPT_PATH = SKILL_DIR / 'scripts' / 'resolve-landmarks.py'
FIXTURE_DIR = THIS_DIR / 'fixtures'
SINGLE_CHUNK = FIXTURE_DIR / 'single-chunk_lx.js'
MULTI_DIR = FIXTURE_DIR  # contains every *_lx.js fixture
UNICODE_CHUNK = FIXTURE_DIR / 'unicode-ids_lx.js'
LANDING_WITH_HASH = FIXTURE_DIR / 'landing-with-hash.html'
LANDING_NO_HASH = FIXTURE_DIR / 'landing-no-hash.html'
LX_MANIFEST = FIXTURE_DIR / 'lx-manifest.json'


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


def run_cli(*cli_args: str, env: Optional[dict] = None) -> subprocess.CompletedProcess:
    proc_env = os.environ.copy()
    if env:
        proc_env.update(env)
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *cli_args],
        capture_output=True,
        text=True,
        env=proc_env,
    )


# ---------------------------------------------------------------------------
# Stub fetcher used by remote-mode internal tests
# ---------------------------------------------------------------------------


class StubFetcher:
    """
    Records every call and returns canned (status, body) pairs.

    `responses` maps URL string -> (status, body) for static responses, or maps
    URL -> a callable `(method) -> (status, body)` for per-method handling.
    """

    def __init__(self, responses: dict):
        self.calls: list[tuple[str, str, float]] = []
        self.responses = responses

    def __call__(self, url, *, method='GET', timeout=10.0):
        self.calls.append((url, method, timeout))
        if url not in self.responses:
            raise resolver.RemoteFetchError(url, f"stub: no response for {url}")
        entry = self.responses[url]
        if callable(entry):
            return entry(method)
        return entry

    def reset_calls(self) -> None:
        self.calls = []


# ---------------------------------------------------------------------------
# Internal-function tests
# ---------------------------------------------------------------------------

def test_internal_parse_chunk() -> None:
    chunk = resolver.parse_chunk(SINGLE_CHUNK)
    check(
        "parse_chunk extracts f, a, e from single-chunk fixture",
        isinstance(chunk, dict) and set(chunk) >= {'f', 'a', 'e'},
        f"got keys: {sorted(chunk)}",
    )


def test_internal_build_index_single() -> None:
    files, anchors, id_to_pair, _ = resolver.build_index([SINGLE_CHUNK])

    fi, ai = id_to_pair['abc1234567890def']
    check(
        "paragraph-level overrides page-level (last write wins)",
        files[fi] == "Group/page.html" and anchors[ai] == "wwp100",
        f"got ({files[fi]!r}, {anchors[ai]!r})",
    )

    fi, ai = id_to_pair['page-only-id']
    check(
        "page-only ID has empty anchor",
        files[fi] == "Group/page.html" and anchors[ai] == "",
        f"got ({files[fi]!r}, {anchors[ai]!r})",
    )

    check(
        "out-of-range file index is skipped",
        "out-of-range-file" not in id_to_pair,
    )
    check(
        "out-of-range anchor index is skipped",
        "out-of-range-anchor" not in id_to_pair,
    )

    check(
        "empty landmark ID is skipped",
        "" not in id_to_pair,
    )


def test_internal_id_format_opacity() -> None:
    files, anchors, id_to_pair, _ = resolver.build_index([SINGLE_CHUNK])

    check(
        "ID format opacity: 16-char hex resolves",
        resolver.resolve_id("abc1234567890def", files, anchors, id_to_pair)
        == "Group/page.html#wwp100",
    )
    check(
        "ID format opacity: 8-char hex resolves",
        resolver.resolve_id("12345678", files, anchors, id_to_pair)
        == "Group/page.html#wwp200",
    )
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
    files, anchors, id_to_pair, _ = resolver.build_index(chunks)

    fi_a, _ = id_to_pair['chunk_a_only']
    fi_b, _ = id_to_pair['chunk_b_only']
    check(
        "multi-chunk merge: shared file string interned to one global index",
        files[fi_a] == "shared/index.html" and fi_a == fi_b,
        f"chunk_a fi={fi_a}, chunk_b fi={fi_b}, file={files[fi_a]!r}",
    )

    fi, ai = id_to_pair['common_id']
    check(
        "multi-chunk merge: last-write-wins across chunks",
        files[fi] == "groupB/page.html" and anchors[ai] == "wwp_b1",
        f"got ({files[fi]!r}, {anchors[ai]!r})",
    )


def test_internal_resolve_id_not_found() -> None:
    files, anchors, id_to_pair, _ = resolver.build_index([SINGLE_CHUNK])
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
    files, anchors, id_to_pair, _ = resolver.build_index([fixture])
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
# Internal-function tests — build_index_from_texts
# ---------------------------------------------------------------------------

def test_internal_build_index_from_texts() -> None:
    text = SINGLE_CHUNK.read_bytes()
    files, anchors, id_to_pair, _ = resolver.build_index_from_texts(
        [(str(SINGLE_CHUNK), text)]
    )
    check(
        "build_index_from_texts mirrors build_index on the same chunk bytes",
        resolver.resolve_id("abc1234567890def", files, anchors, id_to_pair)
        == "Group/page.html#wwp100",
    )


# ---------------------------------------------------------------------------
# Internal-function tests — URL fragment decoder
# ---------------------------------------------------------------------------

def test_unicode_id_resolves_with_unquote_in_index() -> None:
    # Sanity: the fixture contains the raw Unicode key.
    files, anchors, id_to_pair, _ = resolver.build_index([UNICODE_CHUNK])
    check(
        "unicode-ids fixture contains raw '概要' ID",
        '概要' in id_to_pair,
    )
    check(
        "unicode-ids fixture: '概要' resolves to expected path with spaces",
        resolver.resolve_id('概要', files, anchors, id_to_pair)
        == "Advanced Customizations/_xslt-extensions.04.1.html#wwp_overview",
    )


# ---------------------------------------------------------------------------
# Internal-function tests — HTTP primitives with stubbed urlopen
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, body: bytes, status: int = 200):
        self._body = body
        self.status = status

    def read(self):
        return self._body

    def getcode(self):
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeOpener:
    def __init__(self, behavior):
        self.behavior = behavior
        self.calls = []

    def open(self, url_or_request, timeout=None):
        # Normalize argument to a URL string.
        url = url_or_request if isinstance(url_or_request, str) else url_or_request.full_url
        self.calls.append((url, timeout))
        if callable(self.behavior):
            result = self.behavior(len(self.calls) - 1, url, timeout)
        else:
            result = self.behavior
        if isinstance(result, BaseException):
            raise result
        return result


def _install_fake_opener(behavior):
    """Replace _build_opener with one returning a fake. Returns the fake."""
    fake = _FakeOpener(behavior)
    resolver._build_opener = lambda: fake
    return fake


def _restore_default_opener():
    resolver._build_opener = _build_opener_default


_build_opener_default = resolver._build_opener


def test_http_get_happy_path() -> None:
    fake = _install_fake_opener(_FakeResponse(b"hello world"))
    try:
        body = resolver.http_get("https://example.com/x", timeout=5.0, max_attempts=3, base_delay=0.0)
        check(
            "http_get returns bytes on 2xx response",
            body == b"hello world" and len(fake.calls) == 1,
            f"body={body!r}, calls={fake.calls}",
        )
    finally:
        _restore_default_opener()


def test_http_get_transient_retry() -> None:
    sleep_calls: list[float] = []

    def behavior(attempt, url, timeout):
        if attempt < 2:
            return urllib.error.URLError(socket.timeout("simulated timeout"))
        return _FakeResponse(b"recovered")

    fake = _install_fake_opener(behavior)
    original_sleep = resolver._sleep
    resolver._sleep = lambda secs: sleep_calls.append(secs)
    try:
        body = resolver.http_get("https://example.com/x", timeout=5.0, max_attempts=3, base_delay=1.0)
        check(
            "http_get retries transient URLError (timeout) and recovers",
            body == b"recovered" and len(fake.calls) == 3 and sleep_calls == [1.0, 2.0],
            f"body={body!r}, calls={len(fake.calls)}, sleeps={sleep_calls}",
        )
    finally:
        resolver._sleep = original_sleep
        _restore_default_opener()


def test_http_get_exhausted_retries() -> None:
    def behavior(attempt, url, timeout):
        return urllib.error.URLError(socket.timeout("persistent timeout"))

    fake = _install_fake_opener(behavior)
    original_sleep = resolver._sleep
    resolver._sleep = lambda secs: None
    try:
        try:
            resolver.http_get("https://example.com/x", timeout=5.0, max_attempts=3, base_delay=1.0)
            check("http_get raises RemoteFetchError after exhausted retries", False, "did not raise")
        except resolver.RemoteFetchError as e:
            check(
                "http_get raises RemoteFetchError after exhausted retries (URL in message)",
                "https://example.com/x" in str(e) and len(fake.calls) == 3,
                f"calls={len(fake.calls)}, error={e}",
            )
    finally:
        resolver._sleep = original_sleep
        _restore_default_opener()


def test_http_get_4xx_not_retried() -> None:
    def behavior(attempt, url, timeout):
        return urllib.error.HTTPError(url, 404, "Not Found", {}, None)

    fake = _install_fake_opener(behavior)
    original_sleep = resolver._sleep
    resolver._sleep = lambda secs: None
    try:
        try:
            resolver.http_get("https://example.com/x", timeout=5.0, max_attempts=3, base_delay=1.0)
            check("http_get does not retry on 4xx", False, "did not raise")
        except resolver.RemoteFetchError as e:
            check(
                "http_get does not retry on 4xx; raises with URL and status",
                "https://example.com/x" in str(e) and "404" in str(e) and len(fake.calls) == 1,
                f"calls={len(fake.calls)}, error={e}",
            )
    finally:
        resolver._sleep = original_sleep
        _restore_default_opener()


def test_http_get_5xx_retried() -> None:
    def behavior(attempt, url, timeout):
        if attempt < 2:
            return urllib.error.HTTPError(url, 503, "Service Unavailable", {}, None)
        return _FakeResponse(b"recovered after 5xx")

    fake = _install_fake_opener(behavior)
    original_sleep = resolver._sleep
    resolver._sleep = lambda secs: None
    try:
        body = resolver.http_get("https://example.com/x", timeout=5.0, max_attempts=3, base_delay=1.0)
        check(
            "http_get retries on 5xx and recovers",
            body == b"recovered after 5xx" and len(fake.calls) == 3,
            f"body={body!r}, calls={len(fake.calls)}",
        )
    finally:
        resolver._sleep = original_sleep
        _restore_default_opener()


def test_proxy_handler_constructed_from_getproxies() -> None:
    captured: list = []
    real_build_opener = urllib.request.build_opener
    original_getproxies = urllib.request.getproxies

    def fake_getproxies():
        return {'https': 'http://proxy.example:8080'}

    def fake_build_opener(*handlers):
        for h in handlers:
            if isinstance(h, urllib.request.ProxyHandler):
                captured.append(h.proxies)
        return real_build_opener(*handlers)

    urllib.request.getproxies = fake_getproxies
    urllib.request.build_opener = fake_build_opener
    try:
        resolver._build_opener_default = resolver._build_opener  # backup
        opener = resolver._build_opener()
        check(
            "_build_opener installs ProxyHandler built from getproxies()",
            len(captured) == 1 and captured[0].get('https') == 'http://proxy.example:8080',
            f"captured={captured}",
        )
    finally:
        urllib.request.build_opener = real_build_opener
        urllib.request.getproxies = original_getproxies


# ---------------------------------------------------------------------------
# Internal-function tests — cache layout and state machine
# ---------------------------------------------------------------------------


def test_default_cache_root_windows() -> None:
    original_env = os.environ.get('LOCALAPPDATA')
    original_system = resolver.platform.system
    resolver.platform.system = lambda: 'Windows'
    os.environ['LOCALAPPDATA'] = r'C:\Users\test\AppData\Local'
    try:
        root = resolver.default_cache_root()
        expected = Path(r'C:\Users\test\AppData\Local') / 'webworks' / 'reverb-landmarks'
        check(
            "default_cache_root: Windows uses %LOCALAPPDATA%",
            root == expected,
            f"got {root}, expected {expected}",
        )
    finally:
        if original_env is None:
            del os.environ['LOCALAPPDATA']
        else:
            os.environ['LOCALAPPDATA'] = original_env
        resolver.platform.system = original_system


def test_default_cache_root_linux_xdg() -> None:
    original_xdg = os.environ.get('XDG_CACHE_HOME')
    original_system = resolver.platform.system
    resolver.platform.system = lambda: 'Linux'
    if 'XDG_CACHE_HOME' in os.environ:
        del os.environ['XDG_CACHE_HOME']
    try:
        root = resolver.default_cache_root()
        expected = Path.home() / '.cache' / 'webworks' / 'reverb-landmarks'
        check(
            "default_cache_root: Linux without XDG_CACHE_HOME falls back to ~/.cache",
            root == expected,
            f"got {root}",
        )
    finally:
        if original_xdg is not None:
            os.environ['XDG_CACHE_HOME'] = original_xdg
        resolver.platform.system = original_system


def test_default_cache_root_macos() -> None:
    original_system = resolver.platform.system
    resolver.platform.system = lambda: 'Darwin'
    try:
        root = resolver.default_cache_root()
        expected = Path.home() / 'Library' / 'Caches' / 'webworks' / 'reverb-landmarks'
        check(
            "default_cache_root: macOS uses ~/Library/Caches",
            root == expected,
            f"got {root}",
        )
    finally:
        resolver.platform.system = original_system


def test_base_cache_dir_with_path() -> None:
    root = Path('/cache-root')
    base_dir = resolver.base_cache_dir(root, 'https://static.example.com/docs/help/')
    expected = root / 'static.example.com' / 'docs%2Fhelp%2F'
    check(
        "base_cache_dir: encodes nested path as percent-encoded segment",
        base_dir == expected,
        f"got {base_dir}, expected {expected}",
    )


def test_base_cache_dir_root_url() -> None:
    root = Path('/cache-root')
    base_dir = resolver.base_cache_dir(root, 'https://static.example.com/')
    expected = root / 'static.example.com'
    check(
        "base_cache_dir: root path produces no doubled separator",
        base_dir == expected,
        f"got {base_dir}, expected {expected}",
    )


def test_base_cache_dir_trailing_slash_distinct() -> None:
    root = Path('/cache-root')
    with_slash = resolver.base_cache_dir(root, 'https://x.example/help/')
    no_slash = resolver.base_cache_dir(root, 'https://x.example/help')
    check(
        "base_cache_dir: trailing-slash sensitivity preserved",
        with_slash != no_slash,
        f"with_slash={with_slash}, no_slash={no_slash}",
    )


def test_read_cache_manifest_missing(tmp_path: Path) -> None:
    base_dir = tmp_path / 'absent'
    check(
        "read_cache_manifest returns None for missing directory",
        resolver.read_cache_manifest(base_dir) is None,
    )


def test_read_cache_manifest_malformed(tmp_path: Path) -> None:
    base_dir = tmp_path / 'malformed'
    base_dir.mkdir()
    (base_dir / '_manifest.json').write_text('not json at all', encoding='utf-8')
    check(
        "read_cache_manifest returns None for malformed JSON",
        resolver.read_cache_manifest(base_dir) is None,
    )


def test_write_cache_atomic_replaces_old_files(tmp_path: Path) -> None:
    base_dir = tmp_path / 'base'
    # Prior cache with extra files.
    base_dir.mkdir()
    (base_dir / 'OLD_lx.js').write_bytes(b"old chunk")
    (base_dir / '_manifest.json').write_text('{"old": true}', encoding='utf-8')

    new_chunks = {'A_lx.js': b"chunk A", 'B_lx.js': b"chunk B"}
    manifest = {'generation_hash': 'newhash', 'last_poll_ts': 1234.5, 'chunks': [
        {'name': 'A_lx.js', 'url': 'https://x/A_lx.js'},
        {'name': 'B_lx.js', 'url': 'https://x/B_lx.js'},
    ]}
    resolver.write_cache_atomic(base_dir, manifest, new_chunks)

    contents = set(p.name for p in base_dir.iterdir())
    check(
        "write_cache_atomic replaces prior cache (old files gone)",
        contents == {'A_lx.js', 'B_lx.js', '_manifest.json'},
        f"contents={contents}",
    )

    read_back = resolver.read_cache_manifest(base_dir)
    check(
        "write_cache_atomic round-trips manifest contents",
        read_back is not None and read_back.get('generation_hash') == 'newhash',
        f"manifest={read_back}",
    )


def test_cache_decision_branches() -> None:
    check(
        "cache_decision: no_cache=True forces refetch",
        resolver.cache_decision({'last_poll_ts': 0}, ttl_seconds=3600, now=0, no_cache=True) == 'refetch',
    )
    check(
        "cache_decision: missing manifest forces refetch",
        resolver.cache_decision(None, ttl_seconds=3600, now=0, no_cache=False) == 'refetch',
    )
    check(
        "cache_decision: within TTL returns 'use'",
        resolver.cache_decision({'last_poll_ts': 100}, ttl_seconds=3600, now=200, no_cache=False) == 'use',
    )
    check(
        "cache_decision: past TTL returns 'poll'",
        resolver.cache_decision({'last_poll_ts': 100}, ttl_seconds=10, now=200, no_cache=False) == 'poll',
    )
    check(
        "cache_decision: missing last_poll_ts forces refetch",
        resolver.cache_decision({'generation_hash': 'x'}, ttl_seconds=3600, now=0, no_cache=False) == 'refetch',
    )


def test_cache_partial_write_isolated(tmp_path: Path) -> None:
    base_dir = tmp_path / 'partial-base'
    base_dir.mkdir()
    (base_dir / 'good_lx.js').write_bytes(b"good")
    (base_dir / '_manifest.json').write_text(
        json.dumps({'generation_hash': 'h1', 'last_poll_ts': 1.0, 'chunks': [
            {'name': 'good_lx.js', 'url': 'https://x/good_lx.js'},
        ]}),
        encoding='utf-8',
    )
    # Simulate a partial write that did not yet swap.
    staging = tmp_path / 'partial-base.tmp'
    staging.mkdir()
    (staging / '_manifest.json').write_text('{"halfway": true}', encoding='utf-8')

    manifest = resolver.read_cache_manifest(base_dir)
    check(
        "partial-write tolerance: pre-swap reader sees old cache (not the .tmp staging dir)",
        manifest is not None and manifest.get('generation_hash') == 'h1',
        f"manifest={manifest}",
    )


# ---------------------------------------------------------------------------
# Internal-function tests — chunk discovery
# ---------------------------------------------------------------------------


def test_extract_chunk_srcs_basic() -> None:
    html = LANDING_WITH_HASH.read_text(encoding='utf-8')
    srcs = resolver.extract_chunk_srcs_from_html(html, 'https://x.example/help/')
    expected = [
        'https://x.example/help/A_lx.js',
        'https://x.example/help/B_lx.js',
        'https://x.example/help/C_lx.js',
    ]
    check(
        "extract_chunk_srcs_from_html: returns abs URLs in source order, no dupes, ignores non-_lx.js",
        srcs == expected,
        f"got {srcs}",
    )


def test_extract_chunk_srcs_quote_variants() -> None:
    html = """
    <script src="A_lx.js"></script>
    <script src='B_lx.js'></script>
    <script type="text/javascript" src="C_lx.js" defer></script>
    <script src="not_landmarks.js"></script>
    """
    srcs = resolver.extract_chunk_srcs_from_html(html, 'https://x.example/help/')
    check(
        "extract_chunk_srcs_from_html: tolerant of quote and attribute variants",
        srcs == [
            'https://x.example/help/A_lx.js',
            'https://x.example/help/B_lx.js',
            'https://x.example/help/C_lx.js',
        ],
        f"got {srcs}",
    )


def test_extract_generation_hash() -> None:
    html = LANDING_WITH_HASH.read_text(encoding='utf-8')
    check(
        "extract_generation_hash: recovers constant from landing fixture",
        resolver.extract_generation_hash(html) == "abc123def456",
    )
    check(
        "extract_generation_hash: const declaration variant",
        resolver.extract_generation_hash('const GLOBAL_GENERATION_HASH = "xyz789";') == "xyz789",
    )
    check(
        "extract_generation_hash: returns None when absent",
        resolver.extract_generation_hash(LANDING_NO_HASH.read_text(encoding='utf-8')) is None,
    )


def _make_remote_chunks_responses(landing_html: str, manifest_status: int = 404) -> dict:
    """Build a stub-fetcher response map for a base URL exposing the unicode fixture chunks."""
    chunk_bytes = SINGLE_CHUNK.read_bytes()
    base = 'https://x.example/help/'
    responses = {
        base: (200, landing_html.encode('utf-8')),
        base + '_lx-manifest.json': (manifest_status, b'{}'),
        base + 'A_lx.js': (200, chunk_bytes),
        base + 'B_lx.js': (200, chunk_bytes),
        base + 'C_lx.js': (200, chunk_bytes),
    }
    return responses


def test_remote_chunk_texts_first_call_writes_cache(tmp_path: Path) -> None:
    landing_html = LANDING_WITH_HASH.read_text(encoding='utf-8')
    fetcher = StubFetcher(_make_remote_chunks_responses(landing_html))
    cache_dir = tmp_path / 'cache'

    chunks = resolver.remote_chunk_texts(
        base_url='https://x.example/help/',
        cache_dir=cache_dir,
        ttl=3600.0,
        no_cache=False,
        fetcher=fetcher,
        now=1000.0,
    )
    chunk_urls = [u for u, _ in chunks]
    check(
        "remote_chunk_texts: first call discovers and fetches every chunk",
        chunk_urls == [
            'https://x.example/help/A_lx.js',
            'https://x.example/help/B_lx.js',
            'https://x.example/help/C_lx.js',
        ],
        f"chunk_urls={chunk_urls}",
    )

    cached_names = set(p.name for p in cache_dir.iterdir())
    check(
        "remote_chunk_texts: first call populates cache directory",
        cached_names == {'A_lx.js', 'B_lx.js', 'C_lx.js', '_manifest.json'},
        f"cached={cached_names}",
    )

    manifest = resolver.read_cache_manifest(cache_dir)
    check(
        "remote_chunk_texts: cached manifest records generation hash",
        manifest is not None and manifest.get('generation_hash') == 'abc123def456',
        f"manifest={manifest}",
    )


def test_remote_chunk_texts_second_call_uses_cache(tmp_path: Path) -> None:
    landing_html = LANDING_WITH_HASH.read_text(encoding='utf-8')
    fetcher = StubFetcher(_make_remote_chunks_responses(landing_html))
    cache_dir = tmp_path / 'cache'

    resolver.remote_chunk_texts(
        base_url='https://x.example/help/',
        cache_dir=cache_dir, ttl=3600.0, no_cache=False, fetcher=fetcher, now=1000.0,
    )
    fetcher.reset_calls()

    chunks = resolver.remote_chunk_texts(
        base_url='https://x.example/help/',
        cache_dir=cache_dir, ttl=3600.0, no_cache=False, fetcher=fetcher, now=1500.0,
    )
    check(
        "remote_chunk_texts: second call within TTL makes zero fetches",
        len(fetcher.calls) == 0 and len(chunks) == 3,
        f"calls={fetcher.calls}, chunks={len(chunks)}",
    )


def test_remote_chunk_texts_hash_unchanged_reuses_cache(tmp_path: Path) -> None:
    landing_html = LANDING_WITH_HASH.read_text(encoding='utf-8')
    fetcher = StubFetcher(_make_remote_chunks_responses(landing_html))
    cache_dir = tmp_path / 'cache'

    resolver.remote_chunk_texts(
        base_url='https://x.example/help/',
        cache_dir=cache_dir, ttl=3600.0, no_cache=False, fetcher=fetcher, now=1000.0,
    )
    fetcher.reset_calls()

    # Past TTL — should poll the landing page but skip chunk re-fetch.
    chunks = resolver.remote_chunk_texts(
        base_url='https://x.example/help/',
        cache_dir=cache_dir, ttl=10.0, no_cache=False, fetcher=fetcher, now=2000.0,
    )
    landing_calls = [c for c in fetcher.calls if c[0] == 'https://x.example/help/' and c[1] == 'GET']
    chunk_calls = [c for c in fetcher.calls if c[0].endswith('_lx.js')]
    check(
        "remote_chunk_texts: hash unchanged after TTL polls landing only, no chunk re-fetch",
        len(landing_calls) == 1 and len(chunk_calls) == 0 and len(chunks) == 3,
        f"calls={fetcher.calls}",
    )


def test_remote_chunk_texts_hash_changed_refetches(tmp_path: Path) -> None:
    landing_html_v1 = LANDING_WITH_HASH.read_text(encoding='utf-8')
    landing_html_v2 = landing_html_v1.replace('abc123def456', 'xyz999')
    base = 'https://x.example/help/'
    cache_dir = tmp_path / 'cache'
    fetcher = StubFetcher(_make_remote_chunks_responses(landing_html_v1))
    resolver.remote_chunk_texts(
        base_url=base, cache_dir=cache_dir, ttl=3600.0, no_cache=False, fetcher=fetcher, now=1000.0,
    )

    new_responses = _make_remote_chunks_responses(landing_html_v2)
    new_responses[base + 'A_lx.js'] = (200, b"new chunk A")
    new_responses[base + 'B_lx.js'] = (200, b"new chunk B")
    new_responses[base + 'C_lx.js'] = (200, b"new chunk C")
    fetcher2 = StubFetcher(new_responses)

    chunks = resolver.remote_chunk_texts(
        base_url=base, cache_dir=cache_dir, ttl=10.0, no_cache=False, fetcher=fetcher2, now=2000.0,
    )
    chunk_bodies = [body for _, body in chunks]
    check(
        "remote_chunk_texts: hash changed forces re-fetch of every chunk",
        chunk_bodies == [b"new chunk A", b"new chunk B", b"new chunk C"],
        f"bodies={chunk_bodies}",
    )

    manifest = resolver.read_cache_manifest(cache_dir)
    check(
        "remote_chunk_texts: cache manifest updated to new generation hash",
        manifest is not None and manifest.get('generation_hash') == 'xyz999',
        f"manifest={manifest}",
    )


def test_remote_chunk_texts_no_cache_forces_refetch(tmp_path: Path) -> None:
    landing_html = LANDING_WITH_HASH.read_text(encoding='utf-8')
    fetcher = StubFetcher(_make_remote_chunks_responses(landing_html))
    cache_dir = tmp_path / 'cache'

    resolver.remote_chunk_texts(
        base_url='https://x.example/help/',
        cache_dir=cache_dir, ttl=3600.0, no_cache=False, fetcher=fetcher, now=1000.0,
    )
    first_calls = len(fetcher.calls)
    fetcher.reset_calls()

    resolver.remote_chunk_texts(
        base_url='https://x.example/help/',
        cache_dir=cache_dir, ttl=3600.0, no_cache=True, fetcher=fetcher, now=1100.0,
    )
    chunk_fetches = [c for c in fetcher.calls if c[0].endswith('_lx.js')]
    check(
        "remote_chunk_texts: --no-cache re-fetches every chunk despite fresh cache",
        len(chunk_fetches) == 3 and first_calls > 0,
        f"first_calls={first_calls}, second chunk fetches={len(chunk_fetches)}",
    )


def test_remote_chunk_texts_no_hash_warns_and_succeeds(tmp_path: Path, capture_stderr) -> None:
    landing_html = LANDING_NO_HASH.read_text(encoding='utf-8')
    responses = _make_remote_chunks_responses(landing_html)
    fetcher = StubFetcher(responses)
    cache_dir = tmp_path / 'cache'

    chunks = resolver.remote_chunk_texts(
        base_url='https://x.example/help/',
        cache_dir=cache_dir, ttl=3600.0, no_cache=False, fetcher=fetcher, now=1000.0,
    )
    manifest = resolver.read_cache_manifest(cache_dir)
    stderr_text = capture_stderr.read()
    check(
        "remote_chunk_texts: missing GLOBAL_GENERATION_HASH warns and stores null",
        len(chunks) == 2 and manifest is not None and manifest.get('generation_hash') is None
        and 'GLOBAL_GENERATION_HASH' in stderr_text,
        f"chunks={len(chunks)}, manifest={manifest}, stderr={stderr_text[:200]!r}",
    )


def test_remote_chunk_texts_empty_discovery_raises(tmp_path: Path) -> None:
    base = 'https://empty.example/help/'
    fetcher = StubFetcher({
        base: (200, b"<html><body>no scripts here</body></html>"),
        base + '_lx-manifest.json': (404, b''),
    })
    cache_dir = tmp_path / 'cache'
    try:
        resolver.remote_chunk_texts(
            base_url=base, cache_dir=cache_dir, ttl=3600.0, no_cache=False, fetcher=fetcher,
            now=1000.0,
        )
        check("remote_chunk_texts: empty discovery raises", False, "no error raised")
    except resolver.RemoteFetchError as e:
        check(
            "remote_chunk_texts: empty discovery raises RemoteFetchError naming base URL and methods",
            base in str(e) and 'manifest' in str(e).lower() and 'scrape' in str(e).lower(),
            f"error={e}",
        )


def test_remote_chunk_texts_manifest_preferred(tmp_path: Path) -> None:
    base = 'https://m.example/help/'
    landing_html = LANDING_WITH_HASH.read_text(encoding='utf-8')
    manifest_bytes = LX_MANIFEST.read_bytes()
    responses = {
        base: (200, landing_html.encode('utf-8')),
        base + '_lx-manifest.json': (200, manifest_bytes),
        base + 'A_lx.js': (200, b"chunk A from manifest"),
        base + 'B_lx.js': (200, b"chunk B from manifest"),
    }
    fetcher = StubFetcher(responses)
    cache_dir = tmp_path / 'cache'

    chunks = resolver.remote_chunk_texts(
        base_url=base, cache_dir=cache_dir, ttl=3600.0, no_cache=False, fetcher=fetcher, now=1000.0,
    )
    chunk_bytes = [body for _, body in chunks]
    fetched_urls = [c[0] for c in fetcher.calls if c[1] == 'GET']
    check(
        "remote_chunk_texts: manifest probe preferred over HTML scrape",
        chunk_bytes == [b"chunk A from manifest", b"chunk B from manifest"]
        and (base + 'C_lx.js') not in fetched_urls,
        f"chunk_bytes={chunk_bytes}, fetched={fetched_urls}",
    )


# ---------------------------------------------------------------------------
# CLI contract tests
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
    landmarks = artifact.get('landmarks', {}) if isinstance(artifact, dict) else {}
    expected_ids = {
        'abc1234567890def', '12345678', 'getting-started-overview', 'page-only-id',
        'chunk_a_only', 'chunk_b_only', 'common_id',
    }
    missing = expected_ids - landmarks.keys()
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


# ---------------------------------------------------------------------------
# CLI contract tests — URL fragment decode (local mode)
# ---------------------------------------------------------------------------


def test_cli_rewrite_percent_encoded_unicode_local() -> None:
    encoded_url = 'https://example.com/help/#/%E6%A6%82%E8%A6%81'
    decoded_url = 'https://example.com/help/#/概要'
    enc_result = run_cli('rewrite', encoded_url, '--from', str(UNICODE_CHUNK))
    dec_result = run_cli('rewrite', decoded_url, '--from', str(UNICODE_CHUNK))
    expected_suffix = '_xslt-extensions.04.1.html#wwp_overview'
    check(
        "CLI rewrite (local): percent-encoded Unicode ID resolves identically to decoded form",
        enc_result.returncode == 0
        and dec_result.returncode == 0
        and enc_result.stdout.strip() == dec_result.stdout.strip()
        and enc_result.stdout.strip().endswith(expected_suffix),
        f"enc={enc_result.stdout!r}, dec={dec_result.stdout!r}",
    )


def test_cli_rewrite_malformed_percent_exits_1() -> None:
    bad_url = 'https://example.com/help/#/%E6%A6'  # truncated percent sequence
    result = run_cli('rewrite', bad_url, '--from', str(UNICODE_CHUNK))
    check(
        "CLI rewrite: malformed percent sequence exits 1 and stderr names the URL",
        result.returncode == 1 and bad_url in result.stderr,
        f"rc={result.returncode}, stderr={result.stderr!r}",
    )


def test_cli_rewrite_ascii_id_no_double_decode() -> None:
    url = 'https://example.com/help/#/abc1234567890def'
    result = run_cli('rewrite', url, '--from', str(SINGLE_CHUNK))
    expected = 'https://example.com/help/Group/page.html#wwp100'
    check(
        "CLI rewrite: ASCII landmark ID unchanged after unquote step",
        result.returncode == 0 and result.stdout.strip() == expected,
        f"stdout={result.stdout!r}",
    )


def test_cli_rewrite_literal_plus_preserved() -> None:
    # Create a fixture chunk with a literal '+' in the ID so unquote (not
    # unquote_plus) is verified — unquote_plus would convert '+' to ' ' and break the lookup.
    with tempfile.TemporaryDirectory() as tmp:
        fixture = Path(tmp) / 'plus_lx.js'
        fixture.write_text(
            'var landmarks = {"f": ["x.html"], "a": ["a1"], "e": [[0, 0, "a+b"]]};Landmarks.Advance(landmarks);',
            encoding='utf-8',
        )
        url = 'https://example.com/help/#/a+b'
        result = run_cli('rewrite', url, '--from', str(fixture))
        check(
            "CLI rewrite: literal '+' in ID is preserved (unquote, not unquote_plus)",
            result.returncode == 0 and 'x.html#a1' in result.stdout,
            f"rc={result.returncode}, stdout={result.stdout!r}, stderr={result.stderr!r}",
        )


# ---------------------------------------------------------------------------
# CLI contract tests — remote mode & flag plumbing
# ---------------------------------------------------------------------------


def test_cli_rewrite_mutual_exclusion() -> None:
    url = 'https://example.com/help/#/abc1234567890def'
    result = run_cli(
        'rewrite', url,
        '--from', str(SINGLE_CHUNK),
        '--remote-base-url', 'https://other.example/help/',
    )
    check(
        "CLI rewrite: --from and --remote-base-url are mutually exclusive",
        result.returncode != 0 and 'not allowed' in result.stderr.lower(),
        f"rc={result.returncode}, stderr={result.stderr!r}",
    )


def test_cli_rewrite_from_wins_over_http_url() -> None:
    # Auto-infer should NOT fire when --from is supplied.
    url = 'https://static.webworks.com/docs/epublisher/latest/help/#/abc1234567890def'
    result = run_cli('rewrite', url, '--from', str(SINGLE_CHUNK))
    expected = 'https://static.webworks.com/docs/epublisher/latest/help/Group/page.html#wwp100'
    check(
        "CLI rewrite: --from takes priority over auto-infer for HTTP URLs",
        result.returncode == 0 and result.stdout.strip() == expected,
        f"stdout={result.stdout!r}",
    )


def test_cli_no_source_and_non_http_url_exits_1() -> None:
    result = run_cli('rewrite', 'relative-doc/#/abc')
    check(
        "CLI rewrite: no source and non-HTTP URL exits 1 with clear error",
        result.returncode == 1 and 'no source' in result.stderr.lower(),
        f"rc={result.returncode}, stderr={result.stderr!r}",
    )


def test_cli_resolve_remote_mode_via_proxy_script(tmp_path: Path) -> None:
    """End-to-end CLI test: rewrite an HTTP URL via a stub fetcher.

    The stub lives in a separate wrapper script that monkey-patches
    resolver.default_fetcher before invoking main(). We launch the wrapper as a
    subprocess so we exercise the same CLI parsing the resolver normally goes
    through.
    """
    base = 'https://stub.example/help/'
    landing_html = LANDING_WITH_HASH.read_text(encoding='utf-8')
    unicode_chunk = UNICODE_CHUNK.read_bytes()

    wrapper = tmp_path / 'wrapper.py'
    wrapper.write_text(_make_wrapper_script(
        base=base,
        landing_html=landing_html.encode('utf-8'),
        chunk_payload=unicode_chunk,
    ), encoding='utf-8')

    cache_dir = tmp_path / 'cli-cache'
    proc = subprocess.run(
        [sys.executable, str(wrapper),
         'rewrite', base + '#/概要',
         '--cache-dir', str(cache_dir),
         '--cache-ttl', '3600',
         '--http-timeout', '5'],
        capture_output=True, text=True, env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
    )
    expected = 'https://stub.example/help/Advanced%20Customizations/_xslt-extensions.04.1.html#wwp_overview'
    check(
        "CLI rewrite (remote, auto-inferred): resolves and percent-quotes path portion",
        proc.returncode == 0 and proc.stdout.strip() == expected,
        f"rc={proc.returncode}, stdout={proc.stdout!r}, stderr={proc.stderr!r}",
    )

    # A second call against the same cache makes no fetcher calls because
    # the wrapper's stub crashes loudly if called twice — verified by reading
    # the wrapper's lock file.
    second_cache = tmp_path / 'second-cache'
    wrapper_once = tmp_path / 'wrapper_once.py'
    wrapper_once.write_text(_make_wrapper_script(
        base=base,
        landing_html=landing_html.encode('utf-8'),
        chunk_payload=unicode_chunk,
    ), encoding='utf-8')
    proc2 = subprocess.run(
        [sys.executable, str(wrapper_once),
         'rewrite', base + '#/概要',
         '--cache-dir', str(second_cache),
         '--cache-ttl', '3600',
         '--http-timeout', '5'],
        capture_output=True, text=True, env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
    )
    # Reuse the same cache: second invocation should skip every fetch.
    proc3 = subprocess.run(
        [sys.executable, str(wrapper_once),
         'resolve', '概要',
         '--remote-base-url', base,
         '--cache-dir', str(second_cache),
         '--cache-ttl', '3600',
         '--http-timeout', '5',
         '--block-fetcher'],
        capture_output=True, text=True, env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
    )
    check(
        "CLI resolve (remote): second call against same cache requires no network",
        proc2.returncode == 0 and proc3.returncode == 0
        and proc3.stdout.strip() == 'Advanced Customizations/_xslt-extensions.04.1.html#wwp_overview',
        f"proc2 rc={proc2.returncode}, stderr={proc2.stderr!r}; proc3 rc={proc3.returncode}, stdout={proc3.stdout!r}, stderr={proc3.stderr!r}",
    )


def _make_wrapper_script(base: str, landing_html: bytes, chunk_payload: bytes) -> str:
    """Build a wrapper that monkey-patches default_fetcher to a stub before calling main()."""
    return f'''
import importlib.util
import sys

SCRIPT_PATH = {str(SCRIPT_PATH)!r}
spec = importlib.util.spec_from_file_location("resolve_landmarks", SCRIPT_PATH)
resolver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resolver)

BASE = {base!r}
LANDING_HTML = {landing_html!r}
CHUNK_PAYLOAD = {chunk_payload!r}

block_fetcher = '--block-fetcher' in sys.argv
sys.argv = [a for a in sys.argv if a != '--block-fetcher']

responses = {{
    BASE: (200, LANDING_HTML),
    BASE + '_lx-manifest.json': (404, b''),
    BASE + 'A_lx.js': (200, CHUNK_PAYLOAD),
    BASE + 'B_lx.js': (200, CHUNK_PAYLOAD),
    BASE + 'C_lx.js': (200, CHUNK_PAYLOAD),
}}

def stub(url, *, method='GET', timeout=10.0):
    if block_fetcher:
        raise resolver.RemoteFetchError(url, "fetcher should not have been called (cache hit expected)")
    if url not in responses:
        raise resolver.RemoteFetchError(url, "stub: no response")
    return responses[url]

resolver.default_fetcher = stub

sys.exit(resolver.main())
'''


def test_cli_dump_remote_mode(tmp_path: Path) -> None:
    base = 'https://dump.example/help/'
    landing_html = LANDING_WITH_HASH.read_text(encoding='utf-8')
    chunk = SINGLE_CHUNK.read_bytes()

    wrapper = tmp_path / 'wrap.py'
    wrapper.write_text(_make_wrapper_script(
        base=base,
        landing_html=landing_html.encode('utf-8'),
        chunk_payload=chunk,
    ), encoding='utf-8')
    cache_dir = tmp_path / 'cache'
    proc = subprocess.run(
        [sys.executable, str(wrapper),
         'dump', '--remote-base-url', base,
         '--cache-dir', str(cache_dir),
         '--cache-ttl', '3600'],
        capture_output=True, text=True,
        env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
    )
    try:
        artifact = json.loads(proc.stdout)
    except json.JSONDecodeError:
        artifact = None
    landmarks = artifact.get('landmarks', {}) if isinstance(artifact, dict) else {}
    check(
        "CLI dump --remote-base-url: emits same JSON shape as local dump",
        proc.returncode == 0
        and isinstance(artifact, dict)
        and 'abc1234567890def' in landmarks,
        f"rc={proc.returncode}, stderr={proc.stderr!r}, stdout (first 200)={proc.stdout[:200]!r}",
    )


def test_cli_remote_fetch_failure_exits_2(tmp_path: Path) -> None:
    base = 'https://fail.example/help/'
    wrapper = tmp_path / 'wrap.py'
    wrapper.write_text(f'''
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("resolve_landmarks", {str(SCRIPT_PATH)!r})
resolver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resolver)

BASE = {base!r}

def stub(url, *, method='GET', timeout=10.0):
    if url == BASE:
        return (404, b'')
    raise resolver.RemoteFetchError(url, "stub: no response")

resolver.default_fetcher = stub
sys.exit(resolver.main())
''', encoding='utf-8')
    cache_dir = tmp_path / 'cache'
    proc = subprocess.run(
        [sys.executable, str(wrapper),
         'resolve', 'abc',
         '--remote-base-url', base,
         '--cache-dir', str(cache_dir),
         '--cache-ttl', '3600'],
        capture_output=True, text=True,
        env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
    )
    check(
        "CLI remote: 404 on landing page exits 2 and names the URL",
        proc.returncode == 2 and base in proc.stderr,
        f"rc={proc.returncode}, stderr={proc.stderr!r}",
    )


# ---------------------------------------------------------------------------
# Dump artifact + lookup-table consumer path
# ---------------------------------------------------------------------------


EPUBLISHER_FIXTURE = FIXTURE_DIR / 'epublisher-designer-2026.1-help-lookup.json'


def test_cli_dump_deterministic(tmp_path: Path) -> None:
    """Two dump runs against the same source produce byte-identical output
    (excluding the per-run captured_at timestamp)."""
    out_a = tmp_path / 'a.json'
    out_b = tmp_path / 'b.json'
    r1 = run_cli('dump', '--from', str(MULTI_DIR), '--out', str(out_a))
    r2 = run_cli('dump', '--from', str(MULTI_DIR), '--out', str(out_b))
    if r1.returncode != 0 or r2.returncode != 0:
        check("dump is byte-deterministic across runs", False,
              f"r1.rc={r1.returncode}, r2.rc={r2.returncode}")
        return
    bytes_a = out_a.read_bytes()
    bytes_b = out_b.read_bytes()
    # Strip captured_at line so the test does not depend on identical wall clocks
    # between subprocess invocations.
    def _strip_ts(b: bytes) -> bytes:
        return b'\n'.join(line for line in b.split(b'\n') if b'"captured_at"' not in line)
    check(
        "dump is byte-deterministic across runs (excluding captured_at)",
        _strip_ts(bytes_a) == _strip_ts(bytes_b),
        f"differ; first {min(80, len(bytes_a))} bytes a={bytes_a[:80]!r} b={bytes_b[:80]!r}",
    )


def test_cli_dump_structured_shape(tmp_path: Path) -> None:
    """The structured dump shape has format_version, source, landmarks."""
    out = tmp_path / 'dump.json'
    r = run_cli('dump', '--from', str(MULTI_DIR), '--out', str(out))
    if r.returncode != 0:
        check("dump structured shape", False, f"rc={r.returncode}, stderr={r.stderr!r}")
        return
    artifact = json.loads(out.read_text(encoding='utf-8'))
    src = artifact.get('source', {})
    landmarks = artifact.get('landmarks', {})
    expected_chunk_count = len(list(MULTI_DIR.glob('*_lx.js')))
    nested_shape_ok = all(
        isinstance(v, dict) and set(v.keys()) == {'file', 'anchor'}
        for v in landmarks.values()
    )
    check(
        "dump structured shape has {format_version, source, landmarks}",
        set(artifact.keys()) == {'format_version', 'source', 'landmarks'}
        and artifact['format_version'] == 1
        and src.get('type') == 'local-directory'
        and src.get('path') == str(MULTI_DIR)
        and src.get('chunks_found') == expected_chunk_count
        and isinstance(src.get('captured_at'), str)
        and nested_shape_ok,
        f"artifact_keys={sorted(artifact.keys())}, src={src}, "
        f"expected chunks_found={expected_chunk_count}, nested_shape_ok={nested_shape_ok}",
    )


def test_cli_dump_sorted_keys(tmp_path: Path) -> None:
    """The top-level keys and landmark keys appear in sorted order in the file text."""
    out = tmp_path / 'dump.json'
    r = run_cli('dump', '--from', str(MULTI_DIR), '--out', str(out))
    if r.returncode != 0:
        check("dump output is sorted", False, f"rc={r.returncode}, stderr={r.stderr!r}")
        return
    text = out.read_text(encoding='utf-8')
    # Top-level: format_version < landmarks < source alphabetically.
    fmt_pos = text.find('"format_version"')
    lm_pos = text.find('"landmarks"')
    src_pos = text.find('"source"')
    top_ordered = 0 <= fmt_pos < lm_pos < src_pos
    # Landmark keys: '12345678' < 'abc1234567890def' alphabetically.
    pos_8 = text.find('"12345678"')
    pos_abc = text.find('"abc1234567890def"')
    landmark_ordered = 0 <= pos_8 < pos_abc
    check(
        "dump output has sorted top-level and landmark keys",
        top_ordered and landmark_ordered,
        f"top_ordered={top_ordered} (fmt={fmt_pos}, lm={lm_pos}, src={src_pos}); "
        f"landmark_ordered={landmark_ordered} (12345678={pos_8}, abc...={pos_abc})",
    )


def test_cli_dump_unicode_preservation(tmp_path: Path) -> None:
    """Unicode landmark IDs appear as raw UTF-8 bytes, not escaped \\uXXXX."""
    out = tmp_path / 'dump.json'
    r = run_cli('dump', '--from', str(UNICODE_CHUNK), '--out', str(out))
    if r.returncode != 0:
        check("dump preserves Unicode IDs", False, f"rc={r.returncode}, stderr={r.stderr!r}")
        return
    raw = out.read_bytes()
    has_raw_overview = '概要'.encode('utf-8') in raw
    has_escaped_unicode = b'"\\u' in raw
    check(
        "dump preserves raw Unicode IDs (no \\u-escaping in landmark keys)",
        has_raw_overview and not has_escaped_unicode,
        f"raw_overview={has_raw_overview}, has_escapes={has_escaped_unicode}",
    )


def test_cli_round_trip_equivalence_chunks(tmp_path: Path) -> None:
    """Every ID resolves to the same path via --lookup-table as via --from.

    The dump itself goes through the CLI (the artifact contract is what we care
    about), but the per-ID comparison runs in-process so adding a 1003-landmark
    fixture later doesn't spawn 2000+ subprocesses.
    """
    out = tmp_path / 'dump.json'
    rd = run_cli('dump', '--from', str(MULTI_DIR), '--out', str(out))
    if rd.returncode != 0:
        check("round-trip equivalence (chunks)", False, f"dump rc={rd.returncode}")
        return
    artifact = json.loads(out.read_text(encoding='utf-8'))
    files, anchors, id_to_pair, _ = resolver.build_index(
        sorted(MULTI_DIR.glob('*_lx.js'))
    )
    mismatches: list[str] = []
    for landmark_id in sorted(artifact['landmarks']):
        from_chunks = resolver.resolve_id(landmark_id, files, anchors, id_to_pair)
        from_lookup = resolver.resolve_id_from_lookup(landmark_id, artifact)
        if from_chunks != from_lookup:
            mismatches.append(
                f"{landmark_id!r}: chunks={from_chunks!r} lookup={from_lookup!r}"
            )
    count = len(artifact['landmarks'])
    check(
        f"round-trip equivalence: {count} IDs match between chunk index and lookup-table",
        not mismatches,
        '; '.join(mismatches[:3]) + (f" ...({len(mismatches)} mismatches)" if mismatches else ''),
    )


def test_cli_round_trip_equivalence_unicode(tmp_path: Path) -> None:
    """Unicode IDs round-trip through both resolve and rewrite paths."""
    out = tmp_path / 'dump.json'
    rd = run_cli('dump', '--from', str(UNICODE_CHUNK), '--out', str(out))
    if rd.returncode != 0:
        check("round-trip equivalence (unicode resolve)", False, f"dump rc={rd.returncode}")
        return
    a = run_cli('resolve', '概要', '--from', str(UNICODE_CHUNK))
    b = run_cli('resolve', '概要', '--lookup-table', str(out))
    check(
        "round-trip equivalence: Unicode ID via resolve",
        a.returncode == 0 and b.returncode == 0 and a.stdout == b.stdout,
        f"from out={a.stdout!r}; lookup out={b.stdout!r}",
    )

    url = 'http://example.com/help/#/%E6%A6%82%E8%A6%81'
    ra = run_cli('rewrite', url, '--from', str(UNICODE_CHUNK))
    rb = run_cli('rewrite', url, '--lookup-table', str(out), '--base-url', 'http://example.com/help/')
    # Without --base-url the lookup-table path falls through to the URL prefix
    # branch; supply --base-url so both invocations produce the same prefix.
    check(
        "round-trip equivalence: Unicode ID via rewrite (with --base-url)",
        ra.returncode == 0 and rb.returncode == 0 and ra.stdout == rb.stdout,
        f"from out={ra.stdout!r}; lookup out={rb.stdout!r}",
    )


def _write_lookup(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def test_cli_format_version_validation(tmp_path: Path) -> None:
    """Unsupported / missing format_version exits 2 with a clear stderr message."""
    bad = tmp_path / 'v99.json'
    _write_lookup(bad, {
        "format_version": 99,
        "source": {"type": "local-directory", "path": "/x", "chunks_found": 0,
                   "captured_at": "2026-05-21T00:00:00Z"},
        "landmarks": {},
    })
    r = run_cli('resolve', 'some_id', '--lookup-table', str(bad))
    check(
        "format_version=99 exits 2 and stderr names the unsupported version",
        r.returncode == 2 and 'unsupported format_version' in r.stderr and '99' in r.stderr,
        f"rc={r.returncode}, stderr={r.stderr!r}",
    )

    zero = tmp_path / 'v0.json'
    _write_lookup(zero, {
        "format_version": 0,
        "source": {"type": "local-directory", "path": "/x", "chunks_found": 0,
                   "captured_at": "2026-05-21T00:00:00Z"},
        "landmarks": {},
    })
    rz = run_cli('resolve', 'some_id', '--lookup-table', str(zero))
    check(
        "format_version=0 (boundary) exits 2",
        rz.returncode == 2 and 'unsupported format_version' in rz.stderr,
        f"rc={rz.returncode}, stderr={rz.stderr!r}",
    )

    missing = tmp_path / 'missing.json'
    _write_lookup(missing, {
        "source": {"type": "local-directory", "path": "/x", "chunks_found": 0,
                   "captured_at": "2026-05-21T00:00:00Z"},
        "landmarks": {},
    })
    rm = run_cli('resolve', 'some_id', '--lookup-table', str(missing))
    check(
        "missing format_version exits 2 with a clear message",
        rm.returncode == 2 and 'format_version' in rm.stderr,
        f"rc={rm.returncode}, stderr={rm.stderr!r}",
    )

    bad_json = tmp_path / 'bad.json'
    bad_json.write_text('not json', encoding='utf-8')
    rj = run_cli('resolve', 'some_id', '--lookup-table', str(bad_json))
    check(
        "non-JSON lookup-table exits 2 and stderr names the file",
        rj.returncode == 2 and str(bad_json) in rj.stderr,
        f"rc={rj.returncode}, stderr={rj.stderr!r}",
    )


def test_cli_source_mutual_exclusion(tmp_path: Path) -> None:
    """Every pair of source flags is rejected by argparse."""
    out = tmp_path / 'd.json'
    rd = run_cli('dump', '--from', str(MULTI_DIR), '--out', str(out))
    if rd.returncode != 0:
        check("source mutual exclusion", False, f"dump rc={rd.returncode}")
        return
    pairs = [
        ('--from', str(MULTI_DIR), '--remote-base-url', 'https://example.com/help/'),
        ('--from', str(MULTI_DIR), '--lookup-table', str(out)),
        ('--remote-base-url', 'https://example.com/help/', '--lookup-table', str(out)),
    ]
    all_rejected = True
    detail_bits: list[str] = []
    for combo in pairs:
        r = run_cli('resolve', 'some_id', *combo)
        rejected = r.returncode != 0 and 'not allowed' in r.stderr.lower()
        if not rejected:
            all_rejected = False
            detail_bits.append(f"{' '.join(combo)} -> rc={r.returncode} stderr={r.stderr!r}")
    check(
        "every pair of source flags is rejected (argparse mutual exclusion)",
        all_rejected,
        '; '.join(detail_bits),
    )


def test_cli_dump_lookup_table_rejected(tmp_path: Path) -> None:
    """`dump --lookup-table` is rejected even though the flag is registered on the parser."""
    out = tmp_path / 'd.json'
    rd = run_cli('dump', '--from', str(MULTI_DIR), '--out', str(out))
    if rd.returncode != 0:
        check("dump --lookup-table rejected", False, f"dump rc={rd.returncode}")
        return
    r = run_cli('dump', '--lookup-table', str(out))
    check(
        "dump --lookup-table is rejected at exit 1 with a clear message",
        r.returncode == 1 and 'not a valid source for dump' in r.stderr,
        f"rc={r.returncode}, stderr={r.stderr!r}",
    )


def test_cli_dump_real_artifact_smoke() -> None:
    """Real ePublisher Designer 2026.1 fixture loads and resolves correctly."""
    if not EPUBLISHER_FIXTURE.exists():
        check("real-artifact smoke (ePublisher 2026.1)", False,
              f"fixture missing: {EPUBLISHER_FIXTURE}")
        return
    artifact = json.loads(EPUBLISHER_FIXTURE.read_text(encoding='utf-8'))
    src = artifact.get('source', {})
    landmarks = artifact.get('landmarks', {})
    shape_ok = (
        artifact.get('format_version') == 1
        and src.get('type') == 'local-directory'
        and src.get('chunks_found') == 7
        and len(landmarks) > 0
    )
    if not shape_ok:
        check("real-artifact: shape is intact", False,
              f"format_version={artifact.get('format_version')}, src={src}, "
              f"landmark_count={len(landmarks)}")
        return
    check("real-artifact: format_version=1, type=local-directory, chunks_found=7",
          True, f"landmark_count={len(landmarks)}")
    first_id = sorted(landmarks.keys())[0]
    expected_entry = landmarks[first_id]
    expected = (
        f"{expected_entry['file']}#{expected_entry['anchor']}"
        if expected_entry.get('anchor')
        else expected_entry['file']
    )
    r = run_cli('resolve', first_id, '--lookup-table', str(EPUBLISHER_FIXTURE))
    check(
        f"real-artifact: resolve {first_id!r} via --lookup-table",
        r.returncode == 0 and r.stdout.strip() == expected,
        f"rc={r.returncode}, stdout={r.stdout!r}, expected={expected!r}",
    )


def test_cli_dump_remote_source_block(tmp_path: Path) -> None:
    """Remote-mode dump records source.type=remote-base-url with the base URL."""
    base = 'https://dump-source.example/help/'
    landing_html = LANDING_WITH_HASH.read_text(encoding='utf-8')
    chunk = SINGLE_CHUNK.read_bytes()

    wrapper = tmp_path / 'wrap.py'
    wrapper.write_text(_make_wrapper_script(
        base=base,
        landing_html=landing_html.encode('utf-8'),
        chunk_payload=chunk,
    ), encoding='utf-8')
    cache_dir = tmp_path / 'cache'
    out = tmp_path / 'dump.json'
    proc = subprocess.run(
        [sys.executable, str(wrapper),
         'dump', '--remote-base-url', base,
         '--cache-dir', str(cache_dir),
         '--cache-ttl', '3600',
         '--out', str(out)],
        capture_output=True, text=True,
        env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
    )
    if proc.returncode != 0:
        check("remote-mode dump source block", False,
              f"rc={proc.returncode}, stderr={proc.stderr!r}")
        return
    artifact = json.loads(out.read_text(encoding='utf-8'))
    src = artifact.get('source', {})
    check(
        "remote-mode dump: source.type=remote-base-url with base_url and chunks_found>0",
        src.get('type') == 'remote-base-url'
        and src.get('base_url') == base
        and isinstance(src.get('chunks_found'), int)
        and src['chunks_found'] > 0,
        f"src={src}",
    )


# ---------------------------------------------------------------------------
# Reverse-lookup tests (internal + CLI)
# ---------------------------------------------------------------------------


def test_internal_build_index_reverse_map() -> None:
    files, anchors, _, path_to_bindings = resolver.build_index([SINGLE_CHUNK])

    page_fi = files.index("Group/page.html")
    bindings = path_to_bindings.get(page_fi, [])
    anchor_pairs = [(anchors[ai], lid) for ai, lid in bindings]
    expected = [
        ("", "page-only-id"),
        ("wwp100", "abc1234567890def"),
        ("wwp200", "12345678"),
    ]
    check(
        "build_index: path_to_bindings entry for Group/page.html sorted with empty anchor first",
        anchor_pairs == expected,
        f"got {anchor_pairs}",
    )

    # Out-of-range rows should not appear in the reverse map either.
    all_ids = {lid for entries in path_to_bindings.values() for _, lid in entries}
    check(
        "build_index: reverse map drops out-of-range and empty-id rows",
        "out-of-range-file" not in all_ids
        and "out-of-range-anchor" not in all_ids
        and "" not in all_ids,
        f"all_ids={sorted(all_ids)}",
    )


def test_internal_reverse_map_last_write_wins() -> None:
    chunks = sorted([
        FIXTURE_DIR / 'multi-chunk-a_lx.js',
        FIXTURE_DIR / 'multi-chunk-b_lx.js',
    ])
    files, _, _, path_to_bindings = resolver.build_index(chunks)
    group_b_fi = files.index("groupB/page.html")
    ids_under_group_b = [lid for _, lid in path_to_bindings.get(group_b_fi, [])]
    group_a_idx = files.index("groupA/page.html") if "groupA/page.html" in files else -1
    ids_under_group_a = (
        [lid for _, lid in path_to_bindings.get(group_a_idx, [])]
        if group_a_idx >= 0 else []
    )
    check(
        "reverse map: last-write-wins — common_id lives only under groupB/page.html",
        "common_id" in ids_under_group_b and "common_id" not in ids_under_group_a,
        f"under groupA={ids_under_group_a}, under groupB={ids_under_group_b}",
    )


def test_internal_invert_lookup_for_reverse(tmp_path: Path) -> None:
    """`_invert_lookup_for_reverse` walks a dump artifact and returns
    `path -> [(anchor, id), ...]` lists sorted by (anchor, id)."""
    out = tmp_path / 'dump.json'
    rd = run_cli('dump', '--from', str(MULTI_DIR), '--out', str(out))
    if rd.returncode != 0:
        check("_invert_lookup_for_reverse internal shape", False,
              f"dump rc={rd.returncode}, stderr={rd.stderr!r}")
        return
    lookup = json.loads(out.read_text(encoding='utf-8'))
    inverted = resolver._invert_lookup_for_reverse(lookup)
    forward_files = {entry['file'] for entry in lookup['landmarks'].values()}
    check(
        "inverted lookup: every forward file appears as a key",
        set(inverted.keys()) == forward_files,
        f"missing={forward_files - set(inverted.keys())}, "
        f"extra={set(inverted.keys()) - forward_files}",
    )
    sorted_ok = all(v == sorted(v) for v in inverted.values())
    check(
        "inverted lookup: each value list is sorted by (anchor, id)",
        sorted_ok,
        f"unsorted: {[k for k, v in inverted.items() if v != sorted(v)]}",
    )


def test_cli_reverse_multi_binding_default_order() -> None:
    """Bare reverse output lists every ID on its own line in (anchor, id) order,
    with the empty-anchor binding first."""
    r = run_cli('reverse', 'Group/page.html', '--from', str(SINGLE_CHUNK))
    expected_lines = ['page-only-id', 'abc1234567890def', '12345678']
    check(
        "CLI reverse: bare output lists every binding in (anchor, id) order",
        r.returncode == 0 and r.stdout.splitlines() == expected_lines,
        f"rc={r.returncode}, stdout={r.stdout!r}, stderr={r.stderr!r}",
    )


def test_cli_reverse_anchor_filter() -> None:
    """`--anchor <id>` returns only the binding for that anchor."""
    r = run_cli('reverse', 'Group/page.html', '--anchor', 'wwp100', '--from', str(SINGLE_CHUNK))
    check(
        "CLI reverse --anchor wwp100: returns abc1234567890def",
        r.returncode == 0 and r.stdout.strip() == 'abc1234567890def',
        f"rc={r.returncode}, stdout={r.stdout!r}, stderr={r.stderr!r}",
    )


def test_cli_reverse_first_flag() -> None:
    """`--first` returns only the page-level (empty-anchor) binding."""
    r = run_cli('reverse', 'Group/page.html', '--first', '--from', str(SINGLE_CHUNK))
    check(
        "CLI reverse --first: returns page-level ID only",
        r.returncode == 0 and r.stdout.strip() == 'page-only-id',
        f"rc={r.returncode}, stdout={r.stdout!r}, stderr={r.stderr!r}",
    )


def test_cli_reverse_first_flag_no_page_level() -> None:
    """`--first` against a path with no empty-anchor row exits 1 with a clear message."""
    # In single-chunk, "Group/other.html" has only one binding: anchor "wwp_anchor".
    r = run_cli('reverse', 'Group/other.html', '--first', '--from', str(SINGLE_CHUNK))
    check(
        "CLI reverse --first: exit 1 when no page-level binding exists",
        r.returncode == 1
        and 'no page-level binding' in r.stderr
        and 'Group/other.html' in r.stderr,
        f"rc={r.returncode}, stderr={r.stderr!r}",
    )


def test_cli_reverse_json_default() -> None:
    """`--json` emits `{path, matches: [{id, anchor}, ...]}` with all bindings."""
    r = run_cli('reverse', 'Group/page.html', '--json', '--from', str(SINGLE_CHUNK))
    if r.returncode != 0:
        check("CLI reverse --json (happy)", False, f"rc={r.returncode}, stderr={r.stderr!r}")
        return
    payload = json.loads(r.stdout)
    expected = {
        "path": "Group/page.html",
        "matches": [
            {"id": "page-only-id", "anchor": ""},
            {"id": "abc1234567890def", "anchor": "wwp100"},
            {"id": "12345678", "anchor": "wwp200"},
        ],
    }
    check(
        "CLI reverse --json: emits {path, matches:[{id,anchor},...]}",
        payload == expected,
        f"payload={payload!r}",
    )


def test_cli_reverse_json_no_match() -> None:
    """`--json` on a missing path emits `{path, matches: [], error}` and exits 1."""
    r = run_cli('reverse', 'doesnotexist.html', '--json', '--from', str(SINGLE_CHUNK))
    payload = json.loads(r.stdout) if r.stdout.strip() else None
    check(
        "CLI reverse --json (no match): {path, matches:[], error} on stdout, exit 1",
        r.returncode == 1
        and isinstance(payload, dict)
        and payload.get('path') == 'doesnotexist.html'
        and payload.get('matches') == []
        and 'not in index' in payload.get('error', ''),
        f"rc={r.returncode}, stdout={r.stdout!r}",
    )


def test_cli_reverse_unicode_path_raw_and_encoded() -> None:
    """Reverse-lookup against a Unicode path returns identical IDs whether the
    input is raw or percent-encoded, and includes Unicode IDs in its output."""
    raw_path = 'Advanced Customizations/_xslt-extensions.04.1.html'
    encoded_path = 'Advanced%20Customizations/_xslt-extensions.04.1.html'
    raw_r = run_cli('reverse', raw_path, '--from', str(UNICODE_CHUNK))
    enc_r = run_cli('reverse', encoded_path, '--from', str(UNICODE_CHUNK))
    raw_ids = set(raw_r.stdout.splitlines())
    enc_ids = set(enc_r.stdout.splitlines())
    check(
        "CLI reverse: percent-encoded and raw Unicode paths return identical ID sets including '概要'",
        raw_r.returncode == 0
        and enc_r.returncode == 0
        and raw_ids == enc_ids
        and '概要' in raw_ids,
        f"raw rc={raw_r.returncode}, raw_ids={raw_ids}; "
        f"enc rc={enc_r.returncode}, enc_ids={enc_ids}",
    )


def test_cli_reverse_first_and_anchor_mutex() -> None:
    """`--first` and `--anchor` are mutually exclusive at argparse."""
    r = run_cli(
        'reverse', 'Group/page.html',
        '--first', '--anchor', 'wwp100',
        '--from', str(SINGLE_CHUNK),
    )
    check(
        "CLI reverse: --first and --anchor are mutually exclusive (exit 2)",
        r.returncode == 2 and 'not allowed' in r.stderr.lower(),
        f"rc={r.returncode}, stderr={r.stderr!r}",
    )


def test_cli_reverse_anchor_empty_rejected() -> None:
    """`--anchor ""` is rejected with a "use --first" message and exit 2."""
    r = run_cli('reverse', 'Group/page.html', '--anchor', '', '--from', str(SINGLE_CHUNK))
    check(
        "CLI reverse: --anchor '' rejected with use-first guidance (exit 2)",
        r.returncode == 2 and 'use --first' in r.stderr,
        f"rc={r.returncode}, stderr={r.stderr!r}",
    )


def test_cli_reverse_malformed_percent_exits_1() -> None:
    """A malformed percent-encoded path exits 1 with a clear stderr message."""
    bad = 'Group/%E6%A6page.html'  # truncated percent sequence
    r = run_cli('reverse', bad, '--from', str(SINGLE_CHUNK))
    check(
        "CLI reverse: malformed percent sequence exits 1 and stderr names the path",
        r.returncode == 1 and bad in r.stderr and 'Malformed' in r.stderr,
        f"rc={r.returncode}, stderr={r.stderr!r}",
    )


def test_cli_reverse_path_not_in_index() -> None:
    """A path not in the chunk index exits 1 with a clear stderr message."""
    r = run_cli('reverse', 'doesnotexist.html', '--from', str(SINGLE_CHUNK))
    check(
        "CLI reverse: path not in index exits 1 with stderr naming the path",
        r.returncode == 1 and 'not in index' in r.stderr and 'doesnotexist.html' in r.stderr,
        f"rc={r.returncode}, stderr={r.stderr!r}",
    )


def test_cli_reverse_forward_round_trip() -> None:
    """Resolve each ID forward to a path, then reverse-look up that path —
    the result must include the original ID."""
    for fixture in (SINGLE_CHUNK, FIXTURE_DIR / 'multi-chunk-a_lx.js', UNICODE_CHUNK):
        files, anchors, id_to_pair, _ = resolver.build_index([fixture])
        broken: list[str] = []
        for landmark_id, (fi, _) in id_to_pair.items():
            file_path = files[fi]
            r = run_cli('reverse', file_path, '--from', str(fixture))
            if r.returncode != 0:
                broken.append(f"{landmark_id!r}@{file_path!r}: reverse rc={r.returncode}")
                continue
            if landmark_id not in r.stdout.splitlines():
                broken.append(
                    f"{landmark_id!r}@{file_path!r}: not in {r.stdout.splitlines()!r}"
                )
        check(
            f"CLI reverse: forward-then-reverse round-trip includes original ID ({fixture.name})",
            not broken,
            '; '.join(broken[:5])
            + (f" ...({len(broken)} mismatches)" if len(broken) > 5 else ''),
        )


def test_cli_reverse_lookup_parity(tmp_path: Path) -> None:
    """`reverse` against a dumped `--lookup-table` produces the same stdout as
    against the original `--from` source for the same query."""
    # Dump the multi-chunk fixtures and the unicode fixture into separate artifacts.
    multi_dump = tmp_path / 'multi.json'
    unicode_dump = tmp_path / 'unicode.json'
    rd_multi = run_cli('dump', '--from', str(MULTI_DIR), '--out', str(multi_dump))
    rd_uni = run_cli('dump', '--from', str(UNICODE_CHUNK), '--out', str(unicode_dump))
    if rd_multi.returncode != 0 or rd_uni.returncode != 0:
        check("CLI reverse lookup-table parity", False,
              f"multi dump rc={rd_multi.returncode}, unicode dump rc={rd_uni.returncode}")
        return

    cases = [
        # (lookup_path, query_args, label)
        (multi_dump, ['reverse', 'Group/page.html'], 'multi:Group/page.html'),
        (multi_dump, ['reverse', 'Group/page.html', '--first'], 'multi:Group/page.html --first'),
        (multi_dump, ['reverse', 'Group/page.html', '--anchor', 'wwp100'], 'multi:--anchor wwp100'),
        (multi_dump, ['reverse', 'Group/page.html', '--json'], 'multi:--json'),
        (multi_dump, ['reverse', 'groupB/page.html'], 'multi:groupB/page.html'),
        (multi_dump, ['reverse', 'doesnotexist.html'], 'multi:miss'),
        (unicode_dump, ['reverse', 'Advanced Customizations/_xslt-extensions.04.1.html'],
            'unicode:raw'),
        (unicode_dump, ['reverse', 'Advanced%20Customizations/_xslt-extensions.04.1.html'],
            'unicode:encoded'),
    ]
    mismatches: list[str] = []
    for lookup, query, label in cases:
        a = run_cli(*query, '--from', str(MULTI_DIR) if lookup is multi_dump else str(UNICODE_CHUNK))
        b = run_cli(*query, '--lookup-table', str(lookup))
        if a.stdout != b.stdout or a.returncode != b.returncode:
            mismatches.append(
                f"{label}: chunks(rc={a.returncode}, stdout={a.stdout!r}) "
                f"vs lookup(rc={b.returncode}, stdout={b.stdout!r})"
            )
    check(
        f"CLI reverse: chunk-source and --lookup-table produce identical output ({len(cases)} cases)",
        not mismatches,
        '; '.join(mismatches[:3]),
    )


# ---------------------------------------------------------------------------
# Test harness: stderr capture helper for the no-hash warning test
# ---------------------------------------------------------------------------


class _StderrCapture:
    """Tee sys.stderr so a test can read what was written to it."""

    def __init__(self):
        self._buf: list[str] = []
        self._original = sys.stderr

    def __enter__(self):
        self._buf.clear()
        self._original = sys.stderr
        sys.stderr = self
        return self

    def __exit__(self, *exc):
        sys.stderr = self._original
        return False

    def write(self, data: str) -> int:
        text = str(data)
        self._buf.append(text)
        return len(text)

    def flush(self):
        pass

    def read(self):
        return ''.join(self._buf)


def main() -> int:
    if not SCRIPT_PATH.exists():
        print(f"{RED}FAIL:{NC} resolver script not found at {SCRIPT_PATH}", file=sys.stderr)
        return 2
    if not SINGLE_CHUNK.exists():
        print(f"{RED}FAIL:{NC} single-chunk fixture missing at {SINGLE_CHUNK}", file=sys.stderr)
        return 2

    print(f"{YELLOW}Running landmark-resolver verification...{NC}\n")

    # Internal: chunk parsing and index building
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

    # Internal: build_index_from_texts and Unicode unquote
    test_internal_build_index_from_texts()
    test_unicode_id_resolves_with_unquote_in_index()

    # Internal: HTTP primitives
    test_http_get_happy_path()
    test_http_get_transient_retry()
    test_http_get_exhausted_retries()
    test_http_get_4xx_not_retried()
    test_http_get_5xx_retried()
    test_proxy_handler_constructed_from_getproxies()

    # Internal: cache state machine
    test_default_cache_root_windows()
    test_default_cache_root_linux_xdg()
    test_default_cache_root_macos()
    test_base_cache_dir_with_path()
    test_base_cache_dir_root_url()
    test_base_cache_dir_trailing_slash_distinct()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        test_read_cache_manifest_missing(tmp_path)
        test_read_cache_manifest_malformed(tmp_path)
        test_write_cache_atomic_replaces_old_files(tmp_path)
        test_cache_partial_write_isolated(tmp_path)
    test_cache_decision_branches()

    # Internal: chunk discovery
    test_extract_chunk_srcs_basic()
    test_extract_chunk_srcs_quote_variants()
    test_extract_generation_hash()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        test_remote_chunk_texts_first_call_writes_cache(tmp_path)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        test_remote_chunk_texts_second_call_uses_cache(tmp_path)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        test_remote_chunk_texts_hash_unchanged_reuses_cache(tmp_path)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        test_remote_chunk_texts_hash_changed_refetches(tmp_path)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        test_remote_chunk_texts_no_cache_forces_refetch(tmp_path)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with _StderrCapture() as cap:
            test_remote_chunk_texts_no_hash_warns_and_succeeds(tmp_path, cap)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        test_remote_chunk_texts_empty_discovery_raises(tmp_path)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        test_remote_chunk_texts_manifest_preferred(tmp_path)

    # CLI: resolve, dump, rewrite (local mode)
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

    # CLI: URL fragment decode in rewrite
    test_cli_rewrite_percent_encoded_unicode_local()
    test_cli_rewrite_malformed_percent_exits_1()
    test_cli_rewrite_ascii_id_no_double_decode()
    test_cli_rewrite_literal_plus_preserved()

    # CLI: remote-mode flag plumbing
    test_cli_rewrite_mutual_exclusion()
    test_cli_rewrite_from_wins_over_http_url()
    test_cli_no_source_and_non_http_url_exits_1()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        test_cli_resolve_remote_mode_via_proxy_script(tmp_path)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        test_cli_dump_remote_mode(tmp_path)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        test_cli_remote_fetch_failure_exits_2(tmp_path)

    # CLI: dump artifact + --lookup-table consumer path
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        test_cli_dump_deterministic(tmp_path)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        test_cli_dump_structured_shape(tmp_path)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        test_cli_dump_sorted_keys(tmp_path)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        test_cli_dump_unicode_preservation(tmp_path)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        test_cli_round_trip_equivalence_chunks(tmp_path)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        test_cli_round_trip_equivalence_unicode(tmp_path)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        test_cli_format_version_validation(tmp_path)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        test_cli_source_mutual_exclusion(tmp_path)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        test_cli_dump_lookup_table_rejected(tmp_path)
    test_cli_dump_real_artifact_smoke()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        test_cli_dump_remote_source_block(tmp_path)

    # Reverse subcommand
    test_internal_build_index_reverse_map()
    test_internal_reverse_map_last_write_wins()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        test_internal_invert_lookup_for_reverse(tmp_path)
    test_cli_reverse_multi_binding_default_order()
    test_cli_reverse_anchor_filter()
    test_cli_reverse_first_flag()
    test_cli_reverse_first_flag_no_page_level()
    test_cli_reverse_json_default()
    test_cli_reverse_json_no_match()
    test_cli_reverse_unicode_path_raw_and_encoded()
    test_cli_reverse_first_and_anchor_mutex()
    test_cli_reverse_anchor_empty_rejected()
    test_cli_reverse_malformed_percent_exits_1()
    test_cli_reverse_path_not_in_index()
    test_cli_reverse_forward_round_trip()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        test_cli_reverse_lookup_parity(tmp_path)

    passed = sum(1 for _, ok, _ in _results if ok)
    failed = sum(1 for _, ok, _ in _results if not ok)
    print(f"\n{YELLOW}Summary:{NC} {passed} passed, {failed} failed (of {len(_results)})")

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
