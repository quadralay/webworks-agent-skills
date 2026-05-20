#!/usr/bin/env python3
"""
resolve-landmarks.py

Resolves stable Reverb 2.0 landmark URLs (the hash-based "#/<id>" form used in
published help) into direct static file paths by parsing the _lx.js chunk files
emitted alongside every Reverb output. Lets AI consumers fetch documentation
without executing the Reverb JavaScript runtime.

v2 adds a remote mode that fetches _lx.js chunks over HTTP from a published
help mirror and caches them locally — agents can paste any stable URL and
resolve it with no local mirror download. The cache is keyed by
GLOBAL_GENERATION_HASH (emitted by Reverb into the landing page) with a TTL
fallback for mirrors that ship without the constant.

Usage:
    python resolve-landmarks.py resolve <id> [--from <path> | --remote-base-url <url>] [--json]
    python resolve-landmarks.py rewrite <url> [--from <path> | --remote-base-url <url>] [--base-url <url>]
    python resolve-landmarks.py dump [--from <path> | --remote-base-url <url>] [--table]

Sources (mutually exclusive):
    --from <path>           Local *_lx.js chunk file or directory containing chunks.
    --remote-base-url <url> Help mirror base URL (e.g., https://host/docs/help/).
                            `rewrite` auto-infers this from an HTTP/HTTPS URL when
                            neither --from nor --remote-base-url is set.

Remote-mode flags:
    --no-cache              Skip cache freshness/hash checks; re-fetch every chunk.
    --cache-ttl <seconds>   Landing-page re-poll cadence (default 86400 = 24h).
    --cache-dir <path>      Cache root override (default: platform user cache).
    --http-timeout <secs>   Per-request read timeout (default 10).

Other flags:
    --base-url <url>        For "rewrite": replace the inferred URL prefix with this base.
    --json                  For "resolve": emit a JSON object instead of the bare path.
    --table                 For "dump": emit a human-readable table instead of JSON.

Landmark ID formats (treated as opaque strings):
    - 16-character hex hash (default; all Reverb 2.0 releases)
    - 8-character hex hash (new in 2026.1, opt-in)
    - Pass-through source ID (new in 2026.1, opt-in)

The resolver does not regex, length-check, or hex-validate IDs; it does a
straight string-equality lookup against the third element of each e[i] tuple in
the _lx.js data. URL-fragment IDs are urllib.parse.unquote'd before lookup, so
percent-encoded Unicode IDs (e.g., %E6%A6%82%E8%A6%81 -> 概要) round-trip the
same way the browser runtime resolves them.

Manifest file shape (forward-compatible; Reverb does not currently emit one):
    {"chunks": ["Foo_lx.js", "Bar_lx.js"]}
The names resolve relative to the remote base URL.

Exit codes:
    0 - Success.
    1 - Resolution failure (ID not found, URL has no ID after "#/",
        malformed percent-encoding in input URL, or CLI usage error).
    2 - Parse failure, IO failure, or HTTP failure (file missing,
        malformed chunk, empty source, remote fetch error).

Examples:
    # Local: resolve a single ID against one chunk
    python resolve-landmarks.py resolve e5d3d31c42d8d1d4 --from output/FAQs_lx.js

    # Local: resolve against every chunk in a directory
    python resolve-landmarks.py resolve abc12345 --from output/

    # Local: rewrite a published stable URL into a direct URL
    python resolve-landmarks.py rewrite \\
        https://example.com/help/#/e5d3d31c42d8d1d4 --from output/

    # Remote: rewrite a stable URL with no local mirror (auto-inferred base)
    python resolve-landmarks.py rewrite https://example.com/help/#/e5d3d31c42d8d1d4

    # Remote: resolve against a published mirror
    python resolve-landmarks.py resolve e5d3d31c42d8d1d4 \\
        --remote-base-url https://example.com/help/

    # Local: dump the full index as JSON
    python resolve-landmarks.py dump --from output/

    # Local: dump the full index as a human-readable table
    python resolve-landmarks.py dump --from output/ --table
"""

import argparse
import http.client
import json
import os
import platform
import re
import shutil
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable, Optional

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

# Matches `<script src="…_lx.js">` references in the landing-page HTML. Tolerant
# of attribute order, single or double quotes, and extra attributes.
_SCRIPT_LX_RE = re.compile(
    r'<script\b[^>]*\bsrc\s*=\s*["\']([^"\']*_lx\.js)["\'][^>]*>',
    re.IGNORECASE,
)

# Matches `var|const|let GLOBAL_GENERATION_HASH = "<hex>";` declarations.
_GENERATION_HASH_RE = re.compile(
    r'(?:var|const|let)\s+GLOBAL_GENERATION_HASH\s*=\s*["\']([^"\']+)["\']'
)

# Cache schema. Bumped only on incompatible manifest changes.
_CACHE_MANIFEST = '_manifest.json'

# Module-level seams so tests can monkey-patch without unittest.mock.
_sleep = time.sleep
_now = time.time


def debug_log(message: str) -> None:
    """Print debug message to stderr."""
    if DEBUG:
        print(f"{YELLOW}[DEBUG]{NC} {message}", file=sys.stderr)


def error_log(message: str) -> None:
    """Print error message to stderr."""
    print(f"{RED}[ERROR]{NC} {message}", file=sys.stderr)


def warn_log(message: str) -> None:
    """Print warning message to stderr (unconditional, unlike debug_log)."""
    print(f"{YELLOW}[WARN]{NC} {message}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Chunk parsing and index building (v1 — unchanged behavior)
# ---------------------------------------------------------------------------


def parse_chunk_text(text: str, source_label: str) -> dict[str, list]:
    """
    Parse a _lx.js chunk's text into the landmarks dict.

    `source_label` is the file path (local mode) or URL (remote mode) used in
    error messages. Raises ValueError on shape mismatch.
    """
    match = _LANDMARKS_RE.search(text)
    if not match:
        raise ValueError(
            f"{source_label}: not a recognizable _lx.js chunk "
            "(missing 'var landmarks = {...};Landmarks.Advance(...)')"
        )

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError as e:
        raise ValueError(f"{source_label}: landmarks object is not JSON-parseable: {e}") from e

    for key in ('f', 'a', 'e'):
        if key not in data:
            raise ValueError(f"{source_label}: landmarks object is missing required key '{key}'")
        if not isinstance(data[key], list):
            raise ValueError(f"{source_label}: landmarks key '{key}' is not a list")

    return data


def parse_chunk(path: Path) -> dict[str, list]:
    """
    Read a _lx.js chunk and return its landmarks object as a dict.

    The chunk file shape is:
        var landmarks = { "f": [...], "a": [...], "e": [[fi,ai,id], ...] };
        Landmarks.Advance(landmarks);
    """
    debug_log(f"Parsing chunk: {path}")
    return parse_chunk_text(path.read_text(encoding='utf-8'), str(path))


def _merge_chunks(
    chunks: list[tuple[str, dict[str, list]]],
) -> tuple[list[str], list[str], dict[str, tuple[int, int]]]:
    """Shared merge logic: take pre-parsed (label, data) chunks and return the index."""
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

    for _label, chunk in chunks:
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
    parsed = [(str(p), parse_chunk(p)) for p in chunk_paths]
    return _merge_chunks(parsed)


def build_index_from_texts(
    chunks: list[tuple[str, bytes]],
) -> tuple[list[str], list[str], dict[str, tuple[int, int]]]:
    """
    Same as build_index, but takes pre-loaded (label, bytes) pairs instead of
    file paths. Used by the remote-mode front end.
    """
    parsed = [
        (label, parse_chunk_text(content.decode('utf-8'), label))
        for label, content in chunks
    ]
    return _merge_chunks(parsed)


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


# ---------------------------------------------------------------------------
# Remote mode: HTTP primitives
# ---------------------------------------------------------------------------


class RemoteFetchError(Exception):
    """Raised when an HTTP fetch fails permanently."""

    def __init__(self, url: str, reason: str):
        super().__init__(f"{url}: {reason}")
        self.url = url
        self.reason = reason


def _build_opener() -> urllib.request.OpenerDirector:
    """Build a urllib opener configured from HTTP_PROXY / HTTPS_PROXY / NO_PROXY."""
    proxies = urllib.request.getproxies()
    handlers: list = []
    if proxies:
        handlers.append(urllib.request.ProxyHandler(proxies))
    return urllib.request.build_opener(*handlers)


def _is_retryable(exc: BaseException) -> bool:
    """True for transient errors that warrant a retry (timeouts, 5xx, resets)."""
    if isinstance(exc, urllib.error.HTTPError):
        return 500 <= exc.code < 600
    if isinstance(exc, urllib.error.URLError):
        reason = exc.reason
        if isinstance(reason, socket.timeout):
            return True
        # Common transient network errors raised inside URLError.reason
        if isinstance(reason, (ConnectionResetError, ConnectionAbortedError, TimeoutError)):
            return True
        return False
    if isinstance(exc, (socket.timeout, TimeoutError, http.client.RemoteDisconnected)):
        return True
    if isinstance(exc, ConnectionResetError):
        return True
    return False


def http_get(
    url: str,
    timeout: float = 10.0,
    max_attempts: int = 3,
    base_delay: float = 1.0,
) -> bytes:
    """
    GET `url` with retry on transient failures.

    Returns response body as bytes on 2xx. Raises RemoteFetchError on 4xx, on
    exhausted retries, or on any non-transient transport error.
    """
    opener = _build_opener()
    last_exc: Optional[BaseException] = None
    for attempt in range(1, max_attempts + 1):
        try:
            with opener.open(url, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as e:
            if not _is_retryable(e):
                raise RemoteFetchError(url, f"HTTP {e.code}: {e.reason}") from e
            last_exc = e
            debug_log(f"http_get attempt {attempt} for {url} got HTTP {e.code}; retrying")
        except (urllib.error.URLError, http.client.RemoteDisconnected, socket.timeout, TimeoutError, ConnectionResetError) as e:
            if not _is_retryable(e):
                raise RemoteFetchError(url, f"{type(e).__name__}: {e}") from e
            last_exc = e
            debug_log(f"http_get attempt {attempt} for {url} failed: {e}; retrying")
        if attempt < max_attempts:
            _sleep(base_delay * (2 ** (attempt - 1)))

    raise RemoteFetchError(url, f"exhausted {max_attempts} attempts: {last_exc}")


def http_head(url: str, timeout: float = 10.0) -> bool:
    """
    Single-attempt HEAD probe. True on 2xx, False on 4xx, raises on transport
    error or 5xx. Used only by the manifest probe.
    """
    opener = _build_opener()
    request = urllib.request.Request(url, method='HEAD')
    try:
        with opener.open(request, timeout=timeout) as response:
            status = response.status if hasattr(response, 'status') else response.getcode()
            return 200 <= status < 300
    except urllib.error.HTTPError as e:
        if 400 <= e.code < 500:
            return False
        raise RemoteFetchError(url, f"HTTP {e.code}: {e.reason}") from e
    except (urllib.error.URLError, http.client.RemoteDisconnected, socket.timeout, TimeoutError, ConnectionResetError) as e:
        raise RemoteFetchError(url, f"{type(e).__name__}: {e}") from e


# Fetcher contract used by the discovery and cache layers. Returns (status_code,
# body_bytes). 4xx returns (status, body); 5xx and transient errors retry inside
# the default fetcher; permanent transport errors raise RemoteFetchError.
Fetcher = Callable[..., tuple[int, bytes]]


def default_fetcher(
    url: str,
    *,
    method: str = 'GET',
    timeout: float = 10.0,
) -> tuple[int, bytes]:
    """
    Default Fetcher implementation backed by http_get / http_head.

    Tests pass their own Fetcher stub instead of this. The stub records the
    requested URL/method/timeout and returns canned (status, body) pairs.
    """
    if method == 'HEAD':
        return (200, b'') if http_head(url, timeout=timeout) else (404, b'')
    if method == 'GET':
        return (200, http_get(url, timeout=timeout))
    raise ValueError(f"default_fetcher: unsupported method {method!r}")


# ---------------------------------------------------------------------------
# Remote mode: cache layout and state machine
# ---------------------------------------------------------------------------


def default_cache_root() -> Path:
    """
    Return the platform-default cache root for resolved chunk files.

    - Windows: %LOCALAPPDATA%\\webworks\\reverb-landmarks\\
    - macOS:   ~/Library/Caches/webworks/reverb-landmarks/
    - Linux:   $XDG_CACHE_HOME/webworks/reverb-landmarks/
               (falls back to ~/.cache/webworks/reverb-landmarks/)
    """
    system = platform.system()
    if system == 'Windows':
        local_app_data = os.environ.get('LOCALAPPDATA')
        if local_app_data:
            return Path(local_app_data) / 'webworks' / 'reverb-landmarks'
        return Path.home() / 'AppData' / 'Local' / 'webworks' / 'reverb-landmarks'
    if system == 'Darwin':
        return Path.home() / 'Library' / 'Caches' / 'webworks' / 'reverb-landmarks'
    xdg = os.environ.get('XDG_CACHE_HOME')
    if xdg:
        return Path(xdg) / 'webworks' / 'reverb-landmarks'
    return Path.home() / '.cache' / 'webworks' / 'reverb-landmarks'


def base_cache_dir(root: Path, base_url: str) -> Path:
    """
    Per-base subdirectory under the cache root.

    Layout: <root>/<host>/<percent-encoded-path>/. Trailing-slash sensitivity
    is preserved (`/help/` != `/help`), so two base URLs that differ only in
    trailing slash get distinct cache directories.
    """
    parsed = urllib.parse.urlparse(base_url)
    host = parsed.hostname or ''
    path = parsed.path.lstrip('/')
    if path:
        encoded = urllib.parse.quote(path, safe='')
        return Path(root) / host / encoded
    return Path(root) / host


def read_cache_manifest(base_dir: Path) -> Optional[dict]:
    """
    Return the parsed manifest dict, or None if missing or unparseable.

    Manifest shape:
        {"generation_hash": str | null,
         "last_poll_ts": float,
         "chunks": [{"name": str, "url": str}, ...]}
    """
    manifest_path = base_dir / _CACHE_MANIFEST
    if not manifest_path.is_file():
        return None
    try:
        data = json.loads(manifest_path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def write_cache_atomic(
    base_dir: Path,
    manifest: dict,
    chunk_texts: dict[str, bytes],
) -> None:
    """
    Write `manifest` and `chunk_texts` to `base_dir` atomically (best-effort).

    Strategy: stage every file in a sibling `<base_dir>.tmp/` directory, then
    swap the live directory with one rename. If a prior cache exists, it is
    fully replaced — old chunks not in the new set are gone after the swap.
    """
    base_dir = Path(base_dir)
    parent = base_dir.parent
    parent.mkdir(parents=True, exist_ok=True)

    staging = parent / (base_dir.name + '.tmp')
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    for name, content in chunk_texts.items():
        (staging / name).write_bytes(content)

    (staging / _CACHE_MANIFEST).write_text(
        json.dumps(manifest, sort_keys=True, indent=2),
        encoding='utf-8',
    )

    if base_dir.exists():
        shutil.rmtree(base_dir)
    os.rename(staging, base_dir)


def cache_decision(
    manifest: Optional[dict],
    ttl_seconds: float,
    now: float,
    no_cache: bool,
) -> str:
    """
    Return one of 'use', 'poll', 'refetch':
        - no_cache=True              -> 'refetch'
        - missing/invalid manifest   -> 'refetch'
        - within TTL                 -> 'use'  (chunks cached and trusted)
        - past TTL                   -> 'poll' (caller re-fetches landing,
                                                compares hash, then decides
                                                between 'use' and 'refetch')

    `last_poll_ts` in the future (clock skew) or non-finite is treated as
    'poll' rather than 'use' so we never trust a timestamp the clock says
    can't have happened yet.
    """
    if no_cache:
        return 'refetch'
    if manifest is None:
        return 'refetch'
    last_poll = manifest.get('last_poll_ts')
    if not isinstance(last_poll, (int, float)) or isinstance(last_poll, bool):
        return 'refetch'
    age = now - last_poll
    if 0 <= age < ttl_seconds:
        return 'use'
    return 'poll'


# ---------------------------------------------------------------------------
# Remote mode: chunk discovery
# ---------------------------------------------------------------------------


def _ensure_slash(base_url: str) -> str:
    """Append `/` to base_url if absent — `urljoin` is whitespace-sensitive."""
    return base_url if base_url.endswith('/') else base_url + '/'


def _chunk_name_from_url(url: str) -> str:
    """Last path segment of `url` — used as the on-disk filename for caching."""
    path = urllib.parse.urlparse(url).path
    return path.rsplit('/', 1)[-1] or '_chunk_lx.js'


def extract_chunk_srcs_from_html(html: str, base_url: str) -> list[str]:
    """
    Return absolute URLs of every `<script src="..._lx.js">` reference in `html`,
    in source order with duplicates removed.
    """
    seen: set[str] = set()
    result: list[str] = []
    for match in _SCRIPT_LX_RE.finditer(html):
        absolute = urllib.parse.urljoin(base_url, match.group(1))
        if absolute not in seen:
            seen.add(absolute)
            result.append(absolute)
    return result


def extract_generation_hash(html: str) -> Optional[str]:
    """
    Return the `GLOBAL_GENERATION_HASH` constant emitted into the landing page,
    or None if no declaration is found.
    """
    match = _GENERATION_HASH_RE.search(html)
    return match.group(1) if match else None


def probe_manifest(
    base_url: str,
    fetcher: Fetcher,
    timeout: float,
) -> Optional[list[str]]:
    """
    Return chunk URLs from `<base>/_lx-manifest.json` if it exists; None if not.

    Network errors are converted to None — discovery silently falls back to the
    HTML scrape. A real 4xx (no manifest) is the expected case; 5xx propagates
    via the fetcher's normal retry logic.
    """
    manifest_url = urllib.parse.urljoin(_ensure_slash(base_url), '_lx-manifest.json')
    try:
        head_status, _ = fetcher(manifest_url, method='HEAD', timeout=timeout)
    except RemoteFetchError:
        return None
    if not (200 <= head_status < 300):
        return None
    try:
        get_status, body = fetcher(manifest_url, method='GET', timeout=timeout)
    except RemoteFetchError:
        return None
    if not (200 <= get_status < 300):
        return None
    try:
        data = json.loads(body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    chunks = data.get('chunks')
    if not isinstance(chunks, list):
        return None
    seen: set[str] = set()
    result: list[str] = []
    for name in chunks:
        if not isinstance(name, str):
            continue
        absolute = urllib.parse.urljoin(_ensure_slash(base_url), name)
        if absolute not in seen:
            seen.add(absolute)
            result.append(absolute)
    return result


def remote_chunk_texts(
    base_url: str,
    cache_dir: Path,
    ttl: float,
    no_cache: bool,
    fetcher: Fetcher,
    timeout: float = 10.0,
    now: Optional[float] = None,
) -> list[tuple[str, bytes]]:
    """
    Return a list of (chunk_url, chunk_bytes) ready for build_index_from_texts.

    Pure orchestrator: composes cache_decision, the landing-page fetch, the
    manifest probe, the HTML scrape, and the cache write. Network access is
    confined to the `fetcher` callable so tests can stub it end-to-end.
    """
    base_url = _ensure_slash(base_url)
    timestamp = _now() if now is None else now

    manifest = read_cache_manifest(cache_dir)
    decision = cache_decision(manifest, ttl, timestamp, no_cache)
    debug_log(f"remote_chunk_texts: cache decision={decision} for {base_url}")

    if decision == 'use':
        cached = _read_cached_chunks(cache_dir, manifest)
        if cached is not None:
            return cached
        # Cache manifest references files that vanished — treat as refetch.
        debug_log("remote_chunk_texts: cache manifest references missing files; refetching")
        decision = 'refetch'

    # Both 'poll' and 'refetch' start by fetching the landing page.
    landing_status, landing_body = _fetch_or_raise(fetcher, base_url, method='GET', timeout=timeout)
    if not (200 <= landing_status < 300):
        raise RemoteFetchError(base_url, f"HTTP {landing_status}")
    landing_html = landing_body.decode('utf-8', errors='replace')
    current_hash = extract_generation_hash(landing_html)

    if decision == 'poll' and manifest is not None:
        cached_hash = manifest.get('generation_hash')
        if current_hash is not None and cached_hash == current_hash:
            debug_log("remote_chunk_texts: generation hash unchanged; reusing cached chunks")
            cached = _read_cached_chunks(cache_dir, manifest)
            if cached is not None:
                manifest_out = dict(manifest)
                manifest_out['last_poll_ts'] = timestamp
                _update_manifest_poll_ts(cache_dir, manifest_out)
                return cached

    # 'refetch' (or 'poll' that fell through).
    if current_hash is None:
        warn_log(
            f"GLOBAL_GENERATION_HASH not found in landing page at {base_url}; "
            "falling back to TTL-only caching."
        )

    discovered: Optional[list[str]] = probe_manifest(base_url, fetcher, timeout)
    discovery_method = 'manifest'
    if discovered is None or not discovered:
        discovered = extract_chunk_srcs_from_html(landing_html, base_url)
        discovery_method = 'html-scrape'

    if not discovered:
        raise RemoteFetchError(
            base_url,
            "no _lx.js chunks discovered (tried _lx-manifest.json probe and "
            "<script src=…_lx.js> scrape of the landing page)",
        )

    debug_log(f"remote_chunk_texts: discovered {len(discovered)} chunk(s) via {discovery_method}")

    chunk_texts: list[tuple[str, bytes]] = []
    chunk_files: dict[str, bytes] = {}
    chunk_records: list[dict] = []
    for chunk_url in discovered:
        status, body = _fetch_or_raise(fetcher, chunk_url, method='GET', timeout=timeout)
        if not (200 <= status < 300):
            raise RemoteFetchError(chunk_url, f"HTTP {status}")
        chunk_texts.append((chunk_url, body))
        name = _chunk_name_from_url(chunk_url)
        chunk_files[name] = body
        chunk_records.append({'name': name, 'url': chunk_url})

    new_manifest = {
        'schema_version': 1,
        'base_url': base_url,
        'generation_hash': current_hash,
        'last_poll_ts': timestamp,
        'chunks': chunk_records,
    }
    write_cache_atomic(cache_dir, new_manifest, chunk_files)
    return chunk_texts


def _fetch_or_raise(
    fetcher: Fetcher,
    url: str,
    *,
    method: str,
    timeout: float,
) -> tuple[int, bytes]:
    """Wrapper that converts a 4xx from the fetcher into RemoteFetchError."""
    status, body = fetcher(url, method=method, timeout=timeout)
    if 400 <= status < 500:
        raise RemoteFetchError(url, f"HTTP {status}")
    return status, body


def _read_cached_chunks(
    cache_dir: Path,
    manifest: Optional[dict],
) -> Optional[list[tuple[str, bytes]]]:
    """Return cached (url, bytes) pairs from disk, or None if any chunk is missing."""
    if manifest is None:
        return None
    records = manifest.get('chunks')
    if not isinstance(records, list):
        return None
    result: list[tuple[str, bytes]] = []
    for record in records:
        if not isinstance(record, dict):
            return None
        name = record.get('name')
        url = record.get('url') or name
        if not isinstance(name, str):
            return None
        chunk_path = cache_dir / name
        if not chunk_path.is_file():
            return None
        try:
            result.append((url, chunk_path.read_bytes()))
        except OSError:
            return None
    return result


def _update_manifest_poll_ts(cache_dir: Path, manifest: dict) -> None:
    """Atomically rewrite the manifest file with an updated last_poll_ts."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = cache_dir / _CACHE_MANIFEST
    tmp_path = cache_dir / (_CACHE_MANIFEST + '.tmp')
    tmp_path.write_text(
        json.dumps(manifest, sort_keys=True, indent=2),
        encoding='utf-8',
    )
    os.replace(tmp_path, manifest_path)


# ---------------------------------------------------------------------------
# Index loading: dispatch local vs remote sources
# ---------------------------------------------------------------------------


def _build_or_die(source: Path) -> tuple[list[str], list[str], dict[str, tuple[int, int]]]:
    """Run discover_chunks + build_index, mapping exceptions to exit-code 2."""
    try:
        chunk_paths = discover_chunks(source)
        debug_log(f"Discovered {len(chunk_paths)} chunk(s)")
        return build_index(chunk_paths)
    except (FileNotFoundError, ValueError, OSError) as e:
        error_log(str(e))
        sys.exit(2)


def _load_index(
    args: argparse.Namespace,
) -> tuple[list[str], list[str], dict[str, tuple[int, int]]]:
    """
    Dispatch index loading based on which source was specified.

    Returns the same (files, anchors, id_to_pair) shape as _build_or_die. Calls
    sys.exit(2) on any local or remote fetch failure.
    """
    if getattr(args, 'remote_base_url', None):
        try:
            cache_root = Path(args.cache_dir) if args.cache_dir else default_cache_root()
            cache_dir = base_cache_dir(cache_root, args.remote_base_url)
            chunks = remote_chunk_texts(
                base_url=args.remote_base_url,
                cache_dir=cache_dir,
                ttl=args.cache_ttl,
                no_cache=args.no_cache,
                fetcher=default_fetcher,
                timeout=args.http_timeout,
            )
            return build_index_from_texts(chunks)
        except (RemoteFetchError, ValueError, OSError) as e:
            error_log(str(e))
            sys.exit(2)
    return _build_or_die(Path(args.source))


def _format_remote_rewrite_url(base_url: str, resolved_path: str) -> str:
    """
    Compose `<base_url><quoted-path>[#anchor]` for remote rewrite output.

    Splits `resolved_path` on the first `#` (anchor boundary). The path portion
    is percent-quoted via urllib.parse.quote(safe='/') so spaces become %20 but
    path separators stay as `/`. The anchor portion is appended verbatim — the
    runtime's GetPathById emits anchors that are already URL-safe.
    """
    base = _ensure_slash(base_url)
    if '#' in resolved_path:
        path_part, anchor = resolved_path.split('#', 1)
        return base + urllib.parse.quote(path_part, safe='/') + '#' + anchor
    return base + urllib.parse.quote(resolved_path, safe='/')


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def cmd_resolve(args: argparse.Namespace) -> int:
    _require_source(args, allow_autoinfer=False)
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
    raw_id = match.group('id')

    try:
        landmark_id = urllib.parse.unquote(raw_id, errors='strict')
    except (UnicodeDecodeError, ValueError) as e:
        error_log(f"Malformed percent-encoded URL: {args.url} ({e})")
        return 1

    # Auto-infer remote base for HTTP/HTTPS rewrite input when no source set.
    if (
        args.source is None
        and getattr(args, 'remote_base_url', None) is None
        and args.url.lower().startswith(('http://', 'https://'))
    ):
        args.remote_base_url = args.url.split('#/', 1)[0]
        debug_log(f"auto-inferred --remote-base-url={args.remote_base_url}")

    _require_source(args, allow_autoinfer=True)

    files, anchors, id_to_pair = _load_index(args)
    path = resolve_id(landmark_id, files, anchors, id_to_pair)
    if path is None:
        error_log(f"ID not found: {landmark_id}")
        return 1

    if args.base_url:
        print(_ensure_slash(args.base_url) + path)
        return 0

    if getattr(args, 'remote_base_url', None):
        print(_format_remote_rewrite_url(args.remote_base_url, path))
        return 0

    prefix = match.group('prefix')
    if prefix:
        prefix = _ensure_slash(prefix)
    print(prefix + path)
    return 0


def cmd_dump(args: argparse.Namespace) -> int:
    _require_source(args, allow_autoinfer=False)
    files, anchors, id_to_pair = _load_index(args)
    rows = {
        landmark_id: resolve_id(landmark_id, files, anchors, id_to_pair)
        for landmark_id in id_to_pair
    }

    if args.table:
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
    else:
        print(json.dumps(rows, indent=2, sort_keys=True))

    return 0


def _require_source(args: argparse.Namespace, allow_autoinfer: bool) -> None:
    """
    Exit with code 1 (CLI usage failure) when no source is determinable.

    `argparse` covers the mutual-exclusion check; this catches the rewrite case
    where neither flag was given and auto-infer was also unable to set one.
    """
    if args.source is None and not getattr(args, 'remote_base_url', None):
        if allow_autoinfer:
            error_log(
                "no source provided: pass --from <path>, --remote-base-url <url>, "
                "or a stable URL (rewrite mode auto-infers the base from the URL)"
            )
        else:
            error_log("no source provided: pass --from <path> or --remote-base-url <url>")
        sys.exit(1)


# ---------------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------------


def _add_source_flags(subparser: argparse.ArgumentParser, required: bool) -> None:
    """Add --from / --remote-base-url and related remote-mode flags."""
    group = subparser.add_mutually_exclusive_group(required=required)
    group.add_argument(
        '--from', dest='source', default=None,
        help='Path to a *_lx.js chunk or a directory containing chunks',
    )
    group.add_argument(
        '--remote-base-url', dest='remote_base_url', default=None,
        help='Help mirror base URL (fetched over HTTP, cached locally)',
    )
    subparser.add_argument(
        '--no-cache', dest='no_cache', action='store_true',
        help='[remote mode] Skip cache; re-fetch landing page and every chunk',
    )
    subparser.add_argument(
        '--cache-ttl', dest='cache_ttl', type=float, default=86400.0,
        help='[remote mode] Re-poll cadence for the landing page in seconds (default 86400)',
    )
    subparser.add_argument(
        '--cache-dir', dest='cache_dir', default=None,
        help='[remote mode] Override the platform-default cache root',
    )
    subparser.add_argument(
        '--http-timeout', dest='http_timeout', type=float, default=10.0,
        help='[remote mode] Per-request read timeout in seconds (default 10)',
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Resolve Reverb 2.0 stable landmark URLs to direct file paths.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Local: resolve a single ID
    %(prog)s resolve e5d3d31c42d8d1d4 --from output/FAQs_lx.js

    # Local: rewrite a published stable URL into a direct URL
    %(prog)s rewrite https://example.com/help/#/abc12345 --from output/

    # Remote: rewrite a published stable URL with no local mirror
    %(prog)s rewrite https://example.com/help/#/abc12345

    # Remote: resolve against a published help mirror
    %(prog)s resolve abc12345 --remote-base-url https://example.com/help/

    # Local: dump the entire index as JSON
    %(prog)s dump --from output/
"""
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    resolve_parser = subparsers.add_parser(
        'resolve',
        help='Resolve a landmark ID to a relative file path',
    )
    resolve_parser.add_argument('id', help='Landmark ID (opaque string)')
    _add_source_flags(resolve_parser, required=True)
    resolve_parser.add_argument(
        '--json', action='store_true',
        help='Emit a JSON object instead of the bare path',
    )

    rewrite_parser = subparsers.add_parser(
        'rewrite',
        help='Rewrite a stable URL into a direct file URL',
    )
    rewrite_parser.add_argument('url', help='Stable URL of the form "<prefix>#/<id>"')
    _add_source_flags(rewrite_parser, required=False)
    rewrite_parser.add_argument(
        '--base-url', dest='base_url', default=None,
        help='Replace the inferred URL prefix with this base URL',
    )

    dump_parser = subparsers.add_parser(
        'dump',
        help='Emit the full {id: relative_path} map',
    )
    _add_source_flags(dump_parser, required=True)
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
