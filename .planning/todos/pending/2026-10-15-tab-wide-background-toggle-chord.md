---
created: 2026-10-15T12:13:10.983Z
title: Toggle whole-tab background with a chord
area: general
severity: minor
files:
  - .planning/ROADMAP.md (Phase 6)
  - .planning/REQUIREMENTS.md (R4.1-R4.4)
  - tmp/h38-tab-bg-chord-research/ (local, gitignored)
---

## Problem

kitty switches layout with Modifier (ctrl+shift on Linux, cmd on macOS) + `L`. The owner wants an
equivalent chord that toggles/alternates the **entire background of a tab** (all its windows). The
owner's proposal: Modifier + Alt + C, "or any other free chord".

## Ergonomic rule (owner, 2026-10-15)

Same letter on both OSes, only the common modifier changes: `cmd+X` on macOS is `ctrl+shift+X` on
Linux, and `cmd+alt+X` is `ctrl+shift+alt+X`. Never a different key per OS.

## Research (2026-10-15, kitty 0.49.2, evidence in `tmp/h38-tab-bg-chord-research/`)

Introspected kitty's own default map (`definition.iter_all_maps()`: 134 maps, 80 all-OS, 54 macOS).
Under the rule above, one letter is one pair:

| Letter | Linux | macOS | Free in kitty defaults |
|--------|-------|-------|------------------------|
| `c` | `ctrl+shift+alt+c` | `cmd+alt+c` | yes, both |
| `b` | `ctrl+shift+alt+b` | `cmd+alt+b` | yes, both |

- Linux ctrl+shift+alt defaults are only `t` (set_tab_title) and `h`; macOS opt+cmd defaults are
  only `s`, `r`, `k`, `h`, `,`, `page_up`, `page_down`.
- kitty treats `opt`, `alt` and `option` as one modifier (verified through `parse_shortcut`), so
  `cmd+alt+c` and `opt+cmd+c` are the same chord.
- The payload uses only `ctrl+shift+alt+{k,d}`; nothing on `c` or `b`.
- The owner's Modifier+Alt+C works on both OSes. The only conflict is internal: Phase 6 already
  assigns `ctrl+shift+alt+c` (and so `cmd+alt+c`) to the focused-**pane** color cycle.
- Not verified: macOS system shortcuts and KDE/compositor grabs (Phase 10 and the R2.8 oracle).

## Solution

TBD, decide in discuss-phase. Options:

1. **Same chord, wider scope:** Phase 6 gets a tab-wide mode (`--tab` on
   `my-kitty window cycle-color`), still one CLI path. No new chord.
2. **Second chord, same family:** keep `c` for the pane and add `b` (**b**ackground, whole tab) as
   `ctrl+shift+alt+b` / `cmd+alt+b`. Avoid a key-sequence prefix (`ctrl+shift+alt+c > t`): it would
   collide with the chord Phase 6 maps directly.
3. Swap roles: `c` for the tab, another free letter for the pane.

Implementation notes:

- Reuse `scenes/background.set_window_background` / `scenes/accent.set_tab_accent` and
  `palette.toml`; stay stateless via `kitten @ get-colors --match`.
- Phase 6 blocker applies: `window background none` fails on kitty 0.49.0 (reset needs its own
  mechanism).
- Budget <=300 ms per press, measured in an integration test; the R2.8 oracle must be green with
  the new chord present.
