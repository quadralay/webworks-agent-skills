# Composition Jobs (.wacj) — Federated Parcel Composition

> **Applies to ePublisher 2026.1 and later** (new in 2026.1). Earlier versions
> do not recognize `.wacj` files, the `deployScope` attribute, inline
> `<DeploySettings>`, or the `--deployscope` / `--deploysettings` /
> `--destination` / `--dryrun` options. Check the installed version before
> recommending any of this — see the epublisher skill's
> `references/version-compatibility.md`.

Federated parcel composition assembles independently built and deployed
WebWorks Reverb 2.0 outputs (parcels) into one site under a shared shell.
The lifecycle has three independent steps:

1. **Build** — each parcel project builds a complete standalone Reverb site.
2. **Deploy** — each project deploys only its role-appropriate slice into one
   shared destination (the mirror): parcels deploy their content groups,
   the shell deploys the site files. Every parcel deployment includes a
   composition descriptor (`wwcomposition.xml` + a byte-faithful manifest
   fragment) recording its identity.
3. **Compose** — an AutoMap Composition Job (`.wacj`) reads the deployed
   descriptors, splices the combined site TOC into the deployed shell,
   refreshes `sitemap.xml` / `url_maps.xml`, and advances the browser cache
   key — in seconds, without rebuilding any content. On S3 it uploads the
   recomposed files and issues a CloudFront invalidation.

Reverb 2.0 only: the format declares the composition capabilities in
`format.wwfmt`; other formats always deploy everything.

> **Register note:** this reference speaks the developer register ("mirror",
> "descriptor", "harvest") for precision about mechanism. Since 2026.1 the
> product's own logs and dialogs — and any user-facing text you author — use
> the user register instead: *shared destination*, *deployed record*, "read
> the deployed output". See the epublisher skill's `product-foundations.md`
> § Naming and Terminology for the full map.

## Grammar

A `.wacj` is a distinct artifact that *references* jobs — like `.sln` vs
`.csproj`. The same `WebWorks.Automap.exe` runs both (dispatch on the root
element):

```xml
<?xml version="1.0" encoding="utf-8"?>
<CompositionJob name="product-docs" version="1.0">
  <Jobs target="Web Help">
    <Job path="shell\shell.waj"       role="shell"/>
    <Job path="install\install.waj"   role="parcel" build="true"/>
    <Job path="admin\admin.wep"       role="parcel" target="Online Docs"/>
  </Jobs>

  <MergeSettings>
    <TOC name="Guides">
      <Group name="Installation Guide"/>
    </TOC>
    <Group name="Administration Guide"/>
  </MergeSettings>

  <Destination name="ProductionMirror"/>
</CompositionJob>
```

- **`<Jobs target>`** — the composition-wide **output target**, pushed down to
  every member. Optional; omit it to auto-detect per member. See
  [Output target selection](#output-target-selection-determinant).
- **`<Job path role build target>`** — members are `.waj` jobs or `.wep`/`.wrp`
  projects. `role` is `shell`, `parcel`, or `infer` (the default when the
  attribute is absent or unrecognized). `target` is a per-member override of
  `Jobs/@target`. `build` defaults to **false** and is the seam between the two
  composition archetypes — see [Federated vs. derivative
  members](#federated-vs-derivative-members).
- **`<MergeSettings>`** — the composed site TOC. `<Group name>` references a
  deployed parcel **by group name**; `<TOC name>` nests groups under
  containers. Three modes, named as the Administrator's Merge Settings area
  names them:

  | Mode | Grammar | Administrator label |
  |------|---------|---------------------|
  | **Automatic** | omit `<MergeSettings>` entirely | **Automatic (compose every parcel found at the destination)** |
  | **Custom** | declare `<Group>` / `<TOC>` placements | **Custom** |
  | Custom + include-new | `<MergeSettings discover="true">` plus placements | Custom, with **Also include newly published parcels not listed above** checked |

  A declared group with no deployed output is warned once and omitted. The root
  `title` attribute is accepted for `.waj` grammar parity but unused (warned):
  the composed site's title is shell chrome.
- **`<Destination name>`** — the shared destination. (2026.1 pre-release
  builds spelled this `<DeployTarget>`; that spelling is still read for one
  release and rewritten as `<Destination>` on save.) Resolution order:
  the composition job's own inline `<DeploySettings>` → a `--deploysettings`
  overlay file → the machine's deploy preferences (`deploy.prefs`), with a
  drift warning when an inline definition shadows a differing preference.

## Federated vs. derivative members

The `build` flag on each member decides **who publishes that member**, and it
is the only setting that changes what a composition fundamentally does. One
`.wacj` may mix both kinds, member by member.

| `build` | Archetype | Who builds and deploys the member | Where its output lands |
|---------|-----------|-----------------------------------|------------------------|
| absent / `"false"` | **Federated** | the member's own job, on its own cadence | wherever that job's target declares — which had better be this composition's destination |
| `"true"` | **Derivative** | the composition, in a separate process | **this composition's destination**, overriding the member job's own |

**Derivative (self-contained) mode.** A `build="true"` member is built before
the compose, in its own process, with these switches forwarded:

| Forwarded switch | Value | Why |
|------------------|-------|-----|
| `--target=` | the member's selected output target | build exactly the federation target, not the member's whole enabled set |
| `--destination=` | the composition's `<Destination name>` | the member deploys to the *composition's* destination, whatever its own job names |
| `--deployscope=` | derived from `role` (`shell` → `shell`, `parcel` → `groups`; `infer` → omitted) | a composition-driven federation cannot be mis-scoped |
| `--deploysettings=` | a temp overlay of the CLI overlay + the composition's inline definitions | the member process resolves the destination name without `deploy.prefs` seeding |
| `--dryrun` | present when the composition run is dry | the rehearsal reaches member builds too |

Together these make the run **self-contained**: nothing about the member job's
own destination or scope declarations can send its output somewhere the
compose will not read. A `role="infer"` member is the exception — no scope
override is forwarded, so the member project's own declared scope applies.

Log line: `Building member job: <path> (deploys to this composition's destination '<name>').`

**Federated mode has no such override**, so the composition cross-checks it up
front and warns (it does not fail) when an *unbuilt* member's job would deploy
the selected target somewhere else, or nowhere:

```text
Member 'admin': its job deploys output target 'Web Help' to destination 'TeamMirror',
not to this composition's destination 'ProductionMirror'. Output deployed by that job
will not appear at this composition's destination.

Member 'admin': its job declares no destination for output target 'Web Help', so its
output does not deploy anywhere this composition can read. Deploy that target to
destination 'ProductionMirror', or check Build for this member in the composition.
```

Built members are skipped by this check — they deploy to the composition's
destination regardless.

**Authoring defaults differ from editor defaults.** The grammar default is
`build="false"`: a hand-authored member is federated unless it opts in. The
AutoMap Administrator's composition editor adds new members with **Build
checked** — the derivative posture a learning user expects. Neither is wrong;
know which one produced the file you are reading.

## Output target selection (determinant)

Every member composes through one **output target**. Selection runs for every
member *before anything is built*, so a doomed composition fails in seconds
instead of after minutes of member builds.

Per-member precedence, highest first:

1. the member's own `<Job target="...">` attribute — *"member override"*
2. the composition-wide `<Jobs target="...">` — *"composition target"*
3. auto-detection — *"auto-detected"*

Each selection is logged: `Member '<name>': output target '<target>' (<format>, <source>).`

**Auto-detection is never a silent first-match.** The candidate universe is the
member's compose-capable targets — for a `.waj` member, the targets its **job
declares** (each resolved against the stationery by name), preferring the
active `build="True"` subset; for a `.wep`/`.wrp` member, the project's targets
with no active-subset step. Exactly one candidate selects. Two or more is an
error listing them by name:

```text
Member 'admin' has 2 active compose-capable targets: 'Web Help', 'Online Docs'.
Select one with the composition-wide target (<Jobs target="...">) or this member's
<Job target="..."/> attribute.
```

**Compose-capable means the format declares the composition contract** in
`format.wwfmt` — today, WebWorks Reverb 2.0 only. A selected target on any
other format fails:

```text
Member 'admin' target 'Print PDF' uses PDF - XSL-FO, which does not support composition.
The composition needs a WebWorks Reverb 2.0 (compose-capable) target.
```

and when the member has no compose-capable target at all:

```text
Member 'admin' has no compose-capable output target (target 'Print PDF' uses PDF - XSL-FO;
target 'Word' uses Microsoft Word). The composition needs a WebWorks Reverb 2.0
(compose-capable) target on every member.
```

**Names may vary; formats may not.** Two teams' differently named targets
compose fine as long as both are the same format. Heterogeneity is rejected:

```text
Composition members must all use the same output format; found: 'shell' -> WebWorks Reverb 2.0;
'admin' -> PDF - XSL-FO. Member target names may vary across teams, but every member must
produce the same compose-capable format.
```

**Stationery drift** in a member's declared target is the same hard error the
member's own build would raise, surfaced before any build and prefixed with the
member name: `Member 'admin': Target "Web Help" is not defined by the job's
stationery (<path>). Resave the stationery with this target, or remove or rename
the job target, then run again.` (See job-file-guide.md's [Job Target Missing
from the Stationery](./job-file-guide.md#job-target-missing-from-the-stationery).)

**Second line of defense at compose time.** Selection validates *targets*;
harvest validates what is actually *deployed*. A deployed parcel whose
descriptor records a different format name or version than the shell's is
**warned and skipped** — the skew case where a parcel was deployed earlier by
another team or another product version. Descriptors that predate format
identity being recorded are tolerated, not skipped.

```text
Member 'admin' group 'Administration Guide': the output deployed at the destination
was published by Web Help 2025.1, but this composition's shell uses Web Help 2026.1,
so it cannot be included. Rebuild and redeploy it with the current version, then run
this composition again.
```

The composed site loads with the remaining parcels.

## Identity and tolerance

**Group names are the durable identity.** Parcel GroupIDs regenerate across
rebuilds and re-stagings; composition harvests whatever GID each deployed
descriptor currently carries. Always reference parcels by name, never by a
captured GroupID.

**Tolerance:** a declared group with no deployed descriptor is warned and
omitted; the composed site loads cleanly with the parcels present. A missing
shell composition descriptor (`wwcomposition-shell.xml`) is a hard error —
rebuild and redeploy the shell.

## Running

```powershell
& $automapExe composition.wacj              # compose (and build any build="true" members)
& $automapExe composition.wacj --dryrun     # rehearse
```

- Exit code 0 on success; non-zero on error (undefined destination, missing
  shell descriptor, member target selection failure, member build failure).
- A job-style log is written beside the file: `<name>-log.txt` — same framing
  convention as a `.waj` log, so the two cannot drift.

**Which CLI options actually apply.** A `.wacj` composes output that member
jobs already built and deployed, so generation options have nothing to act on.
They are **parsed and ignored**, not rejected:

| Option | On a `.wacj` |
|--------|--------------|
| `--dryrun` | applies — forces the run dry and is forwarded to member builds |
| `--deploysettings` | applies — the overlay participates in `<Destination>` name resolution and is forwarded to member builds |
| `-t` / `--target` | ignored; each member's target comes from [output target selection](#output-target-selection-determinant) |
| `--deployscope` | ignored; each built member's scope is derived from its `role` and cannot be overridden from the CLI |
| `-c`, `-n`, `-d`, `-l`, `--skip-reports` | ignored — no content is generated |
| `-q` / `--quiet` | no effect: a composition log is not the generation engine's progress stream, and the switch is not forwarded to member builds |

The wrapper knows this: it runs a `.wacj` with native semantics automatically
(no injected flags, no target requirement).

**Expected log shape** (English install; markers are localized elsewhere):

```text
Composition job 'product-docs' started at 9:14:02 AM, 2026-08-01.
Member 'shell': output target 'Web Help' (WebWorks Reverb 2.0, auto-detected).
Destination 'ProductionMirror' resolved from the composition job's inline definitions.
Found deployed output for 3 group(s) at destination 'ProductionMirror'.
Composed 3 group(s) into index.html.
Composed cache key: <hash>
Composition complete: 3 group(s), 0 warning(s).
3 group(s) composed, 0 warning(s), 0 error(s) reported.
```

### Log semantics: relayed member lines are not the composition's

A composition builds each `build="true"` member in a **separate process** and
relays that process's console output — stdout and stderr — into its own log, so
a member's warnings and errors are visible where you are already reading. Those
relayed lines keep their `[WARN]` / `[ERROR]` markers, but they are written to
the composition log at Info severity: **they belong to the member's own log and
its own count, and the composition's summary does not include them.**

So a composition log can legitimately *show* more marked lines than its closing
tally counts. Both numbers are right — every ledger counts only its own entries,
and nothing is double-counted across ledgers. When a relayed warning needs
attention, open that member's own log (or its `generate.log`) to see it in
context.

The wrapper's post-build scan of `<name>-log.txt` counts marked lines, so for a
composition with built members its counts are the *visible* marks, relayed ones
included — deliberately looser than the composition's own tally.

## Deploy scope

Every target declares which slice a deployment publishes. In the project it
is the Target Settings **Deploy** field; in a `.waj` it is the optional
`deployScope` attribute on `<Target>`; on the CLI it is `--deployscope`.
CLI overrides job attribute overrides project declaration — **for a target
build**. A composition's own run ignores `--deployscope` entirely and derives
each built member's scope from its `role`, which is why a composition-driven
federation cannot be mis-scoped from the command line.

| Value | Publishes | Use for |
|-------|-----------|---------|
| `everything` | complete generated output (default, legacy behavior) | standalone sites |
| `groups` | content groups + their composition descriptors, no site files | every parcel |
| `shell` | site files + shell composition descriptor, no groups | the shell |

Scoped deployments (and scoped AutoMap Clean) are additive within their
slice: they never delete another project's files in the mirror. Clean is an
AutoMap capability — the Designer/Express Deploy command copies only.

Slice attribution is by group-name prefix and mirrors the format's directory
naming exactly, including space-replacement settings and path-invalid
character folding, so groups with names like `C# API [Draft]` slice
correctly. Per-parcel knowledge-base archives
(`knowledge-parcel-<slug>-<hash>.zip`) belong to the group slice; a folder
Groups-scope Clean also sweeps the build's own prior-generation archives
(never a sibling's).

## Inline destination definitions

Deploy preferences are per-user, per-machine state; a version-controlled job
that references a destination by name alone needs every machine seeded. Both
job kinds can carry the **definition** inline, using the exact deploy.prefs
entry schema — references stay by name:

```xml
<!-- .waj: a direct child of <Job> -->
<DeploySettings>
  <DeploySetting Name="ProductionMirror" Action="s3">
    <Configuration Value="s3://docs-bucket/product" Region="us-east-1"
                   Distribution="E2EXAMPLE" />
  </DeploySetting>
</DeploySettings>

<!-- .wacj: inside <Destination> -->
<Destination name="ProductionMirror">
  <DeploySettings>
    <DeploySetting Name="ProductionMirror" Action="s3">...</DeploySetting>
  </DeploySettings>
</Destination>
```

- Precedence per name: **job file's own inline > `--deploysettings` overlay
  file > deploy.prefs.** An inline definition **wins outright** over a
  same-named `deploy.prefs` entry — it does not merge with it.
- **Every resolution is logged**, so the winning source is never a guess:

  ```text
  Destination 'ProductionMirror' resolved from the composition job's inline definitions.
  Destination 'ProductionMirror' resolved from the --deploysettings file 'ci\destinations.xml'.
  ```

  Silence on this line means the name came from `deploy.prefs`.
- **Drift detector.** When the winning inline definition differs in content
  from a same-named lower-precedence one, the run warns and says which it used:

  ```text
  Inline destination definition 'ProductionMirror' (from the composition job) shadows a
  different definition of the same name in deploy.prefs; using the inline definition.
  ```

  Identical definitions are silent — the warning fires on *difference*, not on
  mere duplication.
- **Unresolvable is an error**, before any member build:
  `Destination 'ProductionMirror' is not defined in deploy.prefs, the --deploysettings overlay, or inline in the composition job.`
- `--deploysettings=<file>` takes the same `<DeploySetting>` entries from an
  XML file — the CI seeding mechanism. A composition forwards its merged
  inline definitions to member builds automatically (they are separate
  processes), so name-only member jobs run on unseeded machines.
- **Security guardrail:** only secret-free transports may be inline — Folder
  (`Action="file"`) and Amazon S3 (`Action="s3"`). WebDAV (`Action="http"`)
  **embeds encrypted credentials and is rejected at parse time**, as are custom
  actions. The rejection happens at job load, *before any build starts*, so a
  job that tries it never partially runs. Those transports stay in
  `deploy.prefs`, where the credentials are machine-local state rather than
  version-controlled content.

## Amazon S3 + CloudFront destinations

An S3 destination stores bucket URI (`s3://bucket` or `s3://bucket/prefix`),
region, optional named AWS credential profile, and optional CloudFront
distribution ID. **No access keys are ever stored** — credentials resolve
through the standard AWS chain (profile, environment, instance role) on the
deploying machine.

- Uploads apply web-appropriate caching: versioned assets immutable,
  pages/maps (html/xml) always revalidated (no-cache).
- A deploy invalidates its own no-cache uploads through CloudFront when a
  distribution is configured (root files exactly; directory contents collapse
  to one `<dir>/*` wildcard per top-level directory). Compose issues one
  invalidation for the recomposed chrome.
- Composition against S3 is two-phase: descriptors + chrome sync down to a
  local `.compose-staging\<name>\` mirror, compose runs locally, changed
  files upload, one invalidation is issued.
- Per-parcel knowledge-base archives are excluded from S3 deploys by design
  (the Platform ingests them by upload from build output, never from S3).
- Nonexistent-on-disk slice entries (external-link baggage stubs) are skipped,
  not fatal.

**Dry run** — two layers:
- The destination's own **Dry run** setting (persisted): every run prints the
  DELETE / PUT / INVALIDATE sets and makes no AWS call.
- The global **`--dryrun`** switch (new in 2026.1): forces a resolved S3
  setting dry for that one run, skips transports without dry-run support with
  an explicit log line, and is forwarded to member builds. There is
  deliberately no opposite switch — a setting declared dry cannot be forced
  live from the CLI.

**What `--dryrun` does to a `.wacj` depends on the destination's transport.**
An S3 compose already runs against a local `.compose-staging` mirror, so it can
rehearse faithfully; every other transport composes *in place*, so the only
honest rehearsal is to not compose at all:

| Destination | `--dryrun` behavior |
|-------------|---------------------|
| Amazon S3 | the resolved setting is forced dry for the run; the full compose runs against the staging mirror, and the would-be GET / PUT / INVALIDATE sets print. Member builds still run (dry). |
| Folder (or any non-S3) | member builds run (dry), then **the compose is skipped** and the run exits 0 |

The skip is explicit, not silent:

```text
Dry run (--dryrun): forcing S3 destination 'ProductionMirror' dry for this run.
Dry run (--dryrun): destination 'ProductionMirror' is composed in place (the 'file'
transport has no dry-run support); skipping the compose.
```

So `--dryrun` against a folder destination validates member selection, member
builds, and destination resolution — but tells you nothing about the compose
itself. To rehearse a folder compose, point a scratch destination at a copy of
the mirror and run for real.

## Authoring a composition in the AutoMap Administrator

A `.wacj` is plain XML and can be written by hand, but 2026.1 gives it a
first-class creation path. Compositions are ordinary rows in the jobs grid:
same name namespace, same Jobs-folder layout
(`<jobsdir>\<name>\<name>.wacj`), same scheduled-task plumbing, same
`<name>-log.txt`. Schedule / Run / Stop / View Log / Rename / Duplicate /
Delete all behave as they do for a `.waj`.

**Creating.** **File > New Job** offers a third intent beside the two
publishing ones:

> Compose published parcels into a website (Composition Job)

Unlike the other two, it has no file picker — a composition is *born in the
Jobs folder*, not derived from an external file. Naming it opens the
composition editor.

**The composition editor** maps 1:1 onto the grammar:

| Editor control | Grammar it writes |
|----------------|-------------------|
| **Member Jobs** grid — Member (path), Role, Build | `<Job path role build>` |
| read-only **Target** column | a member's `<Job target="...">`, when present |
| **Output target:** combo | `<Jobs target="...">` |
| **Deployment** — *Defined in this job* / *Deploy Destinations* | inline `<DeploySettings>` inside `<Destination>` / a name-only `<Destination>` |
| **Merge Settings** — Automatic / Custom (+ include-new checkbox) | omitted `<MergeSettings>` / declared placements / `discover="true"` |

- **Add...** is a dropdown, not a file dialog: it lists the publishing jobs in
  the Jobs folder by name. Jobs already added appear **checked and disabled**,
  so a duplicate member is not reachable. A separator and **Browse...** sit at
  the bottom for a job or project stored anywhere else (filter:
  `*.waj;*.wep;*.wrp`). With no jobs in the Jobs folder, Add... falls straight
  through to Browse.
- Members added here get **Build checked** — the derivative default.
- **Output target:** defaults to **(automatic)** and offers only target names
  whose format is compose-capable. A per-member `target=` override in the file
  is never edited away: the **Target** column appears only when some member
  declares one, and is read-only, making the override visible rather than
  silent. Change or remove it by editing the `.wacj`.
- A destination the composition references but this computer does not define
  is still listed, labeled `<name> (not defined on this computer)`, and stays
  selected on save.
- **Add Group** is seeded from the local members' group names and **Add
  Container** from the container names their Merge Settings declare, but free
  text stays available in both — a federated parcel may have no local member.
  Entering a name that is known only as a *container* under Add Group is
  warned, not silently accepted.

**Adopting a hand-authored `.wacj`.** There is no import mechanism (matching
`.waj`): drop the file in as `<jobsdir>\<name>\<name>.wacj` and the next
refresh discovers it. Run or Schedule lazily creates its scheduled task.
Whoever places the file owns its member paths — the reader rebases relative
paths against the `.wacj`'s own location.

**Round-trip fidelity.** Opening and saving a hand-authored file preserves
nested `<TOC>` containers, inline `<DeploySettings>`, and extra inline
definitions beyond the referenced one. **XML comments are not preserved** once
the editor saves. Keep commentary outside the file if it matters.

## Failure behavior

- A failed deploy is an **error**: it reaches the per-target error count and
  the process exit status (2026.1; earlier versions logged a warning and
  exited 0).
- `Destination '<name>' is not defined in deploy.prefs, the --deploysettings
  overlay, or inline in the composition job.` — seed the name via inline definitions, an overlay file,
  or deploy.prefs.
- `The mirror has no shell composition descriptor (wwcomposition-shell.xml)`
  — the shell was never deployed to that mirror (or the path points at an
  empty directory); rebuild and redeploy the shell.
- An inline WebDAV definition fails at job load, before any build starts.

**Ordered before any member build** (so a doomed run costs seconds, not
minutes): member file existence → [output target
selection](#output-target-selection-determinant) and same-format validation →
destination name resolution → unbuilt-member destination cross-check
(warnings). Member builds run only after all of those pass; a member build that
exits non-zero stops the run with
`Member build failed (exit <n>): <path>`.

## Tooling

The skill's Python tools understand `.wacj` as well as `.waj`:

- `python scripts/parse-job.py composition.wacj` — members with their role,
  build flag and the output target each composes through, the site-TOC spec,
  and the destination (with inline definitions). `--json` adds
  `"kind": "composition"`; `--config` exports a config for `create-job.py`.
  The Merge Settings `mode` is reported with the Administrator's labels:
  `automatic`, `custom`, `custom+include-new`.
- `python scripts/validate-job.py composition.wacj` — grammar preflight:
  member `path`/`role`/`build`, MergeSettings mode and spec, `<Destination>`
  (missing name fails; the pre-release `<DeployTarget>` spelling warns; an
  inline `Action="http"` WebDAV definition fails). Add `--check-members` to
  check member files exist and to cross-check each `.waj` member's declared
  targets and destination against the composition's.
- `python scripts/list-job-targets.py composition.wacj` — one line per member
  with its selected target and how it was selected (`member override` /
  `composition target` / `auto-detect`). `--enabled` / `--disabled` filter on
  `build`.
- `python scripts/create-job.py --template --composition > config.json`, then
  `python scripts/create-job.py --config config.json --output composition.wacj`
  — generates a `.wacj` that matches the product writer's conventions (role
  `infer`, `build="false"` and `discover="false"` omitted; a container title
  equal to its name omitted). Note: `--output` must be relative to the current
  directory.

Reference fixtures: `tests/fixtures/composition-federation/composition.wacj`
(valid federation) and `tests/fixtures/composition-invalid/broken.wacj`
(defect catalogue).

## Related

- Job origin modes, `deployScope`, and inline `<DeploySettings>` in `.waj`
  files: `references/job-file-guide.md`
- What a composed mirror looks like on disk and how to verify it (descriptors,
  manifest splice, cache key): the reverb2 skill's
  `references/federation-architecture.md`
