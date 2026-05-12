# H19 — released chords resolve to kitty defaults

**Capability:** kitty-curated-bindings (Phase 1 §5).
Supersedes the vim-style hjkl assertions in
[h12-bindings-window-nav.md](h12-bindings-window-nav.md), the
`ctrl+shift+0` -> font-reset assertion in
[h13-bindings-font-zoom.md](h13-bindings-font-zoom.md), the `]`/`[`
-> tab-nav assertion in [h11-bindings-tab-nav.md](h11-bindings-tab-nav.md),
and the vsplit/hsplit chord pair in
[h10-bindings-hsplit-relocation.md](h10-bindings-hsplit-relocation.md).

**Status:** Promoted. Configuration in
[`config/kitty/`](../../config/kitty/). Autonomous test in
[`tests/integration/test_h19_bindings_revert.py`](../../tests/integration/test_h19_bindings_revert.py).

## Why the chords reverted

The user's restated mental model is "curate kitty defaults, do not
replace them". The archived `phase1-curated-bindings` change introduced
13 semantic overrides; several clobbered useful kitty defaults
(`show_scrollback`, `scroll_line_down`/`up`, `next_layout`,
`search_scrollback`, `tenth_window`, `scroll_to_prompt 1`). The most
load-bearing loss was `ctrl+shift+l` — the user's daily-driver workflow
is `ctrl+shift+enter` to open a new window then `ctrl+shift+l` to flip
the layout, and the hjkl rebind broke step 2. See
`openspec/changes/phase1-curated-bindings-revert-defaults/design.md`
D1–D4.

## Manual repro

1. Run `make install` to inject our managed config block.
2. Open a fresh kitty window.
3. Press `ctrl+shift+h` — kitty's scrollback pager (`show_scrollback`)
   opens. Press `q` to exit it.
4. Generate some scrollback (e.g. `ls -l /etc | head -100`). Press
   `ctrl+shift+j` and `ctrl+shift+k` — the view scrolls one line at a
   time (`scroll_line_down` / `scroll_line_up`).
5. Open a new window with `ctrl+shift+enter`. Press `ctrl+shift+l` —
   the layout cycles (`next_layout`). Press it again to advance the
   cycle.
6. Press `ctrl+shift+0` — focus jumps to the tenth window if one
   exists, otherwise no-op (kitty's `tenth_window`). It does NOT reset
   the font size. (Reset moves to `ctrl+shift+backspace`, kitty's
   default.)
7. Run any command. Press `ctrl+shift+x` — scrolls to the previous
   shell prompt (`scroll_to_prompt 1`) instead of clearing the screen.
   Instant clear has moved to `super+k` / `cmd+k`; see
   [h20-bindings-clear-relocation-superK.md](h20-bindings-clear-relocation-superK.md).
8. Press `ctrl+shift+/` — kitty's scrollback search opens
   (`search_scrollback`). Press `Esc` to dismiss.

## Observable outcome

* `ctrl+shift+h` opens the scrollback pager.
* `ctrl+shift+j` / `ctrl+shift+k` scroll one line at a time.
* `ctrl+shift+l` cycles layouts.
* `ctrl+shift+0` targets `tenth_window`.
* `ctrl+shift+x` triggers `scroll_to_prompt 1`.
* `ctrl+shift+/` opens scrollback search.

## How the revert was implemented

* `config/kitty/window-nav.conf` — four redundant rebinds (`]`, `[`,
  `f`, `w`); hjkl removed; the `f -> next_window` rebind removed.
* `config/kitty/tab-nav.conf` — five redundant rebinds (`right`,
  `left`, `.`, `,`, `q`); `]`/`[` -> tab-nav rebind removed.
* `config/kitty/font-zoom.conf` — three redundant rebinds (`=`, `-`,
  `backspace`); `0` -> font-reset removed.
* `config/kitty/windowing.conf` — three cwd-inheriting creators (`t`,
  `n`, `enter`); vsplit/hsplit chord pair removed.
* `config/kitty/intentional-overrides.conf` — pruned to six entries
  (three windowing creators + three clear chords).
* `src/kitty_setup/binding_introspection.py` — same-(chord, action)
  rebinds are detected and marked `redundant=True` (no override, no
  conflict). Allow-list entries no longer needed for redundant
  rebinds. See design D7.

## macOS Status

**Deferred.** Linux verified at apply time on Pop!_OS 24.04 + COSMIC +
kitty 0.46.x. No Mac host available; the kitty defaults for these
chords are documented identical across OSes (kitty's `kitty_mod` differs
but pinning `ctrl+shift` in `kitty-setup.conf` keeps the chord literals
identical). Verify on the next available macOS host.

## How the introspection report changes

Before: `Summary: 21 ours, ~64 defaults, 0 conflicts.` with 13 chords
annotated `[overrides default <action>]`.

After: `Summary: 15 ours, ~64 defaults, 0 conflicts.` with 3 chords
annotated `[overrides default <action>]` (the three cwd-inheriting
windowing creators) and 12 chords annotated `[redundant rebind of kitty
default]`. Clear chords (two on each OS) are net-new with no kitty
default — no annotation.
