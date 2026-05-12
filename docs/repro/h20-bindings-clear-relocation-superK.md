# H20 — instant clear chord moves to host-OS-native modifier

**Capability:** kitty-instant-clear (Phase 1 §2) + kitty-curated-bindings.
Supersedes [h02-clear.md](h02-clear.md) and
[h09-bindings-clear-relocation.md](h09-bindings-clear-relocation.md).

**Status:** Promoted. Configuration in
[`config/kitty/clear-linux.conf`](../../config/kitty/clear-linux.conf)
and [`config/kitty/clear-mac.conf`](../../config/kitty/clear-mac.conf);
the installer picks one and renames it to `clear.conf` in the deployed
payload directory. Autonomous test in
[`tests/integration/test_h02_clear.py`](../../tests/integration/test_h02_clear.py).

## Why the chord moved (again)

The previous chord `ctrl+shift+x` clobbered kitty's
`scroll_to_prompt 1` shell-integration jump (a useful default the
user wants to keep). The user's mental model on instant clear is
**iTerm Cmd+K parity**. On macOS the natural chord is `cmd+k`. On Linux
the closest cultural analogue is `super+k` (kernel-prefixed convention
shared by Pop!_OS, GNOME, KDE). `ctrl+shift+alt+k` is shipped as a
cross-OS fallback in case a compositor grabs Super.

This is the one curated chord in the catalog that intentionally
diverges per OS. Every other chord renders identically on Linux and
macOS. See
`openspec/changes/phase1-curated-bindings-revert-defaults/design.md` D5.

## Manual repro (Linux)

1. Run `make install` to inject our managed config block.
2. Confirm `~/.config/kitty/kitty-setup/clear.conf` exists and binds
   `super+k` plus `ctrl+shift+alt+k`. (The installer renames
   `clear-linux.conf` -> `clear.conf` on Linux.)
3. Open a Kitty window. Generate ~50 distinct lines of output:
   ```
   for i in $(seq 1 50); do echo "marker-$i"; done
   ```
4. Press `super+k`.
5. Observe: the screen is empty above the prompt, scrolling up reveals
   no `marker-*` lines (scrollback wiped). The cursor remains usable.
6. Type `echo post-clear` — output appears at the top of an empty
   screen.
7. Generate ~50 lines again. Press `ctrl+shift+alt+k`. Observe the same
   wipe — the fallback chord triggers the same action.
8. Press `ctrl+shift+x`. Observe: nothing clears; the cursor scrolls
   to the previous prompt (`scroll_to_prompt 1`, kitty's default).

## Manual repro (macOS)

**Deferred — no Mac host available at apply time.** When verifying on
macOS:

1. Run `make install`. Confirm `~/.config/kitty/kitty-setup/clear.conf`
   binds `cmd+k` plus `ctrl+shift+alt+k`. (The installer renames
   `clear-mac.conf` -> `clear.conf` on macOS.)
2. Open kitty, generate scrollback, press `cmd+k`. Expect screen +
   scrollback to wipe within 200 ms.
3. Repeat with `ctrl+shift+alt+k` for the fallback.

Until verified, the fallback chord `ctrl+shift+alt+k` is the documented
macOS path.

## Observable outcome

* `super+k` (Linux) / `cmd+k` (macOS): screen + scrollback wiped,
  cursor still responsive, `< 200 ms` round-trip.
* `ctrl+shift+alt+k`: same outcome on both OSes.
* `ctrl+shift+x`: kitty's default `scroll_to_prompt 1`, no clear.

## How the binding decomposes

```
map super+k          combine : clear_terminal scrollback active : send_text normal,application \x0c
map ctrl+shift+alt+k combine : clear_terminal scrollback active : send_text normal,application \x0c
```

`clear_terminal scrollback active` wipes both the visible screen and
the scrollback buffer in one op. `send_text normal,application \x0c`
issues a form-feed so the shell repaints its prompt cleanly. The
combine ensures both happen atomically on the chord.

## Why `ctrl+shift+alt+k` is shipped on both OSes

COSMIC (Pop!_OS 24.04) does not grab `super+k` today, but the Super
key is compositor-owned and future grabs can appear. Shipping
`ctrl+shift+alt+k` on both OSes gives the user a reachable chord
regardless of compositor behaviour, and preserves cross-OS literal
parity for anyone who prefers identical chords on both hosts.
