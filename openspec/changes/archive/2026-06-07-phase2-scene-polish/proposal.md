## Why

Four rough edges surfaced while dogfooding the scenes layer after
`phase2-friendly-color-input` shipped:

1. **No color autocomplete.** Scene names tab-complete (`scene_name_completer`),
   but the color arguments (`tab accent <color>`, `window background <color>`,
   `--tab-accent`) do not — the user has to remember names from a 667-entry
   table with no shell help.
2. **Multi-pane scenes corrupt a populated tab.** `launch_scene` fills the
   *current* tab whenever it runs inside kitty (`$KITTY_WINDOW_ID` set),
   checking only "am I inside kitty?" — never "does the current tab hold exactly
   one window?". Launching a 3-pane scene from a tab that already has 2 windows
   yields **4 windows in one tab** instead of a clean new tab.
3. **Example scenes are never seeded.** The recipe loader reads
   `~/.config/kitty-setup/scenes/`, and every example `.toml` tells the user to
   `cp` files there by hand. Nothing in the install path does it; the only
   reason any scenes exist on this host is a manual copy from a prior session.
   `examples/scenes/` is not even packaged into the wheel.
4. **Alpha in a color value is rejected with a confusing message.** A user who
   types `bg=#001f3faa` (hex with opacity) gets "not a recognized color — use a
   hex like #0a7", because `normalize_color` only matches 3/6-digit hex. Probes
   (`tmp/h26-perpane-opacity/`) proved kitty opacity is **OS-window scope only**
   — not per-pane, not per-tab — so a per-pane alpha cannot become a per-pane
   translucency. The friendly behavior is to accept the alpha and **strip it**
   (use the solid color), keeping opacity as its own explicit OS-window gesture.

These are independent polish items but share one surface (scenes + install) and
one review, so they ship as one change.

## What Changes

- **Color autocomplete (kitty-scenes):** a `color_completer` (mirroring
  `scene_name_completer`) wired onto the `tab accent` / `window background`
  positional `<color>` and `--tab-accent`, completing color **names** (plus
  `NONE`). Hex is not enumerable; the `bg=` inside an inline `--pane 'k=v,…'`
  token is a single opaque arg and is **out of scope** for completion (stated as
  a known limit).
- **Fill-current-tab only when solo (kitty-scenes):** `launch_scene` gains an
  `_origin_tab_is_solo` check via `kitten @ ls` — the current tab is reused
  **only** when it holds exactly one window (the origin). Otherwise the scene
  opens a new tab (the existing out-of-kitty path). Fail-safe: if `ls` fails or
  the origin window is not found, treat as *not solo* (open a new tab) — never
  disturb a populated tab.
- **Seed example scenes on install (kitty-install):** `examples/scenes/*.toml`
  is packaged as data and `my-kitty install` copies each into
  `~/.config/kitty-setup/scenes/` **only if that filename is absent**
  (copy-if-absent) — never overwriting a user edit. Uninstall continues to leave
  the scenes directory untouched (it is user data, outside the managed payload).
  The bootstrap `tools/setup.sh` line that does this in bash is removed (logic
  belongs in the `my-kitty` subcommand, per the stack rule).
- **Accept + strip alpha (kitty-scenes):** `normalize_color` additionally
  accepts 4-digit (`#rgba`) and 8-digit (`#rrggbbaa`) hex, **drops the alpha**,
  and returns the solid `#rgb` / `#rrggbb`. It never errors on a well-formed
  alpha hex. Opacity remains the explicit, OS-window-scoped
  `my-kitty os-window opacity` command (unchanged).

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `kitty-scenes`: (a) color arguments gain shell autocomplete of color names;
  (b) the in-kitty fill-current-tab behavior is narrowed to "current tab holds
  exactly one window"; (c) `normalize_color` accepts and strips alpha
  (4/8-digit hex) instead of rejecting it.
- `kitty-install`: `my-kitty install` seeds packaged example scenes into the
  user scenes directory copy-if-absent, never overwriting; uninstall still does
  not touch user scenes.

## Impact

- **Code:** `scenes/colors.py` (`_HEX_RE` + alpha strip), `scenes/launcher.py`
  (`_origin_tab_is_solo` + condition), `scenes/recipe.py` or a new completer
  module (`color_completer`), `cli.py` (wire completer), `installer.py`
  (`seed_scenes`), `pyproject.toml` (package `examples/scenes` as data),
  `tools/setup.sh` (remove the manual `cp`).
- **Tests:** unit (alpha strip, completer, solo-tab predicate, seed-if-absent);
  integration gated by `KITTI_INTEGRATION=1` (4-window regression, seed copy).
- **Probes:** `tmp/h26-perpane-opacity/` (opacity scope) → promote the verdict
  into a repro doc.
- **Dependencies:** none new. PIL is still generation-time only; no runtime add.
- **Docs:** `docs/repro/` gains the opacity-scope finding; example `.toml`
  comments updated (no longer "cp by hand").
