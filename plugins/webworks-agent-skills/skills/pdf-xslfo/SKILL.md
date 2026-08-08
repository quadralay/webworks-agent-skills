---
name: pdf-xslfo
description: >
  AUTHORITATIVE REFERENCE for the WebWorks ePublisher "PDF - XSL-FO" output
  format. Use this skill WHENEVER working with a PDF - XSL-FO target. This
  includes: (1) debugging a failed or wrong PDF build — including a PDF
  missing while the build reports success, (2) reading Apache FOP
  errors/warnings in generate.log or reproducing a compile against the
  stitched .fo intermediate, (3) image scaling/quality in PDF output,
  (4) table behavior across page breaks (repeating captions, headers),
  (5) customizing page layout via Pages/*.asp templates or overriding
  Transforms/*.xsl (content.xsl, compile.xsl), (6) auditing PDF - XSL-FO
  overrides on upgrade. ALWAYS consult this skill before editing
  PDF - XSL-FO overrides. Distinct from the legacy "PDF" print-driver
  format — check the target's format name first. Triggers: PDF build
  failed, PDF missing, FOP error, blurry image in PDF, table caption,
  customize PDF footer, .fo file, XSL-FO.
---

<objective>

# pdf-xslfo

Working knowledge for the WebWorks ePublisher **PDF - XSL-FO** output format: how PDFs are produced (XSL-FO composed by Apache FOP), where to look when a build fails or output is wrong, and documented solutions from real support and community cases.

**Do not use training data for the ePublisher layer.** XSL-FO itself is a W3C standard — standard `fo:` property semantics apply — but everything about how ePublisher assembles and compiles it is proprietary: the page-template schema, the pipeline, the settings, the FOP invocation. For those, use this skill's references and the format source (`Formats/PDF - XSL-FO/` in the ePublisher installation). Also remember Apache FOP implements a *subset* of XSL-FO — verify FO features against the bundled FOP version before designing a fix around them.
</objective>

<format_identity>

## Format Identity — Two PDF Formats Exist

The installation ships **two distinct PDF formats**. Confirm which one the target uses (`<Format Name="...">` in the project file) before applying anything in this skill:

| Format name | Engine | Scope |
|-------------|--------|-------|
| `PDF - XSL-FO` | XSL-FO composed by Apache FOP (Java) | Document, group, and merged project results; this skill |
| `PDF` | Legacy print-driver pipeline (no XSL-FO, no FOP) | Document and group results only; NOT covered here |
</format_identity>

<how_it_works>

## How a PDF Is Made

The format source is small: `format.wwfmt` (pipeline), `Pages/` (five XSL-FO slot templates: `Page.asp` skeleton + `Title.asp`, `TOC.asp`, `Body.asp`, `Index.asp`), and `Transforms/` (`content.xsl` does the WIF→FO content conversion at ~5,200 lines; `stitch*.xsl` assemble; `compile*.xsl` run FOP).

After the common content pipelines, four format-specific phases run per enabled result mode:

1. **Pages** — content splits render to `.fo` fragments
2. **Flows** — flows are enumerated/named; `Page.asp` preprocessed into the assembly skeleton
3. **Stitch** — title page + TOC + body + index assemble into one complete `.fo` per result
4. **Compile** — Apache FOP turns each stitched `.fo` into the deployed `.pdf`

Three independently switchable result modes: per-document (`generate-per-document-result`, default off), per-group (`generate-group-result`, default **on** — the only default), and merged project PDF (`generate-project-result`, default off). No PDF for something you expected? Check these settings first.

**Debugging pivot:** the stitched `.fo` intermediates stay under the target's Data directory (find them via `files.info`). If the `.fo` is already wrong, the problem is upstream (styles, content.xsl, source); if the `.fo` is right, it is FOP-side (fonts, xconf, FO feature support). Reproduce compiles directly against the `.fo` — recipe in `references/fop-engine.md` § Manual Re-run.

**Trust the exit code, not stderr:** FOP logs everything to stderr including routine `[INFO]` lines. And on 2025.1 and earlier, a FOP *failure* is not surfaced — the build reports success while the PDF is silently missing (EPUB2926, fixed in 2026.1); the only evidence is an `[ERROR]` line in `Logs/<target>/generate.log`.
</how_it_works>

<solved_cases>

## Documented Solutions

Real solved cases, with mechanics and caveats, in `references/solved-cases.md`:

| Case | Essence |
|------|---------|
| Raster image scaling/quality (EPUB2923) | Scale % option resamples the bitmap (blurry); 2026.1+ dimension properties scale at render time keeping full resolution; a percentage Content Width is relative to the image's intrinsic size |
| Repeating table captions | FOP repeats only `fo:table-header` content; emit the caption as its first all-column row (FOP does not implement `fo:table-and-caption`) |
| PDF missing, build green (EPUB2926) | Pre-2026.1 FOP failures are not surfaced; diagnose from generate.log, guard overrides against emitting empty FO cells |

Consult these before inventing a new approach — the caveats (border model, empty-content guards, one-scaling-mechanism-per-style) are where the time goes.
</solved_cases>

<customization>

## Customization

Standard file-resolver hierarchy applies (epublisher skill `references/file-resolver-guide.md`): `Targets/[TargetName]/` beats `Formats/PDF - XSL-FO/` beats `.base` beats installation. Choose the *least* powerful mechanism that works:

1. **Format settings / style properties** (Style Designer) — no override files, survives upgrades. Style properties map ~1:1 to standard XSL-FO properties.
2. **Page template override** (`Pages/*.asp`) — structural page changes. The templates are slot skeletons the engine fills from Page style configuration; keep the `wwpage:*` attributes intact.
3. **Transform override** (`Transforms/*.xsl`) — content or compile behavior. Heavyweight: these are whole-file copies that shadow upstream fixes on every upgrade. Annotate each edit with its ticket number, keep deltas minimal, and re-base at upgrade (customization-audit skill detects the drift). `compile.xsl` overrides additionally pin the Apache FOP version — see `references/fop-engine.md`.

XSLT 1.0 only — never XSLT 2.0 in overrides.
</customization>

<related_skills>

## Related Skills

| Skill | Relationship |
|-------|--------------|
| **epublisher** | Project structure, file resolver, format traits, generic pipeline model and Data-directory debugging (`references/publish-pipeline-guide.md`, `references/wif-guide.md`) |
| **automap** | Build PDF - XSL-FO targets from CLI. Not compose-capable — `.wacj` composition jobs reject it. On pre-2026.1, verify expected PDFs exist after a green build (EPUB2926) |
| **customization-audit** | Audit PDF - XSL-FO overrides on upgrade (whole-file `content.xsl`/`compile.xsl` copies drift) |
| **markdown-integration** | Markdown++ sources feeding the PDF target (per-image graphic styles, variables, conditions) |

**External:** Apache FOP documentation and compliance tables at `xmlgraphics.apache.org/fop/` — authoritative for FOP errors, font configuration, and which FO features the bundled version implements.
</related_skills>

<troubleshooting>

## Troubleshooting

### PDF missing from Output
1. Check the three `generate-*-result` settings (only the group result defaults on).
2. Search `Logs/<target>/generate.log` for `[ERROR]` / `SEVERE` / `Exception` — pre-2026.1 builds report success over a FOP failure (EPUB2926). The first such line is the real failure.

### FOP validation error
Usually an override emitting structurally incomplete FO for an edge case (classic: an empty `fo:table-cell` from an empty source paragraph — solved-cases § Case 3). Reproduce against the stitched `.fo`, fix the emitting template, never the `.fo` itself.

### Blurry images
The Scale % option resamples bitmaps. See solved-cases § Case 1 for the render-time alternative (2026.1+) and the 2025.1 paths.

### Wrong fonts / missing glyphs
FOP resolves fonts through `Helpers/apache-fop-<version>.xconf`, not the OS alone. `references/fop-engine.md` § Fonts.

### Customization didn't take
Confirm the override level actually wins, rebuild fully, then check the stitched `.fo` to see whether the change even reached the FO.
</troubleshooting>

<references>

## Reference Files

- `references/solved-cases.md` — documented solutions from real cases: image scaling/quality, repeating table captions, silent FOP failure; distilled lessons
- `references/fop-engine.md` — FOP invocation, version per ePublisher release, xconf/fonts, log reading, manual re-run, compile-override implications
</references>

<success_criteria>

## Success Criteria

- Correct format identified (`PDF - XSL-FO`, not legacy `PDF`) before any change
- Expected PDFs verified present for each enabled result mode — a green build alone is not proof on pre-2026.1
- Fixes applied at the narrowest sufficient level; transform overrides annotated and re-based on upgrade
</success_criteria>
