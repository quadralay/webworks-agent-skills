# Apache FOP Compile Engine

How the Compile stage turns a stitched `.fo` into a PDF, which FOP version
each ePublisher release uses, how to read FOP output, and how to reproduce a
compile outside the build. Verified against the ePublisher 2026.1
`Transforms/compile.xsl` and the `Helpers/` directory.

## Invocation Mechanics

`compile.xsl` (shared by the document/group/project wrappers) does the
following per stitched `.fo`:

1. Resolves the bundled JRE (`wwenv:JREHome()`) and the FOP helper
   (`wwhelper:apache-fop-<version>`) plus its configuration
   (`wwhelper:apache-fop-<version>.xconf`) to short (8.3) paths.
2. Writes a temporary batch file **beside the stitched `.fo`**
   (`<file>.fo.bat`) that sets `JAVA_HOME`, `FOP_HOME`,
   `CLASSPATH=%FOP_HOME%\build\*;%FOP_HOME%\lib\*` and runs:

   ```
   java.exe <memory-opts> org.apache.fop.cli.Main -c <xconf> -fo <file>.fo -pdf <out>.pdf
   ```

3. Executes the batch, logs the transcript, and **deletes the batch file**
   (success or failure — it is not left behind for reproduction).

Java memory options depend on the JVM bitness (`wwenv:JavaBits()`):

- 64-bit: `-Xms512M -Xmx4g`
- 32-bit: `-Xms128M -Xmx1024M`

The batch file itself is written in `Windows-1252`, or `Shift_JIS` when the
UI locale is Japanese — relevant only if paths contain characters outside
that codepage (the short-path conversion is the mitigation).

## FOP Version per ePublisher Release

The FOP helper name is **hard-coded in `compile.xsl`**, so the shipping FOP
follows the ePublisher release — and an overridden `compile.xsl` pins
whatever version it names. Verified from installed format sources:

- ePublisher ~2010.1–2011.x — Apache FOP (unversioned helper path)
- 2012.1–2013.x — FOP 1.0
- 2014.1 — FOP 1.1
- 2015.1–2020.1 — FOP 2.0
- 2021.1 — FOP 2.6
- 2022.1–2025.1 — FOP 2.8 (EPUB2446)
- 2026.1 — FOP 2.11 (EPUB2786; new in 2026.1)

`Helpers/` keeps every FOP version side by side (`apache-fop-1.0` through
`apache-fop-2.11`, each with its own `.xconf`), so an old pinned override
keeps *working* after an upgrade — silently compiling with the old engine and
its old bugs/behaviors. The customization-audit skill's drift detection
surfaces exactly this; when upgrading a project that overrides `compile.xsl`,
diff against the new installed version and re-apply the customization on top.

## Configuration and Fonts

FOP reads `Helpers/apache-fop-<version>.xconf` (note: at the `Helpers/` root,
not inside the FOP directory). This is standard Apache FOP configuration —
renderer settings and, most importantly, **font discovery**. FOP does not
simply use whatever Windows renders with: glyph coverage, bold/italic
synthesis, and CJK output all depend on what the xconf exposes.

Font symptoms and their meaning:

- `Font "X,normal,700" not found. Substituting with "any,normal,700".` —
  the style asks for a font FOP cannot resolve; output falls back, metrics
  shift. Fix the style's font family or the xconf font config.
- Glyphs rendering as `.notdef` (blank/box) — the resolved font lacks the
  glyphs. Real instance: FrameMaker Symbol-font characters (mu, Delta,
  radical) rendered as `.notdef` until the xconf was corrected — fixed in
  2026.1 (EPUB2811) with an `apache-fop-2.8.xconf` backport for 2025.1
  (EPUB2812). The backport is the precedent for delivering an xconf fix to
  an older release.
- Consult the Apache FOP documentation (`xmlgraphics.apache.org/fop/`) for
  the xconf font syntax of the specific FOP version in play — it differs
  across the 1.x/2.x line.

Prefer changing the *style's* font to a font FOP already resolves. Editing
the xconf is an installation-level change (there is no project-level override
for Helpers): it affects every project building on that machine and must be
re-applied when the installation is upgraded — document it in the project if
you take that path.

## Reading FOP Output

Two facts shape log reading:

1. **FOP routes all console logging to stderr, including `[INFO]`.** Stderr
   content is not a failure signal; the exit code is
   (`exit errorlevel` in the batch propagates it to the build).
2. The compile stage logs the transcript into `generate.log` /
   the build console:
   - (2026.1+, EPUB2926) A FOP failure — non-zero exit or missing output
     PDF — is raised as a build **error**. On success, lines matching
     `[WARN]`, `[ERROR]`, `[FATAL]`, `SEVERE`, or `Exception` are logged as
     build Warnings; everything else as progress Messages. On failure, the
     full transcript is kept at Warning as a backstop.
   - (pre-2026.1) A FOP failure is **not surfaced**: the build reports
     success while that result's PDF is silently missing, and the full
     stderr transcript logs as Warnings even on success — expect `[INFO]`
     noise flagged as warnings; it does not indicate a problem by itself.
     When an expected PDF is missing, grep `generate.log` for `[ERROR]`
     (see `solved-cases.md` § Case 3).

When diagnosing, find the **first** `[ERROR]`/`SEVERE`/`Exception` line; FOP
errors cascade and later messages are usually consequences. Common classes:

| Message class | Meaning | Fix direction |
|---------------|---------|---------------|
| `ValidationException` / "is not a valid child" / "is missing child elements" | The stitched FO violates the FO content model (classic: an empty `fo:table-cell` from an override meeting an empty source paragraph — `solved-cases.md` § Case 3) | Fix the emitting template/override — diff against the installed baseline |
| `PropertyException` / "Invalid property value" | A style property emitted a value FOP rejects | Trace the named property back to the Style Designer value |
| `OutOfMemoryError` | Heap exhausted on a large merged result | 64-bit JVM; split the result; raise heap via compile override (last resort) |
| Font substitution warnings | See Fonts above | Style font family or xconf |
| `FileNotFoundException` on an image | Image referenced by the FO is missing/moved | Check the image pipeline output in Data; by-reference vectors point at originals |

## Manual Re-run (reproduce outside the build)

The build deletes its batch file, but the stitched `.fo` remains in the
target's Data directory (find it via `files.info`). Reproduce a compile with
the same pieces the build used:

```bat
set JAVA_HOME=<install>\Helpers\WebWorks\...jre path (or any compatible JRE)
set FOP_HOME=C:\Program Files\WebWorks\ePublisher\<version>\Helpers\apache-fop-<v>
set CLASSPATH=%FOP_HOME%\build\*;%FOP_HOME%\lib\*
"%JAVA_HOME%\bin\java.exe" -Xmx4g org.apache.fop.cli.Main ^
  -c "C:\Program Files\WebWorks\ePublisher\<version>\Helpers\apache-fop-<v>.xconf" ^
  -fo "<data>\<stitched>.fo" -pdf "%TEMP%\test.pdf"
```

Match the FOP version and xconf to what the target's effective `compile.xsl`
names (check for an override first). A manual run gives you fast iteration on
FO-level problems: edit the `.fo` copy directly to bisect what FOP objects
to, then map the fix back to the style/template that generated it — never
ship an edited `.fo`.

## Overriding compile.xsl

Legitimate reasons: raising Java memory, adding FOP CLI options (PDF/A,
accessibility flags), or pinning a specific FOP for a rendering regression.
Costs: the override freezes the FOP version and invocation against upgrades
(see the version list above) and reimplements log handling. Annotate the
override with its ticket number, keep the delta minimal against the installed
baseline, and re-baseline on every ePublisher upgrade.
