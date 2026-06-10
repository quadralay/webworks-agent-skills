# lint-output.py fixtures

A single committed fixture tree, `good/`, that is a structurally valid minimal
Reverb 2.0 output — `lint-output.py` must report it clean (exit 0).

`good/` is the baseline for the whole suite. `tests/verify-lint-output.py` copies
it to a tempdir and mutates **one** file per scenario to inject a single defect,
then asserts the linter's exit code and findings. Keeping one good tree (rather
than a broken tree per check) means each failure mode is expressed as a minimal
diff from a known-good build — exactly how the real breakages arise.

## What `good/` exercises

| Aspect | Why it is in the fixture |
|--------|--------------------------|
| Two parcels (`Alpha`, `Bravo`) with full deploy units | `parcel-deploy-unit` happy path: `<Name>.html`, `<Name>_ix.html`, `<Name>_lx.js`, `<Name>_sx.js`, `<Name>/` |
| `#parcels` manifest with `<li id="group:<GID>">` + `<a id="<ctx>:<GID>" href>` | `manifest-parcel-groupid` anchor/`<li>` parsing |
| Parcel body `id:<GID>` + `toc:`/`data:`/`page:` divs | parcel-side GroupID extraction |
| Overloaded `breadcrumbs:<GID>` **and** `breadcrumbs:<pageId>` ids | regression guard: page-keyed `breadcrumbs:` ids must **not** be read as GroupIDs (the false positive that the `id`/`toc`/`data`/`page`-only rule fixes) |
| Self-closed **void** elements (`<meta/>`, `<link/>`) | `self-closed-element` must not flag void elements |
| A remote `https://cdn.jsdelivr.net/...` `<script src>` | `reference-integrity` must skip remote refs |
| Local `scripts/*.js` + `css/base.css` with `?v=` cache-busters | `reference-integrity` happy path (query stripped before the on-disk check) |

## Run

```bash
python ../../verify-lint-output.py
```

The verifier injects each defect (self-closed `<script/>`, whole-parcel GroupID
mismatch, `<li>`/anchor GroupID desync, missing deploy-unit file, missing content
directory, missing local asset, missing `index.html`) into a throwaway copy — the
committed `good/` tree is never modified.
