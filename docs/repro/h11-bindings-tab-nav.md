# H11 — tab-nav category (renumbered from h03)

**Capability:** kitty-curated-bindings (Phase 1 §3, tab navigation).

**Status:** Promoted. Configuration in
[`config/kitty/tab-nav.conf`](../../config/kitty/tab-nav.conf). Autonomous
test in
[`tests/integration/test_h11_bindings_tab_nav.py`](../../tests/integration/test_h11_bindings_tab_nav.py).

## Renumbered from h03

Tasks.md originally numbered this hypothesis h03. The slot
`tests/integration/test_h03_introspection.py` is already taken (h03 was used
for binding introspection). To keep the `h<NN>` index unique we shifted this
hypothesis to h11. Design.md D7 + tasks.md §3.4/§3.5 now say h11.

## Why this category exists

Phase 1 §3 (`design.md` D6) puts five chords into a tab-navigation group:

| Chord | Our action | Kitty default action |
| --- | --- | --- |
| `ctrl+shift+]` | `next_tab` | `next_window` |
| `ctrl+shift+[` | `previous_tab` | `previous_window` |
| `ctrl+shift+.` | `move_tab_forward` | `move_tab_forward` |
| `ctrl+shift+,` | `move_tab_backward` | `move_tab_backward` |
| `ctrl+shift+q` | `close_tab` | `close_tab` |

Three chords (`.`, `,`, `q`) are redundant rebinds — same action as the kitty
default, lifted into the category file so `my-kitty keys` groups them under
`tab-nav` instead of `kitty defaults`. Two chords (`]`, `[`) genuinely change
behaviour: kitty 0.46.x maps them to window navigation, but tab-nav owns
them because vim-style window navigation lands on `hjkl` in §4. All five are
allow-listed in `intentional-overrides.conf`. See `design.md` D5/D6 for the
broader rationale.

## Manual repro

1. `make install`.
2. Open kitty, then `ctrl+shift+t` twice to land on tab #3.
3. `ctrl+shift+[` → focus moves to tab #2; `ctrl+shift+]` → tab #3.
4. `ctrl+shift+,` → current tab moves left in the tab bar; `ctrl+shift+.`
   moves it back.
5. `ctrl+shift+q` → current tab closes; focus drops back to the previous tab.
6. `my-kitty keys` → confirm a `tab-nav (5 bindings)` section listing each
   chord with an `[overrides default <kitty default action>]` annotation
   (matching action for `.`/`,`/`q`; `next_window`/`previous_window` for
   `]`/`[`) and `0 conflicts.`

## Verifying autonomously

```
KITTI_INTEGRATION=1 uv run pytest tests/integration/test_h11_bindings_tab_nav.py -v
```

The probe builds a scratch kitty config that includes `tab-nav.conf`,
runs `binding_introspection.enumerate_bindings`, and asserts each chord is
attributed to the `tab-nav` source with the expected action and
`override_of` set to the kitty default action being shadowed — matching
action for `.`/`,`/`q` (true redundant rebind), `next_window`/
`previous_window` for `]`/`[` (genuine behaviour change). All five are
allow-listed and carry no `conflicts_with`.

## Linux Status

Verified on Pop!_OS 24.04 with Kitty 0.46.x on 2026-05-06 by the autonomous
probe (`tests/integration/test_h11_bindings_tab_nav.py`).

## macOS Status

Deferred — the agent does not have access to a macOS host. The chords are in
pure-explicit-modifier form (`ctrl+shift+<key>`) and the managed entry pins
`kitty_mod ctrl+shift`, so they SHOULD resolve to the same physical chords on
macOS. Manual confirmation that each chord changes the active tab / closes
the tab as expected is required before declaring §3 complete on macOS. Tracked
under the umbrella phase1-curated-bindings macOS verification follow-up.

## Known limitations

* The autonomous probe asserts chord-to-action wiring through
  `binding_introspection`. Behavioural confirmation that the actions really do
  switch tabs is left to the manual repro (kitty's remote-control `send-key`
  injects raw key events without traversing the keymap, so the harness cannot
  simulate the chord press).
