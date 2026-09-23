# Delta: kitty-scenes

## ADDED Requirements

### Requirement: Tab-accent scene primitive ships under `my-kitty tab accent`

The system SHALL expose a `my-kitty tab accent <color>` subcommand that
sets a kitty tab's accent color so the tab is visibly distinguishable
both when focused and when unfocused (the load-bearing PRD §9 invariant).
Implementation SHALL invoke `kitten @ set-tab-color` with BOTH
`active_bg=<color>` AND `inactive_bg=<color>` keys in the same call, so a
single user-supplied color satisfies the focused-and-unfocused
requirement without any auto-derivation logic.

The `<color>` positional argument accepts kitty's full color grammar:
- a named color from kitty's named-color table (e.g. `blue`, `darkblue`,
  `forestgreen`),
- a hex string of the form `#rrggbb` (e.g. `#0066cc`),
- the keyword `NONE` to reset the tab's accent to kitty's configured
  default.

The subcommand SHALL accept the following options:
- `--active-fg <color>` — override the foreground when the tab is focused.
  Passed to kitten as `active_fg=<color>`.
- `--inactive-fg <color>` — override the foreground when the tab is
  unfocused. Passed to kitten as `inactive_fg=<color>`.
- `--match <expression>` — kitty match expression passed through to
  `kitten @ --match`. When omitted, the default tab selector is the
  active tab.
- `--to unix:<path>` — explicit remote-control socket path, bypassing
  auto-discovery.

The wrapper MUST NOT validate the color string client-side; an invalid
color (probe-grounded example: `notacolor`) is rejected by kitten with
`"Error: notacolor is not a valid color"`. The wrapper SHALL propagate
kitten's stderr verbatim and exit with kitten's exit code.

#### Scenario: Setting tab accent with a hex color
- **WHEN** the user runs `my-kitty tab accent "#0066cc"` from inside a kitty window where `$KITTY_LISTEN_ON` is set
- **THEN** the kitten invocation includes both `active_bg=#0066cc` and `inactive_bg=#0066cc`, the subcommand exits 0, and the tab visibly carries the color whether focused or not

#### Scenario: Setting tab accent with a named color
- **WHEN** the user runs `my-kitty tab accent darkblue` from inside a kitty window
- **THEN** the subcommand exits 0 (kitten accepts the name; X11 rgb.txt convention applies)

#### Scenario: Resetting tab accent to default
- **WHEN** the user runs `my-kitty tab accent NONE`
- **THEN** the subcommand exits 0 and the tab's accent reverts to whatever the kitty config defined for `active_tab_*` / `inactive_tab_*`

#### Scenario: Invalid color is rejected with kitten's error message
- **WHEN** the user runs `my-kitty tab accent notacolor`
- **THEN** the subcommand exits non-zero, stderr contains the substring `"is not a valid color"`, and no tab state has changed

#### Scenario: --active-fg and --inactive-fg flags pass through to kitten keys
- **WHEN** the user runs `my-kitty tab accent "#0066cc" --active-fg white --inactive-fg "#cccccc"`
- **THEN** the kitten invocation includes `active_bg=#0066cc`, `inactive_bg=#0066cc`, `active_fg=white`, and `inactive_fg=#cccccc`

### Requirement: Window-background scene primitive ships under `my-kitty window background`

The system SHALL expose a `my-kitty window background <color>`
subcommand that sets the background color of a kitty pane (a kitty
"window") via `kitten @ set-colors background=<color> --match <expr>`.
The default selector is the active window; the change SHALL be scoped to
the matched pane only and SHALL NOT affect other panes in the same tab
(probe-grounded: pane A bg = `#001a33`, pane B bg = `#000000` after a
single matched call).

The `<color>` positional argument accepts the same color grammar as
`tab accent` (named, hex, or `NONE`).

The subcommand SHALL accept `--match <expression>` and
`--to unix:<path>` with the same semantics as the other scene
primitives.

#### Scenario: Setting background on the active window
- **WHEN** the user runs `my-kitty window background "#001a33"` from inside a kitty pane
- **THEN** `kitten @ get-colors` for that pane reports `background #001a33`, the subcommand exits 0, and no other pane's background changed

#### Scenario: Per-pane isolation
- **WHEN** the user has 2 panes (id 1 and id 2) and runs `my-kitty window background "#001a33" --match id:1`
- **THEN** `kitten @ get-colors --match id:1` reports `background #001a33`, AND `kitten @ get-colors --match id:2` reports the unchanged default `background #000000`

#### Scenario: Named color resolves via kitty's named-color table
- **WHEN** the user runs `my-kitty window background darkblue`
- **THEN** `kitten @ get-colors` reports `background #00008b` (X11 rgb.txt convention) for the active window, and the subcommand exits 0

### Requirement: OS-window font-size scene primitive ships under `my-kitty os-window font-size`

The system SHALL expose a `my-kitty os-window font-size <value>`
subcommand that sets the font size for ALL sub-windows in the active OS
window via `kitten @ set-font-size <value>`. The primitive is OS-window
scoped because kitty's architecture binds font size to the OS window:
`kitten @ set-font-size --help` states "in kitty all sub-windows in the
same OS window must have the same font size." The CLI noun (`os-window`)
SHALL surface this scope honestly so users learn the model from the
command rather than from a surprise.

The `<value>` positional argument accepts kitten's full grammar:
- absolute (e.g. `14` — interpreted as 14 pt),
- relative with `+`/`-`/`*`/`/` prefix (e.g. `+2`, `-2`, `*1.1`, `/2`),
- `0` to reset to the configured default.

The subcommand SHALL accept:
- `--all` — applies the change to all current AND future OS windows
  (kitten's "configured" semantics). The flag's persistence behaviour
  SHALL be documented in `--help`.
- `--to unix:<path>` — explicit remote-control socket path.

The subcommand SHALL NOT expose `--match` because the kitten verb
operates at the OS-window level, not the window level.

The subcommand MUST handle the argparse quirk where a leading-`-` value
(e.g. `-2`) looks like a flag. The CLI SHALL accept the value as a
single string argument (no client-side numeric parsing) and pass it
through to kitten verbatim.

#### Scenario: Setting absolute font size
- **WHEN** the user runs `my-kitty os-window font-size 14`
- **THEN** the kitten invocation is `kitten @ set-font-size 14`, the subcommand exits 0, and all sub-windows in the active OS window re-render at 14 pt

#### Scenario: Setting relative font size with + prefix
- **WHEN** the user runs `my-kitty os-window font-size +2`
- **THEN** the kitten invocation is `kitten @ set-font-size +2`, the subcommand exits 0, and the font size increases by 2 pt from the current value

#### Scenario: Resetting font size to configured default
- **WHEN** the user runs `my-kitty os-window font-size 0`
- **THEN** the kitten invocation is `kitten @ set-font-size 0`, the subcommand exits 0, and the font size returns to the value in kitty.conf

#### Scenario: --all flag applies to current + future OS windows
- **WHEN** the user runs `my-kitty os-window font-size 14 --all`
- **THEN** the kitten invocation includes `--all`, the subcommand exits 0, and any subsequently-spawned OS windows also start at 14 pt

### Requirement: OS-window opacity scene primitive ships under `my-kitty os-window opacity`

The system SHALL expose a `my-kitty os-window opacity <value>`
subcommand that sets the background opacity of the active OS window via
`kitten @ set-background-opacity <value>`. The primitive is OS-window
scoped because kitty's architecture binds opacity to the OS window:
`kitten @ set-background-opacity --help` states "the background opacity
affects all kitty windows in a single OS window."

The `<value>` positional argument SHALL be a float in the range
`0.0`–`1.0` inclusive, passed unchanged to kitten. Client-side range
validation is OPTIONAL; kitten errors on out-of-range values.

The subcommand SHALL accept:
- `--toggle` — exposes kitten's "reset to default if current opacity
  equals the requested value, else set" semantics. **Implementation
  invariant:** when `--toggle` is passed, the kitten argv SHALL be
  constructed as `[..., "--toggle", "<value>"]` (flag BEFORE positional).
  The reverse order causes kitten to fail with `"Must specify exactly 1
  argument(s) for set_background_opacity"` because kitten consumes the
  positional first and treats the trailing `--toggle` as a stray arg.
- `--all` — apply to all current AND future OS windows.
- `--to unix:<path>` — explicit socket.

This primitive requires `dynamic_background_opacity yes` in the kitty
config (shipped by this change as `config/kitty/dynamic-opacity.conf`,
per the `kitty-install` capability delta). Without the directive, kitten
errors with `"You must turn on the dynamic_background_opacity option in
kitty.conf to be able to set background opacity"`. The wrapper SHALL
propagate this error verbatim — no special handling, no user-facing
re-wording.

#### Scenario: Setting opacity to 0.7
- **WHEN** the user runs `my-kitty os-window opacity 0.7` on a host where `dynamic_background_opacity yes` is configured
- **THEN** the kitten invocation is `kitten @ set-background-opacity 0.7`, the subcommand exits 0, and `kitten @ ls` reports `os_window[0].background_opacity` approximately equal to `0.7` (with tolerance `< 0.01` — kitty stores opacity as a float32 so the stored value is `0.699999988`)

#### Scenario: Toggle resets opacity to default when value matches current
- **WHEN** the user has just set opacity to `0.7` and then runs `my-kitty os-window opacity 0.7 --toggle`
- **THEN** the kitten invocation argv is `["set-background-opacity", "--toggle", "0.7"]` (flag before positional), the subcommand exits 0, and `kitten @ ls` reports `os_window[0].background_opacity` equal to `1.0` (kitty default)

#### Scenario: Opacity without dynamic_background_opacity errors with clear stderr
- **WHEN** the user runs `my-kitty os-window opacity 0.5` on a host where `dynamic_background_opacity yes` is NOT configured
- **THEN** the subcommand exits non-zero and stderr contains the literal substring `"You must turn on the dynamic_background_opacity option in kitty.conf"`

### Requirement: Scenes package extends with one module per primitive

The system SHALL house each new primitive in a dedicated module under
`src/kitty_setup/scenes/`. The layout post-change SHALL be:

```
src/kitty_setup/scenes/
├── __init__.py     (already exposes title; extends to expose accent / background / font / opacity)
├── _client.py      (unchanged)
├── title.py        (unchanged)
├── accent.py       (NEW: set_tab_accent + cli_set_tab_accent)
├── background.py   (NEW: set_window_background + cli_set_window_background)
├── font.py         (NEW: set_os_window_font_size + cli_set_os_window_font_size)
└── opacity.py      (NEW: set_os_window_opacity + cli_set_os_window_opacity)
```

Each new module SHALL follow the same shape as `title.py`: a
domain-typed callable plus a `cli_*(args: argparse.Namespace)` wrapper.
Each module SHALL invoke kitten exclusively via
`_client.kitten_at(...)`; no module SHALL build a `subprocess.run(...)`
call directly against the kitten binary.

`__init__.py` SHALL re-export each new module via `from kitty_setup.scenes
import accent, background, font, opacity` so `cli.scenes.<module>` is
reachable as a module attribute (required for `monkeypatch.setattr`
targets in the CLI dispatch unit tests, same pattern as the existing
`title` re-export).

#### Scenario: Each new module imports the shared client
- **WHEN** a developer greps for `subprocess.run` under `src/kitty_setup/scenes/`
- **THEN** matches appear only in `_client.py`; `accent.py`, `background.py`, `font.py`, `opacity.py`, and `title.py` invoke kitten exclusively through `_client.kitten_at`

#### Scenario: __init__.py re-exports the new modules
- **WHEN** a developer runs `python -c "from kitty_setup import scenes; print(scenes.accent, scenes.background, scenes.font, scenes.opacity)"`
- **THEN** the four module objects print without ImportError or AttributeError

### Requirement: Managed payload ships `dynamic-opacity.conf`

The system SHALL place a file `dynamic-opacity.conf` under the managed
payload directory (`~/.config/kitty/kitty-setup/dynamic-opacity.conf`)
and SHALL add `include dynamic-opacity.conf` to
`~/.config/kitty/kitty-setup/kitty-setup.conf` after the existing
per-topic includes. The file MUST contain the single directive
`dynamic_background_opacity yes`. The file MUST carry a top-of-file
comment block citing this change (`phase2-scene-styling`), the
`kitty-scenes` capability, and the fact that the directive enables
`kitten @ set-background-opacity` (without which the verb errors with
`"You must turn on the dynamic_background_opacity option in kitty.conf
to be able to set background opacity"`).

The directive's visual impact MUST be characterised in the comment
block as zero on hosts that do not invoke `my-kitty os-window opacity`
(kitty's default opacity stays at 1.0 unless the user runs the
primitive).

The file SHALL be removed from the managed payload directory whenever
the managed payload directory itself is removed. The system MUST NOT
leave a dangling `include dynamic-opacity.conf` line in
`kitty-setup.conf` after uninstall — uninstall removes the entire
payload directory per `kitty-config-management`, so the include line
vanishes with it. The `--keep-config` flag SHALL preserve
`dynamic-opacity.conf` alongside the rest of the payload.

#### Scenario: Fresh install ships dynamic-opacity.conf
- **WHEN** the user runs `make install` on a host where the change is applied
- **THEN** the file `~/.config/kitty/kitty-setup/dynamic-opacity.conf` exists with `dynamic_background_opacity yes` present
- **AND** `~/.config/kitty/kitty-setup/kitty-setup.conf` contains the line `include dynamic-opacity.conf`
- **AND** `kitty --debug-config` exits 0

#### Scenario: Re-install is byte-identical
- **WHEN** the user runs `make install` twice with no intervening changes
- **THEN** the second run leaves `dynamic-opacity.conf` byte-identical and does not create a new `kitty.conf.bak.*` file (no-op contract from `kitty-config-management`)

#### Scenario: Uninstall removes the file
- **WHEN** the user runs `my-kitty uninstall` after a successful install that shipped `dynamic-opacity.conf`
- **THEN** the file is removed AND the include line in `kitty-setup.conf` is gone with the rest of the payload directory

#### Scenario: --keep-config preserves the file
- **WHEN** the user runs `my-kitty uninstall --keep-config`
- **THEN** `~/.config/kitty/kitty-setup/dynamic-opacity.conf` is preserved alongside the rest of the payload

### Requirement: Hypothesis-driven shipping under `tmp/h23-styling/`

The change SHALL be driven by a hypothesis-first promotion flow per
`docs/agent-iteration.md` R1 and step 4 of the loop. The hypothesis
scratch directory `tmp/h23-styling/` SHALL exist with `run.py`,
`expected.json`, and `repro.md` during proposal and apply, and SHALL be
deleted before archive.

`run.py` SHALL be a self-contained autonomous probe that spawns a raw
kitty subprocess (NOT KittySession — the harness's `--listen-on` CLI
flag overrides config-level `listen_on`), drives `kitten @
set-tab-color`, `set-colors`, `set-font-size`, and `set-background-opacity`
directly, and asserts the spec's behavioural claims:

- `set-tab-color` accepts named colors, hex colors, and `NONE`; rejects
  invalid colors with a clear error message.
- `set-colors --match` isolates the background change to the matched
  pane only (verified via `kitten @ get-colors --match` on each pane).
- `set-font-size` exits 0 for absolute, relative, and reset forms. Font
  size is NOT programmatically observable via `kitten @ ls`; visual
  outcome is the load-bearing observable (covered by the manual repro).
- `set-background-opacity` requires `dynamic_background_opacity yes` in
  the kitty config and errors with the canonical message otherwise. With
  the directive set, the value is reflected in
  `kitten @ ls -> os_window[0].background_opacity` (with float-precision
  tolerance). `--toggle` resets to default when the requested value
  matches the current value.

The directory SHALL be deleted after the promoted integration tests are
green. The change MUST NOT archive while `tmp/h23-styling/` still exists.

#### Scenario: Probe runs green on the user's host before proposal lands
- **WHEN** the user runs `uv run python tmp/h23-styling/run.py` on a host where kitty is installed and the managed config (with remote-control enabled) is loaded
- **THEN** the probe exits 0 and writes `actual.json` byte-identical to `expected.json`

#### Scenario: Probe directory is gone at archive time
- **WHEN** a reviewer inspects the change at archive time (when `openspec status` reports all artifacts done)
- **THEN** the path `tmp/h23-styling/` does not exist
