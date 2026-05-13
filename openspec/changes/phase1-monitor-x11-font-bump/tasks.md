## 1. External-system probes (R6)

- [x] 1.1 Probe `tmp/probes/phase1-monitor-x11-font-bump/01-font-size-accepts-float.md` — verify kitty 0.46.x accepts a `font_size 13.0` directive without warning or parse error. Command: `kitty --debug-config --config <scratch.conf>` where scratch.conf is one line `font_size 13.0`. Verdict: `holds` / `fails`. Used by: design D1.
- [x] 1.2 Probe `tmp/probes/phase1-monitor-x11-font-bump/02-change-font-size-zero-resets-to-config.md` — verify `change_font_size all 0` resets to the configured `font_size`, not kitty's default `11.0`. Spawn a `KittySession` with `font_size 13.0` in its session config, send `ctrl+shift+=` then `ctrl+shift+backspace`, capture the resolved font size (kitty does not expose this via `kitten @`; this probe is documented-only, citing the kitty docs section "change_font_size action"). Verdict feeds OQ-2.

## 2. Promote — config diff

- [x] 2.1 Append `font_size 13.0` to `config/kitty/monitor.conf` after `linux_display_server x11`, with an inline comment citing this change ID and design D1/D2.
- [x] 2.2 Add one bullet under the existing "Tradeoffs" list at the top of `monitor.conf`: "font_size pinned to 13.0 (kitty default 11.0) to compensate for XWayland's lack of fractional scaling — drop this line to restore kitty's default size".

## 3. Verification

- [x] 3.1 Run `uv run my-kitty install`; confirm `~/.config/kitty/kitty-setup/monitor.conf` contains both `linux_display_server x11` AND `font_size 13.0`. Run `uv run my-kitty doctor`; confirm exit 0 and `parse check: kitty --debug-config exit=0` PASS.
- [x] 3.2 Manual visual check: open kitty + a reference Wayland-native application (Firefox address bar, GNOME Terminal, or COSMIC's built-in terminal if present) side by side at the host's current compositor scale. Judge kitty text height comparable to the reference within human-eye tolerance. Record the outcome (compositor scale + reference app + verdict) in the `## Attempted fixes` table of `docs/repro/h18-monitor-disconnect-survival.md`.
- [x] 3.3 Run `KITTI_INTEGRATION=1 uv run pytest tests/` — confirm green. No new tests expected; the chord catalog count is unchanged (0 new map lines), the install/uninstall round-trip is covered by existing tests.
- [x] 3.4 Verify the uninstall round-trip via `config_updater.install/uninstall` in a tempdir: after install, `monitor.conf` carries both directives; after uninstall, the file and the parent payload dir are gone.

## 4. Verification before completion

- [x] 4.1 Capture `uv run my-kitty doctor` output verbatim into `openspec/changes/phase1-monitor-x11-font-bump/verification.md`.
- [x] 4.2 Capture `KITTI_INTEGRATION=1 uv run pytest tests/` summary into the same file.
- [x] 4.3 Capture the manual visual check outcome (compositor scale + reference app + judgement) into `docs/repro/h18-monitor-disconnect-survival.md` `## Attempted fixes` table and into `verification.md`.
- [x] 4.4 Delete `tmp/probes/phase1-monitor-x11-font-bump/` after the change archives (R6 — probe findings are encoded in design.md D1/D2 and in the inline `monitor.conf` comment).
