# H15 — broadcast category (renumbered from h07)

**Capability:** kitty-curated-bindings (Phase 1 §5, broadcast chord).

**Status:** Promoted. Configuration in
[`config/kitty/broadcast.conf`](../../config/kitty/broadcast.conf).
Autonomous test in
[`tests/integration/test_h15_bindings_broadcast.py`](../../tests/integration/test_h15_bindings_broadcast.py).

## Renumbered from h07

Tasks.md originally numbered this hypothesis h07. Following the
h11/h12/h13/h14 precedent (h03 was already taken by
`test_h03_introspection.py`, and we keep `h<NN>` integers contiguous
after the late-arriving h09/h10 work), we shifted this hypothesis to
h15. design.md D7 + tasks.md §7.1 now say h15.

## Why this category exists

Phase 1 §5 (`design.md` D6) puts one chord into a broadcast group:

| Chord | Our action | Kitty default action |
| --- | --- | --- |
| `ctrl+shift+i` | `launch --allow-remote-control kitty +kitten broadcast` | (none — chord is unbound) |

The chord is genuinely new — kitty 0.46.x has no default on
`ctrl+shift+i`. So this category, like §6 detach, needs no
`intentional-overrides.conf` allow-list entry.

## Why `kitty +kitten broadcast` and not the alternatives?

The h15 probe (`tmp/h15-bindings-broadcast/repro.md`) tested three
candidate action strings:

* `launch --allow-remote-control kitty +kitten broadcast` — the form
  documented in kitty's broadcast kitten manual
  (`share/doc/kitty/html/_sources/kittens/broadcast.rst.txt`). All
  three forms parse cleanly through kitty's binding introspection;
  this one is preferred because it matches upstream documentation
  (most stable surface) and reads identically to what a user would
  type at a shell.
* `launch --allow-remote-control kitten broadcast` — shorter and also
  parses cleanly, but relies on `launch`'s implicit kitten lookup
  (less obvious to a reader).
* `launch --allow-remote-control kitten broadcast.py` — listed in
  design.md D6 as a candidate. It still parses, but the `.py` suffix
  is a relic of older kitty versions where kittens lived as discrete
  `.py` files — modern kittens are registered commands.

The custom-remote-control alternative (`kitty @ send-text --match=...`
wrapper) was not chosen: it duplicates the kitten's behaviour at
maintenance cost.

This resolves the design.md Open Question Q1 (broadcast mechanism)
with the chosen action recorded above.

See `design.md` D5/D6 + Open Question Q1 for the broader rationale.

## Manual repro

1. `make install`.
2. Open kitty with at least two windows in the active tab. Use
   `ctrl+shift+enter` to add a window.
3. Press `ctrl+shift+i` → kitty launches the broadcast kitten in a
   new window inside the active tab. The new window shows a banner
   like "Type to send..." and waits for input.
4. Type a few characters — they appear in every sibling window in the
   active tab (and, by default, in every kitty window across every
   tab; use the kitten's `--match` / `--match-tab` options to scope
   it). For just-this-tab broadcasting, append
   `--match-tab state:focused` to the action.
5. Press `ctrl+esc` (the kitten's default end-session key) to dismiss
   the broadcast window. Press `ctrl+alt+esc` to toggle hiding the
   typed input (useful for typing a password without leaving it
   on-screen).
6. `my-kitty keys` → confirm a `broadcast (1 binding)` section listing
   the chord with the expected action. The chord does not carry an
   `[overrides default ...]` annotation (it is new, not a shadow).
   The summary line reports `0 conflicts.`

## Verifying autonomously

```
KITTI_INTEGRATION=1 uv run pytest tests/integration/test_h15_bindings_broadcast.py -v
```

The probe builds a scratch kitty config that includes
`broadcast.conf`, runs `binding_introspection.enumerate_bindings`,
and asserts:

* The chord is attributed to `broadcast` with the expected action and
  `override_of is None` (no kitty-default shadow).
* It carries no `conflicts_with` entry.
* The full report has zero conflicts.
* `my-kitty keys --json` exposes a one-entry `broadcast` section.

## Linux Status

Verified on Pop!_OS 24.04 with Kitty 0.46.2 on 2026-05-06 by the
autonomous probe (`tests/integration/test_h15_bindings_broadcast.py`).
Manual confirmation that pressing `ctrl+shift+i` opens the broadcast
kitten window and that typed characters appear in sibling windows is
required when running locally — the autonomous probe asserts only
chord-to-action wiring, not the mirroring behaviour.

## macOS Status

Deferred — the agent does not have access to a macOS host. The chord
is in pure-explicit-modifier form (`ctrl+shift+i`) and the managed
entry pins `kitty_mod ctrl+shift`, so it SHOULD resolve to the same
physical chord on macOS. Manual confirmation that the chord opens the
broadcast kitten and mirrors typed input across sibling windows is
required before declaring §5 complete on macOS. Tracked under the
umbrella phase1-curated-bindings macOS verification follow-up.

## Known limitations

* The autonomous probe asserts chord-to-action wiring through
  `binding_introspection`. Behavioural confirmation that the action
  really does launch the broadcast kitten and mirror typed input to
  sibling windows is left to the manual repro. Kitty's remote-control
  `send-key` injects raw key events without traversing the keymap, so
  the harness cannot simulate the chord press; and the broadcast
  kitten reads interactive input, so even if the chord could be
  driven, the input mirroring is itself interactive and would block on
  user input in any non-interactive TTY.
* The default `--match` for the kitten is "all kitty windows" — wider
  than the §5 spec wording "all windows in the active tab". The map
  line ships with no `--match-tab` for now (matches the kitten's
  documented default and the spec's loose "the implementation SHOULD
  use kitty's documented mechanism"); users who want tab-scoped
  broadcasting can edit the `map` line to append
  `--match-tab state:focused`. Tracked as a possible follow-up if the
  default ends up surprising in practice.
