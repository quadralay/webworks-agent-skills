---
date: 2026-05-20
topic: reverb-landmark-resolver-remote-fetch
issue: 76
parent-issue: 54
---

# Reverb Landmark Resolver v2 — Remote `_lx.js` Fetching via `--remote-base-url`

## Summary

Extend `plugins/webworks-claude-skills/skills/reverb2/scripts/resolve-landmarks.py` so it can resolve a stable Reverb 2.0 URL against a **published help mirror over HTTP**, without the caller first downloading the help directory locally. The v1 resolver (issue #54) covers the local-mirror case; v2 closes the most common agent gap — pasting any published stable URL (e.g., the documentation hosted at the canonical Reverb mirror) and getting back the direct file URL.

The change is bounded: no modification to the parser, the index builder, or the merge semantics — those carry over unchanged. v2 adds chunk discovery over HTTP, a local fetch cache keyed by generation hash, sensible retry/proxy behavior, a small CLI surface extension, and one latent-bug fix in the existing fragment handling so percent-encoded Unicode source IDs round-trip the same way the browser runtime resolves them.

---

## Problem Frame

A Reverb 2.0 stable URL is a fragment-based link the browser runtime resolves client-side. Today, an AI consumer that wants the direct file URL must either (a) run the JavaScript runtime, or (b) download the help mirror first and run the v1 resolver against the local copy. Option (a) is out of reach for JS-less fetch tools; option (b) is friction every time an agent encounters a new published mirror.

The runtime verification captured on the parent issue confirms two behaviors that shape the v2 design:

1. The runtime decodes the URL fragment with `decodeURIComponent` before looking it up in the merged index. A stable URL like `<base>/#/%E6%A6%82%E8%A6%81` carries a percent-encoded Unicode source ID (`概要`) and resolves against the raw Unicode key in the index. v1's `rewrite` path does not perform that decode — a latent bug that bites the moment a project uses the `landmark-id-format: source-id` opt-in with non-ASCII source IDs.
2. Each Reverb build emits a `GLOBAL_GENERATION_HASH` into the landing page, and the browser runtime uses it to namespace its `localStorage` cache. The hash is a precise, build-coupled invalidation signal — strictly better than a wall-clock TTL because it survives long stable stretches and changes the moment the mirror rebuilds.

v2 is what closes the JS-less gap for remote mirrors. The same skill that produced v1 (its workflow doc, its `_lx.js` parser, its fixtures, its 28-scenario verification script) is the right home: v2 is one new code path that feeds the existing index builder.

---

## Requirements

**CLI surface**

- R1. Add `--remote-base-url <url>` to `resolve`, `rewrite`, and `dump`. Mutually exclusive with `--from`. When set, the resolver fetches chunks over HTTP from that base URL instead of reading local files.
- R2. `rewrite <stable-url>` auto-infers the remote base when (a) the input URL has an `http://` or `https://` scheme, (b) `--from` was not supplied, and (c) `--remote-base-url` was not supplied. The inferred base is the part of the input URL before `#/`. An explicit `--remote-base-url` overrides the inference.
- R3. Add `--no-cache` to force a fresh fetch on the next invocation (skips both the landing-page poll cache and the chunk cache).
- R4. Add `--cache-ttl <seconds>` (default `86400` — 24 hours) to control how often the resolver re-polls the landing page to check for a generation-hash change. Within the window, cached chunks are trusted without a network round-trip.
- R5. Existing v1 flags (`--from`, `--json`, `--base-url`, `--table`) keep their current behavior unchanged. A caller that supplies `--from` continues to operate fully offline.

**Chunk discovery over HTTP**

- R6. Discover chunks by fetching the landing page at `<remote-base-url>` and extracting `<script src="…_lx.js">` references. Resolve each `src` relative to the base URL. The set of discovered chunk URLs is what gets fetched (and cached).
- R7. If a `_lx-manifest.json` exists at `<remote-base-url>` (cheap HEAD or GET probe), prefer it over the HTML scrape. This keeps the v2 code resilient against future Reverb-side template changes without requiring Reverb to ship a manifest today.
- R8. If both manifest probe and HTML scrape produce zero chunks, emit a clear error naming the base URL and what was tried.

**Cache invalidation (generation-hash primary, TTL fallback)**

- R9. On every remote-mode invocation, the resolver checks whether it has a fresh cached generation hash for the base URL. "Fresh" means the most recent landing-page poll is within `--cache-ttl`. If fresh and a chunk cache exists, the resolver uses cached chunks with no network access.
- R10. If the cache is stale (TTL expired) or absent, the resolver re-fetches the landing page, extracts the `GLOBAL_GENERATION_HASH`, and compares:
  - **Hash unchanged**: reset the TTL window, reuse cached chunks.
  - **Hash changed or no prior cache**: re-fetch every discovered chunk, replace the cached set atomically, record the new hash.
- R11. If the landing page can be fetched but no `GLOBAL_GENERATION_HASH` can be parsed from it, the resolver falls back to TTL-only behavior (a wall-clock cache window) and logs a one-line warning to stderr. This keeps the tool usable against any mirror that happens to ship without the hash, while making the degradation visible.
- R12. `--no-cache` skips both the freshness check and the hash comparison; every chunk is fetched fresh in that invocation. The cache is then repopulated as a side effect (so the next invocation is fast again).

**Local cache layout**

- R13. Cache root resolves per platform: `%LOCALAPPDATA%\webworks\reverb-landmarks\` on Windows, `$XDG_CACHE_HOME/webworks/reverb-landmarks/` (or `~/.cache/webworks/reverb-landmarks/`) on Linux, `~/Library/Caches/webworks/reverb-landmarks/` on macOS. Honor an explicit `--cache-dir <path>` override.
- R14. Within the cache root, each base URL is keyed by host + path (e.g., `<host>/<percent-encoded-help-path>/`). Chunk files are stored verbatim by their basename. A small `_manifest.json` per base URL records the cached generation hash, the last-poll timestamp, and the discovered chunk list.

**URL fragment decoding (latent-bug fix)**

- R15. Apply `urllib.parse.unquote` to the fragment ID extracted from any input URL (`rewrite` mode, local OR remote). This mirrors the browser runtime's `decodeURIComponent` step and is required for the `landmark-id-format: source-id` opt-in with non-ASCII source IDs.
- R16. Malformed percent sequences in the input URL produce a clear error message naming the input — not a silent fallback that passes garbage to the index lookup. The exit code matches v1's "resolution failure" code (`1`).
- R17. R15 applies to local-mode `rewrite` as well, since the decoded-ID property holds regardless of where the chunks come from. v1 callers that happen to pass URL-safe ASCII IDs see no behavior change.

**HTTP behavior**

- R18. Fetch via Python stdlib (`urllib.request`), so the resolver continues to have zero non-stdlib dependencies. `HTTP_PROXY`, `HTTPS_PROXY`, and `NO_PROXY` are honored without custom configuration via `urllib.request.getproxies()`.
- R19. Retry on transient failures (connection reset, read timeout, 5xx response) with exponential backoff: 3 attempts, base delay 1s, doubling. 4xx responses are not retried — they're a clear-error case (R20).
- R20. Any unrecoverable HTTP failure (4xx, exhausted retries, DNS failure, TLS error) produces an error message that names the failing URL and the failure mode. Exit code `2` (matches v1's "parse/IO failure" code). No silent fallback to wrong data.
- R21. A small fixed read timeout (default 10 seconds, configurable via `--http-timeout <seconds>`) bounds the worst-case hang.

**Output shape parity**

- R22. `resolve` and `dump` produce the same JSON/text shapes as v1. The only difference in `rewrite` output is that when `--remote-base-url` (explicit or inferred) was used, the rendered prefix is the absolute remote URL rather than whatever the input URL or `--base-url` carried.
- R23. The resolved direct URL is URL-quoted in the file-path portion (e.g., spaces become `%20`) so the output is paste-ready for HTTP fetch tools. The fragment portion (`#anchor`) is left as-is, matching how the runtime composes anchor links.

**Documentation and verification**

- R24. Update `plugins/webworks-claude-skills/skills/reverb2/workflows/landmark-resolution.md` to cover the remote case — at minimum a new "Step 1b: remote mirror" section, an example of the auto-infer flow, and a short cache-behavior callout (where the cache lives, how to clear it).
- R25. Add at least one end-to-end manual smoke test against a real published Reverb mirror, captured as a small worked-example block in the workflow doc (input URL → expected resolved URL). Whether the test is automated is a planning decision; the worked example is a documentation deliverable.
- R26. Update the existing 28-scenario verification script (`tests/verify-landmark-resolver.py`) — or add a sibling — to cover at minimum: percent-encoded Unicode ID decode, malformed-percent-sequence error path, mutual exclusion of `--from` and `--remote-base-url`, and the cache hit/miss state machine under a stubbed fetcher. Real HTTP calls in the verification script are out of scope (R30).

---

## Acceptance Examples

- AE1. **Covers R1, R2, R5.** Given the v2 resolver, when a user runs `resolve-landmarks.py rewrite "https://<published-mirror>/help/#/e5d3d31c42d8d1d4"` with neither `--from` nor `--remote-base-url`, then the resolver auto-infers the remote base from the URL, fetches the chunks once, and prints a direct URL of the form `https://<published-mirror>/help/<resolved-path>`. Running the same command with explicit `--from <local-dir>` instead behaves exactly as v1 did.
- AE2. **Covers R6, R7, R8.** Given a base URL that publishes a `_lx-manifest.json`, when the resolver runs against it, then the manifest drives discovery (visible as a single GET to `_lx-manifest.json` rather than an HTML parse) and the chunk list matches what the HTML scrape would have produced. Given a base URL with neither a manifest nor any `_lx.js` script tags, the resolver exits with a clear error naming the base URL and the discovery methods tried.
- AE3. **Covers R9, R10, R12.** Given an already-cached base URL whose generation hash is unchanged, when the user runs `resolve` a second time within the TTL, then the resolver makes zero HTTP requests and returns the same path as the first call. When the user runs the same command with `--no-cache`, the resolver re-fetches the landing page and every chunk. When the mirror's `GLOBAL_GENERATION_HASH` has changed, the next invocation after TTL expiry re-fetches all chunks atomically.
- AE4. **Covers R11.** Given a published mirror that ships without `GLOBAL_GENERATION_HASH` in its landing page, when the resolver runs against it, then it falls back to TTL-only caching, prints a one-line warning to stderr, and otherwise resolves correctly.
- AE5. **Covers R15, R16, R17.** Given a stable URL `<base>/#/%E6%A6%82%E8%A6%81` whose decoded ID is `概要`, when `rewrite` runs against either a local or remote source whose index contains the raw key `概要`, then the resolver returns the same path it would for `<base>/#/概要`. Given a malformed percent sequence in the input URL (e.g., `<base>/#/%E6%A6`), the resolver exits with code `1` and an error message naming the input URL.
- AE6. **Covers R18, R19, R20.** Given `HTTPS_PROXY` is set in the environment, when the resolver runs in remote mode, then requests go through the proxy without any custom configuration. Given a transient 503 response, the resolver retries with exponential backoff and succeeds on a later attempt. Given a 404 on a discovered chunk URL, the resolver exits with code `2` and an error naming the failing URL.
- AE7. **Covers R22, R23.** Given a resolved path that contains spaces (e.g., `Advanced Customizations/_xslt-extensions.04.1.html`), when `rewrite` runs in remote mode, then the output URL has the path portion percent-encoded (`Advanced%20Customizations/_xslt-extensions.04.1.html`) and the fragment portion (if any) left as-is.
- AE8. **Covers R24, R25.** Given a reader landing on `workflows/landmark-resolution.md` for the first time, when they reach Step 1, then they can choose between a local mirror and a remote mirror without leaving the doc, and they can run the worked example against the documented published mirror and get the expected direct URL.

---

## Success Criteria

- An AI agent can paste any Reverb 2.0 stable URL from a published mirror and get the direct file URL back with a single `rewrite` invocation, with no local download step and no manual flags beyond the URL itself.
- A second invocation against the same base URL within a day issues no network requests.
- When a mirror rebuilds and its generation hash changes, the next invocation transparently re-fetches every chunk — no manual cache clear, no `--no-cache` required.
- A percent-encoded Unicode source ID resolves to the same file path as its decoded form, against both local and remote mirrors. v1's behavior on URL-safe ASCII IDs is unchanged.
- An HTTP failure produces an error message a human can act on (URL + failure mode), never a silent fallback to a wrong path.
- The resolver continues to require nothing beyond a Python 3 install — no new pip dependencies.

---

## Scope Boundaries

- **No changes to chunk parsing, the index builder, or the merge semantics.** The v1 `parse_chunk` / `build_index` / `resolve_id` functions carry over unchanged. v2 is a new fetch-and-cache front end that hands the existing builder an in-memory list of chunk texts (or local paths) instead of a directory glob.
- **No authenticated remote fetches.** v2 assumes the help mirror is public. If a customer-portal scenario emerges (per-customer published docs behind auth), it gets a separate brainstorm because it pulls in credential storage, header injection, and a different cache-key story.
- **No server-side changes to Reverb.** No new endpoints, no new manifest emission. The manifest probe in R7 is a *forward-compatible* preference: if Reverb later ships a manifest, v2 picks it up automatically without a code change. Until then the HTML scrape carries the discovery.
- **No reverse lookup over HTTP.** Path-to-ID lookup against a remote mirror is a separate concern (the parent plan tracks it as a sibling follow-up). v2 is forward direction only: stable URL or ID → direct URL.
- **No real-HTTP calls in the verification script.** Network tests are flaky in CI and tie verification to the availability of a specific public mirror. The state machine and parser are covered with stubbed fetchers and fixture HTML/JSON. Real-HTTP smoke testing lives in the workflow doc's worked example (R25).
- **No new pip dependencies.** `urllib` from stdlib covers HTTP, proxy env, and TLS. Adding `requests` (or `httpx`, etc.) would be a real carrying cost for a small benefit.
- **No simultaneous cache invalidation for the `--from` (local) mode.** Local mode reads files directly on each invocation; there is no cache. Adding one would mix two unrelated lifecycles.
- **No automatic cache eviction or size cap.** Each base URL's cache is a few hundred KB at most (chunks are small); evicting old base URLs is a manual `rm -rf` against the cache root. Adding an eviction strategy is a YAGNI move until someone reports cache bloat.
- **No version bump in this brainstorm artifact.** Version bump happens at PR time per `CLAUDE.md`.

---

## Key Decisions

- **HTML scrape primary, manifest preference if present (R6, R7).** We have to fetch the landing page anyway to read `GLOBAL_GENERATION_HASH` for cache invalidation. Once that page is in hand, parsing its `<script src="…_lx.js">` tags is one regex pass over already-loaded text. That collapses discovery and the cache-key fetch into a single round-trip and avoids requiring any Reverb-side change. The manifest probe (R7) is a low-cost insurance policy: a single HEAD or GET against `<base>/_lx-manifest.json`; if Reverb ever ships one, we use it automatically; if not, we keep scraping.
- **Generation hash as the primary invalidation signal, TTL as a poll cadence (R9, R10, R11).** The runtime verification on the parent issue showed `GLOBAL_GENERATION_HASH` is constant per build and used by the in-browser runtime for exactly this purpose. It's strictly better than a wall-clock TTL because it survives long stable stretches (months between releases) and changes the moment the mirror rebuilds. TTL still earns a role: it bounds how often we re-poll the landing page to check the hash. Without TTL, every remote invocation does one HTTP request; with TTL=24h, sustained agent usage against a stable mirror is fully offline.
- **Replicate `decodeURIComponent` even though v1 callers don't currently hit it (R15, R17).** The 2026.1 `landmark-id-format: source-id` opt-in is the trigger. Once a project uses it, source IDs are whatever Unicode the source emitted, and stable URLs carry the percent-encoded form. Decoding is required for correctness in both local and remote mode; doing it only in the remote path would create a confusing asymmetry.
- **Auto-infer remote base from input URL (R2).** Eliminates the most common ergonomic friction: pasting a stable URL and immediately having to repeat the same prefix as a flag. The auto-infer rule is unambiguous (HTTP scheme + no `--from` + no explicit `--remote-base-url`) and `--from` retains priority for callers that want to mix a published URL with a local source.
- **Stdlib `urllib` over `requests` (R18).** The v1 resolver has zero external dependencies. Adding `requests` would force every consumer to manage a venv or system install. `urllib.request.getproxies()` honors `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY` cleanly; retry/backoff with three attempts is ~15 lines of code; the only `requests` features we'd actually use are the proxy ergonomics and the API ergonomics, neither of which justify the dependency cost.
- **Cache root keyed by host + path, with `_manifest.json` per base URL (R14).** Multiple base URLs coexist cleanly (e.g., `latest`, `2026.1`, an internal staging mirror) without sharing chunk files. The per-base manifest keeps the generation hash, last-poll timestamp, and discovered chunk list co-located so a stale cache is one file delete from being clean.
- **Same script, not a sibling script (R5).** Splitting into `resolve-landmarks-remote.py` would force users to know which to invoke, would duplicate `parse_chunk` / `build_index`, and would force the workflow doc to fork into two parallel sequences. A single script with a `--remote-base-url` flag is the same shape as v1 with one extra branch.

---

## Dependencies / Assumptions

- v1 (issue #54) is merged and the resolver, fixtures, and workflow doc are present at the paths in `plugins/webworks-claude-skills/skills/reverb2/`. Verified by reading `scripts/resolve-landmarks.py` and `workflows/landmark-resolution.md` at brainstorm time.
- The published Reverb mirrors targeted by the smoke test use the documented `<base>/#/<id>` URL pattern with a trailing `/` on the base. The runtime verification notes assume this; the brainstorm assumes it remains true for the published mirrors in use. The smoke test in R25 confirms the pattern against at least one real mirror.
- `GLOBAL_GENERATION_HASH` is present in the landing page of every current Reverb 2.0 build the team produces. The fallback path (R11) handles the case where it's missing or unparseable, so the assumption is not load-bearing — it only affects whether the optimal cache path is reached.
- Reverb 2.0 landing pages render their `<script src="…_lx.js">` tags as static HTML, not as JS-injected DOM nodes. If a future template moves to injected chunk loading, the HTML scrape would silently fail (zero discovered chunks → R8's clear error). At that point the manifest path (R7) becomes the load-bearing source of truth and Reverb-side coordination is needed.
- The cache directory is a host-keyed scratch area, not a synchronized resource. Multiple machines using the same agent against the same mirror each maintain their own cache; this is fine for a per-invocation tool.
- Python 3.9+ on the agent host (matches the v1 baseline; no new minimum).

---

## Outstanding Questions

### Resolvable at planning time

- [Affects R6, R7, R11] [Verification] Confirm via the smoke-test mirror that (a) `<script src="…_lx.js">` tags are present in the landing-page HTML and (b) a `GLOBAL_GENERATION_HASH` constant is parseable from it. Capture the regex shape used in the verification PR. If both are confirmed, R7's manifest path is documentation-only forward compatibility (no manifest currently exists) and R11's fallback is a code path that won't fire against current mirrors but stays for resilience.
- [Affects R13] [Technical] Resolve the platform-detection rule for the cache root in one place (`platformdirs`-style logic, hand-rolled). `platformdirs` would be a new dependency, contradicting R18's stdlib stance. Planning either picks hand-rolled (matches the zero-dep policy) or carves out an exception with explicit justification.
- [Affects R14] [Technical] Decide whether the per-base cache directory name uses raw host+path (potentially unfriendly characters), a percent-encoded form, or a hash of host+path. Trade-off is between human inspectability and filesystem portability. Planning picks the option whose error case ("user reports the wrong directory was used") is easiest to diagnose.
- [Affects R26] [Technical] Decide whether the verification script's stubbed fetcher lives as a small in-script class or as a fixture directory with served files via `http.server`. The in-script stub is simpler; the served-files approach exercises real `urllib.request` code paths. Planning picks based on how the cache state machine is structured (stub is sufficient if cache logic is decoupled from HTTP, otherwise served files).

### Genuinely uncertain — record as assumption

- [Affects R7] [Open] Whether Reverb ever ships a `_lx-manifest.json`. The brainstorm assumes it might in the future and probes for it; if it never does, the probe is harmless one extra HEAD/GET on first fetch per base URL (cached afterward). Recorded so a future contributor knows the probe is forward-compatible, not load-bearing.
- [Affects R10] [Open] Whether `GLOBAL_GENERATION_HASH` is stable across rebuilds-of-the-same-source. If a no-op rebuild changes the hash (e.g., it includes a build timestamp), every rebuild invalidates the cache even when nothing meaningful changed. This is no worse than the current TTL-only proposal — and still strictly better in the common case — but planning should note the behavior so the cache hit rate isn't oversold to users. Recorded as an explicit assumption.
- [Affects R19] [Open] Whether the retry budget (3 attempts, base delay 1s, doubling) is appropriate for typical mirrors. The numbers are picked to keep total worst-case latency under 10s per chunk. Adjustable in a follow-up if real usage shows them too aggressive or too forgiving.

---

## Out of Scope (Reiterated)

For visibility — these are explicitly deferred and should not appear in the implementation plan:

- Authenticated remote fetches (customer portals behind auth).
- Server-side Reverb changes (new endpoints, manifest emission, hash-as-header).
- Reverse lookup over HTTP (path → ID against a remote mirror).
- Real-HTTP calls in the verification script.
- New pip dependencies.
- Cache eviction strategies / size caps.
- Caching for local-mode (`--from`) invocations.
- Plugin version bump (handled at PR time per `CLAUDE.md`).

---

## Handoff

Next step: `/workflows:plan` against this requirements document to produce an implementation plan. The plan should cover the CLI surface extension, the cache state machine, the discovery probe order, the URL-decode fix, the workflow doc update, and the verification script extension — referencing the R-numbers above for traceability.
