---
date: 2026-05-20
type: feat
status: active
topic: reverb-landmark-resolver-remote-fetch
issue: 76
parent-issue: 54
origin: docs/brainstorms/2026-05-20-issue-76-reverb-landmark-resolver-remote-fetch-requirements.md
---

# feat: Reverb Landmark Resolver v2 — Remote `_lx.js` fetching

## Summary

Extend the v1 resolver at `plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py` so it can resolve a stable Reverb 2.0 URL against a published help mirror over HTTP, with no local download step. Adds a `--remote-base-url` mode (and auto-infer for `rewrite`), a local fetch cache keyed by `GLOBAL_GENERATION_HASH` with TTL fallback, retry/proxy/timeout behavior, and a one-line URL-decode fix that also closes a latent local-mode bug for percent-encoded Unicode source IDs.

No changes to `parse_chunk`, `build_index`, or `resolve_id` — v2 is a new fetch-and-cache front end that hands the existing builder in-memory chunk texts instead of a directory glob. No new pip dependencies; stdlib `urllib` covers HTTP, proxies, and TLS.

---

## Problem Frame

A Reverb 2.0 stable URL is fragment-resolved client-side by JavaScript. v1 closes the JS-less gap for **local** mirrors. v2 closes it for **remote** mirrors — the dominant agent case, where an agent pastes any published `…/help/#/<id>` URL and needs the direct file URL back.

Two runtime behaviors shape the design (verified against the 2026.1 source in the parent issue):

1. The runtime applies `decodeURIComponent` to the URL fragment before index lookup. A stable URL `<base>/#/%E6%A6%82%E8%A6%81` resolves against the raw Unicode key `概要` in the index. v1's `rewrite` path skips this decode — a latent bug that bites the `landmark-id-format: source-id` opt-in with non-ASCII IDs.
2. Each Reverb build emits a `GLOBAL_GENERATION_HASH` constant in the landing page. The browser runtime uses it to namespace `localStorage` cache keys. It is a build-coupled invalidation signal — strictly better than a wall-clock TTL because it survives long stable stretches and changes the moment the mirror rebuilds.

---

## Requirements Traceability

Origin requirements are R1–R26 from `docs/brainstorms/2026-05-20-issue-76-reverb-landmark-resolver-remote-fetch-requirements.md`. Acceptance Examples are AE1–AE8 from the same document.

| Origin scope | Carried into units |
|---|---|
| CLI surface (R1–R5) | U5 |
| Chunk discovery over HTTP (R6–R8) | U4 |
| Cache invalidation, generation-hash primary (R9–R12) | U3, U4 |
| Local cache layout (R13–R14) | U3 |
| URL fragment decoding fix (R15–R17) | U1 |
| HTTP behavior (R18–R21) | U2 |
| Output shape parity (R22–R23) | U5 |
| Documentation and verification (R24–R26) | U6, plus U1–U5 test scenarios |

---

## Key Technical Decisions

- **HTML scrape primary, manifest probe forward-compatible (R6, R7).** The landing page fetch is unavoidable for the generation-hash read, so scraping its `<script src="…_lx.js">` tags collapses discovery into the same round-trip and avoids requiring a Reverb-side manifest today. The manifest probe is a single HEAD/GET against `<base>/_lx-manifest.json` — used if it exists, ignored if not. (see origin: `docs/brainstorms/2026-05-20-issue-76-reverb-landmark-resolver-remote-fetch-requirements.md`)
- **Generation hash primary, TTL as poll cadence (R9, R10, R11).** Confirmed in the parent issue's runtime verification. Strictly better than wall-clock TTL; TTL only bounds how often we re-poll the landing page. The `GLOBAL_GENERATION_HASH`-missing fallback (R11) keeps the tool usable against any mirror that ships without the constant.
- **Apply `decodeURIComponent`-equivalent (`urllib.parse.unquote`) in both local and remote rewrite paths (R15, R17).** Doing it only in remote mode creates a confusing asymmetry; the bug is the same in both modes. v1 callers that pass URL-safe ASCII IDs see no behavior change.
- **Auto-infer remote base from input URL when `rewrite` gets an HTTP/HTTPS scheme and neither `--from` nor `--remote-base-url` is set (R2).** Removes the most common ergonomic friction. `--from` retains priority for mixed scenarios.
- **Stdlib `urllib`, not `requests` (R18).** Zero-dep policy. `urllib.request.getproxies()` honors `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY` cleanly; ~15 lines of retry/backoff cover the rest.
- **Hand-rolled platform cache root, not `platformdirs` (resolves origin "Resolvable at planning time" question about R13).** Adding `platformdirs` would contradict the zero-dep policy. Hand-rolled is one `if sys.platform`/env-var check.
- **Per-base cache directory name is percent-encoded `<host>/<path>` (resolves origin question about R14).** Human-inspectable (`%2F` is still recognizable), filesystem-portable on Windows and POSIX, and produces a clear error when the user reports "the wrong directory was used" (the dir name encodes the failing input). A hash would be opaque; raw chars would break on Windows for any URL containing `:`.
- **In-script stub fetcher via dependency injection (resolves origin question about R26).** Cache state machine and discovery functions accept a `fetcher` callable. Verification passes a stub that returns canned bytes per URL. No `http.server` round-trip — keeps verification fast and free of port-collision flakiness.
- **Single script, not a sibling (R5).** Splitting `resolve-landmarks-remote.py` would duplicate `parse_chunk`/`build_index`, force callers to know which to invoke, and fork the workflow doc.

---

## Assumptions

Carried from the origin document and not re-litigated here:

- Reverb 2.0 landing pages render `<script src="…_lx.js">` tags as static HTML (not JS-injected). If a future template moves to injected loading, the HTML scrape silently returns zero chunks and R8's clear error fires; the manifest path (R7) then becomes load-bearing.
- `GLOBAL_GENERATION_HASH` may not be stable across no-op rebuilds — if it embeds a build timestamp, every rebuild invalidates the cache even when content hasn't changed. Acceptable; still strictly better than TTL-only in the common case.
- The retry budget (3 attempts, base delay 1s, doubling — total worst case ~7s before erroring) is right for current mirrors. Adjustable in a follow-up if real usage shows otherwise.
- Python 3.9+ on the agent host (matches v1 baseline).
- The cache directory is a per-host scratch area, not a synchronized resource.

---

## High-Level Technical Design

This illustrates the intended approach and is directional guidance for review, not implementation specification. The implementing agent should treat it as context, not code to reproduce.

The new code path adds a remote front end before the existing builder. Local and remote paths converge once chunk texts are in hand:

```
                       CLI parse
                          │
                          ▼
              ┌───────────────────────┐
              │ Pick source mode      │   ── --from local OR
              │  (mutual exclusion)   │      --remote-base-url remote OR
              └────┬──────────┬───────┘      auto-infer from URL (rewrite only)
                   │          │
            local  │          │  remote
                   ▼          ▼
       discover_chunks()   remote_chunk_texts(base_url, opts, fetcher)
       (existing)              │
            │                  │ • cache check (per-base manifest)
            │                  │ • landing-page fetch (cached or fresh)
            │                  │ • extract GLOBAL_GENERATION_HASH
            │                  │ • compare hash vs cached
            │                  │ • on miss: manifest probe → HTML scrape
            │                  │ • fetch each chunk (with retry)
            │                  │ • atomic write of new cache
            │                  ▼
            │           list of (name, text) pairs
            ▼                  │
       [read .js files]        │
            │                  │
            ▼                  ▼
       build_index(<chunk texts>) ── existing, unchanged
                   │
                   ▼
       resolve_id() / dump / rewrite-format
```

The `rewrite` command additionally URL-decodes the fragment ID (`unquote`) before lookup, in both local and remote paths. Output URL composition in remote `rewrite` mode percent-quotes the resolved path portion (`Advanced Customizations` → `Advanced%20Customizations`) and leaves any `#anchor` suffix as-is.

---

## Output Structure

No new directory hierarchy. v2 modifies existing files in place. New verification fixtures land under the existing `tests/fixtures/` directory.

---

## Implementation Units

### U1. URL fragment decoder fix in `rewrite`

**Goal:** Apply `urllib.parse.unquote` to the fragment ID parsed by `cmd_rewrite`, and produce a clear error on malformed percent sequences. Applies to both local and remote modes (the bug is the same in both).

**Requirements:** R15, R16, R17. Covers AE5.

**Dependencies:** None.

**Files:**
- `plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py` (modify `cmd_rewrite`)
- `plugins/webworks-claude-skills/skills/reverb2/tests/verify-landmark-resolver.py` (add scenarios)
- `plugins/webworks-claude-skills/skills/reverb2/tests/fixtures/unicode-ids_lx.js` (new fixture with a row whose `e[i][2]` is a raw Unicode ID, e.g., `概要`)

**Approach:**
- After `_STABLE_URL_RE.match` extracts the fragment ID, call `urllib.parse.unquote(landmark_id, errors='strict')` to decode percent sequences.
- Catch `UnicodeDecodeError` and any underlying decode error and emit `error_log(f"Malformed percent-encoded URL: {args.url}")` then return exit code `1`.
- No behavior change for ASCII landmark IDs (unquote of a URL-safe ASCII string is a no-op).
- Decoded ID flows into the existing `resolve_id()` lookup unchanged.

**Patterns to follow:**
- Existing `cmd_rewrite` error path on missing fragment (`return 1`, `error_log` to stderr).
- Existing exit-code policy: `1` for resolution failure, `2` for parse/IO failure. Malformed percent-encoding is a *resolution-input* failure → code `1`.

**Test scenarios:**
- Covers AE5. `rewrite` with input `<base>/#/%E6%A6%82%E8%A6%81` against a fixture whose index contains the raw key `概要` returns the same resolved path as `rewrite` against `<base>/#/概要`. Verify both invocations produce identical stdout.
- Covers AE5. `rewrite` with a truncated percent sequence (e.g., `<base>/#/%E6%A6`) exits with code `1` and stderr contains the input URL.
- ASCII landmark ID (e.g., `abc1234567890def`) resolves identically before and after the decode step — regression guard against accidental double-decoding.
- A fragment ID containing a literal `+` (which `unquote` leaves alone, unlike `unquote_plus`) resolves correctly — guards against picking the wrong decode helper.

**Verification:** New scenarios pass in `verify-landmark-resolver.py`; all existing v1 scenarios still pass.

---

### U2. HTTP client primitives — fetch with retry, proxy, timeout

**Goal:** Internal helpers that issue an HTTP GET (or HEAD) via stdlib `urllib`, honor proxy env vars, retry transient failures with exponential backoff, and raise a typed error on permanent failures.

**Requirements:** R18, R19, R20, R21. Supports AE6.

**Dependencies:** None.

**Files:**
- `plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py` (add `http_get`, `http_head`, and a typed exception class)
- `plugins/webworks-claude-skills/skills/reverb2/tests/verify-landmark-resolver.py` (stub-fetcher tests)

**Approach:**
- Define a small typed exception `RemoteFetchError(Exception)` carrying `url` and `reason`. Public API to the rest of the script.
- `http_get(url: str, timeout: float, max_attempts: int = 3, base_delay: float = 1.0) -> bytes` opens the URL via `urllib.request.urlopen` using a `ProxyHandler` built from `urllib.request.getproxies()`. On transient failures (`urllib.error.URLError` with timeout, `http.client.RemoteDisconnected`, 5xx `HTTPError`) it sleeps `base_delay * 2**(attempt-1)` and retries up to `max_attempts`. On 4xx or after exhausted retries, raises `RemoteFetchError`.
- `http_head(url, timeout)` is one attempt, returns boolean (`True` on 2xx, `False` on 4xx, raises on transport error). Used only by the manifest probe.
- Inject `time.sleep` and a clock via small module-level seams (`_sleep = time.sleep`) so tests can monkey-patch without `unittest.mock`.
- Retry is sequential, blocking — no async, no thread pool.

**Patterns to follow:**
- Existing `debug_log` / `error_log` helpers — write retry attempts to `debug_log` (visible under `DEBUG=1`), final failure to `error_log`.
- Existing module structure: small focused helpers above the command dispatchers.

**Test scenarios:**
- Happy GET: stub `urllib.request.urlopen` to return a `BytesIO` with known bytes; `http_get` returns those bytes after one call.
- Transient retry: stub raises a timeout `URLError` twice, then returns bytes; `http_get` returns bytes and made exactly three calls. Verify `_sleep` was called with `1.0` then `2.0`.
- Exhausted retries: stub raises timeout three times; `http_get` raises `RemoteFetchError` whose message contains the URL.
- 4xx non-retried: stub returns `HTTPError` with status `404`; `http_get` raises `RemoteFetchError` on the first attempt (no retries) and the message names the URL and `404`.
- 5xx retried: stub raises `HTTPError` 503 twice then returns bytes; `http_get` returns bytes after three calls.
- Proxy honored: monkey-patch `urllib.request.getproxies()` to return `{'https': 'http://proxy.example:8080'}`, then verify the `ProxyHandler` installed on the opener carries that mapping. (Does not exercise a real proxy; only that the handler is constructed from the env.)

**Verification:** Stub-fetcher tests pass without any network access.

---

### U3. Cache layout and state machine

**Goal:** Per-platform cache root, per-base subdirectory layout, `_manifest.json` write/read, atomic replace on hash change, and the cache-check decision logic. Pure logic — accepts an injected fetcher so this unit is testable without HTTP.

**Requirements:** R9, R10, R11, R12, R13, R14. Supports AE3, AE4.

**Dependencies:** None (cache logic is decoupled from HTTP). Composed with U2 in U4.

**Files:**
- `plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py` (add cache helpers)
- `plugins/webworks-claude-skills/skills/reverb2/tests/verify-landmark-resolver.py` (stub-fetcher cache tests)

**Approach:**
- `default_cache_root() -> Path`: returns `Path(os.environ['LOCALAPPDATA']) / 'webworks' / 'reverb-landmarks'` on Windows, `Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache')) / 'webworks' / 'reverb-landmarks'` on Linux, `Path.home() / 'Library' / 'Caches' / 'webworks' / 'reverb-landmarks'` on macOS. Honors `--cache-dir` override when passed.
- `base_cache_dir(root: Path, base_url: str) -> Path`: parses `base_url` into host + path, percent-encodes the path with `urllib.parse.quote(safe='')` so `/` becomes `%2F`, joins as `root/<host>/<encoded-path>/`.
- `read_cache_manifest(base_dir) -> dict | None`: returns the parsed `_manifest.json` (keys `generation_hash`, `last_poll_ts`, `chunks: [{name, sha256}]`) or `None` if absent or malformed.
- `write_cache_atomic(base_dir, manifest, chunk_texts: dict[name, bytes])`: writes to a sibling `base_dir + '.tmp'` directory, then `os.replace` (or platform-equivalent rename) over the live directory. Old cache is discarded.
- `cache_decision(manifest, ttl_seconds, now, no_cache_flag) -> Literal['use', 'poll', 'refetch']`:
  - `no_cache_flag=True` → `refetch`
  - `manifest is None` → `refetch`
  - `now - last_poll_ts < ttl` → `use`
  - otherwise → `poll` (caller fetches landing, compares hash, then either marks `use` after `last_poll_ts` reset or runs `refetch`)
- All filesystem ops use `pathlib.Path`; no shelling out.

**Patterns to follow:**
- Existing pure helpers above the dispatchers (`discover_chunks`, `build_index`).
- Existing error wrapping in `_build_or_die` — cache helpers raise; dispatcher maps to exit codes.

**Test scenarios:**
- `default_cache_root` on Windows-style env (`LOCALAPPDATA` set) returns the expected path. Linux-style (`XDG_CACHE_HOME` unset) falls back to `~/.cache/webworks/reverb-landmarks/`. macOS path uses `~/Library/Caches/`.
- `base_cache_dir` for `https://static.webworks.com/docs/epublisher/latest/help/` returns `<root>/static.webworks.com/docs%2Fepublisher%2Flatest%2Fhelp%2F/` — verifies percent-encoding preserves nested paths.
- `base_cache_dir` for `https://static.webworks.com/` (root path) does not produce a doubled separator and is filesystem-creatable on both Windows and POSIX.
- `read_cache_manifest` returns `None` for a missing directory, for a directory missing `_manifest.json`, and for a malformed (non-JSON) manifest.
- `write_cache_atomic` writes a manifest and chunk files to a temp directory, then `os.replace` overlays them. After the call, the live directory contains exactly the new chunks (no leftover files from a prior cache). Verify with a synthetic prior cache containing an extra file that should be gone after the atomic write.
- `cache_decision`: `no_cache_flag=True` always returns `refetch`. Missing manifest returns `refetch`. Manifest within TTL returns `use`. Manifest past TTL returns `poll`.
- Concurrent-write tolerance: simulate a partial write (manifest exists in `.tmp/` but `os.replace` has not happened); a subsequent read sees the pre-replace cache, not a half-written one. Verifies the atomic-replace invariant.

**Verification:** Stub tests cover every branch of `cache_decision`; manifest round-trip and atomic-replace tests pass; no network access.

---

### U4. Chunk discovery — landing-page fetch, manifest probe, scrape, generation hash

**Goal:** Compose U2 (HTTP) and U3 (cache) into the remote-mode entry point that returns a list of `(chunk_name, chunk_bytes)` pairs ready for `build_index`. Handles the manifest probe, HTML scrape, `GLOBAL_GENERATION_HASH` extraction, and the cache-or-refetch state transitions.

**Requirements:** R6, R7, R8, R9, R10, R11. Supports AE2, AE3, AE4.

**Dependencies:** U2, U3.

**Files:**
- `plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py` (add `remote_chunk_texts` and helpers)
- `plugins/webworks-claude-skills/skills/reverb2/tests/verify-landmark-resolver.py` (HTML/JSON discovery tests)
- `plugins/webworks-claude-skills/skills/reverb2/tests/fixtures/landing-with-hash.html` (fixture: minimal landing HTML with `<script src="A_lx.js">`, `<script src="B_lx.js">`, and a `GLOBAL_GENERATION_HASH = "<hex>";` constant)
- `plugins/webworks-claude-skills/skills/reverb2/tests/fixtures/landing-no-hash.html` (fixture: same HTML, no `GLOBAL_GENERATION_HASH` declaration — for R11 fallback)
- `plugins/webworks-claude-skills/skills/reverb2/tests/fixtures/lx-manifest.json` (fixture: `{"chunks": ["A_lx.js", "B_lx.js"]}` or whatever shape is plausible for a future Reverb manifest — see Note)

**Note on manifest shape:** Since Reverb does not currently ship `_lx-manifest.json`, this plan picks a minimal shape (`{"chunks": [<names>]}`) for the probe. The format is forward-compatible: if Reverb later ships a richer shape, the probe code only needs to read the `chunks` field. Document the assumed shape in the script docstring.

**Approach:**
- `extract_chunk_srcs_from_html(html: str, base_url: str) -> list[str]`: regex over the HTML for `<script[^>]*\bsrc=["']([^"']*_lx\.js)["']`, then `urllib.parse.urljoin(base_url, src)` per match. De-duplicate while preserving order.
- `extract_generation_hash(html: str) -> str | None`: regex for a constant declaration like `(?:var|const|let)\s+GLOBAL_GENERATION_HASH\s*=\s*["']([^"']+)["']`. Returns the captured hex or `None`. (Exact pattern confirmed in U4 dev by reading the parent issue's runtime verification; if pattern mismatches a real mirror, U4 tests should be the first to fail.)
- `probe_manifest(base_url, fetcher, timeout) -> list[str] | None`: HEAD `<base>/_lx-manifest.json`. On 2xx, GET and parse `{"chunks": [<names>]}`, return absolute URLs. On 4xx or network error, return `None` (silent fallback to scrape).
- `remote_chunk_texts(base_url, cache_dir, ttl, no_cache, fetcher, now) -> list[tuple[str, bytes]]`: orchestrator:
  1. Compute `cache_dir = base_cache_dir(root, base_url)`.
  2. `decision = cache_decision(...)`.
  3. If `use`: read chunk bytes from `cache_dir`, return.
  4. If `poll`: fetch landing, extract hash, compare with manifest's `generation_hash`. Match → reset `last_poll_ts`, write manifest, return cached chunks. Mismatch → fall through to `refetch`.
  5. If `refetch`: fetch landing (if not already), extract hash (or `None` → R11 warning to stderr), probe manifest → fallback to scrape, fetch each chunk via U2, `write_cache_atomic`, return chunk bytes.
  6. Empty discovery → raise `RemoteFetchError` whose message names the base URL and methods tried (R8).

**Patterns to follow:**
- Module-level `re.compile(...)` constants for the script-src and hash regexes, named consistently with `_LANDMARKS_RE` and `_STABLE_URL_RE`.
- Existing `debug_log` calls at decision points.

**Test scenarios:**
- Covers AE2. With a stub fetcher returning `landing-with-hash.html`, `extract_chunk_srcs_from_html` returns `[<base>A_lx.js, <base>B_lx.js]` in source order with no duplicates.
- `extract_chunk_srcs_from_html` tolerates `<script src='X_lx.js'>` (single quotes), `<script type="text/javascript" src="X_lx.js">` (extra attrs), and ignores `<script src="not_landmarks.js">`.
- `extract_generation_hash` recovers the constant from `var GLOBAL_GENERATION_HASH = "abc123";`, `const GLOBAL_GENERATION_HASH = "abc123";`, and returns `None` when the constant is absent.
- Covers AE2. Manifest probe: stub fetcher returns 2xx on `_lx-manifest.json` HEAD/GET; `probe_manifest` returns the absolute URLs and `remote_chunk_texts` does not invoke the HTML scrape.
- Covers AE2. Empty discovery: stub returns landing HTML with no `_lx.js` script tags and 404 on the manifest probe; `remote_chunk_texts` raises `RemoteFetchError` whose message names the base URL and both methods tried.
- Covers AE3. First-call cache miss: `remote_chunk_texts` against an empty cache invokes the stub fetcher for landing + each chunk, writes the manifest, and the on-disk cache directory contains every chunk plus `_manifest.json` with the expected generation hash.
- Covers AE3. Second-call within TTL: same arguments, same stub, but no stub calls are made; chunks are read from disk.
- Covers AE3. Hash unchanged after TTL: stub returns the same landing HTML; `remote_chunk_texts` issues one landing fetch (no chunk fetches), updates `last_poll_ts`, returns cached chunks.
- Covers AE3. Hash changed: stub returns landing HTML with a different `GLOBAL_GENERATION_HASH`; `remote_chunk_texts` re-fetches every chunk and `write_cache_atomic` replaces the cache. Old chunk files are gone.
- Covers AE3. `no_cache=True`: every invocation bypasses both cache reads and the hash check; every chunk is re-fetched.
- Covers AE4. Landing page has no `GLOBAL_GENERATION_HASH`: `remote_chunk_texts` falls back to TTL-only behavior, writes a one-line warning to stderr, and otherwise returns the expected chunks. The manifest records `generation_hash: null` (or omits the field) so a later run still understands the cache shape.

**Verification:** All discovery and cache-state-machine tests pass without network access.

---

### U5. CLI surface, mutual exclusion, auto-infer, output formatting

**Goal:** Add `--remote-base-url`, `--no-cache`, `--cache-ttl`, `--cache-dir`, `--http-timeout` to `resolve`, `rewrite`, and `dump`. Enforce mutual exclusion with `--from`. Auto-infer remote base for `rewrite` when input has an HTTP scheme and no source flags are set. Wire `_build_or_die` (or its remote-mode sibling) to load chunks via local discovery or `remote_chunk_texts`. Percent-quote the file-path portion of `rewrite` output; leave `#anchor` as-is.

**Requirements:** R1, R2, R3, R4, R5, R22, R23. Covers AE1, AE7. Composes with AE5–AE6 via earlier units.

**Dependencies:** U1, U2, U3, U4.

**Files:**
- `plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py` (CLI + dispatcher wiring)
- `plugins/webworks-claude-skills/skills/reverb2/tests/verify-landmark-resolver.py` (CLI contract tests)

**Approach:**
- Promote `--from` from `required=True` to mutually exclusive with `--remote-base-url` per subcommand. Use `argparse.add_mutually_exclusive_group(required=True)` for `resolve` and `dump`. For `rewrite`, the group is `required=False` because auto-infer covers the URL-scheme case; emit a clear error if no source can be determined.
- New shared flags (per subcommand, via a helper that adds them):
  - `--remote-base-url <url>`
  - `--no-cache` (store_true)
  - `--cache-ttl <seconds>` (default `86400`)
  - `--cache-dir <path>` (default: result of `default_cache_root()`)
  - `--http-timeout <seconds>` (default `10`)
- Auto-infer in `cmd_rewrite`: if `args.url` starts with `http://` or `https://`, `args.source` is None, and `args.remote_base_url` is None, set `args.remote_base_url = args.url.split('#/', 1)[0]`.
- A single `_load_index(args) -> tuple[files, anchors, id_to_pair]` function reads either local files (existing `_build_or_die` path) or invokes `remote_chunk_texts` and passes the chunk-bytes list to a new `build_index_from_texts(chunks: list[tuple[str, bytes]])` helper. `build_index_from_texts` mirrors the existing `build_index` exactly — it just takes pre-loaded bytes instead of file paths.
- Output composition for `rewrite` in remote mode (R22, R23):
  - Resolved path may contain `/` and spaces. Split on `#` once: path portion and optional anchor portion.
  - `urllib.parse.quote(path_portion, safe='/')` → `Advanced Customizations/_xslt-extensions.04.1.html` → `Advanced%20Customizations/_xslt-extensions.04.1.html`.
  - Reassemble: `<remote-base-url>` + quoted path + (`#` + anchor when present, unmodified).
- Error mapping: `RemoteFetchError` → exit code `2` with stderr message naming the URL and failure mode (matches v1's IO-failure code).

**Patterns to follow:**
- Existing `subparsers.add_parser(...)` structure with one `add_argument` cluster per subcommand.
- Existing argparse error formatting via `error_log` for runtime errors (not argparse parse errors, which `argparse` handles).

**Test scenarios:**
- Covers AE1. CLI `rewrite "https://example.com/help/#/abc1234567890def"` with no source flags, stub fetcher returning fixture chunks: exits 0, stdout is `https://example.com/help/<resolved-path>`. The same command with `--from <local-dir>` instead behaves identically to v1 (regression guard).
- Covers AE1 (negative). CLI `rewrite "https://example.com/help/#/x" --from local/ --remote-base-url https://other/`: argparse mutual-exclusion error on stderr, non-zero exit.
- Covers AE7. CLI `rewrite` resolving to `Advanced Customizations/_xslt-extensions.04.1.html` produces output where the path portion is percent-quoted as `Advanced%20Customizations/_xslt-extensions.04.1.html`. With a non-empty anchor (`file.html#wwp100`), the anchor is left as-is in output.
- CLI `resolve <id> --remote-base-url <url>` with stub fetcher returns the same bare relative path (`Group/page.html#wwp100`) as the local-mode invocation against the same fixture chunks. JSON variant matches.
- CLI `dump --remote-base-url <url>` emits the same JSON as `dump --from <local-dir>` against the equivalent fixtures.
- CLI `--no-cache` forces re-fetch: run twice in sequence against a temp cache dir; the stub records two landing-fetch calls and two chunk-fetch passes.
- CLI `--cache-ttl 0` always polls the landing page (TTL expired immediately); verifies the `cache_decision` boundary.
- CLI `--http-timeout 5` propagates into the stub's recorded timeout argument.
- CLI `rewrite` against an HTTP URL with `--from <local-dir>` set: `--from` wins, no remote fetch attempted.
- CLI failure surface: a 404 on a discovered chunk URL → exit code `2`, stderr names the failing URL and the response status.
- CLI failure surface: a 4xx on the landing page → exit code `2`, stderr names the base URL.

**Verification:** Subprocess-based CLI tests cover every new flag, the mutual exclusion, the auto-infer rule, and the output formatting. All v1 CLI tests continue to pass.

---

### U6. Workflow documentation update + worked example against a real mirror

**Goal:** Rewrite `landmark-resolution.md` to cover the remote case end-to-end. New "Step 1b: Remote mirror" section, an auto-infer example, a short cache-behavior callout (where the cache lives per platform, how to clear it, when it auto-invalidates), and a manual smoke-test worked example against a real published Reverb mirror (input URL → expected resolved URL).

**Requirements:** R24, R25. Covers AE8.

**Dependencies:** U5.

**Files:**
- `plugins/webworks-claude-skills/skills/reverb2/workflows/landmark-resolution.md` (modify; new Step 1b and Worked Example block)

**Approach:**
- Insert "Step 1b: Remote mirror" after the existing Step 1, parallel in shape: a small table listing the supported input shapes (`--remote-base-url <url>` flag, or auto-infer from an HTTP `rewrite` input), and an example invocation for each.
- Add a "Cache behavior" subsection: cache root per platform, the `--no-cache` and `--cache-ttl` flags, the `GLOBAL_GENERATION_HASH`-driven invalidation, the TTL-only fallback warning, manual clear by `rm -rf <cache-root>`.
- Replace the Worked Example block with a remote-mode example: paste the canonical published mirror URL → run `rewrite` → expect the documented direct URL. Include the exact expected output so a reader can copy-paste-verify.
- Update the table at Step 2 to add a row for the remote-mode flags.
- Remove the v1 caveat sentence ("If the help output is hosted… Remote `_lx.js` fetching is deferred follow-up work").
- Update intake item 5 in `SKILL.md` if its wording mentions local-only resolution. (Quick check during U6: it currently says "Resolve a stable Reverb landmark URL (or hash) to a direct file path" — neutral on local vs remote, so likely no change needed.)

**Patterns to follow:**
- Existing workflow doc structure (`<required_reading>`, `<process>` with numbered Steps, `<success_criteria>`).
- Existing table shapes for inputs/modes/exit codes.

**Test scenarios:**
- Test expectation: none — documentation unit. Verified manually by:
  1. Following the rewritten Step 1b against the documented published mirror produces the expected direct URL.
  2. Following the cache callout (cache root, clear command) on the implementer's actual platform produces the expected directory and removes it cleanly.

**Verification:** A reader who has not seen v1 can read the workflow doc front-to-back and resolve a remote stable URL on the first try.

---

## Scope Boundaries

### Deferred for later

(From origin "Out of Scope (Reiterated)" — explicitly deferred, not in this plan.)

- Authenticated remote fetches (customer portals behind auth).
- Server-side Reverb changes (new endpoints, manifest emission as a Reverb-side feature, hash-as-header).
- Reverse lookup over HTTP (path → ID against a remote mirror).
- Real-HTTP calls in the verification script.
- New pip dependencies (`requests`, `httpx`, `platformdirs`, etc.).
- Cache eviction strategies / size caps.
- Caching for local-mode (`--from`) invocations.

### Deferred to Follow-Up Work

(Plan-local implementation sequencing — items the agent noticed during planning but that fall outside #76's scope.)

- Persistent cache schema versioning. The current `_manifest.json` shape is implicit. If a future change to the manifest fields breaks compatibility, the symptom will be a `KeyError` on the next invocation. Adding a `schema_version` field now is cheap insurance; deferring it is fine because the cache is per-user scratch and a manual `rm -rf` is the recovery.
- Concurrent invocation locking. Two simultaneous invocations against the same base URL on a fresh cache will both fetch and race the `os.replace`. Last-write-wins is acceptable for a per-user agent tool; if this becomes a problem in CI usage, an advisory lockfile is straightforward.
- Telemetry / cache-hit metrics. Useful for tuning the default TTL, not needed for v2.

### Out of scope for this product

- Anything that changes the Reverb 2.0 published output. v2 only consumes Reverb's existing artifacts.

---

## System-Wide Impact

- **`reverb2` skill:** new behavior on the resolver script. Workflow doc covers the remote case. SKILL.md intake item 5 likely unchanged (neutral wording already).
- **`epublisher` skill:** unaffected. The cross-reference from `epublisher/references/product-foundations.md` to the resolver continues to work; v2 only adds capability.
- **Other consumers of `resolve-landmarks.py`:** none currently. Backward compatibility: every existing flag and behavior is preserved. Existing `--from` users see no change.
- **CI / build pipeline:** no change. The verification script remains the single source of truth for resolver correctness; new scenarios extend it without changing the invocation contract.

---

## Risks and Mitigations

- **Risk: Mirror landing page is JS-injected, scrape finds zero chunks.** Mitigation: the manifest probe (R7) is the fallback. If a real mirror ships without either, R8's clear error names the failed discovery methods.
- **Risk: `GLOBAL_GENERATION_HASH` regex is wrong for real mirrors.** Mitigation: U4 includes a manual smoke test against a real published mirror; the regex is tuned against fixture HTML at planning time and reconciled against the smoke test before merge. R11's fallback path provides a safety net even if the regex misses entirely.
- **Risk: Atomic-replace fails on Windows when chunk files are open.** Mitigation: `os.replace` is the documented atomic-rename primitive on both platforms; chunk files are only opened read-only during reads, closed before writes. Tests cover the partial-write scenario.
- **Risk: Stdlib `urllib` proxy handling differs from `requests`.** Mitigation: U2 tests verify the `ProxyHandler` is constructed from `getproxies()` correctly. Real-proxy testing is documented in U6's smoke-test section as a manual step in environments where a proxy is in use.
- **Risk: Cache-dir name collision when two base URLs differ only in trailing slash.** Mitigation: percent-encoding preserves the slash. `https://example.com/help/` and `https://example.com/help` produce different directory names (`help%2F` vs `help`). Documented in U3 docstring.
- **Risk: A future Reverb release changes `_lx.js` script-tag rendering and the scrape silently breaks.** Mitigation: R8's clear error fires the moment scrape returns zero chunks; users get an actionable message naming both methods tried. The manifest path (R7) becomes the recovery without a code change if Reverb ever ships a manifest.

---

## Verification Strategy

- Every new code path lands with at least one verification scenario in `verify-landmark-resolver.py`. Scenarios use injected stub fetchers; no network calls.
- All existing v1 scenarios in `verify-landmark-resolver.py` continue to pass — regression guard.
- One manual smoke test against a real published Reverb mirror is captured as a worked-example block in `workflows/landmark-resolution.md` (the input URL and the expected resolved URL). The smoke test confirms the `GLOBAL_GENERATION_HASH` regex and the script-tag scrape pattern match real-world output.
- Verification command: `python plugins/webworks-claude-skills/skills/reverb2/tests/verify-landmark-resolver.py` exits 0.
