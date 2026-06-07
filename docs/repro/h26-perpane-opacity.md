# h26 — kitty background-opacity is OS-window scope only

Decides `phase2-scene-polish` #4 (alpha-in-color → opacity). The user asked
whether a color's alpha (`#rrggbbaa`) could be split off and applied as opacity
to a single pane — or at least a single tab. The answer determines whether we
honor the alpha (per-pane/per-tab translucency) or strip it.

## Why

`normalize_color` accepts hex; a user may type `bg=#001f3faa` expecting the
`aa` to make that pane translucent. Before speccing the behavior we must know,
empirically, at what scope kitty applies background opacity — per pane, per tab,
or per OS window — because that dictates whether the alpha can mean anything
useful where it was typed (on a single pane's `bg`).

## Manual repro

Host: kitty 0.47.1, Pop!_OS 24.04 (Wayland/COSMIC). Scripts:
`tmp/h26-perpane-opacity/run.py` (per-pane) and `run_tabs.py` (per-tab). Both
spawn an isolated kitty with `dynamic_background_opacity yes`, drive it over the
remote-control socket, and read the observable from `kitten @ ls`.

**Per-pane** (`run.py`): open 2 panes in one tab, set opacity on pane 1 only.

```
panes: 2  ids=[1, 2]
OS-window keys with 'opac': {'background_opacity': 1.0}
window[0] keys with 'opac': {}                 # windows carry NO opacity field
set-background-opacity --match id:1 0.5  -> rc=0   # targeted pane 1 only
OS-window background_opacity AFTER : 0.5           # the WHOLE window changed
=== VERDICT: PER-OS-WINDOW ===
```

**Per-tab** (`run_tabs.py`): 2 tabs in one OS window, set opacity targeting a
window in tab 1.

```
OS windows: 1   tabs in osw[0]: 2
  tab[0] windows=[1]  opac_fields={}             # tabs carry NO opacity field
  tab[1] windows=[2]  opac_fields={}
set-background-opacity --match id:1 (tab1) 0.5  ->  OS-window 1.0 -> 0.5
=== VERDICT: OS-WINDOW ONLY: tab-2 shares tab-1's opacity ===
```

## Linux Status

**Verified (2026-06-07, kitty 0.47.1).** Background opacity is a property of the
**OS window** (a single GPU surface). `kitten @ set-background-opacity --match`
matches a *window* but applies opacity to the OS window that contains it; `ls`
exposes `background_opacity` only on the OS-window object — never on a tab or a
window (pane). There is **no per-pane and no per-tab opacity**. Different OS
windows can each hold their own value; tabs and panes within one OS window share
the single value.

## Consequence for the design

A color's alpha typed on a per-pane `bg` (or `tab_accent`) cannot become a
per-pane/per-tab translucency. Mapping it to the OS-window opacity would dim
unrelated tabs sharing the window — surprising and unwanted. Therefore
`normalize_color` **accepts 4/8-digit hex and strips the alpha**, returning the
solid color. Opacity stays the explicit, OS-window-scoped
`my-kitty os-window opacity` gesture.

## macOS Status

Deferred-with-reason. The scope of `set-background-opacity` is a property of
kitty's compositing model, not of the Linux display server; the conclusion is
expected to hold on macOS. The repo's macOS path is deferred until the Pop!_OS
path is stable (README), so no macOS run was performed.

## Attempted alternatives

- **Per-pane opacity via `--match id:`** — measured (run.py); changes the whole
  OS window. Rejected.
- **Per-tab opacity** — measured (run_tabs.py); tabs share the OS-window value.
  Rejected.
- **Map alpha → OS-window opacity automatically** — rejected by design: it would
  alter unrelated tabs in the same window.

## Known limitations

- Verified only on kitty 0.47.1. A future kitty that adds per-window opacity
  would let us revisit honoring the alpha; re-run both probe scripts to check.
- The probe uses an isolated spawned kitty; it does not exercise a tiling-WM or
  multi-monitor compositor, which do not affect the opacity scope.
