# phase2-scene-styling

## Why

Phase 2 §9 and §10 of `docs/requirements.md` ask for four styling primitives
that ride on top of the §8 title primitive: tab accent color, per-pane window
background color, OS-window font size, and OS-window transparency. The h22
explore and §8 promotion proved the noun-first CLI shape works; the h23 probe
(`tmp/h23-styling/run.py`) has now grounded all four primitives against a live
kitty 0.46.2 — every wire-level claim in the design below is empirically
verified, including the kitten quirks (`--toggle` argv ordering, float-storage
precision, no programmatic font-size observable).

The probe also surfaced one structural truth: kitty's architecture binds
**font size** and **opacity** to the OS window, not the sub-window (pane).
This is the kitten verb help speaking, not a 0.46.x bug: "in kitty all
sub-windows in the same OS window must have the same font size" and "the
background opacity affects all kitty windows in a single OS window." The CLI
surface reflects that truth via honest noun-scope naming (`window` vs
`os-window`), so users learn the model from the command rather than from a
surprise.

## What Changes

- New `my-kitty tab accent <color>` subcommand: sets tab `active_bg` AND
  `inactive_bg` to the same color in one call, so the role is visible focused
  AND unfocused (the load-bearing PRD §9 requirement). Color grammar matches
  kitten: named (`blue`), hex (`#0066cc`), or `NONE` (reset). Optional
  `--active-fg <color>` and `--inactive-fg <color>` for power users who need
  contrast overrides.
- New `my-kitty window background <color>` subcommand: per-pane background
  via `kitten @ set-colors --match`. Same color grammar (named/hex/NONE
  implied via `--reset`). Per-pane isolation is empirically verified
  (probe assertion: pane A bg = #001a33, pane B bg = #000000 after a single
  matched call).
- New `my-kitty os-window font-size <value>` subcommand: OS-window-scoped
  font size via `kitten @ set-font-size`. Accepts kitten's full grammar —
  absolute (`14`), relative (`+2`, `-2`, `*1.1`, `/2`), reset (`0`). Optional
  `--all` flag exposes kitten's "apply to current AND future OS windows"
  semantics (a state change, not a one-shot — documented in --help).
- New `my-kitty os-window opacity <value>` subcommand: OS-window-scoped
  transparency via `kitten @ set-background-opacity`. Range `0.0–1.0`.
  Optional `--toggle` flag exposes kitten's "reset to default if equal,
  else set" toggle (chord-friendly for §14). Implementation MUST construct
  the kitten argv with `--toggle` BEFORE the positional value — kitten
  parses positional-first and errors out otherwise (probe-grounded).
- New install-time payload `config/kitty/dynamic-opacity.conf` shipping
  the single directive `dynamic_background_opacity yes`. Required by
  `set-background-opacity`; included from `kitty-setup.conf` via the same
  surgical contract as `remote-control.conf` and `monitor.conf`. Adding the
  directive is visually transparent (kitty's default opacity stays at 1.0
  when the directive is on but no opacity command runs).
- New scenes modules: `src/kitty_setup/scenes/accent.py`,
  `background.py`, `font.py`, `opacity.py` — each thin, each delegating to
  `_client.kitten_at()` from the existing `scenes/_client.py`.
- Refactor scope: none. `scenes/_client.py` is sufficient as-is; no
  doctor-helper extraction.
- Hypothesis scratch: `tmp/h23-styling/run.py` already green; promoted to
  integration tests during apply and deleted before archive (same contract
  as h22).

Not in scope:
- §11 (extra layout orientation) — separate change.
- §12-§14 (scene composition, named presets, chord wiring) — separate
  changes. This change's CLI surface is the foundation §13 will compose.
- Per-pane font / per-pane opacity — kitty architecture forbids it; the
  honest naming surfaces that fact.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities

- `kitty-scenes`: extends with 4 new primitive requirements (tab-accent,
  window-background, os-window font-size, os-window opacity), an updated
  "scenes package layout" requirement enumerating the new modules, AND a
  new "managed payload ships `dynamic-opacity.conf`" requirement for the
  install-time precondition (parallel to how `kitty-remote-control` owns
  `remote-control.conf`).
- `my-kitty-cli`: extends the "Single binary on PATH with subcommand
  dispatch" requirement to include the new `os-window` top-level
  subcommand and the new `accent` / `background` nested verbs under
  existing `tab` / `window`. `tab` and `window` themselves already exist
  from `phase2-scene-title-primitive`.

No `kitty-install` or `kitty-config-management` delta needed — the
generic "Payload lives under our own subdirectory" requirement in
`kitty-config-management` already covers any per-topic `*.conf` we add
under `~/.config/kitty/kitty-setup/`. No new doctor check; the existing
`parse check` validates the new directive parses.

## Impact

- Code: `src/kitty_setup/scenes/{accent.py, background.py, font.py,
  opacity.py}` (new); `src/kitty_setup/cli.py` (new subparsers for `tab
  accent`, `window background`, `os-window` noun + `font-size` / `opacity`
  verbs).
- Config payload: `config/kitty/dynamic-opacity.conf` (new);
  `config/kitty/kitty-setup.conf` (+ `include dynamic-opacity.conf` line).
- Tests: `tests/unit/test_scenes_{accent,background,font,opacity}.py`
  (new, ~4 tests each = ~16 unit tests); `tests/integration/test_h23_styling.py`
  (new, raw-subprocess pattern, covering the probe's 23 assertions);
  `tests/unit/test_cli.py` (extended: 4 new routing tests + help-banner
  assertion for `os-window`).
- Hypothesis scratch: `tmp/h23-styling/` (already exists, green; deleted at
  archive).
- Docs: `docs/repro/h23-styling.md` (new manual repro covering visual
  outcomes the integration tests can't auto-verify — tab-bar accent
  visibility, font-size visible change, opacity visible change).
- Dependencies: none added. All four primitives shell out to the same
  `kitten` binary the existing scenes already use.
- Runtime surface: 4 new subcommands. The new `os-window` noun expands the
  top-level subcommand set by exactly one.
- Risk: low-medium. The wire format is empirically grounded; the install-
  time payload follows the established surgical pattern; the kitten
  quirks (--toggle ordering, float precision) are captured in the design
  and tasks. The "per-pane font/opacity is impossible" architecture is
  surfaced via naming, not buried.
