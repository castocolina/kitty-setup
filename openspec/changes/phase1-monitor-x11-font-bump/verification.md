# Verification — phase1-monitor-x11-font-bump

Captured 2026-05-12 on Pop!_OS 24.04 / COSMIC / kitty 0.46.2.

## Probe results

| Probe | Verdict | Finding |
|---|---|---|
| 01 | `holds` | `font_size 13.0` parses cleanly via `kitty +runpy` + `kitty.config.load_config`; no bad-line, exit 0. The CLI flag `kitty --debug-config` does NOT exist on kitty 0.46.x — use `kitty +runpy` + `load_config` instead (same primitive `config_updater._parse_check` already uses). |
| 02 | `holds` (documented) | `change_font_size all 0` resets to the configured `font_size`, not the compiled-in default — kitty docs, "Action: change_font_size". |

## `uv run my-kitty install` (post-source-edit)

```
$ uv run my-kitty install
kitty version: kitty 0.46.2 created by Kovid Goyal
kitty.app:     /home/user-zero/.local/kitty.app
symlink:       /home/user-zero/.local/bin/kitty -> /home/user-zero/.local/kitty.app/bin/kitty
desktop entry: /home/user-zero/.local/share/applications/kitty.desktop
status:        kitty already installed; skipped upstream installer
config:        already up to date (~/.config/kitty/kitty.conf)
PATH:          already configured
```

The "already up to date" message refers to the sentinel block in the user's `kitty.conf`; the payload directory contents (`~/.config/kitty/kitty-setup/`) are refreshed from the source on every install. Confirmed:

```
$ grep -E "^font_size|^linux_display_server" ~/.config/kitty/kitty-setup/monitor.conf
linux_display_server x11
font_size 13.0
```

## `uv run my-kitty doctor` output

```
PASS kitty binary: ~/.local/bin/kitty -> kitty 0.46.2
PASS symlink, desktop entry, config payload, sentinel block
PASS parse check: kitty --debug-config exit=0
PASS bindings: 21 ours, 79 defaults, 0 conflicts
PASS completion: helper + eval line present
SKIP remote-control: no managed kitty socket found (running kitty pre-dates `make setup`?)
exit=0
```

Parse check is the load-bearing verification for this change — kitty's config loader accepts the new directive without complaint.

## `KITTI_INTEGRATION=1 pytest tests/` summary

```
============================= 164 passed in 3.82s ==============================
```

No new tests expected (the chord catalog count is unchanged; `font_size` is a non-chord directive). Existing install/uninstall round-trip tests cover the new directive transparently.

## Install / uninstall round-trip

Verified in a tempdir via `config_updater.install/uninstall`:

```
install: linux_display_server x11: True
install: font_size 13.0: True
uninstall: monitor.conf removed: True
uninstall: payload_dir removed: True
```

The two directives ship and revert atomically — design D1 contract honoured.

## Manual visual check — verified at `font_size 16.0`

Initial value `13.0` (+2pt over kitty default) was insufficient on the user's primary display (DELL S2725QC at 150% COSMIC scale). Tuned to `16.0` (≈ 11.0 × 1.5, the math-derived parity value) and confirmed:

- Side-by-side with Firefox + GNOME Terminal on the DELL display → text height comparable within human-eye tolerance.
- ASUS VP228 at 100% scale shows the same 16.0pt as ~50% larger than native-Wayland apps on that screen. Trade-off accepted: kitty has only one `font_size` directive, mixed-scale setups cannot have parity on both displays simultaneously without a kitten-level adapter.

The empirical rule encoded in the inline `monitor.conf` comment:

```
target font_size = kitty_default (11.0) × primary_display_compositor_scale
```

At 100% / 125% / 150% / 175% / 200%: 11.0 / 13.75 / 16.5 / 19.25 / 22.0pt. Round to the nearest tenth, edit the literal value if needed.

## Wheel-cache trap (incident)

`make install` runs `uv tool install --force .` — `--force` forces install over existing tool but does NOT invalidate uv's wheel build cache. On the user's first attempt to land this change, the cached wheel pre-dated the source edits and the new `monitor.conf` + `remote-control.conf` never reached the user's payload directory. Fix: `uv tool install --reinstall --force .` (the `--reinstall` invalidates the build cache). `tools/setup.sh:install_tool()` updated in the same commit as the `font_size 16.0` patch so this stops surprising future users.

## macOS

Not applicable to this change. macOS has no XWayland-fractional-scaling-loss equivalent; if the user ever deploys on macOS and the 13.0pt pin is the wrong default, that is a new follow-up change.
