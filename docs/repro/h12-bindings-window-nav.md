# H12 — window-nav category (renumbered from h04)

**Capability:** kitty-curated-bindings (Phase 1 §4, vim-style window/split
navigation).

**Status:** Promoted. Configuration in
[`config/kitty/window-nav.conf`](../../config/kitty/window-nav.conf). Autonomous
test in
[`tests/integration/test_h12_bindings_window_nav.py`](../../tests/integration/test_h12_bindings_window_nav.py).

## Renumbered from h04

Tasks.md originally numbered this hypothesis h04. Following the h11 precedent
(h03 was already taken by `test_h03_introspection.py`), we keep the `h<NN>`
integers contiguous after the late-arriving h09/h10 work: h11 = tab-nav,
h12 = window-nav, then h13/h14/etc. for the remaining phase-1 categories.
design.md D7 + tasks.md §4.4/§4.5 now say h12.

## Why this category exists

Phase 1 §4 (`design.md` D6) puts six chords into a window-navigation group:

| Chord | Our action | Kitty default action |
| --- | --- | --- |
| `ctrl+shift+h` | `neighboring_window left` | `show_scrollback` |
| `ctrl+shift+j` | `neighboring_window down` | `scroll_line_down` |
| `ctrl+shift+k` | `neighboring_window up` | `scroll_line_up` |
| `ctrl+shift+l` | `neighboring_window right` | `next_layout` |
| `ctrl+shift+w` | `close_window` | `close_window` |
| `ctrl+shift+f` | `next_window` | `move_window_forward` |

Five chords genuinely change behaviour: kitty 0.46.x maps `h/j/k/l` to
scrollback / scroll-line / layout actions, and `f` to
`move_window_forward` (rotate window position rather than rotate focus).
window-nav prefers vim-style focus motion (`hjkl`) and round-robin focus
cycling (`f`), so all five become overrides. One chord (`w`) is a redundant
rebind — same action as the kitty default, lifted into the category file
so `my-kitty keys` groups it under `window-nav` instead of `kitty
defaults`. All six are allow-listed in `intentional-overrides.conf`.

`ctrl+shift+k` was previously bound to instant-clear by the §1 work; that
binding moved to `ctrl+shift+x`, exposing the underlying kitty default
(`scroll_line_up`) which window-nav now shadows with `neighboring_window
up`. The design.md D6 prediction "k was clear, now unbound" was off by one
step — the kitty default underneath the clear binding re-emerged once
`ctrl+shift+k` was freed.

See `design.md` D5/D6 for the broader rationale.

## Manual repro

1. `make install`.
2. Open kitty, then build a 2x2 layout: press `ctrl+shift+\\` to vsplit,
   then `ctrl+shift+/` to hsplit each side (or `ctrl+shift+enter` repeatedly
   in the active layout).
3. Press `ctrl+shift+h/j/k/l` → focus moves left/down/up/right between the
   four windows in the active tab.
4. Press `ctrl+shift+f` → focus cycles to the next window (round-robin).
5. Press `ctrl+shift+w` → the focused window closes; focus drops back to
   a sibling.
6. `my-kitty keys` → confirm a `window-nav (6 bindings)` section listing
   each chord with an `[overrides default <kitty default action>]`
   annotation (matching action for `w`; the corresponding kitty default for
   `h/j/k/l/f`) and `0 conflicts.`

## Verifying autonomously

```
KITTI_INTEGRATION=1 uv run pytest tests/integration/test_h12_bindings_window_nav.py -v
```

The probe builds a scratch kitty config that includes `window-nav.conf`,
runs `binding_introspection.enumerate_bindings`, and asserts each chord is
attributed to the `window-nav` source with the expected action and
`override_of` set to the kitty default action being shadowed — different
action for `h/j/k/l/f` (genuine behaviour change), matching action for `w`
(true redundant rebind). All six are allow-listed and carry no
`conflicts_with`.

## Linux Status

Verified on Pop!_OS 24.04 with Kitty 0.46.x on 2026-05-06 by the autonomous
probe (`tests/integration/test_h12_bindings_window_nav.py`).

## macOS Status

Deferred — the agent does not have access to a macOS host. The chords are
in pure-explicit-modifier form (`ctrl+shift+<key>`) and the managed entry
pins `kitty_mod ctrl+shift`, so they SHOULD resolve to the same physical
chords on macOS. Manual confirmation that each chord moves window focus /
closes the window as expected is required before declaring §4 complete on
macOS. Tracked under the umbrella phase1-curated-bindings macOS
verification follow-up.

## Known limitations

* The autonomous probe asserts chord-to-action wiring through
  `binding_introspection`. Behavioural confirmation that
  `neighboring_window left/down/up/right` really does move focus between
  splits is left to the manual repro (kitty's remote-control `send-key`
  injects raw key events without traversing the keymap, so the harness
  cannot simulate the chord press). A behavioural test that spawns two
  windows and calls `session.action("neighboring_window", "right")`
  directly was considered but skipped: the action call exercises kitty's
  dispatcher, not the chord-to-action binding under test, so it would
  duplicate `binding_introspection`'s coverage without adding signal.
