# H13 — font-zoom category (renumbered from h05)

> **Superseded by [h19-bindings-revert.md](h19-bindings-revert.md).**
> The `ctrl+shift+0` -> font-reset override was dropped — `0` returns
> to kitty's `tenth_window`. Reset is on `ctrl+shift+backspace`
> (kitty's default), restated as a redundant rebind. See
> `openspec/changes/phase1-curated-bindings-revert-defaults/design.md` D4.

**Capability:** kitty-curated-bindings (Phase 1 §5, font-zoom chords).

**Status:** Promoted. Configuration in
[`config/kitty/font-zoom.conf`](../../config/kitty/font-zoom.conf). Autonomous
test in
[`tests/integration/test_h13_bindings_font_zoom.py`](../../tests/integration/test_h13_bindings_font_zoom.py).

## Renumbered from h05

Tasks.md originally numbered this hypothesis h05. Following the h11/h12
precedent (h03 was already taken by `test_h03_introspection.py`, and we
keep `h<NN>` integers contiguous after the late-arriving h09/h10 work),
we shifted this hypothesis to h13. design.md D7 + tasks.md §5.4/§5.5 now
say h13.

## Why this category exists

Phase 1 §5 (`design.md` D6) puts three chords into a font-zoom group:

| Chord | Our action | Kitty default action |
| --- | --- | --- |
| `ctrl+shift+=` | `change_font_size all +2.0` | `change_font_size all +2.0` |
| `ctrl+shift+-` | `change_font_size all -2.0` | `change_font_size all -2.0` |
| `ctrl+shift+0` | `change_font_size all 0` | `tenth_window` |

Two chords (`=`, `-`) are redundant rebinds — same action as the kitty
default, lifted into the category file so `my-kitty keys` groups them
under `font-zoom` instead of `kitty defaults`. One chord (`0`) genuinely
changes behaviour: kitty 0.46.x maps `ctrl+shift+0` to `tenth_window`
(focus the tenth window in the active tab) and binds the font-reset
action on `ctrl+shift+backspace`. The §5 spec wants the reset action on
`ctrl+shift+0` (the obvious chord, mnemonic for "back to zero"), so our
binding overrides. The kitty default `ctrl+shift+backspace` reset chord
stays under `kitty defaults` and continues to work for users who prefer
it. All three chords are allow-listed in `intentional-overrides.conf`.

`ctrl+shift+-` was previously bound by `windowing.conf` to
`launch --location=hsplit --cwd=current`; §2 moved hsplit to
`ctrl+shift+/`, which freed the chord for this category. The
autonomous probe asserts the chord is now attributed to source
`font-zoom` (not `windowing`), closing the
`fix-ctrl-shift-minus-collision` follow-up named in the archived
`phase1-binding-introspection` proposal.

See `design.md` D5/D6 for the broader rationale.

## Manual repro

1. `make install`.
2. Open kitty and type a line of visible text:

   ```
   echo "the quick brown fox jumps over the lazy dog"
   ```

3. Press `ctrl+shift+=` → text gets visibly larger (font size +2pt).
   Repeat to confirm it keeps growing.
4. Press `ctrl+shift+-` → text gets visibly smaller (font size -2pt).
   Repeat to confirm it keeps shrinking. Note this is no longer the
   hsplit chord — pre-§2 it would have created a horizontal split here.
5. Press `ctrl+shift+0` → font size resets to the configured default
   (the `font_size` value in your kitty.conf, typically the value
   inherited from kitty defaults).
6. `my-kitty keys` → confirm a `font-zoom (3 bindings)` section listing
   each chord with the expected action. `=`/`-` carry
   `[overrides default change_font_size all ±2.0]` (matching action,
   true redundant rebind); `0` carries
   `[overrides default tenth_window]` (genuine behaviour change). The
   summary line reports `0 conflicts.`

## Verifying autonomously

```
KITTI_INTEGRATION=1 uv run pytest tests/integration/test_h13_bindings_font_zoom.py -v
```

The probe builds a scratch kitty config that includes `font-zoom.conf`,
runs `binding_introspection.enumerate_bindings`, and asserts:

* Each chord is attributed to `font-zoom` with the expected action and
  `override_of` set to the kitty default action being shadowed —
  matching action for `=`/`-` (true redundant rebind), `tenth_window`
  for `0` (genuine behaviour change).
* All three are allow-listed and carry no `conflicts_with`.
* `ctrl+shift+-` is attributed to source `font-zoom`, NOT `windowing`.
  This is the load-bearing assertion for §2's hsplit-relocation
  collision fix — if it fires, hsplit slipped back onto `ctrl+shift+-`.

## Linux Status

Verified on Pop!_OS 24.04 with Kitty 0.46.x on 2026-05-06 by the
autonomous probe (`tests/integration/test_h13_bindings_font_zoom.py`)
and visible-font-change manual confirmation.

## macOS Status

Deferred — the agent does not have access to a macOS host. The chords
are in pure-explicit-modifier form (`ctrl+shift+<key>`) and the managed
entry pins `kitty_mod ctrl+shift`, so they SHOULD resolve to the same
physical chords on macOS. Manual confirmation that each chord changes
the visible font size as expected is required before declaring §5
complete on macOS. Tracked under the umbrella phase1-curated-bindings
macOS verification follow-up.

## Known limitations

* The autonomous probe asserts chord-to-action wiring through
  `binding_introspection`. Behavioural confirmation that the actions
  really do change the visible font size is left to the manual repro
  (kitty's remote-control `send-key` injects raw key events without
  traversing the keymap, so the harness cannot simulate the chord
  press). The manual repro is one of the few in this change-set where
  visible behavioural confirmation is straightforward (text gets
  bigger / smaller / resets) — exercise it when verifying.
