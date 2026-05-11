# H18 — Kitty survives monitor disconnect / KVM switch / DPMS power-cycle

**Capability:** kitty-monitor-survival (Phase 1 §6).

**Status:** Promoted (branch a). Configuration in
[`config/kitty/monitor.conf`](../../config/kitty/monitor.conf) — single line
`linux_display_server x11` reroutes kitty through XWayland to dodge a kitty
0.46.x native-Wayland output-handling bug. NO autonomous integration test
backs this requirement — by design — because the failure mode is a real
monitor/KVM event that the harness cannot synthesise. Manual repro on the
user's daily host is the load-bearing verification.

## Why

Kitty's native-Wayland backend (GLFW-Wayland) exits the entire process when
an external monitor that hosts a kitty OS-window goes through an output
reconfig (KVM switch, DPMS power-off, physical unplug). This is a kitty bug,
not a compositor bug — confirmed empirically by the survival of wezterm
(Wayland-native), xterm (XWayland), and chrome under the identical event.
See [probe-01](../../tmp/probes/phase1-monitor-disconnect-survival/01-failure-mode.md)
through [probe-05](../../tmp/probes/phase1-monitor-disconnect-survival/05-kitty-x11-survives.md)
for the audit trail.

The workaround is `linux_display_server x11`: kitty connects via XWayland
instead of native Wayland, inherits XWayland's monitor-handling behaviour
(which doesn't crash), and survives the event. Same path xterm uses.

## Manual repro

1. Run `make install` to inject the curated catalog (which now includes
   `monitor.conf`).
2. Open a kitty window. Place it on an external monitor reachable via KVM
   (or a monitor whose power can be cycled, or a monitor that can be
   physically unplugged).
3. Confirm kitty is running under XWayland:
   ```bash
   KITTY_PID=$(pgrep -af 'kitty.app/bin/kitty' | head -1 | awk '{print $1}')
   tr '\0' '\n' < /proc/$KITTY_PID/environ | grep -E '^(DISPLAY|WAYLAND_DISPLAY)='
   ```
   Expect: `DISPLAY=:1` (or similar) — XWayland reachable. `WAYLAND_DISPLAY`
   may also appear but kitty does not connect via it under
   `linux_display_server=x11`.
4. Inside the kitty window, start a long-running command so a process kill
   is observable:
   ```bash
   ping google.com
   ```
5. Cycle the external monitor — KVM switch, power off + on, or physical
   unplug + replug. Wait ~5 seconds after each event.
6. Verify:
   - The kitty window is still visible (perhaps migrated to a remaining
     display).
   - `ping google.com` is still running with continuous output.
   - The kitty PID is unchanged:
     ```bash
     pgrep -af 'kitty.app/bin/kitty'
     ```
     Same PID as in step 3.

## Linux Status

**verified** (2026-05-11, Pop!_OS 24.04 + COSMIC compositor + kitty 0.46.2).
Empirical evidence in probes 01/04/05. Probe-05 demonstrated kitty PID
202185 survived a full monitor power-cycle under `linux_display_server x11`,
while probe-01/04 demonstrated kitty PID 198611 died under native Wayland
on the same event.

## macOS Status

**deferred** — macOS uses a different windowing model (Quartz / NSWindow),
not Wayland, and the `linux_display_server` option does not apply. The bug
likely does not exhibit on macOS at all. Follow-up: re-verify on a macOS
host when one is available; if the bug doesn't reproduce, this capability
is Linux-only by construction. Tracked under
`phase1-monitor-disconnect-survival-macos` (no proposal filed yet).

## Tradeoffs of XWayland mode

The fix is a workaround, not a fundamental cure. Under XWayland kitty loses:

- **Native fractional scaling.** HiDPI displays under XWayland use integer
  scaling + downsample; sharp at 100 % / 200 %, slightly blurry at 125 % /
  150 % / 175 %. If you run a 4K display at 150 % scale, kitty text may
  appear less crisp than under native Wayland.
- **Wayland-specific clipboard MIME types.** The X11 clipboard model is
  simpler. Image paste pipelines and some MIME-aware tools may behave
  differently. (Relevant to the paused `phase1-paste-preservation` change.)
- **Wayland-only image protocols.** Kitty's wayland-specific image protocol
  bits are not used under XWayland; falls back to the generic kitty
  graphics protocol which still works.
- **Native touch / gesture events.** Wayland touch protocols don't reach
  kitty under XWayland; if you use a touchscreen, gestures may be reduced.

For a daily-driver multi-monitor / KVM workflow these tradeoffs are smaller
than losing every kitty window on every monitor power-cycle.

## Upstream bug (branch d note)

A kitty upstream bug should be filed at
https://github.com/kovidgoyal/kitty/issues so a future kitty release can
restore native Wayland survival. Until that lands, this repo's
`linux_display_server x11` workaround is the daily-driver remedy.

Suggested issue title: "Wayland: kitty exits on output reconfig (KVM
switch / monitor power-cycle) where wezterm, xterm, chrome all survive".
Include the probe-04 cross-terminal table as evidence and probe-03's
cosmic-comp journal lines to rule out compositor fault.

## Attempted fixes

| Date       | Approach                                         | Outcome   |
| ---------- | ------------------------------------------------ | --------- |
| 2026-05-11 | Default native Wayland (`linux_display_server` not set) | ❌ kitty dies on monitor power-cycle |
| 2026-05-11 | `linux_display_server x11` (XWayland)            | ✅ kitty survives |

## Known limitations

- No autonomous integration test — the harness cannot synthesise a real
  monitor hot-plug or KVM switch event. Manual repro is the only
  verification path; documented in the spec as
  "Requirement: Manual-repro-only verification, by design".
- macOS verification deferred (no Mac host available; bug likely doesn't
  exhibit on Quartz windowing).
- Wayland-native features lost under XWayland; see "Tradeoffs" above.
- Daily dogfooding on Pop!_OS 24.04 + COSMIC is the regression detector.
  If the bug returns after a kitty upgrade or a COSMIC upgrade, re-run
  the manual repro and reopen this change with the new findings.
