# Design — phase1-curated-bindings-revert-defaults

## Context

The archived `phase1-curated-bindings` change (merged 2026-05-07) shipped a six-category keybinding catalog that overrode 13 kitty default chords. The user's daily-driver experience with that catalog surfaced two problems:

1. **Vim-style window navigation (`h`/`j`/`k`/`l`) is a foreign idiom for this user.** The user does not use vim as their primary editor. The hjkl mapping was lifted from wezterm conventions because `docs/requirements.md` §5 spelled it out, but the requirement itself was authored without weighing the cost of clobbering kitty defaults `show_scrollback`, `scroll_line_down`, `scroll_line_up`, and `next_layout`. The chord that hurt most was `ctrl+shift+l`: the user's actual workflow is open a new window with `ctrl+shift+enter`, then cycle layouts with `ctrl+shift+l` to flip stacked → side-by-side. The hjkl rebind broke step 2.

2. **The `--location=vsplit/hsplit` chord pair is a placebo without `enabled_layouts splits`.** kitty's `launch --location=vsplit`/`hsplit` is only honoured under the `splits` layout. The catalog ships no `enabled_layouts` directive, so the active layout is whatever kitty's default order picks first (typically `tall`). Under that layout `--location=vsplit` and `--location=hsplit` are both ignored — the new window goes where the layout dictates. So `ctrl+shift+\` and `ctrl+shift+/` produce the same visible result as `ctrl+shift+enter`, and the `ctrl+shift+/` chord additionally costs the user kitty's `search_scrollback` default. Three chords spending two override slots to deliver one behaviour.

The user's restated goal: **curate kitty defaults, do not replace them**. The catalog should make kitty's existing chords discoverable under `my-kitty keys` (file-basename = category attribution), ship net-new behaviours only on chords kitty leaves free, and otherwise leave kitty's idiom intact. `docs/requirements.md` §5 will be amended to match.

## Decisions

### D1. Drop vim-style window navigation; restate kitty defaults

`config/kitty/window-nav.conf` is rewritten to contain redundant rebinds of kitty's own window-nav chords. The category continues to exist for `my-kitty keys` grouping; its content stops semantically overriding kitty.

**Action:**

```
# config/kitty/window-nav.conf (target shape)
map ctrl+shift+]  next_window              # redundant; kitty default restated
map ctrl+shift+[  previous_window          # redundant; kitty default restated
map ctrl+shift+f  move_window_forward      # redundant; kitty default restated
map ctrl+shift+w  close_window             # redundant; kitty default restated
```

Released back to kitty defaults: `ctrl+shift+h` (`show_scrollback`), `ctrl+shift+j` (`scroll_line_down`), `ctrl+shift+k` (`scroll_line_up`), `ctrl+shift+l` (`next_layout`). The pre-change `f` → `next_window` rebind also reverts — kitty's `move_window_forward` is the default.

**Rationale:** the user's stated mental model is "kitty defaults, curated". `next_window`/`previous_window` cover focus-cycling adequately on `]`/`[`; directional navigation is rarely needed in kitty's tiling model because most users have ≤2 splits per tab. The scrollback pager (`h`) and per-line scroll (`j`/`k`) are useful kitty features that should not be silently lost. The layout cycle (`l`) is the user's load-bearing chord — restoring it is the immediate trigger for this change.

**Rejected:** keep vim hjkl on a different modifier (e.g. `ctrl+shift+alt+{h,j,k,l}`). Rejected because the user does not want vim navigation at all; not "vim on a different chord", but "no vim".

### D2. Drop the vsplit/hsplit chord pair; use kitty's compose model

`config/kitty/windowing.conf` keeps only the three cwd-inheriting creator chords:

```
map ctrl+shift+t      launch --type=tab --cwd=current
map ctrl+shift+n      launch --type=os-window --cwd=current
map ctrl+shift+enter  launch --cwd=current
```

`ctrl+shift+\` and `ctrl+shift+/` are removed. The user's split workflow becomes kitty-native: `ctrl+shift+enter` opens a new window, `ctrl+shift+l` (restored by D1) cycles the layout to flip stacked ↔ side-by-side.

**Rationale:** without `enabled_layouts splits` pinned, the `--location=vsplit/hsplit` chords are no-ops dressed up as a feature. Pinning `enabled_layouts splits` would force a single layout on the user and remove kitty's layout-cycle workflow — strictly worse for a user who actively uses `next_layout`. The user explicitly opted for "no nos compliquemos" — drop the chords, accept kitty's compose model.

`ctrl+shift+/` returns to kitty's default `search_scrollback`; `ctrl+shift+\` returns to whatever kitty's default is on that chord on each OS (`new_window_with_cwd` on some versions, unbound on others — kitty's defaults stand either way).

**Rejected:** pin `enabled_layouts splits` and ship dedicated split chords on `ctrl+shift+alt+\` and `ctrl+shift+alt+/`. Rejected on the user's explicit preference for kitty's compose model.

### D3. Drop the `]`/`[` tab-nav rebind; restate kitty tab-nav defaults

`config/kitty/tab-nav.conf` is rewritten to redundant rebinds of kitty's existing tab-nav defaults:

```
map ctrl+shift+right  next_tab               # redundant; kitty default restated
map ctrl+shift+left   previous_tab           # redundant; kitty default restated
map ctrl+shift+.      move_tab_forward       # redundant; kitty default restated
map ctrl+shift+,      move_tab_backward      # redundant; kitty default restated
map ctrl+shift+q      close_tab              # redundant; kitty default restated
```

`ctrl+shift+]`/`[` are released back to kitty defaults (`next_window`/`previous_window`, which D1 then restates from the `window-nav.conf` side as redundant rebinds).

**Rationale:** kitty already binds tab navigation on `ctrl+shift+right/left/./,/q`. The pre-change `]`/`[` → tab-nav rebind was a wezterm-influenced borrowing that the user does not need. Restating kitty's defaults under `tab-nav.conf` keeps the category section in `my-kitty keys` populated without semantic overrides.

**Rejected:** drop the tab-nav category entirely (no redundant rebinds, kitty defaults appear under "kitty defaults" in `my-kitty keys`). Rejected because the `tab-nav` category in `my-kitty keys` is a user-discoverability feature — the user wants to see tab chords grouped under "tab-nav" in the report, not scattered under "kitty defaults".

### D4. Drop the `ctrl+shift+0` font-reset rebind; restate kitty's `ctrl+shift+backspace`

`config/kitty/font-zoom.conf` becomes:

```
map ctrl+shift+=          change_font_size all +2.0   # redundant
map ctrl+shift+-          change_font_size all -2.0   # redundant
map ctrl+shift+backspace  change_font_size all 0      # redundant; kitty default
```

`ctrl+shift+0` returns to kitty default `tenth_window`.

**Rationale:** kitty already maps `ctrl+shift+backspace` to `change_font_size all 0`. The pre-change `0` → font-reset override was based on a probe-13 misreading of kitty defaults (the design document called `0` a kitty default for reset; it was not). Restating on kitty's actual reset chord costs no user-visible chord — `tenth_window` is a niche feature, but it is kitty's default and there is no reason to override it.

**Rejected:** drop the font-zoom category. Same rationale as D3 — categorisation under `my-kitty keys` is a discoverability feature worth one redundant-rebind file.

### D5. Move instant-clear to a per-OS-native modifier; relax the cross-OS literal-parity rule for this one chord

`config/kitty/clear.conf` releases `ctrl+shift+x` back to kitty's `scroll_to_prompt 1` (a shell-integration jump that kitty's shell integration enables out of the box on bash/zsh/fish/etc.). The instant-clear behaviour is bound to per-OS native modifiers:

```
# Linux
map super+k          combine : clear_terminal scrollback active : send_text normal,application \x0c
map ctrl+shift+alt+k combine : clear_terminal scrollback active : send_text normal,application \x0c

# macOS
map cmd+k            combine : clear_terminal scrollback active : send_text normal,application \x0c
map ctrl+shift+alt+k combine : clear_terminal scrollback active : send_text normal,application \x0c
```

The per-OS lines are gated by kitty's `os.platform` conditional include or by shipping two files (`clear.conf` referencing `clear-linux.conf`/`clear-mac.conf`); the exact mechanism is an implementation detail of the apply phase. The `ctrl+shift+alt+k` fallback is shipped on both OSes so the chord is reachable if Super is grabbed by a compositor (today COSMIC does not grab `super+k`, but the Super key is compositor-owned and grabs can appear in future Pop!_OS / COSMIC releases or under different DEs).

`kitty-curated-bindings`'s "Pin kitty_mod for cross-OS chord parity" requirement is amended with an explicit carve-out: this one chord may diverge across OSes. The carve-out is justified by the iTerm-parity goal stated in `docs/requirements.md` §2 ("iTerm Cmd+K parity"). Every other curated chord remains literally identical across Linux and macOS.

**Rationale:** the user's mental model on the clear chord is iTerm Cmd+K. On macOS, Cmd+K is the natural binding (kitty's `kitty_mod` defaults to `cmd` there). On Linux, the closest cultural analogue is Super+K (the kernel-level Super-prefixed keymap convention shared by Pop!_OS, GNOME, KDE, etc.). The previous catalog put clear on `ctrl+shift+x`, which (a) overrode `scroll_to_prompt 1` and (b) did not match either OS's iTerm muscle memory.

**Rejected:** keep literal parity on `ctrl+shift+alt+k` and drop `super+k`/`cmd+k`. Rejected because the user explicitly stated they want the iTerm-parity chord — and accepting the per-OS divergence is the cost of that user-ergonomics win. The fallback chord preserves cross-OS literal parity for any user that wants it.

**Rejected:** keep clear on `ctrl+shift+x` and accept the loss of `scroll_to_prompt 1`. Rejected because the user's broader stance is "curate kitty defaults, do not replace them" — every chord override needs to clear a higher bar than "no obvious user complaint".

### D6. Amend `docs/requirements.md` §5

The pre-change `requirements.md` line 14 reads:

> "Curated keybinding set, no conflicts, identical bindings on Linux and macOS, covering at minimum: tabs (open/close/next/prev/move), windows and splits (open/close/horizontal/vertical), vim-style window navigation (h/j/k/l), font zoom (+/-/reset), detach window or tab to another target, broadcast input across windows, URL hints."

The amended text drops the vim-style mention and the directional-split mention, and codifies the instant-clear carve-out on identical-bindings:

> "Curated keybinding set, no conflicts, identical bindings on Linux and macOS for every chord except the instant-clear chord (which matches host-OS iTerm convention — Cmd+K on macOS, Super+K on Linux), covering at minimum: tabs (open/close/next/prev/move), windows (open/close/cycle), font zoom (+/-/reset), detach window or tab to another target, broadcast input across windows, URL hints."

**Rationale:** the requirement text is the load-bearing spec for §5. Without this edit, the change ships a catalog that intentionally violates the literal text — exactly the kind of silent drift CLAUDE.md prohibits. Editing the requirement aligns spec to user-stated intent.

### D7. Prune and update `intentional-overrides.conf`

After D1–D5 land, the allow-list shrinks materially. Remaining override entries:

```
# windowing.conf — cwd-inheriting replacements for default tab/window/enter chords.
ctrl+shift+t       # overrides new_tab
ctrl+shift+n       # overrides new_os_window
ctrl+shift+enter   # overrides new_window

# clear.conf — instant clear on per-OS native chords + cross-OS fallback.
super+k            # Linux: new chord; no kitty default
cmd+k              # macOS: new chord; no kitty default
ctrl+shift+alt+k   # cross-OS fallback; no kitty default
```

Every other prior allow-list entry (chord-by-chord rationale for hjkl/f/]/[/0/x/`/`\`) is removed — those chords no longer override kitty defaults. The introspection module's same-(chord, action) dedupe (added under `phase1-curated-bindings` and made canonical in `kitty-binding-introspection`) keeps redundant rebinds healthy without per-line allow-list entries (kitty's parsed keymap still surfaces the redundant entries, but the dedupe is what suppresses the false "two of ours = conflict" — no spec change to introspection is needed).

**Rationale:** the allow-list is a maintenance liability. Every entry needs a one-line reason and a reviewer-enforced justification. Shrinking the list from ~17 entries to 6 reduces drift risk.

### D8. Manual repro and integration test surface

Two hypotheses cover this change. Both use the autonomous `KITTI_INTEGRATION=1` harness.

- **h<NN>a — `bindings-revert`**: every reverted chord (`h`, `j`, `k`, `l`, `]`, `[`, `f`, `0`, `\`, `/`) MUST resolve to its kitty default action when `KittySession.list_keymap()` is queried after the change is applied. Manual repro doc records: open a kitty session, press `ctrl+shift+h` → `show_scrollback` pager opens; press `ctrl+shift+l` → layout cycles; etc.

- **h<NN>b — `bindings-clear-relocation-superK`**: instant clear on `super+k` (Linux) and `cmd+k` (macOS) MUST wipe screen + scrollback in <200 ms (re-uses the existing `kitty-instant-clear` scenario harness with a new chord). Manual repro doc records the Linux verification on Pop!_OS 24.04 + COSMIC + kitty 0.46.x with `super+k`, and a macOS "deferred" or "verified" section depending on access.

The vsplit/hsplit chord pair is being deleted, so no integration test backs that deletion — `make doctor` is the regression detector (no `--location=vsplit/hsplit` chord shows up in `my-kitty keys`).

### D9. macOS Status — clear chord

Linux is the first-class target. `super+k` on COSMIC is verified by the implementer at apply time. `cmd+k` on macOS is **deferred verification** — no Mac host is available for this change. The repro doc carries a `## macOS Status: deferred` note with: "macOS chord `cmd+k` is bound from the same `clear.conf`-equivalent file; verify on next available macOS host. Until verified, the fallback chord `ctrl+shift+alt+k` is the documented macOS path." This matches the precedent set by `phase1-monitor-disconnect-survival`.

## Open questions

- None for the user. All three previously open questions (Q1 super+k vs ctrl+shift+alt+k; Q2 splits chord pair; Q3 requirements.md edit) were resolved before this design was authored.

## Non-goals

- Pinning `enabled_layouts` to any specific layout. Out of scope; kitty's default layout cycle is preserved.
- Adding any new categories. Out of scope; the catalog still ships seven category files (`windowing`, `clear`, `tab-nav`, `window-nav`, `font-zoom`, `detach`, `broadcast`, `url-hints`, `monitor`).
- Touching `kitty-binding-introspection`. The same-(chord, action) dedupe handles the new layout (more redundant rebinds, fewer semantic overrides) without spec change.
- Touching `phase1-paste-preservation` or `phase1-monitor-disconnect-survival`. Both are unrelated.

## Rollback

Rolling back this change restores the prior catalog by re-applying the archived `2026-05-07-phase1-curated-bindings` spec deltas and `docs/requirements.md` line 14 text. No data migrations, no config-state surgery — every file edited here is a payload `.conf` or a markdown spec.
