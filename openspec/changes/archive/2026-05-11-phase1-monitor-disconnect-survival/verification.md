# Verification — phase1-monitor-disconnect-survival

Captured 2026-05-11 on Pop!_OS 24.04 + COSMIC + kitty 0.46.2.

## `make doctor`

```
PASS kitty binary: /home/user-zero/.local/bin/kitty -> kitty 0.46.2 created by Kovid Goyal
PASS symlink: /home/user-zero/.local/bin/kitty -> /home/user-zero/.local/kitty.app/bin/kitty
PASS desktop entry: /home/user-zero/.local/share/applications/kitty.desktop
PASS config payload: /home/user-zero/.config/kitty/kitty-setup/kitty-setup.conf
PASS sentinel block: present in /home/user-zero/.config/kitty/kitty.conf
PASS parse check: kitty --debug-config exit=0
PASS bindings: 24 ours, 79 defaults, 0 conflicts
PASS completion: helper /usr/bin/register-python-argcomplete; eval line present in /home/user-zero/.zshrc
```

Exit 0. Binding count unchanged at 24 ours / 79 defaults / 0 conflicts — `monitor.conf` adds zero chords (it's a session setting, `linux_display_server x11`).

## `KITTI_INTEGRATION=1 uv run pytest tests/`

```
150 passed in 4.43s
```

Test count unchanged. The spec's "Requirement: Manual-repro-only verification, by design" explicitly waives autonomous test coverage — the failure mode is hot-plug-dependent and the harness cannot synthesise it.

## Manual repro evidence

### Probe-04 — cross-terminal survival (2026-05-11)

```
Terminal | Path           | PID pre  | PID post | Verdict
---------|----------------|----------|----------|----------
kitty    | Wayland-native | 198611   | DIED     | ❌
wezterm  | Wayland-native | 57980    | 57980    | ✅
xterm    | XWayland       | 198776   | 198776   | ✅
chrome   | Wayland (ctrl) | 5685     | 5685     | ✅
```

Same event killed only kitty. Bug is kitty-specific (probe-01 + probe-03 + probe-04).

### Probe-05 — kitty with `linux_display_server x11` (2026-05-11)

```
kitty-x11 PID pre:  202185
[monitor power-cycle]
kitty-x11 PID post: 202185  ← SAME PID; survived
```

Identical PID before and after the monitor power-cycle confirms the workaround restores survival.

### Install workflow

```
$ uv tool install --reinstall --force .
Installed 2 packages in 1ms
 ~ kitty-setup==0.0.0 (from file:///home/user-zero/git/cco/kitty-setup)

$ my-kitty install
config:        already up to date

$ ls ~/.config/kitty/kitty-setup/monitor.conf
-rw-rw-r-- 1 user-zero user-zero 1384 may 11 10:40 /home/user-zero/.config/kitty/kitty-setup/monitor.conf
```

Note: a clean `make install` (without `--reinstall --force` on the uv tool first) does NOT pick up new payload files because uv caches the wheel by version string. This is a pre-existing uv-tool-install paper-cut, not introduced by this change. Documented as a follow-up concern (no follow-up change named yet).

## Pending verification

- [ ] **User must close all current kitty windows and reopen kitty** so the newly-installed `linux_display_server x11` takes effect. Then re-run the monitor power-cycle 5 times. Each cycle should show: same kitty PID before and after, running shells uninterrupted, kitty window visible after switch-back. When confirmed, mark task 5.3 in tasks.md and update `docs/repro/h18-monitor-disconnect-survival.md` `## Linux Status` with the 5-cycle log.

## Follow-ups (named, no proposals filed yet)

- `phase1-monitor-disconnect-survival-macos` — verify on macOS host when available (bug likely doesn't exhibit on Quartz windowing).
- Upstream kitty bug at https://github.com/kovidgoyal/kitty/issues — file a report so a future kitty release can restore native Wayland survival; until then this repo's XWayland workaround is the daily-driver remedy.
