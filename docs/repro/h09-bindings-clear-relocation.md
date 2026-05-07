# H09 — instant clear chord move (`ctrl+shift+k` → `ctrl+shift+x`)

**Capability:** kitty-instant-clear (Phase 1 §2) + kitty-curated-bindings.
Supersedes the original H02 manual repro.

**Status:** Promoted. Configuration in
[`config/kitty/clear.conf`](../../config/kitty/clear.conf). Autonomous test in
[`tests/integration/test_h02_clear.py`](../../tests/integration/test_h02_clear.py).

## Why the chord moved

Phase 1 §5 of `docs/requirements.md` requires vim-style window navigation on
`h` / `j` / `k` / `l` under the pinned `kitty_mod ctrl+shift` modifier. Instant
clear was previously bound to `ctrl+shift+k`, which collides with the new
window-nav-up chord. The clear behaviour is unchanged; only the chord moved
to `ctrl+shift+x` (unbound in stock kitty, single-key reach, mnemonic with
"exit/erase"). See `openspec/changes/phase1-curated-bindings/design.md` D3.

The configuration file `config/kitty/bindings.conf` was renamed to
`config/kitty/clear.conf` at the same time — file basename = category, so
`my-kitty keys` reports the binding under a section named `clear` instead of
the misleading `bindings`.

## Manual repro

1. Run `make install` to inject our managed config block.
2. Open a Kitty window. Generate ~50 distinct lines of output:
   ```
   for i in $(seq 1 50); do echo "marker-$i"; done
   ```
3. Press `ctrl+shift+x`.
4. Observe: the screen is empty above the prompt, and scrolling up reveals
   no `marker-*` lines.
5. Type `echo post-clear` — output appears at the top of an empty screen.
6. Press `ctrl+shift+k`. Observe: nothing clears (the chord is no longer
   bound to instant-clear).

## How the binding decomposes

```
map ctrl+shift+x combine : clear_terminal scrollback active : send_text normal,application \x0c
```

* `clear_terminal scrollback active` — clears the scrollback buffer of the
  active window. Visible screen content is left alone by this action.
* `send_text normal,application \x0c` — sends Ctrl-L (form feed) to the
  shell. The shell's readline binding maps Ctrl-L to clear-screen, which
  redraws the prompt on a clean visible buffer.

Combined: visible screen empty + scrollback empty in one keystroke. iTerm
Cmd+K parity, no `reset` round-trip.

## Verifying autonomously

```
KITTI_INTEGRATION=1 uv run pytest tests/integration/test_h02_clear.py -v
```

Three tests cover the relocation, none of which press `ctrl+shift+x`
against a live session — `kitten @ send-key` does not traverse the
keymap, so chord-to-action wiring cannot be exercised remotely (see the
docstring at `tests/integration/test_h02_clear.py:13-17`):

1. **Text-shape check on `clear.conf`.** Asserts the new
   `map ctrl+shift+x ...` line is present and no `ctrl+shift+k` map
   line remains. This is the only automated guard that the chord moved.
2. **Action-chain wipe.** Spawns an isolated Kitty session, writes 50
   marker lines, then invokes the action chain directly via
   `session.action("clear_terminal", "scrollback", "active")` followed
   by `session.send_text("\x0c")`. Asserts no marker text remains in
   `get_text(extent="all")` and that a subsequent `echo post-clear`
   prints cleanly. This verifies the underlying clear behavior still
   works after the chord move; it does NOT verify the new chord is
   wired to that action.
3. **Introspection attribution.** Runs
   `binding_introspection.enumerate_bindings(...)` and asserts
   `ctrl+shift+x` is reported under source `clear` (not `bindings`).

## Linux Status

Verified on Pop!_OS 24.04 with Kitty 0.46.2 and bash 5.2 on 2026-05-06.
The autonomous probe in `tests/integration/test_h02_clear.py` covers the
action chain and the introspection plumbing, but it cannot press the
chord (kitten remote-control does not traverse the keymap). Chord-to-
action wiring is therefore load-bearing on a single manual
`ctrl+shift+x` keystroke against a fresh `make install`, performed on
the date above. Re-running this manual step is required after any
change that touches `config/kitty/clear.conf` or the install/PATH path.

## macOS Status

Deferred — the agent does not have access to a macOS host. The chord is in
pure-explicit-modifier form (`ctrl+shift+x`) and the managed entry pins
`kitty_mod ctrl+shift`, so the chord SHOULD resolve to the same physical
combination on macOS. Manual confirmation (visible screen wipe after
`ctrl+shift+x`) is required before declaring §2 complete on macOS. Tracked
under the umbrella phase1-curated-bindings macOS verification follow-up.

## Known limitations

* Verified on Pop!_OS 24.04 with Kitty 0.46.2 and bash 5.2. Shells other than
  bash may not bind Ctrl-L to clear-screen by default; the binding still
  clears the kitty side, but the visible screen may keep its content until
  the shell repaints. Curated keybinding work in a later change should ship
  shell-side guidance.
