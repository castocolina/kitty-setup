## 1. External-system probes (R6) — must precede any config draft

- [x] 1.1 Probe `tmp/probes/phase1-monitor-disconnect-survival/01-failure-mode.md` (2026-05-11). Verdict: `holds` — kitty PID 198611 died on monitor power-cycle while DRM connector list stayed identical pre/post. Cross-terminal control in probe-04 confirmed wezterm, xterm, chrome all survived the same event → bug is kitty-specific.
- [x] 1.2 Probe `tmp/probes/phase1-monitor-disconnect-survival/02-kitty-output-knobs.md` (2026-05-07). Verdict: `fails` — kitty 0.46.2 exposes zero direct knobs for output-disconnect handling. BUT: probe-05 found `linux_display_server x11` is the indirect remedy (reroutes kitty through XWayland whose output-leave handling is sane).
- [x] 1.3 Probe `tmp/probes/phase1-monitor-disconnect-survival/03-cosmic-logs.md` (2026-05-11). Verdict: `partial-with-workaround` — cosmic-comp logs two output-reconfig errors ("Failed to destroy old mode property blob", "Failed to set xwayland primary output") but does NOT log a kill of kitty's surface. cosmic-comp PID stayed alive; cosmic-panel applets restart (cosmetic). Bug is internal to kitty's Wayland event-loop, not in compositor's client management.
- [x] 1.4 Added `## Probes` section to `design.md` (with the additional probes 04/05 surfaced during the investigation).

## 2. Hypothesis (R1) — single dir, manual-only, iterate via repro doc

- [x] 2.1 Hypothesis evidence captured in probes 01/04/05 instead of a separate `tmp/h18-monitor-disconnect-survival/` directory. The branch decision (probe-04 + probe-05) selected D3 branch (a) directly — no extended iteration was needed beyond the cross-terminal test (probe-04) and the XWayland verification (probe-05). Manual repro promoted to `docs/repro/h18-monitor-disconnect-survival.md` directly.
- [x] 2.2 `repro.md` shape applied to `docs/repro/h18-monitor-disconnect-survival.md` (Why / Manual repro / Linux Status / macOS Status / Tradeoffs / Upstream bug note / Attempted fixes table / Known limitations).
- [x] 2.3 Single iteration sufficient. `draft.conf` content = `linux_display_server x11` only; promoted to `config/kitty/monitor.conf` with the canonical WHY block.
- [x] 2.4 N/A — branch (a) succeeded; branches (b/c/d) not needed for the daily-driver fix. Branch (d) upstream bug is named in the repro doc as a follow-up so a future kitty release can restore native Wayland survival.

## 3. Promote — config + repro doc + spec capture

- [x] 3.1 Shipped `config/kitty/monitor.conf` with the single line `linux_display_server x11` plus a top-of-file WHY block citing probes 01/04/05 + design.md D3. Added `include monitor.conf` to `config/kitty/kitty-setup.conf` after `include url-hints.conf`.
- [x] 3.2 N/A — branch (b) not taken.
- [x] 3.3 N/A — branch (c) not taken.
- [x] 3.4 Branch (d) note added to `docs/repro/h18-monitor-disconnect-survival.md` `## Upstream bug` section with suggested issue title and evidence pointers (probe-04 cross-terminal table + probe-03 cosmic-comp log).
- [x] 3.5 Promoted `repro.md` to `docs/repro/h18-monitor-disconnect-survival.md`. `## Linux Status` verified on 2026-05-11 (Pop!_OS 24.04 + COSMIC + kitty 0.46.2, evidence from probe-05). `## macOS Status` deferred — windowing model is different (Quartz, not Wayland), bug likely doesn't exhibit. Follow-up `phase1-monitor-disconnect-survival-macos` named.
- [x] 3.6 No `tmp/h18-...` directory was created; only `tmp/probes/phase1-monitor-disconnect-survival/` exists with probes 01/02/03/04/05 (gitignored scratch; will disappear at archive time per R5).

## 4. Catalog-level verification

- [x] 4.1 `my-kitty keys --json` unchanged in chord count (24 ours, monitor.conf has no chord lines). The file appears as a payload file under `~/.config/kitty/kitty-setup/monitor.conf` after `make install`.
- [x] 4.2 `make doctor` exit 0, `bindings: 24 ours, 79 defaults, 0 conflicts` — unchanged.
- [x] 4.3 `KITTI_INTEGRATION=1 uv run pytest tests/` → `150 passed` — unchanged (no new tests; manual-repro-only per spec).
- [x] 4.4 `make install` confirmed: `monitor.conf` now lives at `~/.config/kitty/kitty-setup/monitor.conf` after `uv tool install --reinstall --force .` (the standard uv-tool caching paper-cut from prior changes — surfaced again here). `make uninstall` removes the file via the existing surgical-removal contract.

## 5. Verification before completion

- [x] 5.1 `make doctor` output captured in `openspec/changes/phase1-monitor-disconnect-survival/verification.md`.
- [x] 5.2 `KITTI_INTEGRATION=1 uv run pytest tests/` summary captured in `verification.md`.
- [ ] 5.3 Capture the manual repro outcome (5 disconnect cycles minimum) into `docs/repro/h18-monitor-disconnect-survival.md` `## Linux Status`. **Pending user verification** — user must close all existing kitty windows, reopen kitty (so `linux_display_server x11` takes effect), then repeat the monitor power-cycle 5 times to confirm survival.
- [x] 5.4 macOS verification deferred; follow-up named `phase1-monitor-disconnect-survival-macos` (no proposal filed yet).
