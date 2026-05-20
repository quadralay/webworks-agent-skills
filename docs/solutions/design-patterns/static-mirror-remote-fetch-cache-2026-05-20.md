---
title: Use the upstream build's generation hash as the primary cache key when extending a static-mirror tool to fetch over HTTP
date: 2026-05-20
category: design-patterns
module: reverb2
problem_type: design_pattern
component: tooling
severity: medium
applies_when:
  - A static-mirror tool (e.g., a JS-less resolver for a JS-runtime URL scheme) is being extended to fetch its source files over HTTP instead of reading them locally
  - The upstream site emits a content-derived build identifier into a known surface (a constant in the landing page, an HTTP header, a manifest file)
  - The original runtime already uses that identifier for client-side cache invalidation
  - Wall-clock TTL alone would force a choice between stale data and wasted re-fetches across long stretches of upstream stability
  - The mirror must replicate browser-runtime behaviors (URL decoding, merge order, fragment parsing) so that its outputs match what the runtime would produce
related_components:
  - reverb2
  - epublisher
  - tooling
tags:
  - reverb2
  - landmark-resolver
  - static-mirror
  - http-caching
  - generation-hash
  - cache-invalidation
  - runtime-fidelity
  - url-decode
---

# Use the upstream build's generation hash as the primary cache key when extending a static-mirror tool to fetch over HTTP

## Context

Issue #54 shipped a JS-less Reverb landmark resolver that parses local `_lx.js` chunks (the `static-mirror-of-a-JS-runtime` pattern, captured in `reverb-landmark-resolver-static-mirror-2026-05-20.md`). That tool answered the "I have the help directory on disk" case. It did not answer the more common agent case: "I have a stable URL pointing at a published Reverb mirror I have never downloaded."

Issue #76 extended the resolver with `--remote-base-url` so any published mirror works without a local download. Doing that surfaces two architectural questions a v1-only design never has to answer:

1. **How does the resolver know what to refetch and when?** A wall-clock TTL is the obvious default but is the wrong primary signal — Reverb mirrors are stable for weeks or months between rebuilds, and a 24h TTL either re-fetches uselessly or serves stale data the moment a rebuild lands.
2. **What runtime behaviors that v1 never had to replicate now become load-bearing?** The browser runtime decodes the URL fragment with `decodeURIComponent` before looking the ID up. v1's `rewrite` path never decoded — a latent bug that bites the moment a project ships the `landmark-id-format: source-id` opt-in (2026.1) with non-ASCII source IDs.

Runtime verification of `landmarks.js` for 2026.1 answered both: each Reverb build emits a `GLOBAL_GENERATION_HASH` constant into the landing page, and the in-browser runtime keys its `localStorage` cache off that hash. The runtime already solved cache invalidation correctly; the static mirror needed to mirror that decision, not invent its own.

## Guidance

When extending a static-mirror tool to fetch its source files over HTTP, treat *both* the data-files contract and the runtime's *operational* behaviors as part of the contract you must replicate.

### Rule 1 — Use the build's content-derived hash as the primary cache key; TTL is the poll cadence, not the invalidation signal

If the upstream emits a build hash, your cache lifecycle becomes a three-state machine driven by the hash, not by wall-clock time:

| Cache state | Trigger | Action |
|-------------|---------|--------|
| `use` | within TTL, manifest present | reuse cached chunks, zero HTTP requests |
| `poll` | past TTL, manifest present | fetch only the landing page; compare hash; if unchanged, reset TTL window and reuse cached chunks; if changed, refetch all chunks |
| `refetch` | no manifest, or `--no-cache`, or post-poll mismatch | fetch landing page + every discovered chunk; write a new manifest atomically |

TTL still earns a role — it bounds how often the resolver re-polls the landing page. Without TTL, every invocation issues at least one HTTP request. With TTL=24h, sustained usage against a stable mirror is fully offline most of the time.

```python
# resolve-landmarks.py
def cache_decision(manifest, ttl_seconds, now, no_cache) -> str:
    if no_cache:
        return 'refetch'
    if manifest is None:
        return 'refetch'
    last_poll = manifest.get('last_poll_ts')
    if not isinstance(last_poll, (int, float)) or isinstance(last_poll, bool):
        return 'refetch'           # corrupt/missing/clock-skew → refetch
    age = now - last_poll
    if 0 <= age < ttl_seconds:
        return 'use'
    return 'poll'
```

The `last_poll` guard catches a real failure mode: timestamps in the future (clock skew) or non-finite values must not collapse to the `use` branch — they must force a `poll` so the cache never trusts a timestamp the clock says cannot have happened yet.

### Rule 2 — Make the landing-page fetch do double duty

The same HTTP request that gives you the build hash is the request that gives you the chunk discovery (the `<script src="…_lx.js">` references). Treat the landing page as a single round-trip that yields *both* signals. A discovery-first design that asks "what chunks exist?" before "has the build changed?" doubles the HTTP cost in the steady state.

```python
# remote_chunk_texts: landing page fetch happens once, drives both signals
landing_status, landing_body = _fetch_or_raise(fetcher, base_url, method='GET', timeout=timeout)
landing_html = landing_body.decode('utf-8', errors='replace')
current_hash = extract_generation_hash(landing_html)
# ...later, after the hash-comparison branch:
discovered = probe_manifest(base_url, fetcher, timeout)   # forward-compat probe
if discovered is None or not discovered:
    discovered = extract_chunk_srcs_from_html(landing_html, base_url)
```

A `_lx-manifest.json` HEAD probe is included as a forward-compatibility hook in case the upstream ever ships one; until then the HTML scrape carries discovery and the manifest path stays dormant. The probe is intentionally a *preference*, not a requirement — never make your tool depend on a manifest the upstream has not committed to emitting.

### Rule 3 — Fall back to TTL-only if the hash is missing, but log it visibly

Some upstream mirrors will not emit the hash (older builds, customer-customized templates, or future template churn). Tolerate the gap, but make the degradation observable: a one-line stderr warning per invocation, not a silent fallback that quietly serves stale data with no clue to the operator.

```python
if current_hash is None:
    warn_log(
        f"GLOBAL_GENERATION_HASH not found in landing page at {base_url}; "
        "falling back to TTL-only caching."
    )
```

### Rule 4 — Runtime fidelity extends to URL decoding (and every other client-side step the browser performs before the index lookup)

A static mirror has to replicate every transformation the runtime applies to its input *before* the data-file contract takes over. The v1 doc captured this for index/merge semantics. v2 adds the URL-fragment decode step that the runtime performs unconditionally:

```js
// landmarks.js (browser runtime)
var m = /^#\/([^\s/?#]+)(.*)$/.exec(param_hash || '');
if (m) {
  try { return decodeURIComponent(m[1]); } catch (e) { return null; }
}
```

```python
# resolve-landmarks.py — mirror the decode step
raw_id = match.group('id')
try:
    landmark_id = urllib.parse.unquote(raw_id, errors='strict')
except (UnicodeDecodeError, ValueError) as e:
    error_log(f"Malformed percent-encoded URL: {args.url} ({e})")
    return 1
```

A v1 caller passing URL-safe ASCII IDs sees no behavior change. A v2 caller pasting a stable URL with a percent-encoded Unicode source ID (`#/%E6%A6%82%E8%A6%81` → `概要`) resolves correctly. The malformed-percent path returns a clear error instead of silently passing garbage to the index lookup.

### Rule 5 — Auto-infer the remote base from the input URL for paste-ergonomic CLIs

When the input *is* a URL with the same prefix the tool would otherwise need as a flag, prefer to infer over requiring the user to repeat themselves:

```python
if (
    args.source is None
    and getattr(args, 'remote_base_url', None) is None
    and args.url.lower().startswith(('http://', 'https://'))
):
    args.remote_base_url = args.url.split('#/', 1)[0]
```

Explicit `--from` or `--remote-base-url` overrides the inference. The rule is unambiguous (HTTP scheme + neither flag set), so the user can predict when inference will fire without reading the implementation.

## Why This Matters

**The hash-keyed cache is correctness, not just an optimization.** A wall-clock TTL gives the operator one knob with two failure modes — set it short and waste bandwidth on stable mirrors, set it long and serve stale data after a rebuild. The build's content-derived hash collapses both failure modes into a single signal that is fresh exactly as long as the build is fresh. Reverb's `compute_cache_key(generation_hash, base_url)` in `landmarks.js` is the same shape: the browser runtime already established that this is the right cache key for *this* problem. A static mirror that picks a different invalidation strategy will diverge from the runtime's freshness contract in observable ways.

**Runtime fidelity is non-negotiable in the URL-decode case.** v1 happened to work because the only ID formats in production at the time were URL-safe ASCII (16- or 8-character hex). The 2026.1 `landmark-id-format: source-id` opt-in (documented in `epublisher-format-traits-xml-schema-2026-05-09.md`) breaks that assumption — source IDs can be arbitrary Unicode, and stable URLs carry their percent-encoded form. The v1 `rewrite` code was one line away from being correct; the bug was latent only because nobody had shipped a project with non-ASCII source IDs yet. A v2 design that paid attention to remote-fetch fidelity but skipped URL-decode fidelity would have left the bug latent forever.

**Make degradation observable.** Silent fallback from `hash` to `TTL` (Rule 3) and silent fallback from `manifest` to `HTML scrape` (Rule 2) are both correct as engineering, but both are dangerous if invisible. The cost of a `warn_log` line is zero; the cost of an operator chasing a stale-cache bug for a week is high.

## When to Apply

- Building a JS-less mirror of any tool whose authoritative behavior lives in a browser runtime, where the mirror will fetch its source files over the network rather than from disk
- Designing the cache layer for any tool that reads from a static site that publishes a build identifier (generation hash, build ID, sentinel file, ETag-as-content-hash, etc.)
- Reviewing an existing static mirror that uses TTL-only invalidation against an upstream that emits a content hash — likely an asymmetry worth closing
- Reviewing an existing static mirror that does not replicate every client-side transformation the upstream runtime performs between the user input and the data-file lookup

## Examples

### Generation hash as the primary key (the cache-decision rule)

The full state machine: `cache_decision` returns one of three sentinels; the caller drives the network behavior from there.

```python
# Caller in remote_chunk_texts
decision = cache_decision(manifest, ttl, timestamp, no_cache)

if decision == 'use':
    return _read_cached_chunks(cache_dir, manifest)

# 'poll' and 'refetch' both fetch the landing page first
landing_status, landing_body = _fetch_or_raise(fetcher, base_url, method='GET', timeout=timeout)
current_hash = extract_generation_hash(landing_body.decode('utf-8', errors='replace'))

if decision == 'poll' and manifest is not None:
    if current_hash is not None and manifest.get('generation_hash') == current_hash:
        # hash unchanged — reset TTL window, reuse cached chunks
        manifest_out = dict(manifest); manifest_out['last_poll_ts'] = timestamp
        _update_manifest_poll_ts(cache_dir, manifest_out)
        return _read_cached_chunks(cache_dir, manifest)

# falling through means: hash changed (or no prior cache, or no_cache, or
# poll missed the cache file on disk) — refetch every discovered chunk
```

The cache directory layout that lets multiple base URLs coexist:

```
<cache_root>/
  <percent-encoded-host>/<percent-encoded-help-path>/
    _manifest.json     # {generation_hash, last_poll_ts, chunks: [{name, url}, ...]}
    chunk1_lx.js
    chunk2_lx.js
    ...
```

Per-base manifests use `os.replace` for atomic swaps so a crash mid-write leaves either the old or the new manifest, never a torn one:

```python
def _update_manifest_poll_ts(cache_dir: Path, manifest: dict) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = cache_dir / _CACHE_MANIFEST
    tmp_path = cache_dir / (_CACHE_MANIFEST + '.tmp')
    tmp_path.write_text(json.dumps(manifest, sort_keys=True, indent=2), encoding='utf-8')
    os.replace(tmp_path, manifest_path)
```

### URL fragment decode (the runtime-fidelity rule)

Decoding lives in the `rewrite` command path so it applies uniformly to local and remote sources:

```python
def cmd_rewrite(args):
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
    # ...rest of rewrite logic uses landmark_id, not raw_id...
```

The `errors='strict'` argument is the load-bearing detail — it surfaces malformed percent sequences as an explicit error instead of letting them silently pass a corrupt string through to the lookup.

### Stdlib retry instead of a `requests` dependency (the no-new-deps rule)

`urllib.request.getproxies()` honors `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY` automatically. Exponential backoff is ~15 lines of code. The carrying cost of a new dependency is not justified by ergonomics alone.

```python
def http_get(url, timeout=10.0, max_attempts=3, base_delay=1.0):
    opener = _build_opener()  # builds with ProxyHandler from getproxies()
    for attempt in range(1, max_attempts + 1):
        try:
            with opener.open(url, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as e:
            if not _is_retryable(e):                  # 4xx → raise immediately
                raise RemoteFetchError(url, f"HTTP {e.code}: {e.reason}") from e
            last_exc = e
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionResetError) as e:
            if not _is_retryable(e):
                raise RemoteFetchError(url, f"{type(e).__name__}: {e}") from e
            last_exc = e
        if attempt < max_attempts:
            _sleep(base_delay * (2 ** (attempt - 1)))
    raise RemoteFetchError(url, f"exhausted {max_attempts} attempts: {last_exc}")
```

`_is_retryable` separates the transient errors (5xx, timeouts, connection resets) from the terminal ones (4xx, DNS failure, TLS error). A 404 on a discovered chunk URL must not be retried — it is information about the upstream, not a transient blip.

### Stubbed fetcher in tests (the no-real-HTTP rule)

The entire fetch and cache layer is driven through a `Fetcher` callable. Tests pass a stub that returns canned `(status, body)` pairs without touching the network:

```python
Fetcher = Callable[..., tuple[int, bytes]]   # returns (status_code, body_bytes)

def remote_chunk_texts(base_url, cache_dir, ttl, no_cache, fetcher, timeout=10.0, now=None):
    # ... orchestrates cache_decision, landing page fetch via fetcher,
    #     manifest probe via fetcher, chunk fetch via fetcher, cache write
```

This makes the cache state machine and the discovery logic fully unit-testable. Real HTTP behavior is verified once, manually, against a real published mirror — captured in the workflow doc as a worked example, not as a CI dependency.

## Related

- `docs/solutions/design-patterns/reverb-landmark-resolver-static-mirror-2026-05-20.md` — the v1 design pattern this learning extends (the parser/index half of the static-mirror story; v2 here adds the HTTP-fetch/cache/runtime-fidelity half)
- `docs/solutions/documentation-gaps/epublisher-format-traits-xml-schema-2026-05-09.md` — documents the `landmark-id-format: source-id` opt-in that exposed the v1 percent-decode latent bug
- `plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py` — the v2 resolver (HTTP client, cache state machine, discovery, URL-decode fix)
- `plugins/webworks-claude-skills/skills/reverb2/workflows/landmark-resolution.md` — workflow doc with the remote worked example
- `plugins/webworks-claude-skills/skills/reverb2/tests/verify-landmark-resolver.py` — 80 verification scenarios covering remote fetch state machine, cache hit/miss/TTL, generation-hash branches, Unicode decode, mutual-exclusion
- `docs/plans/2026-05-20-002-feat-reverb-landmark-resolver-remote-fetch-plan.md` — implementation plan with R-numbered requirements traceability
- `docs/brainstorms/2026-05-20-issue-76-reverb-landmark-resolver-remote-fetch-requirements.md` — brainstorm with key decision rationale
- GitHub issue #76 — feature request, runtime-verification notes that surfaced the hash and the decode bug
- GitHub issue #54 — parent v1 issue
