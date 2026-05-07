# H10 — horizontal-split chord move (`ctrl+shift+-` → `ctrl+shift+/`)

**Capability:** kitty-curated-bindings (Phase 1 §5) + kitty-cwd-inheritance
(Phase 1 §1, no behaviour change — only the chord moved).

**Status:** Promoted. Configuration in
[`config/kitty/windowing.conf`](../../config/kitty/windowing.conf). Autonomous
test in
[`tests/integration/test_h10_bindings_hsplit_relocation.py`](../../tests/integration/test_h10_bindings_hsplit_relocation.py).

## Why the chord moved

Phase 1 §5 calls for font-zoom chords; kitty's stock `change_font_size all -2.0`
sits on `ctrl+shift+-`. Our previous hsplit binding shadowed it, which the
binding-introspection probe-04 surfaced as a regression. Moving hsplit to
`ctrl+shift+/` frees `ctrl+shift+-` for font-zoom-out and gives the split
pair a visual mnemonic:

* `ctrl+shift+\` → vertical split (backslash = vertical bar mnemonic).
* `ctrl+shift+/` → horizontal split (forward slash mirrors the vsplit chord).

See `openspec/changes/phase1-curated-bindings/design.md` D4.

## Manual repro

1. `make install`.
2. Open a Kitty window in some directory `~/work/foo`.
3. Press `ctrl+shift+/`. Observe: the window splits horizontally; the new
   pane's cwd is `~/work/foo` (cwd inheritance preserved).
4. Press `ctrl+shift+-`. Observe: kitty's font shrinks by 2pt
   (`change_font_size all -2.0` is the kitty default, no longer shadowed).
5. Run `my-kitty keys`. Observe: the `windowing` section lists `ctrl+shift+/`
   under action `launch --location=hsplit --cwd=current`. The `kitty defaults`
   section lists `ctrl+shift+-` under `change_font_size all -2.0`. The
   `Summary:` line reports `0 conflicts`.

## Verifying autonomously

```
KITTI_INTEGRATION=1 uv run pytest tests/integration/test_h10_bindings_hsplit_relocation.py -v
```

The probe spawns an isolated kitty session with the promoted `windowing.conf`
and asserts (a) `ctrl+shift+/` produces a second window in the same OS
window, (b) `ctrl+shift+-` does NOT, and (c) `binding_introspection` reports
`ctrl+shift+-` under `kitty-default` with action `change_font_size all -2.0`.

## Linux Status

Verified on Pop!_OS 24.04 with Kitty 0.46.2 on 2026-05-06 by the autonomous
probe and a manual `ctrl+shift+/` keystroke against a fresh `make install`.

## macOS Status

Deferred — the agent does not have access to a macOS host. The chord is in
pure-explicit-modifier form (`ctrl+shift+/`) and the managed entry pins
`kitty_mod ctrl+shift`, so the chord SHOULD resolve to the same physical
combination on macOS. Manual confirmation (visible horizontal split with
inherited cwd after `ctrl+shift+/`) is required before declaring §1/§5
complete on macOS. Tracked under the umbrella phase1-curated-bindings
macOS verification follow-up.

## Known limitations

* The autonomous probe asserts the new window count, not visual layout. A
  manual eyeball check is still required to confirm the split is horizontal
  rather than after-the-current-pane.
