# H01 — cwd inheritance for new tabs / OS windows / splits

**Capability:** kitty-cwd-inheritance (Phase 1 §1).

**Status:** Promoted. Configuration in [`config/kitty/windowing.conf`](../../config/kitty/windowing.conf).
Autonomous test in [`tests/integration/test_h01_cwd.py`](../../tests/integration/test_h01_cwd.py).

## Manual repro

1. Run `make install` to inject our managed config block.
2. Open a Kitty window. In the shell, run `cd /tmp`.
3. Press the keybinding under test:
   - `ctrl+shift+t` → new tab in current OS window.
   - `ctrl+shift+n` → new OS window.
   - `ctrl+shift+enter` → new split in current tab (vertical or horizontal layout).
4. In the new entity, run `pwd`. Expected output: `/tmp`.

## Why we test the action, not the keystroke

`kitten @ send-key` delivers the chord to the foreground TTY (the shell), not to
Kitty's keybinding handler. Once `config_updater`'s parse-check passes, Kitty
knows about the binding — the binding is "if `ctrl+shift+t` is pressed, run THIS
action with THESE args". The meaningful test of the *behavior* is therefore the
action invocation; the binding mapping is configuration we already validated by
parsing.

## Verifying autonomously

```
KITTI_INTEGRATION=1 uv run pytest tests/integration/test_h01_cwd.py -v
```

The test spawns three isolated Kitty sessions (one per case: new tab, new OS
window, new vertical split), invokes `kitten @ launch` with the same arguments
the binding uses, and asserts the new window's `cwd` matches the launching
window's `cwd`.

## Known limitations

* Verified on Pop!_OS 24.04 with Kitty 0.46.2. Other distros / Kitty versions
  not exercised.
* Wayland focus stealing during the test pop-ups is mitigated by
  `--start-as=minimized`. If COSMIC ever stops honoring the flag, switch to
  the nested-compositor fallback documented in design.md (Q1).
