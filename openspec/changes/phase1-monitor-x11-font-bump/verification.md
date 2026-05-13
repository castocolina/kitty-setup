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

## Manual visual check — pending

The user's currently running kitty pre-dates this change. To complete the manual visual check (task 3.2):

1. Quit all kitty instances.
2. Launch a fresh kitty (`Super+T` or `kitty &`).
3. Open a reference Wayland-native app side-by-side (Firefox address bar, GNOME Terminal, or COSMIC's built-in terminal).
4. Compare text heights under the current compositor scale.
5. Record the outcome in `docs/repro/h18-monitor-disconnect-survival.md` `## Attempted fixes` table row dated 2026-05-12.

If 13.0pt is wrong on this host, edit `config/kitty/monitor.conf`, re-run `uv run my-kitty install`, restart kitty, re-check.

## macOS

Not applicable to this change. macOS has no XWayland-fractional-scaling-loss equivalent; if the user ever deploys on macOS and the 13.0pt pin is the wrong default, that is a new follow-up change.
