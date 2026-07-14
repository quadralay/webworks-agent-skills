# Federated Parcel Composition — Output Architecture

> **Applies to ePublisher 2026.1 and later** (new in 2026.1). Earlier Reverb
> 2.0 builds emit none of the `wwcomposition*` artifacts described here.

A federated Reverb 2.0 site is assembled from independently built outputs:
parcel builds contribute content groups, a shell build contributes the site
files, and an AutoMap composition (`.wacj`) splices them together in the
deployed mirror. This reference covers what federation looks like **in the
output** — what to expect when inspecting, linting, or browser-testing a
composed mirror. For the build/deploy/compose workflow, grammar, and CLI, see
the automap skill's `references/composition-jobs.md`.

## Composition artifacts in build output

Every Reverb 2.0 build (2026.1+) emits composition descriptors alongside its
normal output:

- **`<Group Dir>/wwcomposition.xml`** — per-parcel descriptor: decoded group
  name, GroupID, title, entry/index-chunk hrefs (URL-encoded,
  mirror-relative), generation hash, and a url_maps slice.
- **`<Group Dir>/wwcomposition-manifest.html`** — the parcel's `#parcels`
  TOC `<li>` fragment, **byte-identical** to the leaf in that build's own
  `index.html`. Composition splices these raw bytes, never re-serializes.
- **`wwcomposition-shell.xml`** (output root) — shell descriptor: entry file,
  cache-key surface, splice anchor, and compose parameters. Emitted by every
  build; consumed from whichever project deployed the shell slice.

These files are inert in a standalone site — their presence is normal and not
a defect.

## Shell outputs

Two ways a build produces a content-free shell (full chrome, empty `#parcels`
tree, no group-derived files):

- a project with **no source document groups** (the `generate-empty-project`
  capability lets the zero-document build proceed), or
- any project with the **Generate Groups** target setting disabled
  (`connect-groups-generate`) — chrome only: no parcel units, pages, group
  CSS, search index chunks, landmark chunks, per-group sitemaps, companion
  PDFs, or stub-group entries in `sitemap.xml` / `url_maps.xml`.

A shell loads error-free with zero parcels. Do not flag an empty `#parcels`
`<ul role="tree">` as breakage when the target is a shell.

## The composed mirror

After composition, the mirror is a normal Reverb 2.0 site plus:

- `index.html` `#parcels` contains leaves harvested from **different
  builds** — GroupIDs (`group:<id>` element ids, `data-group-title`
  attributes) come from each parcel's own build and share no sequence.
  Container `<li>` folders (from `.wacj` `<TOC>` nesting) carry a colon-join
  of their descendant GroupIDs.
- The site cache key (`GLOBAL_GENERATION_HASH` query strings) is a **composed**
  value that advances on every composition — chrome resources carry the
  composed hash while each parcel's own pages keep their build's hash. A
  mixed hash population across parcels is correct, not stale output.
- Root `sitemap.xml` and `url_maps.xml` are recomposed aggregates over the
  deployed parcels.

**Linting a composed mirror:** GroupID-consistency checks must scope to a
single parcel's slice; cross-parcel ID uniformity does not hold and is not a
defect. The `#parcels` manifest leaves are byte-copies of each parcel's own
manifest fragment, so leaf-vs-parcel-unit consistency still holds per group.

## Runtime tolerance

The 2026.1 loader tolerates missing parcels: parcel iframes are armed for
failure before their `src` is assigned (onerror, a post-load grace check, and
a watchdog), so a declared-but-absent parcel degrades to an omitted entry
instead of a spinner hang. Consequences for testing:

- A composed site with a missing parcel should still load with **zero console
  errors** and no `#connect_body` stuck in `preload`.
- Search results from an absent parcel are silently absent — there is no
  runtime error to detect; verify expected-parcel coverage explicitly.
- Cross-parcel navigation and search work only after composition — parcels
  deployed but not yet composed are invisible to the shell.

## Deploy slices (what belongs to whom)

- **Groups slice:** `<Group Dir>/`, `<Group>.html`, `<Group>_ix.html`,
  `<Group>_lx.js`, `<Group>_sx.js`, the group's composition descriptors, and
  per-parcel knowledge-base archives (`knowledge-parcel-<slug>-<hash>.zip`).
- **Shell slice:** entry page, `css/`, `scripts/`, `splash/`, search page,
  `not-found.html`, root `sitemap.xml` / `url_maps.xml`, `robots.txt`,
  `wwcomposition-shell.xml`.

Slice directory names mirror the format's naming exactly (space replacement
settings, path-invalid character folding), so unusual group names still
attribute correctly. Deployments never delete outside their own slice; stale
files from a pre-federation full deploy must be cleaned deliberately.
