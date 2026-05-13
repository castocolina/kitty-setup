## Why

Phase 1 §6 ships `linux_display_server x11` (in `config/kitty/monitor.conf`) as a workaround for kitty's native-Wayland backend exiting on monitor disconnect / KVM switch / DPMS power-cycle. The fix routes kitty through XWayland — which is itself a documented trade-off in the file's WHY block: "native fractional scaling lost; HiDPI may differ".

Real-world consequence on the user's daily host (Pop!_OS 24.04 / COSMIC / Wayland fractional scaling at 150%): under XWayland, kitty renders text at a smaller effective size than every Wayland-native application beside it. Reading code, log output, and `make doctor` reports requires more zoom-in than other clients on the same display. The user has confirmed the regression by side-by-side comparison on 2026-05-12.

This change ships the smallest font compensation that matches the workaround's footprint: a single `font_size 13.0` directive added to `monitor.conf` next to `linux_display_server x11`. The two directives stay coupled — anyone removing the monitor-survival workaround also reverts the font bump in the same edit. No separate file, no new capability, no per-platform branching.

## What Changes

- Append `font_size 13.0` to `config/kitty/monitor.conf` directly after `linux_display_server x11`, with an inline `# WHY` comment citing the XWayland fractional-scaling loss and this proposal.
- Extend the WHY block at the top of `monitor.conf` with one bullet under the existing "Tradeoffs" list: "font_size pinned to 13.0 (kitty default 11.0) to compensate for XWayland's lack of fractional scaling — undoing this directive restores the kitty default size".
- Update `tests/integration/test_h18_monitor_disconnect_survival.py` (if it exists) OR the introspection test (`test_h03`) to confirm the new directive is preserved through the install/uninstall round-trip. `font_size` is a non-chord directive, so the chord-counting `INCLUDED_PAYLOADS` test is not affected.
- Manual visual check: open kitty after `make install`, observe text size matches surrounding Wayland apps within tolerance. No autonomous test — same precedent as the `linux_display_server x11` line itself (per `kitty-monitor-survival` requirement "Manual-repro-only verification, by design").
- Update `docs/repro/h18-monitor-disconnect-survival.md` `## Attempted fixes` table with a row for the font bump + a one-line note on the visual outcome.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `kitty-monitor-survival`: the X11 workaround now also pins `font_size 13.0` to compensate for XWayland's loss of fractional scaling. A new requirement captures the directive's presence + the rationale, and the existing "Manual-repro-only verification" requirement extends to cover the font size's visual check. No behaviour change to the disconnect-survival contract itself.

## Impact

- **Edited files:** `config/kitty/monitor.conf` (one new directive + one comment line + one bullet in the WHY block).
- **No new files.**
- **No new top-level paths.**
- **System mutations:** install copies the updated `monitor.conf` into the managed payload dir as usual. Uninstall removes it via the existing surgical-removal contract — both `linux_display_server x11` and `font_size 13.0` vanish together.
- **Reversibility:** removing the `include monitor.conf` line from `kitty-setup.conf` reverts both directives. Editing `monitor.conf` to drop just the font line keeps the X11 workaround but restores the default 11.0pt font.
- **Out of scope:** per-user / per-platform font configurability (would be a new capability `kitty-font-defaults`). Font family selection. Anything about the chord-driven font-zoom in `font-zoom.conf` (already covered by `kitty-curated-bindings`).
