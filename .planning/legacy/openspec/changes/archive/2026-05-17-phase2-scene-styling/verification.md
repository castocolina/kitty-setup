# Verification — phase2-scene-styling

Captures the autonomous + manual outcomes that gate archive of this change,
per `tasks.md` §8. The Linux Status row in `docs/repro/h23-styling.md`
must read `verified` before this change archives.

## Autonomous (already green)

### `make doctor` (2026-05-16, host: Pop!_OS 24.04 + COSMIC + kitty 0.46.2)

```
PASS kitty binary: /home/user-zero/.local/bin/kitty -> kitty 0.46.2 created by Kovid Goyal
PASS symlink: /home/user-zero/.local/bin/kitty -> /home/user-zero/.local/kitty.app/bin/kitty
PASS desktop entry: /home/user-zero/.local/share/applications/kitty.desktop
PASS config payload: /home/user-zero/.config/kitty/kitty-setup/kitty-setup.conf
PASS sentinel block: present in /home/user-zero/.config/kitty/kitty.conf
PASS parse check: kitty --debug-config exit=0
PASS bindings: 21 ours, 79 defaults, 0 conflicts
PASS completion: helper /usr/bin/register-python-argcomplete; eval line present in /home/user-zero/.zshrc
SKIP remote-control: no running kitty
```

All applicable checks PASS. The remote-control SKIP is expected — `make
doctor` was run without a kitty instance running. No new doctor check was
added by this change (§8.1 of tasks.md: "no new doctor check expected").

### `make install` (2026-05-16)

`my-kitty install` ran clean. Payload landed at
`~/.config/kitty/kitty-setup/`; new file shipped at
`~/.config/kitty/kitty-setup/dynamic-opacity.conf`:

```
$ cat ~/.config/kitty/kitty-setup/dynamic-opacity.conf
# Phase 2 §10 — runtime opacity precondition.
...
dynamic_background_opacity yes

$ grep -c 'include dynamic-opacity.conf' ~/.config/kitty/kitty-setup/kitty-setup.conf
1
```

Per §8.5: the include line appears exactly once and the directive is
present. Per `kitty-config-management`'s no-op contract, the second
consecutive `make install` (verified in the rolling output) leaves the file
byte-identical and creates no new `kitty.conf.bak.*` file.

### `make test` — unit suite (2026-05-16)

```
======================= 175 passed, 51 skipped in 0.18s ========================
```

Unit suite: **175/175 green** (was 149 before this change; +26 new tests
across `test_scenes_accent.py`, `test_scenes_background.py`,
`test_scenes_font.py`, `test_scenes_opacity.py`, and the `test_cli.py`
extensions). 51 skipped are the gated integration tests.

### `KITTI_INTEGRATION=1 pytest tests/` — full suite incl. integration (2026-05-16)

```
226 passed in 17.12s
```

Integration suite: **51 tests** including:

- `tests/integration/test_h22_window_title.py` — 7 tests still green after
  the helper extraction to `_kitty_subprocess.py`.
- `tests/integration/test_h23_styling.py` — 8 tests new in this change,
  covering all 23 expected.json keys from the h23 probe:
  - `test_opacity_without_directive_errors_clearly` (precondition + stderr)
  - `test_set_tab_color_accepts_named_hex_NONE`
  - `test_set_tab_color_rejects_invalid_color` (incl. stderr substring)
  - `test_set_colors_isolates_to_matched_pane` (launch + pane count +
    per-pane isolation)
  - `test_set_colors_accepts_named_color` (X11 rgb.txt → #00008b)
  - `test_set_font_size_absolute_relative_reset` (14, +2, 0)
  - `test_set_opacity_reflected_in_ls_with_tolerance` (abs < 0.01 per D4)
  - `test_set_opacity_toggle_resets_to_default` (toggle + empty stderr +
    ls reports 1.0)
- All other integration suites (h01, h02, h03, h11-h16, h19, h21) unchanged,
  still green.

### Autocomplete (`my-kitty <TAB>` simulation, §8.6)

Sourcing the same `register-python-argcomplete` machinery that ships with
the install, with `_ARGCOMPLETE=1` set:

```
$ _ARGCOMPLETE=1 ... COMP_LINE='my-kitty ' COMP_POINT=9 my-kitty | grep -E '^(os-window|window|tab|install|doctor)'
doctor
install
os-window
tab
window
```

`os-window` appears in the candidate list alongside the existing
subcommands. The doctor `completion` check above confirms the
`register-python-argcomplete my-kitty` eval line is sourced from
`~/.zshrc` and the helper binary is on PATH; no additional wiring required
by this change (the new subparsers inherit completion from the existing
argcomplete registration in `cli.py`).

### `openspec validate phase2-scene-styling --strict` (§8.8)

```
Change 'phase2-scene-styling' is valid
```

## Manual (user-driven, signed off 2026-05-17)

All §8.4 manual checks signed off by the user on the daily host (Pop!_OS
24.04 + COSMIC + kitty 0.46.2):

- **§7.2 scenarios 1–7 of `docs/repro/h23-styling.md`** all green:
  1. Tab accent visible on focused AND unfocused tabs (named, hex, NONE).
  2. Tab accent invalid color rejected with clear stderr `"is not a valid
     color"`.
  3. Window background per-pane isolation — `--match` targets exactly one
     pane; other panes unchanged.
  4. OS-window font-size absolute (`14`), relative (`+2`), reset (`0`) —
     all panes in the active OS window re-render in lockstep.
  5. OS-window opacity set (`0.7`) → translucent; `--toggle 0.7` →
     back to fully opaque.
  6. Opacity-without-directive error (sanity-check; managed payload
     always ships the directive).
  7. `--match` and `--to` selectors work as designed.

The `## Linux Status` section of `docs/repro/h23-styling.md` is now
`verified (2026-05-17, Pop!_OS 24.04 + COSMIC + kitty 0.46.2)`.

## Probe cleanup (§8.7)

`tmp/h23-styling/` deleted (2026-05-17). The `kitty-scenes` spec's
"Probe directory is gone at archive time" scenario is satisfied.

## Followups

- `phase2-scene-styling-macos` — re-verify all 7 scenarios on a macOS host
  when one is available. The `kitten @` protocol is platform-agnostic, but
  tab-bar accent / opacity / font composition may differ visually.
- Phase 2 §11 (extra layouts), §13 (named scenes — persistence layer that
  re-applies these primitives on session load), §14 (chord-to-scene wiring).
