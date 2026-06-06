## Why

Every color a user can set today — scene `bg` / `tab_accent` (TOML **and** inline
`--pane`), plus the single-noun `my-kitty tab accent <color>` and `my-kitty
window background <color>` commands — is passed **raw** to `kitten @`. The
`phase2-scene-styling` spec made that explicit: *"The wrapper MUST NOT validate
the color string client-side; an invalid color is rejected by kitten."* Two
papercuts fall out of that decision, both verified empirically against the
user's kitty (0.47.1):

1. **kitty's named-color table is a narrow subset of CSS/X11.** `yellow`,
   `blue`, `navy`, `orange`, `gray50` work, but `teal`, `olive`, `lime`, `aqua`,
   `indigo`, `crimson` are **rejected** — even though they are standard X11/CSS
   names. The user reasonably expects "named colors" to mean the *whole* common
   palette, not kitty's gaps.
2. **kitty requires a leading `#` on hex.** `#fff` and `#000` work; the bare
   `fff` / `000` / `ffffff` a casual user types are **rejected**. The user's own
   words: *"apenas me sé que puedo establecer con fff, negro 000 y tonos de
   gris — debe ser amigable."*

And because validation only happens inside kitty, a bad color in a multi-pane
scene is caught **after** the first window/tab is already open — a half-built
scene, not a clean rejection.

## What Changes

A single client-side **color normalization layer** in `my-kitty`, applied to
**every** color input before any `kitten @` call:

- **Hashless hex is accepted** — `fff` → `#fff`, `000` → `#000`, `1a2b3c` →
  `#1a2b3c`. 3- and 6-digit, case-insensitive. (kitty already accepts the `#`
  form; we add the leading `#` so the bare form the user types just works.)
- **The full X11/CSS named-color set is accepted** — names kitty lacks (`teal`,
  `olive`, `lime`, `aqua`, `indigo`, `crimson`, …) are **translated to their hex
  value** before the kitten call, so they render correctly. The translation
  table is built **X11 `rgb.txt` first (precedence)** — the lineage kitty's own
  table descends from — **then CSS/SVG fills only the names X11 lacks** (the
  classic X11 set predates the SVG additions, so it is missing exactly the names
  kitty also rejects: `teal`, `olive`, `lime`, `aqua`, `silver`, `fuchsia`,
  `indigo`, `crimson`), plus `rebeccapurple`. Because X11 wins for any name in
  both, a name kitty already knows translates to the **identical** hex kitty
  would have used — so there is **no tone change / no collision** for `green`,
  `gray`, `purple`, `maroon`. ("X11" here is a color-name *database*, not the
  display server — the table is OS/windowing-system independent.) For names
  kitty already defines, the visual result
  is therefore a no-op — exactly the user's ask: *"si kitty ya lo define, no
  hacemos nada."*
- **Unknown colors are rejected up-front, before any window/tab opens.** A value
  that is neither valid hex nor a recognized name raises a clear client-side
  error (e.g. `'foo' is not a recognized color — use a hex like '#0a7' / '0a7'
  or a name like 'teal'`). For a scene, **all** colors are validated before the
  first `kitten @ launch`, so a typo never leaves a half-built scene behind.
- **`gray`/`grey` both spellings work** (already true in kitty; preserved).
- **Empty string still normalizes to absent** (`None`), unchanged from
  `parse_pane_spec` / the recipe loader.

This **reverses** the `phase2-scene-styling` decision "MUST NOT validate
client-side" — that requirement is replaced. The new contract is "normalize and
pre-validate client-side; pass kitty a value it always accepts."

A new shared module `src/kitty_setup/scenes/colors.py` holds
`normalize_color(value) -> str` (raising a typed `ColorError`) and the baked
name→hex table. It is called from `recipe.py` (TOML `bg`/`tab_accent`),
`launcher.py` (inline `--pane bg` / `--tab-accent`), `accent.py`
(`tab accent` + `--active-fg`/`--inactive-fg`), and `background.py`
(`window background`). Zero new dependencies (the table is a static literal;
`tomllib`/stdlib only).

No `kitten @` wire-format change: kitty still receives `background=#rrggbb` /
`active_bg=<value>`. No managed-payload change, no new doctor check. The
translation is deterministic (value → value), so — like the recipe loader — it
needs **no new `tmp/hNN` wire probe**; it is covered by unit tests plus one
integration test proving a previously-rejected name (`teal`) now applies.

## Capabilities

### New Capabilities

None. Color normalization is a front-end onto the existing `kitty-scenes` color
inputs; it adds/modifies Requirements on that capability rather than introducing
a new one.

### Modified Capabilities

- `kitty-scenes`: **MODIFY** the tab-accent and window-background Requirements
  (and the scene launcher composition Requirement) so that color values are
  normalized client-side — hashless hex accepted, full X11/CSS names translated
  to hex, unknown values rejected **before** any kitten call — replacing the
  prior "wrapper MUST NOT validate the color string client-side" clause. **ADD**
  a Requirement "Color inputs are normalized and validated by `my-kitty`"
  describing the shared `colors.py` contract, and the repro-doc Requirement.

## Impact

- **Affected code (new):**
  - `src/kitty_setup/scenes/colors.py` — `normalize_color()`, `ColorError`, the
    baked X11(+rebeccapurple) name→hex table (likely a generated
    `_color_table.py` data module).
  - `tests/unit/test_scenes_colors.py` — hashless-hex, name translation,
    gap names (teal/olive/lime/…), collision-free known names, unknown→error,
    case-insensitivity, empty→None.
  - `tests/integration/test_color_normalization_e2e.py` — one e2e
    (`KITTI_INTEGRATION=1`) proving `teal` (a name kitty natively rejects) now
    applies as `#008080`, and a scene with a bad color opens **no** window.
  - `docs/repro/friendly-color-input.md` — repro doc (Why, Manual repro, Linux
    Status, macOS Status, Attempted alternatives, Known limitations).
- **Affected code (modified):**
  - `src/kitty_setup/scenes/recipe.py` — normalize `bg`/`tab_accent` in
    `load_scene` (before returning Panes; raise → `SceneRecipeError`).
  - `src/kitty_setup/scenes/launcher.py` — normalize inline `--pane bg` /
    `--tab-accent`; pre-validate all scene colors before the first launch.
  - `src/kitty_setup/scenes/accent.py` — normalize `<color>` /
    `--active-fg` / `--inactive-fg`.
  - `src/kitty_setup/scenes/background.py` — normalize `<color>`.
  - `src/kitty_setup/scenes/__init__.py` — export `colors`.
- **Out of scope (explicit):**
  - `NONE` / reset sentinels and `rgb:`/`rgba()` functional syntax — passthrough
    unchanged if kitty accepts them; not part of the friendly layer for v1.
  - Foreground/theme colors outside the listed commands.
  - macOS visual verification — deferred-with-reason (the value normalization is
    platform-agnostic; the `kitten @` protocol is unchanged).
- **Dependencies:** none added.
- **Performance:** one dict lookup + a regex per color; negligible.
