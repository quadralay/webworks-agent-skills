# Markdown++ Integration Patterns

Detailed walkthroughs of how Markdown++ extensions integrate with ePublisher concepts. For format-level syntax rules, see the `markdown-plus-plus` skill in the [`quadralay/markdown-plus-plus`](https://github.com/quadralay/markdown-plus-plus) plugin.

## Variable Layering

Variables resolve through a four-level hierarchy. Each level overrides those below it for that target.

| Priority | Source | Defined in | Scope |
|----------|--------|------------|-------|
| 1 (highest) | Job file `<Variables>` under `<Target>` | `.waj` | One target in one build |
| 2 | Target-specific variables | `.wep`/`.wrp` | One target across all builds of that project |
| 3 | Project Variables window | `.wep`/`.wrp` | All targets in the project |
| 4 (lowest) | Stationery defaults | `.wxsp` | All projects derived from this Stationery |

### Pattern: Per-Environment Variable Override

Use case: same project builds for staging and production with different URLs.

1. Stationery defines `$api_url;` with a development default.
2. Project does not override.
3. Two targets exist: `Reverb-Staging`, `Reverb-Production`.
4. Each target overrides `$api_url;` with its environment-specific value.
5. Source documents reference `$api_url;` once; output differs per target.

### Pattern: CI/CD Variable Override per Build

Use case: build pipeline injects build-number or release-date at build time.

1. Stationery and project leave `$build_number;` unset.
2. CI generates a `.waj` job file with `<Variables><Variable name="build_number" value="1234"/></Variables>` under each target.
3. AutoMap consumes the job file; the value flows through to output.

## Style Mapping to Stationery

`<!--style:Name-->` is a *reference*. The Stationery defines the *implementation*.

### Walkthrough: Adding a New Callout Style

Goal: add a `<!--style:WarningCallout-->` style that renders with a red border and an icon in Reverb output.

1. **Edit the Stationery** (`.wxsp`):
   - Add `WarningCallout` to the style definitions.
   - Define its block-level type (paragraph, blockquote, list).
2. **Customize the format** for visual rendering:
   - For Reverb 2.0: add a CSS rule for `.WarningCallout` to a customization SCSS file under `[Project]/Formats/WebWorks Reverb 2.0/Pages/sass/` (see `reverb2` skill).
   - For PDF: add the corresponding XSL-FO template.
3. **Use the style in Markdown++**:
   ```markdown
   <!--style:WarningCallout-->
   > **Warning:** Action cannot be undone.
   ```

A common error sequence:

1. Add `<!--style:WarningCallout-->` to the document.
2. Build — output renders as a plain blockquote.
3. Conclude there is a Markdown++ syntax bug.

The bug is in step 1: the Stationery does not define `WarningCallout`, so the helper adapter passes the comment through but no format CSS targets it. Always confirm the Stationery defines the style first.

### Per-Target Style Overrides

The file resolver hierarchy lets a single style render differently per target without changing source documents:

```
[Project]/Targets/Reverb-Internal/Pages/sass/_custom-skin.scss
  → overrides .WarningCallout for the Internal target

[Project]/Formats/WebWorks Reverb 2.0/Pages/sass/_custom-skin.scss
  → applies to all Reverb targets in this project

[Project]/Formats/WebWorks Reverb 2.0.base/Pages/sass/_custom-skin.scss
  → packaged defaults

[Install]/Formats/WebWorks Reverb 2.0/Pages/sass/_custom-skin.scss
  → installation fallback
```

See the `epublisher` skill's `references/file-resolver-guide.md` and the `reverb2` skill's SCSS architecture for details.

## Condition Layering

Conditions are configured in three places that compose at build time.

| Priority | Source | Defined in | Scope |
|----------|--------|------------|-------|
| 1 (highest) | Job file `<Conditions>` under `<Target>` | `.waj` | One target in one build |
| 2 | Per-target visibility | `.wep`/`.wrp` | One target across all builds |
| 3 | Conditions window | `.wep`/`.wrp` | Defines the available conditions for the project |

### Pattern: Single Source, Multiple Audiences

Use case: documentation source produces both an internal-only and a customer-facing build.

1. Conditions window defines `internal` and `external`.
2. Source documents wrap internal content:
   ```markdown
   <!--condition:internal-->
   Engineering notes about the rate limiter.
   <!--/condition-->
   ```
3. Two targets: `Help-Customer` and `Help-Internal`.
4. `Help-Customer` enables `external` only; `Help-Internal` enables both.
5. Same source files; different output content.

### Pattern: Format-Specific Content

Use case: print version omits interactive web elements.

1. Conditions window defines `web`, `print`.
2. Source uses `<!--condition:web-->` and `<!--condition:print-->` to gate content.
3. Reverb target enables `web`; PDF target enables `print`.

## Source Document Group Composition

How includes interact with project source document groups.

### Pattern: Topic Map as Single Source File

Goal: a 30-chapter user guide where each chapter lives in its own file but builds as one document.

1. Create `_user-guide.md` containing only includes:
   ```markdown
   <!--marker:Title="User Guide"-->

   <!--include:01-introduction.md-->
   <!--include:02-getting-started.md-->
   ...
   ```
2. Add **only** `_user-guide.md` to the source document group.
3. Build — the helper adapter resolves all includes; output is one structured document.

The included chapter files do not need to be in the group. They will be processed during the include resolution.

### Pattern: Mixed Standalone and Included Documents

Goal: chapters are usable standalone (separate Reverb topics) and also referenced from a parent document.

If chapter files appear in the group **and** the parent includes them, they will build twice — once standalone, once embedded — producing duplicate URLs.

Choose one composition:

- **Topic-map only**: parent file in group, chapters not in group.
- **Standalone only**: chapters in group, parent file not in group.
- **Hybrid via conditions**: parent uses conditional includes only when a `topic-map` condition is enabled, and use that condition selectively per target.

## Marker Patterns for Output

### Search Keyword Augmentation

```markdown
<!--marker:Keywords="REST, API, endpoint, webhook"-->
# Webhook Configuration
```

These terms feed the Reverb full-text search index. They do not appear in the page; they only affect search hit relevance.

### Index Entries

```markdown
<!--marker:IndexMarker="Authentication"-->
## OAuth Setup
```

Generates an index entry visible in Reverb's index pane (and in PDF index sections).

Hierarchical entries:

```markdown
<!--marker:IndexMarker="Authentication:OAuth"-->
## OAuth Setup

<!--marker:IndexMarker="Authentication:API Key"-->
## API Key Setup
```

Multiple entries:

```markdown
<!--markers:{"IndexMarker": "Authentication, Security:Tokens, OAuth"}-->
## OAuth Setup
```

### Custom Metadata

```markdown
<!--marker:Author="Documentation Team"-->
<!--marker:LastReviewed="2025-Q3"-->
```

These appear as metadata in the WIF intermediate format and are available to format XSL transforms for custom output processing. Useful for tagging content for downstream tools.

## Alias Patterns for CSH and Cross-Document Linking

### Stable URLs

```markdown
<!--#configure-webhooks-->
## Configuring Webhooks
```

The alias becomes the topic's URL fragment. If the heading text later changes from "Configuring Webhooks" to "Setting Up Webhooks," the URL stays `#configure-webhooks` because the alias drove it. Without the alias, the URL would change with the heading.

### Cross-Document Links

```markdown
For setup details, see [Webhook Configuration](webhooks.md#configure-webhooks).
```

The build resolves the cross-document link to the correct output URL for the target's format.

### Context Sensitive Help (CSH)

CSH topic IDs in the host application correspond to alias names. Coordinate with the host-app team to use stable, well-named aliases on every topic that should be CSH-addressable. Use the `reverb2` skill's `parse-url-maps.py` to confirm the alias-to-URL mapping after build.

## Build-Time vs Source-Time Concerns

A useful mental model when debugging:

| Concern | Resolved at | Diagnose by |
|---------|-------------|-------------|
| Variable value | Build time, per target | Check Variables window, target overrides, job file |
| Style rendering | Build time + format CSS/XSL | Check Stationery definition, format customization |
| Condition visibility | Build time, per target | Check per-target condition settings, job file |
| Include resolution | Build time, helper adapter | Check paths relative to including file |
| Marker effects | Build time, then format processing | Check marker syntax, then format-specific behavior |
| Alias URL | Build time, format-specific | Check format's URL generation (e.g., `url_maps.xml` for Reverb) |

Format syntax errors (unclosed conditions, malformed JSON) are caught earlier — at the helper adapter parse step. Use the `markdown-plus-plus` skill's validation script (in the `quadralay/markdown-plus-plus` plugin) to catch those before AutoMap runs.
