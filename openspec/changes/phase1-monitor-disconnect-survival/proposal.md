## Why

Phase 1 §6 of `docs/requirements.md`: "Kitty survives suspend/resume and monitor disconnect — no crash, no exit." Daily-friction item. User runs Pop!_OS 24.04 with the COSMIC compositor (Wayland) and a multi-monitor setup. When an external monitor is unplugged, kitty windows that were on that monitor disappear instead of migrating to the remaining display, costing the user any work-in-flight in those windows (running processes, scrollback, ssh sessions). iTerm and the GNOME default terminal both migrate windows on monitor disconnect; kitty does not — this is the regression to close.

Investigation-led: the cause is unknown. Candidates are (a) kitty doesn't subscribe to the Wayland `wl_output.leave` event correctly and the compositor kills the client when its output goes away, (b) COSMIC-specific output-leave behaviour kills surfaces tied to a vanished output, (c) a kitty config knob exists that makes kitty handle the leave gracefully (similar to how some clients implement output-migration on `wl_output.leave`), (d) it's a kitty bug requiring an upstream report. Probe-first: characterise the actual failure mode before drafting any config or workaround.

Scope is narrow: this change covers ONLY the monitor-disconnect case. The suspend/resume half of §6 is split into a sibling change (`phase1-suspend-resume-survival`) if probing shows it's a distinct failure path; if both modes share the same root cause, fold them into this change with a second hypothesis dir.

## What Changes

- Add probe artefacts under `tmp/probes/phase1-monitor-disconnect-survival/` per R6:
  - **probe-01: characterise the failure mode** — start kitty with two windows on the external monitor, unplug the monitor, observe (process exit? window vanish? compositor error in `journalctl`?). Capture the exact failure shape.
  - **probe-02: kitty config surface for output-leave** — enumerate kitty 0.46.x options whose name or doc mentions `output`, `monitor`, `display`, `surface`, or `migrate`. Verdict: which knobs (if any) influence the behaviour.
  - **probe-03: COSMIC compositor logs on disconnect** — read `journalctl --user-unit=cosmic-comp` (or equivalent) around the disconnect event. Verdict: does COSMIC log the kill, and if so why.
- Hypothesis under `tmp/h18-monitor-disconnect-survival/` with a manual repro (autonomous repro is hard — requires real monitor hot-plug or a Wayland test compositor; KittySession can't synthesise this) plus `draft.conf` capturing the candidate kitty config.
- Based on probe verdicts, ship one of four remediations:
  - **(a) kitty config diff** in a new `config/kitty/monitor.conf` (or merged into an existing category file if appropriate).
  - **(b) compositor-side note** in `docs/repro/h18-monitor-disconnect-survival.md` if the cause is COSMIC-specific and config-only kitty cannot fix it.
  - **(c) helper-shaped restart wrapper** documented in the repro doc (a script that detects monitor disconnect and re-spawns the kitty session). NOT shipped in this change; documented as a workaround.
  - **(d) bug-report-only** if probe-01 surfaces clear evidence of a kitty defect that needs upstream attention. Document the report URL and the workaround in the repro doc.
- Linux-first delivery; macOS deferred (likely doesn't exhibit the issue, but capture status in the repro doc).

## Capabilities

### New Capabilities

- `kitty-monitor-survival`: behavioural contract that kitty windows survive a monitor disconnect — they do NOT process-exit, the OS windows that lived on the gone-monitor migrate to a remaining monitor (or to the primary display), and any running shell processes inside those windows continue uninterrupted. Covers the monitor-disconnect axis only; suspend/resume is a sibling concern.

### Modified Capabilities

None expected. If the remediation is (a) and lives in a new `monitor.conf`, `kitty-config-management` already permits per-topic `*.conf` files under the managed payload dir — no requirement-level change.

## Impact

- **New top-level paths (post-promotion):** `config/kitty/monitor.conf` (if remediation (a) lands), `docs/repro/h18-monitor-disconnect-survival.md`. **NO integration test** in `tests/integration/` — the harness cannot synthesise a real monitor hot-plug; the manual repro is the load-bearing verification.
- **Edited files:** `config/kitty/kitty-setup.conf` (one new `include` line if (a) lands).
- **Hypothesis dirs:** `tmp/h18-monitor-disconnect-survival/`, plus `tmp/probes/phase1-monitor-disconnect-survival/<NN>-<slug>.md` for external-system probes.
- **System mutations:** install copies the new `.conf` file (if (a)) into the managed dir; uninstall removes it via the existing surgical-removal contract.
- **Out of scope:** suspend/resume crash (sibling change `phase1-suspend-resume-survival` if needed), image-paste (§7), paste preservation (§4 — paused), Phase 2 scenes.
