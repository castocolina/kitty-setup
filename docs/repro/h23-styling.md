# H23 — Styling primitives: tab accent, window background, OS-window font + opacity

**Capability:** kitty-scenes (Phase 2 §9 + §10).

**Status:** Promoted. Implementation in
[`src/kitty_setup/scenes/`](../../src/kitty_setup/scenes/) (`accent.py`,
`background.py`, `font.py`, `opacity.py`, sharing `_client.py` with `title.py`
from h22). CLI surface: `my-kitty tab accent <color>`,
`my-kitty window background <color>`, `my-kitty os-window font-size <value>`,
`my-kitty os-window opacity <value>`.

Autonomous integration tests under
[`tests/integration/test_h23_styling.py`](../../tests/integration/test_h23_styling.py)
replicate the 23 assertions captured in the h23 hypothesis probe; unit tests
under `tests/unit/test_scenes_{accent,background,font,opacity}.py` lock in
the kitten-argv invariants (especially the `--toggle` flag-before-positional
rule for opacity).

## Why

Phase 2 §9 of `docs/requirements.md` asks for tab accent color so a tab's role
is identifiable at a glance, focused or not. Phase 2 §10 asks for window
background, font, and transparency. Both extend h22's first scene primitive
(`title`) with the same socket-discovery + `kitten @` plumbing.

The wire-level questions ("does kitten accept named + hex colors?", "is
opacity reflected in `ls`?", "what error does kitten emit when
`dynamic_background_opacity` is off?") were answered by `tmp/h23-styling/run.py`
before this change shipped — 23 assertions, all green against kitty 0.46.2 on
the user's daily host. Two kitten quirks the probe surfaced and the
implementation now defends against:

- `set-background-opacity --toggle <value>` requires the flag **BEFORE** the
  positional value. Reverse order fails with `"Must specify exactly 1
  argument(s)"`.
- kitty stores opacity as a float32-ish value, so `0.7` round-trips as
  `0.699999988…` in `kitten @ ls`. Any code comparing opacity must use
  tolerance, not equality.

A structural truth the probe also surfaced: kitty's architecture binds **font
size** and **opacity** to the OS window, not the sub-window (pane). The CLI
surface honours this by introducing a dedicated `os-window` noun.

## Manual repro

Pre-reqs: `make install` has been run (so `~/.local/kitty.app/bin/kitten`
and `my-kitty` are on PATH; managed `dynamic-opacity.conf` shipped). All
scenarios run from inside a kitty window unless noted.

### 1. Tab accent — named, hex, NONE, focused AND unfocused visible

```bash
my-kitty tab accent blue           # X11 rgb.txt → #0000ff
# Click into another tab to defocus; the accent should still be blue.
my-kitty tab accent "#0066cc"
my-kitty tab accent NONE           # reset to kitty default
```

Expected: the tab's accent color visibly changes on each call. Crucially,
the colored tab remains identifiable when it is **not** focused (the
load-bearing PRD §9 invariant — accent applies to both `active_bg` and
`inactive_bg`). Click another tab to confirm.

### 2. Tab accent — invalid color is rejected loudly

```bash
my-kitty tab accent notacolor
echo "exit: $?"
```

Expected: non-zero exit, stderr contains
`Error: notacolor is not a valid color`. The tab is unchanged.

### 3. Window background — per-pane isolation

Inside a tab with at least two panes (open a second via the windowing
chord, e.g. `ctrl+shift+enter`):

```bash
# From pane A:
my-kitty window background "#001a33"
# From pane B (or use --match to target it explicitly):
my-kitty window background "#330000" --match recent:1
```

Expected: pane A is dark blue, pane B is dark red. Other panes (including
those in other tabs) are untouched.

### 4. OS-window font-size — absolute, relative, reset

```bash
my-kitty os-window font-size 14
my-kitty os-window font-size +2
my-kitty os-window font-size -2
my-kitty os-window font-size 0     # reset to configured default
```

Expected: every pane in the active OS window re-renders at the new size on
each call. `kitten @ ls` does **not** expose font_size — visual outcome is
the only observable. To zoom one OS window but not others, no `--all` flag
needed (default scope is the active OS window).

### 5. OS-window opacity — set, toggle, default

```bash
my-kitty os-window opacity 0.7      # window becomes 70% opaque
my-kitty os-window opacity 0.7 --toggle   # reset to default (1.0)
my-kitty os-window opacity 0.5
```

Expected: the OS window's background goes translucent on the first call,
back to fully opaque on the toggle, then translucent again at 0.5.

### 6. Opacity without `dynamic_background_opacity yes` — clear error

This scenario requires running kitty against a config that does NOT contain
the `dynamic_background_opacity yes` directive. The managed payload
**always** ships it (`config/kitty/dynamic-opacity.conf`), so this is mostly
a sanity check that the error message would survive if a user removed the
include line. Skip unless investigating.

```bash
my-kitty os-window opacity 0.5     # against a kitty without the directive
echo "exit: $?"
```

Expected (when the directive is missing): non-zero exit, stderr contains
`You must turn on the dynamic_background_opacity option in kitty.conf`.

### 7. `--match` selectors for all primitives

Every primitive that targets a sub-window or tab accepts `--match`:

```bash
my-kitty tab accent red --match recent:0
my-kitty window background "#002211" --match id:5
my-kitty os-window font-size 16 --to unix:/tmp/kitty-12345   # explicit socket
```

Expected: each call mutates exactly the matched target. With `--to`, no
auto-discovery happens (useful when running outside kitty or with multiple
kitties).

## Linux Status

**verified (2026-05-17, Pop!_OS 24.04 + COSMIC + kitty 0.46.2)** — all 7
manual repro scenarios above (tab accent named/hex/NONE + focused-and-unfocused
visibility, invalid-color rejection with clear stderr, per-pane background
isolation, OS-window font-size absolute/relative/reset, OS-window opacity
set/toggle/reset, opacity-without-directive error, `--match` and `--to`
selectors) signed off by the user. Autonomous integration tests under
`tests/integration/test_h23_styling.py` are green
(`KITTI_INTEGRATION=1 pytest tests/integration/test_h23_styling.py` →
8 passed).

## macOS Status

**deferred-with-reason** — no Mac host available. The `kitten @` protocol is
platform-agnostic, so the wire-level behaviour is expected to be identical.
Three risk areas to verify on a Mac when one is available: (a) tab-bar
accent rendering may differ depending on macOS's tab-bar drawing path,
(b) opacity composition is mediated by the macOS window server rather than
the compositor, so visual fidelity may differ, (c) font-size step granularity
is not user-visible but the visual outcome is. Tracked under follow-up
change `phase2-scene-styling-macos`.

## Attempted alternatives

| Date       | Approach considered                                                | Outcome   |
| ---------- | ------------------------------------------------------------------ | --------- |
| 2026-05-16 | Hide OS-window scope under `window` (`my-kitty window font 14` applies to all panes) | ❌ rejected: lies about what the command does. A future reader asking "why does `window` affect all panes?" gets no clean answer. |
| 2026-05-16 | `--os-window` flag on `window font` / `window opacity` instead of a new noun | ❌ rejected: makes per-pane the default and OS-window the opt-in, which inverts kitty's actual model (font/opacity ARE OS-window only). |
| 2026-05-16 | Drop opacity entirely (ship only 3 primitives)                     | ❌ rejected: half-addresses §10 and leaves the `dynamic_background_opacity` precondition work for a follow-up. The explore picked Option B: cover both §9 and §10 fully. |
| 2026-05-16 | Validate color strings client-side                                 | ❌ rejected: kitten owns the color grammar (X11 rgb.txt + hex + NONE). Client-side validation would drift from kitten's true acceptance set on every kitty release. Pass through verbatim, propagate kitten's errors verbatim. |
| 2026-05-16 | Bake `dynamic_background_opacity yes` directly into `kitty-setup.conf` (no separate `dynamic-opacity.conf`) | ❌ rejected: breaks the one-payload-file-per-concern pattern that `monitor.conf` and `remote-control.conf` established. Removing opacity support would require editing the umbrella file instead of dropping a single managed file. |

## Recipes

### Role-based tab colors

```bash
# Curated palette: green for dev, red for prod, blue for staging.
alias kt-dev='my-kitty tab accent "#22cc66"'
alias kt-stg='my-kitty tab accent "#3388dd"'
alias kt-prod='my-kitty tab accent "#cc3344"'

# Or composed with title (h22):
prod-tab() {
  my-kitty tab title "🔴 prod $1"
  my-kitty tab accent "#cc3344"
}
prod-tab "us-east-1"
```

### Opacity toggle bound to a shell alias

```bash
# Soft-focus mode: bring opacity down for reading, full back for work.
alias dim='my-kitty os-window opacity 0.7'
alias bright='my-kitty os-window opacity 1.0'
# Or a single toggle that flips between dim and default:
alias dim-toggle='my-kitty os-window opacity 0.7 --toggle'
```

### Font zoom for screen-share

```bash
# Pair with a hotkey in your shell or a kitty key map (Phase 2 §14):
alias zoom-in='my-kitty os-window font-size +2'
alias zoom-out='my-kitty os-window font-size -2'
alias zoom-reset='my-kitty os-window font-size 0'
```

### Compose primitives into a one-shot "scene" function

(A preview of Phase 2 §13 named scenes; until §13 ships, do it by hand.)

```bash
scene-prod() {
  my-kitty tab title "🔴 prod"
  my-kitty tab accent "#cc3344"
  my-kitty window background "#1a0000"
  my-kitty os-window opacity 0.95
}
scene-prod
```

When you find yourself invoking the same compose function from a chord,
that is the cue to promote it to a §13 named scene — chord-to-scene wiring
is §14's problem and reads the named scene as one unit.

## Known limitations

- **Per-pane font-size is kitty-architecturally impossible.** `kitten @
  set-font-size --help`: "in kitty all sub-windows in the same OS window
  must have the same font size." This is why the noun is `os-window`, not
  `window`. The honest naming surfaces the constraint without burying it.
- **Per-pane opacity is kitty-architecturally impossible.** Same reason —
  `kitten @ set-background-opacity --help`: "the background opacity affects
  all kitty windows in a single OS window." Surfaced via the `os-window`
  noun.
- **`kitten @ ls` does NOT expose font-size.** The visual outcome is the
  only observable; integration tests can only assert kitten's exit code,
  not the rendered font size. This is also why §7.2 above carries explicit
  user-visible repro for font-size.
- **`set-tab-color` reverts on kitty restart.** The kitten verb is a
  runtime state mutation, not a persisted config write. If the user closes
  the OS window or restarts kitty, the tab accent reverts to the kitty
  defaults declared in their config. Phase 2 §13 (named scenes) will
  re-apply primitives on load to solve persistence; until then, the runtime
  primitives are session-local.
- **Float-precision in opacity round-trip.** `kitten @ set-background-opacity
  0.7` stores the value as `0.699999988079071`. Anything comparing opacity
  must use tolerance; the integration test uses `abs(actual - expected) <
  0.01`. Codified in `phase2-scene-styling/design.md` D4 so future opacity
  primitives inherit the convention.
- **`--toggle` argv ordering quirk.** Implementation MUST place `--toggle`
  before the positional value, otherwise kitten fails with
  `"Must specify exactly 1 argument(s)"`. Defended by
  `tests/unit/test_scenes_opacity.py::test_set_os_window_opacity_toggle_argv_ordering`.

## Follow-ups

- `phase2-scene-styling-macos`: manual verification of all 7 scenarios on
  a Mac host (kitten protocol is platform-agnostic but visual rendering
  may differ).
- Phase 2 §11 (extra layouts), §13 (named scenes), §14 (chord-to-scene
  wiring). Each is a separate change. This change's CLI surface is the
  foundation §13 will compose.
