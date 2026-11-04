# kitty-monitor-survival Specification

## Purpose
TBD - created by archiving change phase1-monitor-disconnect-survival. Update Purpose after archive.
## Requirements
### Requirement: Kitty process survives monitor disconnect

The kitty process SHALL NOT exit, crash, or terminate when an external monitor on which one or more kitty OS windows are displayed is disconnected. The process PID observed before the disconnect MUST equal the PID observed immediately after the disconnect. The kitty remote-control socket (if `allow_remote_control` is enabled) MUST remain reachable after the disconnect.

#### Scenario: Process PID unchanged after monitor unplug
- **WHEN** the user records the kitty PID via `pgrep -af 'kitty.app/bin/kitty'`, then unplugs the external monitor on which a kitty OS window was displayed, then re-records the PID immediately afterwards
- **THEN** the PID is unchanged — the same numeric pid value, the same start-time per `ps -o pid,lstart,cmd`

#### Scenario: Remote-control socket reachable after disconnect
- **WHEN** the user runs `kitty @ ls` against the running kitty's remote-control socket immediately after disconnecting the external monitor
- **THEN** the command exits 0 and returns valid JSON listing the surviving OS windows

### Requirement: Kitty windows migrate to a remaining monitor on disconnect

When the monitor an OS window was displayed on is disconnected, the OS window SHALL migrate to a remaining monitor — either the primary display, the focused-at-disconnect-time display, or any other still-attached display. The window MUST remain visible and interactive after the migration. The shell process running inside the window SHALL continue uninterrupted (no SIGHUP, no shell exit, no scrollback loss).

#### Scenario: Surviving window is reachable on a remaining monitor
- **WHEN** the user has two OS windows — one on the laptop's built-in display, one on an external monitor — and disconnects the external monitor
- **THEN** both OS windows are visible on the laptop's built-in display; both are interactive (clicking focuses them, typing inserts text); the shell processes inside both continue without interruption

#### Scenario: Long-running process inside the migrated window survives
- **WHEN** the user starts a `tail -f /var/log/syslog` process in a kitty window on the external monitor, then disconnects that monitor
- **THEN** the `tail -f` process continues running (verified via `ps -o pid,etime,cmd` showing the same pid + a continuing etime), the kitty window has migrated to a remaining monitor, and the user can scroll back to read the lines emitted before disconnect

### Requirement: Manual-repro-only verification, by design

The capability SHALL ship with a Linux-verified manual repro under `docs/repro/h18-monitor-disconnect-survival.md`. There SHALL NOT be an autonomous integration test for this requirement. The harness (`KittySession` + `kitten @`) cannot synthesise a real monitor hot-plug event — the bug is in the kitty ↔ Wayland-compositor interaction, which only fires on physical (or compositor-simulated) output disconnect. The manual repro on the user's daily host is the load-bearing verification.

The repro doc SHALL include a `## macOS Status` section that is either `verified` or `deferred-with-reason` (likely deferred — macOS uses a different windowing model and may not exhibit the bug at all). The repro doc SHALL include an `## Attempted fixes` table; that table SHALL carry a row for the X11 workaround AND a row for the `font_size` pin, each with date + outcome (visual outcome for the font pin: "comparable height to surrounding Wayland-native apps under <compositor> at <scale>%").

#### Scenario: Repro doc carries the manual-verification protocol
- **WHEN** the change merges
- **THEN** `docs/repro/h18-monitor-disconnect-survival.md` exists with: a step-by-step manual repro (start kitty windows on external monitor, unplug, observe), a `## Linux Status` section dated and verified on the user's host (Pop!_OS 24.04 + COSMIC + kitty 0.46.2), a `## macOS Status` section, AND an `## Attempted fixes` table whose rows cover (a) the `linux_display_server x11` change, (b) the `font_size` pin from `phase1-monitor-x11-font-bump`, each with date + outcome

#### Scenario: Font visual check is recorded
- **WHEN** the user runs `make install` after this change and opens a kitty window side-by-side with a reference Wayland-native application (GNOME Terminal, Firefox address bar, or similar) on the same display at the same compositor scale
- **THEN** the user judges kitty's text height to be comparable to the reference within human-eye tolerance, AND records the outcome (and the compositor scale at which the check was performed) in the `## Attempted fixes` table of the repro doc

### Requirement: X11 workaround pins font_size to compensate for fractional-scaling loss

When the system ships `linux_display_server x11` (the monitor-disconnect-survival workaround), it SHALL also pin `font_size` to a value larger than kitty's default `11.0pt` in the same `monitor.conf` file. The shipped value at the time of `phase1-monitor-x11-font-bump` archive was `16.0` (tuned from an initial `13.0` after empirical visual check on the user's primary display at 150% compositor scale — `target ≈ kitty_default × scale_factor`). The two directives MUST live in the same file so they are added and removed atomically — uninstalling `monitor.conf` reverts both, and editing `kitty-setup.conf` to drop the `include monitor.conf` line reverts both.

The rationale (WHY block at the top of `monitor.conf`) SHALL state explicitly that the font pin exists because XWayland does not honour Wayland's fractional scaling, so kitty's rendered text would otherwise look smaller than surrounding Wayland-native applications on the user's daily host. The directive MAY be edited to a host-appropriate value; the spec does NOT mandate a specific number — it mandates the *presence* of a font_size pin alongside the X11 directive, with a documented justification.

The font_size pin MUST NOT introduce a chord, MUST NOT add a new file to the managed payload, and MUST NOT require an `intentional-overrides.conf` allow-list entry. `font_size` is a non-chord directive; the chord catalog count is unchanged.

#### Scenario: Both directives ship in the same file
- **WHEN** the user runs `make install` (or `my-kitty install`)
- **THEN** `~/.config/kitty/kitty-setup/monitor.conf` contains both `linux_display_server x11` and a `font_size <value>` line (where `<value>` is a kitty-accepted float strictly greater than `11.0`), AND the WHY block at the top of the file documents the font pin's rationale

#### Scenario: Uninstall reverts both directives atomically
- **WHEN** the user runs `my-kitty uninstall`
- **THEN** `monitor.conf` is removed from the managed payload directory, AND both `linux_display_server x11` and the `font_size` pin no longer apply to the user's kitty (the include line vanishes with the payload per the existing `kitty-config-management` surgical-removal contract)

#### Scenario: Re-running install is byte-identical
- **WHEN** the user runs `make install` twice with no intervening changes
- **THEN** the second run leaves `monitor.conf` byte-identical and does not create a new `kitty.conf.bak.*` file (no-op contract from `kitty-config-management`)

