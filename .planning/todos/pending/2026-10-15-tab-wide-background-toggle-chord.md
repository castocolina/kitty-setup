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

## Research (2026-10-15, kitty 0.49.2, evidence in `tmp/h38-tab-bg-chord-research/`)

Introspected kitty's own default map (`definition.iter_all_maps()`: 134 maps, 80 all-OS, 54 macOS):

- **Linux:** the only ctrl+shift+alt defaults are `ctrl+shift+alt+t` (set_tab_title) and
  `ctrl+shift+alt+h`. `ctrl+shift+alt+c` is **free**, and so is `ctrl+shift+alt+b`.
- **macOS:** opt+cmd defaults are only `s`, `r`, `k`, `h`, `,`, `page_up`, `page_down`.
  `opt+cmd+c` (= `cmd+alt+c`, kitty treats `opt`/`alt`/`option` as one modifier, verified through
  `parse_shortcut`) is **free**, and so is `opt+cmd+b`.
- The payload itself uses only `ctrl+shift+alt+{k,d}`; nothing on `c` or `b`.
- **So the owner's Modifier+Alt+C works on both OSes** as far as kitty defaults go. The only
  problem is internal: Phase 6 already assigns `ctrl+shift+alt+c` to the focused-**pane** color
  cycle.
- Not verified: macOS system shortcuts and KDE/compositor grabs for these chords (Phase 10 and the
  R2.8 oracle are the gates).

## Solution

TBD, decide in discuss-phase. Options:

1. **Same chord, wider scope:** Phase 6 gets a tab-wide mode (`--tab` on
   `my-kitty window cycle-color`), still one CLI path. No new chord, but pane and tab scope then
   need two chords or a modifier to tell them apart.
2. **Second chord, same family (suggested):** keep `ctrl+shift+alt+c` for the pane and add
   `ctrl+shift+alt+b` (**b**ackground, whole tab) on Linux and `opt+cmd+b` on macOS. Both free
   per the research; `b` is a mnemonic for background. Avoid making `ctrl+shift+alt+c` a key-sequence
   prefix (`ctrl+shift+alt+c > t`): it would collide with the chord Phase 6 maps directly.
3. Use `ctrl+shift+alt+c` for the tab and pick another free chord for the pane.

Implementation notes:

- Reuse `scenes/background.set_window_background` / `scenes/accent.set_tab_accent` and
  `palette.toml`; stay stateless via `kitten @ get-colors --match`.
- Phase 6 blocker applies: `window background none` fails on kitty 0.49.0 (reset needs its own
  mechanism).
- Budget <=300 ms per press, measured in an integration test; the R2.8 oracle must be green with
  the new chord present.
