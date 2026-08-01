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
  mirror-relative), generation hash, a url_maps slice, and an optional
  `MergeSettings/Container` chain (the parcel's own placement declaration —
  see "Placement in the composed TOC" below).
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

## Placement in the composed TOC

Where a group's `<li>` lands in the composed `#parcels` tree is decided by two
declarations: the composition's own Merge Settings, and the Merge Settings the
parcel carries in its own deployed descriptor. For each group it composes, the
engine applies the **first** rule that fits:

| Rung | Rule | Source |
|------|------|--------|
| 1 | **The composition places the group.** It appears exactly where the composition's Merge Settings put it — top level, or inside the `<TOC>` containers wrapping it. | `.wacj` `<MergeSettings>` |
| 2 | **The group places itself.** A group the composition does not place, whose descriptor declares a container chain, nests inside those containers at the top level. | `wwcomposition.xml` `MergeSettings/Container` |
| 3 | **Nothing places the group.** It is appended in discovery order — descriptor group title, then decoded group name. Stable run to run. | discovery order |

Rule 1 beats rule 2, and the override is **logged, not silent**: when a
composition places a group that also declared its own container, the log
records an Info line naming both (`Group 'X': merge settings placement
overrides its declared container 'Guides/Install'.`). Groups placed by their
own declaration are reported per container (`'Parcel A', 'Parcel C': placed by
their declared merge settings into container 'Guides'.`). An unexpected
position in a composed site therefore always traces back to a log line.

**Where the parcel's declaration comes from.** The descriptor records the
target's **explicit** Merge Settings container chain, outermost first:

```xml
<wwcomposition:Descriptor …>
  <wwcomposition:MergeSettings>
    <wwcomposition:Container name="Guides"/>
    <wwcomposition:Container name="Install"/>
  </wwcomposition:MergeSettings>
  …
</wwcomposition:Descriptor>
```

Authoring is equivalent in either project form: a `.wep`/`.wrp` target's
`FormatConfiguration/MergeSettings` (a `<TOC>` wrapping the group's
`<MergeGroup>`), or the `<MergeSettings>` block on a `.waj` `<Target>`, which
AutoMap injects into the staged project at build time. A project with **no**
explicit Merge Settings declares no placement — the synthesized fallback the
descriptor transform uses is flat by construction, so its descriptor carries
no `MergeSettings` element at all. The schema is additive: flat groups and
descriptors written before the element existed compose unchanged.

**Container merging.** Containers are created on demand and merged **by name**
at each level, so parcels declaring the same container share one folder. A
parcel-declared name also merges with a same-level `.wacj` container matched by
its `name` **or** its displayed `title`. Sibling order stays deterministic:
parcels arrive in discovery order and append, members of a shared container
keep that order, and a container sits where its first member placed it. In
hybrid mode everything discovered appends after the declared spec.

**Where rule 2 applies.** Only in the modes that admit parcels the composition
does not name: **Automatic** (discovery — compose every deployed group), and a
**Custom** composition with *Also include newly published parcels* selected
(hybrid). In a strictly Custom composition every composed group is named, so
rule 1 covers all of them.

## Containers are not groups

A **container** is a folder in the composed TOC. A **group** is a set of
documents with deployed output. Containers hold groups; only groups carry
content. In a `.wacj`, `<TOC name="…">` declares a container and
`<Group name="…"/>` places a group.

The confusion is easy to reach: once one team's parcel declares `Guides`, that
name is visible in the composed site, and it is tempting to list it as a
`<Group>`. It has no deployed output, so it cannot be composed as one — and
this is **diagnosed, not guessed**. The composition omits the entry and warns
with the actual situation and the actual fix, naming the deployed groups that
declared the container:

```
'Guides' is a placement container declared by deployed groups ('Parcel A', 'Parcel C'),
not a group; omitted. To place those groups, add them directly where you want them.
A group placed by this composition overrides its declared container.
```

(Inside an enclosing container the advice names it: *"To place those groups
inside 'Manuals', add them there directly."*) A name that matches nothing at
all still gets the generic line — `Group 'X': no deployed output was found at
destination 'Prod'; omitted. Deploy its output to this destination, then run
this composition again.` — so the two situations stay distinguishable in the
log.

Malformed and conflicting placement is reported with a fallback to the **top
level**, never a failure:

| Situation | Log line (Warn) |
|-----------|-----------------|
| A declared container with an empty name | `Group 'X' declares a placement container with an empty name; placed at the top level instead.` |
| A declared container colliding with a group of that name at the same level | `Group 'X' declares placement container 'Guides', which collides with a group of that name; placed at the top level instead.` |
| A declared chain landing beside a container carrying the parcel's own name | `Group 'X' declares a placement that collides with a container of the same name; placed at the top level instead.` |

A spec container that ends up holding nothing is dropped with
`Container 'Guides' contains no groups to compose; omitted.`

**Placement problems never fail a compose.** Every case above degrades to flat
(top-level) placement — exactly as if the parcel had declared nothing — and the
site still composes and loads. Treat a placement warning as a TOC-shape
question, never as a broken build. (`Group 'X'` in these lines becomes
`Member 'M'` — or `Member 'M' group 'X'` when the two names differ — when the
host job maps the group to a composition member.)

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

## Not covered here

Two composition topics live outside this reference on purpose:

- **Which output target each member composes through** — the determinant
  selection rule (the member's own `Job/@target`, else the composition-wide
  `Jobs/@target`, else auto-detection among the targets that member itself
  declares; never a silent first match, and every member must select the same
  format). That is job-artifact behavior, not output structure: see the
  automap skill's `references/composition-jobs.md` § "Output target selection
  (determinant)". The end-user framing is the *Output target* entry in the
  docs topic `output-formats/webworks-reverb-20/reverb-federated-parcels.md`.
- **The `.wacj` grammar** — members, roles, destinations, inline deploy
  settings, and CLI dispatch: also the automap skill's
  `references/composition-jobs.md`. This file never duplicates that grammar;
  it describes only what composition leaves behind in the output.
