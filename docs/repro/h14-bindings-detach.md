# H14 — detach category (renumbered from h06)

**Capability:** kitty-curated-bindings (Phase 1 §5, detach chords).

**Status:** Promoted. Configuration in
[`config/kitty/detach.conf`](../../config/kitty/detach.conf). Autonomous
test in
[`tests/integration/test_h14_bindings_detach.py`](../../tests/integration/test_h14_bindings_detach.py).

## Renumbered from h06

Tasks.md originally numbered this hypothesis h06. Following the
h11/h12/h13 precedent (h03 was already taken by
`test_h03_introspection.py`, and we keep `h<NN>` integers contiguous
after the late-arriving h09/h10 work), we shifted this hypothesis to
h14. design.md D7 + tasks.md §6.1 now say h14.

## Why this category exists

Phase 1 §5 (`design.md` D6) puts two chords into a detach group:

| Chord | Our action | Kitty default action |
| --- | --- | --- |
| `ctrl+shift+d` | `detach_window ask` | (none — chord is unbound) |
| `ctrl+shift+alt+d` | `detach_tab ask` | (none — chord is unbound) |

Both chords are genuinely new — kitty 0.46.x has neither bound by
default. So this category is the first in the change where no chord
needs an `intentional-overrides.conf` allow-list entry (contrast §3 /
§4 / §5, where every chord either replaced a kitty default or was a
redundant rebind of one).

## Why `ask` and not `new-tab` / `new-os-window`?

Kitty exposes two flavours per detach action:

* `detach_window ask` / `detach_tab ask` — open an interactive picker
  that lists existing tabs / OS windows so the user chooses the target.
* `detach_window new-tab` / `detach_tab new-os-window` — non-interactive;
  always create a new tab / OS window.

The §6 spec says "kitty-supported equivalent that prompts the user for
target." The `ask` variants are exactly that prompt. With a single
target, the picker still works (lists the lone candidate); with
multiple, it presents a useful chooser. The non-interactive variants
would skip the prompt entirely and always create a fresh container —
fine, but less aligned with the spec wording and with design.md D6's
table.

The h14 probe ran the action strings through kitty's parser via
`binding_introspection.enumerate_bindings` and confirmed both `ask`
flavours parse cleanly. Behavioural confirmation that the picker
appears is left to the manual repro below — kitty remote control's
`send-key` cannot traverse the keymap (consistent with the §4/§5
precedent), so the autonomous probe asserts only "the chord is
registered with the expected action."

See `design.md` D5/D6 for the broader rationale.

## Manual repro

1. `make install`.
2. Open kitty with at least two tabs (so the picker has more than one
   candidate target). Open a tab with `ctrl+shift+t`, optionally a
   second OS window with `ctrl+shift+n`.
3. Press `ctrl+shift+d` → kitty opens an interactive picker listing
   target tabs (and a `New tab` option). Pick one → the active window
   detaches into the chosen tab.
4. Press `ctrl+shift+alt+d` → kitty opens an interactive picker listing
   target OS windows (and a `New OS Window` option). Pick one → the
   active tab detaches into the chosen target.
5. `my-kitty keys` → confirm a `detach (2 bindings)` section listing
   each chord with the expected action. Neither chord carries an
   `[overrides default ...]` annotation (they are new bindings, not
   shadows). The summary line reports `0 conflicts.`

## Verifying autonomously

```
KITTI_INTEGRATION=1 uv run pytest tests/integration/test_h14_bindings_detach.py -v
```

The probe builds a scratch kitty config that includes `detach.conf`,
runs `binding_introspection.enumerate_bindings`, and asserts:

* Each chord is attributed to `detach` with the expected action and
  `override_of is None` (no kitty-default shadow).
* Neither carries a `conflicts_with` entry.
* The full report has zero conflicts.
* `my-kitty keys --json` exposes a two-entry `detach` section.

## Linux Status

Verified on Pop!_OS 24.04 with Kitty 0.46.2 on 2026-05-06 by the
autonomous probe (`tests/integration/test_h14_bindings_detach.py`).
Manual confirmation that `ctrl+shift+d` opens kitty's interactive
window-detach picker and `ctrl+shift+alt+d` opens kitty's interactive
tab-detach picker is required when running locally — the autonomous
probe asserts only chord-to-action wiring.

## macOS Status

Deferred — the agent does not have access to a macOS host. The chords
are in pure-explicit-modifier form (`ctrl+shift+d`,
`ctrl+shift+alt+d`) and the managed entry pins `kitty_mod ctrl+shift`,
so they SHOULD resolve to the same physical chords on macOS. Manual
confirmation that each chord opens kitty's interactive detach picker
as expected is required before declaring §5 complete on macOS.
Tracked under the umbrella phase1-curated-bindings macOS verification
follow-up.

## Known limitations

* The autonomous probe asserts chord-to-action wiring through
  `binding_introspection`. Behavioural confirmation that the actions
  really do open the interactive picker (and that the picker really
  does detach the window/tab into the chosen target) is left to the
  manual repro. Kitty's remote-control `send-key` injects raw key
  events without traversing the keymap, so the harness cannot simulate
  the chord press; and even if it could, the picker UX is itself
  interactive and would block on user input in any non-interactive TTY.
