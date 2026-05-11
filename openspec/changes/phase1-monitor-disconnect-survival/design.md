## Context

Phase 1 §6 of `docs/requirements.md` calls for: "Kitty survives suspend/resume and monitor disconnect — no crash, no exit." This change is scoped to the monitor-disconnect axis only. User-confirmed (2026-05-07) host context:

* Pop!_OS 24.04, COSMIC compositor (Wayland-only — no X11 fallback).
* kitty 0.46.2 installed under `~/.local/kitty.app/`.
* Multi-monitor setup with at least one external monitor that gets unplugged regularly.
* Failure mode (user-reported): kitty windows on the external monitor disappear when it's unplugged. Processes inside those windows are lost.

Foundation in place from `phase1-curated-bindings` (archived 2026-05-07): kitty install, doctor green, surgical install/uninstall, hypothesis-driven workflow.

## Goals / Non-Goals

**Goals:**

* Characterise the failure mode with named probes (R6) — what exactly happens when the monitor unplugs?
* Ship the smallest config-only remediation that resolves it on the user's daily host (Pop!_OS Wayland + COSMIC).
* If config-only is impossible, ship a documentation-only remediation (compositor-side guidance, helper-shaped workaround, or upstream-bug-report pointer).
* Capture the behavioural contract as the new `kitty-monitor-survival` capability so a future regression is visible.
* No autonomous integration test — the failure mode is hot-plug-dependent and the harness cannot synthesise it. Manual repro is the load-bearing verification.

**Non-Goals:**

* Suspend/resume (sibling change `phase1-suspend-resume-survival`).
* Multi-compositor portability (GNOME, KDE, sway, wlroots-based) — verify on the user's daily host (COSMIC); document the gap for other compositors.
* Wayland upstream contributions — if the bug is in kitty's Wayland output handling, the right move is an upstream bug report + a documented workaround in this repo, not a fix patched into our payload.
* Cross-OS — macOS likely doesn't exhibit this (different windowing model), deferred.

## Decisions

### D1: Probe-first, three named probes before any config or workaround

Per `docs/agent-iteration.md` R6, every external-system assumption gets a probe in `tmp/probes/phase1-monitor-disconnect-survival/`. Three planned up front:

* **probe-01: characterise the failure mode.** Start kitty with two visible OS windows on the external monitor (use `--start-as=normal`, place windows manually). Capture: process pid via `pgrep -a kitty`, window list via `kitty @ ls --to=<socket>`, and `journalctl --user --since "5 minutes ago"` snapshot. Unplug the external monitor. Capture the same triple again. Verdict: did the kitty process exit (pid disappeared)? Did kitty itself migrate the windows? Did the compositor kill the surfaces but kitty stayed alive? Did `kitty @ ls` still report the windows after disconnect?
* **probe-02: kitty config surface for output-leave handling.** Run `~/.local/kitty.app/bin/kitty --debug-config 2>&1 | grep -iE 'output|monitor|display|surface|migrate'` and inspect kitty's docs at `~/.local/kitty.app/share/doc/kitty/html/conf.html` for any setting that controls behaviour on output disconnect. Verdict: list the knobs (if any) and document each one's effect.
* **probe-03: COSMIC compositor logs around disconnect.** Run `journalctl --user --since "5 minutes ago" --grep 'cosmic|kitty|wl_output|wl_surface'` immediately after the probe-01 disconnect. Verdict: does COSMIC log a kill of the kitty surfaces, and if so what's the reason? Is there a `wl_output.leave` followed by a surface destruction?

Each probe writes its verdict + the design decision or code path that uses it.

### D2: Single hypothesis under `tmp/h18-monitor-disconnect-survival/`

Manual hypothesis (no `run.py` autonomous probe — the harness cannot synthesise a monitor hot-plug). Contents:
- `repro.md` — manual repro steps, expected behaviour, observed behaviour, attempted fixes table.
- `draft.conf` — candidate kitty config snippet (if D3 picks branch (a)).
- `notes.md` — running notes during the investigation, including any compositor-side experiments tried.

The user runs the repro on their daily host. Each iteration is logged in `notes.md` with date + draft.conf state + observed outcome.

### D3: Promote based on probe verdict

Four branches:

* **Branch (a) — kitty config fix.** If probe-02 surfaces a knob (or a combination) that resolves the regression, ship it in `config/kitty/monitor.conf` with a top-of-file WHY block citing probe-01 + probe-02 verdicts.
* **Branch (b) — compositor-side note.** If probe-03 surfaces COSMIC-specific behaviour and kitty has no config-side workaround, the remediation is documentation only: a paragraph in `docs/repro/h18-monitor-disconnect-survival.md` describing the COSMIC behaviour, linking the user to upstream COSMIC issues, and noting any workaround (e.g. moving windows to the primary monitor before unplug).
* **Branch (c) — helper-shaped workaround documented.** If the bug is real and there's no kitty-config or compositor-config fix, a `scripts/monitor-watch.sh`-style wrapper that detects monitor disconnect and either re-spawns affected kitty windows on the remaining monitor or restores them from a session snapshot. The script is NOT shipped in this change; it's described in the repro doc, scoped as a follow-up change `phase1-monitor-disconnect-helper` if dogfooding shows the user wants it.
* **Branch (d) — bug-report-only.** If probe-01 surfaces clear evidence of a kitty defect (e.g. kitty hard-crashes on `wl_output.leave`), file an upstream bug report at github.com/kovidgoyal/kitty, link the issue from `docs/repro/h18-monitor-disconnect-survival.md`, and document the workaround for users until the upstream fix lands.

### D4: Capability shape — `kitty-monitor-survival`

The new capability is a single behavioural contract: "when an external monitor is disconnected, the kitty process does NOT exit, the OS windows that were on that monitor migrate to a remaining monitor (or to the primary display), and any running shell processes inside those windows continue uninterrupted." Three scenarios:
1. Kitty process survives the disconnect (PID unchanged).
2. Windows migrate to the remaining monitor.
3. Running processes inside surviving windows continue (no SIGHUP, no shell exit).

Backing the spec: the manual repro on the user's daily host. There is no autonomous test backing this requirement — explicitly noted in the spec.

## Risks / Trade-offs

* **Risk:** Probe-01 finds the failure is compositor-specific (COSMIC kills surfaces on `wl_output.leave`) and there's nothing kitty can do. → **Mitigation:** Branch (b) — document the compositor behaviour, push the fix upstream to COSMIC.
* **Risk:** No autonomous test backs the spec — a future regression is invisible to CI. → **Mitigation:** the manual repro is dated and re-runnable; the user verifies on each release tag. If dogfooding shows the regression returns, escalate to upstream kitty.
* **Risk:** macOS may not reproduce the bug (different windowing model). → **Mitigation:** Linux-first per the §5 precedent; macOS deferred-with-note in the repro doc.
* **Risk:** Suspend/resume bug shares root cause with monitor-disconnect bug. → **Mitigation:** if probe-01 reveals shared cause, fold suspend/resume into this change as a second hypothesis (`tmp/h18b-suspend-resume/`) rather than splitting into a sibling change.
* **Risk:** Branch (c) helper script becomes load-bearing for daily use. → **Mitigation:** if so, scope a follow-up change `phase1-monitor-disconnect-helper` to ship it. Keep this change documentation-only until the helper proves necessary.

## Open Questions

1. **Is the failure deterministic on every monitor unplug, or intermittent?** Resolve via probe-01 (run 5 disconnects, count failures).
2. **Does the failure depend on which window is focused at disconnect time?** (Active monitor vs unplugged monitor.) Resolve via probe-01.
3. **Does kitty's `--single-instance` mode change the behaviour?** Some daemonised modes survive client-window kills better than non-daemonised. Worth probing if probe-01 shows the process exits.
4. **Does `allow_remote_control` setting affect the behaviour?** Long-shot; check if probe-02 surfaces it as a related knob.
5. **What does kitty do on `wl_output.leave` in source?** Read `kitty/glfw/cocoa.m` (no — that's macOS) and `kitty/glfw/wl_init.c` for the Wayland output handling. Out of scope for this round; flag if probe-01/03 verdicts demand a code dive.
