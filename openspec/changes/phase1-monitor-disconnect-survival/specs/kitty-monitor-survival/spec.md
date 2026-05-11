## ADDED Requirements

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

The repro doc SHALL include a `## macOS Status` section that is either `verified` or `deferred-with-reason` (likely deferred — macOS uses a different windowing model and may not exhibit the bug at all).

#### Scenario: Repro doc carries the manual-verification protocol
- **WHEN** the change merges
- **THEN** `docs/repro/h18-monitor-disconnect-survival.md` exists with: a step-by-step manual repro (start kitty windows on external monitor, unplug, observe), a `## Linux Status` section dated and verified on the user's host (Pop!_OS 24.04 + COSMIC + kitty 0.46.2), a `## macOS Status` section, and an `## Attempted fixes` table listing each `draft.conf` iteration with date + outcome
