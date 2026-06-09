# browser-test.js fixtures

Two static fixtures that reproduce the Reverb load mechanism `browser-test.js`
keys off — the `preload` class on `<body id="connect_body">` (issue #109).

| Fixture | Models | Expected result |
|---------|--------|-----------------|
| `reverb-good.html` | First content page renders; `connect.js` removes `preload`. | `success: true`, `preloadCleared: true`, exit `0` |
| `reverb-stuck.html` | Spinner hangs (first page never renders) **but** `Parcels.loaded_all` is set to `true`. The false-"passed" trap. | `success: false`, `preloadCleared: false`, `parcelsLoadedAll: true`, exit `1` |

`reverb-stuck.html` is the regression guard: the old heuristic
(`Parcels.loaded_all === true || readyState === 'complete'`) reports this build
as passed; the `preload` signal correctly reports failure.

## Run

```bash
CHROME=$(bash ../../../scripts/detect-chrome.sh | tail -1)
DIR="file://$(pwd)"

# Should PASS (exit 0)
TIMEOUT=6000 node ../../../scripts/browser-test.js "$CHROME" "$DIR/reverb-good.html"

# Should FAIL (exit 1) despite parcelsLoadedAll: true
TIMEOUT=4000 node ../../../scripts/browser-test.js "$CHROME" "$DIR/reverb-stuck.html"

# No-bypass mode (real file:// double-click) — good fixture still passes
TIMEOUT=6000 node ../../../scripts/browser-test.js "$CHROME" "$DIR/reverb-good.html" --vanilla
```

A short `TIMEOUT` keeps the stuck case from waiting the full default 30s before
it fails.
