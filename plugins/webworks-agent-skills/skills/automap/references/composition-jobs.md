# Composition Jobs (.wacj) — Federated Parcel Composition

> **Applies to ePublisher 2026.1 and later** (new in 2026.1). Earlier versions
> do not recognize `.wacj` files, the `deployScope` attribute, inline
> `<DeploySettings>`, or the `--deployscope` / `--deploysettings` / `--dryrun`
> options. Check the installed version before recommending any of this —
> see the epublisher skill's `references/version-compatibility.md`.

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

## Grammar

A `.wacj` is a distinct artifact that *references* jobs — like `.sln` vs
`.csproj`. The same `WebWorks.Automap.exe` runs both (dispatch on the root
element):

```xml
<?xml version="1.0" encoding="utf-8"?>
<CompositionJob name="product-docs" version="1.0">
  <Jobs>
    <Job path="shell\shell.waj"       role="shell"/>
    <Job path="install\install.waj"   role="parcel" build="true"/>
    <Job path="admin\admin.wep"       role="parcel"/>
  </Jobs>

  <MergeSettings>
    <TOC name="Guides">
      <Group name="Installation Guide"/>
    </TOC>
    <Group name="Administration Guide"/>
  </MergeSettings>

  <DeployTarget name="ProductionMirror"/>
</CompositionJob>
```

- **`<Job path role build>`** — members are `.waj` jobs or `.wep`/`.wrp`
  projects. `role` is `shell` or `parcel`. `build` defaults to **false**
  (compose-only; member output is already deployed). A `build="true"` member
  is built first, in its own process, with `--deployscope` derived from its
  role (`shell` → shell, `parcel` → groups) so a composition-driven federation
  cannot be mis-scoped.
- **`<MergeSettings>`** — the composed site TOC. `<Group name>` references a
  deployed parcel **by group name**; `<TOC name>` nests groups under folders.
  `discover="true"` composes every parcel found in the mirror instead
  (DISCOVERY mode); declared groups plus `discover` is the hybrid. The root
  `title` attribute is accepted for `.waj` grammar parity but unused (warned):
  the composed site's title is shell chrome.
- **`<DeployTarget name>`** — the shared destination. Resolution order:
  the composition job's own inline `<DeploySettings>` → a `--deploysettings`
  overlay file → the machine's deploy preferences (`deploy.prefs`), with a
  drift warning when an inline definition shadows a differing preference.

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
& $automapExe composition.wacj                       # compose only
& $automapExe composition.wacj --deployscope=shell   # NOT valid — scope belongs to member builds
```

- Exit code 0 on success; non-zero on error (undefined deploy target, missing
  shell descriptor, member build failure).
- A job-style log is written beside the file: `<name>-log.txt`.
- Expected success lines: `Harvested N parcel descriptor(s) from the mirror`,
  `Composed #parcels (N parcel(s)) into index.html`, `Composed cache key: ...`,
  `Composition complete: N parcel(s), M warning(s).`

Options forwarded to `build="true"` member builds: `--deployscope` (from
role), `--deploysettings` (merged inline + overlay definitions), `--dryrun`,
and `-t`/`--target` semantics apply per member job.

## Deploy scope

Every target declares which slice a deployment publishes. In the project it
is the Target Settings **Deploy** field; in a `.waj` it is the optional
`deployScope` attribute on `<Target>`; on the CLI it is `--deployscope`.
CLI overrides job attribute overrides project declaration.

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

## Inline deploy-target definitions

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

<!-- .wacj: inside <DeployTarget> -->
<DeployTarget name="ProductionMirror">
  <DeploySettings>
    <DeploySetting Name="ProductionMirror" Action="s3">...</DeploySetting>
  </DeploySettings>
</DeployTarget>
```

- Precedence per name: **job file's own inline > `--deploysettings` overlay
  file > deploy.prefs.** The log records which source resolved each name and
  warns when an inline definition shadows a differing preference (the drift
  detector).
- `--deploysettings=<file>` takes the same `<DeploySetting>` entries from an
  XML file — the CI seeding mechanism. A composition forwards its merged
  inline definitions to member builds automatically (they are separate
  processes), so name-only member jobs run on unseeded machines.
- **Security guardrail:** only secret-free transports may be inline — Folder
  (`Action="file"`) and Amazon S3 (`Action="s3"`). WebDAV (`Action="http"`)
  embeds credentials and is rejected at parse time with a clear error, as are
  custom actions. Those stay in deploy.prefs.

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

## Failure behavior

- A failed deploy is an **error**: it reaches the per-target error count and
  the process exit status (2026.1; earlier versions logged a warning and
  exited 0).
- `Deploy target '<name>' is not defined in deploy.prefs or inline in the
  composition job.` — seed the name via inline definitions, an overlay file,
  or deploy.prefs.
- `The mirror has no shell composition descriptor (wwcomposition-shell.xml)`
  — the shell was never deployed to that mirror (or the path points at an
  empty directory); rebuild and redeploy the shell.
- An inline WebDAV definition fails at job load, before any build starts.

## Related

- Job origin modes, `deployScope`, and inline `<DeploySettings>` in `.waj`
  files: `references/job-file-guide.md`
- What a composed mirror looks like on disk and how to verify it (descriptors,
  manifest splice, cache key): the reverb2 skill's
  `references/federation-architecture.md`
