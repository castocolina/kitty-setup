## Why

The shipped `phase1-curated-bindings` change interpreted `docs/requirements.md` §5 literally — "vim-style window navigation (h/j/k/l)" and "splits (horizontal/vertical)" — and produced a catalog that REPLACES 13 kitty default chords with custom actions. Daily-driver use exposed the cost:

- `ctrl+shift+l` (kitty default `next_layout`) was rebound to `neighboring_window right`. The user's actual workflow — `ctrl+shift+enter` to open a new window, then `ctrl+shift+l` to flip the layout from stacked to side-by-side — broke. The user does not use vim; the vim-style mapping was a wezterm-influenced borrowing, not a kitty idiom.
- `ctrl+shift+h` (kitty default `show_scrollback`, the pager) was clobbered.
- `ctrl+shift+j`/`k` (kitty defaults `scroll_line_down`/`up`) were clobbered.
- `ctrl+shift+/` (kitty default `search_scrollback`) was repurposed for `hsplit` — but `launch --location=hsplit` is only honoured by kitty's `splits` layout, and the payload does not pin `enabled_layouts splits`. The chord today produces the same visual result as `ctrl+shift+enter` (generic new window in whatever the current layout dictates), so the vsplit/hsplit dichotomy is fictitious in addition to costing the scrollback-search chord.
- `ctrl+shift+]`/`[` (kitty defaults `next_window`/`previous_window`) were rebound to `next_tab`/`previous_tab`, while tab-nav has its own kitty defaults on `ctrl+shift+right`/`left`.
- `ctrl+shift+0` (kitty default `tenth_window`) was rebound to font reset; kitty already binds reset on `ctrl+shift+backspace`.
- `ctrl+shift+x` (kitty default `scroll_to_prompt 1`, a shell-integration jump) was rebound to instant clear.

The user's actual goal — restated this session — is **curate kitty defaults, do not replace them**. The catalog should make the defaults discoverable under `my-kitty keys` (file-basename = category grouping), pin a small set of net-new behaviours on free chords, and otherwise leave kitty's idiom intact.

## What Changes

- **Drop vim-style window navigation from the curated catalog.** `config/kitty/window-nav.conf` is rewritten to restate kitty's own window-nav defaults (`ctrl+shift+]` next_window, `ctrl+shift+[` previous_window, `ctrl+shift+w` close_window, `ctrl+shift+f` move_window_forward) as redundant rebinds for category attribution. `ctrl+shift+h`/`j`/`k`/`l` are released back to their kitty defaults (`show_scrollback`, `scroll_line_down`, `scroll_line_up`, `next_layout`). The "focus next window in tab" entry on `ctrl+shift+f` reverts from `next_window` to kitty's default `move_window_forward`.
- **Drop the vsplit/hsplit chord pair.** `config/kitty/windowing.conf` keeps `ctrl+shift+t` (new_tab + cwd), `ctrl+shift+n` (new_os_window + cwd), and `ctrl+shift+enter` (new_window + cwd) — semantics-compatible cwd overrides of kitty defaults. The standalone `ctrl+shift+\` and `ctrl+shift+/` lines are removed. Users who want a horizontal/vertical split use kitty's compose model: open a new window with `ctrl+shift+enter`, then cycle layouts with `ctrl+shift+l`.
- **Revert tab-nav `]`/`[` rebind.** `config/kitty/tab-nav.conf` no longer maps `ctrl+shift+]`/`[` to tab actions. Tab navigation lives on kitty's existing defaults (`ctrl+shift+right`/`left` for next_tab/previous_tab; `ctrl+shift+.`/`,` for move_tab_forward/backward; `ctrl+shift+q` for close_tab) — all restated as redundant rebinds. `ctrl+shift+]`/`[` revert to kitty defaults `next_window`/`previous_window`.
- **Revert font-zoom `0` rebind.** `config/kitty/font-zoom.conf` drops the `ctrl+shift+0` → font-reset line. Font reset moves to `ctrl+shift+backspace` (kitty's own default chord for the action) as a redundant rebind. `ctrl+shift+0` returns to kitty default `tenth_window`.
- **Move instant-clear to a free chord.** `config/kitty/clear.conf` releases `ctrl+shift+x` back to `scroll_to_prompt 1` and binds clear on per-OS native chords: `super+k` on Linux, `cmd+k` on macOS (iTerm parity, user's stated mental model). A secondary fallback `ctrl+shift+alt+k` is shipped alongside so the chord is reachable if a compositor grabs `super+k` (COSMIC does not bind it today, but the Super key is compositor-owned and future grabs are out of our control). This is the one chord in the catalog that intentionally diverges across OSes — documented as such.
- **Keep net-new categories untouched.** `detach.conf` (`ctrl+shift+d`, `ctrl+shift+alt+d`), `broadcast.conf` (`ctrl+shift+i`), and `url-hints.conf` (`ctrl+shift+e`, redundant rebind of kitty's default for `open_url_with_hints`) — kitty has no other binding on these chords. Unchanged.
- **Amend `docs/requirements.md` line 14 (Phase 1 §5).** Drop "vim-style window navigation (h/j/k/l)" and "splits (horizontal/vertical)". Phase 1 §5 wording becomes: tabs (open/close/next/prev/move), windows (open/close/cycle), font zoom (+/-/reset), detach window or tab to another target, broadcast input across windows, URL hints, and an instant-clear chord on per-OS-native modifier. Spec text and rationale are checked into this change's spec deltas.
- **Amend `intentional-overrides.conf`.** Remove allow-list entries for chords that revert to kitty defaults. Keep entries only for: cwd-inheritance chords (`t`/`n`/`enter`), instant-clear (Linux: `super+k` + `ctrl+shift+alt+k`; macOS: `cmd+k` + `ctrl+shift+alt+k`), and any other chord that still semantically overrides a kitty default.

## Capabilities

### Modified Capabilities

- `kitty-curated-bindings`:
  - The "Curated catalog covers six categories" requirement MUST relax: window-nav becomes redundant-rebind-only (kitty defaults restated for category attribution), splits are dropped from the windowing category enumeration, and the catalog gains an explicit "follow kitty defaults wherever a category overlaps" rule.
  - The "Window/split navigation chords" requirement MUST drop vim-style h/j/k/l and replace with kitty's own next_window/previous_window/close_window/move_window_forward.
  - The "Tab navigation chords" requirement MUST drop the `]`/`[` → next_tab/previous_tab rebind and restate kitty's existing tab-nav defaults (`ctrl+shift+right`/`left`/`.`/`,`/`q`).
  - The "Font zoom chords" requirement MUST drop the `ctrl+shift+0` → font-reset rule and pin reset to kitty's default `ctrl+shift+backspace`.
  - The "Pin kitty_mod for cross-OS chord parity" requirement MUST add an explicit carve-out for the instant-clear chord — the one curated chord that intentionally diverges per OS.
- `kitty-instant-clear`:
  - The "Instant-clear chord does not collide with curated navigation chords" requirement MUST relax (h/j/k/l are no longer reserved by curated nav, so the prohibition disappears) and be replaced by: instant clear is bound to `super+k` on Linux and `cmd+k` on macOS, with `ctrl+shift+alt+k` as secondary fallback on both OSes. The chord MUST NOT be `ctrl+shift+x` (released back to `scroll_to_prompt 1`).
- `kitty-cwd-inheritance`:
  - The "New splits inherit the launching window's cwd" requirement MUST relax. With the vsplit/hsplit chord pair removed, cwd inheritance for splits is delivered through `ctrl+shift+enter` (new_window + cwd) — kitty places the new window per the active layout. The scenario MUST verify cwd on the chord that survives, not on `vsplit`/`hsplit` chords.

### New Capabilities

None.

## Impact

- **Edited files**: `config/kitty/windowing.conf` (drop vsplit/hsplit chord pair), `config/kitty/window-nav.conf` (drop hjkl, restate kitty defaults), `config/kitty/tab-nav.conf` (drop `]`/`[` rebind, restate kitty defaults on right/left/./,/q), `config/kitty/font-zoom.conf` (drop `0` rebind, restate kitty default on backspace), `config/kitty/clear.conf` (move chord off `x`, add Linux super+k / macOS cmd+k + ctrl+shift+alt+k fallback), `config/kitty/intentional-overrides.conf` (prune entries for chords that revert; add entries for cwd chords + new clear chords + remaining semantic overrides), `docs/requirements.md` (line 14 reword).
- **New paths**: one hypothesis dir under `tmp/h<NN>-bindings-revert/` (or per-category equivalents) per the agent-iteration playbook. Per-OS manual repro under `docs/repro/h<NN>-bindings-clear-relocation-superK.md`. Integration tests under `tests/integration/test_h<NN>_bindings_revert.py` covering: (a) every reverted chord resolves to its kitty default in `KittySession.list_keymap()`; (b) the cwd-inheritance chords still inherit cwd; (c) the new clear chord still wipes screen + scrollback; (d) `my-kitty keys` reports `0 conflicts`.
- **System mutations**: install copies the updated `.conf` files into the managed dir; uninstall removes them via the same surgical-removal contract. No new dependencies, no new `[project.scripts]` entries. No new payload files; the existing per-category file layout is preserved.
- **Out of scope**: paste preservation (Phase 1 §4, paused — unchanged by this change), monitor disconnect (Phase 1 §6, archived — unchanged), image paste (Phase 1 §7 — not yet proposed). Also out of scope: any introduction of `enabled_layouts splits` or a directional-split chord pair (the user explicitly opted out — kitty's compose model — `ctrl+shift+enter` + `ctrl+shift+l` — is the chosen workflow).
- **Reversibility**: every chord this change reverts is restored to kitty's documented default; rolling back this change restores the prior catalog by re-applying the archived `2026-05-07-phase1-curated-bindings` delta.
