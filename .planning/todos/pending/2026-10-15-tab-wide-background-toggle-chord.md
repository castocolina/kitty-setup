---
created: 2026-10-15T12:13:10.983Z
title: Toggle whole-tab background with a chord
area: general
severity: minor
files:
  - .planning/ROADMAP.md (Phase 6)
  - .planning/REQUIREMENTS.md (R4.1-R4.4)
---

## Problem

kitty switches layout with Modifier (ctrl+shift on Linux, cmd on macOS) + `L`. The owner wants an
equivalent chord that toggles/alternates the **entire background of a tab** (all its windows), the
suggestion being Modifier + Alt + C "or any other free chord".

## Solution

TBD. Overlap to resolve in discuss-phase:

- Phase 6 (Pane Color Cycle, R4) already claims `ctrl+shift+alt+c` for the **focused pane**
  background + tab accent, last-write-wins in a multi-pane tab (D-04). This todo is a different
  scope (every pane in the tab), so it needs its own chord, or Phase 6 gets a tab-wide mode
  (`--tab` flag on `my-kitty window cycle-color`, same CLI path as the chord).
- Pick a chord verified free on both OSes' default maps (Phase 3/4 oracle R2.8 gates it); candidates
  must avoid `ctrl+shift+alt+c`, `ctrl+shift+alt+d`, `ctrl+shift+alt+k`, `ctrl+shift+m/i/d`.
- Reuse `scenes/background.set_window_background` / `scenes/accent.set_tab_accent` and the
  palette in `palette.toml`; stateless via `kitten @ get-colors --match`.
- Known blocker for Phase 6: `window background none` fails on kitty 0.49.0 (reset needs its own
  mechanism); the same applies here.
- Budget: <=300 ms per press, measured in an integration test.
