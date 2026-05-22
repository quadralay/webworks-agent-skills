---
name: markdown-integration
description: >
  AUTHORITATIVE REFERENCE for using Markdown++ source documents inside WebWorks
  ePublisher projects. Use when wiring Markdown++ files into a .wep/.wrp/.wxsp
  project, mapping styles to Stationery, configuring variables and conditions
  per target, building Markdown++ sources via AutoMap, or shaping Reverb output
  from Markdown++ markers and aliases. For Markdown++ syntax rules, validation,
  and best practices independent of ePublisher, use the markdown-plus-plus skill
  from the quadralay/markdown-plus-plus plugin.
---

<objective>

# markdown-integration

ePublisher integration patterns for Markdown++ source documents. This skill covers how Markdown++ documents fit into ePublisher projects, Stationery, AutoMap builds, and Reverb output — not the format spec itself.

**Format syntax lives elsewhere.** For Markdown++ syntax (variables, styles, aliases, conditions, includes, markers, multiline tables), validation rules, and authoring best practices, use the **markdown-plus-plus** skill in the [`quadralay/markdown-plus-plus`](https://github.com/quadralay/markdown-plus-plus) plugin. This skill assumes that knowledge and focuses on what changes when those documents become source files in an ePublisher project.

**Do not use training data for ePublisher integration of Markdown++.** Markdown++ is a WebWorks extension and the integration points (Variables window, Conditions window, Stationery style mapping, helper adapter) are proprietary. Use only this skill's references, the `epublisher`/`automap`/`reverb2` skills, and vendor documentation (`static.webworks.com`).
</objective>

<overview>

## Overview

ePublisher routes Markdown++ source files through the **helper adapter** (`Adapters/helper/markdown/`). Each Markdown++ extension maps onto an ePublisher concept:

| Markdown++ extension | ePublisher integration point |
|----------------------|------------------------------|
| `$variable;` | Variables window / Stationery defaults / target overrides |
| `<!--style:Name-->` | Stationery style definitions → format CSS/XSL |
| `<!--condition:name-->` | Conditions window / per-target visibility / job file overrides |
| `<!--include:path-->` | Source document group resolution (paths relative to including file) |
| `<!--marker:...-->` | Output-format processing (search keywords, index entries, CSH) |
| `<!--#alias-->` | Stable URL endpoints in Reverb output (`url_maps.xml`) |

The format-level rules for each are documented in the `markdown-plus-plus` skill from `quadralay/markdown-plus-plus`. This skill documents the ePublisher-side configuration each one requires.
</overview>

<variables>

## Variables — Sources and Resolution

A Markdown++ variable reference (`$product_name;`) is unbound until ePublisher resolves it. There are four sources, in increasing override priority:

1. **Stationery defaults** — defined in the `.wxsp` Stationery project, applied to every project derived from that Stationery.
2. **Project Variables window** — defined in the `.wep`/`.wrp` project, override Stationery defaults for that project.
3. **Target-specific overrides** — defined per target inside the project, override project-level values for one output target.
4. **Job file overrides** — `.waj` job files can override variables per target through the `<Variables>` element under each `<Target>`. These take precedence over all in-project values (target-specific, Project Variables window, and Stationery defaults).

See `references/integration-patterns.md` for the full priority table and per-environment / CI-CD layering patterns.

**Diagnosing unresolved variables:**

- Variable renders as literal `$name;` in output → not defined at any level for that target.
- Variable resolves differently across targets → check job file overrides first (if a `.waj` is in use), then target-level overrides, then project, then Stationery.
- Variable renders correctly in one project but not another derived from the same Stationery → check the project's local override is not blanking the value.

Use the `epublisher` skill's `parse-targets.py` to extract target definitions from the project file.

</variables>

<styles>

## Styles — Mapping to Stationery

A `<!--style:Name-->` comment names a style; the actual visual rendering comes from the Stationery's style definitions and the format's CSS/XSL transforms.

**Resolution path:**

1. Style name in Markdown++ document
2. Stationery `.wxsp` defines the style (inherited by all projects derived from this Stationery)
3. Format's CSS (Reverb, HTML) or XSL-FO templates (PDF) renders the style in output

**Practical rules:**

- Style names are **case-sensitive** and must match a style defined in the Stationery exactly.
- A style referenced in Markdown++ but not defined in the Stationery falls back to default Markdown rendering (no error, no warning).
- New styles require a Stationery edit, not a Markdown++ edit. Adding `<!--style:NewWarningBox-->` to a `.md` file does nothing until `NewWarningBox` exists in the Stationery's style definitions.
- Per-format style overrides live under `[Project]/Formats/[FormatName]/` in the file resolver hierarchy (see `epublisher` skill `references/file-resolver-guide.md`).

**Diagnosing a style that does not render:**

1. Confirm the style is defined in the Stationery (`.wxsp`).
2. Confirm the case matches exactly.
3. Confirm the comment is **attached** to its element (no blank line between) — see the format-level rules in the `markdown-plus-plus` skill.
4. Confirm the format's CSS/XSL actually renders that style class.

</styles>

<conditions>

## Conditions — Configuration and Per-Target Visibility

`<!--condition:name-->...<!--/condition-->` blocks are inert until ePublisher knows which conditions are active for the current target.

**Configuration sources:**

1. **Conditions window** — defines the set of available conditions for the project.
2. **Per-target visibility settings** — each target enables or disables conditions independently, controlling which content appears in that output.
3. **Job file overrides** — `.waj` job files can override condition visibility per target using `<Conditions>` under each `<Target>`.

**Common patterns:**

- **Output-format conditions** (`web`, `print`, `pdf`, `chm`) — enable per target so each target emits only its format-relevant content from the same source file.
- **Audience conditions** (`internal`, `external`, `beta`) — typically toggled across all targets together when producing audience-specific output.
- **Platform conditions** (`windows`, `mac`, `linux`) — useful when a single target serves multiple platforms with conditional sections.

**Diagnosing conditional content not appearing:**

1. Check the target's visibility settings for that condition name.
2. If using a job file, check the `<Conditions>` block under the target — it overrides project settings.
3. Confirm the condition name in the document matches exactly (case-sensitive).

</conditions>

<includes>

## File Includes — Source Document Group Resolution

`<!--include:path/to/file.md-->` directives resolve relative to the **including file**, not the project root.

**ePublisher implications:**

- A topic-map source file added as a single document to a group will pull in all its includes during the build. The included files do not need to be added to the group separately.
- Conditional includes (`<!--condition:web--><!--include:web-only.md--><!--/condition-->`) participate in the per-target condition resolution above.
- Circular include detection happens at build time in the helper adapter; AutoMap reports the cycle in its build log.

**When to add an included file to the group anyway:** if you want it to also build standalone (e.g., as a separate Reverb topic with its own URL), add it to the group separately. If it should only appear as part of a parent document's flow, leave it out of the group.

</includes>

<markers_and_aliases>

## Markers and Aliases in Output

Markers and aliases are inert in source — their effect is entirely defined by the output format's processing.

**Markers in Reverb 2.0:**

- `<!--marker:Keywords="api, auth"-->` populates Reverb's full-text search index with extra terms beyond the visible content.
- `<!--marker:IndexMarker="primary:secondary"-->` creates entries in the generated index (Reverb index pane).
- Marker syntax (single `marker:` vs JSON `markers:{...}`) and ordering rules are documented in the format-level skill.

**Aliases and CSH:**

- `<!--#alias-name-->` creates a stable URL endpoint in the generated output. In Reverb 2.0, aliases populate the `@href` and `@path` attributes in `url_maps.xml`.
- For Context Sensitive Help (CSH), the alias becomes the `@topic` identifier callable from the host application.
- Use the `reverb2` skill's `parse-url-maps.py` to verify which aliases became CSH-addressable topics in built output.

**Practical rule:** every heading that should be deep-linkable from outside the document should have an alias. Generated heading IDs from CommonMark fallback are not stable across heading text changes.

**Bulk alias generation** for documents that lack aliases on existing headings is a format-level authoring task — load the `markdown-plus-plus` skill in the `quadralay/markdown-plus-plus` plugin for the alias-generation script (formerly `add-aliases.py` in this plugin, migrated with the rest of the format spec). If the companion plugin is not installed, alias addition becomes a manual edit per heading.

</markers_and_aliases>

<automap_integration>

## AutoMap Build Integration

Markdown++ source files build through the helper adapter without special configuration — they go in the same source document groups as Word/FrameMaker/DITA files.

**Practical rules:**

- The `automap` skill's `automap-wrapper.sh` builds projects containing Markdown++ sources identically to other source types.
- The helper adapter has no `AdapterConfigurations` entries currently — there are no helper-specific knobs in project files.
- Job files (`.waj`) referencing Stationery built from Markdown++ sources work the same as job files for Word-based Stationery; the `<Documents>` block lists `.md` files alongside any other source type.

**Build-time validation:**

- Format-level Markdown++ syntax errors (unclosed conditions, malformed marker JSON, invalid variable names) surface in AutoMap output during the helper adapter pass.
- ePublisher-integration errors (undefined style, unconfigured condition, unresolved variable) typically do **not** fail the build — they degrade silently to default rendering, no condition expansion, or literal `$variable;` text.

**For format-level pre-build validation, use the `markdown-plus-plus` skill's validation script** (in the `quadralay/markdown-plus-plus` plugin). This catches syntax issues before AutoMap runs and avoids debugging silent fallbacks. Invocation depends on the companion plugin's installed location — load the `markdown-plus-plus` skill (e.g., `markdown-plus-plus:markdown-plus-plus` if the external plugin is installed in this Claude Code instance) for the current script path and arguments. If the companion plugin is not installed, ask the user to install it from `quadralay/markdown-plus-plus` or skip pre-build validation.

</automap_integration>

<reverb_output>

## Reverb Output Considerations

When Markdown++ sources target Reverb 2.0:

- **Search behavior** depends on document content plus marker keywords. `Keywords` markers expand the indexed term set without affecting visible content.
- **Topic URLs** depend on aliases. Documents without aliases get generated IDs that are not stable across content edits.
- **Conditional content** is resolved at build time, not runtime. A target that builds with `web` condition disabled will not include `web`-conditional content in the resulting Reverb output at all — no toggle.
- **Style rendering** depends on the Stationery's style definitions plus the Reverb format's CSS. Use the `reverb2` skill's SCSS workflow to customize how named styles render.

After building, use the `reverb2` skill's browser test (`scripts/browser-test.js`) and CSH analysis (`scripts/parse-url-maps.py`) to verify the Markdown++-driven output behaves as expected.

</reverb_output>

<related_skills>

## Related Skills

| Skill | Plugin | When to Use |
|-------|--------|-------------|
| **markdown-plus-plus** | [`quadralay/markdown-plus-plus`](https://github.com/quadralay/markdown-plus-plus) | Format syntax rules, validation, and authoring best practices for Markdown++ documents |
| **epublisher** | this plugin | Project file structure, Stationery, file resolver hierarchy, target configuration |
| **automap** | this plugin | Building projects with Markdown++ sources via the AutoMap CLI |
| **reverb2** | this plugin | Testing and customizing Reverb 2.0 output generated from Markdown++ sources |

**Typical workflow:**

1. Author Markdown++ documents using the **markdown-plus-plus** skill (format-level rules).
2. Use **markdown-integration** (this skill) to wire those documents into the project: define the variables, styles, and conditions they reference; group them as source documents; configure per-target visibility.
3. Use **automap** to build the project.
4. Use **reverb2** to verify output and customize Reverb-specific theming.

</related_skills>

<common_mistakes>

## Common Mistakes

**Editing Markdown++ source to fix a missing style.** A style only exists once it is defined in the Stationery. Adding `<!--style:NewBox-->` to a `.md` file does nothing until the Stationery defines `NewBox`. Open the Stationery first.

**Expecting conditions to render content at runtime.** ePublisher resolves conditions at build time. Conditional content is either present in the output or absent — there is no per-page toggle in Reverb. To switch which content appears, rebuild with different per-target visibility or different job file overrides.

**Treating an unresolved variable as a Markdown++ syntax error.** A literal `$variable;` in output means ePublisher had no value for it at any source level (Stationery, project, target, job file). The Markdown++ syntax is correct — the integration is incomplete. Check the Variables window first.

**Adding included files to source groups when the parent already includes them.** This causes them to build twice — once standalone, once as part of the parent — producing duplicate URLs and confusing TOC entries. Add a file to a group only if it should also build standalone.

**Looking for Markdown++ syntax docs in this skill.** Format syntax (variables, styles, conditions, includes, markers) lives in the `markdown-plus-plus` skill from `quadralay/markdown-plus-plus`. This skill assumes that knowledge and documents the integration layer.

</common_mistakes>

<references>

## Reference Files

- `references/integration-patterns.md` — Detailed integration-pattern walkthroughs (variable layering, style mapping, condition layering, source-group composition).

</references>

<success_criteria>

## Success Criteria

- Markdown++ source files are wired into the project's source document groups correctly.
- Variables referenced in the document resolve at every target.
- Styles referenced in the document are defined in the Stationery and render correctly per format.
- Conditions referenced in the document have matching configurations in the Conditions window and per-target visibility.
- AutoMap builds complete without helper-adapter errors.
- Reverb output reflects the expected aliases, markers, and conditional content.
</success_criteria>
