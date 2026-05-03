# H02 — instant screen + scrollback clear

**Capability:** kitty-instant-clear (Phase 1 §2).

**Status:** Promoted. Configuration in [`config/kitty/bindings.conf`](../../config/kitty/bindings.conf).
Autonomous test in [`tests/integration/test_h02_clear.py`](../../tests/integration/test_h02_clear.py).

## Manual repro

1. Run `make install` to inject our managed config block.
2. Open a Kitty window. Generate ~50 distinct lines of output:
   ```
   for i in $(seq 1 50); do echo "marker-$i"; done
   ```
3. Press `ctrl+shift+k`.
4. Observe: the screen is empty above the prompt, and scrolling up reveals
   no `marker-*` lines.
5. Type `echo post-clear` — output appears at the top of an empty screen.

## How the binding decomposes

```
map ctrl+shift+k combine : clear_terminal scrollback active : send_text normal,application \x0c
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

The test spawns an isolated Kitty session, writes 50 marker lines, then
invokes both halves of the combine via `kitten @ action` + `send-text` and
asserts no marker text remains in `get_text(extent="all")`.

## Known limitations

* Verified on Pop!_OS 24.04 with Kitty 0.46.2 and bash 5.2. Shells other than
  bash may not bind Ctrl-L to clear-screen by default; the binding still
  clears the kitty side, but the visible screen may keep its content until
  the shell repaints. Curated keybinding work in a later change should ship
  shell-side guidance.
