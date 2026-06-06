# Friendly color input — names, hashless hex, reject-before-launch

**Capability:** kitty-scenes (Phase 2). Change: `phase2-friendly-color-input`.

**Status:** Promoted. Normalizer in
[`src/kitty_setup/scenes/colors.py`](../../src/kitty_setup/scenes/colors.py)
(`normalize_color`, `ColorError`) over the baked table
[`_color_table.py`](../../src/kitty_setup/scenes/_color_table.py). Wired into
`accent.py`, `background.py`, and `launcher.launch_scene` (the central choke
point for both inline and named scenes). Unit tests:
[`tests/unit/test_scenes_colors.py`](../../tests/unit/test_scenes_colors.py);
e2e: [`tests/integration/test_color_normalization_e2e.py`](../../tests/integration/test_color_normalization_e2e.py).

## Why

Every color used to be passed **raw** to `kitten @`, so (verified on kitty
0.47.1): kitty rejects standard names it lacks (`teal`, `olive`, `lime`,
`aqua`, `silver`, `fuchsia`, `indigo`, `crimson`), and it rejects hex without a
leading `#` (`fff`, `000`). And a bad color in a multi-pane scene was only caught
*after* the first window opened — a half-built scene. `my-kitty` now normalizes
every color client-side first:

- **hashless hex** → `#` added (`fff` → `#fff`),
- **full X11/CSS name** → its hex (`teal` → `#008080`),
- **`NONE` / `rgb:` / `rgb()`** → passthrough,
- **unrecognized** → `ColorError`, rejected before any `kitten @` call.

The name table is built **X11 `rgb.txt` first (precedence), then CSS/SVG fills
only the names X11 lacks** (+ `rebeccapurple`). "X11" here is a color-name
*database* (a data file), not the X11 display server — the table is OS- and
windowing-system-independent (Wayland / X11 / macOS render a `#rrggbb`
identically; kitty's color parser is the same cross-platform code). Because X11
wins for any name in both tables, a name kitty already knows maps to the
**identical** hex kitty would produce — no `green`/`gray`/`purple`/`maroon`
tone collision.

## Manual repro

```bash
make install   # ship the updated my-kitty

# 1) a name kitty natively rejects now works (translated to #008080):
my-kitty window background teal
kitten @ get-colors | grep '^background'        # -> background  #008080

# 2) hashless hex just works:
my-kitty window background 001a33               # no '#'
my-kitty tab accent orange                      # name, exits 0

# 3) reject before any window opens — a scene with a bad color builds nothing:
mkdir -p ~/.config/kitty-setup/scenes
printf 'layout="tall"\n[[pane]]\ntitle="ok"\n\n[[pane]]\ntitle="x"\nbg="notacolor"\n' \
  > ~/.config/kitty-setup/scenes/bad.toml
my-kitty scene launch bad
#   -> exits non-zero, stderr: 'notacolor' is not a recognized color — use a
#      hex like '#0a7' / '0a7' or a color name like 'teal'
#   -> NO new tab/window opened.
```

## Linux Status

`verified (2026-06-06, Pop!_OS 24.04 + COSMIC + kitty 0.47.1)`.

- e2e `tests/integration/test_color_normalization_e2e.py` (3 cases) green under
  `KITTI_INTEGRATION=1`: `teal` → `#008080`, `001a33` → `#001a33`, and a scene
  with a bad color leaves the tab count unchanged (no window opened).
- **Superset + no-regression sweep** (task 1.3): all **667** table names were
  driven through `kitten @ set-colors` against a live kitty. Result:
  `kitty_accepts=658, gap_filled=9, mismatches=0` — i.e. kitty's native set is a
  subset of the table, every name kitty accepts renders the **identical** hex
  the table holds (zero tone regression), and the 9 names kitty rejects
  (`teal`/`olive`/`lime`/`aqua`/`silver`/`fuchsia`/`indigo`/`crimson` +
  `rebeccapurple`) are exactly the gap the table fills.
- 42-case unit suite `tests/unit/test_scenes_colors.py` covers hashless hex,
  name translation, collision-free known names, sentinels, empty→absent,
  unknown→error, and per-site rejection (no kitten call on a bad color).

No new `tmp/hNN` wire probe: the transform is deterministic value→value; the
kitten wire format is unchanged (kitty always receives `background=#rrggbb`).

## macOS Status

`deferred-with-reason` — no Mac host available. `normalize_color` is pure Python
`str → str` with no OS or display-server dependency, and the name table is a data
file independent of the windowing system; kitty's color parser and `#rrggbb`
rendering are identical across platforms. The unit suite covers 100% of the
logic host-independently; macOS would behave identically.

## Attempted alternatives

| Approach | Status | Why rejected |
|---|---|---|
| Pass colors raw, let kitten validate | Rejected | The prior contract; it's exactly what leaves `teal`/`fff` broken and half-builds a scene on a bad color. |
| Translate ALL names to CSS hex | Rejected | CSS `green`=#008000 ≠ kitty's X11 `green`=#00ff00 — a silent tone regression for names that already worked. X11-precedence avoids it. |
| Bake only the CSS4 table | Rejected | Misses kitty-native extras (`grayN`, X11-only names) → would wrongly reject names that work today. X11 base + CSS gap-fill is a superset. |
| Ask kitty to validate each color (pre-flight `set-colors`) | Rejected | A kitten round-trip per color; the baked superset table validates offline with no socket. |
| Add a color library (matplotlib/webcolors) | Rejected | Zero-dependency rule; the table is a static generated literal. |

## Known limitations

- **`rgb:` / `rgb()` / `rgba()` forms pass through unvalidated.** They reach
  kitty as-is, so an invalid functional color is still only caught by kitty
  (possibly after a window opens). Hex and names are validated up front.
- **Table is a snapshot.** Sourced from this host's X11 `rgb.txt` + CSS/SVG; a
  future kitty that adds a brand-new name outside the table would have that name
  rejected by `my-kitty`. The 1.3 sweep is the guard; re-run it if kitty's table
  changes. Low risk (the X11/CSS set is stable).
- **`NONE` is the only reset spelling normalized** (`none` → `NONE`); other
  reset spellings are not invented.
