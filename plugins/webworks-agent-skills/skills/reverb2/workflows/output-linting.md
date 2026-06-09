# Workflow: Output Linting (static pre-flight)

*From SKILL.md intake item 6.*

<required_reading>
**No additional references needed** — all information is in this file. The
checks mirror how `scripts/connect.js` loads parcels in any Reverb 2.0 output;
consult that runtime file only when investigating a behavior mismatch.
</required_reading>

<process>
## When to Use

Run the linter on a built or **assembled** Reverb 2.0 output directory to catch
structural breakages that kill the runtime **silently** — the page hangs on the
spinner with no console error — before anyone opens it in a browser. It needs no
Chrome and no runtime, so it belongs in CI and in pre-deploy gates. It is the
cheap *static* counterpart to the browser test (intake item 1), which is the
*runtime* confirmation.

Reach for it especially when output is **assembled from more than one build** —
the Reverb-on-S3 "deploy set" model, a manifest splice, a hand-edit, or any
pretty-printer/formatter run over the HTML. Those are exactly the situations
that produce the breakages below.

## Step 1: Point It at the Output Directory

The argument is the directory that contains `index.html` (the shell entry
point), e.g. `Output/WebWorks Reverb 2.0`.

```bash
python scripts/lint-output.py "<output-dir>"
```

Flags:

| Flag | Effect |
|------|--------|
| `--json` | Emit a structured JSON report instead of human-readable text. |
| `--strict` | Treat warnings as failures (affects the exit code only). |
| `--no-color` | Disable ANSI color (auto-disabled when stdout is not a TTY). |

## Step 2: Read the Checks

| Check | Severity | Breakage | Fix |
|-------|----------|----------|-----|
| `self-closed-element` | error | A non-void element written in XML self-closing form (`<script/>`, `<iframe/>`, `<div/>`, `<span/>`, `<ul/>`, …). In `text/html` the `/` is ignored, so the element parses as *open* and swallows the rest of the document. The first page never renders and there is **no** console error. (Trac #2792.) | Re-emit the element with a real close tag (`<div></div>`). Usually caused by an XML/XHTML formatter run over the output — stop pretty-printing the HTML, or use an HTML-aware formatter. Void elements (`<meta/>`, `<link/>`, `<br/>`, …) and `<svg>`/`<math>` foreign content are exempt. |
| `manifest-parcel-groupid` | error | A parcel's own GroupID disagrees with what the `#parcels` manifest binds. `connect.js` reads `id.split(':')[1]` from each anchor `<a id="<ctx>:<GID>" href="<Name>.html">`, fetches `<Name>.html`, and looks up `toc:<GID>`/`data:<GID>`/`page:<GID>:first` inside it. On a mismatch every lookup returns null, the parcel never attaches, and the spinner hangs. | Rebuild the parcel and the manifest entry from the **same** GroupID, or rewrite the manifest anchor's GroupID to match the parcel (this is what a correct deploy-set assembler does — splice by GroupID). The linter also flags a `<li id="group:<GID>">`-vs-anchor desync within the manifest itself. |
| `parcel-deploy-unit` | error | A manifest parcel `<Name>` is missing a deploy-unit member. | Deploy the whole unit together: `<Name>.html` (the manifest href) and the `<Name>/` content directory are always required; the runtime chunks `<Name>_ix.html`/`<Name>_lx.js`/`<Name>_sx.js` are required when the build's `scripts/connect.js` fetches them (older builds omit `_lx.js`, search-off builds omit `_sx.js`). A parcel is **not** a single self-contained folder. |
| `reference-integrity` | warn | A local `scripts/`/`css/` asset referenced by `index.html` is missing on disk. | Deploy the referenced asset, or fix the reference. Remote (`http(s)://`, `//`) and `data:` references are not checked. |

The self-closed scan covers `index.html`, the root shell pages (`search.html`,
`splash.html`, `not-found.html`), and each parcel's `<Name>.html` and
`<Name>_ix.html`.

## Step 3: Interpret the Exit Code

| Exit code | Meaning | CI action |
|-----------|---------|-----------|
| `0` | Clean — no errors (and no warnings under `--strict`). | Proceed. |
| `1` | At least one error-severity finding (or any warning under `--strict`). | Fail the build; read the findings. |
| `2` | The linter could not run — `<output-dir>` is missing or not a directory. | Check the path; this is a harness error, not a lint result. |

Warnings alone do **not** fail the default run. Add `--strict` in a gate that
should also block on missing-asset warnings.

## Step 4: Output Shapes

**Text** (default) groups findings by check and shows `file:line:col`, the
message, and a source snippet for self-closed hits:

```
ERROR  [self-closed-element]  index.html:7:1900
       <div> is self-closed; in text/html the '/' is ignored and the element
       swallows following markup - kills the Reverb runtime silently (Trac #2792)
       > <div id="injected_break"/>

1 error(s), 0 warning(s)
```

(For minified output every line is `1`; the `col` and snippet locate the hit.)

**JSON** (`--json`) is machine-readable for CI:

```json
{
  "tool": "lint-output",
  "output_dir": "Output/WebWorks Reverb 2.0",
  "success": false,
  "summary": { "errors": 1, "warnings": 0, "total": 1 },
  "findings": [
    {
      "check": "manifest-parcel-groupid",
      "severity": "error",
      "file": "Charlie.html",
      "message": "GroupID mismatch: the manifest binds parcel 'Charlie.html' to GroupID 'parcel-lab-grp-charlie', but the parcel's landmarks use 'other-build-gid-99'. ..."
    }
  ]
}
```

`success` already folds in `--strict`; gate on it (or on the exit code) rather
than re-deriving from the counts.

## Step 5: Chain Into the Browser Test

The linter and the browser test are complementary, not redundant:

- **Linter** = fast *static* pre-flight (CI / pre-deploy; no browser). Catches
  structural breakage — the kinds above — instantly.
- **Browser test** (`browser-test.js`, intake item 1) = *runtime* confirmation
  (post-flight; needs Chrome). Confirms the build actually loads via the
  `preload` signal.

Run the linter first; only spend a browser launch on output that is structurally
sound:

```bash
python scripts/lint-output.py "output/WebWorks Reverb 2.0" || exit 1
node scripts/browser-test.js "$CHROME" "$ENTRY_URL"
```

## Step 6: Extending the Linter

New known-breakage checks are added to `scripts/lint-output.py` as they are
discovered — write a `check_*` function that appends `Finding` objects, call it
from `lint()`, and add a fixture-mutation scenario to
`tests/verify-lint-output.py`. The GroupID-consistency check, for example, came
straight out of a real Reverb-on-S3 deploy-set assembly bug.
</process>

<success_criteria>
This workflow is complete when:
- [ ] The linter was pointed at the directory containing `index.html`
- [ ] Every error-severity finding was understood and fixed (or consciously accepted)
- [ ] The chosen gate strictness (`--strict` or not) matches whether missing-asset warnings should block
- [ ] The exit code was interpreted correctly — `2` traced to a bad path, not mistaken for "found problems"
- [ ] For a real load confirmation, the browser test was run after a clean lint
</success_criteria>
