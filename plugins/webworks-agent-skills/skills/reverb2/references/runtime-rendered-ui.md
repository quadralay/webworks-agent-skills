# Runtime-Rendered UI Surfaces

> **Applies to ePublisher 2026.1 and later.** Both surfaces below are new or
> reworked in 2026.1.

Two pieces of Reverb 2.0 chrome are **not** in the published markup: the
splash page's Groups Grid and the AI Assistant's avatar. The templates ship an
empty container and the runtime builds the DOM into it. That inverts the usual
debugging move — reading the `.asp` will not tell you what renders, and
searching the published HTML for the card markup finds nothing. Read the
JavaScript (`Pages/scripts/connect.js`, `Pages/scripts/page.js`,
`Pages/scripts/assistant.js`), then style through the documented
`ww_skin_*` hooks.

## Splash Groups Grid (EPUB2907)

The splash page is a responsive grid of entry-point cards generated at runtime
from the help set's Groups and Merge Settings Containers. It replaces the
former static splash image.

### What the template contains

`Pages/Splash.asp` is now lean: no splash image, no logo block, no inline
styles. The whole grid region is one empty container:

```html
<nav id="splash_groups" class="ww_skin_splash_groups"
     aria-label="Groups" wwpage:attribute-aria-label="groups-grid-label">&#160;</nav>
```

The `aria-label` is localized from the `GroupsGridLabel` locale string
(`Transforms/splash.xsl` → `locales.xml`).

### How the cards are built

| Step | Where |
|------|-------|
| Wait for `Parcels.loaded_all`, flushing any deferred hydration first (`Navigation.FlushDeferredLoadRemaining`), then re-check the splash is still displayed | `Connect.SplashGroupsSchedule` (`connect.js`) |
| Walk the **master TOC** in `#toc_content` — the `#parcels` manifest skeleton with each loaded parcel's TOC grafted in — and collect one card per top-level `<li>`, with the entries of its direct child `<ul>` as member links | `Connect.SplashGroups_CollectData` (`connect.js`) |
| Post the result to the splash iframe as **structured titles and hrefs, never markup** | `Message.Post` → `'splash_groups_data'` |
| Build the DOM with `createElement` / `textContent`, validate every href with `Message.IsSafeURL`, wire clicks through `Page.InterceptLink` | `Page.SplashGroupsRender` (`page.js`) |

Consequences worth knowing:

- **The grid mirrors the merge hierarchy, not the file tree.** A Merge Settings
  container becomes a card whose members are the groups inside it; a top-level
  group becomes a card whose members are its first TOC level. A container title
  carries no link of its own, and a group title loses its manifest href once
  its parcel TOC is grafted in — so both fall back to the first descendant
  link. Every card is guaranteed to reach a link, or it is dropped.
- **The master TOC is populated whether or not the Menu shows it.** The TOC
  data island in each parcel page is emitted when
  `toc-generate = true` **OR** `show-first-document = false`
  (`Transforms/parcel.xsl`), so the grid still works with the Menu TOC turned
  off. Only a target with the TOC disabled *and* the splash bypassed omits it.
- **Federated shells get their cards the same way.** The shell's own build
  contributes no groups; the grid is populated client-side from the composed
  `#parcels` manifest and the parcel TOCs the runtime loads. Nothing about the
  grid is baked in at compose time.

### Responsive layout

The grid renders **inside the page iframe**, where the Connect frame's
`#layout_div` is not visible. The Connect frame therefore mirrors its layout
vocabulary onto the grid container on every layout change
(`Connect.SplashGroupsPostLayout` → `'splash_groups_layout'` →
`Page.SplashGroupsApplyLayout`). Classes are rebuilt from booleans, never
copied from the message:

| Mode | Class on `#splash_groups` |
|------|---------------------------|
| Desktop | `ww_skin_splash_groups layout_wide` |
| Mobile landscape | `ww_skin_splash_groups layout_narrow` |
| Mobile portrait | `ww_skin_splash_groups layout_narrow layout_tall` |

### DOM and skin hooks

| Element | Class |
|---------|-------|
| Grid container (the `<nav>`) | `ww_skin_splash_groups` |
| Grid list (`<ul>`) | `ww_skin_splash_groups_grid` |
| Card (`<li>`) | `ww_skin_splash_group_card` |
| Card title (`<div>` wrapping an `<a>` or `<span>`) | `ww_skin_splash_group_card_title` |
| Member list (`<ul>`) | `ww_skin_splash_group_card_members` |

Base styling lives in `Pages/sass/skin.scss` § *Splash - Groups Grid*; the
responsive selectors live in `Pages/sass/webworks.scss` § *Splash - Groups Grid
responsive layout* (that is the sheet governing content inside the iframe). The
card hover/lift transitions are disabled under
`@media (prefers-reduced-motion: reduce)`.

### `$splash_groups_*` variables

Layer-1 theming for the grid, by partial:

| Partial | Variables |
|---------|-----------|
| `_sizes.scss` | `$splash_groups_padding`, `$splash_groups_padding_narrow`, `$splash_groups_grid_gap`, `$splash_groups_grid_gap_narrow`, `$splash_groups_card_min_width`, `$splash_groups_card_padding`, `$splash_groups_card_border_radius`, `$splash_groups_card_accent_height`, `$splash_groups_member_link_padding` |
| `_colors.scss` | `$splash_groups_card_background_color`, `$splash_groups_card_border_color`, `$splash_groups_card_border_color_hover`, `$splash_groups_card_accent_color`, `$splash_groups_card_title_text_color`, `$splash_groups_card_title_text_color_hover`, `$splash_groups_card_member_text_color`, `$splash_groups_card_member_text_color_hover` |
| `_borders.scss` | `$splash_groups_card_border_style`, `$splash_groups_card_border_width` |
| `_fonts.scss` | `$splash_groups_card_title_font`, `$splash_groups_card_title_font_size`, `$splash_groups_card_title_font_weight`, `$splash_groups_card_member_font`, `$splash_groups_card_member_font_size` |

Anything the variables do not reach goes in `custom.scss` (see
`scss-architecture.md` § "The `custom.scss` Layer").

### Upgrade impact: `splash.png` overrides stop working

**No template references `splash.png` any more.** The file still ships at
`Pages/images/splash.png`, so a project override of it is silently **inert**
rather than an error — the splash simply shows the grid instead.

A project that customized the splash by overriding `splash.png` must now
override **`Pages/Splash.asp`** instead (or restyle the grid through the
`$splash_groups_*` variables and `custom.scss`). Flag this during any 2026.1
customization audit: an override of `Pages/images/splash.png` in
`Targets/*/` or `Formats/*/` is dead weight after the upgrade.

The inverse also bites: a project carrying a **pre-2026.1 `Splash.asp`
override** keeps its old splash markup, which has no `#splash_groups`
container — so the grid never renders and nothing reports it. `lint-output.py`
flags exactly this case (`splash-groups-container`, warn).

## Assistant avatar (EPUB2911)

The AI Assistant renders the assistant's configured avatar image in place of
the generic Font Awesome icon.

### Source and validation

`avatar_url` arrives on the WebWorks Platform's **public assistant payload**
and is stored as-is by `Assistant_UpdateAssistantData`. Whether it is
*renderable* is decided at render time by `Assistant_GetAvatarImageUrl`, which
accepts only **absolute `http(s)` URLs** — `javascript:`, `data:`,
protocol-relative, and site-relative values all fall back to the generic icon.
The URL is attribute-escaped with `Assistant_EscapeAttribute` before
interpolation (`Assistant_EscapeHtml` routes through `textContent` and leaves
quote characters intact, which is unsafe for an attribute value).

### Markup

One helper, `Assistant_RenderAvatar`, feeds every assistant-side slot: the
**welcome screen**, **assistant message rows**, the **thinking/reasoning
row**, the **error row**, the **latest-response row**, the **streaming row**,
and the **conversation-list (thread list) header**. The user-side avatar slot
is unchanged.

```html
<!-- icon (no usable avatar_url) -->
<div class="ww_skin_assistant_avatar"><i class="fa"></i></div>

<!-- image -->
<div class="ww_skin_assistant_avatar ww_skin_assistant_avatar_has_image">
  <img class="ww_skin_assistant_avatar_image" alt=""
       src="…" onerror="Assistant_HandleAvatarImageError(this)">
</div>
```

`alt` is intentionally empty — the avatar is decorative; the assistant's name
is always rendered beside it.

### Failure fallback

`Assistant_HandleAvatarImageError` swaps that slot back to the icon **and
latches the failure** (`Assistant.assistant_avatar_unavailable`), so later
re-renders neither emit the image nor re-request a URL already known to be
broken. A payload carrying a *different* `avatar_url` clears the latch.

### Skin hooks

| Class | Role |
|-------|------|
| `ww_skin_assistant_avatar` | The slot container. Fixed size at every slot (2rem; 4rem on the welcome screen, 3rem in `.ww_skin_assistant_info`), with `overflow: hidden` so the image crops to the container's corner radius. |
| `ww_skin_assistant_avatar_has_image` | **New in 2026.1.** Added to the container only in the image case, as a target for skins that style a photo differently from the icon (dropping the icon's background tint, for instance). The stock skins do not need it. |
| `ww_skin_assistant_avatar_image` | The `<img>`: fills the container, `object-fit: cover`, `border-radius: inherit`. |

Because the container is already fixed-size at every slot, the message list
does **not** reflow as avatars load.

Sizing and cropping live in `Pages/sass/connect.scss`; the icon's background
and color come from `$assistant_avatar_background_color` /
`$assistant_avatar_icon_color` (`_colors.scss`) and `$assistant_avatar_icon`
(`_icons.scss`) via `Pages/sass/skin.scss`.

> **Packaged skins carry their own copy.** A `.weplugin` skin that ships a full
> `connect.scss` needs the avatar image rules applied to *its* copy too —
> another reason the packaged-skin route is deprecated. See
> `scss-architecture.md` § ".weplugin Migration".

---

**See also:**
- `scss-architecture.md` — the `custom.scss` layer, variable partials, cascade
- `federation-architecture.md` — composed `#parcels` manifests that feed the grid
- `../epublisher/references/file-resolver-guide.md` — override hierarchy for `Splash.asp` and the partials
