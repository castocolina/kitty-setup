## Context

`phase1-monitor-disconnect-survival` shipped `config/kitty/monitor.conf` with one directive — `linux_display_server x11` — to route kitty through XWayland and dodge the native-Wayland output-handling bug. The trade-off is documented in the file's WHY block: XWayland does not honour Wayland's fractional scaling, so kitty's rendered text effectively scales down relative to other apps when the compositor is set to fractional (e.g. 150% on Pop!_OS / COSMIC).

The user has confirmed the regression in side-by-side use against other apps on the same display (2026-05-12). The simplest compensation is to pin `font_size` to a larger value than kitty's default `11.0pt`. The user chose `13.0pt` ("+2 points").

## Goals / Non-Goals

**Goals:**

- Compensate for XWayland's loss of fractional scaling with a single static font_size value that matches the user's daily host.
- Keep the compensation coupled to the X11 workaround — same file, same lifecycle. If the user ever drops `linux_display_server x11`, the font bump goes with it.
- Preserve `kitty-monitor-survival`'s manual-repro-only verification posture. Visual size match is a human check, not a pytest assertion.

**Non-Goals:**

- No per-user / per-display / per-platform font configurability. A future capability `kitty-font-defaults` would own that.
- No reactive scaling. Kitty does not respond to runtime DPI changes via config; a future ratio-based solution would need either upstream native-Wayland fixes (preferred path) or a kitten.
- No change to the chord-driven `font-zoom.conf` chords. `ctrl+shift+=` still steps the size up/down at runtime; the user can override the 13.0 pin per-window via the existing kitten.

## Decisions

### D1. Where the directive lands: inside `monitor.conf`, not a new file

Place `font_size 13.0` in `config/kitty/monitor.conf` next to `linux_display_server x11`. Rationale: the font bump exists **because** of the X11 workaround. Coupling the two in the same file means:

- Removing `include monitor.conf` from `kitty-setup.conf` reverts both directives atomically.
- The reader of `monitor.conf` sees the cause (X11 → no fractional scaling) and the effect (font_size compensation) in the same WHY block.
- No new spec capability, no new file in the chord catalog, no `INCLUDED_PAYLOADS` update (already not in the list — `monitor.conf` ships 0 map lines).

**Alternative considered:** a new `config/kitty/font.conf`. Rejected — decoupling font from the X11 workaround invites the bug "user drops X11, forgets to drop font bump, font_size stays pinned for no documented reason". Single-file coupling avoids that.

### D2. Value: 13.0pt, not a ratio

Kitty's `font_size` directive accepts a single float in points. There is no `font_scale` or `font_size_ratio`. The user picked `13.0` after eyeballing parity with surrounding apps under Pop!_OS / COSMIC 150% scaling. The number is a per-host empirical value, not a derived universal constant.

**Alternative considered:** leave font_size at default and document a manual `ctrl+shift+=` press per new kitty session. Rejected — daily-driver workflow, the chord-press friction defeats the workaround's value.

If a future host renders 13.0 too large or too small, the user edits the literal value in `monitor.conf` and re-runs `make install`. That edit cost is acceptable for a single-user single-host repo today.

### D3. Spec shape: add ONE requirement to `kitty-monitor-survival`

The existing capability has three requirements: process survival, window migration, manual repro. Add a fourth: "X11 workaround pins font_size to compensate for fractional-scaling loss". This is the right anchor because:

- It captures the coupling (font bump exists because of X11).
- It documents the chosen value, the rationale, and the manual visual verification.
- It does NOT mandate per-platform branching (the directive is unconditional in the shipped config; macOS / non-Wayland Linux hosts get the same pin and are free to override).

### D4. Verification: extend the manual repro, no new pytest

`kitty-monitor-survival` already states "Manual-repro-only verification, by design". The font-size visual check follows the same shape:

- After `make install`, the user opens a kitty window and a reference Wayland-native app (e.g. GNOME Terminal, Firefox address bar) side by side.
- "Within tolerance" = the user judges the kitty text height is comparable, not microscopically smaller.
- The outcome lands in `docs/repro/h18-monitor-disconnect-survival.md` `## Attempted fixes` as a one-line note with the date.

No autonomous test. Adding one would require either a screenshot-pixel-diff harness (overkill for a single config line) or a kitten introspection of the resolved font size (kitty exposes `font_size` via `kitty @ get-text` ... no it does not; the directive is read-once at startup).

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| 13.0pt is too large or too small on a different host | The number is editable in `monitor.conf`; re-running `make install` propagates the new value. Documented in design.md D2. The user can also override per-session via the `ctrl+shift+=` chord. |
| Future macOS deployment may have different scaling behaviour | macOS has no fractional-scaling-loss equivalent of XWayland. The 13.0pt pin would still apply unconditionally; if the user finds it wrong on macOS, that's a new follow-up change (`phase1-monitor-x11-font-bump-macos`). |
| User drops the X11 workaround upstream (kitty fixes the Wayland disconnect bug) — the font bump becomes stale | Single-file coupling: when `linux_display_server x11` is removed, the user is one line away from also removing `font_size 13.0`. The WHY comment makes the link explicit. |
| The font_size pin interacts surprisingly with `ctrl+shift+=` (font-zoom) chords | No interaction expected: kitty's `change_font_size` action is delta-based and respects the configured starting point. After `change_font_size all 0` the size returns to 13.0, not 11.0. Verified by manual repro. |
| 13.0pt visually unbalances kitty against other terminals (xterm, alacritty) the user runs concurrently | Out of scope; this change targets the kitty-vs-Wayland-apps gap only. Users with multi-terminal setups can edit `monitor.conf` to their preferred value. |

## Open Questions

- **OQ-1:** Does kitty's `font_size` directive accept fractional values (e.g. `12.5`)? Per kitty 0.46 docs: yes. Confirmed by R6 quick check in tasks 1.1.
- **OQ-2:** Should `font-zoom.conf`'s `change_font_size all 0` reset to 13.0 (configured) or 11.0 (kitty default)? Kitty docs: resets to configured `font_size`. Confirmed by manual repro in task 3.2.
