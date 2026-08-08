# Solved Cases

Real problems solved on PDF - XSL-FO projects, harvested from support and
community work. Each entry gives the problem, the root cause in the format,
the working solution, and its caveats — apply the pattern, not just the
specific fix. Distilled lessons at the end.

## Case 1: Raster image scaling and print quality (EPUB2923)

**Problem:** A user scales a logo down (say to 20%) and the PDF result is
visibly blurry in print and on zoom.

**Root cause:** Two different mechanisms exist, and before 2026.1 only the
lossy one worked for raster images. The `Frame-Markup-External-Graphic`
template in `Transforms/content.xsl` strips all dimension properties for
raster images and always emits the DPI-normalized viewport — so the Graphic
style dimension properties in Style Designer silently did nothing, and the
only working knob was the **Scale %** option, which *resamples the bitmap at
generation time*: a 600x400 image scaled to 20% ships as a 120x80 bitmap
(96 DPI effective on the page).

**Solution (2026.1+, EPUB2923):** use Graphic style **dimension properties**
instead of Scale % — the FO engine scales at render time and the
full-resolution original stays embedded (~5x the linear resolution of the
Scale % result at the same layout size):

- **Content Width / Content Height** (Advanced group): a percentage is
  relative to the image's **own intrinsic size** — per XSL-FO semantics,
  `20%` renders the full-resolution original at 20% of its natural
  dimensions.
- **Width / Height** (Layout group): an absolute box (e.g. `1.25in`); the
  image scales into it, aspect preserved (`scaling="uniform"`).

**Caveats:**

- Use **one mechanism per style**, not both — Scale % resamples first and
  defeats the quality benefit.
- Explicit dimensions are honored verbatim: an oversized Width can overflow
  the page; sizes larger than natural upscale.
- Vector (SVG) images have their own sizing path and are unaffected.
- Companion quality tip: set the Graphic style **Format** option to `png`
  (and **Output file extension** to `.png`) so regenerated screenshots/line
  art avoid JPEG artifacts.
- **Per-image scaling from Markdown++:** assign a dedicated graphic style
  inline — `<!--style:SmallLogo-->` before the image — and set the property
  on that style (markdown-integration skill for the wiring).
- **2025.1 and earlier:** dimension properties on raster images are ignored;
  the paths are the Scale % option or a support-delivered project-level
  override of `content.xsl` annotated with EPUB2923.

**References:** Trac EPUB2923 (r36058, ships 2026.1); how-to spec in
[quadralay/epublisher-docs#85](https://github.com/quadralay/epublisher-docs/issues/85);
three-way sample project and regression gate in quadralay/epublisher-tests
PR #39 (`images/pdf-graphic-dimension-properties`).

## Case 2: Repeating table captions across page breaks

**Problem:** When a table spans multiple pages, the heading row repeats on
each continuation page but the caption appears only on the first page. The
customer wanted the caption to repeat like the heading row does.

**Root cause:** Apache FOP repeats only the contents of `fo:table-header`
at the top of each page a table breaks onto. The stock format emits the
caption as a standalone block *before* the `fo:table`, so it cannot repeat.
`fo:table-and-caption` / `fo:table-caption` are **not** the answer — Apache
FOP does not implement them.

**Solution (project-level override of `content.xsl`):**

1. Remove the standalone caption block emitted before the table.
2. Emit the header section whenever the table has a caption, even with no
   column-heading rows (a caption-only table still repeats its caption).
3. In `Content-TableSection`, emit the caption as the **first,
   all-column-spanning row of `fo:table-header`**. Style the cell white,
   zero-padding, `border-style="hidden"` so it reads as a caption, not a
   header cell; render the caption text with the same templates the
   standalone caption used so its paragraph style is preserved.

**Caveats:**

- `hidden`, not `none`: in the collapsing-border model `none` has the lowest
  priority and loses to the header section's solid border, which bleeds a
  border onto the caption row.
- **Guard against empty captions** — see Case 3: an empty caption paragraph
  (e.g. all text hidden by conditions) must not emit an empty
  `fo:table-cell`. Render the caption content into a buffer first and emit
  the caption row only when the rendered content is non-empty.
- The repeating caption necessarily sits *inside* the table's outer border.
- Applies to every captioned table, not just long ones (short tables look
  unchanged).
- Whole-file override of `content.xsl`: on upgrade, re-base the edits onto
  the new installed file or the copy shadows newer upstream fixes.
- Verified with FOP 2.8 (2025.1); the `fo:table-header` repeat behavior is
  identical on FOP 2.11.

## Case 3: Build succeeds but a PDF is missing (EPUB2926)

**Problem:** Generation completes, AutoMap exits 0, the build/job status
reports success — but one book's PDF is simply absent from the output.

**Root cause:** Before the EPUB2926 fix, an Apache FOP rendering failure was
not surfaced: the compile stage logged FOP's `[ERROR]` output into
`Logs/<target>/generate.log` and moved on. Any fatal FO validation error
kills that entire result's PDF while everything else builds normally. The
triggering instance came from Case 2's Revision 1: an empty caption produced
an empty `fo:table-cell`, and FOP aborted with
`org.apache.fop.fo.ValidationException: "fo:table-cell" is missing child
elements. Required content model: marker* (%block;)+`.

**Diagnosis (all versions):** when an expected PDF is missing, search
`Logs/<target>/generate.log` for `[ERROR]`, `SEVERE`, or `Exception` —
the first such line names the real failure; later ones are usually cascade.
Then reproduce against the stitched `.fo` intermediate (see
`fop-engine.md` § Manual Re-run).

**Fixed (2026.1, EPUB2926):** the compile stage captures the FOP exit code
and raises a build **error** when FOP fails or the output PDF is missing,
and partitions the FOP transcript so warning/error lines surface as build
Warnings instead of being buried.

**Caveats:** on 2025.1 and earlier, treat "build green" as *not* proof the
PDFs exist — verify the expected outputs are present, especially in CI
(automap skill) where nobody eyeballs the output directory.

## Distilled Lessons

- **FOP implements a subset of XSL-FO.** Standard-FO solutions can be dead
  ends (`fo:table-and-caption`). Check FOP's compliance page for the bundled
  FOP version before designing a fix around an FO feature.
- **The FO the format emits is the contract.** Fatal FOP validation errors
  (empty `fo:table-cell`, invalid property values) usually trace back to a
  format override emitting structurally incomplete FO for an edge case the
  stock format never hits. When overriding `content.xsl`, buffer generated
  content and emit enclosing structure only when the content is non-empty.
- **Whole-file overrides shadow upstream fixes.** `content.xsl` is ~5,200
  lines; a project override is a full copy with a few edits. Mark each edit
  with its ticket/case annotation, keep the delta minimal, and re-base on
  every ePublisher upgrade (customization-audit skill automates the drift
  detection).
- **Verify against the bundled FOP version** of the project's base format
  (version list in `fop-engine.md`), and state that in the delivery notes.
